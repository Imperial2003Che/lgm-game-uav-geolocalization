"""Bounded read-only completion audit for one specified newly completed sensitivity fit.

No scientific libraries, checkpoint loading, GPU work, or live experiment writes.
The output identifies the SUES embedding-dimension-1024 seed-1 run; timestamps record actual capture.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
PATH_SHA = '11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1'
BASELINE_SHA = 'e5f1c6512f829a66e9dc73915627d985aec174dfe7f4226696b631298369bd05'
sys.path.insert(0, str(EXECUTION/'primary_path_repair_20260918'))
from project_paths import FrozenProjectPath
from source_contract import verify

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def check(value, message):
    if not value:
        raise RuntimeError(message)

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def record(path):
    path = Path(path)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}

def snapshot(source, destination):
    raw = Path(source).read_bytes()
    path = HERE/destination
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(raw)
    return json.loads(raw.decode('utf-8-sig')), {
        'source': str(source), 'snapshot': str(path), 'bytes': len(raw),
        'sha256': hashlib.sha256(raw).hexdigest(), 'captured_utc': now(),
    }

def main():
    output = HERE/'SUES_EMBED_DIM_1024_SEED1_COMPLETION.json'
    check(not output.exists(), 'Existing report must not be overwritten')
    check(Path(sys.executable).samefile(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe'), 'Wrong baseline interpreter')
    provenance = verify(PATH_SHA)
    baseline_path = EXECUTION/'completion_audits_20260928/ROOT_FIT_41_ADOPTION_20260928.json'
    check(sha(baseline_path) == BASELINE_SHA, 'Accepted baseline report changed')
    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
    baseline_ids = set(baseline['completed_fit_ids'])
    check(baseline['adopted'] and len(baseline_ids) == baseline['completed_fit_count'] == 41, 'Invalid accepted baseline')
    prior_report_path = EXECUTION/'completion_audits_20260928/SUES_EMBED_DIM_256_SEED1_COMPLETION.json'
    check(sha(prior_report_path) == '68d37cb7f5dc09d0dec190ac3c30fb128c01bb8de1a3c7f1101edfcdaa24541e', 'Previous independent report changed')
    prior_report = json.loads(prior_report_path.read_text(encoding='utf-8'))
    check(prior_report['batch_passed'] and set(prior_report['accepted_total_fit_ids']) == baseline_ids, 'Root accepted IDs differ from independent 41-fit report')
    baseline_reports = [record(prior_report_path)]
    derived_source = EXECUTION/'completion_audits_20260928/review_sues_embed_dim_256_seed1.py'
    check(sha(derived_source)=='074d249a71696f5a2e3fb3b77a0c044bdd0b1389652b2b2413adeb77ac031ab5', 'Reviewed derivation source changed')
    owner_reference = EXECUTION/'host_recovery_20260927_2145/OWNER_SNAPSHOT_20260928_133459473.json'
    check(sha(owner_reference)=='01f16a077b9d005322ffc739b30d97b7899db6bd5b6df663cf85f857d8c35d28', 'Root owner reference changed')
    root = FrozenProjectPath(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
    runner = root/'lgm_game_pytorch/experiments/run_frozen_formal_matrix.py'
    ledger_path = root/'lgm_game_pytorch/runs/frozen_formal_matrix_ledger.json'
    parent, parent_snapshot = snapshot(EXECUTION/'status.json', 'SUES_EMBED_DIM_1024_SEED1_PARENT_STATUS_RAW.json')
    ledger, ledger_snapshot = snapshot(ledger_path, 'SUES_EMBED_DIM_1024_SEED1_LEDGER_RAW.json')
    source_paths = {
        'runner_sha256': (runner, 'f251e5088b306ddec4769fab06799008d06194bc459282f2432ac3238f4ba59f'),
        'formal_script_sha256': (root/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py', '081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862'),
        'protocol_sha256': (root/'FORMAL_EXPERIMENT_PROTOCOL.md', '29c0502b07f09d45c6fd7d4a5b582fdd9a443acc9e8b818cd9941c18a0ee34f9'),
    }
    source_records = {}
    for key, (path, expected) in source_paths.items():
        source_records[key] = record(path)
        check(source_records[key]['sha256'] == expected == ledger[key], 'Frozen source changed: '+key)
    module_spec = importlib.util.spec_from_file_location('completion_audit_original_runner_sues_embed1024_seed1', runner)
    mod = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = mod
    module_spec.loader.exec_module(mod)
    mod.Path = FrozenProjectPath
    data = mod.dataset_specs(root, FrozenProjectPath(r'C:\项目\IMTMN\datasets\University-1652'), FrozenProjectPath(r'C:\项目\IMTMN\datasets\SUES-200'))
    specs = mod.main_run_specs(root, mod.DATASETS, mod.MAIN_VARIANTS, mod.MAIN_SEEDS)+mod.sensitivity_run_specs(root, mod.DATASETS)
    check(len(specs) == 42, 'Wrong original spec count')
    registry_sha = mod.registry_sha256(specs)
    check(registry_sha == ledger['registered_registry_sha256'], 'Registry changed')
    frozen_inputs = {name:{'data_root':str(d.data_root),'evidence_path':str(d.evidence),'evidence_sha256':d.evidence_sha256} for name,d in data.items()}
    check(frozen_inputs == ledger['frozen_inputs'], 'Frozen inputs changed')
    spec_by_path = {Path(s.run_dir):s for s in specs}
    spec_by_id = {s.identifier:s for s in specs}
    check(baseline_ids <= set(spec_by_id), 'Baseline IDs outside original registry')
    requested = {'formal_sensitivity/sues200/full/seed_1/resnet18/dim_1024'}
    target_specs = [s for s in specs if s.identifier in requested]
    check(len(target_specs) == 1 and target_specs[0].family == 'formal_sensitivity', 'Requested sensitivity target unavailable')
    targets = {s.identifier for s in target_specs}
    check(not targets & baseline_ids, 'Target accidentally repeats an accepted checkpoint')
    completed_events = {}
    unmatched_events = []
    for event in parent.get('events', []):
        if event.get('status') != 'completed' or event.get('exit_code') != 0:
            continue
        spec = spec_by_path.get(Path(event.get('output_dir','')))
        if spec is None:
            unmatched_events.append(event)
            continue
        check(spec.identifier not in completed_events, 'Duplicate completed run event: '+spec.identifier)
        completed_events[spec.identifier] = event
    check(targets <= set(completed_events), 'Some requested targets lack parent exit0 events')
    check(parent.get('controller_pid') == 16412, 'Different parent; root must inspect identity')

    check(completed_events[target_specs[0].identifier]['pid']==19004, 'Unexpected completed launcher')
    old_pids = [19004,31612]
    ps = "@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -in @("+','.join(map(str,old_pids))+") } | Select-Object ProcessId,Name,ParentProcessId,@{n='CreationDate';e={$_.CreationDate.ToString('o')}},CommandLine) | ConvertTo-Json -Compress"
    raw = subprocess.check_output(['powershell.exe','-NoProfile','-Command',ps], encoding='utf-8', errors='replace').strip()
    cim_rows = json.loads(raw) if raw else []
    if isinstance(cim_rows,dict):
        cim_rows = [cim_rows]
    pid_rows = {int(row['ProcessId']):row for row in cim_rows}
    pid_captured_at = now()
    findings = []
    rows = []
    for s in target_specs:
        event = completed_events[s.identifier]
        command = event['command']
        def arg(name):
            return command[command.index(name)+1]
        check(command[0] == r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe', 'Wrong event interpreter')
        check(Path(command[1]).samefile(EXECUTION/'primary_path_repair_20260918/run_formal_worker.py'), 'Wrong event worker')
        check(arg('--path-compat-sha256') == PATH_SHA and 'train' in command, 'Wrong event registration')
        for key,value in {'--dataset':s.dataset,'--variant':s.variant,'--seed':str(s.seed),'--epochs':'80','--workers':'8','--identities-per-batch':'16','--instances-per-identity':'4','--resume':'none','--backbone':'resnet18','--embed-dim':'1024'}.items():
            check(arg(key) == value, 'Changed event parameter '+s.identifier+' '+key)
        check(Path(arg('--output-dir')) == Path(s.run_dir), 'Wrong event output')
        issues = mod.training_completion_issues(s,data[s.dataset],ledger['formal_script_sha256'])
        check(not issues, 'Original completion validator: '+s.identifier+' '+str(issues))
        prefix = Path('raw_runs')/s.family/s.dataset/'embed_dim_1024'/f'seed_{s.seed}'
        manifest,mr = snapshot(s.run_dir/'run_manifest.json',prefix/'run_manifest.json')
        config,cr = snapshot(s.run_dir/'run_config.json',prefix/'run_config.json')
        history,hr = snapshot(s.run_dir/'history.json',prefix/'history.json')
        body = dict(manifest)
        manifest_sha = body.pop('payload_sha256')
        check(mod.canonical_sha256(body) == manifest_sha, 'Manifest canonical SHA mismatch')
        check(mod.canonical_sha256(config['immutable_config']) == config['run_config_sha256'] == manifest['run_config_sha256'], 'Configuration canonical SHA mismatch')
        check(manifest['status'] == 'completed' and manifest['epochs_completed'] == 80 and manifest['best_epoch'] == 79, 'Incomplete target manifest')
        check(len(history) == 80 and [h['epoch'] for h in history] == list(range(80)), 'Incomplete target history')
        steps = config['immutable_config']['optimization']['steps_per_epoch_actual']
        check(isinstance(steps,int) and steps > 0 and all(h['optimizer_steps'] == steps for h in history), 'Target steps differ from its original configuration')
        check(steps == 375, 'Frozen SUES training step count is not 375')
        check(all(h['examples_seen']==steps*64 and h['validation_selection_mAP'] is None and h['validation']=={} for h in history), 'Frozen examples/no-validation history contract differs')
        immutable=config['immutable_config']
        fingerprint_payload={'dataset':s.dataset,'data_root':immutable['data_root'],'image_inventory':immutable['image_inventory'],'train_ids_sha256':mod.canonical_sha256(immutable['train_ids']),'sues_manifest':immutable.get('sues_manifest'),'evidence_caches':immutable['evidence_caches']}
        fingerprint_sha=mod.canonical_sha256(fingerprint_payload)
        check(fingerprint_sha==ledger['dataset_fingerprints'][s.dataset]['sha256'], 'Original immutable dataset fingerprint differs from frozen ledger')
        artifacts = {}
        for name,declared in manifest['artifacts'].items():
            check(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe artifact name')
            artifacts[name] = record(s.run_dir/name)
            check(artifacts[name]['sha256'] == declared['sha256'] and artifacts[name]['bytes'] == declared['bytes'], 'Target full artifact hash mismatch: '+s.identifier+' '+name)
        check(set(artifacts) == {'run_config.json','history.json','last.pt','best.pt','run.log'}, 'Unexpected target inventory')
        check(artifacts['best.pt']['sha256'] == artifacts['last.pt']['sha256'], 'Final best/last differ')
        current = pid_rows.get(event['pid'])
        pid_class = 'not_present_at_cim_capture'
        if current:
            creation = datetime.datetime.fromisoformat(current['CreationDate'])
            finish = datetime.datetime.fromisoformat(event['finished_utc'])
            start = datetime.datetime.fromisoformat(event['started_utc'])
            if creation > finish:
                pid_class = 'pid_reused_for_process_created_after_original_finished'
            elif creation < start-datetime.timedelta(seconds=2):
                pid_class = 'pid_identifies_earlier_other_process_not_original_launch'
            else:
                pid_class = 'current_pid_identity_needs_root_review'
                findings.append({'run_identifier':s.identifier,'issue':'PID currently present with creation within old event interval; inspect exact identity.', 'current_process':current})
        rows.append({
            'run_identifier':s.identifier,'dataset':s.dataset,'variant':s.variant,'seed':s.seed,'family':s.family,'backbone':s.backbone,'embed_dim':s.embed_dim,
            'dataset_fingerprint_sha256':fingerprint_sha,
            'original_training_completion_issues':issues,'epochs_completed':80,'last_epoch':79,
            'optimizer_steps_each_epoch_from_original_config':steps,
            'manifest_payload_sha256':manifest_sha,'run_config_sha256':config['run_config_sha256'],
            'manifest_raw_snapshot':mr,'config_raw_snapshot':cr,'history_raw_snapshot':hr,
            'artifacts_sha256_verified':artifacts,'parent_completed_event':event,
            'launcher_pid_at_cim_capture':{'classification':pid_class,'current_process':current},
        })
    check(not cim_rows, 'Old training launcher or interpreter PID is present; root must examine identity before admission')
    completion_issues = {s.identifier:mod.training_completion_issues(s,data[s.dataset],ledger['formal_script_sha256']) for s in specs}
    accepted = [identifier for identifier,issues in completion_issues.items() if not issues]
    admitted = baseline_ids|targets
    check(admitted <= set(accepted), 'An already accepted or newly checked run failed current original completion gate')
    extra_accepted = sorted(set(accepted)-admitted)
    extra_events = sorted(set(completed_events)-admitted)
    eval_paths = [str(s.evaluation_dir/'evaluation_manifest.json') for s in specs if (s.evaluation_dir/'evaluation_manifest.json').is_file()]
    science = sorted(m for m in sys.modules if m.split('.')[0] in ('torch','numpy','PIL','torchvision','scipy','matplotlib'))
    check(not science, 'Scientific imports prohibited')
    result = {
        'schema':'bounded-parent-event-sensitivity-completion-review.v1','checked_utc':now(),
        'request_suffix_is_not_capture_time':True,'review_script':record(__file__),'derived_from_script':record(derived_source),'root_owner_reference':record(owner_reference),'executable':sys.executable,
        'source_provenance':provenance,'frozen_sources':source_records,'registered_registry_sha256':registry_sha,'frozen_inputs_match':True,
        'accepted_baseline_report':record(baseline_path),'baseline_completed_fit_count':41,'baseline_completed_fit_ids':sorted(baseline_ids),
        'accepted_baseline_independent_reports':baseline_reports,
        'parent_status_raw_snapshot':parent_snapshot,'ledger_raw_snapshot':ledger_snapshot,
        'parent_controller_pid_in_snapshot':parent['controller_pid'],
        'parent_completed_event_count_at_snapshot':len(completed_events),'unmatched_parent_events':unmatched_events,
        'requested_new_fit_count':1,'new_fits_fully_artifact_verified':len(rows),'new_runs':rows,
        'accepted_total_with_this_bounded_batch':len(admitted),'accepted_total_fit_ids':sorted(admitted),
        'original_42spec_completion_count_at_audit':len(accepted),'original_42spec_completed_ids_at_audit':accepted,
        'completed_outside_this_bounded_batch_pending_root_review':extra_accepted,
        'parent_completed_events_outside_this_batch_pending_root_review':extra_events,
        'formal_evaluation_manifest_count':len(eval_paths),'formal_evaluation_manifests':eval_paths,
        'evaluation_manifest_count_is_observation_only_not_acceptance':True,
        'evaluation_manifest_inventory_scope':'Original 42 spec.evaluation_dir paths under lgm_game_pytorch/evaluations; existence only, no evaluation validation.',
        'evaluations_accepted_by_this_train_audit':0,
        'cim_capture_utc':pid_captured_at,'current_processes_with_old_launcher_pid_numbers':cim_rows,'queried_old_launcher_and_interpreter_pids':old_pids,'old_launcher_and_interpreter_absent_at_cim':not cim_rows,
        'exit_evidence_basis':'Original parent monitored_run completed events with Popen returncode zero; PID presence/creation/command are a later point-in-time identity check.',
        'audit_independently_held_worker_process_handles':False,'audit_independently_observed_interpreter_exit_codes':False,
        'current_five_owner_and_active_pair_verification':'Root handles independently; not certified here.',
        'scientific_modules':science,'torch_checkpoint_loaded':False,'old_41_checkpoint_full_hashes_repeated':False,
        'live_ledger_rehashed_for_stability':False,'live_scientific_sources_states_ledger_modified':False,
        'scientific_results_not_inferred_from_batch_metrics':True,'training_total_seconds_not_used_as_full_resumed_run_efficiency':True,'concrete_identity_findings':findings,
        'batch_passed':not findings,'additional_completions_admitted_by_this_audit':False,
    }
    with output.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(json.dumps({'report':str(output),'report_sha256':sha(output),'script_sha256':sha(__file__),
        'new_fits_verified':len(rows),'accepted_total':len(admitted),'actual_42spec_complete':len(accepted),
        'eval_manifest_count':len(eval_paths),'extra_completed_pending_root_review':extra_accepted,
        'pid_identity_findings':findings,'steps_observed_by_dataset':{d:sorted({r['optimizer_steps_each_epoch_from_original_config'] for r in rows if r['dataset']==d}) for d in mod.DATASETS}},ensure_ascii=False))

if __name__ == '__main__':
    main()
