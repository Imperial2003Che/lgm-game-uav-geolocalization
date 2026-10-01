"""Bounded CPU checks; no author checkpoint/model forward or scientific results."""
import argparse
import ast
import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.dont_write_bytecode=True
import run_camp_author_evaluation as r

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--with-torch-stub',action='store_true')
parser.add_argument('--with-transform',action='store_true')
parser.add_argument('--full-path-inventory',action='store_true')
args=parser.parse_args()
if (args.with_torch_stub or args.with_transform) and os.environ.get('CUDA_VISIBLE_DEVICES')!='':
    parser.error('CPU semantic checks require CUDA_VISIBLE_DEVICES to be explicitly empty')

sources=r.verify_sources()
rank,ap=r.official_rank_function()
record=r.Record
task=r.Task('fixture',(record('q/a','a'),),(record('g/b','b'),record('g/a','a')))
encoded={'q/a':np.array([1,0],np.float32),'g/b':np.array([1,0],np.float32),'g/a':np.array([.8,.6],np.float32)}
metrics,arrays=r.rank_with_query_evidence(task,encoded,1)
assert metrics['gallery']==2 and metrics['r_at_1']==0 and metrics['official_trapezoid_mAP']==.25
assert arrays['top1_gallery_labels'].tolist()==['b']
assert metrics['rank_precision_mAP']==.5 and arrays['positive_ranks_1based'].tolist()==[2]
memory=io.BytesIO();np.savez_compressed(memory,**arrays);memory.seek(0)
r.validate_query_arrays(memory,task,metrics)
altered={**arrays,'per_query_official_trapezoid_AP':np.array([1.],np.float32)}
memory=io.BytesIO();np.savez_compressed(memory,**altered);memory.seek(0)
try:r.validate_query_arrays(memory,task,metrics)
except RuntimeError:pass
else:raise AssertionError('Corrupted AP accepted')

# Execute the unchanged author's AP function with NumPy arrays and a tiny CMC
# allocation stand-in. np.in1d was renamed/removed in newer NumPy; np.isin has
# the same membership role for these one-dimensional fixture indices.
source=r.SOURCE/'sample4geo/evaluate/university.py'
tree=ast.parse(source.read_text(encoding='utf-8'))
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='compute_mAP')
class NumPyNames:
    in1d=staticmethod(np.isin)
    def __getattr__(self,name):return getattr(np,name)
class SmallCMC:
    def __init__(self,n):self.n=n
    def zero_(self):return np.zeros(self.n,dtype=np.int32)
ns={'np':NumPyNames(),'torch':SimpleNamespace(IntTensor=SmallCMC)}
exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(source),'exec'),ns)
for positions in ([0],[1],[0,2],[2,5,7]):
    order=np.arange(max(positions)+2)
    author_ap,_=ns['compute_mAP'](order,np.asarray(positions),np.asarray([],dtype=np.int64))
    assert abs(author_ap-ap(np.asarray(positions)))<1e-12
author_filtered,_=ns['compute_mAP'](np.array([0,1]),np.array([1]),np.array([0]))
assert author_filtered==1 and author_filtered!=metrics['official_trapezoid_mAP']

sealed=r.seal({'x':1});r.verify_seal(sealed)
try:r.verify_seal({**sealed,'x':2})
except RuntimeError:pass
else:raise AssertionError('Tampered manifest accepted')
try:r.release_gate(Path('never_opened'),None)
except RuntimeError as exc:assert 'Explicit later release' in str(exc)
else:raise AssertionError('No release file accepted')

# Exercise the real gate on memory-only status fixtures; never call nvidia-smi.
stamp='2026-09-14T00:00:00+00:00'
fixtures={'release.json':{'schema':'camp-author-checkpoint-release.v1','allow_cuda':True,
                         'prepared_manifest_sha256':'h','preceding_extension_plan_sha256':'h'},
          'status.json':{'status':'completed','controller_pid':1,'started_utc':stamp},
          'pipeline_status.json':{'status':'ready_for_extension_preparation','supervisor_pid':2,'supervisor_started_utc':stamp,
              'jobs':[{'id':name,'status':'completed','exit_code':0,'pid':20+i,'started_utc':stamp} for i,name in enumerate(r.PRIMARY_STAGE_IDS)]},
          'extension_status.json':{'status':'registered_extensions_finished_review_pending','supervisor_pid':3,'plan_sha256':'h','supervisor_started_utc':stamp,
              'jobs':[{'id':name,'status':'completed','exit_code':0,'pid':40+i,'started_utc':stamp} for i,name in enumerate(r.EXTENSION_IDS)]}}
with patch.object(r,'load',side_effect=lambda p:copy.deepcopy(fixtures[Path(p).name])),patch.object(r,'sha',return_value='h'),\
     patch.object(r,'artifact',side_effect=lambda p:{'path':str(p),'sha256':'h'}),patch.object(r,'alive',return_value=False),\
     patch.object(r.subprocess,'run',return_value=SimpleNamespace(stdout='')) as fake_gpu_query:
    r.release_gate(Path('manifest.json'),Path('release.json'))
    assert fake_gpu_query.call_count==1
    fixtures['status.json'].pop('controller_pid')
    try:r.release_gate(Path('manifest.json'),Path('release.json'))
    except RuntimeError:pass
    else:raise AssertionError('Unrecorded preceding process identity accepted')
    fixtures['status.json']['controller_pid']=1
    fixtures['extension_status.json']['jobs'][0]['status']='pending'
    try:r.release_gate(Path('manifest.json'),Path('release.json'))
    except RuntimeError:pass
    else:raise AssertionError('Pending extension accepted')
    assert fake_gpu_query.call_count==1
    fixtures['extension_status.json']['jobs'][0]['status']='completed'
    with patch.object(r,'alive',return_value=True):
        try:r.release_gate(Path('manifest.json'),Path('release.json'))
        except RuntimeError:pass
        else:raise AssertionError('Live preceding process accepted')
    assert fake_gpu_query.call_count==1

