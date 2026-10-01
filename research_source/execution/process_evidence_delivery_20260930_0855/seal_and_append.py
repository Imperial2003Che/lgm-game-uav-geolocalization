"""Seal this completed CPU-control episode and append HANDOFF once; no fixture replay."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,os
HERE=Path(__file__).resolve().parent
EX=HERE.parent
RUN=EX/'newer_native_process_execution_v2_20260930_0820'
REV=EX/'newer_native_process_v2_runtime_review_20260930_0826'
records={}
def bind(p,cap=500000):
    p=Path(p);n=p.stat().st_size
    assert n<cap
    with p.open('rb') as f:r=f.read(cap)
    assert len(r)==n and len(r)<cap
    b={'path':str(p),'bytes':len(r),'sha256':hashlib.sha256(r).hexdigest()}
    records[str(p)]=b
    return b,r
def read(p):return json.loads(bind(p)[1])
def verify(b):assert bind(b['path'])[0]==b
def save(p,v):
    with Path(p).open('xb') as f:
        f.write((json.dumps(v,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode('utf-8'));f.flush();os.fsync(f.fileno())
    return bind(p)[0]
root=read(RUN/'ROOT_CURRENT_HOST_CONTROL_ADOPTION.json')
final=read(RUN/'ROOT_REPORT_FINALIZATION.json')
scope=read(REV/'FINALIZATION_SCOPE_REVIEW.json')
assert scope['local_finalization_scope_passed'] is True and scope['original_root_sealer_actual_exit']==1
assert scope['original_root_sealer_exit_converted_to_zero'] is False
verify(scope['joins_original_report']);verify(scope['joins_separate_finalization'])
for b in scope['bindings']:verify(b)
runtime=read(REV/'RUNTIME_REVIEW.json')
assert runtime['fixture_passed_saved_record_audit'] is True and runtime['check_count']==1877 and runtime['unique_input_count']==198
for p in [RUN/'README_DELIVERY.md',RUN/'TOOL_EXECUTION_RECEIPT.json',RUN/'ROOT_BENIGN_FIXTURE_DECISION.json',
REV/'DELIVERY.json',REV/'RUNTIME_SCOPE_AND_BINDING_ADDENDUM.json',
EX/'newer_native_process_execution_20260930_0810/ROOT_FAILED_CONTROL_ADOPTION.json',
EX/'newer_native_process_runtime_review_20260930_0758/FAILED_RUNTIME_METHOD_ADDENDUM.json',
EX/'external_efficiency_preparation/newer_native_process_evidence_v2/SOURCE_MANIFEST.json',
EX/'external_efficiency_preparation/newer_native_process_evidence_v2/DELIVERY.json',
EX/'heartbeat_observation_20260930_0707/ROOT_OBSERVATION_SEAL.json',
EX/'process_fixture_before_20260930_0810/OBSERVATION_WRAPPER_INCLUDED.json',
EX/'process_fixture_after_failure_20260930_0814/OBSERVATION_WRAPPER_INCLUDED.json',
EX/'process_fixture_before_v2_20260930_0830/OBSERVATION_WRAPPER_INCLUDED.json',
EX/'process_fixture_after_v2_20260930_0840/OBSERVATION_WRAPPER_INCLUDED.json',
EX/'process_fixture_after_v2_20260930_0840/OBSERVER_PID_ONLY.patch']:
    bind(p)
stopped=read(EX/'efficiency_incident_20260929_1448/observation_20260930_085248312/OBSERVATION.json')
assert stopped['gpu_query_exit_code']==0 and stopped['gpu_process_rows']==26
assert stopped['original_gpu_exclusive_gate_would_be_satisfied'] is False and stopped['t6_output_exists'] is False
verify(stopped['gpu_query']);verify(stopped['source'])
assert all(s['unchanged_since_incident'] is True for s in stopped['states'])
for s in stopped['states']:
    verify(s['source'])
after=read(EX/'process_fixture_after_v2_20260930_0840/OBSERVATION_WRAPPER_INCLUDED.json')
for b in after['files']:verify(b)
carrier={k:after['carrier'][k] for k in ['path','bytes','sha256']}
verify(carrier)
assert Path(carrier['path']).read_bytes()==b'0'
contract=read(EX/'t6_recovery_preparation_20260930_0405/RECOVERY_CONTRACT.json')
assert contract['host_boot_utc_ticks']=='639263337875000000'
for d in ['t6_recovery_preparation_20260929_1548','t6_recovery_preparation_20260930_0104','t6_recovery_preparation_20260930_0405']:
    assert not (EX/d/'runtime_attempt').exists()
assert not (EX.parent/'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1').exists()
assert root['scientific_results']==0 and root['scientific_execution_released'] is False
assert final['root_control_adoption_finalized'] is True and final['original_root_sealer_actual_exit']==1
stamp=datetime.now(timezone(timedelta(hours=1))).isoformat()
bind(__file__)
d=save(HERE/'DELIVERY.json',{'schema':'root-process-evidence-current-host-control-delivery.v1','delivered_london':stamp,
'current_host_cpu_control_delivered':True,'actual_two_case_control_passed':True,
'original_root_sealer_actual_exit':1,'separate_written_report_finalizer_actual_tool_exit':0,
'root_adoption':bind(RUN/'ROOT_CURRENT_HOST_CONTROL_ADOPTION.json')[0],
'root_finalization':bind(RUN/'ROOT_REPORT_FINALIZATION.json')[0],
'independent_runtime':bind(REV/'RUNTIME_REVIEW.json')[0],
'independent_finalization_scope':bind(REV/'FINALIZATION_SCOPE_REVIEW.json')[0],
'inputs':list(records.values()),'scientific_execution_released':False,'scientific_results':0,'new_figures':0,
'current_boot_ticks':'639263337875000000','latest_gpu_snapshot':bind(EX/'efficiency_incident_20260929_1448/observation_20260930_085248312/OBSERVATION.json')[0],
'replay_authorized':False,'scope':'One current-host benign CPU runtime control episode; historical source manifests and original failed attempts preserved. No science/B1/T6 completion or future admission.'})
text=f"""
## 当前宿主双退出证据的真实 CPU 控制完成 — {stamp}

