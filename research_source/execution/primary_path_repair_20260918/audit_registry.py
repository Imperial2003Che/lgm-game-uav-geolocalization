"""Read-only diagnosis of the failed 2026-09-18 primary admission."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
from project_paths import FrozenProjectPath, LOGICAL, PHYSICAL, root_identity

HERE = Path(__file__).resolve().parent
RUNNER = LOGICAL / 'lgm_game_pytorch/experiments/run_frozen_formal_matrix.py'
LEDGER = LOGICAL / 'lgm_game_pytorch/runs/frozen_formal_matrix_ledger.json'
def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    assert sha(RUNNER) == 'f251e5088b306ddec4769fab06799008d06194bc459282f2432ac3238f4ba59f'
    spec = importlib.util.spec_from_file_location('audit_frozen_runner', RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    ledger_raw = LEDGER.read_bytes()
    ledger = json.loads(ledger_raw)
    def collect(root):
        main_rows = module.main_run_specs(root, module.DATASETS, module.MAIN_VARIANTS, module.MAIN_SEEDS)
        sensitivity = module.sensitivity_run_specs(root, module.DATASETS)
        module.validate_registry(main_rows, sensitivity)
        rows = main_rows + sensitivity
        data = module.dataset_specs(root, module.Path(r'C:\项目\IMTMN\datasets\University-1652'),
                                   module.Path(r'C:\项目\IMTMN\datasets\SUES-200'))
        inputs = {name: {'data_root': str(v.data_root), 'evidence_path': str(v.evidence),
                        'evidence_sha256': v.evidence_sha256} for name, v in data.items()}
        return rows, module.registry_sha256(rows), data, inputs
    original, physical_hash, _, physical_inputs = collect(PHYSICAL)
    module.Path = FrozenProjectPath
    restored, restored_hash, data, restored_inputs = collect(FrozenProjectPath(LOGICAL))
    assert len(restored) == 42 and physical_hash != ledger['registered_registry_sha256']
    assert restored_hash == ledger['registered_registry_sha256']
    assert restored_inputs == ledger['frozen_inputs']
    for before, after in zip(original, restored):
        for field in ('family', 'dataset', 'variant', 'seed', 'backbone', 'embed_dim'):
            assert getattr(before, field) == getattr(after, field)
        assert Path(before.run_dir).resolve() == Path(after.run_dir).resolve()
        assert Path(before.evaluation_dir).resolve() == Path(after.evaluation_dir).resolve()
    completed = []
    for row in restored:
        issues = module.training_completion_issues(row, data[row.dataset], ledger['formal_script_sha256'])
        if not issues: completed.append(row.identifier)
    assert len(completed) == 13
    assert LEDGER.read_bytes() == ledger_raw
    assert not any(n.split('.')[0] in {'torch', 'numpy', 'PIL', 'cv2'} for n in sys.modules)
    payload = {'scope': 'Actual original runner, all 42 specifications and completion audits; no science imports or writes to experiments',
               'root_identity': root_identity(), 'ledger_sha256': sha(LEDGER),
               'registered_hash': ledger['registered_registry_sha256'], 'physical_path_hash': physical_hash,
               'restored_hash': restored_hash, 'physical_inputs': physical_inputs,
               'restored_inputs': restored_inputs, 'completed_fit_count': len(completed), 'completed_fit_ids': completed,
               'all_nonpath_spec_fields_identical': True, 'ledger_unchanged': True}
    output = HERE / 'ACTUAL_REGISTRY_AUDIT.json'
    with output.open('x', encoding='utf-8') as stream: json.dump(payload, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'report': str(output), 'sha256': sha(output), 'completed': len(completed),
                      'registered_hash_restored': True, 'frozen_inputs_restored': True}))

if __name__ == '__main__': main()
