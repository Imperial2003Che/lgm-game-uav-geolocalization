"""Read-only, standard-library capture for the seven queued pipeline paths.

Does not import any experiment module or read scientific tensor/array payloads.
Writes only its own new review report; refuses to overwrite a prior report.
"""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import os
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
LOGICAL = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
PHYSICAL = Path(r'C:\项目\LGM\02_代码与实验\正式实验工程')
PACKAGE = LOGICAL / 'lgm_game_pytorch'
EXP = PACKAGE / 'experiments'

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def record(p):
    result = {'path': str(p), 'exists': p.exists()}
    if p.is_file():
        result.update(bytes=p.stat().st_size, sha256=sha(p))
    return result

names = [
    'aggregate_frozen_formal_results.py', 'plot_frozen_formal_results.py',
    'run_transactions_t3_transfer_matrix.py', 'run_frozen_robustness_matrix.py',
    'aggregate_formal_robustness.py', 'run_transactions_query_analysis.py',
    'run_transactions_formal_efficiency.py',
]
dependencies = [
    EXP / 'run_frozen_formal_matrix.py', EXP / 'run_cross_dataset_evaluation.py',
    EXP / 'formal_robustness_common.py', EXP / 'run_image_level_robustness.py',
    PACKAGE / 'lgm_game_pytorch' / 'formal_retrieval.py',
]
pipeline = read(EXECUTION / 'pipeline_status.json')
job_records = []
for name in names:
    path = EXP / name
    tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    matches = [job for job in pipeline['jobs'] if Path(job['command'][1]).name == name]
    assert len(matches) == 1
    job = matches[0]
    job_records.append({
        'id': job['id'], 'status_at_capture': job['status'],
        'source': record(path), 'resolved_source': str(path.resolve(strict=True)),
        'same_file_after_resolve': os.path.samefile(path, path.resolve(strict=True)),
        'matches_queued_entrypoint_sha256': sha(path) == job['entrypoint_sha256'],
        'command': job['command'], 'ast_parsed': True,
        'top_level_imports': [ast.unparse(node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))],
    })

state_paths = [
    PACKAGE / 'evaluations' / 'transactions_t3_transfer' / 'transactions_t3_ledger.json',
    PACKAGE / 'runs' / 'frozen_robustness_matrix_ledger.json',
    PACKAGE / 'results' / 'formal_robustness_aggregate' / 'aggregation_run_config.json',
    PACKAGE / 'analysis' / 'transactions_t4_t5' / 'transactions_query_analysis_config.json',
    PACKAGE / 'analysis' / 'transactions_t4_t5' / 'transactions_query_analysis_manifest.json',
    PACKAGE / 'analysis' / 'transactions_t6_formal' / 'transactions_t6_formal_config.json',
    PACKAGE / 'analysis' / 'transactions_t6_formal' / 'transactions_t6_formal_manifest.json',
]

# Exact path normalization expressions used by the unwrapped primary runner's
# completion validator, which T3 and robustness call without reinitializing the
# primary absolute-path registry. This is not the full completion validator.
sample = PACKAGE / 'runs' / 'formal_main' / 'university1652' / 'visual' / 'seed_1' / 'run_config.json'
config = read(sample)
immutable = config['immutable_config']
descriptor = immutable['evidence_caches'][0]
expected_evidence = (PHYSICAL / 'lgm_game_pytorch' / 'evidence_cache' / 'university1652_clip_image_evidence.npz').resolve(strict=True)
expected_data = Path(r'C:\项目\IMTMN\datasets\University-1652').resolve(strict=True)
path_expressions = {
    'sample': record(sample),
    'recorded_cache_path': descriptor['path'],
    'resolved_recorded_cache_path': str(Path(descriptor['path']).resolve()),
    'dataset_spec_cache_path': str(expected_evidence),
    'cache_paths_equal_after_original_normalization': Path(descriptor['path']).resolve() == expected_evidence,
    'cache_paths_samefile': os.path.samefile(Path(descriptor['path']), expected_evidence),
    'recorded_data_path': immutable['data_root'],
    'data_paths_equal_after_original_normalization': Path(immutable['data_root']).resolve() == expected_data,
}

aggregate_path = PACKAGE / 'results' / 'formal_matrix_aggregate' / 'aggregate_manifest.json'
aggregate = read(aggregate_path) if aggregate_path.is_file() else {}
aggregate_names = [r.get('path') for r in aggregate.get('output_artifacts', [])]
plot_default = (EXP / 'plot_frozen_formal_results.py').resolve().parents[2] / 'lgm_game_pytorch' / 'results' / 'formal_matrix_aggregate'
report = {
    'schema': 'lgm-pipeline-path-readonly-review.v1',
    'captured_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'Seven queued pipeline entrypoints and direct path/provenance helpers; source and small JSON metadata only.',
    'root': {'logical': str(LOGICAL), 'physical': str(PHYSICAL), 'resolved': str(LOGICAL.resolve(strict=True)), 'samefile': os.path.samefile(LOGICAL, PHYSICAL)},
    'pipeline_status_snapshot': record(EXECUTION / 'pipeline_status.json'),
    'pipeline_status_at_capture': pipeline.get('status'),
    'jobs': job_records,
    'direct_dependency_sources': [record(p) for p in dependencies],
    'existing_absolute_config_locations': [record(p) for p in state_paths],
    'training_path_expression_checks': path_expressions,
    'aggregate_to_plot': {
        'existing_aggregate': record(aggregate_path), 'existing_status': aggregate.get('status'),
        'plot_default_aggregate_directory': str(plot_default),
        'samefile_as_aggregate_output_directory': os.path.samefile(plot_default, aggregate_path.parent),
        'output_artifact_names': aggregate_names,
        'artifact_names_are_relative': all(not Path(str(n)).is_absolute() for n in aggregate_names),
    },
    'scientific_modules_imported': sorted(set(sys.modules) & {'torch', 'numpy', 'PIL', 'matplotlib'}),
    'scientific_entrypoints_executed': False,
    'scientific_sources_plans_states_modified': False,
    'definite_junction_failure_found': False,
    'not_checked': [
        'No GPU, model forward, dataset array, checkpoint tensor, formal evaluation, plotting or full scientific pipeline execution.',
        'Future official evaluation artifacts do not exist yet; their numerical validity is not established by this source review.',
        'This is a path-alias audit, not certification of every runtime dependency or scientific result.',
        'Future reorganization or preexisting outputs introduced after capture require a fresh identity/config check.',
    ],
}
assert not report['scientific_modules_imported']
assert all(j['same_file_after_resolve'] and j['matches_queued_entrypoint_sha256'] for j in job_records)
assert path_expressions['cache_paths_equal_after_original_normalization']
assert path_expressions['data_paths_equal_after_original_normalization']
destination = HERE / 'READONLY_METADATA_REPORT.json'
with destination.open('x', encoding='utf-8', newline='\n') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({'report': str(destination), 'sha256': sha(destination), 'definite_junction_failure_found': False, 'jobs_checked': len(job_records), 'existing_absolute_configs': sum(p.exists() for p in state_paths)}, ensure_ascii=False))
