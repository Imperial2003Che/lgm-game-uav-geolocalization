"""Derive an isolated successor controller; never edit the registered controllers."""
from pathlib import Path
import difflib, hashlib, json

HERE=Path(__file__).resolve().parent
original=HERE/'supervise_extensions.py'
target=HERE/'supervise_latest_baselines.py'
if target.exists():raise FileExistsError('Preserve existing derived controller')
source=original.read_text(encoding='utf-8')
old="PRECEDING_JOBS = ('formal_aggregate', 'formal_figures', 'cross_dataset_transfer',\n                  'robustness', 'robustness_aggregate', 'query_analysis', 'formal_efficiency_component')"
new="PRECEDING_JOBS = ('real_model_visualizations', 'heldout_height_training',\n                  'heldout_and_seen_height_evaluation', 't1_v3_native_resource_profile_then_7fits_70eval')"
assert source.count(old)==1
result=source.replace(old,new)
changes={
    'registered_extensions_finished_review_pending':'latest_baselines_finished_review_pending',
    'ready_for_extension_preparation':'registered_extensions_finished_review_pending',
    'waiting_for_pipeline':'waiting_for_registered_extensions',
    'running_extensions':'running_latest_baselines',
    'lgm-extension-queue.v1':'lgm-latest-baseline-queue.v1',
    'lgm-extension-execution.v1':'lgm-latest-baseline-execution.v1',
    'extension_plan.json':'latest_baseline_plan.json',
    'extension_supervisor.lock':'latest_baseline_supervisor.lock',
    'extension_status.json':'latest_baseline_status.json',
    'pipeline_status.json':'extension_status.json',
    'extension_logs':'latest_baseline_logs',
    'seven successful stage records':'four successful extension records',
    'Run the registered extension queue after the primary experiment pipeline.':'Run latest author-baseline evaluations after all four registered extensions.',
}
for before,after in changes.items():
    assert before in result,before
    result=result.replace(before,after)
old="    if plan.get('schema') != 'lgm-latest-baseline-queue.v1' or not plan.get('jobs'):"
new="    if plan.get('preceding_extension_plan_sha256') != sha(HERE / 'extension_plan.json'):\n        raise RuntimeError('The prerequisite extension plan changed')\n"+old
assert result.count(old)==1;result=result.replace(old,new)
old="            environment['PYTHONDONTWRITEBYTECODE'] = '1'"
new=old+"\n            environment['PYTHONIOENCODING'] = 'utf-8'\n            for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):\n                environment[variable] = '1'\n            # GPU allocation is granted only after the predecessor gates above.\n            environment['CUDA_VISIBLE_DEVICES'] = '0'"
assert result.count(old)==1;result=result.replace(old,new)
target.write_text(result,encoding='utf-8')
compile(result,str(target),'exec')
(HERE/'latest_baseline_supervisor.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),result.splitlines(True),fromfile=original.name,tofile=target.name)),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
(HERE/'latest_supervisor_derivation.json').write_text(json.dumps(dict(original=str(original),original_sha256=sha(original),derived=str(target),derived_sha256=sha(target),builder_sha256=sha(Path(__file__)),original_unchanged=sha(original)==hashlib.sha256(source.encode()).hexdigest()),indent=2)+'\n',encoding='utf-8')
print(json.dumps({'derived':str(target),'sha256':sha(target)},ensure_ascii=False))
