from pathlib import Path
import json,hashlib,tomllib,datetime
HERE=Path(__file__).resolve().parent;EX=HERE.parent
def rec(p):
 b=p.read_bytes();return {'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(p.read_bytes())
def save(p,d):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
before=load(HERE/'AUTOMATION_BEFORE.json')
request=load(HERE/'AUTOMATION_UPDATE_REQUEST.json')
after=tomllib.loads(Path(r'C:\Users\17703\.codex\automations\automation\automation.toml').read_text(encoding='utf-8'))
assert after['prompt']==request['prompt'] and after['prompt'].startswith(before['prompt'])
for k,v in before.items():
 if k not in ['prompt','updated_at']:assert after[k]==v,k
assert set(after)==set(before)
hf=EX/'HANDOFF.md'; receipt=load(HERE/'HANDOFF_APPEND_RECEIPT.json');current=hf.read_bytes()
assert rec(hf)==receipt['after']
assert hashlib.sha256(current[:receipt['before']['bytes']]).hexdigest()==receipt['before']['sha256']
assert current[receipt['before']['bytes']:]==Path(receipt['append']['path']).read_bytes()
v={'utc':datetime.datetime.now().astimezone().isoformat(),'source':rec(Path(__file__)),'before':rec(HERE/'AUTOMATION_BEFORE.json'),
'request':rec(HERE/'AUTOMATION_UPDATE_REQUEST.json'),'prompt_exact':True,'old_prompt_preserved_as_prefix':True,
'unchanged_fields':[k for k in before if k not in ['prompt','updated_at']],'new_prompt_chars':len(after['prompt']),
'status':after['status'],'handoff_prefix_bytes_and_append_exact':True,'handoff_receipt':rec(HERE/'HANDOFF_APPEND_RECEIPT.json')}
save(HERE/'AUTOMATION_UPDATE_VERIFICATION.json',v)
note='\n\n### 自动跟进同步 — '+v['utc']+'\n\n原automation以automation_update更新，回读prompt47154字符逐字一致；旧43678字符完整前缀保留，仅prompt/updated_at变化，ACTIVE/每小时/名称/目标thread等不变。AUTOMATION_UPDATE_VERIFICATION.json SHA'+rec(HERE/'AUTOMATION_UPDATE_VERIFICATION.json')['sha256']+'；另核HANDOFF原414934字节SHA及实际追加逐字节一致。本轮新增17+6引用修订工作稿及局部文献研究，无新科学/Visio/Overleaf或最终投稿；全部交付前保留跟进。\n'
with hf.open('ab') as f:f.write(note.encode())
save(HERE/'FINAL_RECEIPT.json',{'utc':v['utc'],'automation_verification':rec(HERE/'AUTOMATION_UPDATE_VERIFICATION.json'),'handoff':rec(hf)})
print(json.dumps({'verification':rec(HERE/'AUTOMATION_UPDATE_VERIFICATION.json'),'final':rec(HERE/'FINAL_RECEIPT.json')},ensure_ascii=False))

