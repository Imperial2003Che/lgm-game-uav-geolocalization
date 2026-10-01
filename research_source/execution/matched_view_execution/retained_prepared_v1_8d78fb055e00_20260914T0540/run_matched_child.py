"""One admitted real profile/train/evaluation subprocess; never used in CPU preparation."""
from __future__ import annotations
import importlib
import math
import os
from pathlib import Path
import sys
import traceback
import matched_runtime as r


def tensor_checkpoint_proof(core,spec,prepared,final):
    """Inspect trusted locally produced complete state only after serial admission."""
    import torch
    config=r.read(spec.run_dir/'run_config.json')
    history=r.read(spec.run_dir/'history.json')
    model_config=config['immutable_config']['model']
    with torch.device('meta'):
        reference=core.FormalRetrievalModel(variant=model_config['variant'],backbone=model_config['backbone'],
            embed_dim=model_config['embed_dim'],dropout=model_config['dropout'],pretrained=False)
    expected_state=reference.state_dict()
    proof={}
    for name in ('last.pt','best.pt'):
        path=spec.run_dir/name;before=r.artifact(path)
        state=core.load_torch_checkpoint(path,'cpu')
        needed={'model_state','optimizer_state','scheduler_state','scaler_state','rng_state','history','epoch','immutable_config','run_config_sha256','model_config','evidence_schema'}
        if not needed.issubset(state):raise RuntimeError('Incomplete resumable checkpoint: '+name)
        if set(state['model_state'])!=set(expected_state):raise RuntimeError('Checkpoint model keys differ from exact derived architecture')
        if any(tuple(state['model_state'][key].shape)!=tuple(value.shape) or state['model_state'][key].dtype!=value.dtype for key,value in expected_state.items()):
            raise RuntimeError('Checkpoint model tensor shape/dtype differs from exact derived architecture')
        if state['run_config_sha256']!=config['run_config_sha256'] or state['immutable_config']!=config['immutable_config'] or state['model_config']!=config['immutable_config']['model']:
            raise RuntimeError('Checkpoint configuration does not match the independent run')
        if state['history']!=history or state['epoch']!=len(history)-1 or not 1<=len(history)<=80:raise RuntimeError('Checkpoint epoch/history do not agree; retain and review interrupted atomic writes')
        if final and (state['epoch']!=79 or len(history)!=80):raise RuntimeError('The final checkpoint must contain all 80 epochs')
        if state['best_epoch']!=state['epoch'] or state['best_validation_mAP']!=0.0 or state['epochs_without_improvement']!=0:raise RuntimeError('Checkpoint selection was not the fixed final-completed epoch')
        if not {'python','numpy','torch_cpu','torch_cuda'}.issubset(state['rng_state']):raise RuntimeError('Missing RNG restore state')
        tensors=0
        def finite(value):
            nonlocal tensors
            if isinstance(value,torch.Tensor):
                tensors+=1
                if value.is_floating_point() and not bool(torch.isfinite(value).all()):raise RuntimeError('Nonfinite tensor in saved training state')
            elif isinstance(value,dict):
                for item in value.values():finite(item)
            elif isinstance(value,(list,tuple)):
                for item in value:finite(item)
            elif isinstance(value,float) and not math.isfinite(value):raise RuntimeError('Nonfinite scalar in saved training state')
        finite(state['model_state']);finite(state['optimizer_state']);finite(state['scheduler_state']);finite(state['scaler_state'])
        if r.artifact(path)!=before:raise RuntimeError('Checkpoint changed during read-only audit')
        proof[name]={'artifact':before,'tensor_count_checked':tensors,'all_model_keys_shapes_dtypes_match_exact_meta_architecture':True}
        del state
    return r.seal({'status':'strict_final_checkpoint_verified' if final else 'strict_resume_checkpoint_verified',
        'created_utc':r.utc(),'prepared_sha256':r.sha(prepared),'id':spec.identifier,'epoch':len(history)-1,'history_rows':len(history),
        'config_sha256':config['run_config_sha256'],'checkpoint_artifacts':{k:v['artifact'] for k,v in proof.items()},
        'tensor_checks':proof,'model_optimizer_scheduler_scaler_rng_present':True,'original_checkpoint_bytes_preserved':True})


