"""CPU-only negative fixtures. Fake checkpoint bytes are test data, never results."""
import ast
from contextlib import ExitStack
import copy
import importlib.abc
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','PIL','scipy','timm','cv2','albumentations','transformers'}:
            raise RuntimeError('Scientific import forbidden in stdlib preparation: '+fullname)
sys.meta_path.insert(0,NoScience())
import dac6_contracts as d
import run_six_stages as run
import stage_entry

results=[]
def check(name,fn,reject=False):
    try:fn()
    except (RuntimeError,ValueError,KeyError,FileNotFoundError,TypeError) as error:
        if not reject:raise
        results.append({'name':name,'passed':True,'rejected':type(error).__name__});return
    if reject:raise AssertionError('Negative fixture admitted: '+name)
    results.append({'name':name,'passed':True})

def equal(a,b):d.require(a==b,'Fixture value mismatch')

def train_fixture(root):
    output=root/'train';inputs=root/'inputs';output.mkdir();inputs.mkdir()
    plan={'seed':1,'output_directory':str(output),'data_manifest_sha256':'',
        'science_binding':{'fixture_science_hash':'a'*64},'control_binding':{'fixture_control_hash':'b'*64},'environment':{'fixture_environment':'stdlib'},}
    d.c.write(output/'data_manifest.json',{'test_data_only':True});plan['data_manifest_sha256']=d.sha(output/'data_manifest.json')
    d.c.write(root/'plan.json',plan);pb=d.c.Bound.load(root/'plan.json',d.sha(root/'plan.json'));pb.copy(output/'plan.json')
    status={'status':'completed','epoch_completed':1,'pid':222,'started_utc':'2026-01-01T01:00:00+00:00',
        'actual_adamw_steps':1,'optimizer_step_attempts':1,'amp_skips':0}
    evidence={'actual_adamw_steps':1,'attempted_batches':1,'amp_skips':0,'epoch_loss':1.2,
        'all_model_floating_state_finite':True,'initial_parameter_sha256':'a'*64,'final_parameter_sha256':'b'*64,
        'representative_parameter_changed':True,'final_scaler_state':{'scale':1024}}
    protocol={'method':'DAC','model_state_count':402,'epoch':1,'actual_adamw_steps':1,'actual_loader_batches':1,
        'scheduler_attempts':1,'optimizer_step_max':1,'amp_skips':0,'all_optimizer_moments_finite':True,'test_set_read_or_model_selection':False,
        'scheduler_steps_planned_before_shuffle':1578,'warmup_steps_planned_before_shuffle':157.8}
    order=[[n,'satellite','drone'] for n in range(24)]
    objects={'status.json':status,'training_evidence.json':evidence,'dac_training_protocol_evidence.json':protocol,
        'code_manifest.json':{'science':plan['science_binding'],'control':plan['control_binding']},
        'environment_manifest.json':plan['environment'],'effective_configuration.json':{'seed':1},
        'epoch01_sample_order.json':order,'initial_parameter_evidence.json':{'sha256':'a'*64}}
    for name,value in objects.items():d.c.write(output/name,value)
    d.c.write(inputs/'seed_1_effective_configuration.json',{'seed':1})
    sampling={'official_pair_count':37854,'nominal_pairs_per_batch':24,'expected_batches':1,'sample_count':24,
        'excluded_tail_pairs':37830,'sample_order_sha256':d.sha(output/'epoch01_sample_order.json')}
    d.c.write(output/'epoch01_sampling.json',sampling)
    batch={'epoch':1,'batch_attempt':1,'actual_optimizer_steps':1,'optimizer_updated_this_batch':True,
        'amp_skips':0,'loss_finite':True,'loss':1.2,'scale_after_update':1024,'lr_after_scheduler':.001}
    (output/'batch_progress.jsonl').write_text(json.dumps(batch)+'\n',encoding='utf-8')
    for name in ('runtime_environment.json','stage_bindings.json','serial_release.json','serial_release_gate.json',
        'resource_profile.json','resource_profile_lifecycle.json','dac_optimizer_initialization.json','dac_model_binding.json'):
        d.c.write(output/name,{'unit_test_placeholder':True})
    for name in ('weights_end.pth','checkpoint_complete.pth'):(output/name).write_bytes(b'UNIT TEST ONLY - NOT A PYTORCH CHECKPOINT')
    manifest={name:{k:v for k,v in d.artifact(output/name).items() if k!='path'} for name in ('weights_end.pth','checkpoint_complete.pth')}
    d.c.write(output/'checkpoint_manifest.json',manifest)
    receipt={'stage':'train','status':'completed','exit_code':0,'plan_sha256':pb.sha256,'output_directory':str(output),
        'child_pid':222,'child_started_utc':status['started_utc'],'status_sha256':d.sha(output/'status.json'),
        'result_sha256':d.sha(output/'checkpoint_manifest.json')}
    d.c.write(root/'receipt.json',receipt)
    return pb,d.c.Bound.load(root/'receipt.json',d.sha(root/'receipt.json')),output,inputs

