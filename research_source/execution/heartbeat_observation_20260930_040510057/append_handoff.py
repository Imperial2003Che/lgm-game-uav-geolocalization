"""Append this completed turn's record; preserve the entire previous HANDOFF."""
from pathlib import Path
import datetime, hashlib, json, tomllib
HERE=Path(__file__).parent
EX=HERE.parent
def bind(p):
    p=Path(p); assert p.stat().st_size<500000
    data=p.read_bytes()
    return dict(path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
def save(p,data):
    with Path(p).open('xb') as f: f.write(data)
def encoded(x): return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
pins={
 HERE/'ROOT_BOOT_OBSERVATION_ADOPTION.json':'c28fee27fa4036b199caa50daeee7813723e21c1edf7e854322d4e911c040b59',
 EX/'t6_recovery_preparation_20260930_0405/ROOT_SOURCE_ADOPTION.json':'bd39f17134c264f6637d578cb5521a780db011e8bc820e9d9e3436c182476f3e',
 EX/'heartbeat_boot_review_20260930_0405/DELIVERY.json':'3fad7aba88be19b03e3225e38a5a17384c84a533e7fc2a3d37847270dda80e03',
 EX/'heartbeat_boot_review_20260930_0405/PRODUCER_DELIVERY_ADDENDUM.json':'78666a9e7fe3e4e25ad3121a53f9a020b858b5526a6967f23d639cf1560e8b5c',
 EX/'citation_foundations_review_20260930_0405/ROOT_CITATION_RESEARCH_ADOPTION.json':'bc8ea2a0aaea0bc017afff9ece06cf444ee131be2013ab8012fa28cb9067fdc9',
 EX/'citation_foundations_scope_review_20260930_0405/SCOPE_REVIEW.json':'ec08b761d59c1e76b4755eea743c9f1a3e32074ac70b1d40c317f53324223258',
}
records=[]
for p,h in pins.items():
    b=bind(p); assert b['sha256']==h
    records.append(b)
late=json.loads((EX/'heartbeat_boot_review_20260930_0405/DELIVERY.json').read_text(encoding='utf-8'))
for b in late['artifacts']:
    assert bind(b['path'])==b
    records.append(b)
obs=json.loads((HERE/'OBSERVATION_WRAPPER_INCLUDED.json').read_text(encoding='utf-8'))
for b in obs['files']: assert bind(b['path'])==b
assert Path(obs['carrier']['path']).read_bytes()==b'0'
for name in ('t6_recovery_preparation_20260929_1548','t6_recovery_preparation_20260930_0104','t6_recovery_preparation_20260930_0405'):
    assert not (EX/name/'runtime_attempt').exists()
assert not (EX.parent/'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1').exists()
path=EX/'HANDOFF.md'; before=path.read_bytes()
assert hashlib.sha256(before).hexdigest()=='1505622bcd203a57b3fe39713380c81c1d69e8d24300eba7097c3f3a9dfdda91'
assert not (HERE/'HANDOFF_APPEND_RECEIPT.json').exists()
stamp=datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
addition=('\n\n本轮记录封存时间：'+stamp+'\n').encode('utf-8')+(HERE/'HANDOFF_APPEND.md').read_bytes()
with path.open('ab') as f: f.write(addition); f.flush()
after=path.read_bytes()
assert after==before+addition
automation=Path(r'C:\Users\17703\.codex\automations\automation\automation.toml')
auto_bytes=automation.read_bytes()
save(HERE/'AUTOMATION_BEFORE.toml',auto_bytes)
config=tomllib.loads(auto_bytes.decode('utf-8'))
assert config['id']=='automation' and config['status']=='ACTIVE'
receipt={
 'schema':'heartbeat-handoff-append-receipt.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'prior_handoff':dict(path=str(path),bytes=len(before),sha256=hashlib.sha256(before).hexdigest()),
 'new_handoff':bind(path),'old_prefix_preserved':True,'append':bind(HERE/'HANDOFF_APPEND.md'),
 'bindings':records,'source':bind(__file__),'sixteen_state_logs_unchanged':True,'three_t6_attempts_and_visio_attempt_absent':True,
 'automation_before':bind(HERE/'AUTOMATION_BEFORE.toml'),'automation_update_yet_performed':False,
 'scope':'New reboot observation, separately adopted T6 source contract and partial foundation citation research only. No science, COM, cleanup, release, intent, native probe, lock or state mutation. Existing full package and manuscript unchanged.'}
save(HERE/'HANDOFF_APPEND_RECEIPT.json',encoded(receipt))
print(json.dumps({'receipt':bind(HERE/'HANDOFF_APPEND_RECEIPT.json'),'handoff':bind(path),'prompt_chars':len(config['prompt'])},ensure_ascii=False))
