"""Seal the completed fixed Full robustness audit; no scientific inputs are opened."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

HERE=Path(__file__).parent
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def bind(path,expected=None):
    path=Path(path);sha=digest(path)
    assert expected is None or sha==expected,(path,sha,expected)
    return dict(path=str(path),sha256=sha,bytes=path.stat().st_size)

review=HERE/'a1/REVIEW.json'
rb=bind(review,'a6268401ae9989dd8cfa2eb9394dc9320b108e288ca82b51b5439b35f2478199')
r=json.loads(review.read_text(encoding='utf-8'))
assert r['passed_with_stated_limits'] is True and r['original_completion_issues']==[] and r['scientific_modules']==[]
assert (r['accepted_runs'],r['accepted_corrupted_conditions'],r['accepted_corrupted_tasks'],r['accepted_clean_tasks'])==(1,30,90,3)
assert len(r['artifact_bindings'])==220 and len(r['raw_evidence_bindings'])==247 and len(r['tasks'])==93
assert sum(q['mode']=='exact_inherited_checkpoint_SHA_no_read' for q in r['original_hash_queries'])==1
assert sum(q['mode']=='actual_sealed_artifact_hash' for q in r['original_hash_queries'])==405
assert not r['old_worker_CIM_observation']['matches']
files=[rb,
    bind(HERE/'a1/METADATA.json','bec5d11b18bf79874d4719b622002e18e62db687f58ba31c07e5e7b449cc5763'),
    bind(HERE/'review_full1.py','e12125299612df0d68765b0ad744904a22015edd76a85b48a60759f3b3715d96'),
    bind(HERE/'FULL_FROM_VISUAL_SOURCE_DIFF.patch','4502eac7b6bbca3bf0219caa206235686e97c13f76e62057562e1e03499d4090'),
    bind(HERE/'DERIVATION.json','19111dc00a7093e8a8886bcdcb0ad28b49b33e7f658186f7e01ab7f4119bfe94'),
    bind(HERE/'derive_full_review.py'),bind(Path(__file__))]
for p in sorted((HERE/'contract_review').rglob('*')):
    if p.is_file():files.append(bind(p))
text='''# Fixed University Full seed 1 robustness audit

The first audit execution returned 0 and passed with the explicit evidence limits below. Scope is only University-1652 Full seed 1: 30 corruption conditions, 90 corrupted task results and 3 clean task results. This is not approval of the complete four-run robustness pipeline and includes no SUES result.

The audit binds 220 new artifacts by actual size/SHA, 247 raw inputs, 93 one-dimensional NPZ files, 62 CSV tables and 540 summary rows. It verifies exact query membership/order, full-gallery top-1 mapping, rank/recall relationships, stored AP/RR/margin aggregation, exact float32 per-query deltas, copied clean arrays, signed transitions, degradation equations, and JSON/CSV summary agreement. The already accepted Visual supplement's coverage, exact dtype, CSV ordered/unique columns, AP/unit, and no-science-import checks are integrated in this new source; the Visual source/results remain unchanged.

The original completion function's 52 selected AST definitions are unchanged. A typed standard-library NPZ compatibility layer replaces NumPy I/O/finite checks. The original gate returned no issues; 406 tracked hash requests comprise exactly one inherited SHA for Full's own accepted best.pt and 405 actual sealed-artifact hashes. All other checkpoint opens/requests reject. This is neither native NumPy execution nor a fresh checkpoint-byte verification. The checkpoint exists and matches the accepted path identity and size; metadata stability cannot establish current bytes.

Full uses its own Sep20 independent training report and root adoption, the specific BATCH6 official authority, the accepted T3 row and sealed ledger. The earlier initial12 inventory historical SHA-edge gap elsewhere in the global history is retained; it is not used as this Full checkpoint's authority. Cache/image-content SHA and encoded-feature/pixel-coverage declarations remain inherited, not independently re-executed.

The completed Full CLIP diagnostic sidefile and embedded manifest agree, including canonical payload SHA, 64 deterministic query sample paths, revision, model/candidate hashes and fp16 cache metadata. Its error statistics are producer observations, not newly measured here. The original source has no numerical tolerance gate and the recorded float16 exact fractions are not one. No cached/online equivalence or negligible ranking-effect claim is made. Clean uses cached evidence while corrupted queries use online CLIP, so comparisons combine the change in evidence computation path with image corruption; they are not pure-corruption effects, full-dataset online CLIP accuracy, or efficiency measurements.

Stored float32 AP/RR/margin aggregates are checked against standard-library math.fsum binary64 means with relative tolerance 1e-6 and absolute tolerance 1e-7, allowing original float32 reduction rounding. This is not bitwise NumPy reduction. AP is not recomputed from all positive ranks; margins are not recomputed from complete scores. No model, full ranking, image/corruption/feature or CLIP execution occurs. Only one seed is represented; no three-seed SD or significance claim follows.

The original stage records subprocess.run return 0 and closed stdout/stderr hashes. The independent current CIM observation found old Full PIDs 40820 and 43872 absent. The 325-byte stderr is the exact frozen slow-processor warning. None of this is an independent dual-handle interpreter/launcher exit-code measurement. No live state, frozen source, protocol, recovery or automation was changed.
'''
note=HERE/'SUMMARY.md'
with note.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
files.append(bind(note))
delivery=dict(schema='bounded-full1-robustness-audit-delivery-v1',sealed_utc=datetime.now(timezone.utc).isoformat(),
    passed_with_stated_limits=True,scope=r['scope'],checks=r['checks'],raw_bindings=247,new_artifacts=220,
    original_gate_issues=r['original_completion_issues'],original_definitions=len(r['original_functions']),
    original_hash_request_counts=dict(exact_inherited_checkpoint=1,actual_sealed_artifact=405),
    report=rb,files=files,limits=r['limits'],root_adoption_not_claimed=True,
    first_execution_exit_code=0,scientific_execution_performed=False,old_weights_or_cache_or_image_bytes_opened=False)
p=HERE/'DELIVERY.json'
with p.open('x',encoding='utf-8') as f:json.dump(delivery,f,ensure_ascii=False,indent=2)
print(json.dumps(dict(delivery=bind(p),files=len(files)),ensure_ascii=True))
