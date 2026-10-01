"""Seal this turn's small read-only snapshot; never issue execution authority."""
from pathlib import Path
import hashlib,json
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
EX=HERE.parent
def bind(p):
    p=Path(p); b=p.read_bytes()
    return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p): return json.loads(Path(p).read_bytes())
def verify(d):
    assert bind(d['path'])==d,d['path']
    return d
obs=read(HERE/'OBSERVATION_WRAPPER_INCLUDED.json')
stopped_path=EX/'efficiency_incident_20260929_1448/observation_20260930_050929887/OBSERVATION.json'
stopped=read(stopped_path)
prior_path=EX/'heartbeat_observation_20260930_040510057/OBSERVATION_WRAPPER_INCLUDED.json'
prior=read(prior_path)
contract_path=EX/'t6_recovery_preparation_20260930_0405/RECOVERY_CONTRACT.json'
contract=read(contract_path)
assert len(obs['files'])==16
for d in obs['files']: verify(d)
assert obs['files']==prior['files']
for which in ['first','second']:
    assert obs[which]['boot_utc_ticks']==contract['host_boot_utc_ticks']=='639263337875000000'
    assert obs[which]['matches']==prior[which]['matches']
assert len(obs['first']['matches'])==1 and obs['first']['matches'][0]['name']=='VISIO.EXE'
assert len(stopped['states'])==5 and all(x['unchanged_since_incident'] is True for x in stopped['states'])
assert stopped['first_CIM']['records']==stopped['second_CIM']['records']==[]
assert stopped['gpu_query_exit_code']==0 and stopped['gpu_process_rows']==23
assert stopped['original_gpu_exclusive_gate_would_be_satisfied'] is False
verify(stopped['gpu_query'])
assert stopped['t6_output_exists'] is False and obs['t6_output_absent'] is True
assert obs['carrier']==prior['carrier'] and Path(obs['carrier']['path']).read_bytes()==b'0'
attempts=[EX/f't6_recovery_preparation_{stamp}/runtime_attempt' for stamp in ['20260929_1548','20260930_0104','20260930_0405']]
attempts.append(EX.parent/'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1')
assert all(not p.exists() for p in attempts)
for p,sha in [(contract_path,'7e10d045a396c53a9ffb7ec0996e38f2a88101413cbf5655548a6f80edcb44ff'),(contract_path.parent/'ROOT_SOURCE_ADOPTION.json','bd39f17134c264f6637d578cb5521a780db011e8bc820e9d9e3436c182476f3e')]:
    assert bind(p)['sha256']==sha
report={
 'schema':'root-readonly-heartbeat-observation-seal.v1','utc':datetime.now(timezone.utc).isoformat(),
 'source':bind(__file__),'observation':bind(HERE/'OBSERVATION_WRAPPER_INCLUDED.json'),
 'stopped_observation':bind(stopped_path),'prior_observation':bind(prior_path),
 'current_contract':bind(contract_path),'current_source_adoption':bind(contract_path.parent/'ROOT_SOURCE_ADOPTION.json'),
 'boot_ticks':contract['host_boot_utc_ticks'],'boot_unchanged_since_previous_turn':True,
 'same_complete_current_visio_and_parent_observations':True,'current_visio':obs['first']['matches'][0],
 'science_matches_absent_in_saved_scans':True,'unchanged_state_and_closed_log_files':obs['files'],
 'state_heartbeats':[dict(path=x['source']['path'],status=x['status'],heartbeat_utc=x['heartbeat_utc']) for x in stopped['states']],
 'carrier':obs['carrier'],'attempts_absent_at_seal':[str(p) for p in attempts],
 'gpu_query':stopped['gpu_query'],'gpu_rows':23,'gpu_exit_code':0,'gpu_gate_satisfied':False,
 'execution_released':False,'cleanup_authorized':False,'new_scientific_result':False,
 'limits':[
  'Root AI read the observer source and saved current observations; focused small-file checks only, not an independent second OS capture.',
  'Original broad observer still refers to the historical Sep29 contract. Its false contract_boot_matches_current flag is not a failure of the current Sep30_0405 contract; this seal compares that current contract explicitly.',
  'Same live Visio and current parent-number observation confer no task ownership or cleanup permission.',
  'No exit code is inferred from absence; primary independent exit remains unknown.',
  'This snapshot is not future admission. No release, intent, scientific import, native training probe, COM, cleanup, lock acquisition, state mutation or recovery was performed.',
  'No weights, NPZ, model, cache, image corpus or old large delivery archives were read.'
 ]}
target=HERE/'ROOT_OBSERVATION_SEAL.json'
with target.open('x',encoding='utf-8',newline='\n') as f: json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(bind(target),ensure_ascii=False))
