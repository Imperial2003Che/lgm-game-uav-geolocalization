"""Freeze only source preparation using standard-library file reads.

Does not run driver.prepare, register a queue, create a release, or bind any
future training checkpoint. Runtime metadata comes from the frozen predecessor.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract as k

def main():
    destination = HERE / 'SOURCE_MANIFEST.json'
    k.require(not destination.exists(), 'Source manifest already frozen')
    independent = k.E / 'independent_comparison_plan_v2.json'
    k.require(k.sha(independent) == k.INDEPENDENT_SHA, 'Registered predecessor changed')
    plan = k.read(independent)
    runtime = plan['jobs'][0]['runtime_snapshot']
    k.require(Path(runtime['executable']) == k.PYTHON and not runtime['scientific_modules_imported'], 'Wrong predecessor environment')
    k.require(k.sha(k.CLIP_MANIFEST) == k.CLIP_MANIFEST_SHA, 'CLIP snapshot manifest changed')
    cpu = HERE.parent / 'clip_cpu_offline_validation_1721' / 'result.json'
    k.require(k.sha(cpu) == '23752e1ab4340d243c0b82105d27f8b70e738c5e7b15d66e762527b76f5cd517', 'Independent CPU evidence changed')
    paths = list(HERE.glob('*.py')) + [HERE / 'README.md', HERE / 'HANDOFF.md',
        HERE / 'STDLIB_REVIEW.json', HERE.parent / 'corrected_driver_v1' / 'SOURCE_MANIFEST.json',
        k.E / 't6_corrected_driver_review_1822' / 'INDEPENDENT_REVIEW.json',
        k.COMPONENTS / 'measurement_components.py', k.COMPONENTS / 'SOURCE_MANIFEST.json',
        k.CLIP_MANIFEST, HERE.parent / 'CLIP_OFFLINE_SOURCE_AUDIT_1721.json',
        HERE.parent / 'CLIP_OFFLINE_SOURCE_AUDIT_1721.md', cpu,
        k.P / 'lgm_game_pytorch' / 'formal_retrieval.py',
        k.P / 'lgm_game_pytorch' / 'generate_clip_image_evidence.py',
        k.P / 'experiments' / 'aggregate_frozen_formal_results.py',
        k.P / 'experiments' / 'run_transactions_formal_efficiency.py',
        k.P / 'experiments' / 'transactions_efficiency_analysis.py',
        k.P / 'experiments' / 'run_frozen_formal_matrix.py',
        k.D / 'FORMAL_EXPERIMENT_PROTOCOL.md',
        k.E / 'supervise_pipeline.py', k.E / 'supervise_independent_comparisons.py',
        independent, k.E / 'extension_plan.json', k.E / 'latest_baseline_plan.json']
    pipeline = k.read(k.E / 'pipeline_status.json')
    jobs = [{key: row[key] for key in ('id', 'command', 'entrypoint_sha256')} for row in pipeline['jobs']]
    for row in jobs:
        entry = Path(row['command'][1])
        k.require(k.sha(entry) == row['entrypoint_sha256'], 'Registered pipeline entrypoint changed')
        paths.append(entry)
    # Capture actual installed CLIP loader/model/processor files already audited.
    audit = k.read(HERE.parent / 'CLIP_OFFLINE_SOURCE_AUDIT_1721.json')
    for item in audit['source_pins']:
        paths.append(Path(item['path']))
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    checks = k.read(HERE / 'STDLIB_REVIEW.json')
    k.require(checks['failed'] == 0 and not checks['scientific_execution_performed'], 'Stdlib review failed')
    files = [k.record(path) for path in sorted(set(paths), key=lambda x: str(x).casefold())]
    value = {'schema': 'corrected-primary-t6-source-preparation.v1', 'created_utc': k.now(),
        'files': files, 'pipeline_jobs': jobs, 'baseline_runtime': runtime,
        'execution_performed': False, 'scientific_imports': [], 'driver_prepared_plan_created': False,
        'release_created': False, 'registered_in_any_queue': False, 'full_t6_complete': False,
        'completed_scope': 'real driver implementation and standard-library/AST/mock review only',
        'available_independent_real_evidence': 'CPU CLIP load/learned weights/one training-image interface; no GPU/parity/timing',
        'next_required_before_any_run': ['source review', 'all registered predecessors genuinely completed and exited',
            'complete formal aggregate and existing actual checkpoint binding through driver prepare',
            'separate explicit exact-plan release', 'exclusive GPU and source-derived case resource headroom'],
        'external_efficiency_rows_implemented': 0,
        'missing_full_t6': ['seven matched T1 external fits', 'newer comparator efficiency',
                           'full dataset online CLIP probability parity/accuracy (not claimed)']}
    k.write_new(destination, value)
    print(json.dumps({'path': str(destination), 'sha256': k.sha(destination), 'files': len(files),
                      'prepared_only': True}))

if __name__ == '__main__':
    main()
