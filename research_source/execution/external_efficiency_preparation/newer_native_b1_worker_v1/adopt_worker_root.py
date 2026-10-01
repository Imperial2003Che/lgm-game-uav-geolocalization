"""Adopt reviewed source text and small bindings, without importing the worker."""
from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json

W = Path(__file__).resolve().parent
E = W.parents[1]
R = E / 'newer_native_b1_worker_review_20260930_0304'
O = E / 'heartbeat_observation_20260930_030407230'
bound = {}
def pin(path):
    path = Path(path)
    assert path.is_absolute() and path.stat().st_size <= 1024 * 1024
    assert path.suffix.lower() in ('.py', '.txt', '.json', '.md', '.patch', '.ps1', '.log', '.jsonl', '.lock')
    raw = path.read_bytes()
    item = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    if str(path) in bound:
        assert bound[str(path)] == item
    bound[str(path)] = item
    return item
def verify(item):
    assert pin(item['path']) == item, item['path']
def read(path):
    return json.loads(Path(path).read_bytes())
def pinned(path, sha):
    assert pin(path)['sha256'] == sha, str(path)
    return read(path)

manifest = pinned(W / 'SOURCE_MANIFEST.json', '9f5e40ed7ddd3f35ce48247d37dcb00923f9dae6955b2c89d96261c296460bb3')
review = pinned(R / 'SOURCE_REVIEW.json', '5f9cfab88d9f05ab8a1047ec7756c1c80f676d5fe7fe1e37b83f6ae5377ad2c7')
delivery = pinned(R / 'DELIVERY.json', 'd3ce8ed1c606a42436b33c2ac64608131a8c183ee872a544f7555a77c43d15bf')
observation = pinned(O / 'ROOT_OBSERVATION_SEAL.json', 'ef182e57ae99abda18009a3aac38eb1c5e8b4f57e2ccf4f096a9de6f00cc9f6d')
for item in manifest['files'] + manifest['original_source_references'] + [manifest['prior_B1_root_adoption']]:
    verify(item)
for item in delivery['review_artifacts'] + [delivery['report'], delivery['source'], delivery['producer_manifest']]:
    verify(item)
assert manifest['current_source'] == review['current_source'] == delivery['source'] == pin(W / 'reference_worker.py')
assert manifest['current_source']['sha256'] == 'eed9b25b1204edbcf5172ea2fb24e272b7ff39103f98448e554a3dae779b7f46'
assert review['source_review_passed'] is True and review['execution_approved'] is False
assert review['runtime_body_executed_or_validated'] is False and review['unresolved_source_findings'] == []
checklist = read(R / 'INPUT_CHECKLIST.json')
for item in checklist['source_bindings']:
    verify(item)
static = read(R / 'STATIC_BINDING_REVIEW.json')
for item in static['additional_sources_read']:
    verify(item)
blocks = read(W / 'ORIGINAL_CALL_BLOCKS.json')
for item in blocks['runtime_prefix_metadata']:
    verify(item['prepared'])
    prepared = read(item['prepared']['path'])
    assert prepared['runtime']['prefix'] == item['runtime_prefix']
    assert prepared['python'] == item['python']

old = (W / 'PRE_ROOT_REVIEW_reference_worker.py.txt').read_text(encoding='utf-8')
new = (W / 'reference_worker.py').read_text(encoding='utf-8')
full = ''.join(difflib.unified_diff([], new.splitlines(True), fromfile='/dev/null', tofile='reference_worker.py'))
amendment = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='PRE_ROOT_REVIEW_reference_worker.py.txt', tofile='reference_worker.py'))
assert full == (W / 'FULL_NEW_SOURCE.patch').read_text(encoding='utf-8')
assert amendment == (W / 'ROOT_REVIEW_REVISION.patch').read_text(encoding='utf-8')
initial_checks = read(W / 'NEW_STDLIB_CHECKS.json')
delta_checks = read(W / 'ROOT_REVISION_STDLIB_CHECKS.json')
assert len(initial_checks['checks']) == 29 and initial_checks['passed'] is True
assert initial_checks['source']['sha256'] == pin(W / 'PRE_ROOT_REVIEW_reference_worker.py.txt')['sha256']
assert len(delta_checks['checks']) == 5 and delta_checks['passed'] is True
assert delta_checks['source'] == manifest['current_source']
assert not (W / 'runs').exists()
assert not (E / 'camp_independent_evaluation_v3' / 'b1_reference_runs').exists()
assert not (E / 'dac_independent_evaluation_v2' / 'b1_reference_runs').exists()