report={'status':'passed','scope':'CPU-only fixtures/source and path checks; no real descriptors, author model inference, training or retrieval results',
        'python':sys.executable,'numpy_version':np.__version__,
        'environment_controls':{name:os.environ.get(name) for name in ('CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS')},
        'checks':['Official source/checkpoint/split pins','Frozen rank retains distractors','Original author AP matches frozen AP with no junk',
                  'Author junk removal demonstrably changes the protocol','All positive ranks recover both AP definitions and query recalls','Saved AP corruption rejected',
                  'Manifest corruption rejected','Absent explicit release rejected before GPU checks',
                  'Real serial-gate logic rejects pending stages and live owners using in-memory fixtures; no GPU query executed'],
        'code_sha256':r.sha(HERE/'run_camp_author_evaluation.py'),'camp_model_sha256':r.sha(HERE/'camp_model.py')}

if args.full_path_inventory:
    inventory,tasks=r.discover_tasks(Path(r'C:\项目\IMTMN\datasets\University-1652'),Path(r'C:\项目\IMTMN\datasets\SUES-200'))
    assert len(tasks)==10 and len(inventory)==131062
    assert [(t['query_count'],t['gallery_count']) for t in tasks[:2]]==[(37855,951),(701,51355)]
    assert [(t['query_count'],t['gallery_count']) for t in tasks[2:]]==[(4000,200),(80,10000)]*4
    assert [t['distractor_identity_count'] for t in tasks]==[250,250]+[120]*8
    report['full_path_inventory']={'unique_images':len(inventory),'tasks':10,
                                   'stat_inventory_sha256':r.canonical(inventory),'task_manifest_sha256':r.canonical(tasks),
                                   'all_distractors_retained':True}

if args.with_torch_stub:
    import torch
    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    sys.path.insert(0,str(r.SOURCE))
    official=importlib.import_module('sample4geo.hand_convnext.ConvNext.make_model')
    assert Path(official.__file__).resolve()==(r.SOURCE/'sample4geo/hand_convnext/ConvNext/make_model.py').resolve()
    x=torch.arange(24,dtype=torch.float32).reshape(1,3,2,4)/17
    class Backbone:
        def __call__(self,value):return value.mean(dim=(-2,-1)),value.clone()
    checks=[]
    for scale in (-100.,0.,0.6,100.):
        stub=SimpleNamespace(convnext=Backbone(),pos_embed=torch.ones_like(x)*.7,pos_scale=scale,training=False)
        gap,part=official.build_convnext.forward(stub,x)
        checks.append({'pos_scale':scale,'gap_bytes_sha256':hashlib.sha256(gap.numpy().tobytes()).hexdigest(),
                       'part_bytes_sha256':hashlib.sha256(part.numpy().tobytes()).hexdigest()})
    assert len({row['gap_bytes_sha256'] for row in checks})==1
    assert len({row['part_bytes_sha256'] for row in checks})==4
    assert not torch.cuda.is_initialized()
    report['pos_scale_real_official_forward_fixture']={'status':'passed','source_sha256':r.sha(Path(official.__file__)),
                 'function':'build_convnext.forward','backbone':'tiny fixed CPU stub; not an author model or dataset',
                 'gap_byte_identical_for_all_scales':True,'discarded_part_changes':True,'cases':checks,'cuda_initialized':False}

if args.with_transform:
    import cv2
    import torch
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    # Execute the actual official get_transforms, not a copied expected formula.
    source=r.SOURCE/'sample4geo/dataset/university.py';tree=ast.parse(source.read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='get_transforms')
    namespace={'A':A,'cv2':cv2,'ToTensorV2':ToTensorV2}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(source),'exec'),namespace)
    official_transform=namespace['get_transforms']((384,384))[0]
    image=(np.arange(11*17*3,dtype=np.uint16).reshape(11,17,3)%256).astype(np.uint8)
    adapter=r.make_validation_transform()(image=image)['image']
    actual=official_transform(image=image)['image']
    assert torch.equal(adapter,actual) and tuple(adapter.shape)==(3,384,384) and adapter.dtype==torch.float32
    resized=cv2.resize(image,(384,384),interpolation=cv2.INTER_LINEAR_EXACT).astype(np.float32)
    expected=(resized-np.asarray([.485,.456,.406],np.float32)*255)/(np.asarray([.229,.224,.225],np.float32)*255)
    error=float(np.max(np.abs(adapter.numpy()-expected.transpose(2,0,1))))
    assert error<1e-6 and not torch.cuda.is_initialized()
    report['validation_transform']={'status':'passed','adapter_equals_official_byte_for_byte':True,
          'arithmetic_max_error':error,'shape':[3,384,384],'dtype':'torch.float32','no_flip_tta':True,'cuda_initialized':False,
          'albumentations_version':A.__version__,'opencv_version':cv2.__version__,'torch_version':torch.__version__}

report['torch_imported']='torch' in sys.modules
if report['torch_imported']:report['torch_cpu_threads']=torch.get_num_threads()
if not args.with_transform and not args.with_torch_stub:assert not report['torch_imported']
destination=HERE/('cpu_semantic_validation.json' if args.with_transform or args.with_torch_stub else 'cpu_static_validation.json')
r.save(destination,report)
print(json.dumps(report,ensure_ascii=True,indent=2))
