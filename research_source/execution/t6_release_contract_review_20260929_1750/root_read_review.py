"""Accept only the static explanation of the already adopted conditional release."""
from pathlib import Path
import datetime
import hashlib
import json

W=Path(__file__).resolve().parent
EX=W.parent
bindings={}

def bind(path):
    p=Path(path);b=p.read_bytes()
    return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}

def verify(item):
    key=str(Path(item['path'])).casefold()
    if key in bindings:
        assert bindings[key]['sha256']==item['sha256'] and bindings[key]['bytes']==item['bytes']
    else:
        actual=bind(item['path'])
        assert actual['sha256']==item['sha256'] and actual['bytes']==item['bytes']
        bindings[key]=actual

def walk(obj):
    if isinstance(obj,dict):
        if {'path','sha256','bytes'}<=obj.keys():verify(obj)
        for x in obj.values():walk(x)
    elif isinstance(obj,list):
        for x in obj:walk(x)

p=W/'RELEASE_CONTRACT_REVIEW.json'
report=bind(p)
assert report['sha256']=='e2ac6dc6a3c1068fde976458e31d0e50617c84b888611aff387b6ba76bf567cb'
verify(report)
r=json.loads(p.read_bytes());walk(r)
assert r['status']=='existing_candidate_sufficient_no_new_runner_required'
assert not r['is_execution_release'] and not r['current_execution_approved']
assert r['direct_release_contract']['consumed_fields']==['schema','scope','execute','source_manifest','root_adoption','issued_utc','expires_utc']
assert r['indirect_contract']['candidate_file_count']==14 and r['indirect_contract']['contract_input_count']==96
assert r['indirect_contract']['separate_release_state_spec_boot_fields_consumed'] is False
assert r['future_root_readiness_evidence']['annex_fields_are_consumed_by_candidate'] is False
assert r['current_observation']['gpu_rows']==24 and r['current_observation']['original_gpu_exclusive_gate_satisfied'] is False
prep=EX/'t6_recovery_preparation_20260929_1548'
adopt=json.loads((prep/'ROOT_SOURCE_ADOPTION.json').read_bytes())
assert adopt['execution_released'] is False and adopt['approved_for_future_gated_execution'] is True
assert not (prep/'runtime_attempt').exists()
assert (EX/'latest_baseline_gpu.lock').read_bytes()==b'0'
verify(bind(EX/'latest_baseline_gpu.lock'))
verify(bind(__file__))
out={'schema':'root-future-release-contract-explanation-adoption.v1','time':datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
     'accepted_static_explanation':True,'execution_released':False,'scientific_execution':False,
     'source':bind(__file__),'independent_report':report,'unique_bound_files':len(bindings),'bindings':list(bindings.values()),
     'root_read_scope':'Full independent JSON/MD/sealer and thin PowerShell entry; candidate release_gate and runtime admission/publication/monitor entry blocks directly read. Candidate full source remains the prior exact root source adoption, not a new full rereview here.',
     'conclusion':'Existing source consumes the stated seven release fields and transitively binds fixed contract/spec/state/boot. No new runner is required. This record is not an execution release.',
     'limits':['No candidate, native probe, new test, GPU query, process query or live state/lock operation performed by this script.',
       'Current false GPU gate does not authorize execution; future fresh root readiness and conditional release are separate from guardian actual native/lock/final gates.',
       'Source adoption remains byte-identical with historical execution_released=false. No full96-input or old-control replay.',
       'Read-only statics and current carrier bytes do not prove future runtime behavior or acquired lock. Original process exit unknowns, cooperative handoff and unobserved-child limits persist.']}
target=W/'ROOT_CONTRACT_EXPLANATION_ADOPTION.json'
with target.open('x',encoding='utf-8',newline='\n') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'report':bind(target),'unique_bound_files':len(bindings)},ensure_ascii=False))
