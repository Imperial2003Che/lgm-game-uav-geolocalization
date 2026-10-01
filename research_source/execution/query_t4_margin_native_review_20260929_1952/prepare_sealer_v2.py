"""Preserve the observed packaging-name failure and derive a corrected sealer."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent

def bind(p):
    data = p.read_bytes()
    return {'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

original = HERE/'seal_review.py'
before = original.read_text(encoding='utf-8')
after = before.replace("'raw_final'", "'raw_final_v2'")
after = after.replace("OUT / 'FIGURE_INDEX.json'", "OUT / 'FIGURE_INDEX.csv'")
after = after.replace("('derive_contract.py', 'review_artifacts.py', 'seal_review.py')", "('derive_contract.py', 'review_artifacts.py', 'seal_review.py', 'prepare_sealer_v2.py', 'seal_review_v2.py')")
after = after.replace("'failure_record': 'No independent contract/artifact execution failure and no rejected producer candidate in this figure task.',", "'failure_record': 'No contract/artifact failure or rejected producer figure. Sealer v1 exited1 at missing FIGURE_INDEX.json; actual producer index is.csv. Original source and partial raw_final preserved; v2 uses corrected index and new raw_final_v2.',\n        'sealer_v1_failure': bind(HERE/'REJECTED_SEALER_V1.json'),\n        'sealer_v1_to_v2_diff': bind(HERE/'SEALER_V1_TO_V2.patch'),")
after = after.replace("'root_adoption': 'Pending parent", "'sealer_v1_failure': bind(HERE/'REJECTED_SEALER_V1.json'),\n        'sealer_v1_to_v2_diff': bind(HERE/'SEALER_V1_TO_V2.patch'),\n        'root_adoption': 'Pending parent")
after = after.replace("The sample and full output used the same unchanged builder.", "The sample and full output used the same unchanged builder. Separately, independent sealer v1 exited1 because it requested FIGURE_INDEX.json while the actual index is FIGURE_INDEX.csv. Its unchanged source and partial raw_final directory (including the empty failed target) are preserved. The v2 sealer changes that index path and uses a fresh raw_final_v2 directory; successful data/artifact suites are not repeated.")
with (HERE/'seal_review_v2.py').open('x',encoding='utf-8') as f:f.write(after)
with (HERE/'SEALER_V1_TO_V2.patch').open('x',encoding='utf-8') as f:
    f.write(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='seal_review.py (executed rejected packaging path)',tofile='seal_review_v2.py')))
record = {'schema':'independent-t4-sealer-observed-failure.v1','utc_recorded':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'original_source':bind(original),'exit_code':1,'authority':'Actual exec_command result chunk6b9fe8, observed by reviewer; recorded after failure, not claimed as contemporaneous pre-run snapshot.',
    'error_type':'FileNotFoundError','error':'Original source requested output/FIGURE_INDEX.json; actual fixed producer file is output/FIGURE_INDEX.csv.',
    'failure_location':'seal_review.py main line66 -> snapshot line45 path.read_bytes; before any SOURCE_REVIEW/VISUAL_REVIEW/METADATA/DELIVERY output.',
    'preserved_partial_snapshots':[bind(p) for p in sorted((HERE/'raw_final').iterdir()) if p.is_file()],
    'successful_suites_unchanged':{'contract':4299,'artifact':89023},
    'no_scientific_or_producer_artifact_mutation':True,
    'derivation_source':bind(Path(__file__)),'corrected_source':bind(HERE/'seal_review_v2.py'),'complete_diff':bind(HERE/'SEALER_V1_TO_V2.patch')}
with (HERE/'REJECTED_SEALER_V1.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'failure':bind(HERE/'REJECTED_SEALER_V1.json'),'candidate':bind(HERE/'seal_review_v2.py'),'diff':bind(HERE/'SEALER_V1_TO_V2.patch')},ensure_ascii=False))