先读HANDOFF06:13最新记录及所引限制；普通用户“继续”沿既有授权推进。本轮新工作是低层Windows进程证据组件和实际普通Python CPU控制，不是B1/T6或科研结果。科学42fit/官方42run231task/T3 12run66task/4seed1鲁棒性计数及pipeline first6/7保持；原第七T6仍未测量，primary自身独立exit仍未知。未重新读/hash权重/NPZ/cache/image/60.47GB包或重跑旧通过suite。

源码v1 EX/external_efficiency_preparation/newer_native_process_evidence_v1：helper b21c05e40ec721b343a376e95ba10ae590288ce3eecb33b7238fcf58a16ed023、fixture05379eda9addbac90faea33d73eb9a0faa4fc59450bf65e3e1f11de677fca50f、manifest0ca3e4acea597ceaad41eeb35285338d8a0a6f837c2480410faf857631ab9603。原草稿/source/full diff保留，独立静态66ed055d14540d67b4403702ea6008c8a6ab8852eab6fae2777fcfd0a1a619e8只是源码审查。v1一次实际控制外层tool exit92；zero child在ACK后真实sum332833500写出，但三次WAIT_OBJECT_0后post-exit QueryFullProcessImageNameW各Win31，没有保存任何完整DWORD/exit time；nonzero17未启动，无case/result/closed-log success。数字PID10292/8528/17840/1396的事后缺席不补exit。EX/newer_native_process_execution_20260930_0810/ROOT_FAILED_CONTROL_ADOPTION.json 882cfdca7810da1e7ca04ce73b413508f21ea52bc55cafae47927b416b77df3a仅诊断采用，联合独立FAILED_RUNTIME_REVIEW536319eb1dfd14092ed81750a831f63e66bd5d8c504f54a266fdd955d1a6c5ad、METHOD_ADDENDUM3346ed34bef22c9017900bbb63fe2317d1e2acfdfa4875841fb43b80488466a6。根FAILED root首次exit0/156小绑定。首独立failure sealer因Windows glob大小写收OUTER_FAILURE的schema假设失败，原源/failure保留，v2只修数值文件名过滤后首次诊断封存，不科学重跑。

v2新目录 EX/external_efficiency_preparation/newer_native_process_evidence_v2：helper16238B/cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2、fixture与v1逐字节同05379…、manifesta733c63322aefd299ec6d603ece6a769c466e7e61191780a5580a2b1340132aa、完整BYTE_DIFF bba0f1e0c7e509d42429b67d2a79a5f6de98aad8caac1cf5945d53386eec1413。仅两个退出方法改动：WAIT signaled后立即保存实际DWORD incomplete candidate，随后同一连续held handle GetProcessId/GetProcessTimes保存PID/creation/exit raw100ns与.NET整数，再完整exit publication；image仅live时已捕获不退出后requery，也不fresh按PID reopen。unsupported failclosed；不能反推v1丢失exit。独立v2静态814601c3906f6e8870b4e787f60dfb6149b204848781cbea93b7be3436ae7f80只45新delta，不重跑旧384。historical source manifests/delivery源准备字段不改。

