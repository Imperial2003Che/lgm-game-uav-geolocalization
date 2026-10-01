"""Deferred complete DAC training-state checks; stdlib only at module import."""
from protocol import load,require

def validate_full_training_state(complete,binding,torch):
    """Validate saved state after full402 comparison; never restore training."""
    files=binding['training_files'];proof=load(files['dac_training_protocol_evidence.json']['path'])
    sampling=load(files['epoch01_sampling.json']['path']);counts=binding['optimizer_counts']
    optimizer=complete['optimizer'];require(isinstance(optimizer,dict) and optimizer.get('state') and optimizer.get('param_groups'),'Missing complete AdamW state')
    steps=[]
    for row in optimizer['state'].values():
        require({'step','exp_avg','exp_avg_sq'}.issubset(row),'Incomplete AdamW moments')
        step=float(row['step']);require(step>0 and step==int(step),'Invalid AdamW step');steps.append(int(step))
        for key in ('exp_avg','exp_avg_sq'):
            tensor=row[key];require(isinstance(tensor,torch.Tensor) and tensor.device.type=='cpu','Expected CPU AdamW moments')
            flat=tensor.reshape(-1)
            for start in range(0,flat.numel(),262144):require(bool(torch.isfinite(flat[start:start+262144]).all()),'Nonfinite saved AdamW moments')
    require(min(steps)==proof['optimizer_step_min'] and max(steps)==proof['optimizer_step_max']==counts['actual_adamw_steps'],'Saved optimizer counters differ')
    require(complete['scheduler']['last_epoch']==counts['attempted_batches'],'Saved scheduler attempts differ')
    require(complete['scaler']==complete['training_evidence']['final_scaler_state'],'Saved AMP scaler differs')
    require(complete['scheduler_total_steps_before_initial_shuffle']==1578 and complete['warmup_steps']==157.8,'Original pre-shuffle scheduler differs')
    require(set(complete['rng'])=={'python','numpy','torch_cpu','torch_cuda'} and len(complete['rng']['torch_cuda'])==1,'Complete RNG inventory differs')
    sampler=complete['sampler'];require(len(sampler['pairs'])==37854 and sampler['shuffle_batch_size']==24,'Original next-epoch sampler state differs')
    require(isinstance(sampler['samples_for_next_epoch'],list) and sampler['samples_for_next_epoch'] and len(sampler['samples_for_next_epoch'])%24==0,'Missing next-epoch sampler state')
    require(sampling['expected_batches']==counts['attempted_batches'],'Incomplete original consumed loader')
