"""Version the wholly unstarted independent queue after the CAMP observer repair.

Reuse the unchanged matched-view job and its existing exact release. Bind new
CAMP training/evaluation preparations; retain all prior sources and receipts.
This program uses only the standard library and does not launch any GPU job.
"""
from pathlib import Path
import argparse, copy, datetime, hashlib, importlib.util, json, os, sys, uuid

HERE=Path(__file__).resolve().parent
# Exact original queue hash, kept separate from all newly prepared fingerprints.
OLD_PLAN_SHA='a36388bb2a9c81b70c95ee77f7a80f57b7d43ff5c0470eee151bb1a60d9ab235'
OLD_REGISTRAR_SHA='fb304356e09978e84cffb285dc360cdaffd5cbce8e11e6d3941474f82ae1772e'
CONTROLLER_SHA='0b4678df15c4a1d76cb0665038fe3178bc1838f243439b8d81832e6b8ba6b04d'
PREPARATION_V2_SHA='12747158ce2647474c6d24688ba3ebb872ac137118fab7aefd1c1e0ecfad40ec'
LATEST_SHA='80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'
REPAIR=HERE/'camp_observer_repair_20260914'
PLAN_PATH=HERE/'independent_comparison_plan_v2.json'
RECEIPT_PATH=HERE/'independent_comparison_registration_v2.json'
TRANSACTION_PATH=REPAIR/'registration_v2_transaction.json'

def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()
def encoded(value): return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def write_new(path,data):
    with Path(path).open('xb') as stream: stream.write(data)
def update_transaction(value):
    temporary=TRANSACTION_PATH.with_name(TRANSACTION_PATH.name+'.'+uuid.uuid4().hex+'.tmp')
    write_new(temporary,encoded(value));os.replace(temporary,TRANSACTION_PATH)
def positive_pid(value):
    if type(value) is not int or value<=0: raise RuntimeError('Process identity must be a positive integer')
    return value
def aware_time(value):
    if not isinstance(value,str): raise RuntimeError('Process time must be a timezone-aware string')
    parsed=datetime.datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None: raise RuntimeError('Process time lacks timezone')
    return parsed
def pin_manifest(registrar,job,manifest_path,root):
    root=Path(root).resolve(strict=True);manifest_path=Path(manifest_path).resolve(strict=True)
    if manifest_path.parent!=root: raise RuntimeError('Preparation manifest must belong to its root')
    manifest=read(manifest_path);registrar.pin(job,manifest_path)
    seen=set()
    if not isinstance(manifest.get('files'),list) or not manifest['files']: raise RuntimeError('Empty preparation file list')
    for row in manifest['files']:
        relative=Path(row['path'])
        if '..' in relative.parts or (relative.drive and not relative.is_absolute()): raise RuntimeError('Unsafe preparation payload path')
        path=(root/relative).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file() or path in seen: raise RuntimeError('Preparation payload escapes, repeats or is absent')
        seen.add(path);registrar.pin(job,path,row['sha256'])
