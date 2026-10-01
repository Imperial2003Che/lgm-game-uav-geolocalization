"""Derive the fixed SUES Full1 bounded audit from two accepted stdlib audit sources."""
import ast, difflib, hashlib, json
from pathlib import Path

HERE=Path(__file__).parent
EX=HERE.parent
PRIMARY=EX/'robustness_sues_visual_audit_20260929_1351/review_sues_visual1.py'
SECONDARY=EX/'robustness_full_audit_20260929_1247/review_full1.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PRIMARY)=='30e19aa18bb810604f06c8fb7b6c078d8330355a3e677972b2acc3df37ebdf0c'
assert sha(SECONDARY)=='e12125299612df0d68765b0ad744904a22015edd76a85b48a60759f3b3715d96'
original=PRIMARY.read_text(encoding='utf-8-sig')
full=SECONDARY.read_text(encoding='utf-8-sig')
s=original
def replace(old,new,count=None):
    global s
    actual=s.count(old)
    assert actual>0 and (count is None or actual==count),(old,actual,count)
    s=s.replace(old,new)

replace('SUES visual seed1','SUES full seed1',1)
replace('bounded-sues-visual1','bounded-sues-full1',1)
replace('sues200/visual/seed_1','sues200/full/seed_1')
replace('SUES Visual','SUES Full')
replace("'sues200','visual'","'sues200','full'",1)
replace("'ROOT_OFFICIAL42_AND_PIPELINE2_ADOPTION_20260929.json','ROOT_SUES_BATCH11_ADOPTION_20260929.json'","'ROOT_OFFICIAL42_AND_PIPELINE2_ADOPTION_20260929.json'",1)
replace("'657968ef1cf457bdc0b052c45cd0b2fd4f22dc687dc012d6f8482286e1fb052b'","'3b2bb1629f5b769fcd956c08068fa8ab2c947c9b36898a4bec2742e21110c17e'",1)
replace("official_root['independent_report']['sha256']==officialbind['sha256']","sum(r['sha256']==officialbind['sha256'] and norm(r['path'])==norm(officialbind['path']) for r in official_root['independent_evaluation_reports'])==1",1)
replace('Sep21 BATCH_COMPLETION_1611','Sep22 BATCH_COMPLETION_0944',1)
replace('specific SUES batch11 official/T3','specific SUES batch9-v2 official/T3',1)
replace("check(attempt['stderr']['bytes']==0,'Completed SUES Full stderr is empty')","check(attempt['stderr']['bytes']==325 and attempt['stderr']['sha256']=='939bd35cd671fbdb659d92ea4ee845dd030ef5930dbcf00ef8b97d4cd299d146','Completed SUES Full stderr contains the frozen slow-processor notice')",1)
replace('snapshot_20260929_135047460','snapshot_20260929_140746513',1)
replace('e5c4d484bdb7e703b373863b60fb02cdd3f372bf307559f0d00df96a5bc9d950','cb5c4691b59f450b3cbd80fe4d421646be30438b719feb9ba97c6ba270a5ed1c',1)
replace('@(24428,40060)','@(37764,14260)',1)
replace("{24428:'639262775229496270',40060:'639262775229943530'}","{37764:'639262807063561290',14260:'639262807063659250'}",1)
replace('d19283877ee9967fc36ca82155564cdc5945a44f7633273e119a661bf684f6d9','f5f1752ceb01cb8f9e28cf70712d8bd4f4045cbf1d44f53b4c07a7babf8f9f21',1)

