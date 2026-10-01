from pathlib import Path
import json,hashlib,datetime,re
D=Path(__file__).resolve().parent;EX=D.parent.parent
bindings={};checks=[]
def bind(p):
 p=Path(p);assert p.stat().st_size<1024*1024
 b=p.read_bytes();x={'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};bindings[str(p)]=x;return x
def read(p):bind(p);return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def ck(v,n):
 if not v:raise AssertionError(n)
 checks.append(n)
def same(b):return bind(b['path'])=={k:b[k] for k in ['path','bytes','sha256']}
def ticks(s):
 m=re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,7}))?(Z|[+-]\d\d:\d\d)',s);assert m
 v=datetime.datetime.fromisoformat(m[1]+('+00:00' if m[3]=='Z' else m[3])).astimezone(datetime.timezone.utc)
 z=v.replace(tzinfo=None)-datetime.datetime(1,1,1)
 return (z.days*86400+z.seconds)*10000000+int((m[2] or '').ljust(7,'0'))
curp=D.parent/'OBSERVATION_WRAPPER_INCLUDED.json';oldp=EX/'heartbeat_observation_20260930_050928509'/'OBSERVATION_WRAPPER_INCLUDED.json'
sp=EX/'efficiency_incident_20260929_1448'/'observation_20260930_060845355'/'OBSERVATION.json'
osp=EX/'efficiency_incident_20260929_1448'/'observation_20260930_050929887'/'OBSERVATION.json'
cp=EX/'t6_recovery_preparation_20260930_0405'/'RECOVERY_CONTRACT.json';arp=cp.parent/'ROOT_SOURCE_ADOPTION.json'
cur,old,s,os,contract,adoption=[read(p) for p in [curp,oldp,sp,osp,cp,arp]]
rootp=D.parent/'ROOT_OBSERVATION_SEAL.json';root=read(rootp)
ck(same(cur['source']) and same(s['source']),'Both saved-observer sources match their stored small-file binding; read as text only')
cs=Path(cur['source']['path']).read_text();ss=Path(s['source']['path']).read_text()
ck("t6_recovery_preparation_20260929_1548\\runtime_attempt" in cs,'Broad observer attempt flag scope is only old Sep29 path')
ck(cur['contract']['path'].endswith('t6_recovery_preparation_20260929_1548\\RECOVERY_CONTRACT.json'),'Broad observer contract flag uses historical Sep29 contract')
ck(cur['contract_boot_matches_current'] is False,'Historical boot-mismatch flag retained without relabeling as current-contract failure')
ck(same({'path':str(cp),'bytes':42040,'sha256':'7e10d045a396c53a9ffb7ec0996e38f2a88101413cbf5655548a6f80edcb44ff'}),'Current0405 contract exact known bytes')
ck(same({'path':str(arp),'bytes':16398,'sha256':'bd39f17134c264f6637d578cb5521a780db011e8bc820e9d9e3436c182476f3e'}),'Current0405 source adoption exact known bytes')
ck(adoption['execution_released'] is False,'Current source root has not released execution')
for q in [cur['first'],cur['second'],old['first'],old['second']]:
 ck(q['boot_utc_ticks']==contract['host_boot_utc_ticks']=='639263337875000000','Saved boot sample matches0405 contract integer ticks')
 ck(ticks(q['boot_utc'])==int(q['boot_utc_ticks']),'Saved boot date exact100ns conversion agrees with integer string')
ck(ticks(s['host_boot_utc'])==int(contract['host_boot_utc_ticks'])==ticks(os['host_boot_utc']),'New and prior stopped-observer boot strings agree with0405')
ck(cur['first']['matches']==cur['second']['matches']==old['first']['matches']==old['second']['matches'],'Full saved matched-process/parent records unchanged, not PID-only comparison')
vis=cur['first']['matches'];ck(len(vis)==1,'Broad saved scope contains only one matchedVisio record')
v=vis[0];ck(v['pid']==29480 and v['parent_pid']==13076 and v['name']=='VISIO.EXE','Exact presentVisio PID/name/current parent number')
ck(v['command_line']=='"C:\\Program Files\\Microsoft Office\\root\\Office16\\VISIO.EXE" ','Complete ordinaryVisio command including trailingspace preserved')
ck(ticks(v['creation_utc'])==int(v['creation_utc_ticks'])==639263338233256210,'Visio creation timestamp and integer ticks consistent')
p=v['parent_current_observation'][0]
ck(p=={'pid':13076,'name':'explorer.exe','command_line':'C:\\Windows\\Explorer.EXE','creation_utc_ticks':'639263338065379830'},'Current parent-number record matches full exploreridentity')
ck(s['first_CIM']['records']==s['second_CIM']['records']==[],'Saved narrow scans have no records; not independent freshOS capture')
ck(cur['files']==old['files'] and len(cur['files'])==16,'16 saved state/log bindings unchanged vs0509')
for x in cur['files']:ck(same(x),'Read-only current small state/log matches savedbinding: '+Path(x['path']).name)
prior={a['source']['path']:a for a in os['states']};heart=[]
for a in s['states']:
 prev=prior[a['source']['path']]
 ck(a['source']==prev['source'] and a['status']==prev['status'] and a['heartbeat_utc']==prev['heartbeat_utc'],'Saved state/status/heartbeat unchanged: '+Path(a['source']['path']).name)
 ck(same(a['snapshot']),'New saved state snapshot real bytes match ownbinding')
 snap=read(a['snapshot']['path'])
 ck(snap['status']==a['status'] and snap['heartbeat_utc']==a['heartbeat_utc'],'Saved snapshot status/heartbeat fields agree')
 heart.append({'path':a['source']['path'],'status':a['status'],'heartbeat_utc':a['heartbeat_utc'],'historical_controller_pid':snap.get('controller_pid'),'historical_supervisor_pid':snap.get('supervisor_pid'),'pid_fields_are_not_current_ownership':True})