def load_module(name,path,expected):
    if sha(path)!=expected: raise RuntimeError('Reviewed source changed: '+str(path))
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def verify_retirement(supervisor):
    if PLAN_PATH.exists() or RECEIPT_PATH.exists() or (HERE/'independent_comparison_status.json').exists():
        raise RuntimeError('A current or replacement independent queue exists; do not duplicate')
    if sha(HERE/'independent_comparison_plan.json')!=OLD_PLAN_SHA:
        raise RuntimeError('Prior independent registration changed')
    pause=read(REPAIR/'pause_completed.json'); intent=read(REPAIR/'pause_intent.json')
    if pause.get('status')!='paused_unstarted_for_versioned_observer_repair' or pause.get('main_and_other_successors_untouched') is not True or intent.get('all_jobs_unstarted') is not True:
        raise RuntimeError('A verified unstarted retirement is required')
    retired=Path(pause['retired_state'])
    if retired.resolve()!=(REPAIR/'retired_independent_comparison_status.json').resolve() or sha(retired)!=pause['retired_state_sha256']:
        raise RuntimeError('Retired state evidence differs')
    state=read(retired)
    if state.get('status')!='waiting_for_latest_baselines' or state.get('plan_sha256')!=OLD_PLAN_SHA or len(state.get('jobs',[]))!=3:
        raise RuntimeError('Old queue was not an untouched waiting registration')
    if any(state.get(key) is not None for key in ('surviving_child_pid','active_stage','active_pid')):
        raise RuntimeError('Retired state records a child or an active job')
    for job in state['jobs']:
        execution_fields=('pid','started_utc','finished_utc','exit_code','stdout','stderr','stdout_sha256','stderr_sha256','surviving_child_pid')
        if job.get('status')!='pending' or any(job.get(key) is not None for key in execution_fields):
            raise RuntimeError('Cannot replace a queue with an executed job')
        if any((HERE/'independent_comparison_logs'/(job['id']+suffix)).exists() for suffix in ('.stdout.log','.stderr.log')):
            raise RuntimeError('Old job logs exist; inspect execution history')
    owner=intent['actual_owner']; launcher=intent['launcher']
    owner_pid=positive_pid(owner['ProcessId']);launcher_pid=positive_pid(launcher['ProcessId'])
    if owner_pid!=positive_pid(state.get('supervisor_pid')) or owner_pid!=positive_pid(pause.get('stopped_owner')) or launcher_pid!=positive_pid(pause.get('stopped_launcher')) or positive_pid(owner.get('ParentProcessId'))!=launcher_pid or owner_pid==launcher_pid:
        raise RuntimeError('Retired owner, launcher, parent and pause identities disagree')
    owner_start=aware_time(owner.get('CreationDate')); launcher_start=aware_time(launcher.get('CreationDate'))
    recorded_start=aware_time(state.get('supervisor_started_utc'))
    pause_intent_time=aware_time(intent.get('time'));pause_done_time=aware_time(pause.get('time'))
    if not launcher_start<=owner_start<=recorded_start<=pause_intent_time<=pause_done_time or (recorded_start-owner_start).total_seconds()>60 or (owner_start-launcher_start).total_seconds()>60:
        raise RuntimeError('Retired process creation/start/pause times disagree')
    for record in (owner,launcher):
        if str(HERE/'supervise_independent_comparisons.py').casefold() not in str(record.get('CommandLine','')).casefold():
            raise RuntimeError('Retired process was not this independent supervisor')
        if supervisor.alive(record['ProcessId'],record['CreationDate']):
            raise RuntimeError('A retired queue owner is still alive')
    return pause,state

