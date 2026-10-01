"""Bind completed CAMP/DAC evaluations in an isolated, standard-library context.

This is not an admission/launch controller. A future caller must first establish
actual predecessor exits and the exact release, resources and exclusive GPU lock.
"""
from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

EXECUTION=Path(__file__).resolve().parents[2]
OPS=EXECUTION/'external_efficiency_preparation/newer_native_ops_v1'
OPS_MANIFEST_SHA='c1c6bab09912c26779917fc0875824fd1e26203cfc2ba55a4d77940e8b51af8d'
REGISTRY={
    'CAMP':{'directory':'camp_independent_evaluation_v3','manifest_sha256':'6212c4b317b0a7d097a65ce9946eaa0de357d042e15c16c0a7afe0a458ef32ee',
            'prepared':'preparations/frozen_three_seed_final_v3/manifest.json','prepared_sha256':'305c2b9b56fb6bde1781f459467a6718b9f7ed1df9779bcc7d4a209ca2244317',
            'loader':'camp_independent_model','state_count':395},
    'DAC':{'directory':'dac_independent_evaluation_v2','manifest_sha256':'adb5521285ca50cb21db0c235c1a476c634643b44489ffb7692b500623a8cfe0',
           'prepared':'preparations/fixed_three_seed/manifest.json','prepared_sha256':'9923839dbc3c2504588fed791ef0489047d30c585f3efefd40dfc3da07da64ca',
           'loader':'dac_independent_model','state_count':402},
}
_PACKAGE=None

def require(condition,message):
    if not condition:raise RuntimeError(message)

def exact_seeds(values):
    return isinstance(values,list) and all(type(v) is int for v in values) and values==[1,2,3]

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def parse(raw):
    return json.loads(raw,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON '+x)))

@dataclass(frozen=True)
class FrozenJson:
    path:Path
    raw:bytes
    @classmethod
    def read(cls,path,expected_sha256):
        require(isinstance(expected_sha256,str) and re.fullmatch('[0-9a-f]{64}',expected_sha256) is not None,
                'Actual expected SHA256 is required; no future/default hash')
        path=Path(path).resolve(strict=True);before=path.stat();raw=path.read_bytes();after=path.stat()
        require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns) and len(raw)==after.st_size,
                'JSON changed during first read')
        require(hashlib.sha256(raw).hexdigest()==expected_sha256,'Unexpected initial JSON bytes')
        parse(raw)
        return cls(path,raw)
    def value(self):return parse(self.raw)
    def artifact(self):return {'path':str(self.path),'bytes':len(self.raw),'sha256':hashlib.sha256(self.raw).hexdigest()}
    def unchanged(self):require(self.path.read_bytes()==self.raw,'JSON changed since first read')

def verify_manifest(path,expected):
    snap=FrozenJson.read(path,expected);value=snap.value();seen=set()
    for item in value['files']:
        target=Path(item['path'])
        if not target.is_absolute():target=snap.path.parent/target
        target=target.resolve(strict=True)
        require(target not in seen,'Duplicate frozen source');seen.add(target)
        require(target.stat().st_size==item['bytes'] and sha(target)==item['sha256'],'Frozen source changed: '+str(target))
    snap.unchanged()
    return {'manifest':snap.artifact(),'verified_file_count':len(seen)}

def source_contract(method):
    require(method in REGISTRY,'Unknown native method')
    row=REGISTRY[method];directory=EXECUTION/row['directory']
    return {'evaluation':verify_manifest(directory/'PREPARATION_MANIFEST.json',row['manifest_sha256']),
            'operations':verify_manifest(OPS/'SOURCE_MANIFEST.json',OPS_MANIFEST_SHA),
            'prepared':FrozenJson.read(directory/row['prepared'],row['prepared_sha256'])}

def no_scientific_modules():
    prefixes={'torch','torchvision','numpy','cv2','PIL','timm','albumentations'}
    require(not [name for name in sys.modules if name.split('.')[0] in prefixes],
            'A fresh worker without scientific imports is required')

def open_original_package(method):
    global _PACKAGE
    if _PACKAGE is not None:
        require(_PACKAGE.method==method,'CAMP and DAC require separate processes')
        return _PACKAGE
    source_contract(method);no_scientific_modules()
    reserved=('protocol','run_evaluation','contract_snapshots','complete_state_checks','camp_independent_model','dac_independent_model','sample4geo')
    require(not any(name.split('.')[0] in reserved for name in sys.modules),'Conflicting original package namespace')
    row=REGISTRY[method];directory=(EXECUTION/row['directory']).resolve()
    # Reserve even on import failure; do not retry another method in this process.
    _PACKAGE=SimpleNamespace(method=method,failed=True)
    sys.path.insert(0,str(directory))
    protocol=importlib.import_module('protocol')
    evaluator=importlib.import_module('run_evaluation')
    for module,filename in ((protocol,'protocol.py'),(evaluator,'run_evaluation.py')):
        require(Path(module.__file__).resolve()==directory/filename,'Wrong original module resolved')
    snapshots=importlib.import_module('contract_snapshots') if method=='DAC' else None
    if snapshots is not None:require(Path(snapshots.__file__).resolve()==directory/'contract_snapshots.py','Wrong input snapshot module')
    no_scientific_modules()
    _PACKAGE=SimpleNamespace(method=method,directory=directory,protocol=protocol,evaluator=evaluator,snapshots=snapshots,failed=False)
    return _PACKAGE

