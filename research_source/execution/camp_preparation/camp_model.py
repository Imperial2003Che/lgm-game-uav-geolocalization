"""Load the fixed CAMP evaluation model without pretrained downloads.

Only the process-local factory binding is adapted. Original model source remains
unchanged, and the complete author state dictionary must match strictly.
"""
from contextlib import contextmanager
import importlib
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from unittest.mock import patch

SOURCE_ROOT=Path(__file__).resolve().parents[2]/'literature/official_repos/snapshots/Mabel0403__CAMP__b04a9c856711'
MODEL_CONFIG=dict(views=2,nclasses=701,block=2,triplet_loss=0.3,resnet=False,pos_scale=0.6,
                  if_learn_ECE_weights=True,learn_weight_D_D=0.0,learn_weight_S_S=0.0,
                  learn_weight_D_fine_D_fine=0.5,learn_weight_D_fine_S_fine=1.0,
                  learn_weight_S_fine_S_fine=0.0)

@contextmanager
def no_network():
    def blocked(*args,**kwargs):
        raise RuntimeError('CAMP author-checkpoint evaluation permits no network access')
    with patch.object(socket.socket,'connect',blocked),patch.object(socket.socket,'connect_ex',blocked),patch.object(socket,'create_connection',blocked):
        yield

def build_camp_model(source_root=SOURCE_ROOT,device='cpu',author_checkpoint_schema=True):
    """Build the official model and explicitly reconcile its unused auxiliary key.

    The fixed published author file omits model_1.pos_scale. This scalar only
    modifies the discarded part-feature tensor, never the GAP descriptor. For
    this author-file schema, use the current official default as a plain constant
    rather than inventing a learned checkpoint tensor. Training must retain the
    original parameter and must not use this evaluation-only schema adaptation.
    """
    import torch
    source_root=Path(source_root).resolve()
    sys.dont_write_bytecode=True
    existing=sys.modules.get('sample4geo')
    if existing is not None:
        paths=list(getattr(existing,'__path__',[]))
        if not paths or not all(Path(p).resolve().is_relative_to(source_root) for p in paths):
            raise RuntimeError('Another sample4geo source is already imported')
    sys.path.insert(0,str(source_root))
    with no_network():
        module=importlib.import_module('sample4geo.hand_convnext.model')
        factory=importlib.import_module('sample4geo.hand_convnext.ConvNext.make_model')
        backbone=importlib.import_module('sample4geo.hand_convnext.ConvNext.backbones.model_convnext')
        for item in (module,factory,backbone):
            if not Path(item.__file__).resolve().is_relative_to(source_root):
                raise RuntimeError('CAMP model module resolved outside fixed source')
        original_factory=factory.create_model
        original_torch=backbone.torch
        class ScheduleTorchProxy:
            def __getattr__(self,name):
                return getattr(torch,name)
            def linspace(self,*args,**kwargs):
                # The official drop-path schedule calls .item(); compute these
                # 36 non-parameter constants on CPU during meta construction.
                kwargs['device']='cpu'
                return torch.linspace(*args,**kwargs)
        def checkpoint_only_factory(name,pretrained=True,**kwargs):
            if name!='convnext_base' or kwargs:
                raise RuntimeError('Unexpected official backbone factory request')
            return backbone.ConvNeXt(depths=[3,3,27,3],dims=[128,256,512,1024])
        factory.create_model=checkpoint_only_factory
        if str(device)=='meta':
            backbone.torch=ScheduleTorchProxy()
        try:
            with torch.device(device):
                model=module.make_model(SimpleNamespace(**MODEL_CONFIG))
            model.eval()
        finally:
            factory.create_model=original_factory
            backbone.torch=original_torch
    config=model.get_config()
    if tuple(config['mean'])!=(0.485,0.456,0.406) or tuple(config['std'])!=(0.229,0.224,0.225):
        raise RuntimeError('Official model normalization changed')
    original_keys=model.state_dict()
    if len(original_keys)!=395 or 'model_1.pos_scale' not in original_keys or original_keys['model_1.pos_scale'].shape!=torch.Size([]):
        raise RuntimeError('Original model state schema differs from reviewed 395-key architecture')
    model._author_schema_proof={'original_model_tensor_count':395,'author_checkpoint_tensor_count':394,
        'original_missing_author_key':['model_1.pos_scale'],'descriptor_affected':False,
        'evidence':'Official build_convnext.forward modifies only part_features with pos_scale; predict selects the separate gap_feature via [-2].',
        'adaptation':'Replace only the absent auxiliary parameter with plain constant 0.6 from current official default; not a claimed learned author value.',
        'author_checkpoint_schema_enabled':bool(author_checkpoint_schema)}
    if author_checkpoint_schema:
        del model.model_1.pos_scale
        model.model_1.pos_scale=MODEL_CONFIG['pos_scale']
    return model

def validate_checkpoint_state(model,state):
    """Validate every author tensor key, shape and dtype; no dropped or renamed keys."""
    import torch
    if not isinstance(state,dict) or not state or not all(isinstance(k,str) and isinstance(v,torch.Tensor) for k,v in state.items()):
        raise RuntimeError('Expected the original plain tensor state dictionary')
    expected=model.state_dict()
    missing=sorted(set(expected)-set(state))
    unexpected=sorted(set(state)-set(expected))
    different=[{'key':k,'expected_shape':list(expected[k].shape),'actual_shape':list(state[k].shape),
                'expected_dtype':str(expected[k].dtype),'actual_dtype':str(state[k].dtype)}
               for k in sorted(set(expected)&set(state))
               if expected[k].shape!=state[k].shape or expected[k].dtype!=state[k].dtype]
    if missing or unexpected or different:
        raise RuntimeError(f'Strict author checkpoint mismatch: missing={missing}, unexpected={unexpected}, shape_or_dtype={different}')
    return {'tensor_count':len(state),'total_stored_numel':sum(v.numel() for v in state.values()),
            'missing_keys':missing,'unexpected_keys':unexpected,'shape_or_dtype_mismatches':different,
            'key_normalization':'none','model_config':MODEL_CONFIG,
            'schema_adaptation':model._author_schema_proof,
            'strict_load_scope':'All 394 author tensors match the explicitly adapted inference model; the unadapted current source has 395 tensors.'}

def load_author_model(checkpoint,source_root=SOURCE_ROOT):
    """Called only by evaluate after the external execution gate has passed."""
    import torch
    model=build_camp_model(source_root,'cpu')
    with no_network():
        state=torch.load(checkpoint,map_location='cpu',weights_only=True,mmap=True)
        proof=validate_checkpoint_state(model,state)
        result=model.load_state_dict(state,strict=True,assign=True)
        if result.missing_keys or result.unexpected_keys:
            raise RuntimeError('Strict load unexpectedly returned incompatible keys')
    return model,proof
