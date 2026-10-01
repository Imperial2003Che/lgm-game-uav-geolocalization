"""Small-file, standard-library contract review; never executes scientific code."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
PKG = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch')
OUT = Path(__file__).parent
RUN = PKG / 'runs/formal_robustness/sues200/visual/seed_1'
ID = 'formal_main/sues200/visual/seed_1/resnet18/dim_512'
BINDINGS = []

def read(path, expected=None):
    path = Path(path)
    assert path.suffix in ('.py', '.json', '.md', '.yaml', '.log')
    assert path.stat().st_size < 1_000_000
    data = path.read_bytes()
    h = hashlib.sha256(data).hexdigest()
    assert expected is None or h == expected, str(path)
    BINDINGS.append(dict(path=str(path), bytes=len(data), sha256=h))
    return data

def jread(path, expected=None):
    return json.loads(read(path, expected))

def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), default=str).encode('utf-8')).hexdigest()

def save(name, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with (OUT / name).open('xb') as f:
        f.write(data)
    return dict(path=str(OUT / name), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

config = jread(RUN / 'run_config.json')
ci = config['immutable_config']
manifest = jread(RUN / 'robustness_manifest.json', '2828ab1bac3b49297ec41d3500825e23a8c4f339c00c4934f8112f209cc8f952')
assert canonical(ci) == config['run_config_sha256'] == manifest['run_config_sha256'] == 'd19283877ee9967fc36ca82155564cdc5945a44f7633273e119a661bf684f6d9'
assert manifest['status'] == 'completed' and manifest['dataset'] == 'sues200' and manifest['variant'] == 'visual'
assert canonical({k:v for k,v in manifest.items() if k != 'payload_sha256'}) == manifest['payload_sha256']
assert manifest['expected_corruption_conditions'] == manifest['completed_corruption_conditions'] == 30
assert manifest['condition_count_complete'] and manifest['clip_clean_reproduction_audit'] is None
assert not (RUN / 'clip_clean_reproduction_audit.json').exists()
assert ci['checkpoint'] == manifest['checkpoint'] and ci['checkpoint']['seed'] == 1
assert ci['unique_query_images'] == 16080 and ci['unique_clean_gallery_images'] == 40200
assert ci['image_inventory']['file_count'] == 40200

sources = {
    'experiments/run_frozen_robustness_matrix.py':'7d4be61b772f41853d7407c703af3ec11cbeca762947b53100f78a13266ff574',
    'experiments/run_image_level_robustness.py':'4f33b8aa96fb7d046f570bc65cce36bdb3c47b1875395b11b1565f2dd71c167a',
    'experiments/formal_robustness_common.py':'58bc704cb8c00ceac356c338978e5b3a2324f8743b3a0bff1009b90c9327d01e',
    'lgm_game_pytorch/formal_retrieval.py':'081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862',
}
source_data = {p:read(PKG / p, h).decode('utf-8-sig') for p,h in sources.items()}
core_tree = ast.parse(source_data['lgm_game_pytorch/formal_retrieval.py'])
train_tuple = next(ast.literal_eval(n.value) for n in core_tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SUES_OFFICIAL_TRAIN_IDS' for t in n.targets))
split = read(PKG / 'manifests/sues200_official_train_ids.yaml','c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226').decode()
train_ids = tuple(re.findall(r'^\s*-\s*"(\d{4})"\s*$', split, re.M))
assert train_ids == train_tuple and len(set(train_ids)) == 120
assert len({f'{i:04d}' for i in range(1,201)} - set(train_ids)) == 80
scales = {}
for height in (150,200,250,300):
    scales[f'sues200_uav_{height}m_to_satellite'] = (4000,200,80,200)
    scales[f'sues200_satellite_to_uav_{height}m'] = (80,10000,80,200)
assert set(scales) == set(ci['official_task_scale'])
for task, expected in scales.items():
    row = ci['official_task_scale'][task]
    assert tuple(row[k] for k in ('queries','gallery','query_identities','gallery_identities')) == expected

t3root = jread(EX / 'transfer_audit_20260929_0647/ROOT_TRANSFER12_AND_NATIVE2_ADOPTION.json','fb7588357afa3e225b67088437233db397c067131fb8bc6adf97ce9ccbdd3bdd')
t3 = jread(t3root['independent_transfer_review']['path'],'b0627920c9e8ab1da0dbc6d2d48795b3abe68cf3b79f7d7dba7afa9bba3847c7')
prior = next(x for x in t3['runs'] if x['source_training_identifier'] == ID)
authority = prior['source_training_authority']
training = jread(authority['report_path'], 'f88259d145316e76b36f63130800f2a47f91c0cbdf863fd9cabb2381bbca0bb2')
assert training['batch_passed']
tr = next(x for x in training['new_runs'] if x['run_identifier'] == ID)
assert tr['epochs_completed'] == 80 and tr['original_training_completion_issues'] == []
best = tr['artifacts_sha256_verified']['best.pt']
assert best['bytes'] == 140607467 and best['sha256'] == prior['inherited_checkpoint_SHA'] == ci['checkpoint']['checkpoint_sha256']
assert tr['run_config_sha256'] == ci['checkpoint']['training_run_config_sha256']
assert tr['manifest_raw_snapshot']['sha256'] == ci['checkpoint']['training_manifest_sha256']
root32 = jread(EX / 'completion_audits_20260922/ROOT_BATCH_32_ADOPTION_20260922.json')
assert root32['adopted'] and ID in root32['completed_fit_ids']
assert any(x['sha256'] == authority['report_sha256'] and x['path'] == authority['report_path'] for x in root32['verified_small_evidence_bindings'])
official = jread(prior['source_adoption_metadata']['path'],'78b187ce0388f5d8d28ebcb7139039059cf897eb574051c38ee50e72a60e6a1a')
of = next(x for x in official['runs'] if x['identifier'] == ID)
assert of['inherited_checkpoint_SHA']['specific_training_authority'] == authority
assert of['inherited_checkpoint_SHA']['specific_historical_artifact'] == best
officialroot = jread(prior['source_adoption_metadata']['parent'],'657968ef1cf457bdc0b052c45cd0b2fd4f22dc687dc012d6f8482286e1fb052b')
assert officialroot['independent_report']['sha256'] == '78b187ce0388f5d8d28ebcb7139039059cf897eb574051c38ee50e72a60e6a1a'

obsdir = EX / 'robustness_observation_20260929_0647/snapshot_20260929_135047460'
obs = jread(obsdir / 'OBSERVATION.json','e5c4d484bdb7e703b373863b60fb02cdd3f372bf307559f0d00df96a5bc9d950')
ledger = jread(obsdir / 'frozen_robustness_matrix_ledger.json','222ef32f96e6327d6efe0a33f1125d7d27f50d5db379a52995bf88273dc35060')
record = ledger['runs']['sues200/visual/seed_1']
spec = next(x for x in ledger['immutable_config']['registered_runs'] if x['identifier'] == 'sues200/visual/seed_1')
assert record['status'] == 'completed_and_verified' and len(record['attempts']) == 1
attempt = record['attempts'][0]
assert attempt['returncode'] == 0 and attempt['command'] == spec['command']
for label in ('stdout','stderr'):
    d = attempt[label]
    assert len(read(d['path'],d['sha256'])) == d['bytes']
assert attempt['stdout']['bytes'] == 31150 and attempt['stderr']['bytes'] == 0
oldobs = jread(EX / 'robustness_observation_20260929_0647/snapshot_20260929_130251128/OBSERVATION.json','a1fccfc9fcfed4168e9ca4b0f8ef749c50098b766a6eaef55898b106a45b9dd6')
old_pair = oldobs['robustness']['worker_pair']
assert [(x['pid'],x['creation_utc_ticks']) for x in old_pair] == [(24428,639262775229496270),(40060,639262775229943530)]
assert old_pair[0]['command'] == subprocess.list2cmdline(attempt['command'])
prior_contract = jread(EX / 'robustness_audit_20260929_0946/contract_review/CONTRACT_REVIEW.json','ebb07c9957ad985c1e9a3702ab76803db6d2918557d7076da0ac8c4277691dc7')
cim = jread(OUT / 'CURRENT_OLD_PID_OBSERVATION.json')
for p in cim['processes']:
    p['matches_original_identity'] = any(p['pid']==o['pid'] and int(p['creation_utc_ticks'])==o['creation_utc_ticks'] for o in old_pair)

result = dict(schema='lgm.sues-visual1-robustness-small-contract-review.v1',reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    reviewer='/root/sep29_recovery_review',conclusion='Small-file source and completed-run contracts are consistent; full artifact audit and root adoption are separate.',
    scope=dict(dataset='sues200',variant='visual',seed=1,conditions=30,corrupted_tasks=240,clean_tasks=8,query_array_sets_expected=248,summary_rows_expected=1440),
    canonical_config_sha256=config['run_config_sha256'],inherited_checkpoint=best,training_authority=authority,
    protocol=dict(heights_metres=[150,200,250,300],train_ids=120,test_ids=80,task_scales=scales,unique_queries=16080,unique_clean_gallery_images=40200),
    parent_completion=attempt,old_identity=old_pair,current_old_numeric_pid_observation=cim,
    source_contract_findings=[
        'The fixed 120 IDs are identical to the original embedded ordered split; the 80-ID complement supplies queries. Each height retains all 200 gallery identities, including training identities as prescribed by the frozen official protocol.',
        'Four 4000-UAV-query to 200-satellite-gallery tasks and four 80-satellite-query to 10000-UAV-gallery tasks are separate tasks. Query union is 16080; clean gallery and total used image union are 40200. Shared satellite images are not multiplied in unique-image coverage.',
        'Visual encodes RGB through its normalized visual branch and ignores content/style input tensors. Clean/corrupted code may fetch cached probabilities, but no online CLIP encoder or clean CLIP reproduction audit is instantiated for Visual; null diagnostic is expected, not missing evidence.',
        'Only decoded query pixels are corrupted; every condition reuses the clean gallery. Float32 dot-product scores use stable descending sort over each complete task gallery; AP is the official trapezoidal convention.',
        'Metric degradation is clean minus corrupt; percentage-point drop is 100 times that difference; relative drop is divided by clean only when nonzero. Saved query deltas use corrupted minus clean and correctness transitions use signed int8.',
        'The original completion gate requires completed payload/config/source/provenance, 30 conditions, exact fixed task scales, coverage, expected artifact and query evidence. Known gate coverage gaps remain addressed by the separate artifact auditor, not by edits to frozen source.',
        'SUES Visual uses its own Sep21 batch completion row and fresh-at-that-time best.pt descriptor, directly bound by ROOT_BATCH_32 and inherited via adopted official SUES_BATCH11/T3. It does not use University Full authority or the initial Visual inventory.',
    ],limits=[
        'Only small files and source text were read. No original validator or audit candidate, NumPy, torch, GPU, model, image, cache NPZ or checkpoint byte read was executed in this contract review.',
        'Current checkpoint bytes are not verified here; historical checkpoint SHA and cache/image content SHA are inherited. Metadata stability and producer declarations are not current-byte or rerun proofs.',
        'ROOT42/T3 prior chain acceptance and historically disclosed unrelated chain gaps are inherited; this supplement confirms the direct ROOT32/training report and exact corresponding official/T3 source row without rerunning previous audits.',
        'No 248-array scientific artifact audit, pixel/feature reconstruction, full ranking, all-positive-rank AP reconstruction, three-seed SD or statistical significance is claimed.',
        'Original parent subprocess.run return0, closed logs, historical exact process identity and subsequent CIM presence/absence are distinct from independently held launcher/interpreter exit handles.',
    ],bindings=BINDINGS,scientific_imports=[],checkpoint_cache_image_bytes_read=0,scientific_acceptance=False,root_adoption=False,live_state_modified=False)
read(__file__)
print(json.dumps(save('SUES_VISUAL_CONTRACT_REVIEW.json',result)))
