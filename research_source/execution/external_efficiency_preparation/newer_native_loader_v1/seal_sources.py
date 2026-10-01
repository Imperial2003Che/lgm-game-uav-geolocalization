"""Seal this source preparation, preserving all existing queue contracts."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import source_bindings as b

HERE=Path(__file__).resolve().parent
REVIEW=HERE.parents[1]/'newer_native_loader_review_20260915'
output=HERE/'SOURCE_MANIFEST.json'
if output.exists():raise RuntimeError('Preserve existing source manifest')
report=json.loads((REVIEW/'PATH_ALIAS_FINAL_REVIEW.json').read_text(encoding='utf-8'))
b.require(report['status']=='passed' and report['tests_run']==16,'Final control review did not pass')
for path,expected in report['source_files'].items():b.require(b.sha(path)==expected,'Reviewed source changed')
files=[HERE/name for name in ('source_bindings.py','native_load.py','path_aliases.py','HANDOFF.md','seal_sources.py')]
files.extend(REVIEW/name for name in ('review_loader.py','PATH_ALIAS_FINAL_REVIEW.json','ACTUAL_PATH_ALIAS_EVIDENCE.json','capture_alias_report.py','FINAL_REVIEW.json'))
source_checks={}
for method,row in b.REGISTRY.items():
    source_checks[method]=b.source_contract(method)
    directory=b.EXECUTION/row['directory']
    manifest=directory/'PREPARATION_MANIFEST.json';files.extend([manifest,directory/row['prepared']])
    for item in json.loads(manifest.read_text(encoding='utf-8'))['files']:
        path=Path(item['path']);files.append(path if path.is_absolute() else directory/path)
ops_manifest=b.OPS/'SOURCE_MANIFEST.json';files.append(ops_manifest)
files.extend(Path(item['path']) for item in json.loads(ops_manifest.read_text(encoding='utf-8'))['files'])
unique=sorted(set(p.resolve(strict=True) for p in files),key=str)
evidence=json.loads((REVIEW/'ACTUAL_PATH_ALIAS_EVIDENCE.json').read_text(encoding='utf-8'))
for row in evidence['results']:
    b.require(row['sources_equal_after_same_file_alias_validation'] and not row['scientific_modules_imported'],
              'Actual prepared/alias evidence failed')
payload={'schema':'newer-native-loader-source.v1','status':'source_prepared_model_loading_unexecuted_queue_not_updated',
         'created_utc':datetime.now(timezone.utc).isoformat(),'file_count':len(unique),
         'files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':b.sha(p)} for p in unique],
         'stdlib_tests':16,'native_prepared_reads':['CAMP','DAC'],'actual_model_loading':False,
         'GPU_execution':False,'completed_checkpoints_bound':False,'active_plan_or_release_changed':False,
         'existing_CAMP_direct_entry_still_needs_compatibility':True,'full_t6_complete':False,'manuscript_result':False}
output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(output),'sha256':b.sha(output),'file_count':len(unique),'status':payload['status']}))
