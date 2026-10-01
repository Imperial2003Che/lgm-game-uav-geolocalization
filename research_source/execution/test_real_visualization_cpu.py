"""Small CPU contract/analytic checks. Creates no scientific image or score."""
from pathlib import Path
import ast
import importlib.util
import json
import os
import sys

os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
sys.dont_write_bytecode=True
here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('vis_review',here/'make_real_model_visualizations.py')
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# Check the frozen module signatures without importing torch or running the model.
core_path=v.ROOT/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py'
tree=ast.parse(core_path.read_text(encoding='utf-8'))
functions={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
expected={'encode_records':9,'derive_all_records':3,'build_official_evaluation_tasks':3,
          'load_torch_checkpoint':2,'validate_checkpoint_evidence_schema':2,'inventory_hash':2,
          'build_transforms':2,'protocol_membership_hash':1}
for name,count in expected.items():
    assert len(functions[name].args.args)==count,(name,count)

import numpy as np
import torch
import torch.nn.functional as F
torch.set_num_threads(1)
assert not torch.cuda.is_initialized()

# Grad-CAM analytic oracle: channel mean -> L2 normalization -> cosine target.
# This toy 2x2 tensor exists only to verify the gradient formula, never for figures.
class Toy(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.visual_backbone=torch.nn.Module()
        self.visual_backbone.layer4=torch.nn.Identity()
    def encode_image(self,image,content,style):
        a=self.visual_backbone.layer4(image)
        return F.normalize(a.mean(dim=(2,3)),dim=-1)

model=Toy()
x=torch.tensor([[[[1.,2.],[3.,4.]],[[4.,1.],[1.,2.]]]],requires_grad=True)
y=torch.tensor([[[[5.,5.],[5.,5.]],[[1.,1.],[1.,1.]]]])
dummy=torch.zeros(1,1)
cam,score=v.compute_gradcam(model,(x,dummy,dummy),(y,dummy,dummy))
mean=x.detach().mean(dim=(2,3));q=F.normalize(mean,dim=-1)
target=F.normalize(y.mean(dim=(2,3)),dim=-1)
cosine=(q*target).sum()
derivative=(target-cosine*q)/torch.linalg.vector_norm(mean,dim=1,keepdim=True)
oracle=F.relu((derivative[:,:,None,None]/4*x.detach()).sum(dim=1))[0].numpy()
np.testing.assert_allclose(cam,oracle,atol=2e-8,rtol=2e-6)
assert abs(score-float(cosine))<1e-7
assert not model.visual_backbone.layer4._forward_hooks
assert x.grad is None  # autograd.grad does not populate/accumulate input gradients.

# A failed target must still remove the hook.
bad=x.detach().clone().requires_grad_(True)
bad.data[0,0,0,0]=float('nan')
try:
    v.compute_gradcam(model,(bad,dummy,dummy),(y,dummy,dummy))
except RuntimeError:
    pass
else:
    raise AssertionError('Nonfinite CAM accepted')
assert not model.visual_backbone.layer4._forward_hooks

valid=np.eye(3,dtype=np.float32)
v.check_descriptors(valid,3,3)
for invalid in [np.ones((3,3),dtype=np.float32),valid.astype(np.float64),valid*np.nan]:
    try:v.check_descriptors(invalid,3,3)
    except RuntimeError:pass
    else:raise AssertionError('Invalid descriptor accepted')
assert v.normalized_maps({'a':np.zeros((1,7,7),np.float32)})==(0.,1.)
assert v.normalized_maps({'a':np.ones((1,7,7)), 'b':np.full((1,7,7),2.)})==(2.,2.)
try:v.normalized_maps({'bad':np.full((1,7,7),np.nan)})
except RuntimeError:pass
else:raise AssertionError('Nonfinite raw map accepted')
assert not torch.cuda.is_initialized()
report={'status':'passed','scope':'Static frozen API signatures and small CPU analytic operators; no real checkpoint/model inference, no figure generation',
        'checks':['8 frozen API signatures','Analytic cosine Grad-CAM equality','Hook cleanup on success/error',
                  'No gradient accumulation','FP32/unit-norm/finite descriptor checks','Shared raw-CAM maximum and zero-map preservation','CUDA not initialized'],
        'script_sha256':v.sha(here/'make_real_model_visualizations.py'),'frozen_core_sha256':v.sha(core_path)}
v.dump(here/'real_visualization_cpu_checks.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
