from pathlib import Path
import datetime, hashlib, json, tomllib
HERE=Path(__file__).parent
def binding(p):
    data=Path(p).read_bytes()
    return dict(path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
before=tomllib.loads((HERE/'AUTOMATION_BEFORE.toml').read_text(encoding='utf-8'))
actual_path=Path(r'C:\Users\17703\.codex\automations\automation\automation.toml')
after=tomllib.loads(actual_path.read_text(encoding='utf-8'))
append=(HERE/'AUTOMATION_APPEND.txt').read_text(encoding='utf-8')
expected=before['prompt']+append
assert expected.endswith('\n') and not expected.endswith('\n\n')
assert after['prompt']==expected[:-1]  # App removed exactly one terminal LF.
assert all(after.get(k)==v for k,v in before.items() if k not in {'prompt','updated_at'})
assert not (set(after)-set(before))
assert after['status']=='ACTIVE'
changed=[k for k in set(before)|set(after) if before.get(k)!=after.get(k)]
report={'schema':'heartbeat-automation-update-verification.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'automation_id':after['id'],'prompt_exactly_expected_after_one_terminal_LF_removed':True,'normalization':'App omitted exactly the final LF; all preceding characters preserved','old_prompt_entire_prefix_preserved':True,
 'old_prompt_chars':len(before['prompt']),'new_prompt_chars':len(after['prompt']),'changed_fields':sorted(changed),
 'other_fields_preserved':True,'status':after['status'],'rrule':after['rrule'],
 'before':binding(HERE/'AUTOMATION_BEFORE.toml'),'actual':binding(actual_path),'append':binding(HERE/'AUTOMATION_APPEND.txt'),'source':binding(__file__)}
target=HERE/'AUTOMATION_UPDATE_VERIFICATION.json'
with target.open('x',encoding='utf-8',newline='\n') as f: f.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
stamp=datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
proof=binding(target)
line=(f'\n\n### 自动跟进同步 — {stamp}\n\n已用automation_update更新原automation并回读TOML，prompt除app移除最后一个LF外逐字一致{len(after["prompt"])}字符；原{len(before["prompt"])}字符完整前缀保持，仅prompt/updated_at变化，ACTIVE、每小时频率、名称、目标thread及其余字段不变。EX/heartbeat_observation_20260930_040510057/AUTOMATION_UPDATE_VERIFICATION.json SHA{proof["sha256"]}。首次verifier在精确prompt比较处exit1，未写receipt或HANDOFF；根查明仅末尾LF归一化，新v2单次核验，原source和完整diff保留。本次仅再次重启观察/当前boot源码合同及13条基础引用局部研究；没有新科学运行、图件、论文或Overleaf交付。重启实质变化通知一次，其后同一未满足准入静默；自动跟进保留。\n').encode('utf-8')
handoff=HERE.parent/'HANDOFF.md'; old=handoff.read_bytes()
with handoff.open('ab') as f: f.write(line)
assert handoff.read_bytes()==old+line
print(json.dumps({'verification':proof,'handoff':binding(handoff),'changed_fields':changed},ensure_ascii=False))
