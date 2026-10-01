"""Capture actual file-identity alias evidence in two stdlib-only processes."""
import json
import hashlib
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'external_efficiency_preparation/newer_native_loader_v1'
output=HERE/'ACTUAL_PATH_ALIAS_EVIDENCE.json'
if output.exists():raise RuntimeError('Preserve existing alias evidence')
code="""import sys,json;from contextlib import nullcontext
sys.path.insert(0,sys.argv[1]);import source_bindings as b
method=sys.argv[2];source=b.source_contract(method);p=b.open_original_package(method)
with (p.snapshots.snapshot_scope() if p.snapshots else nullcontext()):
 value=p.evaluator.read_prepared(source['prepared'].path)
b.no_scientific_modules();source['prepared'].unchanged()
print(json.dumps({'method':method,'prepared':source['prepared'].artifact(),'registered_python':value['python'],
 'sources_equal_after_same_file_alias_validation':value['sources']==p.protocol.source_evidence(),
 'aliases':p.alias_guard.latest_aliases,'scientific_modules_imported':False},ensure_ascii=False))
"""
rows=[]
for method in ('CAMP','DAC'):
    result=subprocess.run([sys.executable,'-X','utf8','-c',code,str(PACKAGE),method],capture_output=True,
        text=True,encoding='utf-8',timeout=45,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    rows.append(json.loads(result.stdout))
payload={'scope':'Actual standard-library prepared/source read and Windows same-file checks; no science or checkpoint binding',
         'results':rows,'source_files_edited':False,'prepared_contracts_edited':False,
         'existing_queued_entrypoints_changed':False,
         'remaining':'Existing direct CAMP evaluator entry needs the same reviewed compatibility integrated through an explicit updated queue contract before execution.'}
output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'report':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                  'alias_counts':{r['method']:len(r['aliases']) for r in rows}}))
