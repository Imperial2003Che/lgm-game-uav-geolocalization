"""Write this new adoption's bounded local input contract, not an execution release."""
from pathlib import Path
import json
import hashlib
import os

HERE = Path(__file__).resolve().parent
EX = HERE.parent
L = EX / 'external_efficiency_preparation' / 'newer_native_b1_lifecycle_v1'
W = L.parent / 'newer_native_b1_worker_v2'
R = EX / 'newer_native_b1_lifecycle_review_20260930_0927'


def d(path):
    before = path.stat()
    if before.st_size > 512 * 1024:
        raise RuntimeError('Oversize explicitly named local source/report')
    with path.open('rb') as f:
        raw = f.read(512 * 1024 + 1)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError('Input changed')
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


roles = {
    'lifecycle_manifest': L / 'SOURCE_MANIFEST.json',
    'worker_manifest': W / 'SOURCE_MANIFEST.json',
    'final_source_manifest': L / 'SOURCE_REVIEW_MANIFEST.json',
    'producer_delivery': L / 'DELIVERY.json',
    'pure_controls': L / 'source_controls_v1' / 'NEW_SOURCE_CONTROLS.json',
    'pure_controls_tool_receipt': L / 'source_controls_v1' / 'ACTUAL_TOOL_RECEIPT.json',
    'lifecycle_review': R / 'SOURCE_REVIEW.json',
    'lifecycle_delivery': R / 'DELIVERY.json',
    'lifecycle_input_table': R / 'INPUT_BINDINGS.json',
    'lifecycle_actual_tool_receipt': R / 'ACTUAL_STATIC_TOOL_RECEIPT.json',
    'worker_delta_review': EX / 'b1_worker_body_delta_review_20260930_0930' / 'DELTA_REVIEW.json',
    'worker_delta_delivery': EX / 'b1_worker_body_delta_review_20260930_0930' / 'DELIVERY.json',
    'scope_report': EX / 'b1_integration_scope_20260930_0912' / 'INTEGRATION_SCOPE.json',
    'scope_delivery': EX / 'b1_integration_scope_20260930_0912' / 'DELIVERY.json',
    'observation_seal': EX / 'heartbeat_final_observation_20260930_095757540' / 'ROOT_OBSERVATION_SEAL.json',
    'prior_cpu_control_root': EX / 'newer_native_process_execution_v2_20260930_0820' / 'ROOT_CURRENT_HOST_CONTROL_ADOPTION.json',
    'prior_cpu_control_finalization': EX / 'newer_native_process_execution_v2_20260930_0820' / 'ROOT_REPORT_FINALIZATION.json',
    'prior_cpu_finalization_review': EX / 'newer_native_process_v2_runtime_review_20260930_0826' / 'FINALIZATION_SCOPE_REVIEW.json',
}
if (L / 'ROOT_SOURCE_ADOPTION.json').exists():
    raise RuntimeError('Root output already exists')
value = {
    'schema': 'root-native-b1-source-adoption-inputs.v1',
    'inputs': {k: d(v) for k, v in roles.items()},
    'additional_descriptor_tables': ['producer_delivery', 'final_source_manifest', 'lifecycle_input_table'],
    'review_delivery_roles': ['worker_delta_delivery', 'scope_delivery'],
    'passed_review_roles': ['lifecycle_review', 'worker_delta_review', 'pure_controls'],
    'extra_source_bindings': [d(R / 'review_lifecycle_static.py'), d(Path(__file__))],
    'native_closed_functions': ['_load_process_helper', '_read_runtime_spec', '_wait_control_file',
        '_final_admission_before_ack', '_confirm_controller_live', '_worker_validate_ack_live',
        '_cleanup_references', '_run_native_slot', '_worker_pre_science_handshake',
        'run_reference', 'admit_reference', 'main'],
    'os_snapshot_is_not_future_permission': True,
    'prior_cpu_control_scope': 'Prior ordinary Python CPU control is inherited only jointly with its separate root report finalization and independent scope review. Its original root writer first exit1 is preserved. Neither old CPU cases nor old273/1877/75 suites are rerun or treated as scientific/native evidence.',
    't6_output': r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal',
    'limitations': [
        'Closed source adoption only. Original and new science/API/import/spawn/handshake/admission/ranking/CLI paths FIRST unconditionally reject. Final preACK issuer and independent immutable execution root are absent; a separately reviewed new version is required, never alter these sealed versions to open their gates.',
        'Frozen scientific worker body/PINS/strict original encode_seed and loader/CAMP395-DAC402/DAC before-after scope/raw canonical request/original prepared seal/sole memory batch16-to-1 derivative are inherited unchanged. The old payload seal is not a valid derived seal. Narrow91 body review and whole352 static review are separate.',
        'Producer ran 50 new stdlib synthetic metadata/closed-gate controls once, tool0d7034 exit0. It imported candidate stdlib definitions only. No original package/binder/helper/science/API/subprocess/native/old fixture or old suite ran. source_controls_v1 is consumed; no replay. Root and independent agents did not rerun it.',
        'Corrections are pre-execution static findings, not new native/scientific failures. Initial sources/full diffs and already published no-controls-yet manifests stay historical and are joined with the later actual controls report. First inline input-preparation attempt bbb4d0 failed on guessed receipt filename before writing the contract; it is not root adoption or scientific execution.',
        'All reviews are AI tool reading, not human review. Whole static reviewer authored prior helper_v2 but not this new lifecycle/worker/evidence. No new independent API/runtime proof is attributed to that review.',
        'Native scientific venv/site/startup/redirector two-PID topology/predeclared actual base image and full commands/history of startup imports remain unvalidated. Source sys.modules/current identity assertions do not prove historical startup exclusion.',
        'Actual predecessor independent exits, current boot/state/source/release TTL, empty successful GPU query/integer26GiB available commit/shared continuously retained byte locks and six released fresh method-seed workers remain required. Completed state or absence never substitutes actual held exit0.',
        'Saved record associations and actual SHA/size of four future designated artifacts are candidate consistency only, not trustworthy external execution or original candidate/NPY/ledger/strict loader semantic validation. No actual CompletedInputs, ready/ACK/B1 run or held process evidence is produced here.',
        'Fresh complete gallery/ranking/parity/raw-image-to-full-ranking timing/fullonlineCLIP and original T6/five-layer/extra DAC dependencies remain unfinished. No scientific number, plot, manuscript, Overleaf or old archive changed. All negative findings, metric/seed/SD/CI/resampling/evidence-path and historical SHA-edge limits remain.',
        'Nt class60/current Toolhelp ancestry/unobserved descendants/CreateNew/fsync/read-sharing cooperative scope remain. Reference or stream cleanup is not exit proof or shared-lock release permission; controller cannot prove its own exit.',
        '09:57 London OS/GPU snapshot: unchanged boot and ordinary Visio, 25 compute rows/original exclusive false. PID17896 is now WeChatAppEx with distinct parent/full command/creation, not prior CPU outer, whose exit remains unknown. No app close/attachment, parameter reduction, paging/cloud/reset/credit actions are authorized.',
        'Adoption rechecks file bytes only, not new OS/GPU/available-commit admission. No science release/intent/native training probe/COM/cleanup/lock/state mutation. Keep automatic follow-up until all actual experiments/final editable figures/Visio/manuscript/final Overleaf/submission advice are delivered.',
    ],
}
raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
with (HERE / 'INPUT_CONTRACT.json').open('xb') as f:
    f.write(raw); f.flush(); os.fsync(f.fileno())
print(json.dumps(d(HERE / 'INPUT_CONTRACT.json'), ensure_ascii=False))