start=full.index("    clip=json.loads((TREE/'clip_clean_reproduction_audit.json')")
end=full.index('\n    corepath=',start)
clipblock=full[start:end]
clipblock=clipblock.replace('d8788767a0bd22ef51e0b2a81218b762c5ede896e1668991caa9626b833db10c','3069fcb2b0a9a19f0a201bb2993ff5b31ab43f1377b96dddfed8440fda82c1c4')
clipblock=clipblock.replace('47b9e945ddb892048fa1fbcd0c5de69e89a5bb30b4809171ffa12fc5fcfd5c94','2247388d3bea3a99ebb79be71508bfb76c11d2d1aae3388b9bd22094c3655cd3')
nullblock="    check(manifest['clip_clean_reproduction_audit'] is None,'SUES Full intentionally does not initialize online CLIP')\n    check('clip_clean_reproduction_audit.json' not in artifacts,'SUES Full has no Full CLIP diagnostic artifact')\n"
replace(nullblock,clipblock,1)
start=full.index('    auditpaths=sorted(querypaths')
end=full.index('    check(canonical(querypaths)',start)
sampleblock=full[start:end].replace('039390fb104e00f586bf5a4858aa24675e2cd03f973c53588b2ec90f1e2bac13','8ddc20a8d0fdff79b435592f908e6000f922dd943638247fd644d18b5fb0b66d')
replace("    check(canonical(querypaths)==imm['query_path_membership_sha256']",sampleblock+"    check(canonical(querypaths)==imm['query_path_membership_sha256']",1)
replace("'not_used_by_visual_variant' if corrupted","'recomputed_from_corrupted_rgb_pixels' if corrupted",1)
replace('SUES Full clean/corrupt visual-only pixel pathway declarations','SUES Full clean-cache / corrupt-online pixel pathway declarations',1)
replace('historical independent Sep21 batch member','historical independent Sep22 batch member',1)
old_limit="'SUES Full intentionally skips online CLIP and has null clean reproduction audit. This does not establish any Full cached/online equivalence, Full corruption result or full-dataset onlineCLIP accuracy/efficiency.'"
new_limit="'Full64-sample CLIP diagnostic has no original numerical tolerance gate. Bound numerical errors are producer observations, not independent remeasurement, bitwise equivalence or a calibrated probability test. Clean cached evidence versus corrupted online CLIP mixes evidence-path and pixel-corruption effects; this is not a pure-corruption estimate or full-dataset onlineCLIP accuracy/efficiency measurement.'"
replace(old_limit,new_limit,1)
replace('Only SUES Full seed1 is accepted; no across-seed robustness SD/significance or whole4-run pipeline completion. No SUES Full result is included.','Only SUES Full seed1 is accepted by this audit; no across-seed robustness SD/significance or independent whole4-run pipeline completion is inferred. Earlier adopted runs are not re-audited here.',1)

ast.parse(s)
assert 'sues200/visual/seed_1' not in s
assert "('sues200','visual'" not in s
assert 'SUES Visual' not in s
assert "clip_clean_reproduction_audit'] is None" not in s
assert 'not_used_by_visual_variant' not in s
assert "len(task_reviews)==248 and len(all_summary)==1440" in s
target=HERE/'review_sues_full1.py'
with target.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
diff=''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile=str(PRIMARY),tofile=str(target)))
dp=HERE/'SUES_FULL_FROM_SUES_VISUAL_SOURCE_DIFF.patch'
with dp.open('x',encoding='utf-8',newline='\n') as f:f.write(diff)
record=dict(primary=dict(path=str(PRIMARY),sha256=sha(PRIMARY)),secondary=dict(path=str(SECONDARY),sha256=sha(SECONDARY)),
    derived=dict(path=str(target),sha256=sha(target)),complete_diff=dict(path=str(dp),sha256=sha(dp)),
    scope='Only sues200/full/seed_1, 30 corrupted conditions, 240 corrupted tasks and 8 clean tasks.',
    derivation='SUES Visual protocol, typed NPZ, dtype/CSV/coverage checks retained. Own Sep22 training member/ROOT42 ancestry and official batch9-v2 root edge bound. University Full CLIP diagnostic and deterministic path sample blocks transplanted with exact own SUES pins; no model execution.',
    first_execution_pending=True,old_audits_rerun=False,scientific_source_modified=False)
with (HERE/'DERIVATION.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps(record,ensure_ascii=True))
