"""Read-only full seed-1 completion audit during the subsequent active training run.

Only the frozen stdlib runner and adopted path-source helpers are imported.
The parent status event is the exit evidence; this audit held no worker handles.
"""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
PATH_MANIFEST_SHA = '11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1'
sys.path.insert(0, str(EXECUTION / 'primary_path_repair_20260918'))
from project_paths import FrozenProjectPath
from source_contract import verify

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def record(path):
    path = Path(path)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def check(condition, message):
    if not condition:
        raise RuntimeError(message)

def raw_snapshot(source, name):
    # One complete read of the atomically published status/ledger, never rewrite it.
    raw = Path(source).read_bytes()
    target = HERE / name
    with target.open('xb') as f:
        f.write(raw)
    return json.loads(raw.decode('utf-8-sig')), {
        'source': str(source), 'snapshot': str(target), 'bytes': len(raw),
        'sha256': hashlib.sha256(raw).hexdigest(),
        'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

def main():
    check(Path(sys.executable).samefile(Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe')), 'Wrong original baseline executable')
    output = HERE / 'FULL_SEED1_COMPLETION.json'
    check(not output.exists(), 'Report already exists; do not overwrite')
    provenance = verify(PATH_MANIFEST_SHA)
    root = FrozenProjectPath(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
    runner = root / 'lgm_game_pytorch/experiments/run_frozen_formal_matrix.py'
    ledger_path = root / 'lgm_game_pytorch/runs/frozen_formal_matrix_ledger.json'
    target_dir = root / 'lgm_game_pytorch/runs/formal_main/university1652/full/seed_1'
    status, status_snapshot = raw_snapshot(EXECUTION/'status.json', 'FULL_SEED1_PARENT_STATUS_RAW.json')
    ledger, ledger_snapshot = raw_snapshot(ledger_path, 'FULL_SEED1_LEDGER_RAW.json')
    source_hashes = {
        'runner_sha256': (runner, 'f251e5088b306ddec4769fab06799008d06194bc459282f2432ac3238f4ba59f'),
        'formal_script_sha256': (root/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py', '081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862'),
        'protocol_sha256': (root/'FORMAL_EXPERIMENT_PROTOCOL.md', '29c0502b07f09d45c6fd7d4a5b582fdd9a443acc9e8b818cd9941c18a0ee34f9'),
    }
    sources = {}
    for key, (path, expected) in source_hashes.items():
        sources[key] = record(path)
        check(sources[key]['sha256'] == expected == ledger[key], 'Frozen source mismatch: '+key)

    events = [e for e in status.get('events', []) if Path(e.get('output_dir','')) == Path(target_dir)]
    check(len(events) == 1, 'Need exactly one full seed-1 training event')
    event = events[0]
    check(event.get('status') == 'completed' and event.get('exit_code') == 0 and event.get('pid') == 34304, 'Full seed-1 parent exit event not complete/zero')
    command = event['command']
    def arg(name):
        return command[command.index(name)+1]
    check(command[0] == r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe', 'Unexpected science interpreter')
    check(Path(command[1]).samefile(EXECUTION/'primary_path_repair_20260918/run_formal_worker.py'), 'Unexpected worker source')
    check(arg('--path-compat-sha256') == PATH_MANIFEST_SHA and 'train' in command, 'Missing adopted worker registration')
    for key, expected in {'--dataset':'university1652','--variant':'full','--seed':'1','--epochs':'80','--workers':'8','--identities-per-batch':'16','--instances-per-identity':'4','--resume':'none'}.items():
        check(arg(key) == expected, 'Wrong original training argument: '+key)
    check(Path(arg('--output-dir')) == Path(target_dir), 'Wrong event output')
    check(status.get('controller_pid') == 36528, 'Unexpected parent; root must inspect current owner separately')

    # Only inspect whether the two old PIDs currently exist. No handle-based exit
    # observation and no inference about unrelated/current training ownership.
    ps = "@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -in @(34304,36104) } | Select-Object ProcessId,Name,ParentProcessId,@{n='CreationDate';e={$_.CreationDate.ToString('o')}},CommandLine) | ConvertTo-Json -Compress"
    cim_raw = subprocess.check_output(['powershell.exe','-NoProfile','-Command',ps], encoding='utf-8', errors='replace').strip()
    old_pid_rows = json.loads(cim_raw) if cim_raw else []
    if isinstance(old_pid_rows, dict):
        old_pid_rows = [old_pid_rows]
    check(not old_pid_rows, 'Old launcher/interpreter PID present; root must inspect identity')

    module_spec = importlib.util.spec_from_file_location('audit_frozen_runner_full_seed1', runner)
    mod = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = mod
    module_spec.loader.exec_module(mod)
    mod.Path = FrozenProjectPath
    data = mod.dataset_specs(root, FrozenProjectPath(r'C:\项目\IMTMN\datasets\University-1652'), FrozenProjectPath(r'C:\项目\IMTMN\datasets\SUES-200'))
    specs = mod.main_run_specs(root, mod.DATASETS, mod.MAIN_VARIANTS, mod.MAIN_SEEDS) + mod.sensitivity_run_specs(root, mod.DATASETS)
    check(len(specs) == 42, 'Original registry no longer has 42 specs')
    registry_sha = mod.registry_sha256(specs)
    check(registry_sha == ledger['registered_registry_sha256'], 'Registry hash mismatch')
    frozen_inputs = {name:{'data_root':str(d.data_root),'evidence_path':str(d.evidence),'evidence_sha256':d.evidence_sha256} for name,d in data.items()}
    check(frozen_inputs == ledger['frozen_inputs'], 'Frozen inputs mismatch')
    target = next(s for s in specs if s.family == 'formal_main' and s.dataset == 'university1652' and s.variant == 'full' and s.seed == 1)
    issues = mod.training_completion_issues(target, data[target.dataset], ledger['formal_script_sha256'])
    check(issues == [], 'Original completion validator: '+str(issues))
    manifest, manifest_snapshot = raw_snapshot(target.run_dir/'run_manifest.json', 'FULL_SEED1_RUN_MANIFEST_RAW.json')
    config, config_snapshot = raw_snapshot(target.run_dir/'run_config.json', 'FULL_SEED1_RUN_CONFIG_RAW.json')
    history, history_snapshot = raw_snapshot(target.run_dir/'history.json', 'FULL_SEED1_HISTORY_RAW.json')
    manifest_body = dict(manifest)
    manifest_payload_sha = manifest_body.pop('payload_sha256')
    check(mod.canonical_sha256(manifest_body) == manifest_payload_sha, 'Manifest canonical payload mismatch')
    check(mod.canonical_sha256(config['immutable_config']) == config['run_config_sha256'] == manifest['run_config_sha256'], 'Configuration canonical hash mismatch')
    check(manifest['status'] == 'completed' and manifest['epochs_completed'] == 80 and manifest['best_epoch'] == 79, 'Incomplete manifest')
    check(len(history) == 80 and [row['epoch'] for row in history] == list(range(80)), 'History must be contiguous 80 epochs')
    check(all(row['optimizer_steps'] == 652 for row in history), 'Nonfrozen epoch steps')
    artifacts = {}
    for name, declared in manifest['artifacts'].items():
        path = target.run_dir/name
        check(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe artifact name')
        artifacts[name] = record(path)
        check(artifacts[name]['sha256'] == declared['sha256'] and artifacts[name]['bytes'] == declared['bytes'], 'Full byte-level artifact mismatch: '+name)
    check(set(artifacts) == {'run_config.json','history.json','last.pt','best.pt','run.log'}, 'Unexpected target artifact inventory')
    check(artifacts['best.pt']['sha256'] == artifacts['last.pt']['sha256'], 'Final-epoch best/last differ')
    count_results = {s.identifier:mod.training_completion_issues(s,data[s.dataset],ledger['formal_script_sha256']) for s in specs}
    accepted = [identifier for identifier, found in count_results.items() if not found]
    eval_manifests = [str(s.evaluation_dir/'evaluation_manifest.json') for s in specs if (s.evaluation_dir/'evaluation_manifest.json').is_file()]
    check(len(accepted) == 16 and not eval_manifests, 'Unexpected matrix totals require explicit review')
    science = sorted(m for m in sys.modules if m.split('.')[0] in ('torch','numpy','PIL','torchvision','scipy','matplotlib'))
    check(not science, 'Scientific library unexpectedly imported')
    result = {
        'schema':'parent-event-fit-completion-review.v1',
        'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'review_script':record(__file__), 'executable':sys.executable,
        'source_provenance':provenance, 'frozen_sources':sources,
        'registered_registry_sha256':registry_sha, 'frozen_inputs_match':True,
        'parent_status_raw_snapshot':status_snapshot, 'parent_controller_pid_in_snapshot':status['controller_pid'],
        'parent_completed_event':event,
        'exit_evidence': {
            'basis':'Original monitored_run event from the exact raw parent status snapshot, written after subprocess.Popen.poll returned and p.returncode was zero.',
            'launcher_pid':34304, 'interpreter_pid_from_previous_root_identity':36104,
            'old_pid_cim_rows_at_audit':old_pid_rows,
            'audit_independently_held_worker_process_handles':False,
            'audit_independently_observed_interpreter_exit_code':False,
            'current_five_owner_verification':'Handled separately by root; not certified by this audit.',
        },
        'run_identifier':target.identifier, 'run_dir':str(target.run_dir),
        'original_training_completion_issues':issues,
        'manifest_raw_snapshot':manifest_snapshot, 'config_raw_snapshot':config_snapshot, 'history_raw_snapshot':history_snapshot,
        'manifest_payload_sha256':manifest_payload_sha, 'run_config_sha256':config['run_config_sha256'],
        'epochs_completed':80,'last_epoch':79,'optimizer_steps_each_epoch':652,
        'artifacts_sha256_verified':artifacts,
        'completed_fit_count':len(accepted),'completed_fit_ids':accepted,
        'formal_evaluation_manifest_count':len(eval_manifests), 'formal_evaluation_manifests':eval_manifests,
        'ledger_raw_snapshot':ledger_snapshot,'live_ledger_modified_by_audit':False,
        'live_ledger_not_rehashed_while_controller_active':True,
        'other_completed_runs_checkpoint_hashes_repeated':False,
        'scientific_modules':science,'torch_checkpoint_loaded':False,
        'scientific_sources_plans_live_states_modified':False,
        'scientific_results_not_inferred_from_batch_metrics':True,
        'passed':True,
    }
    with output.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(json.dumps({'report':str(output),'sha256':sha(output),'completed_fit_count':len(accepted),'formal_evaluation_manifest_count':len(eval_manifests),'target_best_sha256':artifacts['best.pt']['sha256']},ensure_ascii=False))

if __name__ == '__main__':
    main()
