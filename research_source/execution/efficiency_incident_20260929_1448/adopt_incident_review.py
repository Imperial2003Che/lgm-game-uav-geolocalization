import datetime, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
seen = {}
def bind(path, expected=None):
    p = Path(path).resolve()
    assert p.is_file() and p.stat().st_size < 1_500_000 and p.suffix.lower() not in ('.pt','.pth','.npz','.npy','.exe')
    data=p.read_bytes(); row={'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
    if expected:
        assert row['sha256']==expected['sha256'],str(p)
        if 'bytes' in expected: assert row['bytes']==expected['bytes'],str(p)
    if str(p).casefold() in seen: assert seen[str(p).casefold()]==row
    seen[str(p).casefold()]=row
    return row
def read(path, digest):
    bind(path,{'sha256':digest}); return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def walk(v):
    if isinstance(v,dict):
        if 'path' in v and 'sha256' in v: bind(v['path'],v)
        for x in v.values():walk(x)
    elif isinstance(v,list):
        for x in v:walk(x)
def normalized(v):
    if isinstance(v,dict):return {k:normalized(x) for k,x in v.items()}
    if isinstance(v,list):return [normalized(x) for x in v]
    if isinstance(v,str) and len(v)>20 and v[:10]=='2026-09-29' and 'T' in v:
        try:return datetime.datetime.fromisoformat(v.replace('Z','+00:00')).astimezone(datetime.timezone.utc).isoformat()
        except ValueError:pass
    return v

rd=EX/'efficiency_incident_review_20260929_1448'
r=read(rd/'INDEPENDENT_INCIDENT_REVIEW.json','0da37ea62441b9aee1e86bd141c1830e9f1ce1cfe9ef0e81672f1359f4510488');walk(r)
s=read(rd/'RECOVERY_SPEC.json','66e499c80036c3ef376993eb0decd01e28cd7adfa07cef54efc1001ac5dc0c45');walk(s)
cap=read(HERE/'capture_20260929_144939892/CAPTURE.json','7cd62f16dcf7f4a1ab9f3578b7c780ecb641ec02bf0fdf55a0a802f8bec2c1e4')
rootcap=read(HERE/'ROOT_CAPTURE_REVIEW.json','0670f1faf0ad8cd58422ac8372cef24ccca77981d5e294276079cdb24338e85e')
assert rootcap['file_binding_checks']==72 and rootcap['t6_output_exists'] is False
state_binding=next(b['snapshot'] for b in cap['bindings'] if b['source']['path'].endswith('execution\\pipeline_status.json'))
state=read(state_binding['path'],state_binding['sha256'])
assert normalized(r['failed_job'])==normalized(state['jobs'][6])
assert normalized(r['first_six_runtime_records'])==normalized(state['jobs'][:6])
assert s['original_t6_command']==state['jobs'][6]['command']
assert s['original_t6_entrypoint_sha256']==state['jobs'][6]['entrypoint_sha256']
assert s['status']=='design_only_not_implemented_not_launched' and s['execution_authorized_by_this_spec'] is False
assert s['live_state_must_remain_unchanged_until_all_gates_pass'] is True
assert r['default_t6_output_observation']['exists'] is False
assert r['current_old_pid_observation']['matches']==[]
assert not Path(r['default_t6_output_observation']['path']).exists()
bind(__file__)
output={'schema':'root-t6-incident-static-adoption.v1','time':datetime.datetime.now().astimezone().isoformat(),
    'adopted_scope':'diagnosis and recovery design only; not implemented or released',
    'independent_review':bind(rd/'INDEPENDENT_INCIDENT_REVIEW.json'),'recovery_spec':bind(rd/'RECOVERY_SPEC.json'),
    'root_capture_review':bind(HERE/'ROOT_CAPTURE_REVIEW.json'),'unique_files':len(seen),'bindings':list(seen.values()),
    'parent_records_utc_normalization_checked':True,'benchmark_result_created':False,'original_gpu_gate_satisfied':False,
    'recovery_launched':False,'live_state_modified':False,'full_t6_complete':False,
    'root_review':'Read complete independent report/spec/MD/sealer, original supervisor, original exclusive guard and run_benchmark ordering, corrected driver status prerequisites; verified explicit UTC normalization of original parent records.',
    'limits':r['limitations'],'next_action':'Observe original GPU admission on later heartbeat; only a new reviewed incident-specific recovery may preserve first6 and retry original T6. No old recovery replay, no user-application shutdown, no alternate driver substitution.'}
p=HERE/'ROOT_INCIDENT_REVIEW_ADOPTION.json'
with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(output,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'adoption':bind(p),'files':output['unique_files']},ensure_ascii=False))
