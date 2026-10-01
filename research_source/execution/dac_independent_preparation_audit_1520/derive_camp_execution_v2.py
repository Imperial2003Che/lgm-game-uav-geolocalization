"""Derive fresh v2 input/execution binding with unchanged science and no execution."""
import ast
from contextlib import redirect_stdout
from datetime import datetime, timezone
import difflib
import hashlib
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
EXEC=HERE.parent
OLD=EXEC/'camp_training_execution'
NEW=EXEC/'camp_training_execution_v2'
INPUT_OLD=EXEC/'camp_training_inputs'
INPUT_NEW=EXEC/'camp_training_inputs_v2'
PREPARATION=EXEC/'camp_training_preparation_v2'
NEW_SHA='12747158ce2647474c6d24688ba3ebb872ac137118fab7aefd1c1e0ecfad40ec'
OLD_SHA='61f4eacc883421c08a5accd32c58c51c3a1a2287bcd5b146c1f1f270abd6b8fd'
BLOCKED={'torch','torchvision','numpy','scipy','matplotlib','PIL','cv2','timm','albumentations','sample4geo'}

class DenyScientific(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path,target=None):
        if fullname.split('.')[0] in BLOCKED:
            raise AssertionError('Scientific import attempted: '+fullname)

sys.meta_path.insert(0,DenyScientific())

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    assert str(Path(sys.executable).resolve()) == r'C:\项目\.venvs\lgm-camp\Scripts\python.exe'
    assert sha(PREPARATION/'PREPARATION_MANIFEST.json')==NEW_SHA
    assert sha(OLD/'PREPARATION_MANIFEST.json')=='2db151e298e1b6421c41a44146d9b0d4066ca9196c80d6818177b4f581876777'
    original_plan=read(OLD/'execution_plan.json')
    assert sha(OLD/'execution_plan.json')=='e326c3a0d510aac4f1a788be5ad158a503e850b9503d6a2266a7ca76d9d512e0'
    original_files=read(OLD/'PREPARATION_MANIFEST.json')['files']
    for row in original_files:
        assert sha(OLD/row['path'])==row['sha256'],row['path']
    for row in original_plan['seeds']:
        assert sha(row['plan_path'])==row['plan_sha256']
        assert not any(Path(row[k]).exists() for k in ('output_directory','profile_directory','training_receipt_directory'))
    inventory=INPUT_OLD/'university_train_content_manifest.json'
    assert sha(inventory)=='c6620e548072d5a9b795018133442986b344820f0fe87af76f362870e4b02da4'
    NEW.mkdir(exist_ok=False)
    INPUT_NEW.mkdir(exist_ok=False)
    replacements={
        'contracts.py':[("'camp_training_preparation'","'camp_training_preparation_v2'"),(OLD_SHA,NEW_SHA)],
        'supervise_training.py':[("'camp_training_inputs'","'camp_training_inputs_v2'")],
        'validate_cpu.py':[("'camp_training_inputs'","'camp_training_inputs_v2'")],
        'run_stage.py':[]}
    diffs=[]
    for filename,pairs in replacements.items():
        before=(OLD/filename).read_bytes()
        after=before
        for find,replacement in pairs:
            assert after.count(find.encode())==1,(filename,find)
            after=after.replace(find.encode(),replacement.encode())
        (NEW/filename).write_bytes(after)
        # Reversing only the named path/hash constants recovers every AST node.
        reverse=after
        for find,replacement in reversed(pairs): reverse=reverse.replace(replacement.encode(),find.encode())
        assert reverse==before
        ast.parse(after.decode('utf-8'))
        diffs.append(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),
            fromfile='camp_training_execution/'+filename,tofile='camp_training_execution_v2/'+filename)))
    doc=(OLD/'README.md').read_text(encoding='utf-8')
    doc=doc.replace('camp_training_preparation','camp_training_preparation_v2').replace('camp_training_inputs','camp_training_inputs_v2').replace(OLD_SHA,NEW_SHA)
    doc+='\n\n## v2记录钩子修复\n\n仅在新的训练适配中将损失观察器传给官方父类的调用修正为 `super().update(val)`。官方父类签名为 `update(self, val)`；模型、loss、优化、采样及超参数保持。三种子计划重新绑定v2，旧v1文件及收据保留。当前目录是准备，尚无release、真实profile、训练或队列登记。精确反例、diff和标准库验证见相邻 `dac_independent_preparation_audit_1520/`。\n'
    (NEW/'README.md').write_text(doc,encoding='utf-8')
    (HERE/'camp_execution_v2.patch').write_text(''.join(diffs),encoding='utf-8',newline='')
    sys.path.insert(0,str(PREPARATION))
    import prepare_or_train as api
    assert Path(api.__file__).resolve().parent==PREPARATION
    bindings=[]
    for seed in (1,2,3):
        old=read(INPUT_OLD/f'seed_{seed}_plan.json')
        out=INPUT_NEW/f'seed_{seed}_plan.json'
        with redirect_stdout(io.StringIO()):
            api.make_plan(SimpleNamespace(plan=str(out), data_manifest=str(inventory),
                pretrained=old['pretrained']['path'],pretrained_sha256=old['pretrained']['sha256'],
                seed=seed,output=old['output_directory']))
        new=read(out)
        transformed=read(INPUT_OLD/f'seed_{seed}_plan.json')
        transformed['created_utc']=new['created_utc']
        transformed['code_manifest']['adapter']['camp_train_runtime.py']='3cbf41ddef34fba1bb1a57f5eca287129748708abb21941f63ff9a5ac40d9b26'
        assert transformed==new,'Unexpected seed plan change'
        bindings.append({'seed':seed,'plan_path':str(out),'plan_sha256':sha(out),
            'old_plan_sha256':sha(INPUT_OLD/f'seed_{seed}_plan.json'),
            'only_semantic_change':'adapter runtime hash (one observer call argument removed)',
            'training_directory_created':Path(new['output_directory']).exists()})
    sys.path.insert(0,str(NEW))
    import supervise_training as supervisor
    assert Path(supervisor.__file__).resolve().parent==NEW
    new_execution=NEW/'execution_plan.json'
    prepared=supervisor.prepare(SimpleNamespace(plan=new_execution,input_directory=INPUT_NEW))
    plan=read(new_execution)
    for key in ('python_executable','preceding_latest_plan_path','preceding_latest_plan_sha256',
                'preceding_extension_plan_sha256','environment_records_sha256','thread_environment',
                'CUDA_VISIBLE_DEVICES','profile_policy','stage_order','checkpoint_selection','profile_use'):
        assert plan[key]==original_plan[key],key
    assert not BLOCKED.intersection(sys.modules)
    for row in original_files: assert sha(OLD/row['path'])==row['sha256']
    for row in original_plan['seeds']: assert sha(row['plan_path'])==row['plan_sha256']
    write(HERE/'CAMP_EXECUTION_V2_DERIVATION.json',{'status':'prepared_not_registered_validation_pending',
        'created_utc':datetime.now(timezone.utc).isoformat(),'new_preparation_sha256':NEW_SHA,
        'new_execution_plan':prepared,'new_seed_bindings':bindings,
        'original_execution_plan_sha256':sha(OLD/'execution_plan.json'),
        'original_execution_manifest_sha256':sha(OLD/'PREPARATION_MANIFEST.json'),
        'new_source_sha256':plan['execution_code_sha256'],
        'diff_sha256':sha(HERE/'camp_execution_v2.patch'),
        'only_execution_code_changes':replacements,
        'original_source_and_seed_plans_unchanged':True,
        'existing_inventory_reused_without_image_scan':{'path':str(inventory),'sha256':sha(inventory)},
        'environment_records_identical':True,'scientific_imports':[],
        'new_release_created':False,'supervisor_started':False,'gpu_profile_or_training':False})
    write(INPUT_NEW/'INPUT_VERIFICATION.json',{'status':'verified_v2_plan_bindings_not_registered',
        'seeds':bindings,'shared_inventory':str(inventory),'shared_inventory_sha256':sha(inventory),
        'original_seed_files_unchanged':True,'no_training_directory_created':True,
        'only_changes_from_original_seeds':'creation timestamp and runtime adapter SHA',
        'environment':read(INPUT_NEW/'seed_1_plan.json')['environment'],
        'scientific_libraries_imported':False,'image_scan_repeated':False})
    print(json.dumps({'execution_plan':str(new_execution),'execution_plan_sha256':sha(new_execution),
        'source_sha256':plan['execution_code_sha256'],'registered':False,'scientific_imports':[]}))

if __name__=='__main__':main()
