"""Register reviewed independent comparisons after the existing author queue.

Standard-library preparation only. It neither starts a supervisor nor imports a
scientific library. Standing user authorization is recorded in exact releases;
all children still enforce their real predecessor/process/GPU gates at runtime.
"""
from pathlib import Path
import argparse,copy,datetime,hashlib,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
CONTROLLER=HERE/'supervise_independent_comparisons.py'
EXPECTED_CONTROLLER='0b4678df15c4a1d76cb0665038fe3178bc1838f243439b8d81832e6b8ba6b04d'
LATEST_SHA='80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'
TRAIN_PLAN_SHA='e326c3a0d510aac4f1a788be5ad158a503e850b9503d6a2266a7ca76d9d512e0'
EVAL_SHA='318c96493396d01d75866751c99c794d984db0ef989c22a6b7ccbe1fa96da02e'
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def encoded(obj):return (json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
def write_new(path,data):
    with Path(path).open('xb') as stream:stream.write(data)
def pin(job,path,expected=None):
    path=Path(path).resolve();actual=sha(path)
    if expected is not None and actual!=expected:raise RuntimeError('Source differs before registration: '+str(path))
    previous=job['source_sha256'].get(str(path))
    if previous is not None and previous!=actual:raise RuntimeError('Conflicting source fingerprint')
    job['source_sha256'][str(path)]=actual
def pin_manifest(job,manifest_path,root):
    manifest=read(manifest_path);pin(job,manifest_path)
    for row in manifest['files']:pin(job,Path(root)/row['path'],row['sha256'])

def main(validate_only=False):
    if sha(CONTROLLER)!=EXPECTED_CONTROLLER or sha(HERE/'latest_baseline_plan.json')!=LATEST_SHA:
        raise RuntimeError('Reviewed supervisor or previous queue changed')
    if (HERE/'independent_comparison_plan.json').exists() or (HERE/'independent_comparison_status.json').exists():
        raise RuntimeError('An independent comparison registration already exists; inspect instead of duplicating')
    review=read(HERE/'independent_supervisor_stdlib_review.json')
    if review['passed']!=36 or review['source_sha256']!=EXPECTED_CONTROLLER:raise RuntimeError('Final supervisor review missing')
    # First validate all real preparation artifacts, then create releases/plan.
    matched_dir=HERE/'matched_view_execution'
    matched=read(matched_dir/'prepared_manifest.json')
    if matched['fits']!=6 or matched['checkpoint_task_evaluations']!=12 or matched['status']!='prepared_not_registered':
        raise RuntimeError('Wrong matched-view scope')
    matched_job=copy.deepcopy(read(matched_dir/'queue_job.json'))
    matched_job.pop('status',None)
    pin(matched_job,matched_dir/'prepared_manifest.json')
    pin(matched_job,matched_dir/'queue_job.json')
    matched_release={'schema':'matched-view-release.v1','allow_cuda':True,
        'prepared_sha256':sha(matched_dir/'prepared_manifest.json'),
        'predecessor_plan_sha256':matched['predecessor_plan_sha256']}

    train_dir=HERE/'camp_training_execution';train_path=train_dir/'execution_plan.json'
    if sha(train_path)!=TRAIN_PLAN_SHA:raise RuntimeError('Final CAMP training execution plan changed')
    train=read(train_path)
    train_release_path=train_dir/'release.json'
    train_job={'id':'camp_native_profile_then_3_independent_fits','command':[train['python_executable'],'-B',str(train_dir/'supervise_training.py'),'supervise','--plan',str(train_path),'--release-file',str(train_release_path)],'cwd':str(train_dir),'source_sha256':{}}
    pin(train_job,train_path,TRAIN_PLAN_SHA)
    pin_manifest(train_job,train_dir/'PREPARATION_MANIFEST.json',train_dir)
    prep_dir=HERE/'camp_training_preparation'
    pin_manifest(train_job,prep_dir/'PREPARATION_MANIFEST.json',prep_dir)
    source_pin=read(prep_dir/'SOURCE_PIN.json')
    for row in source_pin['files']:pin(train_job,Path(source_pin['source_directory'])/row['path'],row['sha256'])
    for seed in train['seeds']:
        pin(train_job,seed['plan_path'],seed['plan_sha256'])
        seed_plan=read(seed['plan_path'])
        pin(train_job,seed_plan['data_manifest_path'],seed_plan['data_manifest_sha256'])
        pin(train_job,seed_plan['pretrained']['path'],seed_plan['pretrained']['sha256'])
    for path,fingerprint in train['environment_records_sha256'].items():pin(train_job,path,fingerprint)
    train_release={'schema':'camp-independent-training-execution-release.v1','allow_cuda':True,
        'execution_plan_sha256':TRAIN_PLAN_SHA,'preceding_latest_plan_sha256':LATEST_SHA}

    eval_dir=HERE/'camp_independent_evaluation';handoff=read(eval_dir/'QUEUE_HANDOFF.json')
    eval_job=copy.deepcopy(handoff['job'])
    eval_release_path=Path(handoff['missing_release_to_create_and_pin'])
    eval_release=read(handoff['template']['path'])
    if sha(handoff['template']['path'])!=handoff['template']['sha256']:raise RuntimeError('Evaluation release template changed')
    if eval_release['prepared_sha256']!=EVAL_SHA or eval_release['training_execution_plan_sha256']!=TRAIN_PLAN_SHA:
        raise RuntimeError('Evaluation preparation differs')
    eval_release['allow_cuda']=True
    pin(eval_job,eval_dir/'QUEUE_HANDOFF.json')
    pin_manifest(eval_job,eval_dir/'PREPARATION_MANIFEST.json',eval_dir)
    for path,fingerprint in train['environment_records_sha256'].items():pin(eval_job,path,fingerprint)

    releases=[(matched_job,matched_dir/'release.json',matched_release),
              (train_job,train_release_path,train_release),(eval_job,eval_release_path,eval_release)]
    for job,path,value in releases:
        if path.exists():raise RuntimeError('Release already exists; do not overwrite: '+str(path))
        for filename,expected in job['source_sha256'].items():
            if sha(filename)!=expected:raise RuntimeError('Prepared payload changed: '+filename)
    spec=importlib.util.spec_from_file_location('reviewed_independent_supervisor',CONTROLLER)
    supervisor=importlib.util.module_from_spec(spec);spec.loader.exec_module(supervisor)
    runtimes={};jobs=[matched_job,train_job,eval_job]
    for job in jobs:
        executable=job['command'][0]
        if executable not in runtimes:runtimes[executable]=supervisor.runtime_snapshot(executable)
        job['runtime_snapshot']=runtimes[executable]
    plan={'schema':'lgm-independent-comparison-queue.v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'controller_sha256':EXPECTED_CONTROLLER,'registration_script_sha256':sha(__file__),
        'preceding_status_required':'latest_baselines_finished_review_pending',
        'preceding_latest_plan_sha256':LATEST_SHA,'jobs':jobs,
        'remaining_work':['Actual native-resource profiles and all registered independent fits/evaluations must complete.',
            'Integrate all independently verified results, fair training-view/backbone/pretraining labels, real figures and complete efficiency comparisons.',
            'Finalize and visually verify manuscript/PPT/PDF, upload a new Overleaf project and deliver its usable URL.'],
        'scope':{'independent_fits':9,'matched_view_tasks':12,'camp_independent_tasks':30,
                 'resource_profiles_are_research_results':False,'existing_frozen_queues_modified':False}}
    # Validate real inputs, entrypoints, working directories and runtimes before
    # creating even an authorized release. Missing source cannot leave a half queue.
    supervisor.check_plan(plan)
    if validate_only:
        print(json.dumps({'status':'ready_for_registration_no_files_written','jobs':[job['id'] for job in jobs]},ensure_ascii=True))
        return
    release_artifacts=[]
    for job,path,value in releases:
        blob=encoded(value);write_new(path,blob)
        fingerprint=hashlib.sha256(blob).hexdigest()
        job['source_sha256'][str(path.resolve())]=fingerprint
        release_artifacts.append({'path':str(path),'sha256':fingerprint})
    supervisor.check_plan(plan)
    plan_path=HERE/'independent_comparison_plan.json';write_new(plan_path,encoded(plan))
    receipt={'status':'registered_not_launched','plan':str(plan_path),'plan_sha256':sha(plan_path),
        'job_ids':[job['id'] for job in jobs],'releases':release_artifacts,'scientific_modules_imported':[],
        'existing_latest_plan_sha256':sha(HERE/'latest_baseline_plan.json')}
    assert not any(name in sys.modules for name in ('torch','numpy','scipy','PIL','matplotlib'))
    write_new(HERE/'independent_comparison_registration.json',encoded(receipt))
    print(json.dumps(receipt,ensure_ascii=True))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate-only',action='store_true')
    main(parser.parse_args().validate_only)
