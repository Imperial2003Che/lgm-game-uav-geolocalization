"""Adopt new read-only boot/PID observations, not a recovery release."""
from pathlib import Path
import datetime, hashlib, json
W=Path(__file__).resolve().parent; X=W.parent; bindings={}
def d(p):
 p=Path(p); assert p.is_file() and p.stat().st_size<1000000
 b=p.read_bytes(); r=dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()); bindings[str(p)]=r; return r
def bound(x):
 r=d(x['path']); assert r['sha256']==x['sha256']
 if 'bytes' in x: assert r['bytes']==x['bytes']
 return r
def j(p): d(p);return json.loads(Path(p).read_bytes())
def walk(o):
 if isinstance(o,dict):
  if all(k in o for k in ('path','sha256')):bound(o)
  for v in o.values():walk(v)
 elif isinstance(o,list):
  for v in o:walk(v)
review=j(X/'host_boot_change_review_20260930_0008/REVIEW.json');walk(review)
obs=j(W/'OBSERVATION_WRAPPER_INCLUDED.json');walk(obs)
assert review['passed_with_stated_scope'] is True
assert obs['contract_boot_matches_current'] is False
assert obs['first']['boot_utc_ticks']==obs['second']['boot_utc_ticks']=='639263179115000000'
assert obs['contract_boot_utc_ticks']=='639262263395000000'
assert obs['runtime_attempt_absent'] and obs['t6_output_absent']
for snap in (obs['first'],obs['second']):
 assert len(snap['matches'])==1
 r=snap['matches'][0]
 assert (r['pid'],r['parent_pid'],r['name'],r['creation_utc_ticks'])==(14420,2232,'AppActions.exe','639263185295777970')
 assert r['command_line']=='"C:\\Windows\\SystemApps\\MicrosoftWindows.Client.CBS_cw5n1h2txyewy\\AppActions.exe" -Embedding'
 assert r['parent_current_observation'][0]['command_line'] is None
assert len(obs['files'])==16
assert Path(obs['carrier']['path']).read_bytes()==b'0'
assert 'run_controller_with_state_retry_v2|' in Path(obs['source']['path']).read_text(encoding='utf8')
source=X/'t6_recovery_preparation_20260929_1548/pipeline_recovery_candidate.py'
assert d(source)['sha256']=='b95ee9ff8c90b9323b89eb3a9228c36e40576b16830eb07dbd78e38cef1f833e'
assert "require(snapshot['host_boot_utc_ticks'] == contract['host_boot_utc_ticks']," in source.read_text(encoding='utf8')
oldroot=X/'t6_recovery_preparation_20260929_1548/ROOT_SOURCE_ADOPTION.json'
assert d(oldroot)['sha256']=='fd093b974627d6ddd6700ffb40c071e2c28deceeb39713fbc8e4cede3dee3fe3'
assert j(oldroot)['execution_released'] is False
d(X/'host_boot_change_review_20260930_0008/review_saved_boot_change.ps1')
report=dict(schema='root-post-stopped-boot-observation-adoption.v1',utc=datetime.datetime.now().astimezone().isoformat(),accepted_with_stated_limits=True,source=d(Path(__file__)),independent_review=d(X/'host_boot_change_review_20260930_0008/REVIEW.json'),wrapper_included_observation=d(W/'OBSERVATION_WRAPPER_INCLUDED.json'),bindings=list(bindings.values()),scope='Read-only host boot change and PID reuse interpretation. No recovery authorization or scientific completion.',new_boot_ticks='639263179115000000',old_contract_boot_ticks='639262263395000000',execution_released=False,scientific_execution=False,limits=['The host boot had already changed in the 23:37 observer. Existing science was stopped before reboot; no new scientific failure or captured exit code is inferred.','Numeric PID14420 now identifies AppActions.exe, not the historical pipeline Python owner. Parent svchost command is unavailable.','The supplemental wrapper-inclusive selector found no scientific or Visio match; not proof about arbitrary command names or unobserved short-lived processes.','Sixteen current state/log files and existing carrier retain recorded bytes. This is not future launch admission.','Existing source adoption remains preserved, but its old boot-bound contract is inapplicable to this boot. A separately reviewed current-boot contract/adoption is required before any future gated release; no old entry replay or source/root overwrite.'])
with (W/'ROOT_BOOT_OBSERVATION_ADOPTION.json').open('x',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(report=d(W/'ROOT_BOOT_OBSERVATION_ADOPTION.json'),bindings=len(report['bindings']))))
