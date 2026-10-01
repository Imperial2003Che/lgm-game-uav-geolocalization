"""Independent small-file observation review. No CIM, launch, scientific imports or control actions."""
from pathlib import Path
import json, hashlib, datetime, re

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = Path(__file__).parent
bindings = {}
checks = []

def bind(path, expected=None):
    path = Path(path)
    assert path.stat().st_size < 500000, str(path)
    data = path.read_bytes()
    record = {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if expected is not None:
        assert all(record[k] == expected[k] for k in ('bytes','sha256')), str(path)
    bindings[str(path)] = record
    return record

def read(path, sha=None):
    b=bind(path)
    if sha: assert b['sha256']==sha, str(path)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def check(condition, label):
    assert condition, label
    checks.append(label)

def ticks(iso):
    m=re.fullmatch(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,7}))?(Z|[+]00:00)',iso)
    assert m,iso
    dt=datetime.datetime.fromisoformat(m[1])
    delta=dt-datetime.datetime(1,1,1)
    return ((delta.days*86400+delta.seconds)*10000000 + int((m[2] or '').ljust(7,'0')))

def write(name, obj):
    data=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    with (HERE/name).open('xb') as f: f.write(data)
    return bind(HERE/name)

obs=read(EX/'heartbeat_observation_20260930_040510057/OBSERVATION_WRAPPER_INCLUDED.json','46543c4e92245872f50aa1016ff09afb20d4197a05b872abe3c454837956615b')
stopped=read(EX/'efficiency_incident_20260929_1448/observation_20260930_040511476/OBSERVATION.json','42422ac8b18e948b857478668c53c885847eb59be91f8dea08fce47ea25ec586')
prior=read(EX/'heartbeat_observation_20260930_030407230/OBSERVATION_WRAPPER_INCLUDED.json','f7bb33d67d5b27e3f24bd9d9e0e239f85aedf8cfff558d7368187dc3afe04baa')
contract=read(EX/'t6_recovery_preparation_20260930_0104/RECOVERY_CONTRACT.json','d0aa27edfc5391689a947dc7a572d38a9a150186672c7d10965715f12e36d136')
old_root=read(EX/'t6_recovery_preparation_20260930_0104/ROOT_SOURCE_ADOPTION.json','fff6965e4d794902105f578cadb4680f363c7d6d31dcfd0a29bd3e636ea09343')
for src in (obs['source'],stopped['source']): bind(src['path'],src)
check(old_root['execution_released'] is False,'Prior source adoption did not release execution')
check(contract['host_boot_utc_ticks']=='639263179115000000','01:04 contract is bound to preceding boot')
check(prior['first']['boot_utc_ticks']==prior['second']['boot_utc_ticks']==contract['host_boot_utc_ticks'],'Prior two observations agree with preceding contract boot')
check(obs['first']['boot_utc_ticks']==obs['second']['boot_utc_ticks']=='639263337875000000','Both new broad observations agree on new boot integer ticks')
check(ticks(stopped['host_boot_utc'])==639263337875000000,'Narrow observer independently saved matching boot timestamp')
check(obs['first']['boot_utc_ticks']!=contract['host_boot_utc_ticks'],'Existing 01:04 boot-bound contract no longer matches current recorded boot')
check(len(obs['files'])==16,'Exactly five states plus eleven closed logs bound')
check(obs['files']==prior['files'],'All sixteen state/log binding values unchanged from preceding saved observation')
for record in obs['files']: bind(record['path'],record)
check(len(stopped['states'])==5,'Five states saved in stopped observation')
for state in stopped['states']:
    bind(state['source']['path'],state['source'])
    bind(state['snapshot']['path'],state['snapshot'])
    saved=read(state['snapshot']['path'])
    check(state['source']['sha256']==state['snapshot']['sha256'] and state['unchanged_since_incident'] is True,'State and snapshot unchanged: '+Path(state['source']['path']).name)
    check(saved['status']==state['status'] and saved['heartbeat_utc']==state['heartbeat_utc'],'Saved status/heartbeat copied exactly: '+Path(state['source']['path']).name)
