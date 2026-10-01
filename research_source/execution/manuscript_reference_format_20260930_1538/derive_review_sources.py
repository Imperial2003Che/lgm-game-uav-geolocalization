"""Create narrowly derived main renderer and this turn's read-only observation seal."""
from pathlib import Path
import hashlib, difflib, os, json

HERE = Path(__file__).resolve().parent
EX = HERE.parent

def create(path, raw):
    with path.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def derive(parent, target, expected_sha, replacements, patch):
    old = parent.read_bytes()
    assert hashlib.sha256(old).hexdigest() == expected_sha
    new = old
    for before, after in replacements:
        assert new.count(before) == 1, before
        new = new.replace(before, after)
    diff = ''.join(difflib.unified_diff(old.decode('utf-8').splitlines(True),
        new.decode('utf-8').splitlines(True), fromfile=str(parent), tofile=str(target)))
    return {'parent': {'path':str(parent), 'bytes':len(old), 'sha256': expected_sha},
        'derived': create(target, new), 'full_diff': create(patch, diff.encode('utf-8'))}

renderer = derive(EX/'manuscript_compile_20260930_0202/render_and_inspect_pdf.py',
    HERE/'render_main_only.py', '4da093ef783da6e6f9f1ed5bfc1d05c51f76a18a9217c26b8eba9bf52cbe23a2',
    [(b"for name in ('main', 'supplementary'):", b"for name in ('main',):")], HERE/'RENDER_SOURCE.patch')
obsdir = EX/'continuation_observation_20260930_153427732'
observation = derive(EX/'heartbeat_observation_20260930_134136303/seal_observation.py',
    obsdir/'seal_observation.py', '9629449678d734a80c36672071d62f6beda4292d444c820cb424ea758bfbf8a7',
    [(b'observation_20260930_134137737', b'observation_20260930_153454158'),
     (b'heartbeat_observation_20260930_1219/', b'heartbeat_observation_20260930_134136303/'),
     (b"stopped['gpu_process_rows']==25", b"stopped['gpu_process_rows']==26"),
     (b"'gpu_rows':25", b"'gpu_rows':26")], HERE/'OBSERVATION_SEAL_SOURCE.patch')
print(json.dumps(create(HERE/'REVIEW_SOURCE_DERIVATIONS.json',
    (json.dumps({'renderer':renderer, 'observation_seal':observation}, ensure_ascii=False, indent=2)+'\n').encode('utf-8')), ensure_ascii=False))
