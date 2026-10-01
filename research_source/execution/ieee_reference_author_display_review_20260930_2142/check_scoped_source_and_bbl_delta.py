"""New read-only delta inspection; no producer, BST interpreter, or compiler execution."""
import datetime
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
OUT = EX.parent
PREP = EX / 'manuscript_ieee_reference_scope_20260930_2155'
DRAFT = OUT / 'manuscript_ieee_reference_scope_20260930_2155/manuscript'
PARENT = OUT / 'manuscript_camp_dac_context_20260930_1948/manuscript'
GLOBAL = OUT / 'manuscript_ieee_reference_display_20260930_2145/manuscript'
KEYS = ('lpn2022', 'sdpl2024', 'vlgeo2026', 'eagle2025', 'r2ploc2025', 'rendering2025')
PRESERVED = ('clip2021', 'mixedprecision2018', 'mobilegeo2026')
DEST = HERE / 'SOURCE_SCOPE_ADDENDUM.json'
assert not DEST.exists(), 'single-use delta report already exists'
bindings = []

def read(path, bound=100000):
    path = Path(path)
    assert 0 <= path.stat().st_size < bound
    raw = path.read_bytes()
    bindings.append({'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    return raw

report_raw = read(PREP / 'SCOPED_DISPLAY_REVISION.json')
producer_report = json.loads(report_raw)
assert producer_report['allowlist'] == list(KEYS)
assert producer_report['compilation_completed'] is False
producer_sources = [read(PREP / name) for name in
                    ('derive_scoped_author_display.py', 'finalize_braced_venue_fields.py')]
main_patch = read(PREP / 'main.tex.patch')
bst_patch = read(PREP / 'IEEEtran_lgm_display.bst.patch')
main_parent = read(GLOBAL / 'main.tex')
main = read(DRAFT / 'main.tex')
assert main_parent.count(b'\\bibliographystyle{IEEEtran}') == 1
assert main == main_parent.replace(b'\\bibliographystyle{IEEEtran}', b'\\bibliographystyle{IEEEtran_lgm_display}', 1)
assert b'\\clearpage' in main
assert main.count(b'\\bstctlcite{IEEEAuthorDisplayControl}') == 1
assert main.index(b'\\bstctlcite{IEEEAuthorDisplayControl}') < main.index(b'\\cite{')
assert b'\\bibliography{ieee_controls,refs}' in main
control = read(DRAFT / 'ieee_controls.bib')
assert b'CTLuse_forced_etal = {yes}' in control
assert b'CTLmax_names_forced_etal = {6}' in control
assert b'CTLnames_show_etal = {1}' in control
bst_before = read(PREP / 'IEEEtran.bst.before')
bst = read(DRAFT / 'IEEEtran_lgm_display.bst')
guard = (b'          cite$ "lpn2022" = cite$ "sdpl2024" = or\n'
         b'          cite$ "vlgeo2026" = or cite$ "eagle2025" = or\n'
         b'          cite$ "r2ploc2025" = or cite$ "rendering2025" = or and\n')
if b'\r\n' in bst_before:
    guard = guard.replace(b'\n', b'\r\n')
assert bst.count(guard) == 1 and bst.replace(guard, b'', 1) == bst_before
anchor = b'          is.forced.et.al and and'
assert bst.count(anchor + (b'\r\n' if b'\r\n' in bst_before else b'\n') + guard) == 1

refs_parent = read(PARENT / 'refs.bib')
refs = read(DRAFT / 'refs.bib')
assert refs == refs_parent
text = refs.decode('utf-8')

def field(entry, name):
    match = re.search(r'\b' + re.escape(name) + r'\s*=\s*\{', entry)
    assert match
    start, depth, i = match.end(), 1, match.end()
    while i < len(entry):
        if entry[i] == '\\':
            i += 2
            continue
        if entry[i] == '{':
            depth += 1
        elif entry[i] == '}':
            depth -= 1
            if depth == 0:
                return entry[start:i]
        i += 1
    raise AssertionError('unclosed selected field')

venues = []
for key in KEYS:
    entry = re.search(r'@\w+\{' + re.escape(key) + r',(.*?)(?=\n@|\Z)', text, re.S)
    assert entry
    venue = field(entry[1], 'journal')
    authors = field(entry[1], 'author')
    assert not ('{' in authors or '}' in authors), 'these selected fields contain no protected corporate author'
    names = re.split(r'\s+and\s+', authors.strip())
    assert len(names) > 6 and all(names) and 'others' not in [n.casefold() for n in names]
    assert venue.replace('{', '').replace('}', '').startswith('IEEE ')
    assert not re.search(r'\beditor\s*=', entry[1])
    venues.append({'key': key, 'journal_raw': venue, 'author_count': len(names),
                   'names_in_original_order': names, 'no_editor': True,
                   'scope': 'current source metadata only; publisher metadata not newly web-audited'})

def blocks(raw):
    matches = list(re.finditer(rb'\\bibitem\{([^{}]+)\}\r?\n', raw))
    assert len(matches) == 44
    keys = [m.group(1).decode('ascii') for m in matches]
    assert len(set(keys)) == len(keys)
    footer_start = raw.index(b'\\end{thebibliography}', matches[-1].end())
    body = {}
    for i, match in enumerate(matches):
        stop = matches[i + 1].start() if i + 1 < len(matches) else footer_start
        body[keys[i]] = raw[match.end():stop]
    return keys, body, raw[:matches[0].start()], raw[footer_start:]

parent_bbl = read(PARENT / 'main.bbl')
new_bbl = read(DRAFT / 'main.bbl')
oldkeys, oldblocks, oldhead, oldfoot = blocks(parent_bbl)
newkeys, newblocks, newhead, newfoot = blocks(new_bbl)
assert oldkeys == newkeys
assert oldhead == newhead and oldfoot == newfoot
assert 'IEEEAuthorDisplayControl' not in newkeys
changed = [key for key in oldkeys if oldblocks[key] != newblocks[key]]
assert set(changed) == set(KEYS) and len(changed) == 6
unchanged = [key for key in oldkeys if key not in KEYS]
assert len(unchanged) == 38 and all(oldblocks[key] == newblocks[key] for key in unchanged)

def normalize_space(raw):
    return b' '.join(raw.split())

author_changes = []
for key in changed:
    before = oldblocks[key]
    after = newblocks[key]
    assert before.count(b'``') == after.count(b'``') == 1
    oldauthor, oldsuffix = before.split(b'``', 1)
    newauthor, newsuffix = after.split(b'``', 1)
    first_author = normalize_space(oldauthor).split(b',', 1)[0]
    expected_author = first_author + b' \\emph{et~al.},'
    assert normalize_space(newauthor) == expected_author
    assert normalize_space(oldsuffix) == normalize_space(newsuffix)
    author_changes.append({'key': key, 'reference_number_1based': oldkeys.index(key) + 1,
                           'old_author_prefix': oldauthor.decode('utf-8'),
                           'new_author_prefix': newauthor.decode('utf-8'),
                           'new_prefix_equals_preserved_first_author_then_etal': True,
                           'title_through_entry_end_equal_after_whitespace_normalization': True,
                           'line_wrapping_not_claimed_byte_identical': True,
                           'normalized_suffix_sha256': hashlib.sha256(normalize_space(oldsuffix)).hexdigest()})
for key in PRESERVED:
    assert key in unchanged and b'\\emph{et~al.}' not in newblocks[key]

result = {
    'schema': 'independent-scoped-bst-source-and-bbl-delta-review.v1',
    'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'method': 'AI full reading of both producer sources and complete two patches, plus one new stdlib byte/metadata/BBL delta checker; no producer, BST interpreter, BibTeX or compiler executed',
    'source_review': {
        'main_has_only_style_name_change_from_global_candidate': True,
        'three_line_guard_is_only_bst_byte_delta_from_preserved_standard_copy': True,
        'stack_semantics': 'Existing T=(nameptr==shown+1) AND (numnames>threshold) AND forced; six cite$ equalities OR to G; final AND leaves T AND G for existing if$, no residual stack item.',
        'fixed_six_key_allowlist_not_general_venue_classifier': True,
        'refs_byte_identical_to_adopted_1948': True,
        'six_current_venue_and_author_fields': venues,
        'original_clearpage_present': True,
        'only_control_key_precedes_first_ordinary_cite': True,
        'ordinary_main_citation_source_unchanged_from_global_candidate': True,
        'source_partial_failure_review': 'Parent-reported consumed first deriver exit1 at regex matching through first nested IEEE closing brace; full source shows draft/main/BST/patch creation before that assertion. Success continuation is a different preserved source and reads braced journal depth. No first deriver or continuation was rerun.',
        'original_failure_and_continuation_actual_runtime_not_independently_reexecuted': True,
        'parser_limit': 'Finalizer is sufficient for these six unescaped protected IEEE journal fields and ordinary unbraced personal author lists; it is not a complete generic BibTeX parser or transaction/replay mechanism.'
    },
    'bbl_delta': {
        'regular_reference_count': 44,
        'identical_order': oldkeys,
        'preamble_and_footer_exact_bytes_unchanged': True,
        'exactly_six_entry_bodies_changed': changed,
        'other_38_entry_bodies_exact_byte_unchanged': unchanged,
        'author_prefix_changes': author_changes,
        'three_requested_non_ieee_entries_exact_body_unchanged': list(PRESERVED),
        'no_control_bibitem': True,
        'not_numbered_43_or_45': True,
        'suffix_comparison': 'Whitespace-normalized TeX suffix from opening title quote to entry end; original physical line wrapping can differ.'
    },
    'scope_limitations': [
        'Official rule evidence and non-IEEE exception/access limitation inherit IEEE_AUTHOR_DISPLAY_REVIEW.md; no new web bibliography verification.',
        'The original six-key references have IEEE journal names in current metadata; this is not independent verification of DOI, publisher article versions, all bibliography entries or science.',
        'No PDF bytes were read, no page count measured, no PDF preview performed, no compiler executed by this reviewer. Parent compile/render observations are separate evidence.',
        'Scientific values, figures, PDFs and 34 complete dependency contents were not rehashed; producer whole-source binding remains separate.',
        'No manuscript, BST, refs, old report, HANDOFF or scientific file was modified; only this new addendum and its new source/receipt are written.',
        'The derived BST is a custom explicit display filter, not the unmodified standard IEEEtran BST.'
    ],
    'inputs': bindings,
}
with DEST.open('x', encoding='utf-8', newline='\n') as file:
    json.dump(result, file, ensure_ascii=False, indent=2)
    file.write('\n')
raw = DEST.read_bytes()
print(json.dumps({'report': str(DEST), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                  'references': len(newkeys), 'changed_entries': changed,
                  'unchanged_entries': len(unchanged), 'input_count': len(bindings)}, ensure_ascii=False))
