"""Standard-library contract for a future, separately released primary T6 run.

Importing this module never imports a scientific library or starts a process.
Existing queues, sources and releases are read-only inputs.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
E = HERE.parents[1]
D = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
P = D / 'lgm_game_pytorch'
PYTHON = Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe')
COMPONENTS = HERE.parent / 'corrected_v1'
CORE_SHA = '081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862'
COMPONENT_SHA = 'a967746f177de58b2d45e910d96063b6e55bbc42675dc692c4798acaf0f6546f'
CLIP_MANIFEST = HERE.parent / 'CLIP_OFFLINE_SNAPSHOT_MANIFEST_1721.json'
CLIP_MANIFEST_SHA = 'ae8d97c54f262adda48e94e0b7a4694e364bbe167eae761e490c02d5c5104226'
CLIP_REVISION = '3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268'
INDEPENDENT_SHA = 'a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49'
DATA_ROOTS = {'university1652': r'C:\项目\IMTMN\datasets\University-1652',
              'sues200': r'C:\项目\IMTMN\datasets\SUES-200'}
CASES = tuple((d, v) for d in DATA_ROOTS for v in ('visual', 'full'))
STATUS_CONTRACTS = (
    ('status.json', 'completed', None, None),
    ('pipeline_status.json', 'ready_for_extension_preparation', None, None),
    ('extension_status.json', 'registered_extensions_finished_review_pending',
     'extension_plan.json', '13ef69f90ef105db4e55a463532fd6ed38f573b3dbe8cd345fd64176318e46be'),
    ('latest_baseline_status.json', 'latest_baselines_finished_review_pending',
     'latest_baseline_plan.json', '80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'),
    ('independent_comparison_status.json', 'independent_comparisons_finished_review_pending',
     'independent_comparison_plan_v2.json', INDEPENDENT_SHA),
)

class GateError(RuntimeError):
    pass

def require(condition, message):
    if not condition:
        raise GateError(message)

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), default=str).encode('utf-8')).hexdigest()

def verify_seal(value):
    body = dict(value)
    expected = body.pop('payload_sha256', None)
    require(expected == canonical(body), 'Canonical payload seal is invalid')

def record(path):
    path = Path(path).resolve(strict=True)
    require(path.is_file(), 'Expected a real source file: ' + str(path))
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}

def verify_record(item):
    actual = record(item['path'])
    require(actual == item, 'Source bytes changed: ' + str(item['path']))
    return actual

def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')
    return record(path)

def scoped_new(parent, name):
    require(isinstance(name, str) and name and all(c.isalnum() or c in '_-' for c in name),
            'Output name must contain only letters, numbers, underscore or hyphen')
    parent = Path(parent).resolve()
    path = (parent / name).resolve()
    require(path.parent == parent and not path.exists(), 'Output is not new and exclusive')
    path.mkdir(parents=True, exist_ok=False)
    return path

def strict_timestamp(value):
    require(isinstance(value, str), 'Process start timestamp is absent')
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(stamp.tzinfo is not None and stamp.utcoffset() is not None,
            'Process timestamp must include timezone')
    return stamp

def process_snapshot():
    # Only PID/creation/parent/executable identity, never user command lines.
    command = ('[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); '
               'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,'
               'ExecutablePath,@{Name="CreatedUtc";Expression={$_.CreationDate.ToUniversalTime().ToString("o")}}'
               ' | ConvertTo-Json -Compress')
    result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', command],
        capture_output=True, text=True, encoding='utf-8', errors='strict', check=True,
        timeout=45, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    rows = json.loads(result.stdout)
    return rows if isinstance(rows, list) else [rows]

def process_identity(pid, rows):
    require(type(pid) is int and pid > 0, 'Invalid process PID')
    matches = [x for x in rows if x['ProcessId'] == pid]
    require(len(matches) == 1, 'Live process identity unavailable: ' + str(pid))
    row = matches[0]
    strict_timestamp(row['CreatedUtc'])
    return row

def exited(pid, started, rows, finished=None):
    require(type(pid) is int and pid > 0, 'Completed job lacks a valid PID')
    declared = strict_timestamp(started)
    live = [x for x in rows if x['ProcessId'] == pid]
    if not live:
        return True
    actual = strict_timestamp(live[0]['CreatedUtc'])
    # Slow Windows spawn can create the SAME job long after its recorded start.
    # Only a new owner created after a verified finish time establishes reuse.
    if finished is None:
        return False
    end = strict_timestamp(finished)
    require(end >= declared, 'Process finish precedes start')
    return actual > end

def no_foreign_python(rows, allowed):
    conflicts = [x for x in rows if x['Name'].lower().startswith(('python', 'pypy'))
                 and x['ProcessId'] not in allowed]
    require(not conflicts, 'Foreign Python processes still exist: ' + json.dumps(conflicts))

def self_and_verified_ancestors(rows):
    # Ancestors of this actual process only; never accept arbitrary PIDs from a plan.
    allowed, pid = set(), os.getpid()
    by_id = {x['ProcessId']: x for x in rows}
    while pid in by_id and pid not in allowed:
        allowed.add(pid)
        pid = by_id[pid]['ParentProcessId']
    require(os.getpid() in allowed, 'Own process identity unavailable')
    return allowed

def gpu_idle(allowed=()):
    result = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name',
        '--format=csv,noheader,nounits'], capture_output=True, text=True,
        encoding='utf-8', errors='strict', check=True, timeout=20,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    rows = []
    for line in result.stdout.splitlines():
        if line.strip():
            fields = next(csv.reader([line]))
            require(len(fields) == 2 and fields[0].strip().isdigit(), 'Unparseable GPU owner')
            rows.append({'pid': int(fields[0]), 'name': fields[1].strip()})
    require(not [r for r in rows if r['pid'] not in allowed], 'GPU is not exclusive: ' + str(rows))
    return rows

def resource_budget(plan, case_index):
    case = plan['cases'][case_index]
    metrics = read(Path(case['evaluation_dir']) / 'metrics.json')['results']
    scales = [(int(x['queries']), int(x['gallery'])) for x in metrics.values()]
    require(scales and all(q > 0 and g > 0 for q, g in scales), 'Missing official task scales')
    descriptor_rows_upper = sum(q + g for q, g in scales)
    # This counts every task's rows, so shared images only make it conservative.
    descriptor_bytes_upper = descriptor_rows_upper * 512 * 4
    rank_elements = max(q * g for q, g in scales)
    checkpoint_bytes = case['checkpoint']['bytes']
    clip_bytes = next(x['bytes'] for x in plan['clip']['files'] if Path(x['path']).name == 'pytorch_model.bin') if case['variant'] == 'full' else 0
    items = {
        'checkpoint_archive_and_loaded_state_upper': 2 * checkpoint_bytes,
        'clip_archive_and_loaded_state_upper': 2 * clip_bytes,
        'encoded_mapping_plus_saved_stack_plus_task_stacks_upper': 3 * descriptor_bytes_upper,
        'largest_retained_int64_rank_matrix': 8 * rank_elements,
        'explicit_unprofiled_interpreter_io_and_allocator_margin': 1024**3,
    }
    return {'case_index': case_index, 'source_task_scales': scales, 'host_components_bytes': items,
        'host_required_available_bytes': sum(items.values()),
        'descriptor_extraction_workers': 0,
        'scope': 'source-derived engineering admission estimate, not a measured peak or OOM guarantee',
        'cuda_explicit_rank_outputs_and_scores_bytes': 12 * rank_elements,
        'cuda_sort_workspace_and_encoder_activations_not_yet_profiled': True}

def resource_gate(plan, case_index):
    # No impossible physical-memory threshold copied from a different training job.
    import ctypes
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ('ullTotalPhys', 'ullAvailPhys', 'ullTotalPageFile',
            'ullAvailPageFile', 'ullTotalVirtual', 'ullAvailVirtual', 'ullAvailExtendedVirtual')]
    state = MEMORYSTATUSEX()
    state.dwLength = ctypes.sizeof(state)
    require(bool(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state))), 'Cannot read memory')
    budget = resource_budget(plan, case_index)
    needed = budget['host_required_available_bytes']
    require(needed <= state.ullTotalPhys, 'Source-derived host estimate exceeds total physical memory; revise allocation design')
    require(state.ullAvailPhys >= needed, 'Insufficient free physical memory for source-derived case estimate')
    require(state.ullAvailPageFile >= needed, 'Insufficient free commit for source-derived case estimate')
    return {'available_physical_bytes': state.ullAvailPhys, 'available_commit_bytes': state.ullAvailPageFile,
            'total_physical_bytes': state.ullTotalPhys, 'budget': budget}

def runtime_snapshot():
    code = ('import importlib.metadata as m,json,sys; '
        'print(json.dumps({"python":sys.version,"executable":sys.executable,'
        '"distributions":sorted((d.metadata.get("Name",""),d.version) for d in m.distributions()),'
        '"scientific_modules_imported":[n for n in ("torch","torchvision","numpy","matplotlib","sklearn") if n in sys.modules]},sort_keys=True))')
    r = subprocess.run([str(PYTHON), '-I', '-c', code], capture_output=True, text=True,
        encoding='utf-8', check=True, timeout=45,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    value = json.loads(r.stdout)
    value['interpreter_sha256'] = sha(PYTHON)
    require(not value['scientific_modules_imported'], 'Metadata probe imported science')
    return value

def check_job_definitions(observed, expected):
    require([x.get('id') for x in observed] == [x['id'] for x in expected], 'Job order/identity changed')
    require(len({x['id'] for x in observed}) == len(observed), 'Duplicate predecessor job')
    for got, wanted in zip(observed, expected):
        for field in ('command', 'cwd', 'entrypoint_sha256', 'source_sha256', 'runtime_snapshot'):
            if field in wanted:
                require(got.get(field) == wanted[field], 'Predecessor job binding changed: ' + wanted['id'] + '/' + field)
        require(got.get('status') == 'completed' and type(got.get('exit_code')) is int
                and got['exit_code'] == 0, 'Predecessor job did not finish successfully')

def assert_nested_owners_exited(value, rows, inherited_start=None):
    if isinstance(value, dict):
        stamp = value.get('started_utc', value.get('supervisor_started_utc', inherited_start))
        for key, v in value.items():
            if key in {'pid', 'child_pid', 'surviving_child_pid', 'launcher_pid', 'worker_pid',
                       'training_pid', 'process_id', 'controller_pid', 'supervisor_pid'} and v not in (None, 0):
                require(exited(v, stamp, rows, value.get('finished_utc')), 'Predecessor owner has not exited: ' + key + '=' + str(v))
            elif isinstance(v, (dict, list)):
                assert_nested_owners_exited(v, rows, stamp)
    elif isinstance(value, list):
        for v in value:
            assert_nested_owners_exited(v, rows, inherited_start)

def predecessors(manifest, rows):
    proofs = []
    for filename, wanted_status, plan_name, plan_sha in STATUS_CONTRACTS:
        path = E / filename
        state = read(path)
        require(state.get('status') == wanted_status, filename + ' is not complete')
        pid_key = 'controller_pid' if filename == 'status.json' else 'supervisor_pid'
        start_key = 'started_utc' if filename == 'status.json' else 'supervisor_started_utc'
        require(exited(state.get(pid_key), state.get(start_key), rows, state.get('finished_utc')), filename + ' owner is live')
        if plan_name:
            require(sha(E / plan_name) == plan_sha and state.get('plan_sha256') == plan_sha,
                    filename + ' does not bind the registered plan')
            expected = read(E / plan_name)['jobs']
            check_job_definitions(state.get('jobs', []), expected)
        elif filename == 'pipeline_status.json':
            check_job_definitions(state.get('jobs', []), manifest['pipeline_jobs'])
        else:
            require(not state.get('active'), 'Main queue still declares an active job')
            events = state.get('events', [])
            require(events and all(x.get('status') == 'completed' and x.get('exit_code') == 0 for x in events),
                    'Main completed event evidence missing')
        assert_nested_owners_exited(state, rows)
        proofs.append(record(path))
    return proofs

def verify_snapshot():
    require(sha(CLIP_MANIFEST) == CLIP_MANIFEST_SHA, 'Fixed CLIP manifest changed')
    clip = read(CLIP_MANIFEST)
    require(clip['revision'] == CLIP_REVISION and len(clip['files']) == 8, 'Wrong CLIP snapshot')
    require(Path(clip['local_snapshot']).name == CLIP_REVISION, 'CLIP directory revision differs')
    for item in clip['files']:
        verify_record(item)
        require(Path(item['path']).parent == Path(clip['local_snapshot']), 'CLIP file escapes snapshot')
    return clip

def aggregate_proof():
    base = P / 'results' / 'formal_matrix_aggregate'
    path = base / 'aggregate_manifest.json'
    value = read(path)
    verify_seal(value)
    require(value.get('status') == 'complete' and value.get('allow_partial') is False,
            'Formal aggregate is not complete')
    expected = {'valid_main_runs': 36, 'valid_sensitivity_runs': 6, 'completed_pairwise_tests': 33}
    require(all(value.get('matrix', {}).get(k) == v for k, v in expected.items()), 'Formal matrix is incomplete')
    artifacts = []
    for item in value['output_artifacts']:
        output = (base / item['path']).resolve()
        require(output.parent == base.resolve(), 'Aggregate output escapes root')
        artifacts.append(verify_record({**item, 'path': str(output)}))
    catalog_path = base / 'input_artifact_sha256.csv'
    require(any(Path(x['path']) == catalog_path for x in artifacts), 'Input catalog is not sealed')
    with catalog_path.open(encoding='utf-8-sig', newline='') as f:
        inputs = list(csv.DictReader(f))
    require(inputs and len(inputs) == value['input_artifact_count'], 'Input artifact count differs')
    for item in inputs:
        input_path = Path(item['path'])
        if not input_path.is_absolute():
            input_path = D / input_path
        verify_record({'path': str(input_path.resolve()), 'bytes': int(item['bytes']), 'sha256': item['sha256']})
    return {'manifest': record(path), 'outputs': artifacts, 'catalog_rows': len(inputs)}

def actual_case_files(dataset, variant):
    run = P / 'runs' / 'formal_main' / dataset / variant / 'seed_1'
    ev = P / 'evaluations' / 'formal_main' / dataset / variant / 'seed_1'
    run_manifest = read(run / 'run_manifest.json')
    evaluation = read(ev / 'evaluation_manifest.json')
    verify_seal(run_manifest)
    verify_seal(evaluation)
    require(run_manifest.get('status') == 'completed' and run_manifest.get('epochs_completed') == 80,
            'Case training is incomplete')
    require(evaluation.get('status') == 'completed', 'Case evaluation is incomplete')
    checkpoint = record(run / 'best.pt')
    require(evaluation['checkpoint']['sha256'] == checkpoint['sha256'], 'Evaluation checkpoint differs')
    return {'dataset': dataset, 'variant': variant, 'seed': 1,
            'run_dir': str(run), 'evaluation_dir': str(ev), 'checkpoint': checkpoint,
            'files': [record(run / 'run_manifest.json'), record(run / 'run_config.json'),
                      record(ev / 'evaluation_manifest.json'), record(ev / 'metrics.json')]}

def frozen_sources():
    manifest = read(HERE / 'SOURCE_MANIFEST.json')
    require(manifest.get('execution_performed') is False, 'Source preparation is mislabelled')
    for item in manifest['files']:
        verify_record(item)
    require(sha(P / 'lgm_game_pytorch' / 'formal_retrieval.py') == CORE_SHA, 'Core changed')
    require(sha(COMPONENTS / 'measurement_components.py') == COMPONENT_SHA, 'Frozen components changed')
    return manifest

def prepare(name):
    manifest = frozen_sources()
    rows = process_snapshot()
    predecessor = predecessors(manifest, rows)
    no_foreign_python(rows, self_and_verified_ancestors(rows))
    gpu_idle()
    aggregate = aggregate_proof()
    clip = verify_snapshot()
    runtime = runtime_snapshot()
    require(runtime == manifest['baseline_runtime'], 'Baseline environment differs from source preparation')
    cases = [actual_case_files(d, v) for d, v in CASES]
    source = record(HERE / 'SOURCE_MANIFEST.json')
    cache = []
    for d in DATA_ROOTS:
        for suffix in ('.npz', '.meta.json'):
            cache.append(record(P / 'evidence_cache' / (d + '_clip_image_evidence' + suffix)))
    cache.append(record(P / 'manifests' / 'sues200_official_train_ids.yaml'))
    directory = scoped_new(HERE / 'preparations', name)
    plan = {'schema': 'corrected-primary-t6-driver-plan.v1', 'created_utc': now(),
        'source_manifest': source, 'predecessors': predecessor, 'aggregate_proof': aggregate,
        'cases': cases, 'cache_and_split': cache, 'clip': clip, 'runtime': runtime,
        'device_index': 0, 'descriptor_batch_size': 128, 'descriptor_workers': 0,
        'original_evaluation_descriptor_workers': 8,
        'full_t6_complete': False, 'online_accuracy_scope': 'one fixed first query per official task',
        'missing_comparison_rows': 'seven external T1 fits and newer comparator efficiency',
        'future_scientific_validation': 'Each case is revalidated by frozen aggregate.validate_completed_run before loading'}
    plan['payload_sha256'] = canonical(plan)
    plan_artifact = write_new(directory / 'plan.json', plan)
    write_new(directory / 'release_TEMPLATE.json', {'allow_run': False, 'plan': plan_artifact,
        'reason': 'Inactive template. Requires separate explicit release after source review and idle-resource checks.'})
    return plan_artifact

def verify_plan(path, manifest):
    plan = read(path)
    verify_seal(plan)
    verify_record(plan['source_manifest'])
    require(Path(plan['source_manifest']['path']) == HERE / 'SOURCE_MANIFEST.json', 'Wrong driver source manifest')
    require([(c['dataset'], c['variant']) for c in plan['cases']] == list(CASES), 'Wrong four-case registry')
    require(plan['device_index'] == 0 and plan['descriptor_batch_size'] == 128 and plan['descriptor_workers'] == 0,
            'Native runtime controls changed')
    for case in plan['cases']:
        verify_record(case['checkpoint'])
        for item in case['files']:
            verify_record(item)
    for item in plan['cache_and_split']:
        verify_record(item)
    for item in plan['predecessors']:
        verify_record(item)
    require(aggregate_proof() == plan['aggregate_proof'], 'Aggregate proof changed')
    require(verify_snapshot() == plan['clip'], 'CLIP sources changed')
    require(runtime_snapshot() == plan['runtime'] == manifest['baseline_runtime'], 'Runtime changed')
    return plan
