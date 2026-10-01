"""Seal this completed offline derivation's small files; no recovery execution."""
from pathlib import Path
import datetime as dt
import hashlib
import json

HERE = Path(__file__).absolute().parent
NEW = HERE.parent / 't6_recovery_preparation_20260930_0405'


def bind(path):
    path = Path(path)
    assert path.suffix.lower() not in {'.pt', '.pth', '.npy', '.npz', '.zip', '.png', '.jpg'}
    assert path.stat().st_size < 2 * 1024**2
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def write(name, value):
    with (HERE / name).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


assert bind(HERE / 'DERIVATION.json')['sha256'] == '089b35de1a5e5d637d10e9caf1b1e0912aa992c7845e14b75ddb5397d9debaad'
assert bind(NEW / 'SOURCE_MANIFEST.json')['sha256'] == '6810affc21226b6e6c1bdea585b1fedbc6992ea7264df1b6e78eb0a0b08daca0'
assert bind(NEW / 'RECOVERY_CONTRACT.json')['sha256'] == '7e10d045a396c53a9ffb7ec0996e38f2a88101413cbf5655548a6f80edcb44ff'
paths = [HERE / name for name in ('derive_new_boot_preparation.py', 'README.md', 'DERIVATION.json',
    'CONTRACT_SEMANTIC_DIFF.json', 'RECOVERY_CONTRACT.patch', 'seal_delivery.py')]
paths += [NEW / name for name in ('pipeline_recovery_candidate.py', 'start_pipeline_recovery_candidate.ps1',
    'captured_pipeline_status.json', 'pipeline_seed.json', 'RECOVERY_CONTRACT.json', 'SOURCE_MANIFEST.json')]
write('DELIVERY.json', {
    'schema': 't6-new-boot-source-derivation-delivery.v1',
    'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'scope': 'Exact four source copies and one separately current-boot contract; source preparation for independent/root review only.',
    'artifacts': [bind(path) for path in paths],
    'derivation_command': [r'C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe', '-B', '-X', 'utf8',
        str(HERE / 'derive_new_boot_preparation.py'), 'c28fee27fa4036b199caa50daeee7813723e21c1edf7e854322d4e911c040b59'],
    'derivation_execution_observed': {'tool': 'exec_command', 'reported_exit_code': 0,
        'basis': 'Actual tool return from the single offline derivation invocation; no claim of separately held launcher/interpreter handles.'},
    'inherited_input_count': 107, 'added_input_count': 7, 'new_input_count': 114,
    'complete_semantic_changes': 40,
    'execution_released': False, 'root_source_adoption_created_by_producer': False,
    'candidate_imported_or_executed': False, 'old_generator_replayed': False,
    'old_science_or_control_suites_rerun': False,
    'native_probe_or_com_or_lock_or_live_state_mutation': False,
    'scientific_result_claimed': False,
    'limitations': ['Saved observations are not future admission.',
        'The unchanged guardian gates only its own attempt; future root admission must check all three retained attempt paths.',
        'No uncaptured process exit or Visio task ownership is inferred. Prior source roots remain unchanged and do not authorize the new manifest.',
        'Source adoption, execution release and scientific result adoption remain separate.']
})
print(json.dumps(bind(HERE / 'DELIVERY.json'), ensure_ascii=False))
