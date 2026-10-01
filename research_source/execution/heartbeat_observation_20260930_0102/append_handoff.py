"""Append this heartbeat's source-only outcomes, preserving the prior HANDOFF bytes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
EX = HERE.parent
OUT = EX.parent
HANDOFF = EX / 'HANDOFF.md'

def desc(p):
    p = Path(p)
    b = p.read_bytes()
    return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

before = HANDOFF.read_bytes()
assert hashlib.sha256(before).hexdigest() == '213ef815a172f0fc19d7f7989f7d4a86fa87cee196359b066ccd5de737dc14b0'
roots = [
    (EX / 't6_recovery_preparation_20260930_0104/ROOT_SOURCE_ADOPTION.json', 'fff6965e4d794902105f578cadb4680f363c7d6d31dcfd0a29bd3e636ea09343'),
    (OUT / 'transfer_native_visio_candidate_20260930_0104/ROOT_SOURCE_ADOPTION.json', 'ed8704bec372e4b5687b3ca4d1505da1360bd33016c2f63a58a01f738e3d703d'),
    (EX / 'heartbeat_final_observation_20260930_012112779/OBSERVATION_WRAPPER_INCLUDED.json', '6c936b7bde226c013a399a21e55a5fc21e57e0363c2ce4b4e8fd5e151e0743fe'),
]
bindings = []
for path, sha in roots:
    d = desc(path)
    assert d['sha256'] == sha
    bindings.append(d)
for name in ('BROKER_SCOPE_DECISION.md','BROKER_QUERY_IMAGE_OBSERVATION.json','ROOT_OBSERVATION_SEAL.json'):
    bindings.append(desc(HERE / name))

section = r'''

## 2026-09-30 01:31 Europe/London — 当前boot的T6合同与T3 Visio修复源码采用，均未执行

本节覆盖“新boot恢复合同仍未准备”和“T3 Visio尚无修复候选”的旧范围；所有科学计数、五state/heartbeat、11闭合日志和carrier保持。只有小文件来源、合同和源码审查，没有新实验、native训练probe、T6计时、COM尝试、图件、release、intent、retirement、锁或live state变更。上一节完整合作伙伴60.47GB ZIP保持原SHA，本轮未读全包/权重/NPZ/cache/image，也未回写该ZIP。论文/Overleaf未改，70页PPT/SVG与两主图Visio仍是已有交付范围。

### 当前只读状态

根01:02:27+01 `heartbeat_observation_20260930_0102/OBSERVATION_WRAPPER_INCLUDED.json` SHAeec7f7e2c906a63420bed6bf1305c08825d78d1b3c4aa37e97487470e1b27f44；ROOT_OBSERVATION_SEAL a039ce8415a581cc92583ba6d9de476ed7b6b2e8143b42462c18d4b2a51ca103。
最新根01:21:13.729794+01 `heartbeat_final_observation_20260930_012112779/OBSERVATION_WRAPPER_INCLUDED.json` SHA6c936b7bde226c013a399a21e55a5fc21e57e0363c2ce4b4e8fd5e151e0743fe。各两次CIM均只见原已识别AppActions14420与未确认VISIO14932；boot仍2026-09-29T22:31:51.5Z/639263179115000000。AppActions创建ticks639263185295777970/parent2232，完整SystemApps命令与上节相同，不是旧pipeline。Visio14932创建ticks639263209854724070/parent2232，完整Office16/VISIO.EXE /Automation /Invisible -Embedding命令与失败后观察相同；没有原candidate HWND/held证据，仍不归属任务，不附加/关闭/清理。父2232 svchost当前ticks639263179238930240，实际CIM command仍null。未匹配科学owner，不能称running/waiting，absence不补造exit0。
原stopped observer01:02:28+01 `efficiency_incident_20260929_1448/observation_20260930_010228007/OBSERVATION.json` SHA93c3e43fa78a98beca64e23ea9feb34a5c5cc3e8fd0a2ee8a720a9ea89392674；GPUquery exit0/26rows/原exclusive=false，T6输出仍不存在。25→26是同一准入未满足，不是新科学失败。广扫描和根采用时16state/log原SHA/size全部相同，carrier仍ASCII0/原SHA/creationticks；未取得锁。snapshot不是未来准入。

### T6新boot最小合同采用

新候选目录 `EX/t6_recovery_preparation_20260930_0104` 是EX直属，保持原运行器HERE.parent路径语义。pipeline_recovery_candidate.py b95ee9ff8c90b9323b89eb3a9228c36e40576b16830eb07dbd78e38cef1f833e、PS入口3c9e1ec672f6ef7b2a33060495c26d4a766add0b74e2780cc7dc4db732d4eb37、captured失败state47fd31336b8e742da91891a87c28a0767989cb45c375aeb000854f50e37acf12、seed20973168dee96357397f27d103db79eec8f71375272fd3d1e9d240487f1d4360四文件与原件逐字节相同；运行器行为未改。只另派生 RECOVERY_CONTRACT.json SHA d0aa27edfc5391689a947dc7a572d38a9a150186672c7d10965715f12e36d136、SOURCE_MANIFEST.json SHA40b6ae257c53d77a024979d84bae71b85320a13e08a7a8c58a07f24bfacaa141（5候选成员+manifest）。旧14候选不是新目录文件计数。

`EX/t6_new_boot_contract_review_20260930_0104`：derive_new_boot_preparation.py 659b61225b7b0119e2f90efe76985bc63b8e1880c55edc45f2b361dc01589313；DERIVATION7e6b0be0a7c2b26677677082b8a9b27fd07c4c492e0af92bc439d42dda27fce0；CONTRACT_SEMANTIC_DIFF4b6705f6e7725072ead98e47814875eca5c01b9d859038782ea139757c17c477；完整RECOVERY_CONTRACT.patch262b0e2415d098d3c331c041dd9b6a819f931e8441a7cb9f1a280c3ef52b5444；DELIVERY9a405d05c40f4aa0dcf9dbcc8ee9024eba8fc02d905098fa157dc4217c02c99e。
旧96input绑定值不改也未重hash，追加11小来源共107；21项完整语义差异仅新prepared time/当前boot/carrier说明/新来源/限制和新bootauthority。旧事故CAPTURE/spec仍是原科学失败，不改历史seed注释；first6完整job与7个ID/order/command/entrysource保持。旧prepare_contract中旧CAPTURE boot和锁缺失断言不再执行。载体仅旁证，不把被持锁文件加入候选runtime hash列表。

根完整原guardian/PS、新派生源/完整diff/新合同字段及相关小报告读审，独立逐项应用21语义patch精确还原新合同并核4副本、first6/7记录与16live小文件，在01:18:18.266134+01首次266checks通过。新目录ROOT_SOURCE_ADOPTION.json SHAfff6965e4d794902105f578cadb4680f363c7d6d31dcfd0a29bd3e636ea09343；根source12d97c0d90c1433c76c34cd669b62104eb546610f2409b7d99a34b5dcf6681cd。schema仍t6-pipeline-recovery-source-adoption.v1，approved_for_future_gated_execution=true只是源码采用，execution_released=false。
当前boot的未来release须绑定这个新manifest/root，不用旧fd093b97作为新manifest authority；旧root保留不改。当前GPU非空，未出release、未消耗runtime_attempt/intent或启动等待。未来root须重新核新旧两目录runtime_attempt不存在、当前state/source/boot/完整owner缺席/空GPUquery/26GiB available_commit/旧logprefix/carrier/T6absence；原guardian仅直接检查自己的runtime_attempt，新增current_boot_authority是被绑定来源，不能声称额外解析运行时门。原六锁、三次准入/两次15秒、真实isolated native导入和回灌、最终准入、15min release、真实child退出/闭流及后继串行门全部保留。不重跑75/其他旧控制或科学suite。

### T3 Visio broker候选仅源码采用

`OUT/transfer_native_visio_candidate_20260930_0104/build_visio_broker_candidate.ps1` SHA248845f8272306897369f2501e6fcce5a7d347cff4cab873d9c995ee65bc35b1/27526B；CANDIDATE_SOURCE_MANIFEST9a4e25323e9fbadb852ecd73433efedbfa5df2ea8bb36ff7a1e9320cc27caf20；CANDIDATE_INPUT_CONTRACT8031c65d90aba9b0705280abb8c7f7f9274ed81759e3e65f4151eef8bd968f5c；完整原执行源→候选diff3809e21a24497c40085de9394551a7247a4f0b438cd0b65ececda1d43c3cd0e6。旧21b292执行入口未改、未重放。绘图及重开导出代码块逐字不变，20个已采用输入及两notes精确复用，不重跑818/800/1247或旧科学检查。

候选在独立runtime_attempt_v1保存CreateNew+Flush(true)逐门unconfirmed证据，任何已有attempt目录拒绝重放；最早entry marker不是所有权。main try先封builder实际exe/完整command/parent/CIM和held整数ticks，再核源/输入/initial空Visio；每次create均重核空Visio。创建前后保存time bounds，HWND→OSPID/CIM/held身份实值先封再判；all-gates持久写成功后才owned=true。保留direct-builder父分支，新broker分支严格动态核Running/LocalSystem DcomLaunch的精确配置/实时PID映射、父name/creation跨pre/post/fresh/final不变。全部Visio自身实际exe/完整命令/HWND/heldticks/callwindow/invisible/zero-doc门保留。

01:11只读服务映射仍为2232；父实际exe和command为null。一次只读PROCESS_QUERY_LIMITED_INFORMATION诊断 `heartbeat_observation_20260930_0102/BROKER_QUERY_IMAGE_OBSERVATION.json` SHA6e377ea8cbc657a60aab4bb58f652347d1f83bd95c244816cfc871a1e8f23bec，query_broker_image.ps1 b770642028bfdf6b86f287e82dfe63d6936fc444cb7fdc501a11679ad0a9c984：OpenProcess2232返回error5，未获handle，后续QueryFullProcessImageName/GetProcessTimes根本未调用，不说那些API已失败。未提权/附加Visio/控制进程。根BROKER_SCOPE_DECISION.md与独立复核确认原FAILURE_ANALYSIS只要求SCM映射+父CIM创建身份，未要求broker内核image/heldhandle；更强草稿新增门会在COM后必然拒绝，已保存旧草稿及完整scope差异并按原范围修正。
这是服务配置+动态SCM映射+CIM父name/creation证明，null实际exe/command保持未知；可读exe若非空仍必须一致，绝不把服务PathName当实际命令/实际image。Visio自身的实际完整身份门不减；不据该新范围反推旧14932所有权。未知既存Visio仍阻断COM，不能为测试而运行候选。

审查中还修复继承清理分支：doc.Close失败单独捕获后继续app清理；confirmed Quit失败仍尝试release并用原held handle观察退出、释放handle，之后才写清理日志；unknown只release尝试，准确保存成功/失败，永不Quit/Kill。原初稿/entry修订前25603B与cleanup修订前26238B及完整diff均保留。Windows清理分支未执行测试；Add-Type在main try前可只留下entry marker，filesystem/宿主故障仍可中断记录，不能从无报告推退出。

独立 `EX/transfer_native_visio_candidate_review_20260930_0104/PREEXEC_SOURCE_REVIEW.json` SHAf09e81c71bd3092f663ccfc1bd1593e5a2d4b24bab7ee8467ebb424f5dc770fa，DELIVERY879a0052964e5ca579cd46211c97f1cd0e93e3bb126413f029f2cd9c95b0ae46。完整源/diff与12项独立小文件/两代码块检查STATIC_BINDINGS_REVIEW852908b7e5543ca7ebee0de8558fdd6b6e54052187995a69fe212fb16ee0cc1f；BROKER_PREDICATE_REVIEW2aa6206b09a34d8fcf7af8cbee516e3ff8c07e4edef689a791eb5854dac8b112首次11个synthetic fixture，仅取实际AST的10个纯布尔表达式验证null接受、错误exe/PID/ticks/SCM/config/name/recheck拒绝。没有运行IdentityGate/NewOwnedApp/builder/CIM/COM/cleanup。作者14文字/字节检查与ParseFile零error是另一范围，不是独立执行或Windows证明，不再重跑通过的检查。

根完整源、所有完整diff、producer三源及finalizer、独立三源/报告/公开scope读审，独立还原完整old→new diff、82唯一小文件绑定/20输入/两notes/原drawing及reopen块、保存表达式结果和16当前state/log，通过556报告checks，在01:29:49.344319+01首次采用新目录ROOT_SOURCE_ADOPTION.json SHAed8704bec372e4b5687b3ca4d1505da1360bd33016c2f63a58a01f738e3d703d；根sourceabbf8e238f4065fb15e8bf6acc373d60aab97390358a38fceb5d5e0aaf95250d。source_adopted=true/execution_released=false/cleanup_authorized=false/figures_adopted=false/new_figures=0。候选尚无runtime_attempt、VSDX/PNG/PDF/图件或视觉审核。未来实际满足空Visio和科学停止/source/state门后仍需单独根执行决策；本记录不授权现在尝试或清理。旧失败与原合作伙伴ZIP不改。

同一GPU准入与未确认Visio状态保持，本轮源码准备正常完成，不重复通知。后续实际实验、其余Visio、LOHO24fit192task、真实解释图、后继baseline/效率、终稿正文/最终Overleaf/投稿建议继续。原五层+额外DAC、全部冻结协议/public拒绝门、科学负结果/证据限制、不关app/不降参/不消费额度及自动跟进完整保留，全部实际交付后才删除。
'''
section = section.replace('## 2026-09-30 01:31 Europe/London', '## ' + datetime.now().astimezone().strftime('%Y-%m-%d %H:%M') + ' Europe/London', 1)
with (HERE / 'HANDOFF_BEFORE_APPEND.md').open('xb') as f:
    f.write(before)
append = section.encode('utf-8')
with (HERE / 'HANDOFF_APPEND.md').open('xb') as f:
    f.write(append)
assert HANDOFF.read_bytes() == before
with HANDOFF.open('ab') as f:
    f.write(append)
after = HANDOFF.read_bytes()
assert after == before + append
receipt = dict(schema='heartbeat-source-adoptions-handoff-append.v1', utc=datetime.now(timezone.utc).isoformat(), before=desc(HERE / 'HANDOFF_BEFORE_APPEND.md'), append=desc(HERE / 'HANDOFF_APPEND.md'), after=desc(HANDOFF), source=desc(__file__), inputs=bindings, prefixPreserved=True, executionReleased=False, newFigures=0)
with (HERE / 'HANDOFF_APPEND_RECEIPT.json').open('x',encoding='utf-8',newline='\n') as f:
    f.write(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(desc(HERE / 'HANDOFF_APPEND_RECEIPT.json'), ensure_ascii=False))