def build_plan(train_sha,eval_sha):
    registrar=load_module('original_independent_registration',HERE/'register_independent_comparisons.py',OLD_REGISTRAR_SHA)
    supervisor=load_module('reviewed_independent_supervisor',HERE/'supervise_independent_comparisons.py',CONTROLLER_SHA)
    pause,retired=verify_retirement(supervisor)
    old=read(HERE/'independent_comparison_plan.json')
    supervisor.check_plan(old)
    supervisor.check_state_jobs(retired,old)
    if sha(HERE/'latest_baseline_plan.json')!=LATEST_SHA: raise RuntimeError('Preceding author queue changed')
    matched=copy.deepcopy(old['jobs'][0])
    if matched['id']!='matched_two_view_profile_then_6fits_12eval': raise RuntimeError('Unexpected unchanged first job')

    train_dir=HERE/'camp_training_execution_v2'; train_path=train_dir/'execution_plan.json'
    if sha(train_path)!=train_sha: raise RuntimeError('Reviewed v2 training plan changed')
    train=read(train_path)
    if train['preparation_manifest_sha256']!=PREPARATION_V2_SHA or [s['seed'] for s in train['seeds']]!=[1,2,3]:
        raise RuntimeError('Wrong v2 training preparation or seed scope')
    train_release_path=train_dir/'release.json'
    train_job={'id':'camp_native_profile_then_3_independent_fits','command':[train['python_executable'],'-B',str(train_dir/'supervise_training.py'),'supervise','--plan',str(train_path),'--release-file',str(train_release_path)],'cwd':str(train_dir),'source_sha256':{}}
    registrar.pin(train_job,train_path,train_sha)
    pin_manifest(registrar,train_job,train_dir/'PREPARATION_MANIFEST.json',train_dir)
    prep_dir=HERE/'camp_training_preparation_v2'
    registrar.pin(train_job,prep_dir/'PREPARATION_MANIFEST.json',PREPARATION_V2_SHA)
    pin_manifest(registrar,train_job,prep_dir/'PREPARATION_MANIFEST.json',prep_dir)
    source_pin=read(prep_dir/'SOURCE_PIN.json')
    for row in source_pin['files']: registrar.pin(train_job,Path(source_pin['source_directory'])/row['path'],row['sha256'])
    for seed in train['seeds']:
        registrar.pin(train_job,seed['plan_path'],seed['plan_sha256'])
        seed_plan=read(seed['plan_path'])
        registrar.pin(train_job,seed_plan['data_manifest_path'],seed_plan['data_manifest_sha256'])
        registrar.pin(train_job,seed_plan['pretrained']['path'],seed_plan['pretrained']['sha256'])
    for path,digest in train['environment_records_sha256'].items(): registrar.pin(train_job,path,digest)
    train_release={'schema':'camp-independent-training-execution-release.v1','allow_cuda':True,'execution_plan_sha256':train_sha,'preceding_latest_plan_sha256':LATEST_SHA}

    eval_dir=HERE/'camp_independent_evaluation_v3'; handoff=read(eval_dir/'QUEUE_HANDOFF.json')
    eval_job=copy.deepcopy(handoff['job'])
    eval_release_path=Path(handoff['missing_release_to_create_and_pin'])
    if eval_release_path.resolve().parent!=eval_dir.resolve(): raise RuntimeError('Evaluation release outside the new preparation')
    template=handoff['template']; eval_release=read(template['path'])
    if sha(template['path'])!=template['sha256'] or eval_release['prepared_sha256']!=eval_sha or eval_release['training_execution_plan_sha256']!=train_sha:
        raise RuntimeError('Evaluation does not bind the reviewed new preparation and training plan')
    eval_release['allow_cuda']=True
    registrar.pin(eval_job,eval_dir/'QUEUE_HANDOFF.json')
    pin_manifest(registrar,eval_job,eval_dir/'PREPARATION_MANIFEST.json',eval_dir)
    for path,digest in train['environment_records_sha256'].items(): registrar.pin(eval_job,path,digest)
    jobs=[matched,train_job,eval_job]
    runtimes={}
    for job in jobs:
        executable=job['command'][0]
        if executable not in runtimes: runtimes[executable]=supervisor.runtime_snapshot(executable)
        actual=runtimes[executable]
        if job is matched and actual!=job['runtime_snapshot']: raise RuntimeError('Unchanged matched runtime differs')
        job['runtime_snapshot']=actual
    releases=[(train_job,train_release_path,train_release),(eval_job,eval_release_path,eval_release)]
    for job,path,value in releases:
        if path.exists(): raise RuntimeError('New release already exists; do not overwrite: '+str(path))
    plan={'schema':'lgm-independent-comparison-queue.v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'controller_sha256':CONTROLLER_SHA,'registration_script_sha256':sha(__file__),
          'registration_dependency_sha256':{str(HERE/'register_independent_comparisons.py'):OLD_REGISTRAR_SHA},
          'preceding_status_required':'latest_baselines_finished_review_pending','preceding_latest_plan_sha256':LATEST_SHA,
          'jobs':jobs,'remaining_work':old['remaining_work'],'scope':copy.deepcopy(old['scope']),
          'supersedes':{'path':str(HERE/'independent_comparison_plan.json'),'sha256':OLD_PLAN_SHA,
                        'retirement':str(REPAIR/'pause_completed.json'),'retirement_sha256':sha(REPAIR/'pause_completed.json'),
                        'reason':'Fix scalar AverageMeter observer signature before any independent profile, fit or evaluation has executed.',
                        'matched_job_and_release_unchanged':True}}
    if plan['jobs'][0]!=old['jobs'][0]: raise RuntimeError('Matched job must remain byte-semantically identical')
    supervisor.check_plan(plan)
    return plan,releases,supervisor

