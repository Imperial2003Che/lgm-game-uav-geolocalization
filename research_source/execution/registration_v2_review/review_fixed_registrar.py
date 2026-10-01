"""Pure stdlib checks; registration body runs only against an in-memory filesystem.

Never invoke the actual registrar main, write a real release, or launch a process.
"""
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
from contextlib import redirect_stdout
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
EXEC=HERE.parent
SOURCE=EXEC/'register_independent_comparisons_v2.py'
BLOCKED={'torch','torchvision','numpy','scipy','matplotlib','PIL','cv2','timm','albumentations'}
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path,target=None):
        if fullname.split('.')[0] in BLOCKED:raise AssertionError('Scientific import attempted '+fullname)
sys.meta_path.insert(0,Guard())

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    source_sha=sha(SOURCE)
    module=load('fixed_registrar_under_review',SOURCE)
    source_tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
    real_read=module.read
    base_intent=real_read(module.REPAIR/'pause_intent.json')
    base_pause=real_read(module.REPAIR/'pause_completed.json')
    base_state=real_read(base_pause['retired_state'])
    checks=[]
    def passed(name):checks.append(name)
    fake=SimpleNamespace(alive=lambda pid,started:False)
    module.verify_retirement(fake)
    passed('Actual retained pause/state/command evidence passes with mocked exited owners')
    scenarios=[
        ('owner_pid_zero',lambda i,p,s:i['actual_owner'].update(ProcessId=0)),
        ('owner_pid_bool',lambda i,p,s:i['actual_owner'].update(ProcessId=True)),
        ('owner_pid_wrong_other_process',lambda i,p,s:i['actual_owner'].update(ProcessId=123)),
        ('owner_creation_missing',lambda i,p,s:i['actual_owner'].update(CreationDate=None)),
        ('owner_creation_timezone_missing',lambda i,p,s:i['actual_owner'].update(CreationDate='2026-09-14T15:02:28')),
        ('stopped_owner_mismatch',lambda i,p,s:p.update(stopped_owner=123)),
        ('launcher_parent_identity_mismatch',lambda i,p,s:i['actual_owner'].update(ParentProcessId=123)),
        ('retired_surviving_child_unexamined',lambda i,p,s:s.update(surviving_child_pid=234)),
        ('pending_job_with_failure_exit_code',lambda i,p,s:s['jobs'][0].update(exit_code=1)),
        ('job_started',lambda i,p,s:s['jobs'][0].update(started_utc='2026-09-14T07:02:28+00:00')),
        ('job_finished',lambda i,p,s:s['jobs'][0].update(finished_utc='2026-09-14T07:02:28+00:00')),
        ('job_stdout',lambda i,p,s:s['jobs'][0].update(stdout='not-started-claim-is-false.log')),
        ('missing_unstarted_attestation',lambda i,p,s:i.update(all_jobs_unstarted=None)),
        ('wrong_owner_command',lambda i,p,s:i['actual_owner'].update(CommandLine='python other.py')),
        ('launcher_after_owner',lambda i,p,s:i['launcher'].update(CreationDate='2026-09-14T16:00:00+08:00')),
        ('active_stage',lambda i,p,s:s.update(active_stage='first_stage')),
    ]
    results=[]
    actual_sha=module.sha
    for label,mutate in scenarios:
        intent,pause,state=copy.deepcopy(base_intent),copy.deepcopy(base_pause),copy.deepcopy(base_state)
        mutate(intent,pause,state)
        # Model a self-consistent content hash for the synthetic state so the
        # semantic identity checks, rather than a trivial stale hash, reject it.
        synthetic_digest=hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest()
        pause['retired_state_sha256']=synthetic_digest
        def fixture_read(p):
            p=Path(p)
            if p==module.REPAIR/'pause_intent.json':return intent
            if p==module.REPAIR/'pause_completed.json':return pause
            if p==Path(pause['retired_state']):return state
            return real_read(p)
        def fixture_sha(p):
            return synthetic_digest if Path(p)==Path(pause['retired_state']) else actual_sha(p)
        with patch.object(module,'read',fixture_read),patch.object(module,'sha',fixture_sha):
            try:module.verify_retirement(fake)
            except (RuntimeError,ValueError,TypeError,KeyError) as error:
                results.append({'scenario':label,'rejected':True,'error':str(error)})
            else:raise AssertionError('Bad retirement accepted: '+label)
        passed('Retirement rejects '+label)
    try:module.verify_retirement(SimpleNamespace(alive=lambda *args:True))
    except RuntimeError as error:assert 'still alive' in str(error)
    else:raise AssertionError('Live old owner accepted')
    passed('Live old owner rejected')
    real_exists=Path.exists
    for blocker in (module.PLAN_PATH,module.RECEIPT_PATH,module.HERE/'independent_comparison_status.json'):
        with patch.object(Path,'exists',lambda p:True if p==blocker else real_exists(p)):
            try:module.verify_retirement(fake)
            except RuntimeError as error:assert 'duplicate' in str(error)
            else:raise AssertionError('Existing registration blocker accepted')
        passed('Existing artifact blocks retirement: '+blocker.name)
    with tempfile.TemporaryDirectory(prefix='manifest_fixture_',dir=HERE) as temp:
        folder=Path(temp)
        inside=folder/'source.py';inside.write_text('# scalar fixture\n',encoding='utf-8')
        manifest=folder/'manifest.json';manifest.write_text('{}',encoding='utf-8')
        rows=[{'path':'source.py','sha256':sha(inside)}]
        calls=[]
        registrar=SimpleNamespace(pin=lambda *args:calls.append(args))
        with patch.object(module,'read',return_value={'files':rows}):module.pin_manifest(registrar,{'source_sha256':{}},manifest,folder)
        assert len(calls)==2
        passed('Contained unique manifest accepted')
        with patch.object(module,'read',return_value={'files':[{'path':str(inside),'sha256':sha(inside)}]}):
            module.pin_manifest(registrar,{'source_sha256':{}},manifest,folder)
        passed('Contained absolute manifest payload accepted')
        for label,test_rows in [('relative_escape',[{'path':'../outside.py','sha256':'a'*64}]),
                                ('absolute_escape',[{'path':str(EXEC/'outside.py'),'sha256':'a'*64}]),
                                ('drive_relative',[{'path':'C:outside.py','sha256':'a'*64}]),
                                ('duplicate',rows+rows),('empty',[])]:
            with patch.object(module,'read',return_value={'files':test_rows}):
                try:module.pin_manifest(registrar,{'source_sha256':{}},manifest,folder)
                except (RuntimeError,OSError):pass
                else:raise AssertionError('Unsafe manifest accepted '+label)
            passed('Manifest rejects '+label)
        # Simulate Windows junction/symlink resolution while keeping all writes local.
        original_resolve=Path.resolve
        def redirected_resolve(p,*args,**kwargs):
            if p==inside:return EXEC/'outside.py'
            return original_resolve(p,*args,**kwargs)
        with patch.object(module,'read',return_value={'files':rows}),patch.object(Path,'resolve',redirected_resolve):
            try:module.pin_manifest(registrar,{'source_sha256':{}},manifest,folder)
            except RuntimeError:pass
            else:raise AssertionError('Resolved junction escape accepted')
        passed('Manifest rejects resolved symlink or junction escape')

    # Compile a renamed copy of main and update_transaction. Globals below route
    # every read/write/existence/replace into a dict. The real main is never called.
    main_ast=copy.deepcopy(next(n for n in source_tree.body if isinstance(n,ast.FunctionDef) and n.name=='main'))
    main_ast.name='memory_registration_body'
    update_ast=copy.deepcopy(next(n for n in source_tree.body if isinstance(n,ast.FunctionDef) and n.name=='update_transaction'))
    transactions=[]
    for scenario in ('success','second_release_failure','post_release_check_failure','receipt_failure','journal_replace_failure','existing_transaction','existing_second_release','late_retirement_failure'):
        memory={}
        class MemoryPath:
            def __init__(self,path):self.path=str(path)
            def __truediv__(self,s):return MemoryPath(str(PurePosixPath(self.path)/s))
            def __str__(self):return self.path
            def resolve(self):return self
            def exists(self):return self.path in memory
            def is_file(self):return self.exists()
            def with_suffix(self,s):return MemoryPath(str(PurePosixPath(self.path).with_suffix(s)))
            def with_name(self,s):return MemoryPath(str(PurePosixPath(self.path).with_name(s)))
            @property
            def name(self):return PurePosixPath(self.path).name
        root=MemoryPath('/memory')
        repair=root/'repair';transaction=repair/'registration_v2_transaction.json'
        plan_path=root/'new_plan.json';receipt_path=root/'new_receipt.json'
        train_release=root/'train_release.json';eval_release=root/'eval_release.json'
        initial_sha='a'*64
        memory[str(root/'matched_view_execution'/'release.json')]=b'unchanged matched release'
        if scenario=='existing_transaction':memory[str(transaction)]=b'old transaction'
        if scenario=='existing_second_release':memory[str(eval_release)]=b'previous release must remain'
        events=[]
        def fake_write(path,data):
            key=str(path)
            if key in memory:raise FileExistsError('Refuse to overwrite '+key)
            if scenario=='second_release_failure' and key==str(eval_release):raise OSError('synthetic second release I/O failure')
            if scenario=='receipt_failure' and key==str(receipt_path):raise OSError('synthetic receipt I/O failure')
            memory[key]=bytes(data);events.append(('write',key))
        replace_attempts=[]
        def fake_replace(src,dst):
            replace_attempts.append((str(src),str(dst)))
            if scenario=='journal_replace_failure' and len(replace_attempts)==1:
                raise OSError('synthetic journal atomic replace failure with temporary retained')
            memory[str(dst)]=memory.pop(str(src));events.append(('replace',str(dst)))
        def fake_sha(path):
            if str(path)==str(SOURCE):return source_sha
            return hashlib.sha256(memory[str(path)]).hexdigest()
        def fake_check(plan):
            events.append(('check_plan',''))
            if scenario=='post_release_check_failure':raise RuntimeError('synthetic post-write pin mismatch')
            for job in plan['jobs']:
                for path,digest in job.get('source_sha256',{}).items():assert fake_sha(path)==digest
        def fake_build(*args):
            jobs=[{'id':'matched','source_sha256':{}},{'id':'camp_train','source_sha256':{}},{'id':'camp_eval','source_sha256':{}}]
            plan={'jobs':jobs,'scope':{'independent_fits':9}}
            return plan,[(jobs[1],train_release,{'allow_cuda':True,'fixture_only':True}),
                         (jobs[2],eval_release,{'allow_cuda':True,'fixture_only':True})],SimpleNamespace(check_plan=fake_check)
        def fake_retirement(*args):
            events.append(('verify_retirement',''))
            if scenario=='late_retirement_failure':raise RuntimeError('synthetic newly active old owner')
        scope=dict(module.__dict__)
        scope.update(HERE=root,REPAIR=repair,TRANSACTION_PATH=transaction,PLAN_PATH=plan_path,
            RECEIPT_PATH=receipt_path,build_plan=fake_build,verify_retirement=fake_retirement,
            write_new=fake_write,sha=fake_sha,os=SimpleNamespace(replace=fake_replace))
        exec(compile(ast.Module(body=[update_ast,main_ast],type_ignores=[]),'memory-only-registration-body','exec'),scope)
        failed=None
        try:
            with redirect_stdout(io.StringIO()):scope['memory_registration_body']('a'*64,'b'*64)
        except (OSError,RuntimeError) as error:failed=str(error)
        if scenario=='success':
            assert failed is None
            journal=json.loads(memory[str(transaction)])
            assert journal['status']=='registered_not_launched' and len(journal['written'])==4
            assert journal['prepared_plan_sha256']==hashlib.sha256(memory[str(plan_path)]).hexdigest()
            assert memory[journal['prepared_plan']]==memory[str(plan_path)]
            assert all(fake_sha(x['path'])==x['sha256'] for x in journal['written'])
            assert events[0][0]=='verify_retirement'
        elif scenario=='existing_transaction':
            assert failed and memory[str(transaction)]==b'old transaction' and not events
            journal=None
        elif scenario=='late_retirement_failure':
            assert failed and not transaction.exists() and not train_release.exists()
            journal=None
        else:
            assert failed
            journal=json.loads(memory[str(transaction)])
            assert journal['status']=='partial_registration_failed'
            assert all(fake_sha(x['path'])==x['sha256'] for x in journal['existing_artifacts'])
            if scenario in ('second_release_failure','existing_second_release','post_release_check_failure','journal_replace_failure'):assert not plan_path.exists()
            if scenario=='existing_second_release':assert memory[str(eval_release)]==b'previous release must remain'
            if scenario=='journal_replace_failure':
                assert len(replace_attempts)==2 and replace_attempts[0][0]!=replace_attempts[1][0]
                assert replace_attempts[0][0] in memory
            # Any retry is blocked by the retained intent/failure transaction.
            before=dict(memory)
            try:scope['memory_registration_body']('a'*64,'b'*64)
            except RuntimeError as error:assert 'transaction already exists' in str(error)
            else:raise AssertionError('Default retry should be blocked')
            assert before==memory
        transactions.append({'scenario':scenario,'error':failed,'journal_status':journal['status'] if journal else None,
            'memory_file_names':sorted(memory),'real_files_written':False})
        passed('In-memory exact transaction body: '+scenario)
    assert sha(SOURCE)==source_sha
    assert not BLOCKED.intersection(sys.modules)
    report={'status':'passed','reviewed_source':str(SOURCE),'reviewed_sha256':source_sha,
        'reviewed_utc':datetime.now(timezone.utc).isoformat(),'check_count':len(checks),'checks':checks,
        'retirement_counterexamples':results,'transaction_fault_injection':transactions,
        'findings':[], 'real_registrar_main_called':False,'actual_active_release_created':False,
        'scientific_imports':[],'gpu_calls':False,'existing_registration_files_modified':False,
        'runtime_validation_scope':'Root performs real validate-only/check-plan against final training and eval preparations; this independent review checks helpers and exact transaction AST with a memory-only filesystem.'}
    (HERE/'FIXED_REVIEW.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'passed','reviewed_sha256':source_sha,'checks':len(checks)}))

if __name__=='__main__':main()
