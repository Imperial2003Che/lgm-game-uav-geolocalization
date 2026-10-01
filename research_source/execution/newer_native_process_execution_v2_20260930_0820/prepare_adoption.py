"""Root saved-record adoption only; no Windows API, fixture replay or science imports."""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
EX=HERE.parent
SRC=EX/'external_efficiency_preparation/newer_native_process_evidence_v2'
INNER=SRC/'runtime_attempt_v1'
OUTER=HERE/'outer_runtime_attempt_v1'
REVIEW=EX/'newer_native_process_v2_runtime_review_20260930_0826'
POST=EX/'process_fixture_after_v2_20260930_0840'
records={}
OFF=504911232000000000
def bind(path,limit=100000):
    path=Path(path)
    size=path.stat().st_size
    assert size < limit, str(path)
    with path.open('rb') as stream:
        raw=stream.read(limit)
    assert len(raw)==size and len(raw)<limit, str(path)
    item={'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    records[str(path)]=item
    return item,raw
def read(path):
    return json.loads(bind(path)[1])
def verify(item,limit=100000):
    assert bind(item['path'],limit)[0]==item,item['path']
def save(path,value):
    raw=(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode('utf-8')
    with Path(path).open('xb') as f:
        f.write(raw);f.flush()
    return bind(path)[0]
decision=read(HERE/'ROOT_BENIGN_FIXTURE_DECISION.json')
assert bind(HERE/'ROOT_BENIGN_FIXTURE_DECISION.json')[0]['sha256']=='d5802b7bcbea908b8eae4dd6a720cab1ae4f0cdfa39abf6c1d2bd9b07d1ed0be'
assert decision['execute'] is True and decision['scientific_admission'] is False
assert decision['maximum_fixture_attempts']==1
verify(decision['outer_source'])
for item in decision['small_inputs']:
    verify(item)
source_manifest=read(SRC/'SOURCE_MANIFEST.json')
assert bind(SRC/'windows_process_evidence.py')[0]['sha256']=='cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2'
assert bind(SRC/'benign_fixture.py')[0]['sha256']=='05379eda9addbac90faea33d73eb9a0faa4fc59450bf65e3e1f11de677fca50f'
ind=read(REVIEW/'RUNTIME_REVIEW.json')
assert ind['fixture_passed_saved_record_audit'] is True and ind['case_count']==2
assert ind['scientific_execution_or_admission'] is False
assert ind['windows_api_or_producer_executed_by_reviewer'] is False
verify(ind['inputs']);verify(ind['diagnostics'],500000)
for item in read(ind['inputs']['path'])['files']:
    verify(item)
delivery=read(REVIEW/'DELIVERY.json')
for name in ['review','inputs','diagnostics','source']:
    verify(delivery[name],500000 if name=='diagnostics' else 100000)
scope_addendum=read(REVIEW/'RUNTIME_SCOPE_AND_BINDING_ADDENDUM.json')
assert scope_addendum['scientific_execution_or_admission'] is False and scope_addendum['runtime_fixture_replayed'] is False
for item in scope_addendum['inputs']:verify(item)
for path in sorted(REVIEW.iterdir()):
    if path.is_file() and path.suffix in ['.py','.md','.patch','.txt','.json'] and path.name!='CHECKS.json':
        bind(path)
intent=read(INNER/'return_intent.json')
assert intent['controller_return_intent']==0 and intent['controller_actual_exit_unknown_here'] is True
controller_report=read(OUTER/'CONTROLLER_EXIT_AND_CLOSED_LOGS.json')
assert controller_report['scientific_admission'] is False and controller_report['outer_self_actual_exit_unknown_in_this_record'] is True
assert controller_report['controller_popen_exit']==0
assert ind['fixture_controller_actual_held_exit_captured_by_outer']==controller_report['controller_actual_held_exit']
actual=[]
logs=[]
for case,code in zip(intent['completed_cases'],[0,17]):
    assert case['case']['child_exit']==case['case']['launcher_exit']==code
    assert case['benign_task']=={'task':'sum_squares_0_through_999','value':332833500}
    assert case['scientific_execution_or_admission'] is False
    for key in ['launcher_exit','interpreter_exit']:
        value=case[key]
        ident=value['identity']
        assert type(value['exit_code_unsigned_dword']) is int and value['exit_code_unsigned_dword']==code
        assert value['wait_result']==0 and value['same_retained_handle_pid_creation_verified'] is True
        assert value['pid']==ident['pid']
        assert value['creation_filetime_100ns']==ident['creation_filetime_100ns']
        assert value['creation_utc_ticks']==ident['creation_utc_ticks']==ident['creation_filetime_100ns']+OFF
        assert type(value['exit_filetime_100ns']) is int and value['exit_filetime_100ns']>value['creation_filetime_100ns']
        assert value['exit_utc_ticks']==value['exit_filetime_100ns']+OFF
        assert value['image_scope']=='Retained live image; not requeried after exit'
        actual.append({'case':case['case']['name'],'role':key,'exit':value})
    logs.extend(case['closed_logs'])
cv=controller_report['controller_actual_held_exit']
assert cv['exit_code_unsigned_dword']==0 and cv['wait_result']==0
assert cv['creation_utc_ticks']==cv['creation_filetime_100ns']+OFF
assert cv['exit_utc_ticks']==cv['exit_filetime_100ns']+OFF
actual.append({'case':'outer','role':'fixture_controller','exit':cv})
logs.extend(controller_report['closed_logs'])
assert len(actual)==5 and len(logs)==10
assert len({v['exit']['pid'] for v in actual})==5
for item in logs:
    verify({key:item[key] for key in ['path','bytes','sha256']})
    assert item['controller_streams_closed'] is True and item['read_lock_denied_write_delete'] is True
events=[]
for directory in [INNER,OUTER]:
    for path in sorted(directory.rglob('*.json')):
        value=read(path)
        if 'event' in value:
            events.append(value)
assert len([e for e in events if e['event']=='exit_observed'])==7
assert not any(e['event']=='failure' for e in events)
for e in [e for e in events if e['event']=='cleanup_complete']:
    assert e['errors']==[] and e['no_termination'] is True and all(e['own_stream_closed'])
cleanup=read(OUTER/'OUTER_RETURN_INTENT_AND_CLEANUP.json')
assert cleanup['return_intent']==0 and cleanup['cleanup_errors']==[] and cleanup['own_redirect_streams_closed'] is True and cleanup['evidence_handles_closed'] is True
assert cleanup['own_actual_exit_unknown'] is True
receipt=read(HERE/'TOOL_EXECUTION_RECEIPT.json')
assert receipt['schema']=='post-execution-tool-transcription.v1' and receipt['tool_result']['exit_code']==0
after=read(POST/'OBSERVATION_WRAPPER_INCLUDED.json')
verify(after['source'])
old=(POST/'OBSERVER_PRIOR_SOURCE.ps1.txt').read_bytes()
now=Path(after['source']['path']).read_bytes()
assert now==old.replace(b'23920,10292,8528,17840,1396)',b'23920,10292,8528,17840,1396,17896,13180,19432,10068,3816,17112)')
diff=b''.join(difflib.diff_bytes(difflib.unified_diff,old.splitlines(keepends=True),now.splitlines(keepends=True),fromfile=b'OBSERVER_PRIOR_SOURCE.ps1.txt',tofile=b'observe_after_v2.ps1'))
diffpath=POST/'OBSERVER_PID_ONLY.patch'
with diffpath.open('xb') as f:f.write(diff)
bind(diffpath);bind(POST/'OBSERVER_PRIOR_SOURCE.ps1.txt')
for which in ['first','second']:
    row=after[which]
    assert row['boot_utc_ticks']=='639263337875000000'
    assert len(row['matches'])==1
    vis=row['matches'][0]
    assert vis['pid']==29480 and vis['parent_pid']==13076 and vis['name']=='VISIO.EXE'
    assert vis['creation_utc_ticks']=='639263338233256210'
    assert vis['command_line']=='"C:\\Program Files\\Microsoft Office\\root\\Office16\\VISIO.EXE" '
assert after['first']['matches']==after['second']['matches']
for item in after['files']:verify(item)
carrier={key:after['carrier'][key] for key in ['path','bytes','sha256']}
verify(carrier)
assert Path(carrier['path']).read_bytes()==b'0'
assert after['carrier']['creation_utc_ticks']=='639262940518466959'
for d in ['t6_recovery_preparation_20260929_1548','t6_recovery_preparation_20260930_0104','t6_recovery_preparation_20260930_0405']:
    assert not (EX/d/'runtime_attempt').exists()
assert not (EX.parent/'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1').exists()
assert not Path('C:/项目/LGM-GAME-Partner-Delivery-20260724/lgm_game_pytorch/analysis/transactions_t6_formal').exists()
v1_root=EX/'newer_native_process_execution_20260930_0810/ROOT_FAILED_CONTROL_ADOPTION.json'
v1_adoption=read(v1_root)
assert v1_adoption['fixture_passed'] is False and v1_adoption['runtime_validated'] is False
method=EX/'newer_native_process_runtime_review_20260930_0758/FAILED_RUNTIME_METHOD_ADDENDUM.json'
bind(method)
bind(EX/'newer_native_process_execution_20260930_0810/ROOT_EXIT_REPAIR_PRIMARY_SOURCES.json')
prior_source=bind(HERE/'ADOPTION_PREPARED_PRIOR.py.txt')[1]
actual_source=bind(__file__)[1]
source_diff=b''.join(difflib.diff_bytes(difflib.unified_diff,prior_source.splitlines(keepends=True),actual_source.splitlines(keepends=True),fromfile=b'ADOPTION_PREPARED_PRIOR.py.txt',tofile=b'prepare_adoption.py'))
with (HERE/'ADOPTION_PREEXEC_DELTA.patch').open('xb') as f:f.write(source_diff)
bind(HERE/'ADOPTION_PREEXEC_DELTA.patch')
bind(__file__)
report={
'schema':'root-adopted-current-host-benign-process-control.v2',
'adopted_utc':datetime.now(timezone.utc).isoformat(),
'root':'Root AI saved-source/runtime/log-byte adoption; producer actors held actual handles; separate independent AI read saved records',
'source_adopted':True,'current_host_two_case_benign_control_passed':True,
'original_scientific_environment_validated':False,'scientific_execution_released':False,
'b1_worker_or_ranking_admitted':False,'scientific_results':0,'new_figures':0,
'actual_external_held_exits':actual,'total_saved_exit_observed_records':7,
'closed_log_count':10,'closed_logs':logs,
'outer_tool_exit_code':0,'outer_independent_held_exit_captured':False,
'independent_review':bind(REVIEW/'RUNTIME_REVIEW.json')[0],
'independent_scope_addendum':bind(REVIEW/'RUNTIME_SCOPE_AND_BINDING_ADDENDUM.json')[0],
'root_after_observation':bind(POST/'OBSERVATION_WRAPPER_INCLUDED.json')[0],
'previous_failed_control_adoption':bind(v1_root)[0],
'previous_failure_method_addendum':bind(method)[0],
'source':bind(__file__)[0],'inputs':list(records.values()),
'replay_authorized':False,'preserved_attempts':[str(INNER),str(OUTER),str(EX/'external_efficiency_preparation/newer_native_process_evidence_v1/runtime_attempt_v1'),str(EX/'newer_native_process_execution_20260930_0810/outer_runtime_attempt_v1')],
'limits':[
'Actual zero and expected nonzero17 CPU controls validate same retained-handle PID/creation/exit evidence on this host only. Seven saved exit records include two supplementary launcher observations of the same children.',
'Outer tool exit0 is forwarded shell evidence, not independently held outer exit; producer aggregate never proves own exit.',
'No post-exit image/command requery: image is retained live evidence. Experimental Nt class60 and current Toolhelp parent observations are not general Windows support/full historical ancestry.',
'Independent and root reviews read persisted actual values and small logs; neither re-held the exited actors or re-ran API/fixture. AI review is not human review.',
'CreateNew publication and read-sharing log seals are cooperative. They do not guarantee immutable publication or malicious-writer historical exclusion.',
'The prior v1 failure/unknown exits remain. No replay, deletion, inferred retrospective exit or repeated old controls.',
'B1 scientific entry gates remain refused. Original scientific venv, predecessor independent exits, current resource/release/boot/shared locks, six fresh scientific workers, immutable evidence gate and full fresh-gallery/ranking/parity/timing/onlineCLIP remain unresolved.',
'Current boot/source observations are not future science/Visio admission. Ordinary Visio persists; latest GPU gate remains false; available commit was not measured here. No scientific release/intent/native probe/COM/cleanup/lock/state action.',
'All scientific counts, frozen commands, negative results and existing result/evidence limitations are unchanged. No old weights/NPZ/cache/image/large archive read or rehash.'
]}
target=HERE/'ROOT_CURRENT_HOST_CONTROL_ADOPTION.json'
saved=save(target,report)
print(json.dumps({'adoption':saved,'unique_small_inputs':len(report['inputs']),'externally_held_actors':len(actual),'saved_exit_records':7,'closed_logs':10,'science_results':0},ensure_ascii=False))