def profile(core,args,lease):
    """Two real native-batch updates through the unchanged original training body."""
    import torch
    original_optimizer=core.optimizer_for_model
    original_scheduler=core.cosine_warmup_scheduler
    updates={'optimizer':0,'scheduler':0}
    class ProfileComplete(BaseException):pass
    def optimizer(*a,**kw):
        result=original_optimizer(*a,**kw)
        def count_step(opt,arguments,keywords):updates['optimizer']+=1
        result.register_step_post_hook(count_step)
        return result
    def scheduler(*a,**kw):
        result=original_scheduler(*a,**kw);old=result.step
        def step(*values,**options):
            answer=old(*values,**options);updates['scheduler']+=1
            if updates['optimizer']>=2:
                torch.cuda.synchronize()
                raise ProfileComplete()
            if updates['scheduler']>=10:raise RuntimeError('Ten batches did not produce two finite AMP optimizer updates')
            return answer
        result.step=step
        return result
    core.optimizer_for_model=optimizer;core.cosine_warmup_scheduler=scheduler
    try:
        core.run_train(args)
    except ProfileComplete:
        if updates['optimizer']!=2:raise RuntimeError('Resource profile optimizer count differs')
        proof=r.seal({'status':'native_resource_profile_passed','created_utc':r.utc(),
            'prepared_sha256':lease['prepared_sha256'],'variant':args.variant,'seed':args.seed,
            'native_batch_size':64,'workers':8,'optimizer_updates':2,'scheduler_updates':updates['scheduler'],
            'amp':True,'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_reserved_bytes':torch.cuda.max_memory_reserved(),
            'torch_version':torch.__version__,'gpu':torch.cuda.get_device_name(0),'scientific_result':False,
            'description':'Disposable seed1 instance, actual original loop through backward/AMP/optimizer/clamp/scheduler; no trial checkpoint enters fitting or model selection.'})
        r.save(Path(args.output_dir)/'resource_profile.json',proof)
        if (Path(args.output_dir)/'last.pt').exists():raise RuntimeError('Resource probe unexpectedly wrote an epoch checkpoint')
    else:raise RuntimeError('Profile unexpectedly completed an epoch schedule')
    finally:core.optimizer_for_model=original_optimizer;core.cosine_warmup_scheduler=original_scheduler


def main():
    lease=r.child_gate()
    if [str(Path(sys.argv[0]).resolve()),*sys.argv[1:]]!=lease['command'][1:]:raise RuntimeError('Admitted child command changed')
    plan=r.validate_prepared(lease['prepared'])
    core=importlib.import_module('formal_retrieval_two_view')
    args=core.build_parser().parse_args(sys.argv[1:]);core.validate_cli(args)
    output=Path(args.output_dir).resolve()
    if str(output)!=lease['output_dir']:raise RuntimeError('Child output differs from lease')
    actual={name:importlib.import_module(name) for name in ('numpy','PIL','torch','torchvision')}
    expected={'numpy':'2.4.4','PIL':'12.2.0','torch':'2.11.0+cu126','torchvision':'0.26.0+cu126'}
    for name,module in actual.items():
        if module.__version__!=expected[name] or not Path(module.__file__).resolve().is_relative_to(r.PYTHON.parent.parent):raise RuntimeError('Imported runtime differs: '+name)
    runtime={'python':sys.executable,'modules':{name:{'version':module.__version__,'file':module.__file__} for name,module in actual.items()},
             'inherited_host_thread_environment':r.thread_environment(),'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),
             'CUBLAS_WORKSPACE_CONFIG':os.environ.get('CUBLAS_WORKSPACE_CONFIG'),'PYTHONHASHSEED':os.environ.get('PYTHONHASHSEED'),'torch_threads':core.torch.get_num_threads(),
             'thread_settings_modified_by_adapter':False}
    r.save(Path(lease['attempt_dir'])/'runtime_actual.json',runtime)
    spec=next((s for s in r.specifications() if s.identifier==lease['id']),None)
    if spec is None:raise RuntimeError('Unknown independent fit')
    if lease['mode']=='profile':
        profile(core,args,lease)
    elif lease['mode']=='train':
        import matched_audit as audit
        audit.origin(spec,lease['prepared'])
        if (spec.run_dir/'last.pt').exists():
            audit.audit_config(spec,plan)
            proof=tensor_checkpoint_proof(core,spec,lease['prepared'],False)
            r.save(Path(lease['attempt_dir'])/'resume_checkpoint_proof.json',proof)
        core.run_train(args)
        audit.audit_config(spec,plan)
        r.save(spec.run_dir/'checkpoint_proof.json',tensor_checkpoint_proof(core,spec,lease['prepared'],True))
    elif lease['mode']=='evaluate':
        import matched_audit as audit
        for registered in r.specifications():audit.train_complete(registered,plan,lease['prepared'])
        core.run_evaluate(args)
    else:raise RuntimeError('Unsupported child operation')


if __name__=='__main__':
    try:main()
    except BaseException as error:
        name=os.environ.get('MATCHED_VIEW_LEASE')
        if name:
            lease=r.read(r.inside(name))
            r.save(Path(lease['attempt_dir'])/'child_failure.json',{'status':'failed','utc':r.utc(),'pid':os.getpid(),
                'type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc()})
        raise
