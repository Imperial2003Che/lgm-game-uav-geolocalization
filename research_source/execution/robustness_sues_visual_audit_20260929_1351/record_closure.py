import datetime, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
B1 = EX / 'external_efficiency_preparation/newer_native_b1_contract_v1'

def binding(p, expected=None):
    data = p.read_bytes()
    rec = {'path': str(p), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    if expected: assert rec['sha256'] == expected
    return rec

def write(p, text):
    with p.open('x', encoding='utf-8', newline='\n') as f: f.write(text)

root = json.loads((B1 / 'ROOT_SOURCE_ADOPTION.json').read_text(encoding='utf-8'))
rb = binding(B1 / 'ROOT_SOURCE_ADOPTION.json', 'dbe6e141cd6510daa7043273314bc9e155080d65f41c7367ed1e3b5a9e8dd3dc')
src = binding(B1 / 'adopt_b1_source.py')
snap_path = EX / 'robustness_observation_20260929_0647/snapshot_20260929_140746513/OBSERVATION.json'
sb = binding(snap_path, 'cb5c4691b59f450b3cbd80fe4d421646be30438b719feb9ba97c6ba270a5ed1c')
snap = json.loads(snap_path.read_text(encoding='utf-8-sig'))
runtime = f'''最新实际只读观察{snap['time']}：robustness_observation_20260929_0647/snapshot_20260929_140746513/OBSERVATION.json SHA{sb['sha256']}，两次CIM核12身份UTC整数ticks/完整命令/parentage，CONTRACT SHA{snap['contract_report']['sha256']}。四owner/launcher pipeline14420/29784、extensions30388/7584、latest33520/12896、independent7484/21652与Sep29原身份一致；四heartbeat UTC13:07:22–38新鲜，后三waiting4/2/3pending，四stderr0、三计划/stateIOv2SHA保持。pipeline14420仍9组已恢复Win5retry/4770bytes，其他三无retry；历史8992八组另批，不能称无retry。
当前SUES Full seed1 launcher37764 parent40780 Creation13:11:46.3561290+01 UTCticks639262807063561290；interpreter14260 parent37764 Creation13:11:46.3659250+01 ticks639262807063659250。stage24120/40780原ticks639262571000923660/639262571001196180不变。14:05:20日志进入contrast severity4 factor0.35；stderr325bytes仅原slowprocessor warning。baseline/cuda/workers8/evalbatch128/chunk128/AMP/corruptionseed20260727/match-cache/clean-audit64/localfilesonly不改。ledger3completed/1running只是runtime；SUES Full未验收。commit38.14759445GiB仅运行快照，26GiB仅新启动准入。下一轮必须先重核worker/phase，旧snapshot不是未来当前状态。'''
b1 = f'''新增效率来源准备 external_efficiency_preparation/newer_native_b1_contract_v1：b1_contract.py SHA3947b52f48335adba748e797d79a89950006f28d073c362c8ded25258f0de486，SOURCE_MANIFEST35d7290f2f2f3189390bd45eddf2d6c4ac7378e313b14c9507de2536b997c1a4、PREPARATION_REPORT8ef5ce01a47199a6e8671f0df1c209c67d7c59e5ba18e06581e32d58e3893b07、完整diff47f148c162b871a7ecc8f25a6fe433b22819606e1f298f59571265c0f090cf85。实现原CAMP/DAC encode_seed来源/AST绑定、精确CompletedInputs未来请求构建、唯一内存batch16→1差异与候选NPY/load/runtime一致性检查；每10task首query子集不是fresh完整图库。原prepared字节不改，派生对象复制的原seal不是派生有效seal。request_from_completed未对真实未来completed输入执行，候选一致性不是独立执行证明。
23项新stdlib合成控制通过；binder/path-alias pin添加后第二次确实重复全部23项，非最小受影响subset、不新增coverage，后续不要再重跑。首版source为事后精确重构并以初报告SHA验证，非当时pre-edit快照。独立efficiency_native_b1_independent_review_20260929/INDEPENDENT_STATIC_REVIEW.json SHA67c096d077b21b67d6e6c1cbe44ebcbb719aff751828ec7b1d4124d58375c77e仅静态无阻塞，未执行候选/控制。根完整最终source/checker/README/sealer及binder增量读审，以四原文件精确重建完整diff，实际31小文件绑定后在{root['time']}采用ROOT_SOURCE_ADOPTION.json SHA{rb['sha256']}，根adopt_b1_source.py SHA{src['sha256']}，首次exit0。仅source preparation，未登记/release/队列修改、未GPU/科学库/权重/计时。execute_reference/admit_reference/measure_task_ranking及旧ranking public门继续无条件拒绝。独立原B1实际worker、六freshworker、外部parent分别捕获launcher/interpreter退出与闭流、完整freshgallery/parity、前序/resource/release/共享锁及全onlineaccuracy仍未实现，不能称T6完成或绕过公开门验收。'''
record = '\n\n## ' + datetime.datetime.now().astimezone().isoformat() + ' — B1来源准备有限采用与例行运行观察\n\n' + b1 + '\n\n' + runtime + '\n'
write(HERE / 'HANDOFF_B1_CLOSURE.md', record)
with (EX / 'HANDOFF.md').open('a', encoding='utf-8', newline='\n') as f: f.write(record)

old = (EX / 'robustness_pair_results_20260929/AUTOMATION_PROMPT_1303.txt').read_text(encoding='utf-8')
intro = old[:old.index('\n\n最新根实际采用')]
sues = (HERE / 'HANDOFF_SUES_VISUAL_ADOPTION.md').read_text(encoding='utf-8')
sues = sues[sues.index('实际根采用 '):sues.index('13:59:40.2069785+01')].strip()
history = '历史University Full采用ROOT_FULL1_ADOPTION.json SHAea8c3065092db79c67005b6b6aa1b54a5433ba39ae4b143504f09618f98fd1f5，与Visual根81ec5d80b7370ae5dc79c3f12e0633b88ade73be3422ec155ea11def68713cc6联合继承；具体Full训练authority/manifest及审核见HANDOFF12:59段，不重读旧附件。\n'
history += old[old.index('Full64诊断file'):old.index('旧Full40820/')].strip()
tail = old[old.index('University seed1两run的逐任务描述统计'):]
start = tail.index('最新实查2026-09-29T13:02:57.6619707+01:00')
end = tail.index('两张原主结果图完整原生SVG替代版本')
tail = tail[:start] + runtime + '\n\n' + tail[end:]
point = tail.index('仍需B1独立执行/证据门')
tail = tail[:point] + b1 + '\n' + tail[point:]
prompt = intro + '\n\n最新已采用结果（截至2026-09-29 13:59 Europe/London +01）：\n' + sues + '\n\n' + history + '\n\n' + tail
assert '累计鲁棒性2/4run' not in prompt and '两SUES仍未验收' not in prompt
assert '累计鲁棒性3/4run' in prompt and '无条件拒绝' in prompt
write(HERE / 'AUTOMATION_PROMPT_1410.txt', prompt)
records = {'time': datetime.datetime.now().astimezone().isoformat(), 'source': binding(Path(__file__)), 'b1_root': rb, 'snapshot': sb, 'handoff_addendum': binding(HERE / 'HANDOFF_B1_CLOSURE.md'), 'prompt': binding(HERE / 'AUTOMATION_PROMPT_1410.txt'), 'automation_update_still_required': True}
write(HERE / 'CLOSURE_PREPARED.json', json.dumps(records, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'prompt': records['prompt'], 'chars': len(prompt), 'closure': binding(HERE / 'CLOSURE_PREPARED.json')}, ensure_ascii=False))
