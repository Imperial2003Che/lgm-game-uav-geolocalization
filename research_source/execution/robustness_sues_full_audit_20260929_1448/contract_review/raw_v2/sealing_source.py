"""Seal small-file contract/static review only; no scientific imports or artifact replay."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

EX=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
PKG=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch')
OUT=Path(__file__).parent
RUN=PKG/'runs/formal_robustness/sues200/full/seed_1'
ID='formal_main/sues200/full/seed_1/resnet18/dim_512'
B=[]
(OUT/'raw_v2').mkdir(exist_ok=True)

def bind(label,path,digest=None):
    p=Path(path)
    assert p.suffix in ('.py','.json','.md','.patch','.log') and p.stat().st_size<2_000_000
    data=p.read_bytes(); h=hashlib.sha256(data).hexdigest()
    assert digest is None or h==digest, str(p)
    s=OUT/'raw_v2'/(label+p.suffix)
    with s.open('xb') as f:f.write(data)
    d=dict(label=label,source=dict(path=str(p),bytes=len(data),sha256=h),snapshot=dict(path=str(s),bytes=len(data),sha256=h))
    B.append(d)
    return data,d
def j(label,path,digest=None):
    data,b=bind(label,path,digest);return json.loads(data),b
def can(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(name,obj):
    data=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
    with (OUT/name).open('xb') as f:f.write(data)
    return dict(path=str(OUT/name),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())

cfg,cb=j('run_config',RUN/'run_config.json'); im=cfg['immutable_config']
mf,mb=j('manifest',RUN/'robustness_manifest.json','19e8c7b0b9d929dd19b677f09459836542678f901641ff241ff31a967d906760')
assert can(im)==cfg['run_config_sha256']==mf['run_config_sha256']=='f5f1752ceb01cb8f9e28cf70712d8bd4f4045cbf1d44f53b4c07a7babf8f9f21'
assert can({k:v for k,v in mf.items() if k!='payload_sha256'})==mf['payload_sha256']
assert mf['dataset']=='sues200' and mf['variant']=='full' and mf['status']=='completed'
assert mf['expected_corruption_conditions']==mf['completed_corruption_conditions']==30 and mf['condition_count_complete']
assert im['unique_query_images']==16080 and im['unique_clean_gallery_images']==40200 and im['image_inventory']['file_count']==40200
assert im['checkpoint']==mf['checkpoint'] and im['checkpoint']['seed']==1
diag,db=j('clip_diagnostic',RUN/'clip_clean_reproduction_audit.json','2247388d3bea3a99ebb79be71508bfb76c11d2d1aae3388b9bd22094c3655cd3')
assert diag==mf['clip_clean_reproduction_audit'] and can({k:v for k,v in diag.items() if k!='payload_sha256'})==diag['payload_sha256']=='3069fcb2b0a9a19f0a201bb2993ff5b31ab43f1377b96dddfed8440fda82c1c4'
assert diag['samples']==64 and diag['selection_seed']==20260727 and diag['schema_version']==im['schema_version']
cache=im['evidence_caches'][0]; cm,cmb=j('cache_metadata',cache['meta_path'],cache['meta_sha256'])
prov=diag['clip_provenance']
assert prov['precision']==cm['hardware']['precision']==cm['run_configuration']['precision']=='fp16'
assert prov['model_name']==cm['model']['name']=='openai/clip-vit-base-patch32'
assert prov['revision']==prov['loaded_revision']==cm['model']['revision_requested']==cm['model']['revision_resolved']=='3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268'
for key in ('model_config_sha256','combined_candidates_sha256'):assert prov[key]==cm['hashes'][key]
assert prov['probability_semantics']==cm['probability_semantics'] and prov['local_files_only'] is True

tr,tb=j('t3_root',EX/'transfer_audit_20260929_0647/ROOT_TRANSFER12_AND_NATIVE2_ADOPTION.json','fb7588357afa3e225b67088437233db397c067131fb8bc6adf97ce9ccbdd3bdd')
t3,_=j('t3_report',tr['independent_transfer_review']['path'],'b0627920c9e8ab1da0dbc6d2d48795b3abe68cf3b79f7d7dba7afa9bba3847c7')
prior=next(r for r in t3['runs'] if r['source_training_identifier']==ID); authority=prior['source_training_authority']
training,_=j('specific_training',authority['report_path'],'2183ab32674d171f0d7ce15ea96b5e72b1990ad7071404e89403108f28f96a25')
rows=[r for r in training['new_runs'] if r['run_identifier']==ID];assert len(rows)==1
row=rows[0];best=row['artifacts_sha256_verified']['best.pt']
assert training['batch_passed'] and row['epochs_completed']==80 and row['original_training_completion_issues']==[] and row['optimizer_steps_each_epoch_from_original_config']==375
assert best['bytes']==172338603 and best['sha256']==prior['inherited_checkpoint_SHA']==im['checkpoint']['checkpoint_sha256']=='7478740b013990c83c5c21f619bc89b2664ee70ff90fda18ab3b7ac420c870e9'
assert row['run_config_sha256']==im['checkpoint']['training_run_config_sha256'] and row['manifest_raw_snapshot']['sha256']==im['checkpoint']['training_manifest_sha256']
r36,_=j('root36',EX/'completion_audits_20260922/ROOT_BATCH_36_ADOPTION_20260922.json','1c7bdd8e27328118789462a3db2f8283d6803e50c26a2914dd4674010ddf358f')
assert r36['adopted'] and ID in r36['completed_fit_ids'] and r36['independent_report']['sha256']==authority['report_sha256'] and r36['independent_report']['path']==authority['report_path']
official,ob=j('official_report',prior['source_adoption_metadata']['path'],'3cb6894e754bf9388519b5886491deca61e807472b7dbde9c2e93dd3ff65c074')
of=next(r for r in official['runs'] if r['identifier']==ID)
assert of['inherited_checkpoint_SHA']['specific_training_authority']==authority and of['inherited_checkpoint_SHA']['specific_historical_artifact']==best
oroot,_=j('official_root',prior['source_adoption_metadata']['parent'],'3b2bb1629f5b769fcd956c08068fa8ab2c947c9b36898a4bec2742e21110c17e')
assert sum(x['path']==ob['source']['path'] and x['sha256']==ob['source']['sha256'] for x in oroot['independent_evaluation_reports'])==1

ledger,lb=j('final_ledger',PKG/'runs/frozen_robustness_matrix_ledger.json')
run=ledger['runs']['sues200/full/seed_1'];spec=next(r for r in ledger['immutable_config']['registered_runs'] if r['identifier']=='sues200/full/seed_1')
assert run['status']=='completed_and_verified' and len(run['attempts'])==1 and run['robustness_manifest_sha256']==mb['source']['sha256']
attempt=run['attempts'][0];assert attempt['returncode']==0 and attempt['command']==spec['command']
for label in ('stdout','stderr'):
    data,_=bind('closed_'+label,attempt[label]['path'],attempt[label]['sha256']);assert len(data)==attempt[label]['bytes']
assert attempt['stderr']['bytes']==325 and attempt['stdout']['bytes']==31195
old,_=j('old_identity_snapshot',EX/'robustness_observation_20260929_0647/snapshot_20260929_140746513/OBSERVATION.json','cb5c4691b59f450b3cbd80fe4d421646be30438b719feb9ba97c6ba270a5ed1c')
pair=old['robustness']['worker_pair'];assert [(p['pid'],p['creation_utc_ticks']) for p in pair]==[(37764,639262807063561290),(14260,639262807063659250)]
assert pair[0]['command']==subprocess.list2cmdline(attempt['command'])
cim=json.loads(subprocess.run(['powershell','-NoProfile','-Command',"@{utc=[DateTime]::UtcNow.ToString('o');processes=@(Get-CimInstance Win32_Process|Where-Object {$_.ProcessId -in @(37764,14260)}|ForEach-Object {@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks.ToString();command=$_.CommandLine}})}|ConvertTo-Json -Depth 5 -Compress"],capture_output=True,text=True,check=True).stdout)
for p in cim['processes']:p['matches_original_identity']=any(p['pid']==x['pid'] and int(p['creation_utc_ticks'])==x['creation_utc_ticks'] for x in pair)
assert not any(p['matches_original_identity'] for p in cim['processes'])

sources={
'experiments/run_frozen_robustness_matrix.py':'7d4be61b772f41853d7407c703af3ec11cbeca762947b53100f78a13266ff574',
'experiments/run_image_level_robustness.py':'4f33b8aa96fb7d046f570bc65cce36bdb3c47b1875395b11b1565f2dd71c167a',
'experiments/formal_robustness_common.py':'58bc704cb8c00ceac356c338978e5b3a2324f8743b3a0bff1009b90c9327d01e',
'lgm_game_pytorch/formal_retrieval.py':'081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862'}
for i,(path,digest) in enumerate(sources.items()):bind('original_source_'+str(i),PKG/path,digest)
candidate,sb=bind('candidate',OUT.parent/'review_sues_full1.py','e6dc1126279ec05b40b89e279ae41a4863fbef0a88e0c7b87fd6d0a0febf9f13')
base,bb=bind('prior_sues_visual_source',EX/'robustness_sues_visual_audit_20260929_1351/review_sues_visual1.py','30e19aa18bb810604f06c8fb7b6c078d8330355a3e677972b2acc3df37ebdf0c')
def defs(data):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(data).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
assert defs(candidate)==defs(base)
bind('complete_diff',OUT.parent/'SUES_FULL_FROM_SUES_VISUAL_SOURCE_DIFF.patch','e8581e34b18519de920f6abf2be7c00e26dc7d1318557ce53df5fa7093a5096c')
bind('derivation',OUT.parent/'DERIVATION.json')
_,md=bind('review_markdown',OUT/'SUES_FULL_SOURCE_REVIEW.md')
_,selfbinding=bind('sealing_source',__file__)
limits=['Static and small-file review only; no original validator or candidate execution, scientific imports, NPZ review, GPU, model, weight/cache/image byte reading.','Current checkpoint bytes and cache/image content SHA are inherited; metadata is not proof of current bytes. Prior ROOT42/T3 chain acceptance and disclosed unrelated historical gaps remain inherited.','The 64-sample CLIP values are producer diagnostics with no numerical acceptance threshold, no bitwise/cache-online equivalence or negligible ranking-impact inference. Clean cached versus corrupted online evidence is not a pure pixel-corruption comparison.','Saved AP/RR checks do not rerun full rankings or AP from all positive ranks; producer coverage is not re-executed here. No three-seed robustness SD/significance.','Original parent return0, closed logs and absence of old exact identities do not establish independent dual-handle exit codes.','This review is not root adoption or whole-pipeline completion; later T6 failure remains separate and unresolved.']
report=dict(schema='lgm-game.independent-sues-full-robustness-contract-supplement.v1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewer='/root/sep29_recovery_review',status='small_file_full_contract_consistency_passed_with_inherited_limitations',scope=dict(dataset='sues200',variant='full',seed=1,conditions=30,corrupted_tasks=240,clean_tasks=8),source_and_small_file_bindings=B,review_markdown=md['source'],sealing_source=selfbinding['source'],specific_training_authority=authority,inherited_checkpoint=best,canonical_config_sha256=cfg['run_config_sha256'],manifest=mb['source'],clip_diagnostic=diag,clip_numerical_values_independently_recomputed=False,clip_threshold_gate=False,official_task_scales=im['official_task_scale'],parent_record=attempt,old_identity=pair,current_old_numeric_pid_observation=cim,interpretation_limits=limits,scientific_imports=[],scientific_acceptance=False,live_state_modified=False)
out=save('SUES_FULL_CONTRACT_REVIEW.json',report)
static=dict(schema='lgm-game.independent-sues-full-audit-source-static.v1',created_utc=report['created_utc'],reviewer=report['reviewer'],candidate=sb['source'],base=bb['source'],contract_report=out,review_markdown=md['source'],sealing_source=selfbinding['source'],complete_diff_read=True,top_level_functions_and_classes_unchanged=True,blocking_findings=[],verdict='No blocking source-adaptation issue found; only the bounded audit claims stated in the source are supported.',findings=['Specific Sep22 Full member and SUES batch9-v2 official report replace prior Visual authority; exact unique path/SHA official-root array edge checked.','Full non-null CLIP diagnostic and deterministic query-path sample contract replace Visual null gate; Full clean-cache/corrupt-online semantics explicit.','SUES four-height/all-200-gallery protocol and 248 array/1440 summary expectations retained.','Exact allowlisted inherited checkpoint SHA and rejection of other checkpoint accesses retained; no broad hash bypass.','Old process identity comparison uses exact UTC ticks and distinguishes reused numeric PID; no fabricated exit proof.'],interpretation_limits=limits,candidate_or_control_tests_executed=False,scientific_acceptance=False)
print(json.dumps([out,save('SUES_FULL_SOURCE_STATIC_REVIEW.json',static)],ensure_ascii=False))
