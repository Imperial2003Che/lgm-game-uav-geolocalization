"""One append of limited research evidence; never modify scientific state or old artifacts."""
from pathlib import Path
import datetime as dt, hashlib, json, os

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = Path(__file__).resolve().parent
SDK = EX/'schema_package_research_20260930_1228'
ICLR = EX/'citation_iclr_open_fields_20260930_1212'
CHM = EX/'schema_chm_directory_static_review_20260930_1228'
OBS = EX/'heartbeat_observation_20260930_1219'
HF = EX/'HANDOFF.md'

def descriptor(p, cap=256*1024):
    n=p.stat().st_size
    if not 0 <= n <= cap: raise ValueError('Bounded new report only: '+str(p))
    with p.open('rb') as f: b=f.read(cap+1)
    if len(b)!=n or len(b)>cap: raise ValueError('Read length changed: '+str(p))
    return {'path':str(p), 'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}, b

def save(p, value):
    b=(json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf8')
    if len(b)>128*1024: raise ValueError('Journal report size')
    with p.open('xb') as f: f.write(b); f.flush(); os.fsync(f.fileno())
    return {'path':str(p), 'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}

root_d, root_b=descriptor(SDK/'ROOT_LIMITED_RESEARCH_ADOPTION.json')
root=json.loads(root_b)
if root_d['bytes']!=23946 or root_d['sha256']!='dd13d790d36ab2c02e81d65106ecdcd2fddfad0771baae3eeec564c3e1b95741':
    raise ValueError('Executed root report exact binding changed')
if root['scientific_execution_or_acceptance_added'] or root['all_task_completed']:
    raise ValueError('Limited scope changed')
selected=[SDK/'ACTUAL_ROOT_ADOPTION_TOOL_RECEIPT.json', SDK/'SDK_DATA_TRANSCRIPT_SCOPE_ADDENDUM.json',
          SDK/'ROOT_ADOPTION_FAILURE_TOOL_RECEIPT.json', SDK/'ROOT_ADOPTION_V1_TO_V2.patch',
          SDK/'adopt_limited_research.py', SDK/'adopt_limited_research_v2.py',
          EX/'schema_limited_research_source_review_20260930_1328'/'SOURCE_DELTA_REVIEW.json', SDK/'ACTUAL_DATA_TOOL_RECEIPT.json',
          EX/'schema_limited_research_source_review_20260930_1328'/'FINAL_SCOPE_REVIEW.json',
          SDK/'ACTUAL_CHM_DIRECTORY_TOOL_RECEIPT.json', SDK/'ROOT_WEB_RESEARCH_SCOPE.json',
          ICLR/'FIELD_REVIEW.json', ICLR/'DELIVERY.json',
          EX/'offline_native_xsd_feasibility_20260930_1212'/'XSD_FEASIBILITY_REVIEW.json',
          SDK/'OFFICIAL_SDK_DATA_DOWNLOAD_V3.json', SDK/'SDK_INERT_PAYLOAD_EXTRACTION.json',
          SDK/'SDK_READONLY_FILE_TABLE_v2.json',
          EX/'schema_msi_file_table_review_20260930_1255'/'SDK_SAVED_FILE_TABLE_REVIEW.json',
          SDK/'SDK_SINGLE_CHM_DATA_EXTRACTION.json', CHM/'STATIC_REVIEW.json', CHM/'SAVED_VALUES_REVIEW.json',
          OBS/'ROOT_OBSERVATION_SEAL.json', OBS/'OBSERVATION_WRAPPER_INCLUDED.json', Path(__file__).resolve()]
bindings=[root_d]+[descriptor(p)[0] for p in selected]
byname={Path(b['path']).name:b for b in bindings}
now=dt.datetime.now(dt.timezone.utc)
london=now+dt.timedelta(hours=1)
utc=now.isoformat()
old=HF.read_bytes()
old_sha=hashlib.sha256(old).hexdigest()
if len(old)!=457639 or old_sha!='953b77bdea29a2a10eae44e197542e7b826b7b4c67d3ee2ef43948e57448d61d':
    raise ValueError('HANDOFF changed; no append or retry')
source_d=byname['seal_research_handoff.py']
delivery={
    'schema':'lgm.limited-research-delivery.v1', 'sealed_utc':utc,
    'root_adoption':root_d, 'joint_data_transcript_correction':byname['SDK_DATA_TRANSCRIPT_SCOPE_ADDENDUM.json'],
    'final_scope_review':byname['FINAL_SCOPE_REVIEW.json'],
    'bindings':bindings, 'binding_count':len(bindings),
    'citation_scope':'Three ICLR ordinal gaps closed; three publisher roles/current literal OpenReview Cite unknown. No confirmed reference error or manuscript change.',
    'format_scope':'Actual official SDK inert-byte acquisition/extraction, one read-only MSI query and one uncompressed CHM directory listing. Applicable complete2012 XSD/import closure and Visio application acceptance remain pending.',
    'root_first_invocation':'b9f32d exit1, invalid utf8-sig spelling before reportwrite; source/failure preserved. Separate v2 codec/provenance delta reviewed before its single actual invocation; actual result is in bound tool receipt.',
    'source_failure_branches':'Static review does not dynamically test exceptional paths; data API close returns are not process exits.',
    'scientific_execution_added':False,'new_figure_or_paper_delivery':False,'Overleaf_updated':False,
    'full_XSD_application_acceptance':False,'all_task_completed':False,
    'known_resource_blocker_unchanged':True,'automation_retained':True,'notification_decision':'DONT_NOTIFY',
    'method':'Root AI read the new sources/deltas/reports and performed stated ordinary data actions. Peer AI saved-value/static reviews are distinct from independent API/container decoding or human review.',
    'no_old_large_rehash_or_passed_suite_replay':True,
    'handoff_before':{'path':str(HF),'bytes':len(old),'sha256':old_sha},
    'append_semantics':'Cooperative in-process byte comparison and prefix-preserving append; not atomic against arbitrary external writers. No science state, locks, release, intent or app action.'}
delivery_d=save(HERE/'DELIVERY.json',delivery)

def tag(name):
    x=byname[name]; return f"{x['bytes']}B/{x['sha256']}"

text=f'''\r\n## {london:%Y-%m-%d %H:%M} Europe/London — 限定引用与文件格式资料调查；无科学/新图稿/应用验收\r\n\r\n本轮先读最新HANDOFF12:10文件交付记录。根实际采用时间{root['adopted_utc']}，EX/schema_package_research_20260930_1228/ROOT_LIMITED_RESEARCH_ADOPTION.json {root_d['bytes']}B/{root_d['sha256']}，{root['binding_count']}个具名新研究输入绑定，非科学测试数。根首次adopt_limited_research.py实际b9f32d exit1在CSV decode未知codec utf8-sig处、任何root报告写前；三原Bib块比较已先发生，不能称首exit0。原source {tag('adopt_limited_research.py')}和失败receipt保持；另v2仅utf-8-sig及三局部provenance输入，source {tag('adopt_limited_research_v2.py')}，完整diff {tag('ROOT_ADOPTION_V1_TO_V2.patch')}，独立SOURCE_DELTA_REVIEW {tag('SOURCE_DELTA_REVIEW.json')}。实际v2工具结果见ACTUAL_ROOT_ADOPTION_TOOL_RECEIPT {tag('ACTUAL_ROOT_ADOPTION_TOOL_RECEIPT.json')}，不重跑旧suite/producer/科学。\r\n\r\nICLR局部FIELD_REVIEW {tag('FIELD_REVIEW.json')}与DELIVERY {tag('DELIVERY.json')}：12作者/booktitle/type/publisher保存字段对三真实Bib块，3会议序数缺口（2017 fifth/2018 sixth/2019 seventh）已核官网；作者列表与会议上下文有原作者/机构资料支持，非12项全新发现。三个publisher角色及current OpenReview Cite/venue-ID仍unknown，0已证错误；不改BibTeX/论文/编译/数字/图。根另实际读六primary页面，web时间未完整捕获不虚造；OpenReview403和access error不作未存在证明，非全bibliography或人工审稿。\r\n\r\n初始XSD_FEASIBILITY_REVIEW {tag('XSD_FEASIBILITY_REVIEW.json')}保留当时未下载的历史范围。正确2012/main九part及import依赖未全部获得/验收；官网另长schema为2011/1/core且有XSD1.1构造，不改namespace/删约束/拼片段代替。随后根真实普通数据动作：从fresh官方Microsoft details id36825得到精确download.microsoft.com URL，v3一次47081a exit0，OFFICIAL_SDK_DATA_DOWNLOAD_V3 {tag('OFFICIAL_SDK_DATA_DOWNLOAD_V3.json')}。14,250,888字节EXE仅.exe.data，实际SHA a5128bd6c38912f7ad0b2e6e54e804ea8890c2e3328436a90e01d59b8fcda533；未执行/安装。原Python403/PS v2 header类型失败保留。ACTUAL_DATA_TOOL_RECEIPT {tag('ACTUAL_DATA_TOOL_RECEIPT.json')}必须联合SDK_DATA_TRANSCRIPT_SCOPE_ADDENDUM {tag('SDK_DATA_TRANSCRIPT_SCOPE_ADDENDUM.json')}：v2实际已写137665B HTML，后package Fetch-Bounded在Invoke-WebRequest返回后转换Content-Length失败；旧“before page-body file or package download”措辞过宽。无v2 package文件/完成report，但不称没有接收网络package bytes；不重写原receipt。\r\n\r\n根7acc48仅PE/CAB头与MSCF carve，实际outer CAB13893516B/b1f80267f000c2ff7b8ddeea9c888381907c611640ee9497692e4df8cc1fcd3c；系统expand只列/提取inert CAB/EULA/readme，1cad21 exit0，SDK_INERT_PAYLOAD_EXTRACTION {tag('SDK_INERT_PAYLOAD_EXTRACTION.json')}。Inner CAB13365839B/e2b013e7375cfe4e668af792630e07008c92615be984c34b4e767b6b2cad328b，header declared13350399留15440未知trailing bytes，不当完整CAB验证；236文件名为File key aliases，不直接当installed name。EULA仅文本读，无许可法律结论或安装动作。\r\n\r\nread_sdk_file_table_v1未执行；新v2完整delta/失败诊断和独立close分支先读。真实一次bfad3d exit0调用已装System32 msi.dll READONLY+一个4列SELECT，SDK_READONLY_FILE_TABLE_v2 {tag('SDK_READONLY_FILE_TABLE_v2.json')}：236完整保存行，238个record/view/database Close返回0，无错误，MSI before/after3063808B/738282e60eb7e2470248cefb89389e6e73680ce4b3d9237f80e17a8259123462实际一致。无installer/actions/customactions/msiexec/downloaded代码。独立SDK_SAVED_FILE_TABLE_REVIEW {tag('SDK_SAVED_FILE_TABLE_REVIEW.json')}一次a3da98 exit0仅15新保存关系checks/4小绑定，236 File key/size吻合，234 installed名与alias不同，23文档为6CHM+17HTM；无独立API调用/MSI或CAB重读，其作者先写v2诊断delta这一角色范围保留。保存238API close不是launcher/interpreter退出证据。\r\n\r\n根3c7b84 exit0系统expand仅VISSDK.CHM数据，SDK_SINGLE_CHM_DATA_EXTRACTION {tag('SDK_SINGLE_CHM_DATA_EXTRACTION.json')}：6764354B/19a74be23751db246fdf047d49a187187074113ad9095febd0cb640dba465a4a，未help viewer/COM/member运行。目录reader v1/v2/v3未执行、全部源与三完整delta保留；根完整读最终v4和STATIC_REVIEW {tag('STATIC_REVIEW.json')}后实际0b910c exit0一次，chm_directory_attempt_v1已消费不删/重放。保存SDK_CHM_DIRECTORY_CANDIDATE1566445B/2d9a44834e240e4ea8df4dfc608396e599f0557ad227fac33fa6245ca7b39ab1，12:09:36.921686→.936222 UTC：4312目录member/59chunks（58PMGL/1PMGI）/17section0+4295section1，无schema文件名候选。整个CHM为SHA物理读过，不是每member内容读/解压；未LZX/memberHTML/PMGI内容/quickref/padding/完整CHM/XSD验证。空候选不排除opaque HTML里schema，未形成适用schema集合。独立SAVED_VALUES_REVIEW {tag('SAVED_VALUES_REVIEW.json')}一次4771ee exit0仅保存序号/58链/计数/描述符关系，不独立读CHM或运行parser。上游libmspack master实现仅primary implementation参考、未pinned或Microsoft规范。\r\n\r\n最新本轮现场实际12:15:34双广CIM+12:16:08.3068713 London窄观察：EX/heartbeat_observation_20260930_1219/ROOT_OBSERVATION_SEAL {tag('ROOT_OBSERVATION_SEAL.json')}及OBSERVATION_WRAPPER_INCLUDED {tag('OBSERVATION_WRAPPER_INCLUDED.json')}；stopped observation_20260930_121607895/OBSERVATION5381B/811a25d258a5f378db2a9014dfa8cba94396ea283d12c16dc93538fb633fd485。GPUquery exit0/25rows/原gatefalse/T6outputabsent，同boot639263337875000000；两窄science扫描空，16state/log/5heartbeat及carrier原b0/creationtick未变，3T6与原Visio候选attempt全无。广CIM仍普通VISIO29480,parentexplorer13076/原全命令和ticks；17896现WeChatAppEx,parent5000，不作旧CPUouter退出/归属。历史observer Sep29 bootfalse不当0405当前合同失败。未测available_commit，以上保存snapshot不是root采用时新OS/resource准入，更不是未来release许可；GPU非空不启动等待。\r\n\r\n本轮仅限定资料/源码/保存值调查，根与peer为AI读审、非人工；普通tool0/APIclose/sourcepreparation不替科学双held退出、fresh全图库或验收。全XSD/Visio实际repair-free打开/render/export/edit-roundtrip仍待，上一轮68原生文件包仅file-scope已交付、不再次通知或重hash包/旧权重。42fit/官方42run231task/T3 12run66task/扰动4seed1run120condition660corrupt+22clean/pipeline first6/7不变，T6未测；原primary自身独立exit未知。无scientificrelease/intent/native训练probe/COM/cleanup/共享锁或科学state修改，不关用户app/改分页/减batch-workers-epochs/买云/消费reset额度。0405合同、三attempt/三次准入15s×2/六锁/真实native/15minrelease/捕获退出闭流/五层串行+额外DAC冻结保持；B1/ranking拒绝门不开。LOHO24fit192task/真实解释图/作者和独立baseline/额外DAC/full效率、应用验收、论文终排/最终Overleaf及投稿建议继续，17+6稿/原Overleaf/60.47GB包保持。Full官方10/11与T3全部11R1负结果、seed统计/鲁棒双路径/query masks和全部SHA历史缺边/no freshmodel-fullrank-AP/resampling限制继承，不用资料调查代替科学完成。\r\n\r\n本episode DELIVERY {delivery_d['bytes']}B/{delivery_d['sha256']}位于limited_research_delivery_20260930_1333，{len(bindings)}个局部交接绑定。append为cooperative prefix comparison，非任意writer原子。本轮正常准备/同阻塞无用户可处理事项，DONT_NOTIFY；全部真实实验/终稿图表/最终Overleaf投稿建议交付前保留自动跟进。\r\n'''
text+=f"\r\n后到FINAL_SCOPE_REVIEW {tag('FINAL_SCOPE_REVIEW.json')}仅AI读取最终root/toolreceipt/外置更正三小报告的语义范围，不重读57input/payload或重跑source/API/SCI，不冒人工或独立held退出。根实际完整读审后联合交接。\r\n"
addition=text.encode('utf8')
with HF.open('r+b') as f:
    current=f.read()
    if current!=old: raise ValueError('Concurrent HANDOFF change; preserve delivery, no append')
    f.seek(0,2); f.write(addition); f.flush(); os.fsync(f.fileno())
actual=HF.read_bytes()
if actual!=old+addition: raise ValueError('Post-append mismatch; no rollback/replay')
receipt={
    'schema':'lgm.limited-research-handoff-append-receipt.v1','completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
    'source':source_d,'delivery':delivery_d,'before':delivery['handoff_before'],
    'append_bytes':len(addition),'append_sha256':hashlib.sha256(addition).hexdigest(),
    'after':{'path':str(HF),'bytes':len(actual),'sha256':hashlib.sha256(actual).hexdigest()},
    'prefix_preserved':True,'scientific_or_app_execution':False,'automation_retained':True,
    'replay_allowed':False,'arbitrary_external_writer_atomicity_claimed':False}
receipt_d=save(HERE/'HANDOFF_APPEND_RECEIPT.json',receipt)
print(json.dumps({'delivery':delivery_d,'handoff_receipt':receipt_d,'after':receipt['after']},ensure_ascii=False))
