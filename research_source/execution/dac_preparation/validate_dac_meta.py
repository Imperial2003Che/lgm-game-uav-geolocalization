"""Validate official DAC checkpoint against exact model schema on meta only."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import traceback

P = Path(__file__).resolve().parent
E = P.parent


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    output = P/'strict_meta_compatibility.json'
    metadata_path = P/'author_checkpoint_metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    checkpoint = Path(metadata['checkpoint'])
    report = {'status':'started','started_utc':datetime.now(timezone.utc).isoformat(),
        'python':sys.executable,'python_version':sys.version,
        'validator_path':str(Path(__file__).resolve()),'validator_sha256':sha(__file__),
        'factory_path':str(P/'dac_model.py'),'factory_sha256':sha(P/'dac_model.py'),
        'checkpoint_path':str(checkpoint),'checkpoint_sha256_expected':metadata['checkpoint_sha256'],
        'prior_metadata_path':str(metadata_path),'prior_metadata_sha256':sha(metadata_path),
        'process_thread_environment':{name:os.environ.get(name) for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']},
        'model_forward_executed':False,'real_tensor_checkpoint_load':False,'gpu_executed':False}
    try:
        assert checkpoint.stat().st_size==metadata['checkpoint_bytes']
        assert sha(checkpoint)==metadata['checkpoint_sha256']
        import torch
        from dac_model import build_dac_model, validate_checkpoint_state, no_network
        if torch.cuda.is_initialized():
            raise RuntimeError('CUDA already initialized before meta validation')
        report['environment_versions']={name:importlib.metadata.version(name) for name in ['torch','torchvision','timm','numpy','Pillow']}
        with no_network() as attempts:
            model=build_dac_model(device='meta')
            state=torch.load(checkpoint,map_location='meta',weights_only=True,mmap=True)
            assert all(value.device.type=='meta' for value in state.values())
            prior={x['key']:(x['shape'],x['dtype'],x['numel']) for x in metadata['tensors']}
            actual={key:(list(value.shape),str(value.dtype),value.numel()) for key,value in state.items()}
            assert prior==actual, 'Checkpoint metadata changed from prior restricted inspection'
            proof=validate_checkpoint_state(model,state)
            assert proof['tensor_count']==metadata['tensor_count']==402
            assert proof['total_stored_numel']==metadata['total_stored_numel']==96510327
            result=model.load_state_dict(state,strict=True,assign=True)
            assert not result.missing_keys and not result.unexpected_keys
            report['strict_load_result']={'strict':True,'assign':True,'missing_keys':result.missing_keys,'unexpected_keys':result.unexpected_keys}
            report['schema_comparison']=proof
            report['construction']=model._dac_construction_proof
            report['dtype_counts']=dict(Counter(str(v.dtype) for v in state.values()))
            report['parameters_numel']=sum(x.numel() for x in model.parameters())
            report['buffers_numel']=sum(x.numel() for x in model.buffers())
            report['tensor_comparisons']=[{'key':key,'shape':list(value.shape),'dtype':str(value.dtype),'numel':value.numel(),'device':'meta','matches':True} for key,value in sorted(state.items())]
            assert attempts==[]
        # Boundary fixtures reuse meta tensors only and do not run the model.
        boundary=[]
        key=next(iter(state))
        cases={
            'missing_key':{k:v for k,v in state.items() if k!=key},
            'unexpected_key':dict(state,unexpected_dac_fixture=torch.empty((),device='meta')),
            'wrong_shape':dict(state,**{key:torch.empty((1,),device='meta',dtype=state[key].dtype)}),
            'wrong_dtype':dict(state,**{key:torch.empty(state[key].shape,device='meta',dtype=torch.float64)}),
        }
        for name,case in cases.items():
            try:
                validate_checkpoint_state(model,case)
            except RuntimeError as error:
                boundary.append({'case':name,'rejected':True,'message':str(error)})
            else:
                raise AssertionError(f'Failed to reject schema fixture: {name}')
        report['negative_schema_fixtures']=boundary
        assert not torch.cuda.is_initialized()
        assert sha(checkpoint)==metadata['checkpoint_sha256']
        report.update(status='strict_meta_compatible_no_schema_adaptation',
            checkpoint_sha256_after=metadata['checkpoint_sha256'],cuda_initialized=False,
            finished_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        report.update(status='failed_preserved',error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),
            finished_utc=datetime.now(timezone.utc).isoformat())
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        raise
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','schema_comparison','dtype_counts','parameters_numel','buffers_numel','cuda_initialized','model_forward_executed']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
