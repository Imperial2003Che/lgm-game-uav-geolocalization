"""Bind the fully read editorial consolidation before mutable inputs change."""
from pathlib import Path
import datetime,hashlib,json
W=Path(__file__).absolute().parent
def bind(p):
    p=Path(p); b=p.read_bytes()
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
m=W/'MANIFEST.json'
assert bind(m)['sha256']=='309deeeba1350e033d4358a27473e842f65a772749bb3c6532ba4a44e915cffe'
j=json.loads(m.read_bytes())
pins=j['outputs']+j['source_bindings']+[j['sealing_source']]
for pin in pins:
    assert bind(pin['path'])==pin,pin['path']
base=(W/'PROMPT_BASE.txt').read_text(encoding='utf-8')
assert base.count('有效整数commit counters≥26GiB')==1
report={'schema':'root-heartbeat-editorial-consolidation-adoption.v1','time':datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
 'accepted_for_final_editorial_update':True,'automation_applied':False,
 'review':'Root completely read the final base, coverage, manifest and sealing source; these consolidate historical repetitions without changing authorization, gates, scientific scope or evidence limits.',
 'clarification_for_final_derived_prompt':{'before':'有效整数commit counters≥26GiB','after':'有效整数 available_commit_bytes=commit_limit_bytes−committed_bytes≥26GiB','authority':'Pinned pipeline_recovery_candidate.py memory gate; available commit is the startup threshold. Sealed base remains unchanged.'},
 'pending':'Append only actually root-adopted T5 delivery and latest real observations, use automation_update, preserve schedule and notification behavior, then exact readback.',
 'bindings':[bind(m)]+pins+[bind(__file__)], 'no_science_native_recovery_release_state_lock_change':True}
p=W/'ROOT_CONSOLIDATION_ADOPTION.json'
with p.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'report':bind(p),'bound_files':len(report['bindings'])},ensure_ascii=False))
