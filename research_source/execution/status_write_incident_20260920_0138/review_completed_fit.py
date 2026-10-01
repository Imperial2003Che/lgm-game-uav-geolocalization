"""Read-only completion audit after the detached Windows worker's observed exit."""
import datetime, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent
sys.path.insert(0, str(EXEC / 'primary_path_repair_20260918'))
from project_paths import FrozenProjectPath
from source_contract import verify

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def record(p):
    p = Path(p)
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def check(condition, message):
    if not condition:
        raise RuntimeError(message)

def main():
    provenance = verify('11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1')
    check(sha(HERE/'CAPTURE.json') == '48b8688111e0ca5dfeab86b4e1815d86fcff9a1d7fdd75ee2726d0cb455fa956', 'Capture changed')
    started = read(HERE/'OBSERVER_STARTED.json')
    receipt = read(HERE/'OBSERVED_EXIT.json')
    check(started['source_sha256'] == sha(HERE/'observe_detached_train.py') == '8b5f331e041b6b4f2f8e34faa837e6b339b189b8b3bfd5571e5c4559bf453f17', 'Observer source changed')
    check(started['capture_sha256'] == sha(HERE/'CAPTURE.json'), 'Observer capture mismatch')
    check(receipt['processes'] == started['processes'] and receipt['pid'] == started['pid'], 'Observed identities mismatch')
    check(receipt['both_exited_zero'] is True and set(receipt['actual_exits']) == {'7176', '29512'}, 'Both actual exit receipts required')
    check(all(row['exit_code'] == 0 for row in receipt['actual_exits'].values()), 'Nonzero actual exit')
    for row in receipt['run_files_after_exit'].values():
        check(record(row['path']) == row, 'Post-exit artifact changed: '+row['path'])
    for row in read(HERE/'CAPTURE.json')['preserved']:
        check(sha(row['copy']) == row['sha256'] == sha(row['source']), 'Incident source changed')
    ps = "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\\.exe$' } | Select-Object ProcessId,ParentProcessId,@{n='CreationDate';e={$_.CreationDate.ToString('o')}},CommandLine) | ConvertTo-Json -Compress"
    raw = subprocess.check_output(['powershell.exe','-NoProfile','-Command',ps], encoding='utf-8', errors='replace')
    processes = json.loads(raw or '[]')
    if isinstance(processes, dict): processes = [processes]
    own = next(p for p in processes if p['ProcessId'] == os.getpid())
    allowed = {os.getpid(), own['ParentProcessId']}
    check(all(p['ProcessId'] in allowed and 'review_completed_fit.py' in p['CommandLine'] for p in processes), 'Other Python still live')
    root = FrozenProjectPath(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
    runner = root/'lgm_game_pytorch/experiments/run_frozen_formal_matrix.py'
    ledger_path = root/'lgm_game_pytorch/runs/frozen_formal_matrix_ledger.json'
    ledger_before = sha(ledger_path)
    ledger = read(ledger_path)
    for key, p in [('runner_sha256',runner),('formal_script_sha256',root/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py'),('protocol_sha256',root/'FORMAL_EXPERIMENT_PROTOCOL.md')]:
        check(sha(p) == ledger[key], 'Frozen source mismatch '+key)
    spec = importlib.util.spec_from_file_location('audit_frozen_runner', runner)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.Path = FrozenProjectPath
    data = mod.dataset_specs(root, FrozenProjectPath(r'C:\项目\IMTMN\datasets\University-1652'), FrozenProjectPath(r'C:\项目\IMTMN\datasets\SUES-200'))
    specs = mod.main_run_specs(root, mod.DATASETS, mod.MAIN_VARIANTS, mod.MAIN_SEEDS)+mod.sensitivity_run_specs(root, mod.DATASETS)
    check(mod.registry_sha256(specs) == ledger['registered_registry_sha256'], 'Registry mismatch')
    frozen_inputs = {name:{'data_root':str(d.data_root),'evidence_path':str(d.evidence),'evidence_sha256':d.evidence_sha256} for name,d in data.items()}
    check(frozen_inputs == ledger['frozen_inputs'], 'Frozen inputs mismatch')
    target = next(s for s in specs if s.family=='formal_main' and s.dataset=='university1652' and s.variant=='visual_style' and s.seed==2)
    issues = mod.training_completion_issues(target,data[target.dataset],ledger['formal_script_sha256'])
    check(issues == [], 'Original completion validator: '+str(issues))
    manifest = read(target.run_dir/'run_manifest.json')
    artifacts = {}
    for name, row in manifest['artifacts'].items():
        artifacts[name] = record(target.run_dir/name)
        check(artifacts[name]['sha256']==row['sha256'] and artifacts[name]['bytes']==row['bytes'], 'Full artifact hash mismatch '+name)
    accepted = [s.identifier for s in specs if not mod.training_completion_issues(s,data[s.dataset],ledger['formal_script_sha256'])]
    eval_manifests = [str(s.evaluation_dir/'evaluation_manifest.json') for s in specs if (s.evaluation_dir/'evaluation_manifest.json').exists()]
    check(len(accepted)==14 and not eval_manifests, 'Unexpected matrix totals require review')
    check(sha(ledger_path)==ledger_before, 'Audit changed ledger')
    science = [m for m in sys.modules if m.split('.')[0] in ('torch','numpy','PIL','torchvision','scipy','matplotlib')]
    check(not science, 'Scientific library unexpectedly imported')
    result = {'schema':'detached-fit-completion-review.v1','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'review_script':record(__file__),'executable':sys.executable,'source_provenance':provenance,
      'observer_started':record(HERE/'OBSERVER_STARTED.json'),'observed_exit':record(HERE/'OBSERVED_EXIT.json'),
      'capture':record(HERE/'CAPTURE.json'),'actual_exits':receipt['actual_exits'],
      'python_processes_at_audit':processes,'only_audit_python_live':True,'original_owner_and_observer_absent':True,
      'run_identifier':target.identifier,'run_dir':str(target.run_dir),'original_training_completion_issues':issues,
      'epochs_completed':manifest['epochs_completed'],'last_epoch':manifest['best_epoch'],'artifacts_sha256_verified':artifacts,
      'run_manifest':record(target.run_dir/'run_manifest.json'),'completed_fit_count':len(accepted),'completed_fit_ids':accepted,
      'formal_evaluation_manifest_count':len(eval_manifests),'ledger':record(ledger_path),'ledger_unchanged':True,
      'scientific_modules':science,'scientific_results_not_inferred_from_batch_metrics':True,'passed':True}
    output=HERE/'COMPLETED_FIT_REVIEW_20260920.json'
    with output.open('x',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'report':str(output),'sha256':sha(output),'completed_fit_count':len(accepted),'formal_evaluation_count':0}))

if __name__ == '__main__': main()
