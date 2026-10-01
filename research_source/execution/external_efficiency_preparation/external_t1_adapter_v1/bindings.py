"""Read-only, standard-library binding of the frozen seven T1 efficiency slots.

No future checkpoint is fabricated. bind_completed_slot only returns an in-memory
binding after real existing T1 fit/evaluation artifacts pass its file checks.
The scientific loader additionally runs the original complete validators.
"""
from __future__ import annotations
from functools import lru_cache
import importlib.util
import importlib.metadata
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
E = HERE.parents[1]
BASE = E / 'baseline_preparation'
DELIVERY = BASE / 'compatibility_v3' / 'delivery'
EXT = DELIVERY / 'external_baselines'
WORK = BASE / 'compatibility_v3' / 'work'
RUNS = EXT / 'runs' / 'transactions_t1'
V2 = HERE.parent / 'corrected_driver_v2'
V2_MANIFEST_SHA = '59f1c85e6e58541b50aec8054c37ac101b3cf58995e1c565c0abf4b51c0a760e'
COMPONENTS = HERE.parent / 'corrected_v1'
COMPONENT_SHA = 'a967746f177de58b2d45e910d96063b6e55bbc42675dc692c4798acaf0f6546f'
EXPECTED_SLOTS = (
    ('qdfl_dinov2_b14/seed_1', 'qdfl', 'QDFL', 'qdfl_dinov2_b14', 1, 160),
    ('qdfl_dinov2_b14/seed_2', 'qdfl', 'QDFL', 'qdfl_dinov2_b14', 2, 160),
    ('qdfl_dinov2_b14/seed_3', 'qdfl', 'QDFL', 'qdfl_dinov2_b14', 3, 160),
    ('fsra_vit/seed_1', 'qdfl', 'FSRA', 'fsra_vit', 1, 120),
    ('sdpl_swinv2_b/seed_1', 'qdfl', 'SDPL', 'sdpl_swinv2_b', 1, 160),
    ('ccr_convnext_b/seed_1', 'qdfl', 'CCR', 'ccr_convnext_b', 1, 200),
    ('mccg_convnext_tiny/seed_1', 'mccg', 'MCCG', 'mccg_convnext_tiny', 1, 200),
)
EXPECTED_TASKS = ('university1652_drone_to_satellite', 'university1652_satellite_to_drone',
    'sues200_uav_150m_to_satellite', 'sues200_satellite_to_uav_150m',
    'sues200_uav_200m_to_satellite', 'sues200_satellite_to_uav_200m',
    'sues200_uav_250m_to_satellite', 'sues200_satellite_to_uav_250m',
    'sues200_uav_300m_to_satellite', 'sues200_satellite_to_uav_300m')
ROLE_NAMES = ('query_drone', 'gallery_drone', 'query_satellite', 'gallery_satellite',
              'satellite_all', 'drone_150_all', 'drone_200_all', 'drone_250_all', 'drone_300_all')
SIZES = {'qdfl_dinov2_b14': (280, 280), 'fsra_vit': (256, 256),
         'sdpl_swinv2_b': (256, 256), 'ccr_convnext_b': (384, 384), 'mccg_convnext_tiny': (256, 256)}
BATCHES = {'qdfl_dinov2_b14': 8, 'fsra_vit': 8, 'sdpl_swinv2_b': 8,
           'ccr_convnext_b': 4, 'mccg_convnext_tiny': 8}

