"""Read back the one-byte carrier and bind reviewed, actually executed initialization."""
from pathlib import Path
import hashlib,json,datetime
HERE=Path(__file__).absolute().parent
EX=HERE.parent
def binding(p):
    p=Path(p);raw=p.read_bytes()
    assert len(raw)<1000000 and p.suffix.lower() not in {'.pt','.npz','.npy'}
    return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
checked={}
def walk(v):
    if isinstance(v,dict):
        if {'path','bytes','sha256'}<=v.keys():
            a=binding(v['path']);assert a=={k:v[k] for k in a};checked[a['path']]=a
        else:
            for child in v.values():walk(child)
    elif isinstance(v,list):
        for child in v:walk(child)
source_review=EX/'shared_lock_initialization_review_20260929_1652/STATIC_REVIEW.json'
assert binding(source_review)['sha256']=='0a84901ca559aab0f7916e54bd60d9d6b10c3427818fbaa27ee9c21627c638f1'
receipt=HERE/'INITIALIZATION.json'
assert binding(receipt)['sha256']=='06dfe795672aabaf76e65acd0efd95843c483b9e0db443f251e409d5fc8b29e1'
review=read(source_review);execution=read(receipt)
walk(review);walk(execution)
assert execution['script']==review['script'] and execution['independent_review']==binding(source_review)
assert execution['status']=='created_exact_single_ascii_zero_byte'
assert execution['before']['matched_processes']==execution['final_before_create']['matched_processes']==[]
assert execution['before']['states']==execution['final_before_create']['states']==execution['after_states']
lock=EX/'latest_baseline_gpu.lock'
assert lock.read_bytes()==b'0'
assert execution['lock']==binding(lock)
assert execution['real_byte_lock_acquisition'] is False and execution['execution_release_created'] is False
assert execution['recovery_started'] is False and execution['scientific_execution'] is False
report={'schema':'root-persistent-shared-byte-carrier-adoption.v1',
 'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'actual_single_byte_initialization_readback_adopted',
 'source':binding(Path(__file__).absolute()),'independent_static_review':binding(source_review),
 'actual_initializer_receipt':binding(receipt),'actual_initializer_tool_exit_code':0,
 'lock':binding(lock),'unique_input_bindings':len(checked),'bindings':list(checked.values()),
 'root_scope':'Root read complete initializer/diff/static report/sealer and original two byte-lock implementations, verified all independent bindings before one actual execution, then independently read back exact one byte and unchanged state hashes.',
 'old_source_adoption_unchanged':binding(EX/'t6_recovery_preparation_20260929_1548/ROOT_SOURCE_ADOPTION.json'),
 'replay_forbidden':True,'lock_owned':False,'GPU_admitted':False,'native_import':False,'recovery_launched':False,
 'limits':review['interpretation_limits']+['Only missing persistent file prerequisite is now met; no ownership/resource/scientific/predecessor completion is inferred.','No new runtime release/intent, state publication, source changes, or successor launch. Old preparation reports describe the historical missing-file state and must not be rerun.']}
out=HERE/'ROOT_INITIALIZATION_ADOPTION.json'
with out.open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'report':binding(out),'lock':binding(lock),'unique_input_bindings':len(checked)},ensure_ascii=False))
