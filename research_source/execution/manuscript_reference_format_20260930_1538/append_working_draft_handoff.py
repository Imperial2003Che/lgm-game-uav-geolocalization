"""Append one actual local-draft delivery record, with cooperative prefix checking."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib,json,os
HERE=Path(__file__).resolve().parent; EX=HERE.parent; OUT=EX.parent
NEW=OUT/'manuscript_reference_format_20260930_1538'
OBS=EX/'continuation_observation_20260930_153427732'
HANDOFF=EX/'HANDOFF.md'
def bind(p):
    p=Path(p);n=p.stat().st_size;assert n<=256*1024,str(p)
    b=p.read_bytes();assert len(b)==n
    return {'path':str(p),'bytes':n,'sha256':hashlib.sha256(b).hexdigest()}
def read(p):return json.loads(Path(p).read_bytes())
def write(p,value):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    return bind(p)
roots=[NEW/'ROOT_MANUSCRIPT_REFERENCE_FORMAT_ADOPTION.json',NEW/'DELIVERY.json',HERE/'ACTUAL_ADOPTION_TOOL.json',HERE/'ACTUAL_EXECUTION_TOOLS.json',HERE/'ACTUAL_SUPPLEMENT_TOOLS.json',
       HERE/'SUPPLEMENT_DEPENDENCY_ADDENDUM.json',HERE/'ROOT_VISUAL_REVIEW.json',OBS/'ROOT_OBSERVATION_SEAL.json',OBS/'OBSERVATION_WRAPPER_INCLUDED.json',
       EX/'manuscript_reference_format_review_20260930_1538/INDEPENDENT_FORMAT_REVIEW.json',
       EX/'manuscript_reference_format_review_20260930_1538/INDEPENDENT_SUPPLEMENT_FORMAT_ADDENDUM.json',Path(__file__).resolve(),
       EX/'external_efficiency_preparation/newer_native_b1_slot_bridge_v1/SOURCE_MANIFEST.json',
       EX/'external_efficiency_preparation/newer_native_b1_slot_bridge_v1/AUTHOR_DELIVERY.json',
       EX/'external_efficiency_preparation/newer_native_b1_slot_bridge_v1/INTERFACE_CONTRACT.json']
bindings=[bind(p) for p in roots]
assert bindings[0]['sha256']=='12acbee506d53a95b873786601eaee87f8d0dede15a1d09639c4a274667590e5'
assert bindings[1]['sha256']=='11654ee3002be6cf272af915a5c1e8ca6681264f4bf6c321ba13a53811881b80'
delivery=read(roots[1]);obs=read(roots[7])
for expected in obs['unchanged_state_and_closed_log_files']:
    assert bind(expected['path'])==expected,expected['path']
assert Path(obs['carrier']['path']).read_bytes()==b'0'
assert all(not Path(p).exists() for p in obs['attempts_absent_at_seal'])
prefix=HANDOFF.read_bytes()
assert len(prefix)==476795 and hashlib.sha256(prefix).hexdigest()=='64d090c239508c145a139ca66724934f3eff3e5b4919c9b738785a5976c5f53b'
assert bindings[-3]['sha256']=='c88c720f6f0c14c64f02e4ea4b62bb13135c86a3d0a5723f9a7f674dc9adb99d'
assert bindings[-2]['sha256']=='e0ced0314fd4281e44e320673bd103985fce9951ca010911a119efb8fe676e71'
now=datetime.now(timezone.utc)
body=f'''

## 2026-09-30 {now.astimezone(timezone(timedelta(hours=1))).strftime('%H:%M')} Europe/London — 实际16+6本地引用排版工作稿，非最终稿/Overleaf/科学新增

本次普通用户“继续”后实际交付 OUT/manuscript_reference_format_20260930_1538。ROOT_MANUSCRIPT_REFERENCE_FORMAT_ADOPTION.json 19925B/12acbee506d53a95b873786601eaee87f8d0dede15a1d09639c4a274667590e5、DELIVERY.json 57848B/11654ee3002be6cf272af915a5c1e8ca6681264f4bf6c321ba13a53811881b80，根adopt_and_package_working_draft.py11879B/7b27ee38933130c22f53106f62e0281ac03c72182fe78352db89d93519483939实际44deba exit0/1.5519084s。新LGM_GAME_Reference_Format_Working_Draft_20260930.zip {delivery['zip']['bytes']}B/{delivery['zip']['sha256']}，106成员逐实际CRC/size/SHA通过；新本地包含32可编辑源依赖、正文/补充PDF、BBL、编译/源差异/独立报告与22新预览。旧19MB/60.47GB包不读/不重hash/不回写。main.pdf16p7146864B/2c18c420a3f0e2f4bfd1e0e97ee72c7bbf21bb7b5678c16b3272cdd955b09e7a；supplementary.pdf6p273344B/6b4db9b58dfe94ab6279284b6e769ade1403b312f66f08414314d0dfc3ae0ac0。open_in_codex只返回queued，不虚称当前窗口已显示。

唯一源变更refs.bib17个journal显示字段（GRS10/CASVT6/IP1），均为已装IEEEabrv.bib三标准值，未新增宏依赖。新refs20905B/d868d592aa6510d7b7ecdce5aaa8f1beda6ed0cae380b9acc20e6e970390702e，逆17替换精确恢复父refs21188B/5aa4d85644e26e04f5d2895389d72c2e2cd8d63eeffc59613115f8b527e526e7；571CRLF/583总LF保持。main.tex50800B/fe0dc1a9c03995ea1ad35d5660ccfd3f28749c06d306c0b82d0f2bbc7dd7b07e及其他31源依赖保持。52BibTeX库条目、17改journal、42正文引用严格分开：15正文BBL条目仅缩写/物理折行，27字节完全相同；所有42键/次序完整。没有删引/改作者题名页码DOIURL、字体版心、科学数字/表/图、负结果或证据限制。以0520父root8e6f290c…和外置addendum a1d755bb…联合继承，非重新全bibliography/484数值或科学套件验收。

实际MiKTeX禁自动安装/禁shellescape main-only四命令14:50:23–26UTC，66a69e exit0/3.5186398s；正文一次编译16页，原p17孤AQE引文并入p16。后来根发现supplementary.tex通过输入表格依赖同refs，父supplementary.bbl有mean2025/cdmnet2025/infogeo2026三条；前两期刊也受影响。初始REFERENCE_FORMAT_REVISION.json29673B/b6819b9594296828866347289408e9907e268ca6a202d577d5cf73e61003d338和其inherit-only声明保留历史，必须联合SUPPLEMENT_DEPENDENCY_ADDENDUM.json2936B/245c1d13b9694d3667ea30df0d9f2122e74d3a5b70530ae1e83995ffa7bf02b8；旧supp273353B/8c985d3a77d425fa367418f210f7c5a66cfcb9255b9e70e18180118b7d51a8cb保存在EX/...1538/supplementary.before.pdf及独立compile attempt before副本。另supp-only四命令14:57:17–19UTC，43a07d exit0/2.0280041s；未重编主文、未改supp源/科学。八真实命令均exit0而非自身独立held退出；补充compiler遗留main-only docstring不代表实际循环/命令scope，由显式addendum限定。

根已装Python311/fitz main-only5e22a1 exit0/1.4494389s及supp-only692fb6 exit0/0.54245s，无安装/科学库/GPU。22新PNG中20（main1–15/supp1–5）与0520父预览逐SHA完全相同，继承原视觉验收不重看。根实际original看过新main16与supp6两改变页：42/3参考文献可见、无裁剪/重叠。ROOT_VISUAL_REVIEW.json20207B/a95e865a35ce52cdc01a43f67340c2ea35df41249cd573840c1e096941d61e59；所有22页layout无??/越界/Overfull/undefined，main4underfullhbox、supp2hbox3vbox保持，不称零诊断。字号源未改，不把论文已有公式上标小字号当图表最小8pt全页证明。初始16+6的supp PDF继承决定已被真实supp编译取代。

独立AI EX/manuscript_reference_format_review_20260930_1538/INDEPENDENT_FORMAT_REVIEW.json26345B/dfeffe2733a7b0bb1bff1d575cae4c851891d128ab3e79ceac6145b1417480f0及md4020B/e5a257315dcf8204cf74854d6ff540040b0230d1ba0d154e3358a0dfe19b925b，仅17源字段/21文本依赖与42BBL保留；10图PDF仅从新复制manifest继承，根实际新文件绑定证明；不是人类/全图科学审稿。已执行临时here-string两checker986416/447dc6源码及工具返回后补保存、明确非提前签名日志/不重跑。独立INDEPENDENT_SUPPLEMENT_FORMAT_ADDENDUM.json3922B/3014ffcaa95e1097f9916badcc90ed4143364671df56087e6804858be219aa1e（9c1769 exit0/0.1741451s）仅新增3BBL/2GRS缩写/单supp循环差异，原主报告不改/未重跑主42。根完整源/diff/独立checker报告读审、实际compile/PDF/20samePNG+2视觉及新ZIP验收分别记录；独立未编译/看PDF/484重验/科学执行。

当前实际只读15:34:28London广OBS13925B/80f2a6a7314c99a15219cb2b0bf7c77df88036940113ab17b3d9b74be836476b在EX/continuation_observation_20260930_153427732，双14:34:28.1247144Z/14:34:28.7440226Z同普通用户VISIO29480/parentexplorer13076/原完整命令及ticks639263338233256210/639263338065379830；数字17896仍WeChatAppEx/parent5000/639263535469540740及parent639263535467145040，不当旧CPUouter身份/退出。窄observation_20260930_153454158/OBSERVATION5381B/2a298a631e96a5e818feea491229caf2e59b44c4a03539e6c728af33a0bba2de实际15:34:54.5931842+01，双CIM无科学匹配、5state/heartbeat原bytes、GPUqueryexit0/26rows/gatefalse/T6absent，同boot639263337875000000。ROOT_OBSERVATION_SEAL12979B/3adb4e534ff1f6c946ab2f66b6cce7e21d07f291b15e360a771438af3e9be7bb（ae1afe exit0/0.1907969s）核当前0405contract，历史Sep29observer false不是当前失败；未测available_commit。根采用/journal16state-log/carrierb0和三T6+Visioattempt全无只是文件核对，非新OS/GPU准入。无science release/intent/native训练probe/COM/cleanup/共享锁/state动作；非空GPU不出release或启动等待，不关闭/附加既存Visio。

为必要缺口另新B1闭门one-slotIPC桥接正在静态接线，PREP/newer_native_b1_slot_bridge_v1下v1三源/原→v1完整diff保留，最新v2 native_lifecycle_bridge_v2.py37146B/a7758c1724c14161718a7a7e436d08ca4bfe74f93ee34c782ae37efdcbfd1310，reference_worker_bridge_v2.py22401B/82b7018c3cb8ffd8923f1e8a3fa7d04eddd2df9e62ab9ab0493fb1a01013f94c，guardian_exchange_v2.py21229B/9c03423e679b91bedf855edf51dbcdd82dc4019dcb5b63056aac82994aa311c2，三v1→v2patch保留。作者4562cb/8572a6 exit0仅普通离线源字节派生，未import候选/测试/API/native/science，所有effectFIRST无条件拒绝，initial authority None在nativePopen前拒绝；新slot12字段与distinctgrant/schema不复用old8候选，不修改旧封v1或monkeypatch。本条仅根收到作者未完成seal的进度身份，不是根采用/科学执行验收；独立/root/b1_slot_bridge_static_1605正在完整源/diff有限静态审查，后到AUTHOR/manifests/发现需新append联合，不提前宣称审查通过。actualpredecessor独立exit/currentboot/resource/release/六byte锁/外guardian双held ACK退出闭流/immutable门仍缺，保存resource字段不代表独立物理证明。旧passed50/352/91/75及科学suite不重跑。

本轮只交付新本地16+6排版工作稿，不是最终稿/Overleaf；原审阅项目网址、70PPTSVG/2main应用验收Visio/68file-only VSDX、60.47GB完整包及所有科学计数保持。T6/LOHO24fit192task/真实cuda16解释图/作者20复评/独立9fit42eval和额外DAC3fit30eval/完整图库ranking-parity-原图全排名timing-onlineCLIP/完整XSD及Visio实际无repair渲染编辑roundtrip/后续正文与最终Overleaf投稿建议仍待。Full官方10/11与T3全部11meanR1负结果、3seed sampleSD/seed1扰动混合证据路径、T4/T5mask分母非posterior/无indresampling/历史SHA缺边等限制完整保持。0405boot三attempt/三次15s×2门/六锁/原nativeprobe/15minT6release/真实launcher+interpreter退出闭流/五层串行+额外DAC保持；不关app/改分页/降参/买云/消费reset额度。普通用户继续本轮可通知此真实新工作稿，已知不可处理阻塞不重复通知；全部实际交付前保留自动跟进。append仅cooperative expected prefix核对，不保证任意writer原子。
'''
body+='''\n桥接后到作者seal覆盖上文“作者未完成seal”状态：SOURCE_MANIFEST.json8528B/c88c720f6f0c14c64f02e4ea4b62bb13135c86a3d0a5723f9a7f674dc9adb99d、AUTHOR_DELIVERY.json9623B/e0ced0314fd4281e44e320673bd103985fce9951ca010911a119efb8fe676e71、INTERFACE_CONTRACT3325B/e5a4644626390653c3453dad5c50b18bd2ffeca6b1031643d902bdcb95b4899b，19新小來源只是作者封存；作者1a8025 exit0/0.2644958s普通metadata，未运行candidate/AST/tests/science。根仅完整读三metadata并局部绑定，不采纳19全部源码边，也未完整读三新v2源/五patch，不能称根采用。独立agent/root/b1_slot_bridge_static_1605在partial完整文本读取后曾服务Selected model at capacity，非候选/科学执行失败；随后仅封partial不补造checker。其dormant grant scope字段可能缺实际值核验仅未完成静态线索，不能称现在已放行/安全/漏洞验收；需要后续完整独立审查及根实际源/diff审读，任何后到partial报告须新addendum联合，不回写本记录。全部旧effect门/FIRST拒绝、authority None/未执行/未根采用完整保持。\n'''
append=body.encode('utf-8')
delivery_record=write(HERE/'HANDOFF_DELIVERY.json',{'schema':'local-format-draft-handoff.v1','utc':now.isoformat(),'inputs':bindings,
    'new_zip_descriptor_inherited_from_actual106_member_delivery':delivery['zip'],'zip_rehashed_for_journal':False,
    'state_log_carrier_attempts_file_recheck_only':True,'pending_bridge_source_not_adopted':True,
    'expected_handoff_prefix':{'bytes':len(prefix),'sha256':hashlib.sha256(prefix).hexdigest()},
    'append_bytes':len(append),'append_sha256':hashlib.sha256(append).hexdigest(),'automatic_followup_retained':True})
assert HANDOFF.read_bytes()==prefix
with HANDOFF.open('ab') as f:f.write(append);f.flush();os.fsync(f.fileno())
after=HANDOFF.read_bytes();assert after==prefix+append
receipt=write(HERE/'HANDOFF_APPEND_RECEIPT.json',{'schema':'cooperative-handoff-append-receipt.v1','utc':datetime.now(timezone.utc).isoformat(),
    'source':bind(__file__),'delivery':delivery_record,'before':{'bytes':len(prefix),'sha256':hashlib.sha256(prefix).hexdigest()},
    'append':{'bytes':len(append),'sha256':hashlib.sha256(append).hexdigest()},
    'after':{'path':str(HANDOFF),'bytes':len(after),'sha256':hashlib.sha256(after).hexdigest()},'prefix_preserved':True})
print(json.dumps({'delivery':delivery_record,'receipt':receipt,'handoff_bytes':len(after),'utc':now.isoformat()},ensure_ascii=False))