@dataclass(frozen=True)
class CompletedInputs:
    method:str
    prepared:FrozenJson
    binding:FrozenJson
    completion:FrozenJson
    def unchanged(self):
        for item in (self.prepared,self.binding,self.completion):item.unchanged()
    def seed_binding(self,seed):
        require(type(seed) is int and seed in (1,2,3),'Only registered seeds 1/2/3')
        matches=[row for row in self.binding.value()['seeds'] if row['seed']==seed]
        require(len(matches)==1,'Seed is missing or duplicated')
        return matches[0]

def validate_completion(package,inputs,bound):
    p=package.protocol;completed=inputs.completion.value();p.verify_seal(completed)
    require(completed.get('status')=='completed' and type(completed.get('task_count')) is int
            and completed['task_count']==30 and exact_seeds(completed.get('seeds')),
            'All 30 actual evaluations are required')
    require(completed.get('prepared')==inputs.prepared.artifact() and completed.get('binding')==inputs.binding.artifact(),
            'Completion belongs to different prepared/bound bytes')
    artifacts={};root=inputs.completion.path.parent
    for key,item in completed['artifacts'].items():
        normalized=key.replace('\\','/')
        require(normalized not in artifacts,'Duplicate normalized artifact path')
        artifacts[normalized]=item
    required={'metrics_all_30.json','three_seed_summary.json','metrics_all_30.csv'}
    for seed in (1,2,3):required.update({f'seed_{seed}/metrics.json',f'seed_{seed}/descriptors.npy',f'seed_{seed}/strict_complete_final_load.json'})
    require(required.issubset(artifacts),'Incomplete scientific evaluation artifacts')
    for relative,item in artifacts.items():
        target=(root/relative).resolve()
        require(target.is_relative_to(root) and target==Path(item['path']).resolve(),'Completion artifact escaped or changed identity')
        p.verify_artifact(item)
    score_item=artifacts['metrics_all_30.json']
    score_snap=FrozenJson.read(score_item['path'],score_item['sha256']);metrics=score_snap.value()
    require(set(metrics)=={'1','2','3'},'Wrong completed metric seed set')
    prepared=inputs.prepared.value()
    task_item=prepared['membership']['tasks'];tasks=FrozenJson.read(task_item['path'],task_item['sha256'])
    task_names={row['name'] for row in tasks.value()};require(len(task_names)==10,'Expected ten original complete-gallery tasks')
    for seed in bound['seeds']:
        rows=metrics[str(seed['seed'])];require(set(rows)==task_names,'Wrong completed task set')
        for task,row in rows.items():
            require(row['method']==inputs.method and type(row['seed']) is int and row['seed']==seed['seed'] and row['checkpoint_sha256']==seed['checkpoints']['weights_end.pth']['sha256'],
                    'Method, seed or checkpoint of original scores differs')
    score_snap.unchanged();tasks.unchanged();inputs.unchanged()

def bind_completed(method,binding_path,binding_sha256,completion_path,completion_sha256):
    """No output is written and no future checkpoint/hash is manufactured."""
    original=source_contract(method)
    inputs=CompletedInputs(method,original['prepared'],FrozenJson.read(binding_path,binding_sha256),
                           FrozenJson.read(completion_path,completion_sha256))
    package=open_original_package(method)
    require(not package.failed,'Original package import failed')
    scope=package.snapshots.snapshot_scope() if package.snapshots is not None else nullcontext()
    with scope:
        if package.snapshots is not None:
            for snap in (inputs.prepared,inputs.binding,inputs.completion):
                require(package.snapshots.input_snapshot(snap.path).raw==snap.raw,'Different first-read control bytes')
        prepared=package.evaluator.read_prepared(inputs.prepared.path)
        bound=package.evaluator.verify_bound(prepared,inputs.binding.path)
        require(prepared==inputs.prepared.value() and bound==inputs.binding.value(),'Returned values differ from first-read JSON')
        require(prepared['method']==method and exact_seeds(prepared['seeds']) and exact_seeds([r['seed'] for r in bound['seeds']]),
                'Expected original method and three ordered seeds')
        validate_completion(package,inputs,bound)
        if package.snapshots is not None:package.snapshots.unchanged_inputs()
    require(source_contract(method)==original,'Original source contract changed')
    inputs.unchanged()
    return inputs
