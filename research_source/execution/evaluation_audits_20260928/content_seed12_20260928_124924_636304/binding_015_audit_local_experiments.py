"""Read-only local evidence audit; does not import torch or start jobs."""
import csv, datetime, hashlib, importlib.util, json, sys
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent
OLD = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
NEW = Path(r'C:\项目\LGM-GAME-TGRS-Submission-20260824-v1.5.0')
RUNNER = OLD / 'lgm_game_pytorch/experiments/run_frozen_formal_matrix.py'
spec = importlib.util.spec_from_file_location('frozen_audit_runner', RUNNER)
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)

def jload(p, default=None):
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.is_file() else default

def sha(p):
    return runner.sha256_file(p)

def metadata(p, hash_file=False):
    r = {'path': str(p), 'exists': p.is_file()}
    if p.is_file():
        s = p.stat()
        r.update(bytes=s.st_size, modified_local=datetime.datetime.fromtimestamp(s.st_mtime).isoformat())
        if hash_file: r['sha256'] = sha(p)
    return r

script_sha = sha(OLD / 'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py')
datasets = runner.dataset_specs(OLD, Path(r'C:\项目\IMTMN\datasets\University-1652'), Path(r'C:\项目\IMTMN\datasets\SUES-200'))
specs = runner.main_run_specs(OLD, runner.DATASETS, runner.MAIN_VARIANTS, runner.MAIN_SEEDS) + runner.sensitivity_run_specs(OLD, runner.DATASETS)
rows = []
for item in specs:
    directory = item.run_dir
    manifest = jload(directory / 'run_manifest.json', {})
    config = jload(directory / 'run_config.json', {})
    history = jload(directory / 'history.json', [])
    issues = runner.training_completion_issues(item, datasets[item.dataset], script_sha)
    artifacts = []
    for name in ('run_config.json','history.json','best.pt','last.pt','run.log'):
        p = directory / name
        m = metadata(p, p.is_file())
        declared = manifest.get('artifacts',{}).get(name,{}).get('sha256')
        if declared:
            m['declared_sha256'] = declared
            m['declared_hash_match'] = m.get('sha256') == declared
            if not m['declared_hash_match']: issues.append(f'actual SHA-256 mismatch: {name}')
        counterpart = NEW / p.relative_to(OLD)
        m['delivery_copy_path'] = str(counterpart)
        m['delivery_copy_equal'] = counterpart.is_file() and p.is_file() and counterpart.stat().st_size == p.stat().st_size and sha(counterpart) == m.get('sha256')
        artifacts.append(m)
    evaluation = item.evaluation_dir / 'evaluation_manifest.json'
    row = {'identifier':item.identifier,'family':item.family,'dataset':item.dataset,'variant':item.variant,'seed':item.seed,'backbone':item.backbone,'embed_dim':item.embed_dim,
           'run_dir':str(directory),'evaluation_dir':str(item.evaluation_dir),'manifest_status':manifest.get('status','absent'),
           'training_admissible':not issues,'training_issues':issues,'history_epochs':len(history),'last_history_epoch':history[-1].get('epoch') if history else None,
           'elapsed_training_seconds':manifest.get('total_training_seconds'),'evaluation_manifest_exists':evaluation.is_file(),
           'scientific_config':{k:config.get('immutable_config',{}).get(k) for k in ('dataset','model','optimization','selection','seed','protocol','code_sha256')},
           'artifacts':artifacts}
    rows.append(row)

ledger_path = OLD / 'lgm_game_pytorch/runs/frozen_formal_matrix_ledger.json'
ledger = jload(ledger_path,{})
key_hashes = {str(p.relative_to(OLD)): sha(p) for p in [RUNNER,OLD/'FORMAL_EXPERIMENT_PROTOCOL.md',OLD/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py']}
ledger_checks = {
 'runner_sha256_matches':sha(RUNNER)==ledger.get('runner_sha256'),
 'protocol_sha256_matches':sha(OLD/'FORMAL_EXPERIMENT_PROTOCOL.md')==ledger.get('protocol_sha256'),
 'formal_script_sha256_matches':script_sha==ledger.get('formal_script_sha256'),
 'registered_matrix_sha256_matches':runner.registry_sha256(specs)==ledger.get('registered_registry_sha256')}
cache = []
for name, ds in datasets.items():
    meta = ds.evidence.with_suffix('.meta.json')
    cache.append({'dataset':name,'data_root':str(ds.data_root),'evidence':metadata(ds.evidence,True),'metadata':metadata(meta,True),'content':jload(meta,{}),'frozen_hash_match':ds.evidence_sha256==ledger.get('frozen_inputs',{}).get(name,{}).get('evidence_sha256')})

formal_stats = {'expected_main':36,'expected_sensitivity':6,'admissible_training':sum(x['training_admissible'] for x in rows),'partial_training':sum(x['manifest_status']=='running' for x in rows),'not_started':sum(x['manifest_status']=='absent' for x in rows),'evaluation_manifest_count':sum(x['evaluation_manifest_exists'] for x in rows)}
payload = {'audit_time_local':datetime.datetime.now().astimezone().isoformat(),'method':'Filesystem and JSON/CSV read-only audit, with streamed SHA-256 of all available training artifacts; no training or checkpoint deserialization.',
 'authoritative_root':str(OLD),'delivery_root_compared':str(NEW),'formal_summary':formal_stats,'ledger_checks':ledger_checks,'entrypoint_hashes':key_hashes,'runs':rows,'evidence_caches':cache}
(OUT/'experiment_inventory.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'formal_summary':formal_stats,'ledger_checks':ledger_checks,'available':[{k:r[k] for k in ('identifier','manifest_status','training_admissible','training_issues','history_epochs','elapsed_training_seconds')} for r in rows if r['manifest_status']!='absent']},ensure_ascii=False,indent=2))
