"""Import real frozen training modules with CUDA initialization prohibited."""
import os,sys,argparse,ast,json,traceback
from pathlib import Path
P=Path(__file__).resolve().parent
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['XFORMERS_DISABLED']='1';os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
sys.dont_write_bytecode=True
p=argparse.ArgumentParser();p.add_argument('--framework',choices=['qdfl','mccg'],required=True);a=p.parse_args()
delivery=P/'compatibility_v3/delivery';work=P/'compatibility_v3/work'
sys.path.insert(0,str(delivery))
from external_baselines import qdfl_adapter as q
import torch
def no_cuda(*args,**kwargs):raise RuntimeError('CPU import preflight forbids CUDA initialization')
torch.cuda._lazy_init=no_cuda
result={'framework':a.framework,'status':'running','torch_version':torch.__version__,'interpreter':sys.executable,'gpu_executed':False}
try:
 if a.framework=='qdfl':
  root=work/'patched_sources/qdfl-627296d5-adapter-v4'
  os.environ['LGM_QDFL_U1652_TRAIN_ROOT']=r'C:\项目\IMTMN\datasets\University-1652\train'
  os.environ['LGM_QDFL_DINOV2_VITB14_WEIGHTS']=str(work/'weights/dinov2_vitb14_pretrain.pth')
  DM,Model=q._load_qdfl_runtime(root)
  result['imported_classes']=[DM.__name__,Model.__name__]
 else:
  root=work/'patched_sources/mccg-e1c51b01-adapter-v3';sys.path.insert(0,str(root));os.chdir(root)
  tree=ast.parse((root/'train.py').read_text(encoding='utf-8'))
  imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
  namespace={};exec(compile(ast.Module(body=imports,type_ignores=[]),str(root/'train.py')+'#imports','exec'),namespace)
  assert 'np' in namespace
  result['imported_callables']=[x for x in ['make_model','make_optimizer','make_dataset','cal_loss','cal_triplet_loss','GradScaler'] if x in namespace]
 assert not torch.cuda.is_initialized()
 result.update(status='passed',cuda_initialized=False)
except Exception as e:result.update(status='failed',error=str(e),traceback=traceback.format_exc(),cuda_initialized=torch.cuda.is_initialized())
(P/(a.framework+'_cpu_import_preflight.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['status']=='passed' else 2)
