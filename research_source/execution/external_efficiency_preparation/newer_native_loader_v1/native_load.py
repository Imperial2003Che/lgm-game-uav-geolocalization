"""Real future strict native loading. No scientific imports at module scope."""
from contextlib import nullcontext
from dataclasses import dataclass
import importlib
import importlib.util
import inspect
import os
from pathlib import Path
import subprocess
import sys
import source_bindings as b

b.require(Path(b.__file__).resolve()==Path(__file__).with_name('source_bindings.py').resolve(),
          'Foreign source-binding module')
_MODEL_ATTEMPTED=False

def import_file(name,path):
    path=Path(path).resolve()
    b.require(name not in sys.modules,'Unexpected existing private module: '+name)
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

def require_compute_idle(stdout):
    rows=[line.strip() for line in stdout.splitlines() if line.strip()]
    # Before the first CUDA import this worker must not already own a context.
    b.require(not rows,'CUDA compute owner exists or NVIDIA ownership is unavailable')

def verify_native_settings(prepared):
    settings=prepared['settings']
    expected={'image_size':384,'descriptor_dim':1024,'amp':True,'flip_tta':False,'batch_size':16,
              'workers':0,'ranking_chunk_size':64,'device':'cuda:0'}
    b.require(all(type(settings.get(k)) is type(v) and settings[k]==v for k,v in expected.items()),
              'Frozen native evaluation settings differ')
    b.require(Path(sys.executable).resolve()==Path(prepared['python']).resolve(),
              'Use the actual registered native interpreter')
    b.require(Path(sys.prefix).resolve()==Path(prepared['runtime']['prefix']).resolve(),
              'Native environment prefix differs')
    for key,value in settings['thread_environment'].items():
        b.require(os.environ.get(key)==value,'Native launch environment differs: '+key)

@dataclass
class LoadedSlot:
    method:str
    seed:int
    inputs:object
    operations:object
    original_package:object
    original_loader:object
    no_network:object
    provenance:dict

