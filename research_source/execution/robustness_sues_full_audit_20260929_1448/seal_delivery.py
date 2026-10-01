"""Seal the completed fixed SUES Full1 audit without rerunning its checks."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

HERE=Path(__file__).parent
def bind(path,expected=None):
    path=Path(path);data=path.read_bytes();sha=hashlib.sha256(data).hexdigest()
    assert expected is None or expected==sha,(path,expected,sha)
    return dict(path=str(path),sha256=sha,bytes=len(data))
rp=HERE/'a1/REVIEW.json'
rb=bind(rp,'3cfaf28ba6caa7d0c12bcf65853dbb1c1a918363216287a6baf1d2c31b9abb78')
r=json.loads(rp.read_text(encoding='utf-8'))
assert r['passed_with_stated_limits'] and r['original_completion_issues']==[] and r['scientific_modules']==[]
assert (r['accepted_runs'],r['accepted_corrupted_conditions'],r['accepted_corrupted_tasks'],r['accepted_clean_tasks'])==(1,30,240,8)
assert len(r['artifact_bindings'])==375 and len(r['raw_evidence_bindings'])==407 and len(r['tasks'])==248 and r['summary_rows']==1440
assert sum(q['mode']=='exact_inherited_checkpoint_SHA_no_read' for q in r['original_hash_queries'])==1
assert sum(q['mode']=='actual_sealed_artifact_hash' for q in r['original_hash_queries'])==715
assert len(r['specific_training_source_bindings']['root42_ancestry'])==7
assert len(r['original_functions'])==52 and not r['old_worker_CIM_observation']['matches']
assert r['full_clip_diagnostic']['canonical_verified'] and r['full_clip_diagnostic']['sample_path_selection_checked_without_image_bytes']
assert not r['full_clip_diagnostic']['tolerance_gate_exists'] and not r['full_clip_diagnostic']['numerical_error_recomputed']
files=[rb,
    bind(HERE/'a1/METADATA.json','710c0280f76a99cf379bc85f17467fef462fcb094f5d37cafdcc773b07f71c43'),
    bind(HERE/'review_sues_full1.py','e6dc1126279ec05b40b89e279ae41a4863fbef0a88e0c7b87fd6d0a0febf9f13'),
    bind(HERE/'SUES_FULL_FROM_SUES_VISUAL_SOURCE_DIFF.patch','e8581e34b18519de920f6abf2be7c00e26dc7d1318557ce53df5fa7093a5096c'),
    bind(HERE/'DERIVATION.json','8cc319ff4e1fb815f73b68221e053980d6325ac0551ceca7d4f3844b9c3358fe'),
    bind(HERE/'derive_sues_full_review.py'),bind(Path(__file__))]
contract=HERE/'contract_review'
assert contract.is_dir() and any(contract.glob('*STATIC*.json')) and any(contract.glob('*CONTRACT*.json')),'Separate contract and static review must be available before sealing'
bind(contract/'SUES_FULL_CONTRACT_REVIEW.json','f83d76b74acc491e7984cd471771f760b3306ecf88dfab0133559e4da70c45c5')
bind(contract/'SUES_FULL_SOURCE_STATIC_REVIEW.json','7d88895ed9b741bfb2db548d536a1e3bedd7068ca2d229f6d8382fabe0badbf5')
static=json.loads((contract/'SUES_FULL_SOURCE_STATIC_REVIEW.json').read_text(encoding='utf-8'))
assert static['candidate']['sha256']==r['source']['sha256'] and static['blocking_findings']==[] and not static['candidate_or_control_tests_executed']
for p in sorted(contract.rglob('*')):
    if p.is_file():files.append(bind(p))
note=HERE/'SUMMARY.md'
text='''# Fixed SUES Full seed 1 robustness audit

First independent audit execution returned 0 and passed with stated limits. The only newly reviewed scope is SUES-200 Full seed 1: 30 corruption conditions, 240 corrupted task results and 8 clean task results. Earlier three adopted runs are inherited; this report does not independently re-audit the entire four-run stage or adopt later pipeline stages.

The audit binds 375 new artifacts by actual size/SHA and 407 raw inputs, including 248 NPZ files, 62 CSV tables and 1440 summary rows. There are 3,592,417 assertions and 24,624 numeric comparisons. The original 52 AST definitions are unchanged under a typed standard-library compatibility layer and original completion issues are empty. The 716 tracked hash calls comprise one exact inherited SUES Full checkpoint SHA and 715 actual sealed-artifact hashes. This is not native NumPy execution or fresh checkpoint-byte verification; all other checkpoint requests and checkpoint/cache/image byte opens are rejected.

The own training authority is the unique SUES Full seed1 member of the accepted Sep22 BATCH_COMPLETION_0944 report (SHA2183ab32674d171f0d7ce15ea96b5e72b1990ad7071404e89403108f28f96a25). Seven small-file ancestry nodes are rebound to ROOT42, verifying each actual parent path/SHA edge. The historical best.pt SHA7478740b013990c83c5c21f619bc89b2664ee70ff90fda18ab3b7ac420c870e9 and size172338603 agree with the specific SUES_BATCH9-v2 official acceptance, ROOT_OFFICIAL42, accepted T3 source row and sealed checkpoint ledger. Current file identity/existence/size and stable metadata are checked without opening the weight; metadata is not proof of current bytes. Initial-inventory evidence is not substituted and historical source-edge gaps elsewhere remain disclosed.

The original 120 training IDs and complementary 80 test/query IDs, four heights150/200/250/300m, exact two directions and complete200-identity galleries are retained. Each height has4000 UAV queries against200 satellites and80 satellite queries against10000 UAV images; each gallery identity has50 UAV images per height. Directory metadata enumerates40200 paths, the uniquequery union is16080 and gallery union40200. Original pure task-building and protocol hashes agree. No image/cache bytes are read.

Every stored query's membership/order, label, top1 index/path/label mapping, rank bounds, recall, exact float32 reciprocal rank, copied clean arrays, float32 AP/RR deltas and signed-int8 correctness transitions are checked. All producer dtypes, JSON/CSV values, ordered unique columns, degradation formulas and summary rows agree. Stored AP/RR/margin means are checked using math.fsum binary64 with relative1e-6/absolute1e-7 tolerance for original float32 reduction; this is not bitwise native NumPy reduction. AP is not recomputed from all positive ranks or margin from complete scores. Pixel/feature coverage remains a bound producer declaration, not independent execution.

Full has its own non-null64-sample CLIP diagnostic: sidefile SHA2247388d3bea3a99ebb79be71508bfb76c11d2d1aae3388b9bd22094c3655cd3, canonical payload3069fcb2b0a9a19f0a201bb2993ff5b31ab43f1377b96dddfed8440fda82c1c4, deterministic query sample membership8ddc20a8d0fdff79b435592f908e6000f922dd943638247fd644d18b5fb0b66d. Embedded/sidefile/provenance/cache-small-metadata and actual64 query path selection agree. The producer reports content MAE0.00011518623068695888/max0.00244140625 and style MAE0.000110904875327833/max0.001953125; exact-float16 fractions are0.12073863636363637 and0.1390625. These errors were not independently remeasured. No numerical tolerance gate exists in the frozen source, so this does not establish cache/online equivalence or bitwise reproduction. Clean uses cached evidence while corrupt queries recompute online CLIP on corrupted RGB; the degradation mixes evidence-path and pixel-corruption effects. It is not a pure-corruption estimate or full-dataset onlineCLIP accuracy/efficiency measurement.

The original parent subprocess.run return0 at2026-09-29T13:36:15.123085Z and closed stdout/stderr are bound. Independent CIM at2026-09-29T13:54:25.5145492Z found oldFull PIDs37764/14260 absent. The325-byte stderr contains only the frozen slow-processor notice. This is not an independent dual-handle launcher/interpreter exit-code observation. No live state, frozen science code, protocol, recovery entry, HANDOFF or automation was modified. Onlyseed1 is represented, with no across-seed SD or significance claim.

Separate static/small-file contract review found no blocking adaptation issue and did not execute this artifact audit. Its first small-file sealer used an incorrect ROOT36 field assumption; the source, raw captures and REJECTED_ATTEMPT.json are preserved. Its v2 bound the actual independent_report edge and succeeded. That corrected review assumption is not a scientific-result change or a failure of this first artifact-audit execution. Later pipeline T6 failure is outside this audit scope and remains separate.
'''
with note.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
files.append(bind(note))
d=dict(schema='bounded-sues-full1-robustness-audit-delivery-v1',sealed_utc=datetime.now(timezone.utc).isoformat(),
    passed_with_stated_limits=True,scope=r['scope'],checks=r['checks'],raw_bindings=407,new_artifacts=375,
    original_gate_issues=[],original_definitions=52,original_hash_request_counts=dict(exact_inherited_checkpoint=1,actual_sealed_artifact=715),
    report=rb,files=files,limits=r['limits'],root_adoption_not_claimed=True,first_execution_exit_code=0,
    scientific_execution_performed=False,old_weights_or_cache_or_image_bytes_opened=False)
out=HERE/'DELIVERY.json'
with out.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
print(json.dumps(dict(delivery=bind(out),files=len(files)),ensure_ascii=True))
