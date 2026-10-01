"""Preparation verifier; execution is intentionally unavailable in this v1."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_preparation():
    path = HERE/'SOURCE_MANIFEST.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if manifest['status'] != 'components_prepared_not_executable_not_registered':
        raise RuntimeError('Unexpected source preparation status')
    for item in manifest['files'] + manifest['frozen_sources']:
        file = Path(item['path'])
        if file.stat().st_size != item['bytes'] or sha(file) != item['sha256']:
            raise RuntimeError('Source preparation changed: '+str(file))
    return {'status':'verified_component_preparation', 'measurement_executed':False,
            'full_t6_complete':False, 'remaining':manifest['not_implemented']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('verify', 'run'))
    args = p.parse_args()
    if args.action == 'run':
        raise SystemExit('Execution unavailable: serial registration/owner gates, real checkpoint/model/CLIP loading, output persistence and full-gallery verification require a separately reviewed driver. No scientific import or benchmark was attempted.')
    print(json.dumps(verify_preparation(), ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
