"""Seal existing bounded-review artifacts without rerunning checks or raw NPZ reads."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent


def record(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def save(name, value):
    with (HERE / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


main_source = HERE / 'review_post.py'
annex_source = HERE / 'review_adopted_aggregate_inputs_v2.py'
main_report = HERE / 'REVIEW.json'
annex_report = HERE / 'adopted_inputs_v2/RECONCILIATION.json'
assert record(main_source)['sha256'] == 'bb510281e547182ddc675d8ab34d7905625bb3ed4d7f540416b0cad5a7c36521'
assert record(main_report)['sha256'] == 'e350ca764a7b6a053afbab3062eee6412306685ffeb2c5b9185578896ff451bc'
assert record(annex_source)['sha256'] == '70d4c1cd808c3a21ea7d58667468aa2bc072a39ff1ca24507a841ce4a1aa4512'
assert record(annex_report)['sha256'] == '43b6ed0ec2a2dd655b1c8289d4dbe5ff0071523705a3ee224cf9117064999410'
review = json.loads(main_report.read_bytes())
annex = json.loads(annex_report.read_bytes())
capture = json.loads((HERE / 'a1/CAPTURE.json').read_bytes())
assert review['passed_with_stated_limits'] is True and annex['passed'] is True
assert review['query']['source_authority'] == annex['prior_official_input_authority_mandatory_gate']
assert annex['aggregate_SUES_Full_input_adoption_pending'] is False
with (HERE / 'FULL_NEW_REVIEW_SOURCES.patch').open('x', encoding='utf-8', newline='\n') as stream:
    for source in (HERE / 'capture_once.py', main_source, HERE / 'review_adopted_aggregate_inputs.py',
                   HERE / 'prepare_annex_v2.py', annex_source, Path(__file__).resolve()):
        stream.writelines(difflib.unified_diff([], source.read_text(encoding='utf-8').splitlines(True),
                          fromfile='/dev/null', tofile=source.name))
# Directly hash only small source/report/log/annex/static files, not a1 raw scientific files.
files = [p for p in HERE.rglob('*') if p.is_file() and 'a1' not in p.relative_to(HERE).parts]
sealed = [record(p) for p in sorted(files, key=lambda p: str(p).casefold())]
for entry in review['metadata_chain_additions']:
    path = Path(entry['snapshot'])
    item = record(path)
    assert item['sha256'] == entry['sha256'] and item['bytes'] == entry['bytes']
    sealed.append(item)
save('SOURCE_AND_SMALL_ARTIFACT_MANIFEST.json', {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'actual_small_file_bindings': sealed, 'raw_snapshot_bindings_inherited_without_rehash': capture['bindings'],
    'raw_capture': record(HERE / 'a1/CAPTURE.json'),
    'note': 'This sealer does not rerun main/annex audit, or reread any NPZ/checkpoint/cache/image bytes.'})
save('DELIVERY.json', {'schema': 'joint-post-robustness-review-delivery.v1',
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'passed_with_stated_limits': True, 'root_adoption_pending': True,
    'main_source': record(main_source), 'main_review': record(main_report),
    'annex_source': record(annex_source), 'annex_review': record(annex_report),
    'capture': record(HERE / 'a1/CAPTURE.json'),
    'manifest': record(HERE / 'SOURCE_AND_SMALL_ARTIFACT_MANIFEST.json'),
    'readme': record(HERE / 'README.md'),
    'static_review': record(HERE / 'static_review/POST_SOURCE_STATIC_REVIEW.json'),
    'full_new_source_diff': record(HERE / 'FULL_NEW_REVIEW_SOURCES.patch'),
    'annex_revision_diff': record(HERE / 'ANNEX_V2_FROM_REJECTED_V1.patch'),
    'preparation_rejection_record': record(HERE / 'ANNEX_PREPARATION_REJECTION.json'),
    'execution': {'main': {'attempts': 1, 'observed_shell_exit_code': 0,
        'stdout': record(HERE / 'first_review.stdout.log'), 'stderr': record(HERE / 'first_review.stderr.log')},
        'annex_v1': {'attempts': 1, 'observed_shell_exit_code': 1,
        'stdout': record(HERE / 'first_annex.stdout.log'), 'stderr': record(HERE / 'first_annex.stderr.log')},
        'annex_v2': {'attempts': 1, 'observed_shell_exit_code': 0,
        'stdout': record(HERE / 'v2_annex.stdout.log'), 'stderr': record(HERE / 'v2_annex.stderr.log')},
        'note': 'Audit shell exit observations; not scientific child/launcher dual-handle proof.'},
    'scope': {'aggregate_source_rows': 3960, 'adopted_runs': 4, 'adopted_clean_task_records': 22,
        'adopted_corrupted_task_records': 660, 'query': review['query']},
    'limits': annex['limits']})
print(json.dumps({'delivery': record(HERE / 'DELIVERY.json'),
                  'manifest': record(HERE / 'SOURCE_AND_SMALL_ARTIFACT_MANIFEST.json')}))
