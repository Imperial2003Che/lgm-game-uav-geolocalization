"""Append a quiet, unchanged observation without modifying prior task evidence."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import sys

HERE = Path(__file__).resolve().parent
EX = HERE.parent

def binding(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def write_new(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with path.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    return binding(path)

review_path = Path(sys.argv[1]).resolve(strict=True)
assert review_path.parent == HERE / 'independent_review'
review = binding(review_path)
assert review['sha256'] == '91cb251d593283884d33ed10b4bf6bb56e694d4671801f298593bf424610da60'
review_value = json.loads(review_path.read_bytes())
assert review_value['disposition']['new_objection'] is False
assert review_value['disposition']['new_user_action_needed'] is False
seal = json.loads((HERE / 'ROOT_OBSERVATION_SEAL.json').read_bytes())
assert seal['boot_unchanged_since_previous_turn'] is True
assert seal['same_complete_current_visio_and_parent_observations'] is True
assert seal['gpu_exit_code'] == 0 and seal['gpu_rows'] == 23 and seal['gpu_gate_satisfied'] is False
assert seal['execution_released'] is False and seal['cleanup_authorized'] is False
assert len(seal['attempts_absent_at_seal']) == 4
now = datetime.now().astimezone().isoformat()
root = binding(HERE / 'ROOT_OBSERVATION_SEAL.json')
obs = seal['observation']
stop = seal['stopped_observation']
text = f'''

## 2026-09-30 同一未满足准入的安静复核 — {now}

本轮先读HANDOFF最新引用稿交付记录及相应scope/addendum和当前0405源码采用限制，再实际只读观察。EX/heartbeat_observation_20260930_0609/OBSERVATION_WRAPPER_INCLUDED.json {obs['bytes']}B/SHA{obs['sha256']}；广CIM实际05:08:44.7224786Z及05:08:45.3052332Z。stopped observation_20260930_060845355/OBSERVATION.json {stop['bytes']}B/{stop['sha256']}，实际06:08:45.6367458+01，GPUquery退出0且23行，原exclusive门false；T6output不存在。目录0609只是本轮标识，实际观察时间以上述记录为准。

boot仍2026-09-30T02:56:27.5000000Z/ticks639263337875000000。两广扫描仍仅普通VISIO.EXE29480，parent13076，creationticks639263338233256210；完整Office16引号路径后空格，无Automation/Invisible。当前parent-number观察仍explorer.exe13076/ticks639263338065379830/命令C:\\Windows\\Explorer.EXE；完整字段与上一0509观察相同，无科学命令匹配。该普通Visio不属本任务已证明所有权，不附加/退出/清理。无科学匹配和历史PID缺席不补退出码，primary独立exit仍未知。

ROOT_OBSERVATION_SEAL.json {root['bytes']}B/{root['sha256']} 首次exit0，只对本轮保存观察和小文件核查。16state/log、5原heartbeat及carrier b0/creationticks均不变；三个T6目录Sep29_1548/Sep30_0104/Sep30_0405的runtime_attempt和Visio候选runtime_attempt_v1全无。根sealer只改前轮两条观察路径，SEALER_PRIOR_SOURCE.py.txt和完整SEALER_PATH_ONLY.patch保留，无旧suite扩测。原broad仍针对Sep29历史boot合同的false，不是0405当前合同失败；根明确核0405 boot匹配。未测本轮available_commit，不宣称26GiB门已满足；GPU非空已经禁止release及启动等待。

独立AI保存观察复核 {review['path']} {review['bytes']}B/SHA{review['sha256']}；根读完整报告/来源和说明后引用。独立说明中的“非任务所有应用”只按未证明本任务所有理解，不能反向证明该实例实际归属。独立小文件/字段复核不是另一轮CIM/GPU捕获；没有独立持有进程句柄/退出证明。当前snapshot不是未来许可，所有三次准入/两次15秒/六锁/native子进程/15min release/实际launcher-interpreter退出闭流及后继串行门保持。

本轮没有新科学、源码采用、图件、论文、Overleaf或投稿交付，没有release/intent/native科学probe/COM/cleanup/锁/state动作。没有重新编译既有稿、重跑科学或控制suite、读取/重hash大ZIP/权重/NPZ/cache/image。未把观察或先前B1闭门源码当真实效率执行。最新17+6引用修订工作稿、70PPTSVG/2mainVisio、全部已采用结果及60.47GB完整包保持；T6/LOHO24fit192task/真实解释图/剩余Visio/后继作者与独立baseline/额外DAC/完整效率/最终正文排版/最终Overleaf和投稿建议尚待完成。全部负结果、证据缺边、冻结参数和资源限制继承。

同一不可执行状态无新用户处理事项，本轮DONT_NOTIFY。既有每小时自动跟进保留；本轮没有改自动prompt，后续仍先读HANDOFF实际最新记录，全部真实交付后才删除跟进。
'''
addition = text.encode('utf-8')
handoff = EX / 'HANDOFF.md'
before = handoff.read_bytes()
before_record = binding(handoff)
with handoff.open('r+b') as f:
    current = f.read()
    assert current == before, 'HANDOFF changed before append'
    f.seek(0, 2)
    f.write(addition)
    f.flush()
    os.fsync(f.fileno())
after = handoff.read_bytes()
assert after == before + addition
receipt = {
    'schema': 'quiet-heartbeat-handoff-append.v1', 'time': now,
    'source': binding(__file__), 'root_observation': root,
    'independent_saved_observation_review': review,
    'before': before_record, 'after': binding(handoff),
    'append_bytes': len(addition), 'append_sha256': hashlib.sha256(addition).hexdigest(),
    'original_prefix_preserved': True,
    'decision': 'DONT_NOTIFY', 'automation_preserved': True,
    'automation_prompt_modified': False, 'execution_released': False,
    'new_scientific_result': False,
}
print(json.dumps(write_new(HERE / 'HANDOFF_APPEND_RECEIPT.json', receipt), ensure_ascii=False))
