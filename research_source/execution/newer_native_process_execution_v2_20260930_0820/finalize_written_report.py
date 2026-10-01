"""Limited post-write report finalization; do not rerun adopted runtime checks."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
HERE=Path(__file__).resolve().parent
def bind(p,cap=250000):
    p=Path(p)
    size=p.stat().st_size
    assert size<cap
    with p.open('rb') as f:r=f.read(cap)
    assert len(r)==size and len(r)<cap
    return {'path':str(p),'bytes':len(r),'sha256':hashlib.sha256(r).hexdigest()},r
target=HERE/'ROOT_CURRENT_HOST_CONTROL_ADOPTION.json'
report_binding,raw=bind(target)
report=json.loads(raw)
failure_binding,fraw=bind(HERE/'ROOT_SEAL_POSTWRITE_FAILURE.json')
failure=json.loads(fraw)
assert report_binding['bytes']==104883 and failure['actual_tool_exit']==1
assert failure['stage'].startswith('save(target, report) wrote root report')
assert report['source_adopted'] is True and report['current_host_two_case_benign_control_passed'] is True
assert report['original_scientific_environment_validated'] is False and report['scientific_execution_released'] is False
assert report['b1_worker_or_ranking_admitted'] is False and report['scientific_results']==0
assert report['outer_independent_held_exit_captured'] is False and report['replay_authorized'] is False
assert len(report['actual_external_held_exits'])==5 and report['total_saved_exit_observed_records']==7 and report['closed_log_count']==10
assert len(report['inputs'])==len({r['path'] for r in report['inputs']})
source_binding,sraw=bind(HERE/'prepare_adoption.py')
assert source_binding==report['source']
assert b"stream.write(raw);stream.flush()" not in sraw
assert b"f.write(raw);f.flush()" in sraw and b"return bind(path)[0]" in sraw
bindings=[report_binding,failure_binding,source_binding,bind(__file__)[0]]
for name in ['ADOPTION_PREPARED_PRIOR.py.txt','ADOPTION_PREEXEC_DELTA.patch']:
    bindings.append(bind(HERE/name)[0])
record={'schema':'root-benign-control-written-report-finalization.v1',
'finalized_utc':datetime.now(timezone.utc).isoformat(),
'root_control_adoption_finalized':True,'joins_without_modifying':report_binding,
'original_root_sealer_actual_exit':1,'root_sealer_failure_scope':'After report write/close, default100KB digest-return rejected104883B; previous assertions reached completion by actual traceback code path.',
'limited_finalizer_scope':'Only existing report syntax/scope/unique index count and exact writer/failure bytes; no replay of core source/runtime/log checks, candidate or API.',
'root_input_binding_count':len(report['inputs']),'bindings':bindings,
'replay_authorized':False,'scientific_execution_released':False,
'limits':['Root report and original source remain exact. This record completes report byte finalization separately; it does not turn original exit1 into exit0.',
'Current-host two benign CPU cases only; original scientific venv/B1/T6/future execution authority remain unvalidated.',
'Root and independent agents inspect saved producer handle evidence; no independent held outer caller exit exists.']}
out=HERE/'ROOT_REPORT_FINALIZATION.json'
with out.open('xb') as f:
    f.write((json.dumps(record,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode('utf-8'));f.flush()
print(json.dumps({'finalization':bind(out)[0],'unchanged_report':report_binding,'root_bindings':len(report['inputs'])},ensure_ascii=False))

