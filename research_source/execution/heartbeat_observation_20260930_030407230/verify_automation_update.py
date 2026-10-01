"""Verify the app update against exact saved request and retain old settings."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json, tomllib
HERE = Path(__file__).resolve().parent
E = HERE.parent
path = Path('C:/Users/17703/.codex/automations/automation/automation.toml')
before = json.loads((HERE / 'AUTOMATION_BEFORE.json').read_bytes())
request = json.loads((HERE / 'AUTOMATION_REQUEST.json').read_bytes())
actual = tomllib.loads(path.read_text(encoding='utf-8'))
assert actual['prompt'] == request['prompt']
assert actual['prompt'].startswith(before['prompt'])
unchanged = [key for key in before if key not in ('prompt', 'updated_at')]
assert {k: actual[k] for k in unchanged} == {k: before[k] for k in unchanged}
assert set(actual) == set(before)
def pin(p):
    p = Path(p)
    raw = p.read_bytes()
    return dict(path=str(p), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
report = {
    'utc': datetime.now(timezone.utc).isoformat(),
    'verified': True, 'automation_id': actual['id'],
    'exact_request_prompt_matches': True, 'original_prompt_prefix_preserved': True,
    'old_prompt_chars': len(before['prompt']), 'new_prompt_chars': len(actual['prompt']),
    'unchanged_fields': unchanged, 'status': actual['status'], 'rrule': actual['rrule'],
    'before': pin(HERE / 'AUTOMATION_BEFORE.json'), 'request': pin(HERE / 'AUTOMATION_REQUEST.json'),
    'actual_toml': pin(path), 'verification_source': pin(Path(__file__).resolve()),
    'scientific_or_COM_execution': False, 'automation_deleted': False,
}
out = HERE / 'AUTOMATION_UPDATE_VERIFICATION.json'
with out.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
sha = pin(out)['sha256']
now = datetime.now(timezone(timedelta(hours=1))).isoformat()
sync = f'\r\n\r\n### 自动跟进同步 — {now}\r\n\r\n已用automation_update更新原automation并回读TOML。prompt逐字一致40939字符，原38021字符完整前缀保持；仅prompt/updated_at变，ACTIVE、每小时频率、name、target_thread_id及其余字段不变。EX/heartbeat_observation_20260930_030407230/AUTOMATION_UPDATE_VERIFICATION.json SHA{sha}。本轮只闭门B1源码采用、官网要求资料及同一只读状态；不是新执行/图件/终稿或最终投稿建议。无需用户处理，保持静默，不删除跟进。\r\n'
handoff = E / 'HANDOFF.md'
before_append = handoff.read_bytes()
with handoff.open('ab') as stream:
    stream.write(sync.encode('utf-8'))
after_append = handoff.read_bytes()
assert after_append == before_append + sync.encode('utf-8')
print(json.dumps({'verification': pin(out), 'handoff': pin(handoff), 'status': actual['status'], 'prompt_chars': len(actual['prompt'])}, ensure_ascii=True))
