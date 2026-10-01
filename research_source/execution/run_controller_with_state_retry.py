"""Transparent state-I/O wrapper for the already registered five controllers."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import sys

HERE=Path(__file__).resolve().parent
PACKAGE=HERE/'state_io_retry_20260920'
sys.path.insert(0,str(PACKAGE))
from resilient_state import wrap
TARGETS={
    'primary':'continue_formal_matrix_path_compat_v1.py',
    'pipeline':'supervise_pipeline.py',
    'extensions':'supervise_extensions_path_compat_v1.py',
    'latest':'supervise_latest_baselines_path_compat_v1.py',
    'independent':'supervise_independent_comparisons_path_compat_v1.py',
}

def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def verify(expected):
    path=PACKAGE/'SOURCE_MANIFEST.json'
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected: raise RuntimeError('State I/O manifest changed')
    for row in json.loads(raw)['files']:
        item=Path(row['path'])
        if item.stat().st_size!=row['bytes'] or sha(item)!=row['sha256']:
            raise RuntimeError('State I/O source changed: '+str(item))
    if path.read_bytes()!=raw: raise RuntimeError('State I/O manifest changed during verification')
    return {'manifest':str(path),'sha256':expected,'actual_controller_entry':str(Path(__file__)),
            'scope':'Only retry original state writer on Windows errors 5/32/33; science and commands unchanged'}

def load(role,expected):
    provenance=verify(expected)
    target=HERE/TARGETS[role]
    provenance.update(role=role,original_controller=str(target))
    spec=importlib.util.spec_from_file_location('registered_'+role+'_with_state_retry',target)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    def decorate(writer):
        return wrap(writer,diagnostic_path=PACKAGE/('io_retry_'+role+'_'+str(os.getpid())+'.jsonl'),provenance=provenance)
    if role=='extensions':
        original_load=module.load_controller
        def load_extension(expected_extension):
            controller=original_load(expected_extension)
            controller.save=decorate(controller.save)
            return controller
        module.load_controller=load_extension
    else:
        module.save=decorate(module.save)
    if any(name.split('.')[0] in ('numpy','torch','PIL','matplotlib') for name in sys.modules):
        raise RuntimeError('Controller wrapper imported scientific libraries')
    return module

def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--role',choices=TARGETS,required=True)
    parser.add_argument('--io-manifest-sha256',required=True)
    options,arguments=parser.parse_known_args()
    module=load(options.role,options.io_manifest_sha256)
    sys.argv=[str(HERE/TARGETS[options.role]),*arguments]
    module.main()

if __name__=='__main__': main()
