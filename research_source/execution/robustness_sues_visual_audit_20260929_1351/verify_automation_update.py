import datetime, hashlib, json, tomllib
from pathlib import Path

here = Path(__file__).resolve().parent
prompt_path = here / 'AUTOMATION_PROMPT_1410.txt'
data = prompt_path.read_bytes()
expected = data.decode('utf-8')
settings = tomllib.loads(Path('C:/Users/17703/.codex/automations/automation/automation.toml').read_text(encoding='utf-8'))
assert settings['prompt'] == expected
assert settings['id'] == 'automation' and settings['kind'] == 'heartbeat'
assert settings['status'] == 'ACTIVE' and settings['rrule'] == 'FREQ=HOURLY;INTERVAL=1'
assert settings['target_thread_id'] == '01a083ef-fe98-7152-92fd-a741f9937364'
assert settings['name'] == '跟进论文实验与图表定稿'
assert settings.get('notification_policy') is None
report = {'time': datetime.datetime.now().astimezone().isoformat(), 'exact_prompt_equal': True,
    'chars': len(expected), 'prompt_path': str(prompt_path), 'prompt_sha256': hashlib.sha256(data).hexdigest(),
    'status': settings['status'], 'kind': settings['kind'], 'rrule': settings['rrule'],
    'target_thread_id': settings['target_thread_id'], 'notification_policy': settings.get('notification_policy'),
    'updated_via_app_tool': True, 'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
p = here / 'AUTOMATION_UPDATE_VERIFIED.json'
with p.open('x', encoding='utf-8', newline='\n') as f:
    json.dump(report, f, ensure_ascii=False, indent=2); f.write('\n')
digest = hashlib.sha256(p.read_bytes()).hexdigest()
with (here.parent / 'HANDOFF.md').open('a', encoding='utf-8', newline='\n') as f:
    f.write('\n\n' + report['time'] + ' 自动跟进经 app tool 更新并逐字符回读验证17631字prompt一致；本目录AUTOMATION_PROMPT_1410.txt SHA' + report['prompt_sha256'] + '；AUTOMATION_UPDATE_VERIFIED.json SHA' + digest + '。保留ACTIVE/hourly/原thread/正常运行静默通知意图，更新SUES Visual3/4采用及当前Full身份、B1仅源准备状态；全部真实实验、终稿图表、Overleaf和投稿建议完成前继续保留。\n')
print(json.dumps({'verified': True, 'report_sha256': digest, 'prompt_sha256': report['prompt_sha256']}, ensure_ascii=False))
