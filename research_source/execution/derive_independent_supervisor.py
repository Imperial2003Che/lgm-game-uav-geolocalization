"""Derive a separate successor controller without modifying registered queues."""
from pathlib import Path
import ast,difflib,hashlib,json

HERE=Path(__file__).resolve().parent
source=HERE/'supervise_latest_baselines.py'
target=HERE/'supervise_independent_comparisons.py'
expected='d102ad89c2aa1e029f70c9b9c18c8780d402f3a18d81272b5ffa1982e4ea5453'
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
assert not target.exists(), 'Do not overwrite a prepared successor'
before=source.read_text(encoding='utf-8')
text=before
old="PRECEDING_JOBS = ('real_model_visualizations', 'heldout_height_training',\n                  'heldout_and_seen_height_evaluation', 't1_v3_native_resource_profile_then_7fits_70eval')"
new="PRECEDING_JOBS = ('camp_author_checkpoint_full_gallery_10tasks',\n                  'dac_author_checkpoint_full_gallery_10tasks')"
assert text.count(old)==1
text=text.replace(old,new)
replacements=[
 ('Run latest author-baseline evaluations after all four registered extensions.', 'Run independently trained comparisons after the two author-checkpoint evaluations.'),
 ('preceding_extension_plan_sha256','preceding_latest_plan_sha256'),
 ('extension_plan.json','latest_baseline_plan.json'),
 ('latest_baseline_plan.json','independent_comparison_plan.json'),
 ('registered_extensions_finished_review_pending','latest_baselines_finished_review_pending'),
 ('waiting_for_registered_extensions','waiting_for_latest_baselines'),
 ("read(HERE / 'extension_status.json')","read(HERE / 'latest_baseline_status.json')"),
 ("sha(HERE / 'extension_status.json')","sha(HERE / 'latest_baseline_status.json')"),
 ('latest_baseline_supervisor.lock','independent_comparison_supervisor.lock'),
 ("path = HERE / 'latest_baseline_status.json'","path = HERE / 'independent_comparison_status.json'"),
 ('lgm-latest-baseline-queue.v1','lgm-independent-comparison-queue.v1'),
 ('lgm-latest-baseline-execution.v1','lgm-independent-comparison-execution.v1'),
 ('running_latest_baselines','running_independent_comparisons'),
 ("logs = HERE / 'latest_baseline_logs'","logs = HERE / 'independent_comparison_logs'"),
 ('four successful extension records','two successful author-checkpoint evaluation records'),
 ]
# Distinguish the predecessor plan from this controller's own plan explicitly.
for old,new in replacements:
    assert old in text, old
    text=text.replace(old,new)
text=text.replace("sha(HERE / 'independent_comparison_plan.json')","sha(HERE / 'latest_baseline_plan.json')")
text=text.replace("state.update(status='latest_baselines_finished_review_pending', finished_utc=utc())",
                  "state.update(status='independent_comparisons_finished_review_pending', finished_utc=utc())")
# Resource threads belong to each frozen experiment, not to this outer queue.
# CAMP's inner runner sets its registered resource environment; matched-view
# training inherits exactly the same host variables as the original main fit.
old="            for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):\n                environment[variable] = '1'\n            # GPU allocation is granted only after the predecessor gates above.\n            environment['CUDA_VISIBLE_DEVICES'] = '0'\n"
assert old in text
text=text.replace(old,"            # Each experiment controls its own frozen resource environment.\n")
ast.parse(text)
assert "plan.get('preceding_latest_plan_sha256') != sha(HERE / 'latest_baseline_plan.json')" in text
assert "default=HERE / 'independent_comparison_plan.json'" in text
target.write_text(text,encoding='utf-8',newline='\n')
diff=''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile=source.name,tofile=target.name))
(HERE/'independent_supervisor.patch').write_text(diff,encoding='utf-8',newline='\n')
report={'source':str(source),'source_sha256':expected,'derived':str(target),'derived_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'changes':'Separate predecessor IDs/plan/status/lock/logs and successor namespace; inherit experiment resource environment. Existing queues unchanged.','status':'derived_not_registered'}
(HERE/'independent_supervisor_derivation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
