"""Read-only helper counterexamples; NEVER call registrar main or create releases."""
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
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
    pinned_sha=sha(SOURCE)
    module=load('registrar_v2_under_review',SOURCE)
    source_tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
    real_read=module.read
    base_intent=real_read(module.REPAIR/'pause_intent.json')
    base_pause=real_read(module.REPAIR/'pause_completed.json')
    base_state=real_read(base_pause['retired_state'])
    calls=[]
    fake=SimpleNamespace(alive=lambda pid,started:calls.append((pid,started)) or False)
    accepted=[]
    scenarios=[
        ('owner_pid_zero',lambda i,p,s:i['actual_owner'].update(ProcessId=0)),
        ('owner_pid_bool',lambda i,p,s:i['actual_owner'].update(ProcessId=True)),
        ('owner_pid_wrong_other_process',lambda i,p,s:i['actual_owner'].update(ProcessId=123)),
        ('owner_creation_missing',lambda i,p,s:i['actual_owner'].update(CreationDate=None)),
        ('owner_creation_timezone_missing',lambda i,p,s:i['actual_owner'].update(CreationDate='2026-09-14T15:02:28')),
        ('stopped_owner_mismatch',lambda i,p,s:p.update(stopped_owner=123)),
        ('launcher_parent_identity_mismatch',lambda i,p,s:i['actual_owner'].update(ParentProcessId=123)),
        ('retired_surviving_child_unexamined',lambda i,p,s:s.update(surviving_child_pid=234,surviving_child_started_utc='2026-09-14T07:02:28+00:00')),
        ('pending_job_with_failure_exit_code',lambda i,p,s:s['jobs'][0].update(exit_code=1)),
    ]
    actual_sha=module.sha
    for label,mutate in scenarios:
        intent,pause,state=copy.deepcopy(base_intent),copy.deepcopy(base_pause),copy.deepcopy(base_state)
        mutate(intent,pause,state)
        def fixture_read(p):
            p=Path(p)
            if p==module.REPAIR/'pause_intent.json':return intent
            if p==module.REPAIR/'pause_completed.json':return pause
            if p==Path(pause['retired_state']):return state
            return real_read(p)
        # A changed synthetic state is accompanied by its own declared digest;
        # identity/semantic checks must still reject it. No actual evidence is edited.
        calls.clear()
        with patch.object(module,'read',fixture_read):
            try:module.verify_retirement(fake)
            except (RuntimeError,ValueError,TypeError,KeyError) as error:
                accepted.append({'scenario':label,'rejected':True,'error':str(error)})
            else:
                accepted.append({'scenario':label,'rejected':False,'owner_checks':copy.deepcopy(calls)})
    old=load('original_pin_helpers_for_review',EXEC/'register_independent_comparisons.py')
    manifest_counterexamples=[]
    for row_path in ('../outside.py',str(EXEC/'outside.py')):
        writes=[]
        fake_manifest={'files':[{'path':row_path,'sha256':'a'*64}]}
        with patch.object(old,'read',return_value=fake_manifest),patch.object(old,'pin',side_effect=lambda job,path,expected=None:writes.append(str(Path(path).resolve()))):
            old.pin_manifest({'source_sha256':{}},EXEC/'synthetic_root/manifest.json',EXEC/'synthetic_root')
        manifest_counterexamples.append({'row_path':row_path,'pinned_paths':writes,
            'escaped_root':not Path(writes[-1]).is_relative_to(EXEC/'synthetic_root')})
    main_node=next(n for n in source_tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    release_loop=next(n for n in main_node.body if isinstance(n,ast.For) and ast.unparse(n.iter)=='releases')
    assert any(isinstance(n,ast.Call) and ast.unparse(n.func)=='write_new' for n in ast.walk(release_loop))
    assert not any(isinstance(n,ast.Try) for n in ast.walk(main_node))
    findings=[
        {'priority':'P1','title':'Retirement proof does not bind valid actual owner identities',
         'line_start':48,'line_end':62,'counterexamples':accepted,
         'recommendation':'Require int not bool positive PID, timezone-aware creation time, exact ownerPID=retired supervisorPID=pause stopped_owner, launcherPID=pause stopped_launcher=owner ParentProcessId, intent all_jobs_unstarted True. Require recorded starts compatible with actual evidence and inspect recursive owner/child fields plus no active/finished/failed job evidence.'},
        {'priority':'P2','title':'Reused manifest helper accepts absolute/traversal payload paths',
         'line_start':78,'line_end':82,'counterexamples':manifest_counterexamples,
         'recommendation':'Before old pin_manifest, require exact reviewed manifestSHA when available, unique nonabsolute paths resolving inside the expected root, declared size/hash and execution-code equality. Validate evaluator command and --release-file equals the new controlled release path.'},
        {'priority':'P2','title':'Two release writes have no partial-commit receipt or immediate final retirement check',
         'line_start':137,'line_end':149,
         'evidence':'AST shows sequential write_new calls in release loop, then check_plan, plan write and receipt write with no try/failure record. A later write/check failure leaves earlier active release without a new plan or transaction failure record.',
         'recommendation':'Preflight and recheck retirement immediately before exclusive journaled registration; pin hashes of intended release bytes before writes; validate plan against planned bytes; retain transaction intent and written-file SHA after every step; on exception write failure receipt listing actually created files. Reject/explicitly recover existing incomplete transaction; never automatically overwrite/delete its evidence. No plan/no live supervisor means this is a recovery gap, not evidence that GPU execution occurred.'},
    ]
    assert sha(SOURCE)==pinned_sha
    assert not BLOCKED.intersection(sys.modules)
    report={'status':'changes_requested','reviewed_source':str(SOURCE),'reviewed_sha256':pinned_sha,
        'reviewed_utc':datetime.now(timezone.utc).isoformat(),'findings':findings,
        'tested':'verify_retirement and original pin_manifest with synthetic read/owner/pin mocks only; static AST of main, never executed main',
        'science_imports':[],'gpu_calls':False,'release_created':False,'current_evidence_modified':False,
        'evaluation_v3_status':'Not final at review time; real build_plan/check-plan will be root responsibility after fixes and final eval SHA.'}
    (HERE/'INITIAL_REVIEW.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'sha256':pinned_sha,'findings':len(findings),'accepted_bad_retirement_scenarios':sum(not x['rejected'] for x in accepted)}))

if __name__=='__main__':main()