def load_native_slot(inputs,seed):
    """Caller has already admitted this exact slot; it retains the GPU lock.

    No output/checkpoint is saved by this function. It repeats actual completed
    binding checks, uses the original strict loader, then constructs operations.
    Each slot needs a fresh process, including subsequent seeds of one method.
    """
    global _MODEL_ATTEMPTED
    b.require(not _MODEL_ATTEMPTED,'A native slot has already been attempted in this process')
    b.require(isinstance(inputs,b.CompletedInputs),'Use actual validated completed inputs')
    b.require(type(seed) is int and seed in (1,2,3),'Unknown registered seed')
    b.no_scientific_modules();inputs.unchanged()
    confirmed=b.bind_completed(inputs.method,inputs.binding.path,inputs.binding.artifact()['sha256'],
                               inputs.completion.path,inputs.completion.artifact()['sha256'])
    b.require(confirmed==inputs,'Completed input binding changed')
    prepared=inputs.prepared.value();verify_native_settings(prepared)
    package=b.open_original_package(inputs.method)
    helper=package.protocol.helpers()
    runtime_metadata=helper.runtime_snapshot(sys.executable)
    b.require(runtime_metadata==prepared['runtime'],'Installed native environment changed')
    compute=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],
        capture_output=True,text=True,encoding='utf-8',errors='strict',timeout=30,check=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    require_compute_idle(compute.stdout)
    _MODEL_ATTEMPTED=True
    os.environ['CUDA_VISIBLE_DEVICES']='0'
    # All imports below occur only in a future released worker with real inputs.
    import numpy as np
    import torch
    import torch.nn.functional as F
    import torchvision
    import cv2
    import timm
    import albumentations
    from PIL import Image
    site=(Path(sys.prefix)/'Lib/site-packages').resolve()
    modules=(np,torch,F,torchvision,cv2,timm,albumentations,Image)
    module_files={}
    for module in modules:
        path=Path(module.__file__).resolve()
        b.require(path.is_relative_to(site),'Foreign scientific package resolved: '+module.__name__)
        module_files[module.__name__]=str(path)
    b.require(not torch.cuda.is_initialized(),'CUDA was initialized before native setup')
    b.require(not torch.is_inference_mode_enabled() and not torch.is_autocast_enabled('cuda')
              and not torch.is_autocast_enabled('cpu'),'Inherited inference/AMP context')
    torch.set_num_threads(1);cv2.setNumThreads(1)
    loader=importlib.import_module(b.REGISTRY[inputs.method]['loader'])
    b.require(Path(loader.__file__).resolve()==package.directory/(b.REGISTRY[inputs.method]['loader']+'.py'),
              'Foreign strict loader resolved')
    selected=inputs.seed_binding(seed)
    scope=package.snapshots.snapshot_scope() if package.snapshots is not None else nullcontext()
    with scope:
        model,proof,no_network=loader.load_complete_final_model(selected)
        b.require(proof.get('strict') is True and proof.get('assign') is True
                  and proof.get('final_checkpoint_sha256')==selected['checkpoints']['weights_end.pth']['sha256'],
                  'Strict original checkpoint load proof differs')
        b.require(len(model.state_dict())==b.REGISTRY[inputs.method]['state_count'],'Wrong complete native state count')
        if inputs.method=='CAMP':
            b.require(isinstance(model.model_1.pos_scale,torch.nn.Parameter) and model.model_1.pos_scale.requires_grad,
                      'Independent CAMP learned pos_scale must be preserved')
        factory_name='_'+inputs.method.lower()+'_independent_full_original_model_factory'
        factory=sys.modules[factory_name]
        b.require(Path(factory.__file__).resolve()==Path(package.protocol.MODEL_FACTORY).resolve(),'Wrong model factory')
        source_root=Path(factory.SOURCE_ROOT).resolve()
        class_path=Path(inspect.getfile(type(model))).resolve()
        b.require(class_path.is_relative_to(source_root),'Native class outside frozen official source')
        loaded_sources={}
        for name,module in tuple(sys.modules.items()):
            if name=='sample4geo' or name.startswith('sample4geo.'):
                path=getattr(module,'__file__',None)
                if path:
                    path=Path(path).resolve();b.require(path.is_relative_to(source_root),'Cross-method model namespace contamination')
                    loaded_sources[name]={'path':str(path),'sha256':b.sha(path)}
        model=model.to('cuda:0').eval();transform=helper.make_validation_transform()
        torch.backends.cudnn.benchmark=True;torch.backends.cudnn.deterministic=False
        device=torch.device('cuda:0')
        b.require(torch.cuda.current_device()==0 and all(p.device==device and p.dtype==torch.float32 for p in model.parameters()),
                  'Native model dtype/device differs')
        for item in selected['checkpoints'].values():package.protocol.verify_artifact(item)
        b.require(package.protocol.source_evidence()==prepared['sources'],'Scientific source changed during strict loading')
        if package.snapshots is not None:package.snapshots.unchanged_inputs()
    operations_module=import_file('_newer_native_fixed_operations',b.OPS/'native_ops.py')
    operations_module.verify_source_recipe(inputs.method)
    components=import_file('_newer_native_fixed_measurements',operations_module.COMPONENT_PATH)
    runtime=components.Runtime(torch,np,None,None,device)
    operations=operations_module.Operations(inputs.method,runtime,cv2,F,model,transform,components)
    inputs.unchanged()
    provenance={'method':inputs.method,'seed':seed,'runtime_metadata':runtime_metadata,
        'source_artifact_path_aliases':package.alias_guard.latest_aliases,
        'library_files':module_files,'strict_complete_final_load':proof,
        'actual_model_class':type(model).__module__+'.'+type(model).__name__,
        'actual_model_source':{'path':str(class_path),'sha256':b.sha(class_path)},
        'actual_model_sources':loaded_sources,'actual_model_object_id':id(model),
        'checkpoint':selected['checkpoints']['weights_end.pth'],
        'original_transform_helper':{'path':str(Path(helper.__file__).resolve()),'sha256':b.sha(helper.__file__)},
        'runtime_flags':components.runtime_flags(runtime),'torch_threads':torch.get_num_threads(),'opencv_threads':cv2.getNumThreads(),
        'model_load_outside_timing':True,'full_gallery_recomputed_here':False,
        'parent_admission_and_exit_proof_still_required':True,'full_t6_complete':False,'manuscript_result':False}
    # Remove labels belonging to the primary method, retaining actual flags.
    provenance['runtime_flags'].pop('native_formal_autocast',None)
    provenance['runtime_flags'].pop('native_clip_autocast',None)
    return LoadedSlot(inputs.method,seed,inputs,operations,package,loader,no_network,provenance)