for label in ('first','second'):
    snap=obs[label]
    check(ticks(snap['boot_utc'])==int(snap['boot_utc_ticks']),label+' boot ISO and integer ticks agree')
    check(len(snap['matches'])==1,label+' broad scan has exactly one matched process')
    v=snap['matches'][0]
    check(v['pid']==29480 and v['parent_pid']==13076 and v['name']=='VISIO.EXE',label+' observed Visio and parent numbers')
    check(v['command_line']=='"C:\\Program Files\\Microsoft Office\\root\\Office16\\VISIO.EXE" ',label+' full Visio command is ordinary executable command without automation switches')
    check(v['creation_utc_ticks']=='639263338233256210' and ticks(v['creation_utc'])==int(v['creation_utc_ticks']),label+' Visio creation ISO and ticks agree')
    parent=v['parent_current_observation']
    check(len(parent)==1 and parent[0]['pid']==13076 and parent[0]['name']=='explorer.exe' and parent[0]['command_line']=='C:\\Windows\\Explorer.EXE' and parent[0]['creation_utc_ticks']=='639263338065379830',label+' current parent-number observation identifies explorer')
    check(14420 not in [x['pid'] for x in snap['matches']] and 14932 not in [x['pid'] for x in snap['matches']],label+' prior matched AppActions/unknown Visio identities absent from current filtered records')
check(obs['first']['matches']==obs['second']['matches'],'Process identity/command/parent records unchanged across both broad scans')
check(not stopped['first_CIM']['records'] and not stopped['second_CIM']['records'],'Narrow science/old-PID filter returned no records twice')
gpu=stopped['gpu_query']; bind(gpu['path'],gpu)
rows=[line for line in Path(gpu['path']).read_text(encoding='utf-8-sig').splitlines() if re.match(r'^\s*\d+\s*,',line)]
check(len(rows)==stopped['gpu_process_rows']==23,'Actual bound GPU query text contains twenty-three numeric rows')
check(stopped['gpu_query_exit_code']==0 and stopped['original_gpu_exclusive_gate_would_be_satisfied'] is False,'Successful GPU query remains nonempty; exclusive gate false')
bind(obs['carrier']['path'],obs['carrier'])
check(Path(obs['carrier']['path']).read_bytes()==b'0' and obs['carrier']['byte_values']==[48] and obs['carrier']['creation_utc_ticks']=='639262940518466959','One-byte carrier content verified; recorded creation identity unchanged')
check(stopped['t6_output_exists'] is False and obs['t6_output_absent'] is True and not Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal').exists(),'T6 output absent in saved observations and current path check')
for name in ('t6_recovery_preparation_20260929_1548','t6_recovery_preparation_20260930_0104'):
    check(not (EX/name/'runtime_attempt').exists(),name+' attempt absent at independent check')
check(not (EX.parent/'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1').exists(),'Visio candidate attempt absent at independent check')
bind(__file__)
report={'schema':'independent-new-boot-observation-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Independent AI agent full text review of both observer sources and saved observations; stdlib small-file binding/value/timestamp checks. No independent CIM repetition or science/COM execution.','accepted_observation_scope':True,'new_boot_utc_ticks':'639263337875000000','previous_contract_boot_utc_ticks':'639263179115000000','existing_boot_contract_valid_for_new_boot':False,'execution_released':False,'cleanup_authorized':False,'new_scientific_failure_inferred':False,'independent_exit_code_inferred':False,'checks':checks,'bindings':list(bindings.values()),'limitations':['The broad observer matches listed historical PID numbers, all Visio processes and specified science/controller command patterns; it is not an exhaustive guarantee against arbitrary unlisted code.','Parent fields are current parent-number observations; no historical parent ownership or held process handle is proven.','Current Visio 29480 is not established as task-owned. No attach, Quit, Kill, or process-control authorization is provided.','Absence of former AppActions 14420 and unknown Visio 14932 supplies no captured exit code or retroactive ownership.','Scientific states/logs already represented a stopped queue before this boot change; a new scientific interruption is not inferred.','The persistent byte carrier is not proof of a held OS lock or GPU exclusivity.','The saved nonempty GPU query forbids execution release or launching to wait. Future admission needs a separate new-boot source contract and fresh full gates.','No weights, model/cache/image arrays, old scientific or synthetic control suites, recovery runner, native probe, release, intent, COM, lock acquisition, or live state writes were performed.']}
out=write('OBSERVATION_REVIEW.json',report)
print(json.dumps({'report':out,'checks':len(checks),'bindings':len(bindings)},ensure_ascii=False))
