"""Observe real AdamW updates and parameter bytes without changing the update math."""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import matched_runtime as r


def optimizer_structure(optimizer,scaler,scheduler,epoch,scheduled_batches):
    if not isinstance(optimizer,dict) or not optimizer.get('state') or not optimizer.get('param_groups'):
        raise RuntimeError('AdamW state or parameter groups are empty')
    groups=optimizer['param_groups']
    if any(not isinstance(group,dict) or not group.get('params') for group in groups):raise RuntimeError('Invalid AdamW parameter group')
    allowed={key for group in groups for key in group['params']}
    if not set(optimizer['state']).issubset(allowed):raise RuntimeError('AdamW state references unknown parameter IDs')
    steps=[]
    for value in optimizer['state'].values():
        if not isinstance(value,dict) or not {'step','exp_avg','exp_avg_sq'}.issubset(value):raise RuntimeError('AdamW moments/step are incomplete')
        step=float(value['step'])
        if not math.isfinite(step) or step<=0 or step!=int(step):raise RuntimeError('AdamW state has no positive real updates')
        if not hasattr(value['exp_avg'],'shape') or value['exp_avg'].shape!=value['exp_avg_sq'].shape:raise RuntimeError('AdamW moment shapes differ')
        steps.append(int(step))
    required_scaler={'scale','growth_factor','backoff_factor','growth_interval','_growth_tracker'}
    if not isinstance(scaler,dict) or not required_scaler.issubset(scaler):raise RuntimeError('AMP scaler restore state is incomplete')
    if not (float(scaler['scale'])>0 and float(scaler['growth_factor'])>1 and 0<float(scaler['backoff_factor'])<1 and int(scaler['growth_interval'])>0 and int(scaler['_growth_tracker'])>=0):
        raise RuntimeError('Invalid AMP scaler state')
    required_scheduler={'base_lrs','last_epoch','_step_count','_last_lr','lr_lambdas'}
    if not isinstance(scheduler,dict) or not required_scheduler.issubset(scheduler):raise RuntimeError('Scheduler restore state is incomplete')
    expected=(epoch+1)*scheduled_batches
    if scheduler['last_epoch']!=expected or scheduler['_step_count']<expected or not scheduler['base_lrs'] or not scheduler['_last_lr']:
        raise RuntimeError('Scheduler did not process the complete registered batch schedule')
    return {'maximum_parameter_step':max(steps),'minimum_parameter_step':min(steps),'parameters_with_adamw_state':len(steps),
            'scheduled_batches_through_epoch':expected,'scaler_and_scheduler_structure_complete':True}


def tensor_fingerprints(tensors):
    import torch
    result={}
    for name,tensor in sorted(tensors.items()):
        value=tensor.detach().cpu().contiguous()
        # The byte view avoids converting or rounding scientific parameter values.
        raw=value.reshape(-1).view(torch.uint8).numpy().tobytes()
        result[name]={'shape':list(value.shape),'dtype':str(value.dtype),'sha256':hashlib.sha256(raw).hexdigest()}
    return result


def validate_observed_updates(record,epoch,scheduled_batches,maximum_parameter_step,parameter_fingerprints,prepared_sha256):
    r.verify_seal(record)
    if record.get('schema')!='matched-actual-optimizer-updates.v1' or record.get('prepared_sha256')!=prepared_sha256:
        raise RuntimeError('Actual optimizer-update evidence is absent or belongs to another preparation')
    rows=record.get('epochs',[])
    if len(rows)!=epoch+1 or not record.get('initial_parameter_fingerprints'):
        raise RuntimeError('Optimizer observation does not cover every completed epoch')
    cumulative=0
    for index,row in enumerate(rows):
        actual=row.get('actual_adamw_updates')
        if row.get('epoch')!=index or row.get('scheduled_batches')!=scheduled_batches or type(actual) is not int or not 0<actual<=scheduled_batches:
            raise RuntimeError('Invalid or all-skipped actual epoch optimizer updates')
        cumulative+=actual
        if row.get('cumulative_actual_adamw_updates')!=cumulative:raise RuntimeError('Optimizer update cumulative count differs')
    if cumulative!=maximum_parameter_step:raise RuntimeError('Observed AdamW calls differ from checkpoint parameter step counters')
    if record.get('latest_parameter_fingerprints')!=parameter_fingerprints:raise RuntimeError('Parameter bytes differ from the observed checkpoint')
    if record['initial_parameter_fingerprints']==parameter_fingerprints:raise RuntimeError('No trainable parameter changed during fitting')
    return {'epochs_observed':len(rows),'actual_adamw_updates':cumulative,'scheduled_batches':scheduled_batches*(epoch+1),
            'amp_skipped_updates':scheduled_batches*(epoch+1)-cumulative,'trainable_parameters_changed':True}