EX/newer_native_process_execution_v2_20260930_0820：outer7f06502ca666cffcd2f06b4b3c0242e8deb816ab077bb16d28de6153221a233d仅v1→v2目录字符串；ROOT_BENIGN_FIXTURE_DECISION21954B/d5802b7bcbea908b8eae4dd6a720cab1ae4f0cdfa39abf6c1d2bd9b07d1ed0be单次普通Python CPU决策、62小绑定，scientific_admission=false。已实际一次执行Python311 -I -S -B -X utf8 outer；内部固定-I -S -B，hidden/stdinDEVNULL/新xb流。tool chunk7af064实际exit0/2.0759077s，post TOOL_EXECUTION_RECEIPT仅转录，不独立held outer exit。

v2 actual outer17896 creationticks639263506977026507；controller13180/ticks639263506978052498；zero launcher19432/639263506979383717与child10068/639263506983033482分别真实held exit0；nonzero17 launcher3816/639263506987597532与child17112/639263506991334112分别真实held exit17；outer另held controller13180 exit0。完整Python路径/cmd/current parent与精确heldcreation各两次先核后raw requestSHA/identity ACK；两组真实小任务均ACK后写sum332833500。五不同外部held退出actors，另两条launcher对同child观察，共7保存exit_observed。8case+2controller日志闭流后实际size/SHA/read-sharing封存。outer自己只有forwarded tool0，其aggregate/return intent不补独立held exit。v1和v2两个inner/outer runtime_attempt_v1全部已实际存在/消耗，不删除/rollback/重放。这里没有任何科学venv/torch/CUDA/COM/B1 body/native训练probe、科学release/intent/共享byte锁/state修改。

独立AI EX/newer_native_process_v2_runtime_review_20260930_0826：RUNTIME_REVIEW16400B/04ea2c922415fa9e78e35c6289ca17dd25d6a105637361382028a6635d87fc9a首次runtime审查exit0，1877报告checks/198 INPUT_BINDINGS（67570B/6c3ecb6af7d6d484139c927e27a2dc48e285229c41671006fc6ea0f7e6ed818e）；console1879/199只是封表后source2检查，不额外case。CHECKS397300B/c7731b0cb6909004e898c65574434423d86ab51463f16acdc889e9ee3a987428；DELIVERY958bbe54ce4ec232f717c2bbe564cc3660b4a32c8442f8dc69b761f01458fb3c；联合RUNTIME_SCOPE_AND_BINDING_ADDENDUM12095B/fcc66df66d23d0f88d13fa54305d004f844bc700232be124e4b2c754493b1f14，56新小边。source03409f57c8269ed8ef7c019b4ea1a774a4ed0292fc28d69e3e676e9c7e2bb62f及完整预执行deltaee64c9c6…保留。独立读实际小JSON/log/原producer持有句柄保存值，不重新held原进程/运行API/fixture或科学；非人类审稿。

根已完整源/helper/fixture/outer/修复diff/独立runtime及sealers/source/公开scope读审。ROOT_CURRENT_HOST_CONTROL_ADOPTION104883B/5ecd3ab4c1b04ab3b824ad89298c3dd77b0d6397c23a85731982bcf0cb41b29c/273小绑定，但首次prepare_adoption a0d3495…在完整写入并关闭后返回默认100KB digest-bound时真实exit1；不能称根首次exit0。ROOT_SEAL_POSTWRITE_FAILURE536be19…和完整工具转录891a83d…保留。原root/source不改，另finalize_written_report65063106…首次exit0，仅已有报告字节/来源/索引计数，ROOT_REPORT_FINALIZATION3227B/46be01eaed9cbb1fd33df92e21e726aec266845d0dd890207a2e77c1387f9025联合。独立FINALIZATION_SCOPE_REVIEW15200B/43b53cb28bef485a0f2fef39d5cc64cf077237c8f755173fe8cf68e9bfb30572首次76局部checks/12边，原准备源/6314完整delta保留；根读完整core/sealer/delta，未重跑273/1877/fixture。根当前scope采用及报告字节finalization分别说明，scope review联合不可省。此episode DELIVERY={d['sha256']}，source/关键文件绑定在本目录；README_DELIVERY可直接阅读。source_adopted/current_host_two_case_control=true只是此组件；original_scientific_environment_validated/scientific_execution_released/b1_worker_or_ranking_admitted=false。

