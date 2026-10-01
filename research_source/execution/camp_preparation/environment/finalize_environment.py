"""Freeze the independently checked CAMP/DAC runtime without importing ML libraries."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('preparation_helpers',HERE/'prepare_environment.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
read,sha,put=module.read,module.sha,module.put
ready=HERE/'camp_environment_ready.json'
if ready.exists():raise FileExistsError('Do not overwrite a frozen runtime record')
before=read('source_before.json');installed=read('camp_environment_packages.json')
assert module.fingerprint(module.SOURCE)==before
assert module.fingerprint(module.TARGET)==installed
module.check_versions(installed)
assert len(installed['packages'])==70 and len(before['packages'])==53
for row in installed['records']:
    assert sha(module.TARGET/row['path'])==row['sha256']
execution=HERE.parents[1]
evidence_paths=[execution/'camp_training_preparation/REAL_PAIR_CPU_adapter_reader.json',
                execution/'camp_preparation/cpu_semantic_validation.json',
                execution/'dac_preparation/cpu_semantic_validation.json']
evidence=[]
def verify_no_cuda(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ('cuda_initialized','gpu_execution'):assert item is False
            verify_no_cuda(item)
    elif isinstance(value,list):
        for item in value:verify_no_cuda(item)
for path in evidence_paths:
    value=json.loads(path.read_text(encoding='utf-8'))
    assert value['status']=='passed'
    verify_no_cuda(value)
    evidence.append(dict(path=str(path),sha256=sha(path)))
pair=json.loads(evidence_paths[0].read_text(encoding='utf-8'))
assert Path(pair['sys_prefix']).resolve()==module.TARGET.resolve()
for item in pair['runtime_environment'].values():
    assert Path(item['origin']).resolve().is_relative_to(module.TARGET.resolve())
put('camp_environment_ready.json',dict(status='ready_cpu_verified',created_utc=datetime.now(timezone.utc).isoformat(),
    python=str(module.TARGET/'Scripts/python.exe'),environment_root=str(module.TARGET),
    methods=['CAMP','DAC'],environment_type='locally adapted; neither official source provides a locked environment',
    source_environment=str(module.SOURCE),source_environment_unchanged=True,original_package_count=53,final_package_count=70,
    copied_files=read('copy_status.json')['files'],copied_bytes=read('copy_status.json')['bytes'],
    copied_manifest_sha256=sha(HERE/'copied_file_manifest.json'),packages=installed['packages'],records=installed['records'],
    wheels=read('planned_additions.json')['additions'],pip_report_sha256=sha(HERE/'pip_install_report.json'),
    cpu_evidence=evidence,actual_module_origins=pair['runtime_environment'],
    inherited_core_versions=dict(numpy='2.4.4',pillow='12.2.0',torch='2.11.0+cu126',torchvision='0.26.0+cu126'),
    fixed_process_threads={'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'},
    source_invariance_sha256=sha(HERE/'source_after.json'),future_mutation_policy='Do not install or upgrade in this runtime after preparation manifests are frozen; create a new versioned environment instead.',
    finalize_script_sha256=sha(Path(__file__)),gpu_experiments_executed=False))
print(json.dumps(dict(path=str(ready),sha256=sha(ready),status='ready_cpu_verified'),ensure_ascii=False))
