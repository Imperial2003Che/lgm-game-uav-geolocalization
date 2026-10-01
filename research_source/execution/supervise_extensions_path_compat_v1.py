"""Run the original extension controller with same-file entrypoint spelling."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import sys

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'extension_path_repair_20260920/SOURCE_MANIFEST.json'

def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def verify(expected):
    raw = MANIFEST.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected: raise RuntimeError('Extension path manifest changed')
    for row in json.loads(raw)['files']:
        path = Path(row['path'])
        if path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise RuntimeError('Extension compatibility source changed: '+str(path))
    if MANIFEST.read_bytes() != raw: raise RuntimeError('Manifest changed during verification')

def load_controller(expected):
    verify(expected)
    path = HERE / 'supervise_extensions.py'
    spec = importlib.util.spec_from_file_location('original_extension_controller', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original_entrypoint, original_save = module.entrypoint, module.save
    aliases = []
    def entrypoint(job):
        actual = original_entrypoint(job)
        if str(actual) in job.get('source_sha256', {}): return actual
        found = []
        for registered, fingerprint in job.get('source_sha256', {}).items():
            candidate = Path(registered)
            if candidate.is_file() and os.path.samefile(actual, candidate):
                before = actual.stat()
                if sha(actual) != fingerprint or sha(candidate) != fingerprint:
                    raise RuntimeError('Entrypoint alias source hash mismatch')
                after = actual.stat()
                if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                    raise RuntimeError('Entrypoint changed during alias verification')
                found.append(candidate)
        if len(found) != 1: raise RuntimeError('Expected one same-file registered entrypoint: '+job['id'])
        aliases.append({'job': job['id'], 'registered': str(found[0]), 'resolved': str(actual),
                        'sha256': sha(actual), 'same_file': True})
        return found[0]
    def save(path, data):
        verify(expected)
        if Path(path).name == 'extension_status.json':
            data['execution_path_compatibility'] = {'manifest': str(MANIFEST), 'sha256': expected,
                'original_controller': str(HERE / 'supervise_extensions.py'),
                'actual_controller': str(Path(__file__)), 'aliases': aliases}
        return original_save(path, data)
    module.entrypoint = entrypoint
    module.save = save
    return module

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--manifest-sha256', required=True)
    options, arguments = parser.parse_known_args()
    module = load_controller(options.manifest_sha256)
    sys.argv = [str(HERE / 'supervise_extensions.py'), *arguments]
    module.main()

if __name__ == '__main__': main()
