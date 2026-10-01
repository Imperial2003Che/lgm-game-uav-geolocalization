"""New isolated synthetic controls only. Never call real runtime dependencies."""
from pathlib import Path
import copy
import importlib.util
import json
import os
import sys
import types
from unittest.mock import patch

HERE=Path(__file__).absolute().parent
spec=importlib.util.spec_from_file_location('candidate_under_synthetic_test',HERE/'pipeline_recovery_candidate.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
CHECKS=[]

def ok(name,condition):
    if not condition:raise AssertionError(name)
    CHECKS.append(name)

def reject(name,action):
    try:action()
    except (RuntimeError,FileExistsError,ValueError,KeyError):CHECKS.append(name);return
    raise AssertionError('Unexpected acceptance: '+name)

def put(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(c.encoded(payload))

def main():
    folder=HERE/'synthetic_control_a1'
    folder.mkdir(exist_ok=False)
    original=c.read(HERE/'captured_pipeline_status.json')
    contract=c.read(HERE/'RECOVERY_CONTRACT.json')
    recovery=c.read(contract['recovery_spec']['path'])
    seed=c.read(HERE/'pipeline_seed.json')
    c.validate_seed(seed,original,recovery,contract['incident_capture'])
    ok('Only job7 pending; first6 records exact',seed['jobs'][:6]==original['jobs'][:6] and
       [j['status'] for j in seed['jobs']]==['completed']*6+['pending'])
    for index in range(6):
        candidate=copy.deepcopy(seed);candidate['jobs'][index]['finished_utc']='changed'
        reject('Reject predecessor whole record change '+str(index+1),lambda candidate=candidate:
               c.validate_seed(candidate,original,recovery,contract['incident_capture']))
        candidate=copy.deepcopy(seed);candidate['jobs'][index]['command'].append('--changed')
        reject('Reject predecessor command change '+str(index+1),lambda candidate=candidate:
               c.validate_seed(candidate,original,recovery,contract['incident_capture']))
    candidate=copy.deepcopy(seed);candidate['jobs'][6]['command'].append('--changed')
    reject('Reject changed original T6 command',lambda:c.validate_seed(candidate,original,recovery,contract['incident_capture']))
    for name,gpu in [('foreign desktop',{'exit_code':0,'stdout':'421, desktop.exe'}),
                     ('unknown permissions',{'exit_code':0,'stdout':'421, [Insufficient Permissions]'}),
                     ('query failed',{'exit_code':1,'stdout':''}),('ambiguous row',{'exit_code':0,'stdout':'unparseable'})]:
        reject('GPU '+name,lambda gpu=gpu:c.gpu_gate(gpu))
    ok('Empty successful GPU result accepted',c.gpu_gate({'exit_code':0,'stdout':'\n'})['exit_code']==0)
    sample={'commit_limit_bytes':c.MIN_COMMIT,'committed_bytes':0,'available_commit_bytes':c.MIN_COMMIT}
    ok('Exact 26 GiB boundary accepted',c.memory_gate(sample)==sample)
    for key,value in [('committed_bytes',None),('commit_limit_bytes',0),('available_commit_bytes',c.MIN_COMMIT-1),
                      ('commit_limit_bytes',True),('committed_bytes',c.MIN_COMMIT+1)]:
        bad=dict(sample);bad[key]=value
        reject('Reject invalid memory '+key+' '+repr(value),lambda bad=bad:c.memory_gate(bad))
    for name in ('gpu_foreign','gpu_query_failure','source_changed','state_CAS_changed'):
        area=folder/name;area.mkdir();live=area/'pipeline_status.json';live.write_bytes(c.encoded(original));pin=c.binding(live)
        intent=area/'attempt'
        def denied():raise RuntimeError(name)
        reject('Publish '+name+' before mutations',lambda:c.publish_once(intent,live,pin,c.encoded(seed),{},denied))
        ok('Zero intent/live mutations '+name,not intent.exists() and c.binding(live)==pin)
    area=folder/'cas_after_gate';area.mkdir();live=area/'pipeline_status.json';live.write_bytes(c.encoded(original));pin=c.binding(live)
    def race():live.write_bytes(b'changed by synthetic competitor');return {'marker':'race'}
    reject('Final state byte race rejects before intent',lambda:c.publish_once(area/'attempt',live,pin,c.encoded(seed),{},race))
    ok('Race does not create intent',not (area/'attempt').exists())
    area=folder/'successful_publish';area.mkdir();live=area/'pipeline_status.json';live.write_bytes(c.encoded(original));pin=c.binding(live)
    c.publish_once(area/'attempt',live,pin,c.encoded(seed),{},lambda:{'marker':'final fresh sample'})
    ok('Final gate sample sealed in intent',c.read(area/'attempt/launch_intent.json')['final_admission']['marker']=='final fresh sample')
    ok('Retired original exact and seed exact',c.binding(area/'attempt/retired_pipeline_status.json')['sha256']==pin['sha256'] and live.read_bytes()==c.encoded(seed))
    reject('Existing intent permanently refuses replay',lambda:c.assert_unused(area/'attempt'))
    partial=folder/'partial_attempt';partial.mkdir()
    reject('Empty partial attempt also permanently refuses replay',lambda:c.assert_unused(partial))
    old=b'Old T6 GPU exclusivity error\r\n';log=folder/'append.log';log.write_bytes(old);pin=c.binding(log)
    with log.open('ab') as stream:stream.write(b'New actual attempt line\r\n')
    row=c.prefix_gate(log,pin)
    ok('Append old prefix retained and exact new offset',row['new_start_offset']==len(old) and row['new_sha256']==c.digest(b'New actual attempt line\r\n'))
    log.write_bytes(b'X'+log.read_bytes()[1:])
    reject('Append prefix corruption rejected',lambda:c.prefix_gate(log,pin))
    launch_folder=folder/'launch_reentry';launch_folder.mkdir()
    payload={'popen_launcher_pid':7,'launcher_api_creation_utc_ticks':'123','command':['a','b']}
    c.launch_record_once(launch_folder,payload);pin=c.binding(launch_folder/'launch.json')
    c.launch_record_once(launch_folder,payload)
    ok('Monitor reentry accepts same immutable launch',c.binding(launch_folder/'launch.json')==pin)
    reject('Wrong reused launch identity rejected',lambda:c.validate_launch_record(launch_folder,7,'124',['a','b']))
    reject('Exact role mismatch rejected',lambda:c.controller_tokens_match(['python','-B','x','--role','primary'],
        ['python','-B','x','--role','pipeline'],{os.path.normcase(os.path.abspath('python'))}))
    reject('Reused primary PID conservatively blocked',lambda:c.processes_gate({'processes':[{'pid':33924,'name':'desktop.exe','command':'desktop'}]},33924,set()))
    # The following calls runtime ONLY with every external observation/native /
    # process/lock dependency replaced. All files are under synthetic_control_a1.
    # It is not an actual admission/ValidateOnly/native probe or controller launch.
    for mode in ('success','spawn_failure','native_failure','boot_changed','candidate_changed','anchor_first_failure'):
        base=folder/('runtime_'+mode);base.mkdir();ex=base/'live';ex.mkdir();root=base/'root';root.mkdir()
        state=ex/'pipeline_status.json';put(state,original)
        put(ex/'status.json',{'status':'completed','controller_pid':33924})
        for name in c.STATE_NAMES[2:]:put(ex/name,{'status':'synthetic_original_interrupted'})
        put(base/'captured_pipeline_status.json',original);put(base/'pipeline_seed.json',seed)
        put(base/'spec.json',recovery)
        fixturecontract={'recovery_spec':c.binding(base/'spec.json'),'input_bindings':[],
           'incident_capture':contract['incident_capture'],'live_state_bindings':[c.binding(ex/name) for name in c.STATE_NAMES],
           'append_log_prefixes':[],'primary_controller_pid':33924,'host_boot_utc_ticks':'1000'}
        put(base/'RECOVERY_CONTRACT.json',fixturecontract)
        put(base/'candidate_fixture.json',{'fixed':'source'})
        manifest={'candidate_files':[c.binding(base/'candidate_fixture.json'),c.binding(base/'RECOVERY_CONTRACT.json'),c.binding(base/'pipeline_seed.json')]}
        put(base/'SOURCE_MANIFEST.json',manifest)
        put(base/'adoption.json',{'schema':'t6-pipeline-recovery-source-adoption.v1','source_manifest':c.binding(base/'SOURCE_MANIFEST.json'),'approved_for_future_gated_execution':True})
        now=c.dt.datetime.now(c.dt.timezone.utc)
        put(base/'release.json',{'schema':'t6-pipeline-recovery-release.v1','scope':'pipeline_only_original_stage7','execute':True,
          'source_manifest':c.binding(base/'SOURCE_MANIFEST.json'),'root_adoption':c.binding(base/'adoption.json'),
          'issued_utc':now.isoformat(),'expires_utc':(now+c.dt.timedelta(minutes=10)).isoformat()})
        args=types.SimpleNamespace(release=base/'release.json',release_sha256=c.binding(base/'release.json')['sha256'],
              root_adoption=base/'adoption.json',root_adoption_sha256=c.binding(base/'adoption.json')['sha256'])
        calls=[];held=[];anchor_calls=[]
        class FakeLock:
            def __init__(self,path):self.path=path;self.closed=False;held.append(self)
            def close(self):self.closed=True
        def snapshot():
            return {'host_boot_utc_ticks':'1001' if mode=='boot_changed' else '1000',
              'processes':[{'pid':os.getpid(),'parent_pid':0,'name':'python.exe','command':str(Path(c.__file__).absolute())}]}
        def native():
            calls.append('native_simulated')
            if mode=='native_failure':raise RuntimeError('synthetic native rejection')
            if mode=='candidate_changed':put(base/'candidate_fixture.json',{'changed':True})
            os.environ['T6_SYNTHETIC_ENV_APPLIED']='yes'
            return {'isolation':{'launcher_pid':9001,'interpreter_pid':9002}}
        def popen(*arguments,**kwargs):
            calls.append('popen_simulated')
            ok('Native simulated env reaches actual launch-parent call '+mode,os.environ.get('T6_SYNTHETIC_ENV_APPLIED')=='yes')
            ok('Shared lock still held at simulated spawn '+mode,not held[0].closed)
            if mode=='spawn_failure':raise RuntimeError('synthetic Popen failure')
            final=copy.deepcopy(original);final['supervisor_pid']=777;final['status']='ready_for_extension_preparation'
            final['jobs'][6].update(status='completed',exit_code=0,pid=888)
            put(state,final)
            return types.SimpleNamespace(pid=777,returncode=0,poll=lambda:0)
        def anchor(child):
            anchor_calls.append(1)
            if mode=='anchor_first_failure' and len(anchor_calls)==1:raise RuntimeError('synthetic anchor capture failure')
            return {'identity':{'pid':777},'api_creation_utc_ticks':'1230','handle':123,'controller_tokens_checked':True}
        def monitor(child,tracked,destination,command,anch,allowed):
            calls.append('monitor_simulated')
            ok('Shared lock held during monitor '+mode,not held[0].closed)
            payload={'popen_launcher_pid':777,'launcher_api_creation_utc_ticks':'1230','command':command}
            c.launch_record_once(destination,payload)
            return {'actual_owner_observed':True,'final_runtime_status':'ready_for_extension_preparation'}
        patches={'HERE':base,'EX':ex,'ROOT':root,'PYTHON':Path(sys.executable),'ByteLock':FakeLock,
          'process_snapshot':snapshot,'fresh_gpu':lambda:{'exit_code':0,'stdout':''},'fresh_memory':lambda:dict(sample),
          'load_native_module':lambda _:types.SimpleNamespace(verify_training_environment_isolated=native,scientific_modules=lambda:[]),
          'subprocess':types.SimpleNamespace(Popen=popen,DEVNULL=-3,CREATE_NO_WINDOW=0),
          'launcher_anchor':anchor,'observe_until_exit':monitor,
          'ctypes':types.SimpleNamespace(windll=types.SimpleNamespace(kernel32=types.SimpleNamespace(CloseHandle=lambda _:True)),c_void_p=lambda value:value)}
        with patch.multiple(c,**patches),patch.object(c.time,'sleep',lambda _:None):
            if mode=='success':c.runtime(args)
            else:reject('Synthetic runtime '+mode,lambda:c.runtime(args))
        ok('All simulated outer locks safely released '+mode,all(lock.closed for lock in held))
        if mode in ('native_failure','boot_changed','candidate_changed'):
            ok('Pre-admission failure no live-state/intent changes '+mode,not(base/'runtime_attempt').exists() and state.read_bytes()==c.encoded(original) and 'popen_simulated' not in calls)
        else:
            ok('Attempt preserved '+mode,(base/'runtime_attempt/launch_intent.json').is_file() and (base/'runtime_attempt/retired_pipeline_status.json').read_bytes()==c.encoded(original))
            if mode!='success':ok('Partial failure preserved without rollback '+mode,(base/'runtime_attempt/failure_after_intent.json').is_file())
        os.environ.pop('T6_SYNTHETIC_ENV_APPLIED',None)
    # Exercise the real monitor loop with fake CIM/handle functions, including a
    # failed launch diagnostic followed by same-attempt reentry. Never call CUA/CIM.
    monitorbase=folder/'monitor_loop';monitorbase.mkdir();put(monitorbase/'pipeline_status.json',{'supervisor_pid':777,'status':'ready_for_extension_preparation'})
    own={'pid':os.getpid(),'parent_pid':0,'name':'python.exe','command':str(Path(c.__file__).absolute())}
    anchor={'identity':{'pid':777},'api_creation_utc_ticks':'1230','handle':123,'controller_tokens_checked':True}
    tracked={(777,123):anchor};child=types.SimpleNamespace(pid=777,returncode=0,poll=lambda:0)
    calls=[]
    actual_once=c.launch_record_once
    def first_diagnostic_failure(*args):
        calls.append(1)
        if len(calls)==1:raise OSError('synthetic diagnostic failure')
        return actual_once(*args)
    with patch.multiple(c,EX=monitorbase,process_snapshot=lambda:{'processes':[own]},
         collect_descendants=lambda *args:None,handle_status=lambda _: {'signaled':True,'exit_code_observed':0},
         launch_record_once=first_diagnostic_failure),patch.object(c.time,'sleep',lambda _:None):
        result=c.observe_until_exit(child,tracked,monitorbase,['same'],anchor,set())
        ok('Monitor exits safely after first diagnostic write fails',result['two_absence_scans'] and len(result['monitor_errors'])==1)
        result2=c.observe_until_exit(child,tracked,monitorbase,['same'],anchor,set())
        ok('Monitor reentry does not repeat immutable write forever',result2['two_absence_scans'])
    for path in HERE.glob('*.py'):compile(path.read_text(encoding='utf-8'),str(path),'exec')
    ok('All candidate/preparation/check source compiles without importing science',not c.SCIENTIFIC.intersection(name.split('.')[0] for name in sys.modules))
    report={'schema':'t6-recovery-new-synthetic-controls.v1','completed_utc':c.utc(),'status':'passed','checks':len(CHECKS),
      'check_names':CHECKS,'candidate_source':c.binding(HERE/'pipeline_recovery_candidate.py'),
      'control_source':c.binding(Path(__file__)),
      'limits':['Only new isolated synthetic fixtures; no old scientific/control suites were rerun.',
       'Runtime branch calls used fake source/state/GPU/memory/CIM/lock/native/Popen/handle dependencies entirely under synthetic_control_a1.',
       'No real native import, GPU query, Windows controller, release, live state, intent or retired artifact was created.',
       'Synthetic monitor observations are not actual process exits or resource admission.']}
    c.immutable(folder/'REPORT.json',report)
    print(json.dumps({'checks':len(CHECKS),'report':c.binding(folder/'REPORT.json')},ensure_ascii=False))

if __name__=='__main__':main()
