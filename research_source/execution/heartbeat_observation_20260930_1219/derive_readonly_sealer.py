from pathlib import Path
import hashlib, difflib, os
HERE=Path(__file__).resolve().parent
prior=HERE.parent/'offline_native_delivery_observation_20260930_114212033'/'seal_observation.py'
raw=prior.read_bytes()
if len(raw)!=5325 or hashlib.sha256(raw).hexdigest()!='da782b470c0c0d092e6e223a18fe5a53f45afad6e1ba12fd4c441b21c6e6c1f9':
    raise ValueError('Exact previously read read-only sealer required')
before=raw.decode()
old="prior_path=EX/'heartbeat_observation_20260930_102052846/OBSERVATION_WRAPPER_INCLUDED.json'"
new="prior_path=EX/'offline_native_delivery_observation_20260930_114212033/OBSERVATION_WRAPPER_INCLUDED.json'"
if before.count(old)!=1 or before.count('observation_20260930_114213078/OBSERVATION.json')!=1:
    raise ValueError('Two exact observation path replacements only')
after=before.replace(old,new).replace('observation_20260930_114213078/OBSERVATION.json','observation_20260930_121607895/OBSERVATION.json')
for name, content in [('SEALER_PRIOR_SOURCE.py.txt',raw), ('SEALER_PATH_ONLY.patch',''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='prior-readonly-sealer',tofile='current-readonly-sealer')).encode()), ('seal_observation.py',after.encode())]:
    with (HERE/name).open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
print('Two current saved-observation paths derived; no probe, state, lock or execution release.')
