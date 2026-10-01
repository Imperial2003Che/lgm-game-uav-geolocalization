"""Read-only analysis of retained logs and source; standard library only."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
OLD = EXECUTION / 'memory_recovery_20260914_1424'
FAILURE = EXECUTION / 'camp_observer_repair_20260914' / 'main_failure_1544'
CORE = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\lgm_game_pytorch\formal_retrieval.py')
TORCH = Path(r'C:\项目\.venvs\lgm-baselines\Lib\site-packages\torch')

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

old_bytes = (OLD / 'run' / 'process_stderr.log').read_bytes()
new_bytes = (FAILURE / '13_process_stderr.log').read_bytes()
assert new_bytes.startswith(old_bytes), 'Retained stderr must have the exact old prefix'
suffix = new_bytes[len(old_bytes):]
assert b'worker process 4' in suffix and b'<torch_42888_1931977535_316>' in suffix
assert b'worker process 0' not in suffix
suffix_path = HERE / 'INDEPENDENT_NEW_STDERR_ONLY.log'
if suffix_path.exists():
    assert suffix_path.read_bytes() == suffix
else:
    suffix_path.write_bytes(suffix)

prior = read(OLD / 'system_before_recovery.json')
current = read(HERE / 'system_before_recovery.json')
samples = read(OLD / 'memory_recovery_observation.json')['samples']
compact = []
for s in samples:
    workers = [p['ProcessId'] for p in s['python_processes'] if p['ParentProcessId'] == 42416]
    pm = {p['IDProcess']: p for p in s['python_memory']}
    compact.append({
        'time': s['local_time'],
        'committed_bytes': s['memory']['CommittedBytes'],
        'commit_limit': s['memory']['CommitLimit'],
        'available_mbytes': s['memory']['AvailableMBytes'],
        'worker_count': len(workers),
        'worker_pids': workers,
        'trainer_private_bytes': pm[42416]['PrivateBytes'],
        'worker_private_bytes_sum': sum(pm.get(p, {}).get('PrivateBytes', 0) for p in workers),
    })
peak = max(compact, key=lambda s: s['committed_bytes'])
baseline = prior['memory']['CommittedBytes']
delta = peak['committed_bytes'] - baseline
headroom_gate = 26 * 1024 ** 3
limit = current['memory']['CommitLimit']
max_commit = limit - headroom_gate
now_commit = current['memory']['CommittedBytes']
assert delta == 23055872000

files = [
    CORE, TORCH / 'utils/data/dataloader.py', TORCH / 'utils/data/_utils/pin_memory.py',
    TORCH / 'utils/data/_utils/collate.py', TORCH / 'storage.py',
    EXECUTION / 'continue_formal_matrix.py', OLD / 'system_before_recovery.json',
    OLD / 'memory_recovery_observation.json', OLD / 'run/process_stderr.log',
    FAILURE / '13_process_stderr.log', FAILURE / '00_status.json',
    FAILURE / '08_history.json', FAILURE / '09_run_config.json',
    HERE / 'system_before_recovery.json', HERE / 'checkpoint_verification.json',
]
facts = [
    {'id': 'F1', 'finding': 'The 15:44 addition is worker 4 CPU shared-storage mapping 1455, then pin-memory shared-event error 2. The worker 0 / mapping counter 0 traceback is retained from the 14:24 failure, not another new 15:44 event.', 'source': str(EXECUTION / 'continue_formal_matrix.py'), 'lines': [168, 169]},
    {'id': 'F2', 'finding': 'Each epoch replaces the loader with persistent_workers=False and an epoch-derived generator seed; it exhausts the iterator without an early training-loop break.', 'source': str(CORE), 'lines': [2074, 2083, 2087, 2094, 2101]},
    {'id': 'F3', 'finding': 'Installed DataLoader returns a fresh iterator without assigning self._iterator for persistent_workers=False; exhaustion calls _shutdown_workers, joins pin-memory thread and workers, closes queues; atexit retention applies only when persistent_workers and pin_memory are both true.', 'source': str(TORCH / 'utils/data/dataloader.py'), 'lines': [487, 493, 499, 1237, 1508, 1625, 1655, 1669, 1674]},
    {'id': 'F4', 'finding': 'Actual epoch boundary at 15:06 shows workers 8->1->3->7 and commit 63.99->49.57->53.81->60.60 decimal GB. This demonstrates an observed release/recreation cycle, not accumulating old worker generations in that interval.', 'source': str(OLD / 'memory_recovery_observation.json')},
    {'id': 'F5', 'finding': 'Trainer PrivateBytes stays about 7.661 GB during nine full-worker samples; workers total about 14.86-14.95 GB. The shorter sample covers only one epoch boundary, so it cannot disprove slower native allocator/driver growth or external workload changes.', 'source': str(OLD / 'memory_recovery_observation.json')},
    {'id': 'F6', 'finding': 'Loss/history use Python scalars and detached values; sampler cache is replaced per epoch. Resume state remains as one CPU-loaded checkpoint dictionary for the function lifetime; current checkpoint is about 163 MB, a bounded retention, not per-epoch list growth.', 'source': str(CORE), 'lines': [1224, 2054, 2069, 2130, 2174, 2187, 2188]},
    {'id': 'F7', 'finding': 'Default prefetch_factor is 2 for workers>0. Eight workers may have 16 outstanding tasks. Two FP32 image tensors of 64x3x224x224 consume 77,070,336 bytes per batch; 16 nominal batches correspond to 1,233,125,376 bytes, before worker libraries, dataset copies, active batches and transient shared/pinned copies. This arithmetic is not a measured peak.', 'source': str(TORCH / 'utils/data/dataloader.py'), 'lines': [285, 286, 1294, 1551]},
]
report = {
    'schema': 'independent-memory-diagnosis.v1',
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope': 'Source, retained logs, prior/current lightweight CIM snapshots only; no scientific imports, training, process termination, environment changes, or pagefile changes by this reviewer.',
    'conclusion': 'System commit shortage is evidenced; cumulative loader leak is not established. Current non-training baseline remains too high for a justified unchanged retry.',
    'new_stderr': {'old_prefix_bytes': len(old_bytes), 'total_bytes': len(new_bytes), 'new_suffix_bytes': len(suffix), 'suffix_path': str(suffix_path), 'suffix_sha256': sha(suffix_path)},
    'source_facts': facts,
    'retained_sampling': compact,
    'resource_gate_review': {
        'prior_baseline_bytes': baseline,
        'prior_sampled_peak_bytes': peak['committed_bytes'],
        'prior_sampled_peak_time': peak['time'],
        'observed_global_increment_bytes': delta,
        'observed_global_increment_gib': delta / 1024 ** 3,
        'gate_headroom_bytes': headroom_gate,
        'gate_headroom_gib': 26,
        'buffer_above_observed_increment_bytes': headroom_gate - delta,
        'buffer_above_observed_increment_gib': (headroom_gate - delta) / 1024 ** 3,
        'current_snapshot_time': current['time'],
        'current_commit_bytes': now_commit,
        'current_limit_bytes': limit,
        'max_admissible_commit_at_current_limit_bytes': max_commit,
        'required_commit_reduction_bytes': max(0, now_commit - max_commit),
        'gate_currently_passes': limit - now_commit >= headroom_gate,
        'judgment': '26 GiB available commit is a reasonable conservative engineering admission gate: it adds about 4.53 GiB above the sampled global increase. It is not a guaranteed bound, a measured 80-epoch peak, or a cure. Use current measured CommitLimit, never assume pagefile growth.',
    },
    'pre_resume_conditions': [
        'Check exact owner PID+creation time and all descendant workers; all prior experiment processes and the CPU checkpoint-check probe must have exited.',
        'Retain failed state/log/checkpoint/config/environment and hashes; use independently checked complete epoch 35 state, same frozen core, baseline executable, workers8, batch64, 80 total epochs, scheduler/scaler/RNG and immutable config.',
        'Require at least 26 GiB CommitLimit minus CommittedBytes in at least 3 lightweight samples across 30 seconds; recheck immediately before launching, fail closed if counters are missing/invalid or headroom drops. This sampling duration is an engineering recommendation, not a scientific protocol parameter.',
        'Only a real reduction in non-experiment commit, or an explicitly user-authorized resource change, supplies new recovery evidence. Do not close Weixin or other user apps without explicit permission.',
        'Do not reduce workers/batch/prefetch, disable pinning, enable persistent workers, replace Python/Torch, change device/environment or patch frozen scientific code. Persistent workers would also retain stale worker dataset epoch state under this implementation.',
        'Validate all first-four post-failure jobs are wholly unstarted before retiring their status; never erase completed/started job evidence. Fifth v2 has no current status: launch the existing registered v2 plan explicitly without registration replay or trying to retire a nonexistent status.',
        'After launch, collect lightweight commit, trainer/worker private bytes, PID generations and epoch progress; require new complete epoch evidence and inspect several boundaries before calling recovery sustained. Stop auxiliary scientific jobs; no unreviewed periodic kill/resume policy.',
    ],
    'not_demonstrated': ['No direct memory sample at the exact 15:44 failure instant.', 'No proof of long-duration native pinned allocator/driver leak or external-app attribution.', 'No claim that 26 GiB headroom will guarantee all remaining fits/evaluations.', 'No new experiment result.'],
    'source_pins': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files],
}
(HERE / 'INDEPENDENT_DIAGNOSIS.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
md = f'''# 15:44 Windows1455 独立诊断

结论：本次故障有系统提交额度不足的直接错误证据；尚无“逐轮旧 DataLoader/worker 不释放”的证据。16:25 停机基线仍约 42.04 GB，不能把原样再启动当作修复。

## 本次错误与历史错误已分离

控制器 continue_formal_matrix.py 第168行按追加模式写 process_stderr.log。14:24旧备份是 {len(old_bytes)} 字节，15:44备份 {len(new_bytes)} 字节，旧备份逐字节等于新文件前缀。新追加 {len(suffix)} 字节单独保存在 INDEPENDENT_NEW_STDERR_ONLY.log。

新故障是 worker 4 在 default_collate → _new_shared → _new_using_filename_cpu 创建 `<torch_42888_1931977535_316>` 时返回1455。之后 pin-memory 线程出现 event2。文件开头 worker0 / counter0 属于14:24旧错误，不应重复归因于本次。未取得15:44瞬时commit采样，不能补造其数值。

## 生命周期源码和实测

- 冻结 formal_retrieval.py 第2074–2101行每轮新建 DataLoader，persistent_workers=False，worker seed为 seed + 1,000,003 × epoch。
- 本地 torch/utils/data/dataloader.py 第487–500行非persistent路径返回新iterator，不存入loader._iterator；1508–1510行耗尽会调用_shutdown_workers。1651–1676行顺序结束并join pin-memory线程和workers、关闭队列。1237行的atexit保留只在persistent_workers且pin_memory同时为True时启用，本任务不走该路径。
- 真实采样15:06:23有8workers、commit63.99GB；15:06:33只1个新worker、commit49.57GB，随后3→7workers、commit53.81→60.60GB。至少这个完整轮边界确实释放了旧worker资源。
- 9个全worker采样中trainer PrivateBytes约7.661GB，workers合计14.86–14.95GB，没有该区间内单调累积证据。采样只覆盖一个边界，不能排除更慢的原生缓存/驱动增长或其他应用负载变化。
- formal_retrieval.py 第2130–2135行将loss和accuracy变为标量；2174–2187行history只存数值、列表、空validation字典。采样器1224–1227行替换缓存。2054行CPU断点字典保留至函数结束，是一次性、约163MB文件规模的有界持有，不能解释为每轮叠加。
- 默认prefetch_factor=2（DataLoader285–286行），8worker对应最多16个尚未完成的任务。每batch两组FP32 64×3×224×224图像共77,070,336字节，16batch名义图像量1,233,125,376字节；实际还有worker库/数据副本、活跃batch与共享和pinned暂存。这是尺寸推导，不是实测峰值。

## 26 GiB 启动准入门限审查

| 项目 | 字节 | GiB |
|---|---:|---:|
| 14:24保存的停机commit | {baseline:,} | {baseline/1024**3:.3f} |
| 15:04–15:06已采样最大commit | {peak['committed_bytes']:,} | {peak['committed_bytes']/1024**3:.3f} |
| 两者全系统增量 | {delta:,} | {delta/1024**3:.3f} |
| 拟要求可用commit | {headroom_gate:,} | 26.000 |
| 高于已采样增量的缓冲 | {headroom_gate-delta:,} | {(headroom_gate-delta)/1024**3:.3f} |
| 当前commit上限 | {limit:,} | {limit/1024**3:.3f} |
| 此上限下可启动的最大基线commit | {max_commit:,} | {max_commit/1024**3:.3f} |
| 16:25当前停机commit | {now_commit:,} | {now_commit/1024**3:.3f} |
| 当前还需真实降低commit | {max(0,now_commit-max_commit):,} | {max(0,now_commit-max_commit)/1024**3:.3f} |

**支持26GiB作为保守工程准入门限，当前不通过。** 它在已采样21.47GiB全系统增量上再留约4.53GiB；比只看“当前有20多GB空闲”更有依据。增量并非纯训练独占成本，采样峰值也不是80轮或15:44故障峰值，因而门限不保证后续稳定。

建议跨30秒至少3个轻量CIM样本都满足门限，在实际启动前立即复查，任何缺值或额度回落均不启动。使用实测CommitLimit，不假设分页文件还能自动增长。不同后续作业仍需各自资源预检。

## 恢复前条件

1. 完整35轮断点、源哈希、immutable配置、optimizer/scheduler/AMP/RNG和旧错误已核验保存；检查核验探针及旧trainer/worker/监督PID加创建时间均已退出。
2. 等待非实验基线实际降低至门限，再按同解释器、8workers、batch64、80总轮和原随机协议续跑。没有用户明确授权就不关闭微信等应用、不改分页文件。等待时间本身不等于资源已经释放。
3. 前四层只在所有后继作业确为未启动时归档失败状态；第五层v2已登记、无当前status，明确使用existing v2 plan启动，不重登记、不迁移不存在的status。
4. 启动后只做轻量commit/PrivateBytes/worker世代与epoch监测；以新的完整轮和若干跨轮资源曲线验证。无科学依据把缩batch、改workers/prefetch/pinning或persistent_workers称为原配置续跑；本代码worker数据集epoch复制也使随意启用persistent_workers不可接受。
5. 不采用外部定期杀进程后续跑来“清内存”。原core没有受审的完整轮安全退出接口，外部看到manifest后已可能进入下一轮，此类控制需要独立设计/验证且不能冒充现有修复。

本审查仅用文本、标准库和轻量CIM；未导入科学库、未启动或停止实验、未改环境和冻结科学源码。所有精确路径、行号、采样明细与源SHA见同名JSON。
'''
(HERE / 'INDEPENDENT_DIAGNOSIS.md').write_text(md, encoding='utf-8')
print(json.dumps({'status': 'independent_diagnosis_written', 'report': str(HERE / 'INDEPENDENT_DIAGNOSIS.json'), 'new_stderr_prefix_exact': True, 'gate': report['resource_gate_review']}, ensure_ascii=False, indent=2))
