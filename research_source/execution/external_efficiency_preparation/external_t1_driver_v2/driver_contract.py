"""Standard-library seven-slot binding and admission for actual single-slot runs.

No scientific imports, process launch, active release, or checkpoint binding is
performed at import. Whole-queue admission reuses reviewed primary v2 helpers.
"""
from __future__ import annotations
from functools import lru_cache
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ADAPTER = HERE.parent / 'external_t1_adapter_v2'
ADAPTER_SHA = '1e6fd42b5b8777712e4283a48425bfc3f367fe58467118bf09567f59dbb11464'

@lru_cache(maxsize=1)
def adapters():
    manifest = ADAPTER / 'SOURCE_MANIFEST.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != ADAPTER_SHA:
        raise RuntimeError('Frozen native adapter v2 manifest changed')
    source = json.loads(manifest.read_text(encoding='utf-8'))
    for name in ('bindings', 'native_ops', 'native_load'):
        path = ADAPTER / (name + '.py')
        item = next(row for row in source['files'] if Path(row['path']) == path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError('Frozen adapter code changed: ' + name)
        if name in sys.modules and Path(sys.modules[name].__file__).resolve() != path.resolve():
            raise RuntimeError('Foreign native adapter namespace: ' + name)
    sys.path.insert(0, str(ADAPTER))
    return tuple(importlib.import_module(name) for name in ('bindings', 'native_ops', 'native_load'))

def common():
    return adapters()[0].common()

def no_science_loaded():
    common().require(not any(name in sys.modules for name in
        ('torch', 'numpy', 'PIL', 'torchvision', 'transformers', 'scipy', 'matplotlib')), 'Scientific import preceded admission')

def read_bound_json(path):
    """One raw read binds the parsed value and its artifact; recheck before use."""
    k = common()
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    record = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    value = json.loads(raw.decode('utf-8-sig'))
    k.verify_record(record)
    return value, record

def verify_sources():
    k = common()
    source = k.read(HERE / 'SOURCE_MANIFEST.json')
    k.require(source['scientific_execution_performed'] is False, 'Mislabelled source preparation')
    for item in source['files']:
        k.verify_record(item)
    adapters()[0].source_manifest()
    return source

def admitted_predecessors():
    k = common()
    primary = k.frozen_sources()
    rows = k.process_snapshot()
    proofs = k.predecessors(primary, rows)
    k.no_foreign_python(rows, k.self_and_verified_ancestors(rows))
    k.gpu_idle()
    return proofs, k.process_identity(os.getpid(), rows)

def derive_slot_budget(binding):
    """Conservative source-derived host admission, not empirical peak memory."""
    k = common()
    metrics = k.read(Path(binding['evaluation_dir']) / 'metrics.json')
    shapes = [row['shape'] for row in metrics['descriptor_fingerprints'].values()]
    k.require(shapes and all(len(x) == 2 and all(type(n) is int and n > 0 for n in x) for x in shapes),
              'Completed evaluation lacks real descriptor dimensions')
    sizes = [n * d * 4 for n, d in shapes]
    max_gallery = max(int(x['gallery']) for x in metrics['tasks'])
    parts = {'checkpoint_archive_and_loaded_state_upper': 2 * binding['checkpoint']['bytes'],
        'largest_native_output_list_cat_and_fingerprint_bytes_upper': 3 * max(sizes),
        'official_128query_cpu_score_sort_workspace_upper': 128 * max_gallery * 24,
        'explicit_unprofiled_runtime_and_allocator_margin': 1024**3}
    return {'host_required_available_bytes': sum(parts.values()), 'host_components_bytes': parts,
        'descriptor_output_bytes': sum(sizes), 'disk_required_free_bytes': sum(sizes) + 1024**3,
        'largest_descriptor_shape': shapes[sizes.index(max(sizes))], 'all_declared_shapes': shapes,
        'extraction_workers': 0, 'estimate_is_not_measured_peak': True,
        'cuda_encoder_activations_not_yet_profiled': True}

def resource_gate(binding):
    import ctypes
    k = common()
    budget = derive_slot_budget(binding)
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in ('ullTotalPhys', 'ullAvailPhys', 'ullTotalPageFile',
             'ullAvailPageFile', 'ullTotalVirtual', 'ullAvailVirtual', 'ullAvailExtendedVirtual')]
    state = MEMORYSTATUSEX()
    state.dwLength = ctypes.sizeof(state)
    k.require(bool(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state))), 'Cannot read host memory')
    needed = budget['host_required_available_bytes']
    k.require(needed <= state.ullTotalPhys, 'Slot estimate exceeds physical RAM; allocation design needs review')
    k.require(state.ullAvailPhys >= needed and state.ullAvailPageFile >= needed,
              'Insufficient physical/commit headroom for real slot allocation estimate')
    free = shutil.disk_usage(HERE).free
    k.require(free >= budget['disk_required_free_bytes'], 'Insufficient disk headroom for actual descriptor artifacts')
    return {'budget': budget, 'observed_available_physical': state.ullAvailPhys,
        'observed_available_commit': state.ullAvailPageFile, 'observed_disk_free': free}