def main():
    files=list(d.HERE.glob('*.py'))
    for path in files:check('AST '+path.name,lambda p=path:ast.parse(p.read_text(encoding='utf-8')))
    spec=d.spec_bound(d.HERE/'execution_spec.json',d.sha(d.HERE/'execution_spec.json'))
    check('exact six-stage order from sealed 3 plans',lambda:equal([x['id'] for x in spec.value['jobs']],d.ORDER))
    check('sealed control payload unchanged',lambda:d.pin_package(d.CONTROL,d.CONTROL_SHA))
    check('sealed inputs payload unchanged',lambda:d.pin_package(d.INPUTS,d.INPUT_SHA))
    check('profile has no inherited resource state',lambda:equal(run.late_profile_binding({'stage':'profile'},None),None))
    check('train cannot precede profile',lambda:run.late_profile_binding({'stage':'train','seed':1},None),True)
    previous={'id':'seed_1_profile','status':'completed','artifact_verification':{'profile':{'sha256':'a'*64},'lifecycle':{'sha256':'b'*64}}}
    check('only actual prior profile hashes are bound',lambda:equal(run.late_profile_binding({'stage':'train','seed':1},previous),{'profile_sha256':'a'*64,'receipt_sha256':'b'*64}))
    check('wrong seed profile rejected',lambda:run.late_profile_binding({'stage':'train','seed':2},previous),True)
    check('failed resource profile rejected',lambda:run.late_profile_binding({'stage':'train','seed':1},{**previous,'status':'failed'}),True)
    with patch.object(d.g,'exited',side_effect=lambda x:x) as exited:
        job={'finished_utc':'2026-01-01T02:00:00+00:00','launcher_pid':1,'launcher_started_utc':'2026-01-01T01:00:00+00:00','launcher_exit_code':0,
            'supervisor_pid':2,'supervisor_started_utc':'2026-01-01T01:00:01+00:00','supervisor_exit_code':0,'controller_pid':3}
        owners=d.stage_owners_exited(job)
        check('stage exit gate excludes still-running coordinator',lambda:equal(set(x['pid'] for x in d.g.owners(owners)),{1,2}))
    with tempfile.TemporaryDirectory(prefix='dac6_stdlib_fixtures_') as tmp:
        root=Path(tmp)
        pb,rb,output,inputs=train_fixture(root)
        with patch.object(d,'INPUTS',inputs),patch.object(d.g,'exited',return_value=[]):
            baseline=d.verify_training_artifacts(pb,rb)
            check('full artifact verifier accepts internally consistent fixture',lambda:equal(baseline['actual_adamw_steps'],1))
            check('both final checkpoint files are bound',lambda:equal(set(baseline['files']) >= {'weights_end.pth','checkpoint_complete.pth'},True))
            def mutation(name,value):
                path=output/name;old=path.read_bytes()
                try:
                    if isinstance(value,bytes):path.write_bytes(value)
                    else:d.c.write(path,value)
                    d.verify_training_artifacts(pb,rb)
                finally:path.write_bytes(old)
            check('modified final weight bytes rejected',lambda:mutation('weights_end.pth',b'changed'),True)
            check('missing full recovery checkpoint rejected',lambda:mutation('checkpoint_manifest.json',{}),True)
            evidence=d.c.read(output/'training_evidence.json')
            for name,values in [('zero real AdamW',{'actual_adamw_steps':0}),('AMP mismatch',{'amp_skips':1}),
                ('unchanged parameter',{'final_parameter_sha256':'a'*64}),('missing scaler',{'final_scaler_state':{}}),
                ('fixture tagged as actual',{'fixture_only':True}),('nonfinite loss',{'epoch_loss':float('nan')})]:
                check(name+' rejected',lambda v=values:mutation('training_evidence.json',{**evidence,**v}),True)
            protocol=d.c.read(output/'dac_training_protocol_evidence.json')
            for name,values in [('CAMP 395 schema',{'model_state_count':395}),('wrong scheduler attempts',{'scheduler_attempts':2}),
                ('test selection',{'test_set_read_or_model_selection':True}),('changed original pre-shuffle steps',{'scheduler_steps_planned_before_shuffle':1577})]:
                check(name+' rejected',lambda v=values:mutation('dac_training_protocol_evidence.json',{**protocol,**v}),True)
            check('missing actual batch trace rejected',lambda:mutation('batch_progress.jsonl',b''),True)
            check('wrong effective seed rejected',lambda:mutation('effective_configuration.json',{'seed':2}),True)
            sampling=d.c.read(output/'epoch01_sampling.json')
            check('truncated loader rejected',lambda:mutation('epoch01_sampling.json',{**sampling,'expected_batches':2}),True)
        # Immutable input snapshot detects a changed external path after admission.
        p=root/'bound.json';d.c.write(p,{'version':1});bound=d.c.Bound.load(p,d.sha(p));d.c.write(p,{'version':2})
        check('captured old input cannot acquire new file SHA',bound.unchanged,True)
        bad=copy.deepcopy(spec.value);bad['jobs'][0],bad['jobs'][1]=bad['jobs'][1],bad['jobs'][0]
        d.c.write(root/'bad_spec.json',bad)
        check('train-before-profile specification rejected',lambda:d.spec_bound(root/'bad_spec.json',d.sha(root/'bad_spec.json')),True)
    # Exercise the actual outer-observer branch with fake Win32 handles. A child
    # may write a completion intent and then fail: no final manifest may exist.
    for actual_code,launcher_code in ((7,0),(0,7),(259,0)):
        with tempfile.TemporaryDirectory(prefix='dac6_exit_fixture_') as tmp:
            root=Path(tmp);stamp='2026-01-01T01:00:00+00:00'
            fake_spec=SimpleNamespace(path=root/'spec.json',sha256='a'*64,
                value={'status_path':str(root/'runtime/status.json'),'completion_path':str(root/'runtime/completion_manifest.json')},unchanged=lambda:None)
            fake_release=SimpleNamespace(path=root/'release.json',sha256='b'*64,unchanged=lambda:None)
            class Process:
                def __init__(self,*args,**kwargs):
                    self.pid=101;self._handle=1;self.returncode=None
                    request=d.c.read(root/'runtime/coordinator_request.json')
                    identity={'schema':'dac-actual-worker-identity.v2','pid':202,'started_utc':stamp,
                        'plan_sha256':'a'*64,'release_sha256':'b'*64,'lineage':[
                            {'pid':202,'started_utc':stamp,'parent_process_id':101},
                            {'pid':101,'started_utc':stamp,'parent_process_id':request['parent_pid']},
                            {'pid':request['parent_pid'],'started_utc':stamp,'parent_process_id':0}]}
                    d.c.write(root/'runtime/coordinator_identity.json',identity)
                    d.c.write(root/'runtime/candidate_completion.json',{'intent_only':True})
                def poll(self):return self.returncode
                def wait(self):self.returncode=launcher_code;return launcher_code
            class Handle:
                def __init__(self,pid,existing_handle=None):self.pid=pid;self.started_utc=stamp
                def exit_code(self):return actual_code
                def close(self):pass
            with ExitStack() as stack:
                for obj,name,value in ((d,'HERE',root),(d,'spec_bound',lambda *x:fake_spec),(d,'release_bound',lambda *x:fake_release),
                    (d.g,'process_started',lambda pid:stamp),(d.g,'ProcessObservation',Handle),(run.subprocess,'Popen',Process)):
                    stack.enter_context(patch.object(obj,name,value))
                check(f'actual coordinator {actual_code}/launcher {launcher_code} rejects completion',lambda:run.supervise_coordinator('spec','a'*64,'release','b'*64),True)
                check(f'coordinator {actual_code}/launcher {launcher_code} leaves intent but no final manifest',
                    lambda:equal(((root/'runtime/candidate_completion.json').exists(),(root/'runtime/completion_manifest.json').exists()),(True,False)))
                check(f'coordinator {actual_code}/launcher {launcher_code} failure receipt retained',
                    lambda:equal(d.c.read(root/'runtime/controller_lifecycle.json')['status'],'failed'))
    # Focused regression: zip truncation and an unverified candidate artifact
    # list must not become a sealed completion even with actual exit0 receipts.
    identity={'pid':202,'started_utc':'2026-01-01T01:00:00+00:00'}
    release=SimpleNamespace(path=d.HERE/'not_created_release.json',sha256='b'*64,unchanged=lambda:None)
    final_state={'schema':'dac-six-stage-execution-status.v2','status':'completed','exit_code':0,
        'execution_spec_path':str(spec.path),'execution_spec_sha256':spec.sha256,'execution_manifest_sha256':'c'*64,
        'root_release_path':str(release.path),'root_release_sha256':release.sha256,
        'controller_pid':identity['pid'],'controller_started_utc':identity['started_utc'],
        'jobs':[{**row,'control_receipt_sha256':'d'*64} for row in spec.value['jobs']]}
    def fixture_artifact(row,record):return {'fixture_stage_result':row['id']}
    artifacts=[{'seed':row['seed'],'plan_path':row['plan_path'],'plan_sha256':row['plan_sha256'],
        'output_directory':row['output_directory'],'control_receipt_path':row['control_receipt_path'],
        'control_receipt_sha256':'d'*64,'artifacts':fixture_artifact(row,row)}
        for row in spec.value['jobs'] if row['stage']=='train']
    candidate={'schema':'dac-six-stage-completion.v2','execution_spec_sha256':spec.sha256,
        'execution_manifest_sha256':'c'*64,'status_sha256':'e'*64,'training_artifacts':artifacts}
    def validate_candidate_fixture(state_changes=None,candidate_changes=None):
        state=copy.deepcopy(final_state);state.update(state_changes or {})
        intent=copy.deepcopy(candidate);intent.update(candidate_changes or {})
        return run.validated_completion_candidate(spec,release,identity,
            SimpleNamespace(value=state,sha256='e'*64,unchanged=lambda:None),
            SimpleNamespace(value=intent,unchanged=lambda:None))
    with patch.object(d,'own_manifest',return_value='c'*64),patch.object(d,'verify_stage',side_effect=fixture_artifact) as verified_stage:
        check('six verified stages rebuild exactly three seed artifacts',lambda:equal(validate_candidate_fixture(),candidate))
        check('all six verification return values are consumed',lambda:equal(verified_stage.call_count,6))
        for name,changes in [('truncated five stages',{'jobs':final_state['jobs'][:5]}),
            ('extra seventh stage',{'jobs':final_state['jobs']+[final_state['jobs'][0]]}),
            ('wrong stage order',{'jobs':list(reversed(final_state['jobs']))}),
            ('wrong final status schema',{'schema':'incorrect'}),('wrong final spec SHA',{'execution_spec_sha256':'f'*64}),
            ('wrong final source manifest',{'execution_manifest_sha256':'f'*64}),
            ('wrong final root release',{'root_release_sha256':'f'*64})]:
            check(name+' cannot seal',lambda v=changes:validate_candidate_fixture(state_changes=v),True)
        for name,changes in [('empty candidate artifacts',{'training_artifacts':[]}),
            ('candidate unrelated artifact values',{'training_artifacts':[{'seed':1},{'seed':2},{'seed':3}]}),
            ('candidate wrong schema',{'schema':'incorrect'}),('candidate wrong spec SHA',{'execution_spec_sha256':'f'*64}),
            ('candidate wrong source SHA',{'execution_manifest_sha256':'f'*64}),
            ('candidate stale status SHA',{'status_sha256':'f'*64}),('candidate unexpected extra field',{'unverified':True})]:
            check(name+' cannot seal',lambda v=changes:validate_candidate_fixture(candidate_changes=v),True)
    # No Win32 process/GPU function is called by these fixtures.
    check('no scientific modules imported',lambda:equal([x for x in sys.modules if x.split('.')[0] in {'torch','numpy','PIL','scipy','timm','cv2','albumentations','transformers'}],[]))
    check('no active runtime created',lambda:equal((d.HERE/'runtime').exists(),False))
    report={'schema':'dac-six-stage-stdlib-validation.v2','fixture_only':True,'tests_passed':len(results),'tests':results,
        'scientific_imports':False,'gpu_execution':False,'actual_experiment_results':False,
        'source_files_sha256':{p.name:d.sha(p) for p in files},'spec_sha256':spec.sha256}
    d.c.write(d.HERE/'EXECUTION_VALIDATION.json',report)
    print(json.dumps({'passed':len(results),'report_sha256':d.sha(d.HERE/'EXECUTION_VALIDATION.json')}))

if __name__=='__main__':main()
