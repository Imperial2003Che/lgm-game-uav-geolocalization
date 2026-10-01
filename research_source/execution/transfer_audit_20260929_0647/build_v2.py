from pathlib import Path
import hashlib,difflib
here=Path(__file__).parent
old=here/'review_transfer.py';base=old.read_text(encoding='utf-8')
assert hashlib.sha256(old.read_bytes()).hexdigest()=='3ccba056f279227aa0b425d318b77cab23123c92dabea55e4ada7d38ae012645'
s=base.replace("allowed_eval={'BATCH10_EVALUATION_REVIEW.json','BATCH6_EVALUATION_REVIEW.json','SUES_BATCH11_EVALUATION_REVIEW.json','SUES_BATCH9_EVALUATION_REVIEW.json'}", "allowed_eval={'BATCH10_EVALUATION_REVIEW.json':'7dc08f79d974394c95c53fca990fd55b3832981d72bc0d09a2b64b53206988c8','BATCH6_EVALUATION_REVIEW.json':'f2d578c904e14c99b4d5b4a00ace980d3ecca99c5ba43d2ebe6c7b228e98acf1','SUES_BATCH11_EVALUATION_REVIEW.json':'78b187ce0388f5d8d28ebcb7139039059cf897eb574051c38ee50e72a60e6a1a','SUES_BATCH9_EVALUATION_REVIEW.json':'3cb6894e754bf9388519b5886491deca61e807472b7dbde9c2e93dd3ff65c074'}")
s=s.replace("dest.name in allowed_eval or (dest.name.startswith", "(dest.name in allowed_eval and digest==allowed_eval[dest.name]) or (dest.name.startswith")
s=s.replace("check(allowed_eval.issubset(docs)", "check(set(allowed_eval).issubset(docs)")
s=s.replace("'SUES_MANIFEST_SOURCE','canonical_sha256','slugify'", "'SUES_MANIFEST_SOURCE','canonical_json_bytes','canonical_sha256','slugify'")
anchor="    matrix_path=PKG/'experiments/run_transactions_t3_transfer_matrix.py'"
s=s.replace(anchor,"    rejected_source=snap(HERE/'review_transfer.py',expected='3ccba056f279227aa0b425d318b77cab23123c92dabea55e4ada7d38ae012645')[1]\n    rejected_report=snap(HERE/'attempt_20260929_055612_827811/TRANSFER_REVIEW.json',expected='df43c200e9ec1a364ab2571eae73424b58997a6ac05747c6919feb0d47f5180a')[1]\n    report['rejected_candidate_retained']=dict(source=rejected_source,report=rejected_report,reason='Inherited metadata traversal followed a historical rejected same-name report; v2 pins all four accepted review SHAs and adds statically identified missing pure canonical helper. No scientific change.')\n    snap(HERE/'V1_TO_V2.patch')\n"+anchor)
compile(s,'v2','exec')
new=here/'review_transfer_v2.py'
with new.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
with (here/'V1_TO_V2.patch').open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(difflib.unified_diff(base.splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(new))))
print(hashlib.sha256(new.read_bytes()).hexdigest())