现场：本轮07:06London observer及08:04普通CPU前观察保持科学停；v2前广双07:27:34.2049149Z/07:27:34.8045449Z SHA26e0f4aa40943024bff2e3da1c3978cd45165da99d13f613ab40bcdcf4ad6593；v2后广双07:40:07.9877836Z/07:40:08.5768137Z EX/process_fixture_after_v2_20260930_0840/OBSERVATION_WRAPPER_INCLUDED9321B/41a37104c7bdf21d7b732beb89f3be472e258663245c61bdc50cc37db93c7154，仅既有普通VISIO29480/parentexplorer13076及相同ticks/fullcmd，无科学或新CPU actor匹配。observer只添6实际CPU PID，原source/full diff保留；absence不当exit证据。boot639263337875000000保持。原broad历史Sep29 bootfalse仍不是0405合同失败。最新stopped实际08:52:48.6988958+01 EX/efficiency_incident_20260929_1448/observation_20260930_085248312/OBSERVATION5381B/bf893bcf1f5a9c60e666159904ceed68c8c681566af266a0e91c3efad287b12f，窄双CIM空/5state heartbeat原bytes/GPUquery0且26rows/gatefalse/T6absent。采用/交接时再核16state-log/carrierb0原bytes和3T6+Visio候选attempt全无；文件再核非未来OS/GPU准入，没有测available_commit。GPU仍非空不出release或启动等待；不附加关闭普通Visio。

当前组件科学限制：Nt class60仍undocumented/currenthost experimental；Toolhelp当前parent数字配heldcreation不保证完整历史祖先；CreateNew/flush发布与日志read-sharing/流关闭是cooperative，非任意writer原子/历史排除。实际CPU控制不验证原科学venv launcher、实际B1执行器/不可变结果门、前序真实独立exit、当前boot/resource/release/sharedlocks、六fresh CAMP/DAC workers或fresh完整图库/排名/parity/原图全ranking计时/fullonlineCLIP。五个B1入口/CLI与原ranking公共拒绝门保持，不能绕内部primitive或改封v1打开。下一步仍需另新科学controller/worker集成版本与独立审查，不能把本次CPU控制当科学admission、T6完成或后继release。

最新17+6引用工作稿/70PPTSVG/2mainVisio/60.47GB包/Overleaf保持，无论文/图件/科学新增。五层+额外DAC、LOHO24fit192task、真实cuda16解释图、其余Visio、后继baseline与完整效率、终稿正文/最终Overleaf/投稿建议仍待，全部负结果/三seedSD/seed1mixed证据/非posterior/T4T5分母与历史SHA缺边/fullrankAP/resampling限制保持。既有资源授权不变，不关app/减参/买云/消费reset或额度。只通知这一真实新组件控制交付一次，同一科学资源阻塞静默；全部实际交付前保留每小时跟进。
"""
append=('\n\n'+text+'\n').encode('utf-8')
with (HERE/'HANDOFF_APPEND_RECORD.md').open('xb') as f:f.write(append)
handoff=EX/'HANDOFF.md'
before=handoff.read_bytes()
before_record={'path':str(handoff),'bytes':len(before),'sha256':hashlib.sha256(before).hexdigest()}
with handoff.open('r+b') as f:
    assert f.read()==before,'HANDOFF changed before cooperative append'
    f.seek(0,2);f.write(append);f.flush();os.fsync(f.fileno())
after_bytes=handoff.read_bytes()
assert after_bytes==before+append
receipt=save(HERE/'HANDOFF_APPEND_RECEIPT.json',{'schema':'handoff-cooperative-append-receipt.v1','utc':datetime.now(timezone.utc).isoformat(),
'before':before_record,'append':bind(HERE/'HANDOFF_APPEND_RECORD.md')[0],
'after':{'path':str(handoff),'bytes':len(after_bytes),'sha256':hashlib.sha256(after_bytes).hexdigest()},
'delivery':d,'old_prefix_exact':True,'scope':'Exact before-prefix plus new append verified; cooperative CAS, not atomic against arbitrary concurrent writers.'})
print(json.dumps({'delivery':d,'handoff_receipt':receipt,'handoff_after_bytes':len(after_bytes)},ensure_ascii=False))

