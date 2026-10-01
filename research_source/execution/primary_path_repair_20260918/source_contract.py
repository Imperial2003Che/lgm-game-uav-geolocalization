"""Source identity for the narrowly scoped primary project-path adapter."""
from pathlib import Path
import hashlib
import json
from project_paths import root_identity, require

HERE = Path(__file__).resolve().parent

def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def verify(expected):
    require(isinstance(expected, str) and len(expected) == 64, 'Exact path adapter manifest SHA is required')
    path = HERE / 'SOURCE_MANIFEST.json'
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, 'Path adapter source manifest changed')
    value = json.loads(raw)
    for row in value['files']:
        target = Path(row['path'])
        require(target.stat().st_size == row['bytes'] and sha(target) == row['sha256'],
                'Path adapter source changed: ' + str(target))
    identity = root_identity()
    require(path.read_bytes() == raw, 'Path adapter manifest changed during verification')
    return {'manifest_path': str(path), 'manifest_sha256': expected, 'root_identity': identity,
            'scope': 'Only project path spelling in original runner/core namespaces; native pathlib unchanged'}
