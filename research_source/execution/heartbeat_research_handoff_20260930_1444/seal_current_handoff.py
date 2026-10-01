"""One bounded research/source journal append; no scientific or application action."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = Path(__file__).resolve().parent
HF = EX / 'HANDOFF.md'
BEFORE_BYTES = 466359
BEFORE_SHA = 'ed615f06bfe2dd92db3b68643eb2693fc573bd8f434d1e64266f3cc923ed1aca'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded(path, cap=256 * 1024):
    n = path.stat().st_size
    if not 0 <= n <= cap:
        raise ValueError('Selected bounded report only: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(cap + 1)
    if len(raw) != n or len(raw) > cap:
        raise ValueError('Changed selected report length: ' + str(path))
    return {'path': str(path), 'bytes': n, 'sha256': digest(raw)}, raw


def publish(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if len(raw) > 128 * 1024:
        raise ValueError('Journal output bound before CreateNew')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def main():
    input_d, input_raw = bounded(HERE / 'INPUTS.json')
    inputs = json.loads(input_raw)
    if inputs['schema'] != 'heartbeat-research-journal-inputs.v1':
        raise ValueError('Exact journal input schema required')
    selected = {}
    bindings = []
    raw_by_id = {}
    for row in inputs['records']:
        ident, expected = row['id'], row['descriptor']
        if ident in selected:
            raise ValueError('Duplicate journal input ID')
        actual, raw = bounded(Path(expected['path']))
        if actual != expected:
            raise ValueError('Selected new report changed: ' + ident)
        selected[ident] = actual
        raw_by_id[ident] = raw
        bindings.append({'id': ident, 'descriptor': actual})
    required_ids = {'literal_root', 'literal_csv', 'literal_diff', 'region_report',
                    'table_scope', 'literal_ind_delta', 'literal_ind_scope', 'literal_tool',
                    'literal_delivery', 'venue_report', 'venue_delivery', 'guardian_v3_source',
                    'guardian_v2_manifest', 'guardian_v3_addendum', 'guardian_v3_delta',
                    'guardian_ind_v2', 'guardian_ind_v3', 'broad_observation',
                    'observation_seal', 'stopped_observation'}
    if not required_ids <= selected.keys():
        raise ValueError('Missing journal tag inputs before any report publication')
    source_d, _ = bounded(Path(__file__).resolve())
    bindings.extend(({'id': 'journal_inputs', 'descriptor': input_d},
                     {'id': 'journal_source', 'descriptor': source_d}))
    literal = json.loads(raw_by_id['literal_delivery'])
    if literal['confirmed_transcription_corrections'] != 1 or literal['science_execution'] or literal['T6_complete']:
        raise ValueError('Literature-only correction scope changed')
    if literal['root_actual_original_pages'] != 6 or literal['root_literal_values'] != 72:
        raise ValueError('Root literal-reading scope changed')
    venue = json.loads(raw_by_id['venue_delivery'])
    if len(venue['remaining_unknown']) != 4 or venue['final_submission_recommendation']:
        raise ValueError('Bounded venue unknown-field scope changed')
    observation = json.loads(raw_by_id['observation_seal'])
    if observation['gpu_rows'] != 25 or observation['gpu_gate_satisfied'] or observation['execution_released']:
        raise ValueError('Saved known-blocked observation scope changed')
    v3 = json.loads(raw_by_id['guardian_v3_addendum'])
    if v3['source_adopted'] or v3['execution_released'] or v3['runnable_guardian_complete']:
        raise ValueError('Authored guardian was not an execution/adoption authority')
    if v3['selected_source'] != selected['guardian_v3_source']:
        raise ValueError('Authored selected v3 association changed')
    # At append, these are only current file byte checks, not fresh OS/GPU admission.
    state_bindings = []
    for expected in observation['unchanged_state_and_closed_log_files']:
        actual, _ = bounded(Path(expected['path']))
        if actual != expected:
            raise ValueError('Scientific state/closed-log byte change; no journal append')
        state_bindings.append(actual)
    carrier, raw = bounded(Path(observation['carrier']['path']), cap=2)
    if raw != b'0' or carrier['sha256'] != observation['carrier']['sha256']:
        raise ValueError('Persistent carrier bytes changed; no initialization or repair')
    for path in observation['attempts_absent_at_seal']:
        if Path(path).exists():
            raise ValueError('Attempt appeared; preserve journal/source, no runtime replay')
    if Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal').exists():
        raise ValueError('T6 output appeared; require real scientific review')
    before = HF.read_bytes()
    if len(before) != BEFORE_BYTES or digest(before) != BEFORE_SHA:
        raise ValueError('HANDOFF prefix changed; no append or replay')
    now = dt.datetime.now(dt.timezone.utc)
    london = now.astimezone(dt.timezone(dt.timedelta(hours=1)))
    delivery = {
        'schema': 'lgm.heartbeat-limited-research-source-delivery.v1',
        'sealed_utc': now.isoformat(),
        'bindings': bindings,
        'binding_count': len(bindings),
        'literature_scope': 'Root actual six saved original table pages and 72 printed literals; one future research CSV correction89.90->89.00. Independent two printed-value fields inspected in actual pixels and one-byte delta scope only.',
        'venue_scope': 'One agent bounded official lookup; four live/billing fields remain unknown. Root read reports, no independent root web repeat.',
        'guardian_scope': 'Unadopted FIRST-closed v3 source plus independent static diagnostic/delta review, not runnable guardian, native topology validation, execution release or scientific result.',
        'current_file_bindings_at_append': state_bindings,
        'carrier_bytes_at_append': carrier,
        'saved_OS_GPU_observation_is_future_admission': False,
        'current_append_file_check_is_new_OS_GPU_capture': False,
        'available_commit_measured': False,
        'science_or_native_probe_COM_cleanup_lock_or_state_mutation': False,
        'new_figure_or_manuscript_Overleaf_delivery': False,
        'old_weights_NPZ_cache_image_corpus_big_ZIP_read': False,
        'old_passed_science_or_control_suite_replayed': False,
        'T6_completed_B1_admitted_all_task_complete': False,
        'notification_decision': 'DONT_NOTIFY',
        'requires_user_action': False,
        'automation_retained': True,
        'handoff_before': {'path': str(HF), 'bytes': len(before), 'sha256': digest(before)},
        'append_semantics': 'Cooperative byte comparison and prefix-preserving append; no arbitrary-writer atomicity or retrospective process proof.'
    }
    delivery_d = publish(HERE / 'DELIVERY.json', delivery)
    def tag(ident):
        item = selected[ident]
        return str(item['bytes']) + 'B/' + item['sha256']
    text = f'''\r\n## {london:%Y-%m-%d %H:%M} Europe/London — 原报72值局部读核与一字段研究更正；guardian仍未采用/不可运行\r\n\r\n本轮先读HANDOFF13:37最新记录及所引报告，实际磁盘/工具时间优先于heartbeat旧触发。没有新科学、T6/B1测量、图件、稿件或Overleaf更新。42fit/官方42run231task/T3双向12run66task/鲁棒4seed1run120condition660corrupt+22clean和pipelinefirst6/7保持；primary自身独立exit未知，不称当前running/waiting或从absence补exit0。\r\n\r\nEX/camp_dac_root_literal_review_20260930_1353/ROOT_CAMP_DAC_LITERAL_ADOPTION.json {tag('literal_root')}，根真实一次44d2b8 exit0/0.1789188s，createdUTC2026-09-30T12:59:26.069654+00:00。根实际original看六原保存PNG：CAMP物理7/8/9页TableI/II/III，DAC物理7/8/9页TableI/II/IV，共36own-method行72原报显示字符串；71原CSV值一致，一处DAC TableIV物理9/印刷13279 University→SUES受控迁移drone→satellite200m AP研究CSV89.90应为论文实际89.00。纠正的是本地旧研究转录，非作者论文错误或项目科研数字失败。新AUTHOR_REPORTED_ROWS_ROOT_CORRECTED.csv {tag('literal_csv')}，完整ONE_FIELD_LITERAL.diff {tag('literal_diff')}；6440字节只offset5280一个ASCII57→48，原CRLF及其余值/字段保持，原CSV与原报告封存不回写。另一DAC同域300m AP保持98.14；根初看94.14疑点经独立original像素与根高分辨PDF region否定，未写过94.14，不能说两处错误。\r\n\r\n根已装Python311/fitz单次普通数据裁区8f38fb exit0/0.4197519s，REGION_READ_REPORT {tag('region_report')}；两个原PDF顶部高分辨区域真实original看完，未新下载/重hash整PDF或安装软件。六PNG字节与21具名局部根输入属于本次限定来源检查，原整PDF描述符继承，不保证当前wholePDF bytes/全部原render链。根fullpage及独立clippedPDFtext均不含目标数字，不作numeric corroboration。CAMP可见articleheader5637614，物理ordinal7/8/9不是真实印刷页码；早TABLE_READ_SCOPE {tag('table_scope')}里printed_page7/8/9仅物理标签解释须以上文更正联合，不回写旧inventory。DAC印刷13277/13278/13279；天气TableIII与CAMP参数/timing表未纳入72值采用。\r\n\r\n独立EX/camp_dac_literal_delta_review_20260930_1349/DELTA_REVIEW {tag('literal_ind_delta')}只真实看DACp8/p9两个疑点；FINAL_LITERAL_SCOPE_REVIEW {tag('literal_ind_scope')}一次2a14f3 exit0/0.249466s完整根源/1747diff读审与6局部byte关系，未重复全72或21根input图/原PDF/图render/science。根fullsource及独立报告读审后联合ACTUAL_ROOT_LITERAL_TOOL_RECEIPT {tag('literal_tool')}和DELIVERY {tag('literal_delivery')}。普通tool0/写报告不是held launcher/interpreter双退出；AI而非人工审稿。根仅current main.tex/refs.bib wordboundary CAMP/DAC token0核对，不是全稿语义无引用证明，原稿/refs/PDF/ZIP/Overleaf均保持。\r\n\r\n本采用仅将72印刷AP/R1点值作为未来文献转录，不采用原研究报告全部主张或公开baseline融合。CAMP paper24/48批量、oneepoch warmup与code0.1总steps/预训练及AP定义差异，DAC24pairs/48images/10%warmup与ImageNet22k来源分列；同域SUES与University→SUES受控迁移不是作者权重复评或项目独立训练。原报点值不变成三seedmean/SD/CI/显著性，不跨height/directionpool；项目官方trapezoidmAP/cosine/ties/frozenrecipe不改，Full主结果10/11和T3全部11meanR1负结果、所有historicalSHA缺边/未freshmodel-fullrank-AP/resampling限制完整继承。\r\n\r\n另EX/submission_open_fields_research_20260930_1405/OPEN_FIELDS_REVIEW {tag('venue_report')}及DELIVERY {tag('venue_delivery')}是agent13:02:33–13:06:29UTC四次有界官网工具读核，根完整读报告但未独立重web。RemoteSensing APC与instructions直读均429；generalAPC直读internalaccesserror无明确HTTP。CHF2700仅两个月前/上月官方index参考，liveAPC/authorformat仍unknown。IEEE generic supplementary guidance实际直读支持单独上传PDF；100MB仅video，单独上传不证明不计费。TGRS/JSTARS当前作者页有界直读/targetedfind未找到补充PDF计入超页/收费的明确规则，两项继续unknown；页码说明/printedpages字样不补造规则。旧TGRS230USD超10页/GRSS200、可选OA2800与JSTARS1800仅继承不新验收；不将IEEE17+6转MDPI页数、不算新费用/最终建议/录用概率/分区，不投稿/购买/发编辑信。四unknown无新用户操作。\r\n\r\n必要的B1六freshworker外guardian只完成未采用源码草稿，PREP/newer_native_b1_guardian_v1/guardian_v3.py {tag('guardian_v3_source')}；不可运行/未import/未API/native/science/未执行控制或生成release/intent/attempt，不以source preparation代SCI。原guardian.py38756B1ec7630e…、v2 40136Bc2dbebea…/完整3702delta、旧SOURCE_MANIFEST {tag('guardian_v2_manifest')}与AUTHOR_DELIVERY/README保持；v3须联合SOURCE_REVIEW_ADDENDUM_V3 {tag('guardian_v3_addendum')}和完整8641delta {tag('guardian_v3_delta')}。原大shell sourcewrite CreateProcess206在shell启动前拒绝，无源/科学进程执行；4933fc/89f89a、809187/f5c0e0实际exit0仅普通CPU离线源派生/metadata封存，不nativevenv或双heldexitproof。\r\n\r\n根完整读v2与3702delta/manifest/template/README、v3完整8641delta及新保留分支和源派生程序；独立静态诊断/受影响delta报告分别为 {tag('guardian_ind_v2')} / {tag('guardian_ind_v3')}。v2 partial写/APIwait/terminal异常/setupfailure写可逃出retention，被作者与独立静态发现；没有runtime事故，不能借FIRSTclosed宣称旧异常路径完整。v3仅最小源安排：lock.acquire移setup try、locking前记acquisition_started，partial/actorwait/ledger/边界/sleep异常留owner/stream，不从写失败补退出/默认unlock；unknown descendants与openstreams仍阻断，不补空/补exit。此是AI静态delta读审，未动态异常分支/Windows/native或完整Python故障安全证明；硬host/guardian死亡仍释放OS锁，必须残留child新事故审计。原README安全语句仅未验设计边界，由外置新说明限定，不回写旧README。\r\n\r\n四reviewed pins均None：上游含primary历史独立退出实际合同裁定、另审one-slotIPC bridge、完整quietdescendant/science collector、外部heldguardian observer；actualnativevenv/baseimage/fullcommands拓扑未验。_quiet_snapshot明确IncompleteIntegration，不接受caller空数组/回调/布尔为quietauthority。旧native_lifecycle_v1 FIRST拒绝且无本新exchange接口，没monkeypatch或修改封v1开门；新运行/public/private/API/publisher/CLI均FIRST无条件拒绝。六slot模板futureCompletedInputs/request/spec/bootstrap/nonce/release/boot/authority全null，只固定原CAMP frozen_three_seed_final_v3与额外DAC fixed_three_seed prepared；不是liveplan。新的B1≤900秒/单slot proposal和grant不复用原8字段candidate或T6七字段release；不是已有执行许可。完整空GPU/整数26GiB initial/pre-spawn/preACK门保留且无PID豁免；predecessor五层+额外DAC/共享bytecarrier锁/外parent分别heldcontroller-launcher-interpreter/真退出闭流边界是dormant设计，没科学验收/全图库ranking/parity/全timing/onlineCLIP。SOURCEADOPTED/RUNNABLE/EXECUTION/MEASUREMENT仍false，下一步须缺接口实际接线、审查与冻结前序资源自然满足。旧50/352/91/839/1877及科学suite未重跑。\r\n\r\n本轮真实只读现场为13:41:36–38London，广OBS {tag('broad_observation')}及ROOT_OBSERVATION_SEAL {tag('observation_seal')}；stopped observation_20260930_134137737/OBSERVATION {tag('stopped_observation')}实际13:41:38.1087762+01。GPUqueryexit0/25rows/gatefalse/T6absent，窄双CIM空、5state-heartbeat原bytes，同boot639263337875000000；广双12:41:36.6743041Z/12:41:37.2837482Z仍普通VISIO29480,parentexplorer13076/完整cmd和creationticks639263338233256210/639263338065379830。17896现WeChatAppEx,parent5000/639263535469540740与parent639263535467145040，不当旧CPUouter17896/639263506977026507的退出或归属。原Sep29observer bootfalse非0405当前contractfailure；未测available_commit，以上是保存snapshot非未来准入。journal append时16state/log/carrierb0及3T6+原Visioattemptabsence只是文件再核，非新OS/GPU准入。当前GPU非空不出release或启动等待，既存用户Visio不附加关闭、不绕emptyVisio。\r\n\r\n本episode DELIVERY {delivery_d['bytes']}B/{delivery_d['sha256']}，{len(bindings)}局部交接绑定位于heartbeat_research_handoff_20260930_1444，不重新72数字/旧大包权重hash或suite。无science release/intent/nativeprobe/COM/cleanup/共享锁或科学state动作。0405当前boot合同/三attempt/三次准入15s×2/六锁/原nativeprobe/15minT6release/实际launcher+interpreter退出闭流/五层串行+额外DAC及所有冻结限制保持。70PPTSVG/2main应用验收Visio/68file-only未应用验收VSDX/17+6工作稿/原Overleaf/60.47GB包不变。T6/LOHO24fit192task/真实cuda16解释图/作者20复评/独立9fit42eval与额外DAC/完整效率/完整XSD和Visio实际repairfree-render-export-editroundtrip/终稿正文/最终Overleaf投稿建议均未完成；不关app/改分页/减参数/买云/消费reset额度。本轮限定研究更正与健康源码准备不影响当前稿件或scientificresults、同不可处理阻塞，DONT_NOTIFY；全部真实交付前保留自动跟进。append仅cooperative prefix比较，非对任意writer原子。\r\n'''
    addition = text.encode('utf-8')
    with HF.open('r+b') as stream:
        if stream.read() != before:
            raise ValueError('Concurrent HANDOFF mutation; preserve delivery, no append')
        stream.seek(0, 2)
        stream.write(addition)
        stream.flush()
        os.fsync(stream.fileno())
    after = HF.read_bytes()
    if after != before + addition:
        raise ValueError('Postappend mismatch; no rollback or replay')
    receipt = {
        'schema': 'lgm.heartbeat-research-handoff-append-receipt.v1',
        'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'source': source_d, 'inputs': input_d, 'delivery': delivery_d,
        'before': delivery['handoff_before'],
        'append_bytes': len(addition), 'append_sha256': digest(addition),
        'after': {'path': str(HF), 'bytes': len(after), 'sha256': digest(after)},
        'prefix_preserved': True, 'scientific_or_app_execution': False,
        'automation_retained': True, 'replay_allowed': False,
        'arbitrary_external_writer_atomicity_claimed': False
    }
    receipt_d = publish(HERE / 'HANDOFF_APPEND_RECEIPT.json', receipt)
    print(json.dumps({'delivery': delivery_d, 'receipt': receipt_d, 'after': receipt['after']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