state_and_logs = [x for x in observation['bindings'] if
    (Path(x['path']).parent == E and Path(x['path']).name.endswith('status.json')) or
    Path(x['path']).suffix in ('.log', '.jsonl')]
assert len(state_and_logs) == 16
for item in state_and_logs:
    verify(item)
carrier = next(x for x in observation['bindings'] if Path(x['path']).name == 'latest_baseline_gpu.lock')
verify(carrier)
assert Path(carrier['path']).read_bytes() == b'0'
absent = [E / 't6_recovery_preparation_20260929_1548' / 'runtime_attempt',
          E / 't6_recovery_preparation_20260930_0104' / 'runtime_attempt',
          E.parent / 'transfer_native_visio_candidate_20260930_0104' / 'runtime_attempt_v1',
          Path('C:/项目/LGM-GAME-Partner-Delivery-20260724/lgm_game_pytorch/analysis/transactions_t6_formal')]
assert all(not x.exists() for x in absent)
source = pin(Path(__file__).resolve())
report = {
    'schema': 'newer-native-b1-worker-root-source-adoption.v1',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'Closed original-encoder worker source body, exact original-source correspondence, producer new bounded checks and independent AI static review. No runnable lifecycle integration or scientific execution.',
    'source_adopted': True, 'execution_released': False, 'scientific_execution': False,
    'runnable_worker_validated': False, 'full_t6_complete': False, 'new_figures': 0,
    'manuscript_result': False, 'root_source': source,
    'worker': manifest['current_source'], 'producer_manifest': pin(W / 'SOURCE_MANIFEST.json'),
    'independent_review': pin(R / 'SOURCE_REVIEW.json'),
    'unique_bindings': len(bound), 'bindings': list(bound.values()),
    'root_review': {
        'full_initial_and_final_worker_source_read': True,
        'full_root_amendment_and_complete_new_source_difference_verified': True,
        'producer_checker_and_sealer_sources_read': True,
        'independent_both_sources_and_reports_read': True,
        'original_scientific_read_scope': 'Full original encode_seed/read_prepared/strict loader blocks, relevant stdlib binder and B1 contract, not all historical scientific sources or artifacts.',
        'resolved_findings': ['JSON-type-exact sole batch derivation', 'Actual control size bound before content read'],
        'producer_controls': '29 on preserved initial source plus 5 affected new checks on final source; reports read and bound, not rerun.',
        'review_kind': 'AI-agent tool-text/source review; no external human reviewer',
    },
    'current_snapshot': {
        'root_observation': pin(O / 'ROOT_OBSERVATION_SEAL.json'),
        'state_log_files_rechecked': 16, 'carrier_ascii0_unchanged': True,
        'gpu_rows_from_0304_snapshot': 26, 'existing_unconfirmed_visio_from_0304_snapshot': True,
        'snapshot_is_execution_admission': False, 'absence_paths': list(map(str, absent)),
    },
    'remaining': review['remaining_execution_obligations'] + [
        'Six real fresh CAMP/DAC seed workers after actual earlier layers and DAC completion.',
        'Independent immutable result admission with externally retained handles and closed streams.',
        'Fresh full-gallery re-encoding, original-image-to-full-ranking timing/parity, full-dataset online CLIP accuracy.',
        'Original pipeline T6 and all other frozen dependencies remain required; existing public refusal gates unchanged.',
    ],
    'no_old_scientific_or_control_suite_rerun': True,
    'no_old_weights_NPZ_cache_image_or_partner_zip_read': True,
    'no_original_binder_or_encoder_or_science_import_or_call': True,
}
out = W / 'ROOT_SOURCE_ADOPTION.json'
with out.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(path=str(out), bytes=out.stat().st_size, sha256=hashlib.sha256(out.read_bytes()).hexdigest(), unique_bindings=report['unique_bindings']), ensure_ascii=True))
