"""Read this project's own archived checkpoint while all training is stopped."""
import os, sys, json, datetime, hashlib, zipfile
from pathlib import Path
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
assert Path(sys.executable).resolve()==Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe').resolve()
import torch
torch.set_num_threads(1)
assert torch.__version__=='2.11.0+cu126'
root=Path(__file__).resolve().parent/'memory_recovery_20260914_1424'
run=root/'run'
read=lambda name: json.loads((run/name).read_text(encoding='utf-8-sig'))
history=read('history.json'); manifest=read('run_manifest.json'); config=read('run_config.json')
assert len(history)==18 and [row['epoch'] for row in history]==list(range(18))
assert manifest['last_completed_epoch']==17 and manifest['history_rows']==18
reports=[]
for name in ('last.pt','best.pt'):
    path=run/name
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
    # Locally generated trusted training checkpoint, including Python/NumPy RNG.
    state=torch.load(path,map_location='cpu',weights_only=False,mmap=True)
    required={'model_state','optimizer_state','scheduler_state','scaler_state','rng_state','immutable_config','run_config_sha256','history','epoch'}
    assert required<=state.keys()
    assert state['epoch']==17 and state['history']==history
    assert state['run_config_sha256']==manifest['run_config_sha256']==config['run_config_sha256']
    assert state['immutable_config']==config['immutable_config']
    assert state['immutable_config']['seed']==2
    assert {'python','numpy','torch_cpu','torch_cuda'}<=state['rng_state'].keys()
    assert len(state['rng_state']['torch_cuda'])==1
    tensors=[]
    def check(value):
        if isinstance(value,torch.Tensor):
            tensors.append(value)
            if value.is_floating_point(): assert bool(torch.isfinite(value).all())
        elif isinstance(value,dict):
            for item in value.values(): check(item)
        elif isinstance(value,(tuple,list)):
            for item in value: check(item)
    check(state['model_state']); check(state['optimizer_state'])
    assert len(state['optimizer_state']['state'])>0 and state['scaler_state']
    assert state['scheduler_state']['last_epoch']==18*652
    reports.append({'file':str(path),'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'epoch_zero_based':17,'completed_epochs':18,'finite_model_and_optimizer_tensors':len(tensors),'optimizer_parameter_states':len(state['optimizer_state']['state']),'scaler_state':state['scaler_state'],'scheduler_state':state['scheduler_state'],'config_sha256':state['run_config_sha256'],'rng_state_fields':list(state['rng_state'])})
    del tensors, state
assert reports[0]['sha256']==reports[1]['sha256']
report={'status':'verified_complete_epoch_18','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'executable':sys.executable,'torch':torch.__version__,'cuda_initialized':torch.cuda.is_initialized(),'reports':reports,'note':'Read-only audit before restart. No scientific helper may remain alive during training.'}
assert not report['cuda_initialized']
(root/'checkpoint_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'cuda_initialized':False,'files':len(reports)}))