ck(len(heart)==5,'Five state heartbeat records checked')
ck(cur['carrier']==old['carrier'] and cur['carrier']['byte_values']==[48],'Saved carrier metadata/creationtick/byte unchanged')
ck(same(cur['carrier']) and Path(cur['carrier']['path']).read_bytes()==b'0','Current carrier byte exactASCII0; read only no lock acquisition')
ck(same(s['gpu_query']),'New saved GPU text matches ownhashsize')
g=Path(s['gpu_query']['path']).read_text();rows=[r for r in g.splitlines() if re.match(r'^\s*\d+\s*,',r)]
ck(len(rows)==s['gpu_process_rows']==os['gpu_process_rows']==23,'23 saved GPU rows counted from new rawtext; unchanged count')
ck(s['gpu_query']['sha256']==os['gpu_query']['sha256'],'Saved GPU query rawbytes unchanged vs0509')
ck(s['gpu_query_exit_code']==0 and s['original_gpu_exclusive_gate_would_be_satisfied'] is False,'GPU query succeeded but original exclusive gate false')
ck(cur['t6_output_absent'] is True and s['t6_output_exists'] is False,'Both saved observations report absentT6 output')
paths=[EX/'t6_recovery_preparation_20260929_1548'/'runtime_attempt',EX/'t6_recovery_preparation_20260930_0104'/'runtime_attempt',EX/'t6_recovery_preparation_20260930_0405'/'runtime_attempt',EX.parent/'transfer_native_visio_candidate_20260930_0104'/'runtime_attempt_v1']
attempts=[{'path':str(x),'exists_at_readonly_review':x.exists()} for x in paths]
ck(not any(x['exists_at_readonly_review'] for x in attempts),'All3T6 andVisio attempt paths absent at separate passive filesystemcheck')
ck(same(root['observation']) and same(root['stopped_observation']),'New root seal binds exactly these two observations')
ck(root['execution_released'] is False and root['boot_unchanged_since_previous_turn'] is True,'Current root interpretation matches unchanged source-only state')
ck(set(root['attempts_absent_at_seal'])==set(str(p) for p in paths),'Root seal explicitly covers all4attempt paths')
readme='''本次为独立AI对保存观察、观察器文本及少量文件字节的复核，未重新调用CIM、nvidia-smi或持有任何进程句柄。两广扫描、两窄扫描都是根已保存的OS捕获，不是本代理独立第二次捕获。\n\n当前boot639263337875000000与0509观察、0405合同一致。保存完整Visio29480/creation639263338233256210/普通Office命令和当前父explorer13076/creation639263338065379830与前轮相同；此为非任务所有应用，无附加/关闭授权。旧科学PID不出现不证明独立exit0，state内历史PID也不等于当前owner。\n\n16state/log绑定和实际小字节、5状态/heartbeat、新保存GPU原文本23行及exit0、carrier一字节0都保持。GPU门false，未测本轮availablecommit，不能称资源准入满足。T6仍无输出；四attempt目录另行只读存在性检查均无，但snapshot不授权未来启动。\n\n原broad的contract_boot_matches_current=false仅指历史Sep29合同；旧runtime_attempt_absent也只查Sep29目录。新root和本复核显式使用0405合同/三T6与Visio路径，未扩张旧字段含义。这些是已知范围提示，不是新失败。无实质状态变化或新需用户处理事项。未执行科学/COM/recovery/release/intent/lock，未改旧文件或state。\n'''
with (D/'REVIEW.md').open('x',encoding='utf-8',newline='\n') as f:f.write(readme)
r={'schema':'independent-saved-heartbeat-observation-review.v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'IndependentAI text and small-byte review only; no fresh CIM/GPU/held-process capture','checks_count':len(checks),'checks':checks,'inputs':list(bindings.values()),'current_saved_boot_ticks':contract['host_boot_utc_ticks'],'current_full_visio_and_parent_record':v,'state_heartbeats':heart,'attempt_path_passive_checks':attempts,'separate_review_readme':bind(D/'REVIEW.md'),'review_source':bind(__file__),'disposition':{'material_change_since0509':False,'new_objection':False,'new_user_action_needed':False,'new_scientific_result':False,'current_resource_admission':False,'GPU_exclusive':False,'commit_headroom_evidence_available_this_review':False,'execution_released':False,'cleanup_authorized':False},'limits':['Saved OS observations are reused as evidence, not independently recaptured.','No exit status inferred from absence, no ownership inferred from PID or timestamp alone.','Historical broad contract flag and old-onlyattempt flag have limited scope, as stated in README.','These snapshots and passive existence checks cannot replace a future complete fresh admission.','No weights/caches/NPZ/image corpus/large archives/scientific modules were accessed.']}
with (D/'OBSERVATION_REVIEW.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'review':bind(D/'OBSERVATION_REVIEW.json'),'readme':bind(D/'REVIEW.md'),'source':bind(__file__),'checks':len(checks),'input_bindings':len(r['inputs'])},ensure_ascii=False,indent=2))
