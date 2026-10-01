"""One cooperative journal append for an actually adopted new file-only package."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json, os

HERE = Path(__file__).resolve().parent
EX = HERE.parent
OUT = EX.parent
NATIVE = OUT / 'offline_native_visio_20260930_1030'
REVIEW = EX / 'offline_native_visio_independent_review_20260930_1030'
HANDOFF = EX / 'HANDOFF.md'
def create(path, raw):
    with path.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
def desc(path, raw):
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def bound(path, size, sha):
    if path.stat().st_size != size or size > 256 * 1024:
        raise ValueError('bounded delivery report size differs')
    with path.open('rb') as f:
        raw = f.read(size + 1)
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('pinned delivery report bytes differ')
    return raw, desc(path, raw)
if any((HERE / x).exists() for x in ['DELIVERY.json', 'HANDOFF_APPEND.md', 'HANDOFF_APPEND_RECEIPT.json']):
    raise ValueError('Any prior delivery publication refuses replay')
root_raw, root_d = bound(NATIVE/'ROOT_NATIVE_FILE_SCOPE_ADOPTION.json', 109580, 'fe78c427bbcdc4cc6ccbe1774cd7bf790efc99dba7f752b7f70f23ef49d1911d')
package_raw, package_d = bound(NATIVE/'package_attempt_v1'/'DELIVERY.json', 100797, 'e4cf2ff7836e670476cd08ec98c419112c63faf9324c9f97265c757918ea8538')
scope_raw, scope_d = bound(REVIEW/'DELIVERY_SCOPE_REVIEW.json', 6951, '26a402a6dc596ca57bef2232129329936689a0575b6e3c51562685887e56a7e2')
_, root_receipt_d = bound(NATIVE/'ROOT_ADOPTION_ACTUAL_TOOL_RECEIPT.json', 2433, '58149d7efbf00b51f94ec361d2155d23a8c667a4a3f96e673517f76a1f47fbe1')
_, package_receipt_d = bound(NATIVE/'package_attempt_v1'/'ACTUAL_TOOL_RECEIPT.json', 1297, '36a20941fb06962d0b4d858299dc1196a171e3b5ab7e95a70096fe049ed94ba8')
_, delta_d = bound(REVIEW/'SOURCE_ADOPTION_V2_DELTA_ADDENDUM.json', 4850, '60a05535935afe5e7bcca13cc11264078cf824b4e09741697099c3d174486f3f')
_, decision_d = bound(NATIVE/'ROOT_PACKAGE_FILE_DECISION.json', 3375, 'db95a39509547bff059f7b16976b238c59df6b94355369721f3c17505fe16045')
root, package, scope = map(json.loads, (root_raw, package_raw, scope_raw))
if not (root['adopted_for_native_file_scope'] is True and scope['independent_AI_semantic_scope_review_passed'] is True):
    raise ValueError('Actual root file adoption and later independent scope required')
if root['actual_package'] != package['package'] or root['native_file_count'] != 68 or root['package_member_count'] != 394:
    raise ValueError('Actual package relations differ')
if root['scientific_execution_released'] is not False or any(root['application_validation'].values()):
    raise ValueError('File scope must not become science or native-application completion')
before = HANDOFF.read_bytes()
if len(before) != 445721 or hashlib.sha256(before).hexdigest() != 'abd61f4ffa6fb31bd55503262caf7efcd1b830dbfecd68100a95beda57085aa0':
    raise ValueError('Latest HANDOFF changed; do not overwrite or append stale record')
stamp = datetime.now(timezone.utc)
london = stamp.astimezone(timezone(timedelta(hours=1))).isoformat()
delivery = dict(
    schema='offline-native-file-delivery-joint-adoption.v1',
    sealed_utc=stamp.isoformat(),
    scope='68 actual native VSDX files plus sources and native-XML CPU previews; application validation pending',
    package=root['actual_package'], root_file_adoption=root_d,
    package_delivery=package_d, independent_AI_delivery_scope=scope_d,
    actual_forwarded_root_tool=root_receipt_d, actual_forwarded_packager_tool=package_receipt_d,
    external_v2_source_delta=delta_d, one_package_file_decision=decision_d,
    native_file_count=68, native_objects=19945, native_texts=8879,
    native_total_bytes=2582980, family_counts=root['family_counts'],
    font_pt_counts=root['font_pt_counts'], width_mm=181.9,
    ZIP_members_actual_CRC_size_SHA_verified=394,
    root_actual_original_final_CPU_previews_seen=68,
    independent_actual_sample_CPU_previews_seen=2,
    independent_actual_final_representative_CPU_previews_seen=5,
    package_and_native_reports_not_replayed_by_this_delivery_sealer=True,
    new_ZIP_bytes_not_reread_by_this_delivery_sealer=True,
    Visio_application_validation=root['application_validation'],
    scientific_recomputation=False, scientific_execution_released=False,
    all_task_complete=False, automatic_followup_retained=True,
    current_readonly_observation_seal=root['current_readonly_observation_seal'],
    observation_is_not_future_admission=True,
    tool_receipts_are_not_independent_held_launcher_interpreter_exit_proof=True,
    limits=root['limits'],
    note='Read the already sealed README jointly with its packaged 8.5pt font addendum and this later root report. Earlier README/package root-pending fields record their original timestamps; they are not overwritten.',
    source=desc(Path(__file__), Path(__file__).read_bytes()))
delivery_path = HERE/'DELIVERY.json'
delivery_bytes = (json.dumps(delivery, ensure_ascii=False, allow_nan=False, indent=2)+'\n').encode()
create(delivery_path, delivery_bytes)
delivery_d = desc(delivery_path, delivery_bytes)
append = f'''

## 68份原生VSDX文件与源包实际交付，应用验收仍待 — {london}

本轮先读HANDOFF最新10:11 B1 source-only记录及其所引采用/现场限制，实际文件和工具时间优先于heartbeat触发。此次新完成的是已采用科研图件的原生文件表示与交付包，不是新的科学实验、T6/B1执行或最终Visio应用验收。OUT/offline_native_visio_20260930_1030已真实生成68个单页VSDX：T3双向2、seed1扰动22、T4 visual-margin11、T5 risk11、reliability11、paired11。合计2582980B、19945平铺原生对象（rect1892/text8879/circle1818/line7356），宽181.9mm、各自原高度；Arial8/8.5/9/10pt最小8，分别8440/132/239/68文字。逐对象原生结构，不称group/Excel联动/GUI编辑实测；无page raster/embeddedSVG/OLE/Excel/group。原70PPTSVG/2main已应用验收VSDX与所有科学数值、旧稿/60.47GB完整包保持未回写。

方法为普通Python CPU直接写OPC/ShapeSheet原生文字/几何，未启动Office/COM、没有附加或退出当前普通VISIO29480。微软官方允许不经Automation构造文件（https://learn.microsoft.com/en-us/office/client-developer/visio/how-to-manipulate-the-visio-file-format-programmatically），但该说明不是本批应用兼容证据。实际68文件的repair-free打开、Visio重算/渲染/导出、GUI改动保存关闭重开和完整XSD全部pending；原2main的真实Visio证据不能覆盖本68。未来应用验收仍须自然满足真实无既存Visio/无科学owner等当时门并另审执行方案，不能以本批CPU文件放行或清理许可替代。

Builder最终build_offline_vsdx_v2.py30425B/655f0ff75d14826c34eab2d41cee304bf2f656bc9c611468c6e0d997d02370e6，INPUT_MANIFEST_v2.json1052344B/506aa8f9bee244714e61ec610a21345ecbdd89b91cf816d57db1c9c490b10bdd。177已选小源绑定、171精确sidecar副本，仅六原图件authority root精确继承；无旧权重/NPZ/cache/image/大ZIP输入。原initial/v1与两完整diff保留；OneD不合法属性在预执行阶段移除，原生line使用PinX/Y/Width/Angle端点关系/Geometry和LineCap1。两T3 sample首次tool1e379d exit0、根两张实际original CPU预览看完后单次full68 tool5ab393 exit0/8.5316605s。output68/BUILD_REPORT.json92748B/9a25ed045d253652ebfa6363ad274b745fff74f80ef2b8665aeda0d0bd826475；sample/full已消耗，不重放。

独立输入EX/offline_visio_input_review_20260930_1030：INPUT_AUTHORITY_REVIEW254614B/557bbd1480f57d543628b3da3a1288ada07ae44277c9b363991e72603d42ae2c，DELIVERY52720B/af8df41e69edbf68f9b439d58acbdcb4952a6bb337362f5348e6171fa9c4d416，首次1863局部字节/来源/单位检查、163实际绑定；不是新的模型/fullranking/AP/statistics验收。独立reader使用stdlib/Pillow与已安装Arial，CPU预览由实际保存VSDX PageSheet/XForm/Geometry/Text/Character/Paragraph读取，source SVG仅另一来源数值关系核查，不是预览渲染源；未scientific/Office/API。第一次实际v3因codec utf8-sig笔误tool a3a457 exit1，57099 partial局部checks、无完成图/PNG，REVIEW_FAILURE240B/c561494bbc2abcfe99b84252bf76974fcf1f5aff0faf290d7ced6191e1d5fc62及原目录/源保留。新v4仅codec和新review目录delta，不能称v3成功或重放v3。

独立reader_v4.py31719B/29b61bbc0ccd1ba6b4ce63f2d2f6029a84e3380eedf45f944fdd79e54eef4989，full68_review_v4/ARTIFACT_REVIEW5630497B/366a42231df3e23890e813e1bfbe2ae853660a3787f4f218a15708b7a5e6f17a实际首次tool531ad7→1a6cd8 exit0；8641669为重复finite/局部XML/几何/文本/关系守卫计数，后加1输出界限，不是同数科学验收或唯一样本。68真实native-only CPU PNG宽1375，各clip0；Pillow/FreeType baseline/kerning/wrapping/caps只是近似，不等于Visio exporter。独立实际看2sample及5final代表页，不称独立全68视觉。独立DELIVERY57251B/a7d965c96e5edd12364a70100d51960ab537ff832fa2a7d5b243f9baff511e43。

根selected native核查root_native_file_check.py8061B/b9280f48a2a9f82897c226ec3c978ffc3a777f54a8f20030d1b851ab883b3ecb，toolf73c74 exit0，ROOT_NATIVE_BYTE_AND_STRUCTURE_CHECK117575B/477483bc41ee83822a07f35135adaa2a555c261000e21faf3e1a08e8d3caa4a8；347839重复局部守卫/243新来源绑定，171副本、68VSDX/各9part CRC和flat editlock0等所列范围，不重跑独立decoder或科学suite。根全68最终PNG实际original逐页看完，另2sample已看，ROOT_CPU_NATIVE_XML_VISUAL_REVIEW104253B/e9b4d207f941fdd12be551e941bc1df772d323c9f2812e6afd905595bb7f3fcf，toolb2be77 exit0只是记录sealer，不自动代替实际读图。AI读审非人类，未见标签重叠/裁剪、街景低值/零值/负结果保留。

EX/offline_visio_delivery_scope_20260930_1030/README_FINAL.md6571B/03238c13efec6af69fea43e9e910c3a55fd755ae3ef1edbd15d1c94c58ce69af和INDEX_FINAL253618B/200d08d315b5fa2312fab6163e5dc71d25ebf73dcf1d0b7500fa44b84ca487fc保持封存时root/ZIP pending的历史时间范围。第一次metadata finalizer21e75b exit1只因11reliability页尺寸浮点精确比较差≤2.842170943040401e-14mm、写交付说明前；新v2仅该保存metadata比较1e-8mm容差，数据/尺寸原值不改，9a196e首次exit0。FINAL_SCOPE_BINDINGS2502B/dcc54cf756f29b51879f866e6f215ed021768525d4ede3a5efa46fb610af5be1须联合FINAL_EXECUTED_SOURCE_BINDING_ADDENDUM4133B/381e3a83cca246246d3cd665a8f9cb3ed16ebb36fcbfbfbad1011e50da71fc05，旧source常量指针不回写。README漏枚举8.5pt须联合README_FONT_SIZE_ADDENDUM2130B/fd2ecefe72cf562fc3c56ec39c48ac2c31134584b5a41cdc715336c96193a0bb，132实际8.5pt保留，不改任何图。

PACKAGE_INPUTS184381B/3b42cec9166869ba3140484f1fe247f6ed4693feec3c46c21e278298b641fa62由prepare_package_inputs_v3.py11203B/1faa5e4eb0ed4e196a2794259bee3642941bb15d0dbdd0d81d84720db20c3a7d首次bc7fb4 exit0封393payload成员；其v1/v2未执行。根程序逐393安全路径/casefold/suffix/限定新来源及六精确原小图件root报告审核toolabb557 exit0，全文packager/delta及新scope已读。ROOT_PACKAGE_FILE_DECISION3375B/db95a39509547bff059f7b16976b238c59df6b94355369721f3c17505fe16045只授权单次普通CPU文件ZIP，不是science/COM/recovery/locks release。

package_native_delivery_v2.py8891B/df98fea0af8cc087ca9e51c4e24a4c90310125f1fe82c42402df08532476195f实际一次827bfa exit0/1.8836392s。package_attempt_v1已消费，禁止删除/重放；LGM_GAME_68_Native_Visio_XML_And_Sources_20260930.zip20522019B/f96c26e6f01417e85aa7df2d8a2b162404a9f2324fd8485092f0db1a3a8741e9，393payload+非自列非自hashcatalog=394成员实际CRC/size/SHA/byte-match通过。含68VSDX、68CPU native-XML PNG、完整源表SVG/CSV/notes/原图注和source/diff/实际审查记录，未附任何Visio实际PNG/PDF导出或TTF/旧大ZIP/权重。包DELIVERY100797B/e4cf2ff7836e670476cd08ec98c419112c63faf9324c9f97265c757918ea8538与其ACTUAL_TOOL_RECEIPT1297B/36a20941fb06962d0b4d858299dc1196a171e3b5ab7e95a70096fe049ed94ba8保持root_pending历史字段；后到根采用单独外置，不回写已封ZIP。

根adopt_native_file_delivery_v2.py12446B/eff9a5f1e9f7dbc8913fe642eb918c229905ec66a59eccbec0059955f67bcac9全文原源/delta已读、独立外置SOURCE_ADOPTION_V2_DELTA_ADDENDUM4850B/60a05535935afe5e7bcca13cc11264078cf824b4e09741697099c3d174486f3f联合：v1新来源allowlist不含六原小root的预执行不一致修正为506aa8精确manifest唯一六path/size/SHA exception，非runtime失败或任意旧source开放。实际首次680915 exit0/0.5365854s，ROOT_NATIVE_FILE_SCOPE_ADOPTION109580B/fe78c427bbcdc4cc6ccbe1774cd7bf790efc99dba7f752b7f70f23ef49d1911d，原始adopted UTC2026-09-30T10:58:18.908722+00:00；独立读新ZIP全部394成员CRC/size/SHA，并联合报告/图件来源，88110局部JSON/路径/成员守卫与14 selected input bindings（含20.5MB新ZIP与5.6MB独立报告，不统称14小文件）。ROOT_ADOPTION_ACTUAL_TOOL_RECEIPT2433B/58149d7efbf00b51f94ec361d2155d23a8c667a4a3f96e673517f76a1f47fbe1仅680915实际转录，不held launcher/interpreter双exit，不科学/原venv证据。

独立后到DELIVERY_SCOPE_REVIEW6951B/26a402a6dc596ca57bef2232129329936689a0575b6e3c51562685887e56a7e2，tool9344b2 exit0，只AI完整读取5新报告/receipt/addendum，未重读ZIP/native/PNG/旧root或重跑；未见新范围问题。根完整读此报告后联合。本episode DELIVERY {delivery_d['bytes']}B/{delivery_d['sha256']}位于{HERE.name}/DELIVERY.json，采用file-only=true/application-XSD-science-alltask=false；这一局部交付才是新完成，不将源准备/CPU tool0算实验或终稿。

本批数据口径完全继承：Full官方10/11三seed R1+mAP低于Visual，T3全部11meanR1低于Visual，mAP/MRR仅SUES→University street→sat略正。三seed等权sampleSD分母2，R1/mAP%/delta pp/MRR scaled，不pool/SE/CI/显著性。扰动seed1、100×corrupt/各自clean保留率，>100/非单调/低基线保留，Full cached-clean对online-corrupt混合证据路径、64样本非等价。T4仅132Visual-margin/shared mask，330其余存源不绘；N20描述-only，margin非posterior/非机制因果。T5 risk为自己的mask和selected-query风险/realizedkN，十点非all-prefix integral；reliability空bin null/15bin原人数/固定score非posterior/较低ECE非更好校准或准确率；paired selectedANDcorrect/共同全N、同k不同成员、overlap非共同correct，75%原点及utility Holm范围。无模型/fullranking/AP/statistics/独立resampling新验收；历史SHA缺边及metadata不证明当前weight/cache/image byte限制全部继承，CSV/图注/notes源字节保留，不造图或用imagegen。

最新现场为实际11:42:12–13 London只读：EX/offline_native_delivery_observation_20260930_114212033/OBSERVATION_WRAPPER_INCLUDED13937B/f4e72376500024bc3e19ae21132bbfe43f6c877668da7ae6792f260c38f91286，ROOT_OBSERVATION_SEAL13001B/b2fde34bfc2b74076b44e6a5b6b4109925b8452016438097046138e2ab6ac0d1；stopped observation_20260930_114213078/OBSERVATION5381B/3c02473f453dedd757d92a9673ea42519cf3d38643a62e5d8e7d71955ec2ab94实际11:42:13.3915972+01，窄双CIM空/5state-heartbeat原bytes/GPUqueryexit0且25rows/gatefalse/T6absent。广双10:42:12.3916827Z/10:42:13.0219202Z同boot639263337875000000、普通VISIO29480/parentexplorer13076/原fullcmd及ticks，另17896现WeChatAppEx,parent5000/creation639263535469540740和parent639263535467145040，不是旧CPUouter17896/639263506977026507，数字复用不补退出或归属。16state/log/carrierb0/creationtick及3T6+原Visio候选attempt缺席保持；旧observer Sep29 bootfalse不当0405当前合同失败。未测available_commit，GPU非空不生成release/启动候选等待。根采用这里只绑定保存snapshot指针，不重新CIM/GPU或据此放行；它不是未来许可。

本轮无任何scientificrelease/intent/native科学probe/COM/cleanup/用户应用关闭/共享锁或5state修改。当前科学计数42fit/42official231task/12T3 66task/4seed1run120condition和pipeline first6/7不变，primary自身独立exit仍未知，T6未测。0405当前boot合同及三attempt/三次资源准入15s×2/六锁/真实原native子进程/15min release/launcher-interpreter实际退出闭流/后继串行门完整保留，不能用本68文件开B1/ranking公共拒绝门或改封源。LOHO24fit192task、真实cuda16解释图、作者与独立baseline、额外DAC、完整效率、剩余Visio应用验收、最终正文排版/最终Overleaf和投稿建议仍待；17+6工作稿/原Overleaf/60.47GB完整包保持，不读hash旧大包/权重，不重跑已通过source/control/science suite，不关app/减参/分页/买云/消费reset或额度。本次只通知这68新原生文件包一次；同科学资源阻塞静默。全部实际交付前保留每小时自动跟进；本轮无需改原prompt，原指令始终要求先读HANDOFF实际最新，本段优先于旧“其他Visio无文件”描述而不改变应用/科学待项。
'''.encode()
append_path = HERE/'HANDOFF_APPEND.md'
create(append_path, append)
with HANDOFF.open('r+b') as f:
    current = f.read(2 * 1024 * 1024)
    if current != before:
        raise ValueError('HANDOFF changed before append; keep partial delivery and do not replay')
    f.seek(0, os.SEEK_END); f.write(append); f.flush(); os.fsync(f.fileno())
after = HANDOFF.read_bytes()
if after != before + append:
    raise ValueError('HANDOFF append byte check failed; keep actual record')
receipt = dict(schema='native-file-delivery-handoff-append-receipt.v1', utc=datetime.now(timezone.utc).isoformat(),
               previous=desc(HANDOFF, before), appended=desc(append_path, append), result=desc(HANDOFF, after),
               delivery=delivery_d, source=desc(Path(__file__), Path(__file__).read_bytes()),
               original_prefix_and_exact_append_verified=True, cooperative_append_not_arbitrary_writer_atomicity=True,
               scientific_or_Visio_application_execution=False, all_task_complete=False, automation_retained=True)
receipt_path = HERE/'HANDOFF_APPEND_RECEIPT.json'
receipt_bytes = (json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()
create(receipt_path, receipt_bytes)
print(json.dumps(dict(delivery=delivery_d, handoff_receipt=desc(receipt_path, receipt_bytes), handoff=desc(HANDOFF, after)), ensure_ascii=False))
