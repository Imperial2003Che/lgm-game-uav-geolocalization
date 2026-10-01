"""Read-only automation verification and append-only task handoff evidence."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import tomllib

HERE=Path(__file__).absolute().parent
CONFIG=Path(r'C:\Users\17703\.codex\automations\automation\automation.toml')
def bind(path):
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

config=tomllib.loads(CONFIG.read_text(encoding='utf-8-sig'))
prompt=(HERE/'AUTOMATION_PROMPT_1620.txt').read_text(encoding='utf-8')
assert config['prompt']==prompt
assert config['id']=='automation' and config['kind']=='heartbeat'
assert config['name']=='跟进论文实验与图表定稿'
assert config['status']=='ACTIVE' and config['rrule']=='FREQ=HOURLY;INTERVAL=1'
assert config['target_thread_id']=='01a083ef-fe98-7152-92fd-a741f9937364'
assert config.get('notification_policy') is None and config.get('notificationPolicy') is None
section=(HERE/'LATEST_HANDOFF_1620.md').read_text(encoding='utf-8')
assert (HERE.parent/'HANDOFF.md').read_text(encoding='utf-8-sig').endswith(section)
report={'schema':'heartbeat-prompt-update-verification.v1',
    'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'passed',
    'automation_id':config['id'],'kind':config['kind'],'name':config['name'],
    'active':True,'hourly':True,'thread_preserved':True,'notification_policy_unchanged':True,
    'prompt_exact_disk_match':True,'prompt_characters':len(prompt),
    'config':bind(CONFIG),'prompt':bind(HERE/'AUTOMATION_PROMPT_1620.txt'),
    'latest_handoff_section':bind(HERE/'LATEST_HANDOFF_1620.md'),
    'root_recovery_source_adoption':bind(HERE/'ROOT_SOURCE_ADOPTION.json'),
    'source':bind(Path(__file__).absolute()),
    'scope':'App tool updated automation; this verifier only read configuration and appended evidence to HANDOFF.'}
destination=HERE/'AUTOMATION_UPDATE_VERIFICATION_1620.json'
with destination.open('x',encoding='utf-8',newline='\n') as f:
    json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
record=bind(destination)
with (HERE.parent/'HANDOFF.md').open('a',encoding='utf-8',newline='\n') as f:
    f.write('\n\n自动跟进更新核实 '+report['utc']+'：应用工具更新既有automation，ACTIVE/hourly/原thread/名称及通知偏好保持；磁盘tomllib核prompt全文精确一致（'+str(len(prompt))+'字符）。AUTOMATION_PROMPT_1620.txt SHA '+report['prompt']['sha256']+'；AUTOMATION_UPDATE_VERIFICATION_1620.json SHA '+record['sha256']+'。仅两张主结果PPT新交付通知，未变T6阻塞静默，全部任务未完成故保留自动跟进。\n')
print(json.dumps({'verification':record,'prompt_sha256':report['prompt']['sha256']},ensure_ascii=False))
