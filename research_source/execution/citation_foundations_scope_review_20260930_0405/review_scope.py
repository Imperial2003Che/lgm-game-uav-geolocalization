"""Independent bounded local citation-scope review; no web, producer or science execution."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import re

HERE = Path(__file__).absolute().parent
EX = HERE.parent
PRODUCER = EX / 'citation_foundations_review_20260930_0405'
MANUSCRIPT = EX.parent / 'manuscript_evidence_revision_20260930_0202' / 'manuscript'
PINS = {
    'FOUNDATION_CITATION_REVIEW.json': '1fc0add81a24d08395cfe99ba8aa653e5b1fdd0842c55b086ecc63d89be4a1ca',
    'DELIVERY.json': '15317cd56357905614f3497895890b710b2a98ed7f57a500e9788e227403eb96',
}
bindings = {}
checks = []


def read(path):
    path = Path(path)
    assert path.suffix.lower() in {'.json', '.md', '.bib', '.tex', '.py'}
    assert path.stat().st_size < 150000
    data = path.read_bytes()
    desc = {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if path.parent == PRODUCER and path.name in PINS:
        assert desc['sha256'] == PINS[path.name]
    bindings[str(path)] = desc
    return data.decode('utf-8-sig')


def require(value, message):
    assert value, message
    checks.append(message)


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip()


def parse_fields(raw):
    fields = {}
    for match in re.finditer(r'(?m)^\s*(\w+)\s*=\s*\{', raw):
        start, depth, index = match.end(), 1, match.end()
        while depth:
            char = raw[index]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
            index += 1
        fields[match.group(1).lower()] = normalize(raw[start:index - 1])
    return fields


report = json.loads(read(PRODUCER / 'FOUNDATION_CITATION_REVIEW.json'))
access = json.loads(read(PRODUCER / 'PRIMARY_ACCESS.json'))
decision = json.loads(read(PRODUCER / 'CORRECTION_DECISION.json'))
delivery = json.loads(read(PRODUCER / 'DELIVERY.json'))
read(PRODUCER / 'REVIEW.md')
bib = read(MANUSCRIPT / 'refs.bib')
main = read(MANUSCRIPT / 'main.tex')
supp = read(MANUSCRIPT / 'supplementary.tex')
read(Path(__file__).absolute())
for desc in delivery['files']:
    if desc['path'] in bindings:
        require(bindings[desc['path']] == desc, 'Producer file binding: ' + Path(desc['path']).name)
for desc in report['local_inputs']:
    require(bindings[desc['path']] == desc, 'Local unchanged input: ' + Path(desc['path']).name)
keys = ['clip2021', 'csls2018', 'rerank2017', 'aqe2007', 'resnet2016', 'dropout2014',
        'adamw2019', 'sgdr2017', 'mixedprecision2018', 'efron1979', 'mcnemar1947', 'holm1979', 'commoncorruptions2019']
require(report['scope_keys'] == keys and report['scope_count'] == 13, 'Exact requested 13-key scope')
entries = {entry['key']: entry for entry in report['entries']}
require(list(entries) == keys and len(entries) == len(report['entries']), 'Exactly 13 unique detailed entries')
starts = list(re.finditer(r'@\w+\s*\{\s*([^,]+),', bib))
raw_entries = {m.group(1).strip(): bib[m.end():starts[i+1].start() if i+1 < len(starts) else len(bib)]
               for i, m in enumerate(starts)}
source_ids = {x['id'] for x in access['sources']}
local_field_count = 0
for key in keys:
    actual = parse_fields(raw_entries[key])
    for field, record in entries[key]['fields'].items():
        require(actual.get(field) == record['local_value'], 'Saved local field: ' + key + '/' + field)
        local_field_count += 1
    require(set(entries[key]['sources']) <= source_ids, 'All source locators resolve: ' + key)
    require(key in main and key not in supp, 'Actual main citation occurrence and no supplementary direct occurrence: ' + key)
    require(entries[key]['confirmed_correction_required'] is False, 'No proven metadata correction: ' + key)
require(report['all_bibliography_verified'] is False and report['all_fields_verified'] is False,
        'Partial scope remains explicit')
require(report['scientific_validation'] is False and report['manuscript_modified'] is False,
        'No scientific or manuscript-edit adoption claimed')
require(decision['confirmed_bibtex_corrections'] == [] and decision['corrected_snippets_or_diff_created'] is False,
        'No unsupported bibliography patch proposed')
require(entries['aqe2007']['fields']['pages']['status'] == 'unresolved_primary_evidence', 'AQE pages unresolved')
require(entries['efron1979']['fields']['doi']['status'] == 'unresolved_primary_evidence', 'Efron DOI unresolved')
require(entries['efron1979']['fields']['author']['status'] == 'unresolved_primary_evidence', 'Efron expanded name unresolved')
require(entries['holm1979']['fields']['doi']['status'] == 'unresolved_primary_evidence', 'Holm DOI unresolved')
source_map = {x['id']: x for x in access['sources']}
require(source_map['csls_conference']['access'] == 'official_index_only_direct_restricted'
        and source_map['csls_arxiv']['access'] == 'direct_success', 'Conference/index and arXiv/direct access kept distinct')
require(source_map['rerank_ieee']['access'] == 'direct_restricted'
        and source_map['rerank_anu']['access'] == 'author_institution_index_only', 'Rerank IEEE direct restriction remains explicit')
require('Current master was read, not a pinned 2019 commit' in source_map['corruptions_code']['facts'],
        'ImageNet-C code chronology limitation retained')
main_lines = main.splitlines()
targeted_lines = [210, 316, 317, 357, 358, 359, 360, 531, 532, 534, 536, 537,
                  568, 569, 570, 571, 572, 573, 583, 584, 585, 586, 652, 653, 654, 655, 656, 657]
findings = [
    {'topic': 'CSLS author order', 'decision': 'Keep the selected conference citation order on the producer evidence; no automatic swap to the differently ordered arXiv record.',
     'limit': 'The conference PDF author block was indexed evidence in the producer audit. This independent review did not browse it or upgrade it to a direct read.'},
    {'topic': 'Rerank pagination', 'decision': 'The IEEE 3652--3661 and CVF 1318--1327 ranges are version-specific evidence, not a proved typo. No page replacement is justified.',
     'limit': 'IEEE page and DOI were corroborated by indexed author-institution evidence; direct IEEE access did not succeed.'},
    {'topic': 'Unresolved metadata', 'decision': 'Retain unresolved AQE pages, Efron DOI/expanded given name, Holm DOI and ICLR ordinal/publisher-role fields as unresolved.',
     'limit': 'No error can be inferred just from inaccessible metadata; no new DOI or page range should be invented.'},
    {'topic': 'McNemar', 'decision': 'The specific exact-binomial formula needs a dedicated source check if strengthened in a future open manuscript revision.',
     'limit': 'The obtained abstract supports correlated-proportions attribution only. This is not proof of an incorrect test or experiment, and does not validate query or training uncertainty.'},
    {'topic': 'ImageNet-C', 'decision': 'An optional future clarification that illumination direction and severity levels are adapted is supported by the current author-code record and local reduced-brightness prose.',
     'limit': 'Interpret "original author function" in the producer report as the currently read author-maintained master only; the 2019 implementation was not pinned. No canonical ImageNet-C equivalence or need to change the frozen transform follows.'},
    {'topic': 'Other foundation citations', 'decision': 'Bounded method attribution and version years are consistent with the saved audit; no numeric hyperparameter or scientific outcome is thereby accepted.',
     'limit': 'CLIP precision/preprocessing, ResNet implementation dimensions, dropout probability, optimizer/AMP details, bootstrap resampling and Holm families remain outside this review.'},
    {'topic': 'Line locators', 'decision': 'McNemar test text occurs at main.tex 570 and its citation at 571; the report range 569--570 includes preceding bootstrap context. Holm citation is also at 571.',
     'limit': 'This minor locator precision is recorded here; it does not change claim interpretation or require modifying the sealed manuscript or producer report.'},
]
output = {
    'schema': 'lgm.foundation-citation-independent-scope-review.v1',
    'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'reviewer': 'Independent AI agent /root/boot_contract_0405; no external human reviewer.',
    'accepted_for_bounded_scope_only': True,
    'method': 'Complete local reading of the producer final audit/access/decision/README/delivery, local refs.bib and targeted actual TeX citation contexts; independent stored-field and binding checks. No producer import/execution, web browsing, manuscript change or science validation.',
    'scope_keys': keys, 'saved_local_field_count_checked': local_field_count,
    'checks': checks, 'findings': findings,
    'targeted_actual_main_lines': [{'line': n, 'text': main_lines[n-1]} for n in targeted_lines],
    'bindings': list(bindings.values()),
    'confirmed_bibtex_corrections': [], 'manuscript_modified': False,
    'independently_browsed_web_sources': False, 'all_bibliography_verified': False,
    'scientific_validation': False, 'root_adoption_created': False,
}
with (HERE / 'SCOPE_REVIEW.json').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
data = (HERE / 'SCOPE_REVIEW.json').read_bytes()
print(json.dumps({'path': str(HERE / 'SCOPE_REVIEW.json'), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                  'checks': len(checks), 'saved_fields': local_field_count}, ensure_ascii=False))
