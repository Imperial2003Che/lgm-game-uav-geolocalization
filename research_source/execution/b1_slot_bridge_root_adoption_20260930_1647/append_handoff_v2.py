"""Append one truthful source-only heartbeat record with cooperative prefix checks."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = Path(__file__).resolve().parent
OBS = EX / 'heartbeat_observation_20260930_162819876'
REVIEW = EX / 'newer_native_b1_slot_bridge_review_20260930_1605'
NOTE = EX / 'predecessor_exit_contract_note_20260930_1647'
CAP = 262144
EXPECTED_HANDOFF_BYTES = 487281
EXPECTED_HANDOFF_SHA = '35e1094a0597f22e0be863f312c797ad5fcb0f25baf084dd5b3c2daa615df2e3'
bindings = {}
cache = {}

def bound(path, expected=None):
    path = Path(path)
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(EX.resolve()):
        raise ValueError('Input escaped execution workspace')
    key = str(resolved).casefold()
    if key not in cache:
        before = path.stat()
        if not 0 <= before.st_size <= CAP:
            raise ValueError('Unbounded input: ' + str(path))
        with path.open('rb') as stream:
            raw = stream.read(CAP + 1)
        after = path.stat()
        if not (len(raw) == before.st_size == after.st_size and
                before.st_ino == after.st_ino and before.st_mtime_ns == after.st_mtime_ns):
            raise ValueError('Saved file changed during read: ' + str(path))
        cache[key] = raw
        bindings[key] = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected and bindings[key] != expected:
        raise ValueError('Saved descriptor mismatch: ' + str(path))
    return cache[key]

def item(path):
    bound(path)
    return bindings[str(Path(path).resolve()).casefold()]

def load(path, expected=None):
    return json.loads(bound(path, expected))

def new_json(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if len(raw) > CAP:
        raise ValueError('Oversized new report')
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

receipt_path = HERE / 'HANDOFF_APPEND_RECEIPT.json'
if receipt_path.exists() or (HERE / 'DELIVERY.json').exists():
    raise ValueError('This append has already been attempted; no replay')
source = load(HERE / 'ROOT_CLOSED_SOURCE_ADOPTION.json', {
    'path': str(HERE / 'ROOT_CLOSED_SOURCE_ADOPTION.json'), 'bytes': 54258,
    'sha256': '018991eae1b13dc0de5b2ec12b0bcd57a4bee8c0153cd12c76c79da714db8cc2'})
research = load(HERE / 'ROOT_PREDECESSOR_CONTRACT_RESEARCH_ADOPTION.json', {
    'path': str(HERE / 'ROOT_PREDECESSOR_CONTRACT_RESEARCH_ADOPTION.json'), 'bytes': 50354,
    'sha256': 'a2842ce77ec791d13411e5c81a66ed26b392df5b70c24d53d3c85a5d39e087e4'})
observation = load(OBS / 'ROOT_OBSERVATION_SEAL.json', {
    'path': str(OBS / 'ROOT_OBSERVATION_SEAL.json'), 'bytes': 15871,
    'sha256': '9dc9c7145421d2afea00198f8cd41f5832cfaffccb637b8e8e436ab067d31a25'})
if not (source['source_adopted'] is True and source['execution_released'] is False and
        research['research_note_adopted'] is True and research['execution_adjudication_adopted'] is False and
        observation['gpu_rows'] == 26 and observation['gpu_gate_satisfied'] is False):
    raise ValueError('Source/research/saved-observation scope mismatch')
for directory, names in (
    (HERE, ('adopt_closed_source.py', 'adopt_predecessor_research.py', 'ACTUAL_ROOT_ADOPTION_TOOLS.json', 'append_handoff.py', 'append_handoff_v2.py', 'derive_append_v2.py', 'APPEND_V2_DERIVATION.json', 'append_handoff_v1_to_v2.patch', 'FAILED_HANDOFF_APPEND_TOOL_RETURN.json')),
    (REVIEW, ('COMPLETED_REVIEW.json', 'COMPLETED_REVIEW.md', 'COMPLETED_STATIC_CHECK_RESULT_V1.json',
              'COMPLETED_STATIC_CHECK_ACTUAL_TOOL_RETURN_V1.json', 'check_completed_review_v1.py')),
    (NOTE, ('PREDECESSOR_EXIT_CONTRACT_NOTE.json', 'PREDECESSOR_EXIT_CONTRACT_NOTE.md',
            'ACTUAL_NOTE_SAVE_TOOL_RETURN.json', 'save_contract_note.py')),
    (OBS, ('OBSERVATION_WRAPPER_INCLUDED.json', 'ACTUAL_OBSERVATION_TOOLS.json', 'seal_observation.py')),
):
    for name in names:
        bound(directory / name)
bound(EX / 'efficiency_incident_20260929_1448' / 'observation_20260930_162821323' / 'OBSERVATION.json')
if len(observation['unchanged_state_and_closed_log_files']) != 16:
    raise ValueError('Missing16 saved state/log descriptors')
state_logs = []
for saved in observation['unchanged_state_and_closed_log_files']:
    expected = {key: saved[key] for key in ('path', 'bytes', 'sha256')}
    bound(saved['path'], expected)
    state_logs.append(expected)
carrier = EX / 'latest_baseline_gpu.lock'
if bound(carrier) != b'0':
    raise ValueError('Persistent byte carrier changed')
absent = []
for path_string in observation['attempts_absent_at_file_seal']:
    # Saved entries are explicit absolute attempt paths, not wildcard discovery.
    path = Path(path_string)
    if not path.is_relative_to(EX.parent) or path.exists():
        raise ValueError('Attempt exists or escaped allowed output scope: ' + str(path))
    absent.append(str(path))
if len(absent) != 4:
    raise ValueError('Need3 T6+Visio attempt checks')
if Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal').exists():
    raise ValueError('T6 output changed; a new incident review is needed')
stamp = datetime.now(timezone.utc).isoformat()
root_source = item(HERE / 'ROOT_CLOSED_SOURCE_ADOPTION.json')
root_research = item(HERE / 'ROOT_PREDECESSOR_CONTRACT_RESEARCH_ADOPTION.json')
review_desc = item(REVIEW / 'COMPLETED_REVIEW.json')
delivery_value = {
    'schema': 'heartbeat-closed-b1-source-research-delivery.v1', 'utc': stamp,
    'scope': 'Necessary closed source adoption and historical contract research; no scientific delivery',
    'root_source': root_source, 'root_research': root_research,
    'independent_review': review_desc,
    'bindings': list(bindings.values()),
    'current16_state_logs_unchanged': state_logs,
    'carrier_current_bytes': item(carrier),
    'carrier_creation_ticks_inherited_saved_observation': observation['carrier']['creation_utc_ticks'],
    'attempts_absent_at_this_file_check': absent,
    'saved_OS_GPU_observation_not_fresh_future_admission': item(OBS / 'ROOT_OBSERVATION_SEAL.json'),
    'primary_own_exit_unknown': True, 'execution_adjudication_adopted': False,
    'scientific_or_native_or_B1_release': False, 'new_scientific_result_or_figure_or_manuscript': False,
    'old_suite_or_checkpoint_or_old_archive_work': False,
    'notification_decision': 'DONT_NOTIFY', 'automation_retained': True,
    'cooperative_file_checks_not_arbitrary_writer_atomicity': True,
}
delivery = new_json(HERE / 'DELIVERY.json', delivery_value)
text = f'''

## {stamp} — 必要闭门B1桥接源码根采用及历史前序合同研究，无新科学/图稿/Overleaf

本轮先读HANDOFF末尾16:12与15:17partial记录及所引报告。前次实际16+6本地引用排版稿/106成员ZIP已通知并保持，不重复发送、编译或验大包。PREP/newer_native_b1_slot_bridge_v1原三v1/三v2/五完整patch/作者SOURCE_MANIFEST c88c720f…与AUTHOR e0ced031…完整保留。根已完整读三选中v2源/五patch、作者离线派生与封存程序/metadata、独立checker及解释；guardian共享源只相关authority/IPC块及先前v3delta继承，不冒称本轮全程序运行或故障安全审计。三选中源仍a7758c1724c14161718a7a7e436d08ca4bfe74f93ee34c782ae37efdcbfd1310 /82b7018c3cb8ffd8923f1e8a3fa7d04eddd2df9e62ab9ab0493fb1a01013f94c /9c03423e679b91bedf855edf51dbcdd82dc4019dcb5b63056aac82994aa311c2，37146/22401/21229B。

独立EX/newer_native_b1_slot_bridge_review_20260930_1605新增COMPLETED_REVIEW.json {review_desc['bytes']}B/{review_desc['sha256']}及MD；check_completed_review_v1.py17229B/686adbbe596f3db35f5460b3ca44c9895cd58ed31b7fea1e3b57e37591086ccd。唯一实际7f1cdb exit0/0.2146681s，21枚举有界小文件独立字节读/hash、AST5源、162局部静态断言、FIRST64(桥40+guardian24)/CLI4/None5、五完整delta字节再生通过，原worker科学执行body只runs→worker_runs控制根字符串。数目不是科学测试/样本/实际运行体测试；未import/执行候选或WinAPI/native/science。Windowsstdout中文路径显示乱码，ACTUAL_TOOL_RETURN完整原样保留；独立清楚path索引从固定checker/metadata分列，不重跑修显示。旧partial四文件及NOT_RUN状态保持历史，后到completed仅覆盖限定静态审查状态。

scope线索无本轮必修：INTERFACE仅要求16key无scope值域，固定producer descriptive scope可互通，真实执行范围由release.scope精确限定；两个relation不核grant.scope值/类型，不能虚称已核。producer canonical+LF，但grant消费者无raw==canonical equality；stable bounded byte/SHA和TTL关联不等于canonical已验/实际资源或锁证明。新effect/public/private/CLI第一句拒绝、exchange与guardian五None pin保留，没有安装issuer/旧门绕过/monkeypatch。根ROOT_CLOSED_SOURCE_ADOPTION.json {root_source['bytes']}B/{root_source['sha256']}，实际d5f4fe exit0/0.2209547s，39唯一新小绑定/348报告局部文件与保存结果一致性检查；只source_adopted=true，execution/runnable/native/B1/science/T6=false。根未重跑162/旧suite，未改变作者/旧根状态。

另EX/predecessor_exit_contract_note_20260930_1647/PREDECESSOR_EXIT_CONTRACT_NOTE.json59670B/c820362a29d8fcc6e725c3a30ca0f52fec5df30ac341483fefc9c5c0da19d946，MD3213B/7d77d06e7eabc2448bb21added292d87a5ea699b41131e04646d85eaa38ef27c；实际c8dfa7 exit0/0.1964694s普通stdlib源研究/保存，postexecution实际收据2317B/998adf18fe7057054edb90e6ce712541d96808bf183b8156bebf022e26208119保留原乱码，不是held退出。曾capacity服务终止与rg错查不存在serial_release.py只研究工具问题，非新科学事故；随后实际dac2_gates.py已读。原pipeline75–93及DAC serial_gate169–200/退出129–140只有saved completed成功job/events与无活owner/合格PID复用，不要求primary顶层自身独立held DWORD0。它是未来有限role policy裁定依据，绝不从absence/Popen或24saved events补造primary exit0、重跑42科学或修改旧root。primary own exit仍unknown，科学42fit/官方采用保持；新B1尚无已采用执行例外/policy/adjudication。本研究不批准例外，未来新执行actor仍按真实合同捕获各自双退出闭流。

根完整note/保存源/10组原行引用及17必要小来源读审，ROOT_PREDECESSOR_CONTRACT_RESEARCH_ADOPTION.json {root_research['bytes']}B/{root_research['sha256']}实际93e76a exit0/0.2055173s，21局部小绑定/257精确保存引用行核验。官方677924B根只继承SHA3b2bb162…与agent已读局部字段，本轮根仅stat，不全hash/附件复验。research_note_adopted=true、execution_adjudication_adopted=false分开，不能据此出release。根两次实际返回保存在ACTUAL_ROOT_ADOPTION_TOOLS.json，均metadata退出，不替代科学独立held退出。真实前序五层+额外DAC、完整quietcollector/外guardianobserver/nativevenv拓扑、执行authority/immutable科学门、六未来CompletedInputs及fresh全图库/ranking/parity/全timing/onlineCLIP仍缺。

本轮真实只读广15:28:20.2480978Z/15:28:20.8847902Z在EX/heartbeat_observation_20260930_162819876/OBSERVATION_WRAPPER_INCLUDED.json16907B/7caf167349e826245ac708e9338c0b39e5cedbbc96ed59cb8277a5ada9425947（da70c3 exit0）。仍普通用户VISIO29480/parentexplorer13076/原完整cmd/ticks639263338233256210与639263338065379830；WeChatAppEx17896/parent5000/639263535469540740与639263535467145040，非旧CPUouter。数字14420现在conhost.exe/parentnode13212/creation639263776238715890，实际cmd为系统conhost 0x4，父creation639263776238680690/完整cua-repl.mjs命令；数字10292现svchost.exe/parentservices2056/creation639263784761765050，实际command=null未知，父creation639263337994081000也commandnull。不能当旧科学PID/当前任务所有权或补exit。

窄stopped observation_20260930_162821323/OBSERVATION5767B/2c8df67c071ea28d70f524062ddad428dcfa4f3b25d416ed3bf1d4407e269670，实际16:28:21.7967026+01（5fc9f3 exit0），双记录各含同14420conhost，非空不能写双CIM空；保存过滤范围未识别原scienceowner。5state/heartbeat原bytes、GPUqueryexit0/26rows/gatefalse/T6absent、同boot639263337875000000。根本轮ROOT_OBSERVATION_SEAL15871B/9dc9c7145421d2afea00198f8cd41f5832cfaffccb637b8e8e436ab067d31a25（af0d16 exit0）核四实际身份/两复用/精确null与原16state-log/carrierb0、当前0405contractroot/三T6+Visioattempt无；旧Sep29observer bootfalse非0405失败。未测available_commit，snapshot非未来准入/历史exit/COM归属许可。append再核16state-log和carrier当前bytes/四attempt/T6absence仅文件核对，不是新OS/GPUquery。

本episode DELIVERY.json {delivery['bytes']}B/{delivery['sha256']}只新局部交接绑定。无science release/intent/native训练probe/COM/cleanup/共享锁/state修改；GPU非空不出release或启动等待，既存Visio不附加/关闭/绕empty门。0405boot合同/三attempt/三次准入15s×2/六锁/原isolatednativeprobe/15minT6release/实际launcher+interpreter退出闭流/五层串行+额外DAC保持；不关app/改分页/降参/买云/消费reset额度。70PPTSVG/2main应用验收Visio/68file-only未XSD或应用验收VSDX/已交付16+6稿/原Overleaf/60.47GB旧完整包和所有科学计数保持。

T6/LOHO24fit192task/真实cuda16解释图/作者20复评/独立9fit42eval与额外DAC3fit30eval/完整效率与fresh图库ranking/完整XSD及Visio无repair-render-export-editroundtrip/终稿正文/最终Overleaf与投稿建议均待真实完成。Full官方10/11与T3全部11meanR1负结果、三seed sampleSD/seed1扰动双路径、T4/T5mask分母非posterior/无indresampling/历史SHA缺边限制完整保留。本轮仅必要健康源码审查/有限合同研究，同已知不可处理实验资源条件，DONT_NOTIFY；全部实际交付前保留跟进。journalappend仅cooperative expected-prefix检查，不保证任意writer原子。

本局部append_handoff.py首112c04 exit1仅metadata reader错误要求size>0而拒绝真实0B闭合pipeline.stdout.log，非过大log/科学失败；发生在DELIVERY/journal写前，根核旧487281B journal prefix与两个报告均未改，原源和实际失败完整保留。另append_handoff_v2.py只允许0<=size<=262144且追加本说明/错误来源索引，完整delta与offline派生封存，未重跑已通过源审查或科学/control suite。
'''
addition = text.encode('utf-8')
handoff = EX / 'HANDOFF.md'
with handoff.open('r+b') as stream:
    before = stream.read()
    if len(before) != EXPECTED_HANDOFF_BYTES or hashlib.sha256(before).hexdigest() != EXPECTED_HANDOFF_SHA:
        raise ValueError('HANDOFF changed; preserve new delivery without append/replay')
    stream.seek(0, os.SEEK_END)
    stream.write(addition)
    stream.flush()
    os.fsync(stream.fileno())
after = handoff.read_bytes()
if after != before + addition:
    raise ValueError('Postappend mismatch; preserve incident, do not replay')
receipt = new_json(receipt_path, {
    'schema': 'closed-source-heartbeat-handoff-append-receipt.v1', 'utc': datetime.now(timezone.utc).isoformat(),
    'delivery': delivery,
    'before': {'path': str(handoff), 'bytes': len(before), 'sha256': hashlib.sha256(before).hexdigest()},
    'addition': {'bytes': len(addition), 'sha256': hashlib.sha256(addition).hexdigest()},
    'after': {'path': str(handoff), 'bytes': len(after), 'sha256': hashlib.sha256(after).hexdigest()},
    'original_prefix_exactly_retained': True, 'scientific_release': False,
    'cooperative_append_not_arbitrary_writer_atomicity': True,
})
print(json.dumps({'delivery': delivery, 'receipt': receipt,
                  'handoff_after': {'bytes': len(after), 'sha256': hashlib.sha256(after).hexdigest()},
                  'local_delivery_bindings': len(bindings), 'notification': 'DONT_NOTIFY'}, ensure_ascii=False))