def prepare(name):
    """Future callable binding. Never invoked during this source-only preparation."""
    no_science_loaded()
    source = verify_sources()
    preceding, owner = admitted_predecessors()
    b = adapters()[0]
    bindings = [b.bind_completed_slot(row['run_id']) for row in b.slots()]
    k = common()
    # Recheck completion proofs after reading the seven actual checkpoint sets.
    k.require(admitted_predecessors()[0] == preceding, 'Predecessor evidence changed during preparation')
    directory = k.scoped_new(HERE / 'preparations', name)
    plan = {'schema': 'external-t1-seven-slot-efficiency-plan.v2', 'created_utc': k.now(),
        'source_manifest': k.record(HERE / 'SOURCE_MANIFEST.json'), 'predecessors': preceding,
        'bindings': bindings, 'run_ids': [row['run_id'] for row in b.slots()],
        'task_count_per_slot': 10, 'total_task_count': 70, 'device_index': 0,
        'sampling_rule': 'first query in each frozen official task order',
        'full_gallery_metric_rtol': 2e-6, 'full_gallery_metric_atol': 2e-7,
        'descriptor_fingerprint_policy': 'exact same native batch descriptor SHA as completed official evaluation',
        'b1_cross_batch_policy': 'diagnostic arrays and actual differences; only independent B1-vs-B1 extractor parity is exact',
        'slot_budgets': [derive_slot_budget(binding) for binding in bindings],
        'full_t6_complete': False, 'manuscript_result': False,
        'scope': 'independently callable one-slot workers; seven-slot scheduling and final combined table not implemented'}
    plan['payload_sha256'] = k.canonical(plan)
    record = k.write_new(directory / 'plan.json', plan)
    k.write_new(directory / 'release_TEMPLATE.json', {'allow_run': False, 'plan': record,
        'allowed_run_ids': plan['run_ids'], 'reason': 'Inactive template. Separate reviewed exact-plan release required.'})
    return record

def verify_plan(plan_path, run_id, *, expected_record):
    k, b = common(), adapters()[0]
    verify_sources()
    plan, captured = read_bound_json(plan_path)
    k.require(captured == expected_record, 'Plan changed after exact release binding')
    k.verify_seal(plan)
    k.verify_record(plan['source_manifest'])
    k.require(Path(plan['source_manifest']['path']) == HERE / 'SOURCE_MANIFEST.json', 'Wrong driver source binding')
    expected = [row['run_id'] for row in b.slots()]
    k.require(plan['run_ids'] == expected and [v['row']['run_id'] for v in plan['bindings']] == expected,
              'Prepared seven-slot registry changed')
    k.require(plan['task_count_per_slot'] == 10 and plan['total_task_count'] == 70 and plan['device_index'] == 0,
              'Task/device scope changed')
    k.require(plan['full_gallery_metric_rtol'] == 2e-6 and plan['full_gallery_metric_atol'] == 2e-7,
              'Frozen comparison thresholds changed')
    k.require(plan['sampling_rule'] == 'first query in each frozen official task order' and
              plan['descriptor_fingerprint_policy'] == 'exact same native batch descriptor SHA as completed official evaluation',
              'Prepared sampling/descriptor parity policy changed')
    k.require(plan['b1_cross_batch_policy'] == 'diagnostic arrays and actual differences; only independent B1-vs-B1 extractor parity is exact',
              'Prepared cross-batch diagnostic policy changed')
    k.require(plan['full_t6_complete'] is False and plan['manuscript_result'] is False, 'Partial scope is mislabelled')
    k.require(run_id in expected, 'Unregistered efficiency slot')
    for item in plan['predecessors']:
        k.verify_record(item)
    binding = plan['bindings'][expected.index(run_id)]
    b.verify_binding(binding)
    k.require(derive_slot_budget(binding) == plan['slot_budgets'][expected.index(run_id)], 'Native descriptor/resource inputs changed')
    k.verify_record(captured)
    return plan, binding

def verify_release(release_path, plan_path, run_id):
    k = common()
    release, release_record = read_bound_json(release_path)
    _, plan_record = read_bound_json(plan_path)
    k.require(release.get('allow_run') is True and release.get('plan') == plan_record,
              'A separate active release for this exact plan is required')
    k.require(run_id in release.get('allowed_run_ids', []), 'This slot is not included in the release')
    k.verify_record(release_record)
    k.verify_record(plan_record)
    return release_record, plan_record

def failure_artifacts(output, error):
    """Preserve v2 parity arrays before writing JSON metadata, never in JSON itself."""
    import traceback
    k = common()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    arrays, persistence_errors = {}, []
    np = sys.modules.get('numpy')
    for attr, filename in (('actual_descriptor_array', 'failure_descriptor_actual.npy'),
                           ('expected_descriptor_array', 'failure_descriptor_expected.npy')):
        if hasattr(error, attr):
            try:
                k.require(np is not None, 'Real NumPy runtime unavailable for failure-array persistence')
                with (output / filename).open('xb') as f:
                    np.save(f, getattr(error, attr), allow_pickle=False)
                arrays[attr] = k.record(output / filename)
            except BaseException as save_error:
                persistence_errors.append({'attribute': attr, 'error': str(save_error)})
    proof = {'status': 'failed', 'utc': k.now(), 'type': type(error).__name__, 'error': str(error),
        'traceback': traceback.format_exc(), 'descriptor_arrays': arrays,
        'array_persistence_errors': persistence_errors, 'evidence': getattr(error, 'evidence', None),
        'full_t6_complete': False, 'manuscript_result': False}
    t = sys.modules.get('torch')
    if t is not None and t.cuda.is_initialized():
        try:
            proof['actual_cuda_at_failure'] = {'allocated': t.cuda.memory_allocated(0),
                'reserved': t.cuda.memory_reserved(0), 'peak_allocated': t.cuda.max_memory_allocated(0),
                'peak_reserved': t.cuda.max_memory_reserved(0), 'free_total': list(t.cuda.mem_get_info(0))}
        except BaseException as diagnostic_error:
            proof['cuda_diagnostic_error'] = str(diagnostic_error)
    return k.write_new(output / 'failure.json', proof)
