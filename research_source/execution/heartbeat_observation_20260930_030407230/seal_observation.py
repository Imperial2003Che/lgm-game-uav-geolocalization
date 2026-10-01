"""Bind this heartbeat's two read-only snapshots, without executing any candidate."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
EX = HERE.parent
OUT = EX.parent
BINDS = {}
def desc(p):
    p=Path(p)
    assert p.is_file() and p.stat().st_size < 1_000_000
    b=p.read_bytes()
    d=dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    assert str(p) not in BINDS or BINDS[str(p)]==d
    BINDS[str(p)]=d
    return d
def load(p):
    desc(p)
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(d):
    assert desc(d['path'])=={k:d[k] for k in ('path','bytes','sha256')}

broad=load(HERE/'OBSERVATION_WRAPPER_INCLUDED.json')
stopped_path=EX/'efficiency_incident_20260929_1448/observation_20260930_030407052/OBSERVATION.json'
stopped=load(stopped_path)
assert desc(HERE/'OBSERVATION_WRAPPER_INCLUDED.json')['sha256']=='f7bb33d67d5b27e3f24bd9d9e0e239f85aedf8cfff558d7368187dc3afe04baa'
assert desc(stopped_path)['sha256']=='bd2e71c368a3929a1c993843ae42bb1a7a3586a0db97a5b86dc05dab0d9aba57'
pin(broad['source']);pin(stopped['source']);pin(stopped['gpu_query'])
assert len(broad['files'])==16 and len(stopped['states'])==5
for d in broad['files']:pin(d)
for row in stopped['states']:
    pin(row['source']);pin(row['snapshot'])
    assert row['unchanged_since_incident'] is True
    live=load(row['source']['path'])
    assert live['status']==row['status'] and live['heartbeat_utc']==row['heartbeat_utc']
for phase in ('first','second'):
    snap=broad[phase]
    assert snap['boot_utc_ticks']=='639263179115000000'
    assert len(snap['matches'])==2
    identities={r['name']:r for r in snap['matches']}
    assert set(identities)=={'AppActions.exe','VISIO.EXE'}
    for name,pid,ticks,command in (
      ('AppActions.exe',14420,'639263185295777970','"C:\\Windows\\SystemApps\\MicrosoftWindows.Client.CBS_cw5n1h2txyewy\\AppActions.exe" -Embedding'),
      ('VISIO.EXE',14932,'639263209854724070','"C:\\Program Files\\Microsoft Office\\Root\\Office16\\VISIO.EXE" /Automation /Invisible -Embedding')):
        r=identities[name]
        assert r['pid']==pid and r['parent_pid']==2232 and r['creation_utc_ticks']==ticks and r['command_line']==command
        parent=r['parent_current_observation']
        assert len(parent)==1 and parent[0]['creation_utc_ticks']=='639263179238930240' and parent[0]['command_line'] is None
assert stopped['gpu_query_exit_code']==0 and stopped['gpu_process_rows']==26
assert stopped['original_gpu_exclusive_gate_would_be_satisfied'] is False and stopped['t6_output_exists'] is False
pin(broad['carrier']);assert Path(broad['carrier']['path']).read_bytes()==b'0'
assert broad['carrier']['creation_utc_ticks']=='639262940518466959'
new_t6=EX/'t6_recovery_preparation_20260930_0104'
new_visio=OUT/'transfer_native_visio_candidate_20260930_0104'
t6=load(new_t6/'ROOT_SOURCE_ADOPTION.json');visio=load(new_visio/'ROOT_SOURCE_ADOPTION.json')
pin(t6['source_manifest']);pin(visio['manifest']);pin(visio['candidate'])
contract=load(new_t6/'RECOVERY_CONTRACT.json')
assert str(contract['host_boot_utc_ticks'])==broad['second']['boot_utc_ticks']
assert not t6['execution_released'] and not visio['execution_released'] and not visio['cleanup_authorized']
for p in (new_t6/'runtime_attempt',EX/'t6_recovery_preparation_20260929_1548/runtime_attempt',new_visio/'runtime_attempt_v1'):
    assert not p.exists()
assert not Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal').exists()
desc(__file__)
report=dict(schema='heartbeat-stopped-source-snapshot.v1',utc=datetime.now(timezone.utc).isoformat(),source=desc(__file__),bindings=list(BINDS.values()),state_summary=[dict(status=r['status'],heartbeat_utc=r['heartbeat_utc'],file=r['source']['path']) for r in stopped['states']],current_boot_contract_matches=True,old_contract_mismatch_is_historical=True,gpu_query_rows=26,scientific_owner_matched=False,existing_unconfirmed_visio=True,execution_released=False,cleanup_authorized=False,scientific_execution=False,scope='Current read-only snapshots and small state/log/source pins. Saved process identities are not later admission; no candidate/COM/recovery/science or old control suite executed. New boot contract source adoption remains valid only as source evidence, GPU admission is not satisfied.')
with (HERE/'ROOT_OBSERVATION_SEAL.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(desc(HERE/'ROOT_OBSERVATION_SEAL.json'),ensure_ascii=False))