@lru_cache(maxsize=1)
def common():
    # Reuse reviewed stdlib helpers only, not the primary-model resource/plan gate.
    import hashlib
    import json
    manifest_path = V2 / 'SOURCE_MANIFEST.json'
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != V2_MANIFEST_SHA:
        raise RuntimeError('Corrected driver v2 source manifest changed')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    path = V2 / 'contract.py'
    item = next(x for x in manifest['files'] if Path(x['path']) == path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise RuntimeError('Pinned common contract changed')
    spec = importlib.util.spec_from_file_location('external_t1_reviewed_common', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def source_manifest():
    k = common()
    manifest = k.read(HERE / 'SOURCE_MANIFEST.json')
    k.require(manifest['scientific_execution_performed'] is False, 'Source preparation is mislabelled')
    for item in manifest['files']:
        k.verify_record(item)
    k.require(k.sha(COMPONENTS / 'measurement_components.py') == COMPONENT_SHA, 'Shared measurement components changed')
    return manifest

def slots():
    k = common()
    matrix = k.read(EXT / 'transactions_t1_matrix.json')
    fields = ('run_id', 'framework', 'method', 'config_id', 'seed', 'epochs')
    observed = tuple(tuple(row[x] for x in fields) for row in matrix['runs'])
    k.require(observed == EXPECTED_SLOTS and matrix['registered_run_count'] == 7, 'Frozen seven-slot matrix differs')
    k.require(matrix['official_evaluation']['total_task_evaluations'] == 70, 'T1 task count differs')
    return matrix['runs']

def role_kind(role):
    common().require(role in ROLE_NAMES, 'Unknown or ambiguous view role: ' + str(role))
    return 'satellite' if 'satellite' in role else 'drone'

def checkpoint_path(row):
    suffix = Path('checkpoints/last.ckpt') if row['framework'] == 'qdfl' else Path('net_last.pth')
    return RUNS / 'fits' / row['run_id'] / suffix

def bind_completed_slot(run_id):
    """File-only future binding; writes no plan/release and reads no tensor payload."""
    k = common()
    source_manifest()
    registered = slots()
    k.require(run_id in [row['run_id'] for row in registered], 'Unregistered fit slot')
    ledger_path = RUNS / 'transactions_t1_ledger.json'
    ledger = k.read(ledger_path)
    k.require(ledger.get('status') == 'all_fits_and_official_evaluations_complete', 'T1 is not fully complete')
    k.require(set(ledger.get('runs', {})) == {row['run_id'] for row in registered}, 'T1 ledger slot set differs')
    gate_path = RUNS / 'transactions_t1_all_fits_gate.json'
    gate = k.read(gate_path)
    k.verify_seal(gate)
    k.require(gate['status'] == 'all_seven_fits_validated' and gate['registered_run_count'] == 7, 'All-fit gate is incomplete')
    k.require([r['run_id'] for r in gate['runs']] == [r['run_id'] for r in registered], 'All-fit gate ordering differs')
    k.require(gate['matrix_sha256'] == k.sha(EXT / 'transactions_t1_matrix.json') and
              gate['runner_sha256'] == k.sha(EXT / 'run_transactions_t1_matrix.py'), 'All-fit sources differ')
    records = [k.record(ledger_path), k.record(gate_path)]
    selected = None
    for row, gated in zip(registered, gate['runs']):
        status = ledger['runs'][row['run_id']]
        k.require(status.get('status') == 'completed' and status.get('evaluation_status') == 'completed',
                  'A T1 fit or official evaluation is incomplete: ' + row['run_id'])
        fit = RUNS / 'fits' / row['run_id']
        evaluation = RUNS / 'evaluations' / row['run_id']
        cp = checkpoint_path(row)
        for path, key in ((fit / 'fit_manifest.json', 'fit_manifest'),
                          (fit / 'run_config.json', 'run_config'), (cp, 'checkpoint')):
            actual = k.record(path)
            k.require(Path(gated[key + '_path']) == path and gated[key + '_sha256'] == actual['sha256'],
                      'All-fit gate artifact changed: ' + str(path))
            records.append(actual)
        fit_manifest = k.read(fit / 'fit_manifest.json')
        k.verify_seal(fit_manifest)
        k.require(fit_manifest['status'] == 'completed' and fit_manifest['completed_epochs'] == row['epochs'],
                  'Final-epoch fit is incomplete')
        manifest_path = evaluation / 'evaluation_manifest.json'
        manifest = k.read(manifest_path)
        k.verify_seal(manifest)
        k.require(manifest['status'] == 'completed' and tuple(manifest['task_names']) == EXPECTED_TASKS,
                  'Official ten-task evaluation is incomplete')
        k.require((manifest['config_id'], manifest['seed']) == (row['config_id'], row['seed']), 'Evaluation fit identity differs')
        cfg_path = evaluation / 'evaluation_config.json'
        config = k.read(cfg_path)
        k.verify_seal(config)
        k.require(manifest['evaluation_config_sha256'] == k.sha(cfg_path), 'Evaluation config changed')
        k.require(config['fit']['checkpoint_sha256'] == gated['checkpoint_sha256'] and
                  Path(config['fit']['checkpoint_path']) == cp, 'Evaluation belongs to another checkpoint')
        actual_artifacts = {p.relative_to(evaluation).as_posix() for p in evaluation.rglob('*') if p.is_file()
                            and p.name not in {'evaluation_manifest.json', 'status.json'}}
        k.require(actual_artifacts == set(manifest['artifacts']), 'Official evaluation file set differs')
        records.append(k.record(manifest_path))
        records.append(k.record(evaluation / 'status.json'))
        for relative, item in manifest['artifacts'].items():
            path = (evaluation / relative).resolve()
            k.require(path.is_relative_to(evaluation.resolve()), 'Evaluation artifact escapes its root')
            records.append(k.verify_record({**item, 'path': str(path)}))
        if row['run_id'] == run_id:
            selected = {'row': row, 'checkpoint': k.record(cp), 'fit_dir': str(fit),
                        'evaluation_dir': str(evaluation), 'evaluation_config': config}
    inventory = RUNS / 'transactions_t1_official_test_inventory_gate.json'
    inventory_payload = k.read(inventory)
    k.verify_seal(inventory_payload)
    k.require(inventory_payload['status'] == 'content_frozen_after_all_fits_gate' and
              inventory_payload['all_fits_gate_sha256'] == k.sha(gate_path), 'Official input inventory is not bound')
    records.append(k.record(inventory))
    selected.update({'schema': 'external-t1-efficiency-slot-binding.v1', 'source_manifest': k.record(HERE / 'SOURCE_MANIFEST.json'),
        'all_seven_completed_artifacts': records, 'all_fits_gate': str(gate_path), 'test_inventory_gate': str(inventory),
        'all_seven_original_scientific_validators_still_required_at_load': True,
        'full_t6_complete': False, 'manuscript_result': False})
    return selected

def verify_binding(binding):
    k = common()
    source_manifest()
    k.verify_record(binding['source_manifest'])
    k.require(Path(binding['source_manifest']['path']) == HERE / 'SOURCE_MANIFEST.json', 'Wrong adapter source binding')
    k.require(binding == bind_completed_slot(binding['row']['run_id']), 'Completed slot inputs changed')
    return binding

def native_environment(framework):
    lock = common().read(EXT / 'transactions_environment_lock.json')
    return lock['environments']['qdfl_framework' if framework == 'qdfl' else 'mccg']

def verify_current_environment(framework):
    """Metadata only, in the actual future child; never invokes another interpreter."""
    k = common()
    expected = native_environment(framework)
    k.require(Path(sys.executable).resolve() == Path(expected['executable']).resolve(), 'Wrong native T1 interpreter')
    k.require(sys.version == expected['python'], 'Native Python version changed')
    rows = [list(row) for row in sorted({(str(d.metadata.get('Name', '')).strip().lower(), d.version)
                for d in importlib.metadata.distributions() if str(d.metadata.get('Name', '')).strip()})]
    k.require(rows == expected['installed_distributions']['rows'], 'Native T1 package lock changed')
    return {'python': sys.version, 'executable': sys.executable, 'installed_distributions': rows}