def main(train_sha,eval_sha,validate_only=False):
    if any(len(value)!=64 or any(c not in '0123456789abcdef' for c in value) for value in (train_sha,eval_sha)):
        raise RuntimeError('Use reviewed full SHA256 values')
    if TRANSACTION_PATH.exists(): raise RuntimeError('A registration transaction already exists; inspect its exact prepared bytes and partial-file hashes before recovery')
    plan,releases,supervisor=build_plan(train_sha,eval_sha)
    if validate_only:
        print(json.dumps({'status':'ready_for_versioned_registration_no_files_written','jobs':[j['id'] for j in plan['jobs']],'matched_unchanged':True}))
        return
    verify_retirement(supervisor)
    release_records=[];prepared_releases=[]
    for job,path,value in releases:
        blob=encoded(value);digest=hashlib.sha256(blob).hexdigest()
        job['source_sha256'][str(path.resolve())]=digest
        release_records.append({'path':str(path),'sha256':digest})
        prepared_releases.append((path,blob))
    prepared_plan_path=REPAIR/'prepared_independent_comparison_plan_v2.json'
    plan_blob=encoded(plan)
    transaction={'status':'intent','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'script_sha256':sha(__file__),'training_plan_sha256':train_sha,'evaluation_prepared_sha256':eval_sha,
        'prepared_plan':str(prepared_plan_path),'prepared_plan_sha256':hashlib.sha256(plan_blob).hexdigest(),
        'target_plan':str(PLAN_PATH),'releases':[{**record,'value':value} for record,(_,_,value) in zip(release_records,releases)],
        'written':[],'recovery_policy':'Never rerun default registration or overwrite files. Verify this prepared plan, every source pin, all existing artifact hashes and unstarted retirement before explicitly completing missing exact artifacts; no scientific job is launched here.'}
    write_new(TRANSACTION_PATH,encoded(transaction))
    try:
        write_new(prepared_plan_path,plan_blob)
        for path,blob in prepared_releases:
            write_new(path,blob)
            transaction['written'].append({'path':str(path),'sha256':sha(path)})
            update_transaction(transaction)
        supervisor.check_plan(plan)
        write_new(PLAN_PATH,plan_blob)
        transaction['written'].append({'path':str(PLAN_PATH),'sha256':sha(PLAN_PATH)});update_transaction(transaction)
        receipt={'status':'registered_not_launched','plan':str(PLAN_PATH),'plan_sha256':sha(PLAN_PATH),
                 'job_ids':[j['id'] for j in plan['jobs']],'new_releases':release_records,
                 'unchanged_matched_release_sha256':sha(HERE/'matched_view_execution/release.json'),
                 'prior_registration_sha256':OLD_PLAN_SHA,'scientific_modules_imported':[]}
        assert not any(name.split('.')[0] in ('torch','numpy','scipy','PIL','matplotlib') for name in sys.modules)
        write_new(RECEIPT_PATH,encoded(receipt))
        transaction['written'].append({'path':str(RECEIPT_PATH),'sha256':sha(RECEIPT_PATH)})
        transaction.update(status='registered_not_launched',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());update_transaction(transaction)
    except BaseException as error:
        transaction.update(status='partial_registration_failed',error=f'{type(error).__name__}: {error}',
            failed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            existing_artifacts=[{'path':str(path),'sha256':sha(path)} for path in [prepared_plan_path,*(p for p,_ in prepared_releases),PLAN_PATH,RECEIPT_PATH] if path.is_file()])
        update_transaction(transaction)
        raise
    print(json.dumps(receipt,ensure_ascii=True))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-plan-sha',required=True)
    parser.add_argument('--evaluation-prepared-sha',required=True)
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args();main(args.training_plan_sha,args.evaluation_prepared_sha,args.validate_only)
