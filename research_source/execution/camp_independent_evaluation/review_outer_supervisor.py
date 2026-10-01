"""Read-only root-controller audit; all process probes are in-memory mocks."""
import ast
import copy
import difflib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
from protocol import HERE,EXECUTION,artifact,load,save,sha,utc

class BlockScientific(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','scipy','matplotlib','cv2','PIL','timm','sklearn','pptx'}:
            raise RuntimeError('Scientific import forbidden')
sys.meta_path.insert(0,BlockScientific());sys.dont_write_bytecode=True
source=EXECUTION/'supervise_independent_comparisons.py'
original=EXECUTION/'supervise_latest_baselines.py'
patch_path=EXECUTION/'independent_supervisor.patch'
review_path=EXECUTION/'independent_supervisor_stdlib_review.json'
spec=importlib.util.spec_from_file_location('_independent_outer_controller_readonly_audit',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
stamp='2026-09-14T00:00:00+00:00'
base={'status':'latest_baselines_finished_review_pending','plan_sha256':'mock_plan',
      'supervisor_pid':100,'supervisor_started_utc':stamp,
      'jobs':[{'id':name,'status':'completed','exit_code':0,'pid':200+i,'started_utc':stamp} for i,name in enumerate(module.PRECEDING_JOBS)]}
observations=[]
def check(name,mutate,expect_rejection=True,live=None):
    fixture=copy.deepcopy(base);mutate(fixture)
    try:
        value=module.preceding_ready(fixture,is_alive=live or (lambda *_:False),expected_plan_sha256='mock_plan')
        outcome='ready' if value else 'wait'
    except (RuntimeError,ValueError,TypeError):outcome='rejected'
    observations.append({'case':name,'observed':outcome,'expected':'rejected' if expect_rejection else 'wait',
                         'passed':outcome==('rejected' if expect_rejection else 'wait')})
check('completed child missing PID',lambda s:s['jobs'][0].pop('pid'))
check('completed child zero PID',lambda s:s['jobs'][0].update(pid=0))
check('completed child negative PID',lambda s:s['jobs'][0].update(pid=-1))
check('completed child bool PID',lambda s:s['jobs'][0].update(pid=True))
check('completed child naive timestamp',lambda s:s['jobs'][0].update(started_utc='2026-09-14T00:00:00'))
check('completed child invalid timestamp',lambda s:s['jobs'][0].update(started_utc='invalid'))
check('supervisor invalid timestamp',lambda s:s.update(supervisor_started_utc='invalid'))
check('wrong predecessor hash',lambda s:s.update(plan_sha256='wrong'))
check('failed author job',lambda s:s['jobs'][1].update(exit_code=1))
check('live author process',lambda s:None,False,lambda pid,*_:pid==200)
check('live predecessor supervisor',lambda s:None,False,lambda pid,*_:pid==100)
new_text=source.read_text(encoding='utf-8');old_text=original.read_text(encoding='utf-8')
expected_patch=''.join(difflib.unified_diff(old_text.splitlines(keepends=True),new_text.splitlines(keepends=True),
                                          fromfile=original.name,tofile=source.name))
registered_review=load(review_path)
tree=ast.parse(new_text)
environment_assignments=[]
for node in ast.walk(tree):
    if isinstance(node,ast.Assign):
        for target in node.targets:
            if isinstance(target,ast.Subscript) and isinstance(target.value,ast.Name) and target.value.id=='environment':
                environment_assignments.append(ast.literal_eval(target.slice))
report={'schema':'independent-comparison-controller-external-review.v1','checked_utc':utc(),
        'reviewer':'literature_tables_0914','sources':[artifact(path) for path in (source,original,patch_path,review_path)],
        'existing_review_check_count':registered_review['passed'],
        'existing_review_matches_current_source':registered_review['source_sha256']==sha(source),
        'patch_exactly_matches_derived_source':expected_patch==patch_path.read_text(encoding='utf-8'),
        'additional_process_identity_fixtures':observations,
        'child_environment_assignments':environment_assignments,
        'resource_environment_left_to_each_runner':set(environment_assignments)=={'PYTHONDONTWRITEBYTECODE','PYTHONIOENCODING'},
        'lifecycle_source_findings':[
            'Existing state is resumed only while waiting; running, failed and completed states are rejected.',
            'Launch intent is persisted before Popen; child is polled to actual exit before advancing.',
            'Nonzero child exit raises and retains the child record; no automatic retry loop exists.',
            'Plans, entrypoints, all registered source hashes and metadata-only runtime are rechecked before every launch.',
            'Private state, lock and log paths preserve all existing controllers and queues.'],
        'scientific_imports':[],'gpu_queries':0,'processes_launched':0,'files_outside_owned_directory_modified':False}
report['status']='passed_read_only_review' if all(row['passed'] for row in observations) and report['patch_exactly_matches_derived_source'] and report['existing_review_matches_current_source'] else 'findings_require_root_review'
destination=HERE/('OUTER_SUPERVISOR_REVIEW_'+sha(source)[:12]+'.json')
save(destination,report)
print(json.dumps({'status':report['status'],'report':str(destination),'failed_cases':[row['case'] for row in observations if not row['passed']]}))
