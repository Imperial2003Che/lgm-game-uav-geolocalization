"""Verify the app-managed update by reading TOML; never modify automation TOML."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import tomllib

HERE = Path(__file__).resolve().parent
PATH = Path(r'C:\Users\17703\.codex\automations\automation\automation.toml')

def desc(p):
    p = Path(p)
    b = p.read_bytes()
    return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

before = json.loads((HERE / 'AUTOMATION_BEFORE.json').read_text(encoding='utf-8'))
request = json.loads((HERE / 'AUTOMATION_REQUEST.json').read_text(encoding='utf-8'))
after = tomllib.loads(PATH.read_text(encoding='utf-8-sig'))
assert after['prompt'] == request['prompt']
assert after['prompt'].startswith(before['prompt'])
assert {k:v for k,v in after.items() if k not in ('prompt','updated_at')} == {k:v for k,v in before.items() if k not in ('prompt','updated_at')}
assert after['id'] == 'automation' and after['status'] == 'ACTIVE'
with (HERE / 'AUTOMATION_AFTER.json').open('x',encoding='utf-8',newline='\n') as f:
    f.write(json.dumps(after,ensure_ascii=False,indent=2)+'\n')
report = dict(schema='heartbeat-automation-update-verification.v1', utc=datetime.now(timezone.utc).isoformat(), passed=True, exactPromptMatch=True, priorPromptPrefixPreserved=True, otherFieldsPreserved=True, changedFields=[k for k in after if before.get(k) != after[k]], promptCharacters=len(after['prompt']), status=after['status'], inputs=[desc(HERE/n) for n in ('AUTOMATION_BEFORE.json','AUTOMATION_REQUEST.json','AUTOMATION_AFTER.json','AUTOMATION_APPEND.txt')], source=desc(__file__))
target = HERE / 'AUTOMATION_UPDATE_VERIFICATION.json'
with target.open('x',encoding='utf-8',newline='\n') as f:
    f.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
sealed = desc(target)
handoff = HERE.parent / 'HANDOFF.md'
old = handoff.read_bytes()
receipt = json.loads((HERE/'HANDOFF_APPEND_RECEIPT.json').read_text(encoding='utf-8'))
assert desc(handoff) == receipt['after']
text = '\n\n### 自动跟进同步 — ' + datetime.now().astimezone().isoformat() + '\n\n已用automation_update更新原automation；TOML回读prompt与实际提交逐字一致（'+str(report['promptCharacters'])+'字符），原prompt完整前缀保留。仅prompt/updated_at变化；ACTIVE、原每小时频率、名称、target_thread_id及其余字段保持。heartbeat_observation_20260930_0102/AUTOMATION_UPDATE_VERIFICATION.json SHA'+sealed['sha256']+'。仅追加本轮新boot合同与T3 Visio源码采用和实际只读状态，不是执行release/清理/图件交付，不删除跟进。\n'
with handoff.open('ab') as f:
    f.write(text.encode('utf-8'))
assert handoff.read_bytes() == old + text.encode('utf-8')
with (HERE/'AUTOMATION_HANDOFF_RECEIPT.json').open('x',encoding='utf-8',newline='\n') as f:
    f.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),before=receipt['after'],after=desc(handoff),verification=sealed,prefixPreserved=True),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(sealed,ensure_ascii=False))
