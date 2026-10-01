"""Prepare a human-readable heartbeat update; does not mutate automation settings."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, tomllib

root=Path(__file__).parent
settings=tomllib.loads(Path(r'C:\Users\17703\.codex\automations\automation\automation.toml').read_text(encoding='utf-8'))
old=settings['prompt']
assert settings['id']=='automation' and settings['kind']=='heartbeat' and settings['status']=='ACTIVE'
note=(root/'HANDOFF_ADDITION.md').read_text(encoding='utf-8')
paragraphs=note.split('\n\n')
# Preserve the full previous instructions except the obsolete current-process block.
start=old.index('当前使用execution/robustness_observation')
end=old.index('两张原主结果图',start)
observer=old[start:old.index('最新07:16:',start)]
new_scope='最新根实际采用2026-09-29 10:02:08 Europe/London +01：首个完整鲁棒性University visual seed1已联合独立审核并根采用，1run/30扰动条件/90扰动task+3clean task。其余三run未验收，整个robustness阶段未完成，pipeline整体仍3/7。42fit、官方42run231task、T3 12run66task既有采用不变。\n\n'
new_scope+='\n\n'.join(paragraphs[2:6])+'\n\n'
current='\n\n'.join(paragraphs[6:10])+'\n\n'
new=old[:start]+observer+current+old[end:]
intro_end=new.index('\n\n')+2
new=new[:intro_end]+new_scope+new[intro_end:]
new=new.replace('最新根实际采用2026-09-29 07:06:56','既有根采用2026-09-29 07:06:56',1)
assert 'snapshot_20260929_100131109' in new and 'ROOT_VISUAL1_ADOPTION.json' in new
assert 'Full clean CLIP64' in new and '最新07:16:55' not in new
assert 'corrected_driver_v3' in new and 'https://www.overleaf.com/project/6ab9825d2cb870b10bc95589' in new
for name,text in [('AUTOMATION_PROMPT_BEFORE.txt',old),('AUTOMATION_PROMPT_1002.txt',new)]:
    with (root/name).open('x',encoding='utf-8',newline='') as f:f.write(text)
def bind(p):
    b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
record=dict(created_utc=datetime.now(timezone.utc).isoformat(),source=bind(Path(__file__)),old=bind(root/'AUTOMATION_PROMPT_BEFORE.txt'),new=bind(root/'AUTOMATION_PROMPT_1002.txt'),characters=len(new),preserved_settings={k:v for k,v in settings.items() if k!='prompt'},settings_modified=False)
with (root/'AUTOMATION_PROMPT_PREPARATION.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps(record,ensure_ascii=False))
