"""Seal source-only preparation once; never execute scientific operations."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
EXECUTION=HERE.parents[1]
output=HERE/'SOURCE_MANIFEST.json'
if output.exists():raise RuntimeError('Preserve the existing source manifest')
spec=importlib.util.spec_from_file_location('newer_native_sealed_operations',HERE/'native_ops.py')
ops=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ops;spec.loader.exec_module(ops)
review=EXECUTION/'newer_native_ops_review_20260915'
report=json.loads((review/'FINAL_STDLIB_REVIEW.json').read_text(encoding='utf-8'))
if report['status']!='passed' or report['tests_run']!=12 or report['source_sha256']!=ops.digest(HERE/'native_ops.py'):
    raise RuntimeError('Final reviewed source mismatch')
for path,expected in report['review_scripts'].items():
    if ops.digest(path)!=expected:raise RuntimeError('Final review script changed')
records={m:ops.verify_source_recipe(m) for m in ('CAMP','DAC')}
if records!=report['source_recipes']:raise RuntimeError('Reviewed original sources changed')
files=[HERE/'native_ops.py',HERE/'HANDOFF.md',Path(__file__),review/'test_native_ops.py',review/'final_review.py',
       review/'FINAL_STDLIB_REVIEW.json',review/'STDLIB_REVIEW.json',ops.COMPONENT_PATH]
for row in records.values():files.extend([Path(row['encoder_path']),Path(row['transform_path'])])
files=sorted(set(p.resolve() for p in files),key=str)
payload={'schema':'newer-native-operations-source.v1','status':'source_operations_prepared_not_integrated_not_run',
         'created_utc':datetime.now(timezone.utc).isoformat(),
         'files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':ops.digest(p)} for p in files],
         'source_count':len(files),'final_stdlib_tests':12,'scientific_execution':False,
         'actual_checkpoints_bound':False,'active_release_created':False,'registered':False,
         'full_t6_complete':False,'manuscript_result':False}
output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(output),'sha256':ops.digest(output),'source_count':len(files),'status':payload['status']}))
