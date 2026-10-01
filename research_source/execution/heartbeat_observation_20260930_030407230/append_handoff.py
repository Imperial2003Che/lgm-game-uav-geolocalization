"""Append this completed source/research step; retain all preceding records."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json

HERE = Path(__file__).resolve().parent
E = HERE.parent
handoff = E / 'HANDOFF.md'
before = handoff.read_bytes()
assert hashlib.sha256(before).hexdigest() == '570ed6a52d95c08e60c7c168a65446ae98d1bd86820595f5c5263d69b0d8e151'
now = datetime.now(timezone(timedelta(hours=1)))
body = f'''

## {now.isoformat()} — B1原编码调用体仅源码采用，投稿要求资料刷新；当前准入未变化

本轮没有新科学执行、独立B1结果、T6测量、图件、论文/Overleaf修订或完整包重打。新完成范围是闭门的B1 worker调用体及其源码审查、供后续最终建议使用的官网要求资料。它们不构成运行准入、终稿或最终投稿建议。相同GPU/未知Visio阻塞和正常源码推进保持静默，自动跟进保留。

根最新实际只读03:04:07+01：EX/heartbeat_observation_20260930_030407230/OBSERVATION_WRAPPER_INCLUDED.json 10740B/f7bb33d67d5b27e3f24bd9d9e0e239f85aedf8cfff558d7368187dc3afe04baa；ROOT_OBSERVATION_SEAL.json 11594B/ef182e57ae99abda18009a3aac38eb1c5e8b4f57e2ccf4f096a9de6f00cc9f6d，root source bff9b4977538e9085dd8f8b53ea60e598d94dde8d27f8abfdccade5a0ac68cd7。两次广CIM仍仅AppActions14420 parent2232/ticks639263185295777970/原SystemApps完整命令及未知VISIO14932 parent2232/ticks639263209854724070/原Office16 Automation Invisible完整命令。父2232 ticks639263179238930240/实际CIM commandnull。没有科学owner；boot仍2026-09-29T22:31:51.5Z/639263179115000000。不得从absence补造exit0或反推Visio原candidate归属。
原stopped observer新目录EX/efficiency_incident_20260929_1448/observation_20260930_030407052/OBSERVATION.json 5871B/bd2e71c368a3929a1c993843ae42bb1a7a3586a0db97a5b86dc05dab0d9aba57；GPUquery实际exit0/26rows/原exclusivefalse、T6output不存在。五state/heartbeat及11日志原bytes不变，carrier ASCII0/原creationticks不变。新boot合同匹配，旧contract mismatch只是历史预期。新旧T6 runtime_attempt及Visio runtime_attempt_v1均无；根源码采用时再核16state/log和carrier未变。无release/intent/native训练probe/COM/cleanup/锁/state动作，snapshot不是未来准入。

### 新B1 worker：实际原调用路径已写入源码，但尚无可执行准入

EX/external_efficiency_preparation/newer_native_b1_worker_v1/reference_worker.py 17414B/eed9b25b1204edbcf5172ea2fb24e272b7ff39103f98448e554a3dae779b7f46；SOURCE_MANIFEST.json 5736B/9f5e40ed7ddd3f35ce48247d37dcb00923f9dae6955b2c89d96261c296460bb3。ROOT_SOURCE_ADOPTION.json 21948B/7164824c5bde5b602978f3c816e76cbb9860611c2232a12910799eb87e0c13e7，根首次exit0/60唯一小文件绑定；root source5d3022ab0a54a982290b5fdb057b295ec7a638eaa80d26301d5a75dd8ce9158c。source_adopted=true、execution_released=false、runnable_worker_validated=false、scientific_execution=false、newfigures0。既有B1 contract/root与ranking公共拒绝门均不改、不绕过；本源不是已完成独立B1执行器。

整个门后调用体使用原CompletedInputs binder/request_from_completed、原保存prepared封印与原protocol.verify_seal后，复用已采用derive_b1_prepared，内存仅batch16→1。derived保留原payload_sha256字段但明确只是历史metadata，对derived无效且不送read_prepared/verify_seal；新envelope分列原文件/原canonical/derivedcanonical。重建request必须与输入JSON canonical+LF精确字节一致。两份真实小prepared均有runtime.prefix=C:\\项目\\.venvs\\lgm-camp，未probe该环境或调用原binder。
唯一科学调用写成原package.evaluator.encode_seed(derived,actual seed binding,去重的十task首query子集,native,log)，没有提取/重编译encoder或用measurement loader替换。原CAMP395 learnedpos_scale、DAC402三头DSA及完整checkpoint严格加载、OpenCV原transform、CUDA FP16归一化→FP32 1024维输出均由原源码保留。完整原read_prepared/encode_seed/strictloader六块及行号/实际bytes在ORIGINAL_CALL_BLOCKS.json 98772d97ff8827ff7ab30de47b78eae842b8889468d6d26724dbc988a08830a9；IMPLEMENTATION_MAP7d20de240c9fd67d30e63090e4eba8ae8ac51a64f739df4ac6eae2f5da249af8。

原local_output/save约束要求native输出在对应原evaluation根内b1_reference_runs/新run；控制记录在新worker/runs/同run，均存在即拒绝，不猴补原路径门。DAC原snapshot_scope围住read_prepared/编码/检查并在前后显式unchanged_inputs，不能只靠退出scope声称重核。原四产物descriptor/imageledger/strictload/runtime由既有candidatechecker核一致性；候选和return_intent仍明确independent_execution/measurement/freshgallery/fullonline/T6/manuscript均false，return0意图不是实际exit。失败仅保留partial文件名/size不把未闭memmap hash作完整证据；失败落盘仍可能失败，须未来外部parent真实退出/闭流保证，未实测。

run_reference/admit_reference/_execute_original_reference/_load_sources_after_admission/_import_pinned五个入口第一句全部无条件ClosedExecutionGate，CLI也拒绝，没有caller bool/dict/path/class/候选返回值可以开门。本轮仅新模块纯stdlib synthetic helper/闭门测试；无原模块、原binder、原encoder、GPU、模型、权重、NPZ/cache/image读取。首版16973B/5b888a1e4bc14985dc5f25e31c12fe1123dc1bee9b9b91f4c09076df117f5353与29checks cf0f17cc158bf4aa8ae20e060e7fccaf3ae06a50b3fcb380b5112fae099301b1保留。根发现普通dict equality容许非batch int/bool/float类型差异、声明size门先hash实际文件可越界；新源改canonical(reverse)==canonical(prepared)及实际stat先判/有界read。完整diff6eaa275e75701e4b0c765a1131f0d2b6b1ba37d77a54b91851316314e09dc7f3；仅5项受影响新checks83720300798440522bdd194ac3353e99854f014fed13504d927e90fb6a1d38e8首次通过，未重跑29或旧suite，不称34项最终运行体测试。

独立EX/newer_native_b1_worker_review_20260930_0304/SOURCE_REVIEW.json 18345B/5f9cfab88d9f05ab8a1047ec7756c1c80f676d5fe7fe1e37b83f6ae5377ad2c7；DELIVERY2822B/d3ce8ed1c606a42436b33c2ac64608131a8c183ee872a544f7555a77c43d15bf；STATIC_BINDING_REVIEW8d8c3181ca978237ebbb2c349153e596018f7542f0ceb4db9eed3ccf22f72c98。AI代理独立全文/AST/小字节检查，13旧源不变、12manifest成员、六原调用块/runtime字段/全部新diff，读29和5报告不重跑、不importproducer。根完整首终源/完整diff/producer checker与sealer/独立两源和报告读审，绑定60小文件/保存报告/当前16state-log，不重复已通过科学或控制suite。
仍需真实外部controller：实际前序完成及独立退出、当前boot/plan/release/资源准入/持共享byte锁、六CAMP/DAC fresh method-seed worker的launcher与interpreter双held身份/先ACK后科学/双exit后闭流/不可变证据门。未来须另新审查source/controller版本，不能修改已封v1或把旧root当执行许可。fresh全图库重编码/排名parity、原图至完整ranking计时、全数据集onlineCLIP准确率仍另待，首query子集不替代这些范围。五层+额外DAC、原T6及所有冻结门继续。

### 投稿要求资料刷新，不是最终投稿建议

EX/submission_requirements_refresh_20260930_0304/REQUIREMENTS_REVIEW_zh.md6810B/db9fafab3365e33dbb64afff447805b399b6b91f9623f4395f17dda79f4cc9cf；WEB_ACCESS baa15dcba8f14155b0bb53af0815aa7b71ff9d7ec7ee4d7ae52351128fc7850f；LOCAL_INPUTS69b476fb9fb4ab1fb7eab58bedf4593e12d3c03c73c69a99dd5f0881b301dad3；DELIVERYc35070ca2b64e25f679b47a288a53156af7ee167e084efe398065e5db7a39a4a。实际官网研究窗口02:05:35–02:08:50UTC/London03:05–03:08，不拿heartbeat触发时间当检索时间。根完整新说明和3报告读审，直接复核TGRS，ROOT_REQUIREMENTS_RESEARCH_ADOPTION.json3590B/c218e11312cc37336245114d981b1e3d309afa6336f67073cd1ff4cfc3ad77f2；root source06df98dddb73f03075590cf7c5c5021e6432f6427de5dfb44cd92a645f6275b9首次exit0。
TGRS2026新稿从第11印刷页起230USD/页、GRSS会员200，10页不是最大页数；Hybrid传统路径无OA APC，2026可选OA2800另计。官网另请求前11页可选110USD/page sustaining费，根附记与mandatory超页费分开；个人/机构实际优惠资格未核。JSTARS官方期刊页由资料代理成功直读确认1800USD/完全OA，根自己的再直读受限，未确认硬页数/超页表。RemoteSensing直接429/失败，采用官方域约两个月前索引：Article至少18页、Results/Discussion分开等仍需选刊前实时确认；IEEE16页+6页补充不等于MDPI18页。索引APC2700CHF仅参考，当前实时确认unknown。两IEEE刊6页supp具体上限/计费unknown，不按22页直接收费。所有三刊不推接受率/分区/录用保证；当前16+6页工作稿范围继承原root，未重新读PDF/ZIP/权重。报告仅后续建议资料，不更新旧最终建议或Overleaf、不提交、不购买服务。

既有16+6页本地论文工作稿、60.47GB完整合作伙伴包、70PPTSVG/两mainVisio保持，未重hash或回写旧大包。T6、LOHO24fit192task、真实解释图、其余Visio、后继作者/独立baseline、额外DAC/效率、最终正文/Overleaf/投稿建议继续。原负结果、sampleSD/seed1/证据路径和历史SHA缺边、未model/fullranking/AP/resampling限制与不关app/不降参/不消费额度规则完整保持。全部真实交付后才删除跟进。
'''
raw = body.replace('\n', '\r\n').encode('utf-8')
with (HERE / 'HANDOFF_APPEND.md').open('xb') as stream:
    stream.write(raw)
with handoff.open('ab') as stream:
    stream.write(raw)
after = handoff.read_bytes()
assert after == before + raw
receipt = {
    'utc': datetime.now(timezone.utc).isoformat(),
    'before': {'bytes': len(before), 'sha256': hashlib.sha256(before).hexdigest()},
    'append': {'path': str(HERE / 'HANDOFF_APPEND.md'), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
    'after': {'path': str(handoff), 'bytes': len(after), 'sha256': hashlib.sha256(after).hexdigest()},
    'old_prefix_unchanged': True,
    'scientific_or_figure_execution': False,
}
out = HERE / 'HANDOFF_APPEND_RECEIPT.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
print(json.dumps({'receipt': str(out), 'sha256': hashlib.sha256(out.read_bytes()).hexdigest(), 'after_bytes': len(after)}, ensure_ascii=True))
