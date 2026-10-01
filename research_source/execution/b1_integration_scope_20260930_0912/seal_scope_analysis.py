"""One-time stdlib source-analysis publication. No module import/fixture/science."""
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
PREP = EX / 'external_efficiency_preparation'

def bind(path):
    path = Path(path).resolve(strict=True)
    before = path.stat()
    if before.st_size > 250_000:
        raise RuntimeError('Only bounded sources and scope records are allowed')
    with path.open('rb') as stream:
        raw = stream.read(250_001)
    after = path.stat()
    if len(raw) != before.st_size or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) != (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
        raise RuntimeError('Source changed while reading')
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}, raw

def save(name, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    with (HERE/name).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return bind(HERE/name)[0]

source_paths = {
 'worker_v1': PREP/'newer_native_b1_worker_v1/reference_worker.py',
 'b1_contract': PREP/'newer_native_b1_contract_v1/b1_contract.py',
 'ranking_bridge': PREP/'newer_native_ranking_v1/ranking_bridge.py',
 'process_helper_v2': PREP/'newer_native_process_evidence_v2/windows_process_evidence.py',
 'benign_fixture_v2': PREP/'newer_native_process_evidence_v2/benign_fixture.py',
 'completed_binder': PREP/'newer_native_loader_v1/source_bindings.py',
 'strict_native_loader': PREP/'newer_native_loader_v1/native_load.py',
 'path_aliases': PREP/'newer_native_loader_v1/path_aliases.py',
 'corrected_contract': PREP/'corrected_driver_v3/contract.py',
 'camp_original_evaluator': EX/'camp_independent_evaluation_v3/run_evaluation.py',
 'camp_original_protocol': EX/'camp_independent_evaluation_v3/protocol.py',
 'dac_original_evaluator': EX/'dac_independent_evaluation_v2/run_evaluation.py',
 'dac_original_protocol': EX/'dac_independent_evaluation_v2/protocol.py',
 'dac_stage_topology': EX/'dac_training_execution_v2/run_six_stages.py',
 'dac_stage_stdlib_entry': EX/'dac_training_execution_v2/stage_entry.py',
}
authority_paths = {
 'worker_v1_root': PREP/'newer_native_b1_worker_v1/ROOT_SOURCE_ADOPTION.json',
 'b1_contract_root': PREP/'newer_native_b1_contract_v1/ROOT_SOURCE_ADOPTION.json',
 'current_host_control': EX/'newer_native_process_execution_v2_20260930_0820/ROOT_CURRENT_HOST_CONTROL_ADOPTION.json',
 'current_host_finalization': EX/'newer_native_process_execution_v2_20260930_0820/ROOT_REPORT_FINALIZATION.json',
 'independent_finalization_scope': EX/'newer_native_process_v2_runtime_review_20260930_0826/FINALIZATION_SCOPE_REVIEW.json',
 'independent_runtime_scope': EX/'newer_native_process_v2_runtime_review_20260930_0826/RUNTIME_SCOPE_AND_BINDING_ADDENDUM.json',
 'camp_prepared': EX/'camp_independent_evaluation_v3/preparations/frozen_three_seed_final_v3/manifest.json',
 'dac_prepared': EX/'dac_independent_evaluation_v2/preparations/fixed_three_seed/manifest.json',
 'current_pyvenv_configuration': Path(r'C:\项目\.venvs\lgm-camp\pyvenv.cfg'),
}
records = {}; raws = {}
for key,path in {**source_paths,**authority_paths}.items():
    records[key],raws[key] = bind(path)
trees = {key:ast.parse(raws[key].decode('utf-8-sig')) for key in source_paths}

def function_block(key,name):
    matches=[n for n in ast.walk(trees[key]) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name]
    if len(matches)!=1: raise RuntimeError('Source function is not unique: '+key+'/'+name)
    node=matches[0];lines=raws[key].decode('utf-8-sig').splitlines()
    raw=('\n'.join(lines[node.lineno-1:node.end_lineno])+'\n').encode('utf-8')
    return {'source':records[key], 'function':name, 'start_line':node.lineno,
            'end_line':node.end_lineno, 'normalized_text_sha256':hashlib.sha256(raw).hexdigest(),
            'normalization':'Source logical lines joined by LF; not original raw byte slice',
            'text':raw.decode('utf-8')}

blocks=[]
for key,names in {
 'worker_v1':('_closed_execution_admission','_import_pinned','_load_sources_after_admission','_execute_original_reference'),
 'process_helper_v2':('confirm_twice','wait','signaled_exit_times','seal_closed_log'),
 'b1_contract':('request_from_completed','check_candidate_artifacts','execute_reference','admit_reference'),
 'completed_binder':('validate_completion','bind_completed'),
 'corrected_contract':('exited','predecessors'),
 'dac_stage_stdlib_entry':('main',),
}.items():
    blocks.extend(function_block(key,name) for name in names)
block_record=save('SOURCE_BLOCKS.json',{'scope':'Read-only source extraction; no imported/executed function', 'blocks':blocks})
pin_assignments=[n for n in trees['worker_v1'].body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINS' for t in n.targets)]
pins_source=ast.get_source_segment(raws['worker_v1'].decode('utf-8-sig'),pin_assignments[0])
camp=json.loads(raws['camp_prepared']);dac=json.loads(raws['dac_prepared'])
report={
 'schema':'b1-next-minimal-native-lifecycle-source-analysis.v1',
 'created_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'AI read-only source analysis and concrete next source-only integration design; not independent review of future implementation and not source/execution adoption',
 'source_bindings':records,
 'source_blocks':block_record,
 'old_worker_PINS_exact_source':pins_source,
 'observed_prepared_metadata':{method:{'python':p['python'],'runtime_prefix':p['runtime']['prefix'],'runtime_executable':p['runtime']['executable'],'runtime_python':p['runtime']['python'],'settings':p['settings']} for method,p in [('CAMP',camp),('DAC',dac)]},
 'current_pyvenv_configuration_scope':'Only current configuration bytes read. home/executable are candidate expectations, not actual live kernel image/command/process ownership. Historical command string is not an execution command.',
 'minimum_complete_source_unit':[
   'New lifecycle_v1/controller.py with full dormant single-slot orchestration and first-statement unconditional science/execution guard; no edits to accepted existing sources.',
   'New worker_v2/reference_worker.py preserving all existing original-reference body and original package calls. Add stdlib ready/ACK/bootstrap validation strictly before _load_sources_after_admission; preserve closed CLI/private/import/load/run/admit execution guards.',
   'New lifecycle_v1/evidence_contract.py that verifies exact bounded source/bootstrap/raw-request/identity/ACK/actual-exit/log/artifact linkage without importing science. It must expose only consistency inspection until a reviewed issuer and result-admission authority are integrated.',
 ],
 'native_topology':[
   'External stdlib parent launches the registered venv python -B new worker directly. Popen.pid may be a Windows venv redirector; actual worker os.getpid is a candidate from its ready file and must be separately retained before ACK.',
   'Do not copy explicit ordinary-Python launcher/child fixture topology as proof of native venv topology. Captured native launcher and interpreter may be distinct. The report does not assert what a future live native process tree will be.',
   'Predeclare both executable identity bindings: registered venv executable for launcher and independently reviewed base executable for actual interpreter. Bind pyvenv.cfg and any allowed complete command transformation in a new source/runtime authority. Prepared sys.executable/prefix alone cannot prove kernel image.',
   'Expected actual complete command must derive from a predeclared native launch contract, not the worker ready self-report. Exact observed full command and kernel image must be checked twice on live retained identities. If unexpected topology/command/short-lived child prevents this, preserve refusal/partial attempt; do not infer identity or exit from absence.',
   'The scientific worker should preserve original native -B/site-enabled environment; fixture -I -S -B is ordinary-CPU-only. Native -S/site bootstrap compatibility has not been implemented or validated here, and must not be used to silently replace registered runtime semantics.',
 ],
 'ack_before_science_state_machine':[
   'Controller first guard remains unconditionally closed until separately reviewed preceding authority, source/adoption plan, current boot, actual completion/exits, fresh resource/release, shared-byte lock and future slot issuer are complete.',
   'Future parent captures immutable canonical B1 raw request plus LF, bootstrap bytes and exact source/image/command/native-path descriptor in a brand-new lifecycle attempt. Presence of any attempt rejects replay. Bootstrap lifecycle path is separate from fresh worker-v2/runs/run_id control path and original evaluation/b1_reference_runs/run_id native path.',
   'After release/lock/resource and request rechecks, parent opens stdout/stderr with CreateNew, declares exact argv/environment, launches native worker and immediately retains the Popen launcher identity; failure to capture remains a preserved incident.',
   'Worker starts with only stdlib modules: read/verify bootstrap descriptor and supplied exact B1 raw request descriptor, verify no scientific imports, open self limited evidence identity, CreateNew ready including actual PID/creation and bootstrap/raw request SHA; then wait for parent ACK before any original module import, binder call, checkpoint/image access, CUDA or encode_seed.',
   'Parent treats ready as candidate only, independently opens actual interpreter limited+SYNCHRONIZE handle; verifies launcher external-parent and interpreter launcher/direct-parent branch only under predeclared native topology with exact image/full command/100ns creation twice. Parent retains both through actual exit.',
   'Immediately before ACK, a future final-admission hook must recheck captured sources/plan/raw request/release TTL/current boot/preceding authority/actual retained live lock owner and strict resource gate. Hook is an explicit missing issuer, not a caller boolean or JSON path.',
   'CreateNew/flush ACK binds raw B1 request SHA, bootstrap SHA, exact admitted slot method/seed, controller retained identity, launcher retained identity, actual interpreter retained identity and final admission record. Worker verifies exact raw-byte descriptors, self identity, live parent identity and all captured source/admission bytes unchanged before entering copied original body.',
   'Original body rebinds CompletedInputs and reconstructs canonical B1 request exactly; derives only in-memory batch16->1 after verifying original seal; copies historical payload_sha256 without pretending valid derivative seal; retains CAMP395/DAC402/strictloader/transform/FP16->FP32/DAC snapshot behavior; creates original four outputs and only candidate/return intent.',
 ],
 'actual_exit_and_closed_stream_boundary':[
   'Use v2 HeldProcess.wait on separately retained launcher/interpreter handles, not Popen.wait alone. Actual signaled DWORD and same handle PID/creation/positive exit FILETIME must be saved separately for both; only expected real zero exits can publish successful scientific reference execution evidence.',
   'Do not call snapshot/kernel_identity/image after signaled exit; inherit live image record and validate PID/time on retained handle as v2 does. Do not fresh reopen numeric PID after exit. An uncaptured short-lived child remains unknown.',
   'Close all own redirected streams after both real held exits; seal_closed_log read-sharing with both designated exit_observations then binds actual stdout/stderr byte sizes/SHA. Keep failures/partial native/attempt unchanged; no retry, kill, cleanup deletion or rollback.',
   'After closed streams, external parent rereads worker return intent, candidates and four artifacts, checks exact actual raw request and source/candidate association and rereads all immutable controls; worker hashes/return_intent cannot stand in for parent process evidence.',
   'A parent may report actual exits of children it held. Its own return intent cannot prove its independent exit; if downstream authority requires parent/controller exit, a separate already-admitted outer observer must retain this parent and close its streams before sealing the final aggregate. Do not circularly demand future child/parent exits before authorizing their initial launch.',
 ],
 'minimum_evidence_contract':[
   'Never accept arbitrary caller arrays, filenames, class instances, self-certified booleans or candidate consistency as independent B1 execution.',
   'A future allowed root must bind the new producer source/adoption, fixed native topology and approved plan; one slot bootstrap/raw request, predeclared unique run paths, source bindings and final admission bytes; exactly the two externally held identities/exits and every designated closed stdout/stderr; worker original artifacts and immutable candidate/return intent.',
   'Verifier reads exact canonical bytes with duplicate-key rejection, bounded sizes and unchanged before/after physical file identity. Resolve paths under allowed fresh roots, reject duplicate/path escape/same-content different physical file aliases, check unmodified sources/raw request and exact method/seed/order/selected query content. Revalidate candidate four artifact consistency only after external closed-process boundary.',
   'CreateNew+fsync/read-sharing is cooperative publication; it does not prove arbitrary-writer atomicity, historical malicious-writer exclusion or cryptographic trust. A copied JSON describing held handles cannot itself prove an external parent ran. Actual execution root adoption joins observed parent API records and native source/runtime proof.',
   'Reference result admission is bounded to deduplicated first query per ten frozen tasks. Expose no descriptor to ranking unless a separately reviewed complete evidence gate and execution adoption are satisfied. Full-gallery fresh encoding/order/parity and full-dataset online CLIP remain later independent duties.',
 ],
 'preceding_admission_gaps':[
   'Original pipeline stage7 T6 is incomplete; extension, author re-evaluation and independent training/evaluation layers have not completed. Neither the current observations nor the ordinary CPU control change that.',
   'CompletedInputs currently requires actual per-method completed evaluation status with all three seeds/30 tasks and verifies existing completed artifacts. Request construction cannot manufacture future completion manifests/checkpoints or be called as if these inputs already exist.',
   'Primary own independent exit code remains unknown. An upstream authority must preserve this limitation and adjudicate the real applicable release contract without rerunning completed science to manufacture exit evidence. No new B1 component may convert absence into exit0.',
   'corrected_driver_v3.contract.exited returns true for no live PID at lines134-147. Its predecessor helper therefore cannot be imported as a new actual-held-exit issuer. This is a source semantic distinction, not a newly observed scientific failure.',
   'Current boot/resource/release/shared-byte-lock authority has not issued a B1 science execution grant. Parent reported fresh GPU26rows/exclusivefalse this round; no new observer or resource measurement was performed by this analysis agent. Existing ordinary Visio still blocks COM independently, not a B1 scientific gate waiver.',
 ],
 'unchanged_scientific_scope':[
   'Old v1 worker, B1 contract execute_reference/admit_reference/measure_task_ranking and old ranking_bridge.measure_task_ranking remain unconditionally closed. No invocation of private primitives is allowed.',
   'No real model, encode_seed, binder, request_from_completed against actual completed inputs, weights/NPZ/cache/image/large ZIP, GPU, COM, release/intent, lock or queue/state writer was invoked. No old CPU fixture or accepted suite was replayed.',
   'This publication is a source-analysis design only: no new runnable scientific executor adoption, native runtime validation, source release, scientific measurement, fresh gallery, ranking parity, full dataset accuracy, T6 completion or manuscript result.',
 ],
 'flags':{'scientific_execution':False,'source_adopted':False,'runnable_native_validated':False,'release_or_intent_created':False,'real_lock_touched':False,'old_source_modified':False,'old_suite_or_fixture_replayed':False,'B1_admitted':False,'full_T6_complete':False},
}
record=save('INTEGRATION_SCOPE.json',report)
markdown='''# 下一最小 B1 原生集成源码范围

本报告只是本轮独立 AI 只读源码分析，不是未来新源审查/采用或科学执行许可。完整源块、当前小文件绑定、原 worker PINS、建议状态机及缺口见 INTEGRATION_SCOPE.json 与 SOURCE_BLOCKS.json。

可实际编写的最小完整单元是新 lifecycle/controller.py + evidence_contract.py 和新 worker_v2/reference_worker.py。它必须包含真实单 slot 的 dormant Popen/连续 held双身份/ACK/实际双退出/闭流/结果关联，而不是只有 false 字段的空运行器。所有 spawn、原包导入、科学 body 与 CLI 的第一句仍无条件拒绝；缺失前序/currentboot-resource-release-lock issuer 时不得执行。旧 v1 和原公共拒绝门保持。

原 Windows venv 需要从实际 native launch 捕获 launcher与 interpreter。prepared 固定的是 venv sys.executable/prefix；pyvenv.cfg 只有配置候选，不能当 kernel image 或完整命令证据。普通 Python 显式二角色 CPU fixture 并未验证 native redirector。新 parent应直接启动原 venv -B 新 stdlib worker；从 ready实际 PID独立开 interpreter handle，并以先声明且绑定的两个 image/full-command与父creation身份双核，ACK才允许原模块导入及encode_seed。未知分支保留拒绝，禁止由自报值反填expected。

ACK/lifecycle路径须在 parent全新 attempt下；它与新 worker_v2/runs/<run_id> control及原 evaluation/b1_reference_runs/<run_id> native目录分开。这样ready不提前创建原body要求不存在的control/native目录。原body保留CompletedInputs、canonical request+LF、batch16到1唯一内存派生、CAMP395/DAC402/严格loader/原transform/FP16到FP32/DAC scope和四原产物。

外部parent必须分别观察连续 held launcher/interpreter的实际DWORD/PID/100ns creation/exit FILETIME，双真实0退出后关闭本方stdout/stderr，再read-sharing封字节。Parent只证明它持有的child退出；own return intent不证明自身退出，若后继合同要求自身exit须另有外层held观察者。证据门先核外部边界及所有字节再返回原查询子集reference的一致性，不能据caller数组/path/class/self-report开ranking。fresh完整gallery/排名parity/原图全rank计时/full online CLIP仍在后续范围。

原stage7 T6及后继科学未完成、当前GPU非空、前序primary独立exit未知、原CAMP/DAC三seed30任务completed binder输入缺席；这些都不能由本次普通CPU证明补齐。corrected_driver_v3.exited无live PID返回true，不可拿它直接作为新held独立exit issuer。CreateNew/fsync/read-sharing是合作约束，并非任意writer原子或历史恶意writer排除保证。
'''
with (HERE/'SCOPE.md').open('xb') as stream:
    stream.write(markdown.encode('utf-8'));stream.flush();os.fsync(stream.fileno())
md_record=bind(HERE/'SCOPE.md')[0]
delivery=save('DELIVERY.json',{'schema':'b1-integration-source-analysis-delivery.v1','created_utc':datetime.now(timezone.utc).isoformat(),'scope':'Read-only source analysis only; not future-source review/adoption or native execution','report':record,'source_blocks':block_record,'notes':md_record,'analysis_source':bind(__file__)[0],'old_sources_unchanged':[records[k] for k in records],'no_science_or_fixture_or_com_or_lock_or_release_or_state':True})
print(json.dumps({'report':record,'source_blocks':block_record,'delivery':delivery},ensure_ascii=False))
