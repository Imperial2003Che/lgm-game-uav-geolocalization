"""Bounded read-only style/author-field inspection; writes only a new research report."""
import datetime
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent
BIB = OUT / 'manuscript_camp_dac_context_20260930_1948/manuscript/refs.bib'
BST = Path(r'C:\Users\17703\AppData\Local\Programs\MiKTeX\bibtex\bst\ieeetran\IEEEtran.bst')
CLS = Path(r'C:\Users\17703\AppData\Local\Programs\MiKTeX\tex\latex\ieeetran\IEEEtran.cls')
KEYS = ('vlgeo2026', 'clip2021', 'sdpl2024', 'mixedprecision2018', 'mobilegeo2026')
DEST = HERE / 'SELECTED_AUTHORS_AND_LOCAL_BST.json'
assert not DEST.exists(), 'single-use report destination already exists'
assert BIB.stat().st_size < 65536
raw = BIB.read_bytes()
text = raw.decode('utf-8')

def braced_value(start):
    assert text[start] == '{'
    depth, i = 1, start + 1
    while i < len(text):
        c = text[i]
        if c == '\\':
            i += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    raise AssertionError('unclosed selected value')

def top_level_and_names(author):
    """Delimiter scan: whitespace AND whitespace outside protected braces."""
    names, depth, start, i, separators = [], 0, 0, 0, []
    while i < len(author):
        if author[i] == '\\':
            i += 2
            continue
        if author[i] == '{':
            depth += 1
        elif author[i] == '}':
            depth -= 1
            assert depth >= 0
        elif depth == 0 and author[i].isspace():
            match = re.match(r'\s+and\s+', author[i:], flags=re.IGNORECASE)
            if match:
                names.append(author[start:i].strip())
                separators.append({'offset': i, 'literal': match.group(0)})
                i += len(match.group(0))
                start = i
                continue
        i += 1
    assert depth == 0
    names.append(author[start:].strip())
    assert all(names)
    assert all(name.casefold() != 'others' for name in names)
    return names, separators

selected = []
for key in KEYS:
    entry = list(re.finditer(r'@([A-Za-z]+)\s*\{\s*' + re.escape(key) + r'\s*,', text))
    assert len(entry) == 1, key
    _, entry_end = braced_value(text.find('{', entry[0].start()))
    entry_text = text[entry[0].end():entry_end - 1]
    author = list(re.finditer(r'\bauthor\s*=\s*\{', entry_text, re.IGNORECASE))
    assert len(author) == 1, key
    opening = entry[0].end() + author[0].end() - 1
    value, end = braced_value(opening)
    names, separators = top_level_and_names(value)
    regular_split = [n.strip() for n in re.split(r'\s+and\s+', value, flags=re.IGNORECASE)]
    assert names == regular_split, 'selected fields contain no protected AND discrepancy'
    selected.append({
        'key': key, 'entry_type': entry[0].group(1),
        'author_start_line_1based': text[:opening].count('\n') + 1,
        'author_end_line_1based': text[:end].count('\n') + 1,
        'author_value_exact_decoded': value,
        'author_value_utf8_bytes': len(value.encode('utf-8')),
        'author_value_sha256': hashlib.sha256(value.encode('utf-8')).hexdigest(),
        'author_count': len(names), 'names_in_original_order': names,
        'separator_literals': separators,
        'contains_protected_braces': '{' in value or '}' in value,
        'more_than_six': len(names) > 6,
        'first_author_metadata': names[0],
        'not_author_identity_or_bibliographic_metadata_audit': True,
    })

def local_blocks(path, ranges):
    assert path.stat().st_size < 400000
    retained = {f'{lo}-{hi}': [] for lo, hi in ranges}
    highest = max(hi for _, hi in ranges)
    with path.open('r', encoding='utf-8', newline='') as file:
        for n, line in enumerate(file, 1):
            if n > highest:
                break
            for lo, hi in ranges:
                if lo <= n <= hi:
                    retained[f'{lo}-{hi}'].append(line)
    result = []
    for (lo, hi), lines in zip(ranges, retained.values()):
        assert len(lines) == hi - lo + 1
        piece = ''.join(lines)
        result.append({'first_line': lo, 'last_line': hi,
                       'exact_decoded_text': piece,
                       'selected_block_utf8_sha256': hashlib.sha256(piece.encode('utf-8')).hexdigest()})
    return {'path': str(path), 'file_bytes_metadata_only': path.stat().st_size,
            'full_file_hash_not_read_or_claimed': True,
            'selected_blocks': result}

bst = local_blocks(BST, ((1, 48), (90, 106), (288, 302), (358, 364), (525, 540),
                          (1198, 1249), (1273, 1285), (2260, 2278),
                          (2295, 2317), (2366, 2378), (2390, 2406)))
cls = local_blocks(CLS, ((4432, 4445),))
report = {
    'schema': 'ieee-author-display-local-review.v1',
    'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope': 'five named current author fields and selected installed BST/class source blocks only',
    'refs': {'path': str(BIB), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
    'parser_scope': 'BibTeX braced field extraction with brace/escape-aware whitespace-AND delimiter scan; these five fields contain ordinary individual names and no protected brace groups',
    'selected_authors': selected, 'local_bst': bst, 'local_class': cls,
    'supported_candidate_parameters': {'CTLuse_forced_etal': 'yes', 'CTLmax_names_forced_etal': '6', 'CTLnames_show_etal': '1'},
    'source_logic': {
        'forced_etal_default': False,
        'default_threshold': 10,
        'default_shown_names': 1,
        'comparison': 'numnames > max.num.names.before.forced.et.al',
        'six_authors_unchanged_under_candidate': True,
        'candidate_more_than_six_shows_first_then_etal': True,
        'author_and_editor_use_same_format_names': True,
        'bstctlcite_writes_aux_citation_not_visible_citation': True,
        'control_entry_updates_settings_not_regular_bibitem': True,
        'control_must_be_processed_before_regular_entries': True,
        'candidate_is_global_name_display_control_not_venue_filter': True,
    },
    'not_executed': ['BibTeX', 'LaTeX compilation', 'manuscript editing', 'refs editing', 'BST/class editing', 'scientific import/execution', 'COM/HH', 'installation'],
    'page_reduction': 'not tested; no claim',
    'not_all_44_reference_names_or_metadata_audited': True,
    'no_manuscript_or_handoff_modified': True,
}
with DEST.open('x', encoding='utf-8', newline='\n') as file:
    json.dump(report, file, ensure_ascii=False, indent=2)
    file.write('\n')
content = DEST.read_bytes()
print(json.dumps({'report': str(DEST), 'bytes': len(content),
                  'sha256': hashlib.sha256(content).hexdigest(),
                  'counts': {row['key']: row['author_count'] for row in selected},
                  'scope': report['scope']}, ensure_ascii=False))
