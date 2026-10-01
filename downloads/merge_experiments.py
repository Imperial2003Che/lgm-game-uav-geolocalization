"""Join downloaded experiment parts in order and verify transport SHA256. No model execution."""
from pathlib import Path
import json, hashlib, os

folder=Path(__file__).resolve().parent
manifest=json.loads((folder/'EXPERIMENTS_MANIFEST.json').read_text(encoding='utf-8'))
destination=folder/manifest['zip_name']
if destination.exists():
    raise SystemExit('Output already exists; choose an empty folder before joining.')
whole=hashlib.sha256()
try:
    with destination.open('xb') as output:
        for part in manifest['parts']:
            source=folder/part['name']
            if source.stat().st_size!=part['bytes']: raise RuntimeError('Wrong size: '+source.name)
            digest=hashlib.sha256(); read=0
            with source.open('rb') as handle:
                while block:=handle.read(8*1024*1024):
                    digest.update(block); whole.update(block); output.write(block); read+=len(block)
            if digest.hexdigest()!=part['sha256']: raise RuntimeError('SHA256 mismatch: '+source.name)
            print('Verified '+source.name,flush=True)
        output.flush(); os.fsync(output.fileno())
    if destination.stat().st_size!=manifest['zip_bytes'] or whole.hexdigest()!=manifest['zip_sha256']:
        raise RuntimeError('Joined ZIP verification failed')
except Exception:
    print('Incomplete output retained; do not extract it.')
    raise
print('Verified ZIP: '+str(destination))
