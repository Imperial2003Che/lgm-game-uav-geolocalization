"""Register the two CPU-verified author evaluations without changing prior queues."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('latest_controller',HERE/'supervise_latest_baselines.py')
controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
read,sha=controller.read,controller.sha
def put(path,value):
    with Path(path).open('x',encoding='utf-8') as handle:json.dump(value,handle,ensure_ascii=False,indent=2)
plan_path=HERE/'latest_baseline_plan.json'
if plan_path.exists():raise FileExistsError('Do not overwrite registered latest-baseline plan')
review=read(HERE/'latest_supervisor_review.json')
assert review['reviewed_source_sha256']==sha(HERE/'supervise_latest_baselines.py')
assert not review.get('findings') and all(x['passed'] for x in review['fixtures'])
environment_path=HERE/'camp_preparation/environment/camp_environment_ready.json'
environment=read(environment_path)
assert environment['status']=='ready_cpu_verified' and environment['final_package_count']==70
python=environment['python'];runtime=controller.runtime_snapshot(python)
preceding_sha=sha(HERE/'extension_plan.json')
preserved={str(p):sha(p) for p in (HERE/'continue_formal_matrix.py',HERE/'supervise_pipeline.py',HERE/'supervise_extensions.py',HERE/'extension_plan.json')}

configs=[dict(name='camp',prepared=HERE/'camp_preparation/preparations/20260914T045031917075Z/manifest.json',expected='ddb8a3029557a1039c005e94648d40bf95397ee7b84cad0f33ab6dcacfaa1ec7'),
         dict(name='dac',prepared=HERE/'dac_preparation/preparations/20260914T045232800767Z/manifest.json',expected='c2d3dd28731eb21177ed84d5355afc3410cab72f4bc1026a949892cfefbcde40')]
jobs=[]
for config in configs:
    name=config['name'];prepared=config['prepared']
    assert sha(prepared)==config['expected']
    manifest=read(prepared)
    assert manifest['task_count']==10 and manifest['unique_images']==131062
    assert manifest['python']==python
    directory=HERE/(name+'_preparation')
    script=directory/('run_'+name+'_author_evaluation.py')
    release=prepared.with_name('release.json')
    put(release,dict(schema=name+'-author-checkpoint-release.v1',allow_cuda=True,
        prepared_manifest_sha256=sha(prepared),preceding_extension_plan_sha256=preceding_sha,
        registered_utc=datetime.now(timezone.utc).isoformat(),
        release_note='Standing user authorization for the complete real experiment pipeline. This job may execute only after all previously registered extensions finish and every recorded process exits; the evaluator independently enforces these gates and holds the shared GPU lock.'))
    pins={}
    def collect_artifacts(value):
        if isinstance(value,dict):
            if {'path','sha256'}<=value.keys():
                path=Path(value['path'])
                if path.is_file():
                    assert sha(path)==value['sha256'],str(path)
                    pins[str(path.resolve())]=value['sha256']
            for entry in value.values():collect_artifacts(entry)
        elif isinstance(value,list):
            for entry in value:collect_artifacts(entry)
    collect_artifacts(manifest)
    for path in (prepared,script,release,environment_path,directory/'source_pins.json'):
        pins[str(path.resolve())]=sha(path)
    for row in environment['records']:
        path=Path(environment['environment_root'])/row['path']
        assert sha(path)==row['sha256'];pins[str(path.resolve())]=row['sha256']
    job=dict(id=name+'_author_checkpoint_full_gallery_10tasks',
        command=[python,'-B',str(script),'--stage','evaluate','--prepared',str(prepared),'--release-file',str(release)],
        cwd=str(directory),source_sha256=pins,runtime_snapshot=runtime,
        scientific_result_type='author checkpoint, locally re-evaluated; not independent training',
        tasks='University-1652 D2S/S2D and University-to-SUES transfer at four heights in both directions; all gallery distractors retained',
        status_at_registration='Prepared and CPU verified; no evaluation metrics produced')
    jobs.append(job)
plan=dict(schema='lgm-latest-baseline-queue.v1',created_utc=datetime.now(timezone.utc).isoformat(),
    controller_sha256=sha(HERE/'supervise_latest_baselines.py'),preceding_status_required='registered_extensions_finished_review_pending',
    preceding_extension_plan_sha256=preceding_sha,jobs=jobs,
    remaining_work=['CAMP full independent training: real native-batch resource profile, all registered seeds, final checkpoints and evaluations.',
        'DAC independent training adapter and resource verification; latest source comparisons and complete matched efficiency table.',
        'Six separately registered University two-view V/full seed controls for fair external-method comparison.',
        'All genuine numeric outputs, final model figures, full manuscript integration, review package and Overleaf upload.'])
controller.check_plan(plan)
put(plan_path,plan)
assert {p:sha(p) for p in preserved}==preserved
put(HERE/'latest_baseline_registration.json',dict(status='registered_not_launched',plan=str(plan_path),plan_sha256=sha(plan_path),
    jobs=[x['id'] for x in jobs],tasks=20,pinned_files=[len(x['source_sha256']) for x in jobs],
    cpu_review_sha256=sha(HERE/'latest_supervisor_review.json'),environment_ready_sha256=sha(environment_path),
    preserved_prior_sources=preserved,gpu_experiments_started=False,registered_utc=datetime.now(timezone.utc).isoformat()))
print(json.dumps({'plan':str(plan_path),'sha256':sha(plan_path),'jobs':2,'tasks':20},ensure_ascii=False))