class TrainingObserver:
    def __init__(self,core,spec,prepared,plan):
        self.core=core;self.spec=spec;self.prepared=prepared;self.plan=plan
        self.path=spec.run_dir/'optimizer_updates.json'
        self.record=r.read(self.path) if self.path.exists() else {'schema':'matched-actual-optimizer-updates.v1',
            'prepared_sha256':r.sha(prepared),'id':spec.identifier,'epochs':[]}
        if self.path.exists():
            r.verify_seal(self.record)
            if self.record['prepared_sha256']!=r.sha(prepared) or self.record['id']!=spec.identifier:raise RuntimeError('Unrelated optimizer observation')
        self.calls=0;self.previous_calls=0;self.pre_called=False;self.model=None
        self.original_optimizer=core.optimizer_for_model;self.original_save=core.atomic_torch_save

    def install(self):
        def optimizer(model,*args,**kwargs):
            self.model=model;result=self.original_optimizer(model,*args,**kwargs)
            def before_step(opt,arguments,keywords):
                if not self.pre_called:
                    current=tensor_fingerprints(dict(model.named_parameters()))
                    if self.record['epochs'] and current!=self.record['latest_parameter_fingerprints']:
                        raise RuntimeError('Resumed parameters differ from last checkpoint observation')
                    self.record.setdefault('initial_parameter_fingerprints',current)
                    self.pre_called=True
            def after_step(opt,arguments,keywords):self.calls+=1
            result.register_step_pre_hook(before_step);result.register_step_post_hook(after_step)
            return result
        def save_checkpoint(path,payload):
            if Path(path).name!='last.pt':return self.original_save(path,payload)
            epoch=int(payload['epoch']);scheduled=self.plan['steps_per_epoch'];actual=self.calls-self.previous_calls
            if len(self.record['epochs'])!=epoch or not 0<actual<=scheduled:raise RuntimeError('Actual optimizer updates do not match the next completed epoch')
            if not math.isfinite(float(payload['history'][-1]['train_loss'])):raise RuntimeError('Nonfinite original epoch training loss')
            structure=optimizer_structure(payload['optimizer_state'],payload['scaler_state'],payload['scheduler_state'],epoch,scheduled)
            current=tensor_fingerprints(dict(self.model.named_parameters()))
            if current==self.record.get('initial_parameter_fingerprints'):raise RuntimeError('No trainable parameter changed')
            cumulative=sum(row['actual_adamw_updates'] for row in self.record['epochs'])+actual
            if structure['maximum_parameter_step']!=cumulative:raise RuntimeError('Observed calls and saved AdamW step counters differ')
            self.original_save(path,payload)
            self.record['epochs'].append({'epoch':epoch,'scheduled_batches':scheduled,'actual_adamw_updates':actual,
                'cumulative_actual_adamw_updates':cumulative,'amp_skipped_updates':scheduled-actual,
                'parameter_state_sha256':r.canonical(current)})
            self.record.update(latest_parameter_fingerprints=current,updated_utc=r.utc())
            self.record.pop('payload_sha256',None);self.record=r.seal(self.record);r.save(self.path,self.record)
            self.previous_calls=self.calls
        self.core.optimizer_for_model=optimizer;self.core.atomic_torch_save=save_checkpoint

    def restore(self):
        self.core.optimizer_for_model=self.original_optimizer;self.core.atomic_torch_save=self.original_save
