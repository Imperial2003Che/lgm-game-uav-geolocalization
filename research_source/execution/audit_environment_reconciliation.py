"""Read original manifests/configs and package source evidence; never import models."""
from pathlib import Path
import ast
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
BACKUP = HERE / 'resume_backups/20260914_110612/lgm_game_pytorch/runs/formal_main/university1652/visual_style/seed_1'
EXPECTED = {'numpy':'2.4.4','Pillow':'12.2.0','torch':'2.11.0+cu126','torchvision':'0.26.0+cu126'}

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

rows=[]
for variant in ('content','style','visual','visual_content'):
    for seed in (1,2,3):
        folder=ROOT/f'lgm_game_pytorch/runs/formal_main/university1652/{variant}/seed_{seed}'
        mpath=folder/'run_manifest.json'
        cpath=folder/'run_config.json'
        manifest,config=load(mpath),load(cpath)
        packages=manifest.get('dependencies_and_device',{}).get('packages')
        config_packages=config.get('environment',{}).get('packages')
        rows.append({'variant':variant,'seed':seed,'status':manifest.get('status'),
                     'manifest_path':str(mpath),'manifest_sha256':sha(mpath),'manifest_packages':packages,
                     'config_path':str(cpath),'config_sha256':sha(cpath),'config_packages':config_packages,
                     'matches_original_four_versions':packages==EXPECTED and config_packages==EXPECTED})

backup_config=load(BACKUP/'run_config.json')
backup_manifest=load(BACKUP/'run_manifest.json')
backup={'directory':str(BACKUP),'config_sha256':sha(BACKUP/'run_config.json'),
        'manifest_sha256':sha(BACKUP/'run_manifest.json'),'config_environment':backup_config['environment'],
        'manifest_status':backup_manifest.get('status'),'manifest_dependencies_and_device':backup_manifest.get('dependencies_and_device')}

probes={}
for key,name in [('baselines','environment_baselines_probe.json'),('transactions_normal','environment_normal_probe.json'),
                 ('transactions_isolated','environment_isolated_probe.json'),('mccg_isolated','environment_mccg_probe.json')]:
    p=HERE/name
    probe=load(p)
    probes[key]={'evidence_path':str(p),'evidence_sha256':sha(p),'executable':probe['executable'],
                 'packages':{name:item['metadata_version'] for name,item in probe['packages'].items()},
                 'isolated':probe['isolated'],'PYTHONPATH':probe['PYTHONPATH'],'PYTHONHOME':probe['PYTHONHOME'],
                 'scientific_modules_imported':probe['scientific_modules_imported']}

core=ROOT/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py'
tree=ast.parse(core.read_text(encoding='utf-8'))
checkpoint=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='checkpoint_payload')
returned_dict=next(n for n in ast.walk(checkpoint) if isinstance(n,ast.Return) and isinstance(n.value,ast.Dict)).value
keys=[ast.literal_eval(k) for k in returned_dict.keys]
assert 'environment' not in keys and 'dependencies_and_device' not in keys

report={'status':'read_only_reconciled','completed_original_fits':rows,'epoch50_backup':backup,'interpreter_probes':probes,
        'all_12_original_fit_version_records_match':all(r['matches_original_four_versions'] for r in rows),
        'checkpoint_software_evidence':{'source':str(core),'source_sha256':sha(core),'function':'checkpoint_payload','line':checkpoint.lineno,
                                        'checkpoint_keys':keys,'conclusion':'Checkpoint payload does not store dependency versions; original run_config environment and completed manifest dependency records are the direct version evidence.'},
        'conclusion':'Transactions differs from the original recorded NumPy/Pillow versions in normal and isolated invocations. Both baselines and mccg metadata plus literal package version-source text match the original four versions. The selected formal/T2 interpreter is baselines.',
        'limit':'Matching four recorded package versions does not establish a byte-identical historical environment. No original scientific source, model, data, environment or running process was modified by this audit.'}
assert not any(n in sys.modules for n in ('torch','torchvision','numpy','PIL'))
(HERE/'environment_reconciliation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'original_fit_count':len(rows),'all_12_records_match':report['all_12_original_fit_version_records_match'],
                  'backup_versions':backup['config_environment']['packages'],'runtimes':probes},ensure_ascii=True,indent=2))
