"""Seal only the completed SUES Visual1 audit and its read-only contract review."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

HERE=Path(__file__).parent
def bind(path,expected=None):
    path=Path(path);data=path.read_bytes();sha=hashlib.sha256(data).hexdigest()
    assert expected is None or expected==sha,(path,expected,sha)
    return dict(path=str(path),sha256=sha,bytes=len(data))
rp=HERE/'a1/REVIEW.json'
rb=bind(rp,'cdd39eeb16618cbf3373099c9df67b7b8be9ec72fc2f575dc9807d3ee5e8ad32')
r=json.loads(rp.read_text(encoding='utf-8'))
assert r['passed_with_stated_limits'] and r['original_completion_issues']==[] and r['scientific_modules']==[]
assert (r['accepted_runs'],r['accepted_corrupted_conditions'],r['accepted_corrupted_tasks'],r['accepted_clean_tasks'])==(1,30,240,8)
assert len(r['artifact_bindings'])==374 and len(r['raw_evidence_bindings'])==409 and len(r['tasks'])==248 and r['summary_rows']==1440
assert sum(q['mode']=='exact_inherited_checkpoint_SHA_no_read' for q in r['original_hash_queries'])==1
assert sum(q['mode']=='actual_sealed_artifact_hash' for q in r['original_hash_queries'])==714
assert len(r['specific_training_source_bindings']['root42_ancestry'])==9
assert not r['old_worker_CIM_observation']['matches']
files=[rb,
    bind(HERE/'a1/METADATA.json','88684c87cb26ff2982a4a74651621eb651026fa6cacd4c58b9e21e41b2a80394'),
    bind(HERE/'review_sues_visual1.py','30e19aa18bb810604f06c8fb7b6c078d8330355a3e677972b2acc3df37ebdf0c'),
    bind(HERE/'SUES_VISUAL_FROM_FULL_SOURCE_DIFF.patch','b78b04ef20efbaaece67bc926b00f8f425c9a20e57dfd165d5d951194db614f7'),
    bind(HERE/'DERIVATION.json','37a102aa4fea29f4a48aba754e3e4b3485250c8119bdbb1b9f370fa585722522'),
    bind(HERE/'derive_sues_visual_review.py'),bind(Path(__file__))]
for p in sorted((HERE/'contract_review').rglob('*')):
    if p.is_file():files.append(bind(p))
note=HERE/'SUMMARY.md'
text='''# Fixed SUES Visual seed 1 robustness audit

First independent audit execution returned 0 and passed with stated limits. The only new accepted scope is SUES-200 Visual seed 1, comprising 30 corruption conditions, 240 corrupted task results and 8 clean task results. The original four-run robustness stage is not declared complete, and no SUES Full result is included.

The audit binds 374 new artifacts by actual size/SHA and 409 raw inputs, including 248 NPZ files, 62 CSV tables and 1440 summary rows. The original 52 AST definitions are unchanged under a typed standard-library compatibility layer; original completion issues are empty. The 715 tracked hash calls consist of one exact inherited SUES Visual checkpoint SHA and 714 actual sealed-artifact hashes. It is not native NumPy execution or a fresh checkpoint-byte validation. All other checkpoint requests and checkpoint/cache/image-content byte opens are prohibited.

Training authority is the exact SUES Visual seed1 new_runs member of the independently accepted Sep21 BATCH_COMPLETION_1611 report. Nine small-file ancestry nodes are rebound to ROOT42, with each actual parent JSON containing the exact next path/SHA edge. The historical best.pt SHA/size agrees with the specific SUES batch11 official acceptance, accepted T3 source row and sealed checkpoint ledger. The existing checkpoint has the same file identity and size; metadata stability does not prove current bytes. No University checkpoint or initial inventory is substituted. Historical source-edge gaps elsewhere in the global evidence chain remain disclosed.

The original fixed 120 training IDs and complementary 80 query IDs are bound by actual YAML SHA and exact original constants. The audit enumerates metadata of all 40200 image paths under the two SUES roles, runs the unchanged pure task builder, and checks four heights (150/200/250/300 m), both directions, all 200 gallery identities and 50 UAV images per identity per height. Each height has 4000 UAV queries against 200 satellites and 80 satellite queries against 10000 UAV images. Unique query union is 16080; clean gallery union is 40200. No image or cache bytes are opened.

Every task's stored query membership/order, labels, full-gallery top1 path/index mapping, rank bounds, recalls, float32 RR, exact copied clean arrays, float32 AP/RR differences and signed-int8 correctness transitions are checked. Original aggregate degradation and summary formulas, JSON/CSV values and ordered unique CSV fields agree. All exact producer array dtypes and complete clean coverage declarations are checked. Stored AP/RR/margin means use math.fsum binary64 reference with relative tolerance 1e-6 and absolute 1e-7 for original float32 reduction rounding; this is not bitwise NumPy reduction. AP is not recomputed from all positive ranks; margins are not recomputed from full scores.

Visual intentionally skips online CLIP and has a null CLIP clean audit. Pixel/feature coverage and image/cache SHA are producer declarations or inherited evidence, not new image decoding, corruption/feature reconstruction or inference. This result establishes no SUES Full result, cache/online equivalence, or full-dataset online CLIP accuracy/efficiency. Only seed1 is represented, so no multi-seed SD, significance or whole-stage claim is made.

The original parent subprocess.run return0 and closed stdout/stderr are bound. Independent CIM at 2026-09-29T12:55:49.4830622Z found old Visual PIDs 24428 and 40060 absent. This is not an independent dual-handle launcher/interpreter exit-code measurement. No live state, frozen science source, protocol, recovery entry, HANDOFF or automation was modified.
'''
with note.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
files.append(bind(note))
d=dict(schema='bounded-sues-visual1-robustness-audit-delivery-v1',sealed_utc=datetime.now(timezone.utc).isoformat(),
    passed_with_stated_limits=True,scope=r['scope'],checks=r['checks'],raw_bindings=409,new_artifacts=374,
    original_gate_issues=[],original_definitions=52,original_hash_request_counts=dict(exact_inherited_checkpoint=1,actual_sealed_artifact=714),
    report=rb,files=files,limits=r['limits'],root_adoption_not_claimed=True,first_execution_exit_code=0,
    scientific_execution_performed=False,old_weights_or_cache_or_image_bytes_opened=False)
out=HERE/'DELIVERY.json'
with out.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
print(json.dumps(dict(delivery=bind(out),files=len(files)),ensure_ascii=True))
