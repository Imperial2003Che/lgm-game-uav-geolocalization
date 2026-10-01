"""Future strict 395-state CAMP loader. No scientific imports at module scope."""
import importlib.util
from pathlib import Path
import sys
from protocol import AUTHOR, MODEL_FACTORY, MODEL_FACTORY_SHA, sha, load, canonical, compare_schema, verify_artifact

def load_complete_final_model(binding):
    """Only called after all serial/release checks during future evaluation.

    Both completed training files are restricted mmap reads. Every model tensor
    in the complete checkpoint must equal the final weights byte for byte.
    """
    import torch
    if sha(MODEL_FACTORY)!=MODEL_FACTORY_SHA:raise RuntimeError('Fixed original CAMP factory changed')
    name='_camp_independent_full_original_model_factory'
    if name not in sys.modules:
        spec=importlib.util.spec_from_file_location(name,MODEL_FACTORY)
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    factory=sys.modules[name]
    for item in binding['checkpoints'].values():verify_artifact(item)
    with factory.no_network():
        # Explicit False keeps the original learned pos_scale Parameter. Never
        # call the 394-state author loader or its author-specific validator.
        model=factory.build_camp_model(device='meta',author_checkpoint_schema=False)
        if not isinstance(model.model_1.pos_scale,torch.nn.Parameter) or not model.model_1.pos_scale.requires_grad:
            raise RuntimeError('The original learned pos_scale must remain a Parameter')
        complete=torch.load(binding['checkpoints']['checkpoint_complete.pth']['path'],map_location='cpu',weights_only=True,mmap=True)
        final=torch.load(binding['checkpoints']['weights_end.pth']['path'],map_location='cpu',weights_only=True,mmap=True)
        if not isinstance(complete,dict) or complete.get('schema_version')!=1 or complete.get('epoch_completed')!=1 or complete.get('next_epoch')!=2:raise RuntimeError('Unsupported final complete checkpoint')
        if complete.get('plan_sha256')!=binding['plan']['sha256']:raise RuntimeError('Complete checkpoint training plan differs')
        training_files=binding['training_files']
        if complete.get('profile_sha256')!=training_files['resource_profile.json']['sha256']:raise RuntimeError('Complete checkpoint resource profile differs')
        for key in ('code_manifest.json','data_manifest.json','environment_manifest.json','runtime_environment.json','serial_release_gate.json'):
            if complete.get('manifests',{}).get(key)!=training_files[key]['sha256']:raise RuntimeError('Complete checkpoint provenance differs: '+key)
        config=load(training_files['effective_configuration.json']['path'])
        if canonical(complete.get('configuration'))!=canonical(config) or config.get('seed')!=binding['seed']:raise RuntimeError('Complete checkpoint seed/configuration differs')
        evidence=load(training_files['training_evidence.json']['path'])
        if canonical(complete.get('training_evidence'))!=canonical(evidence):raise RuntimeError('Complete checkpoint training evidence differs')
        if complete.get('global_step')!=evidence['actual_adamw_steps'] or complete.get('attempted_batches')!=evidence['attempted_batches']:raise RuntimeError('Complete checkpoint step counts differ')
        for key in ('optimizer','scheduler','scaler','rng','sampler'):
            if complete.get(key) is None:raise RuntimeError('Complete training checkpoint lacks '+key)
        from_complete=complete.get('model')
        if not isinstance(final,dict) or not isinstance(from_complete,dict):raise RuntimeError('Expected original tensor mappings')
        for label,state in [('weights_end',final),('checkpoint_complete.model',from_complete)]:
            if not all(isinstance(k,str) and isinstance(v,torch.Tensor) for k,v in state.items()):raise RuntimeError('Non-tensor model state in '+label)
        metadata=lambda state:{k:(tuple(v.shape),str(v.dtype)) for k,v in state.items()}
        expected=metadata(model.state_dict());proof=compare_schema(expected,metadata(final));compare_schema(expected,metadata(from_complete))
        checked=0
        for key,value in final.items():
            other=from_complete[key]
            # Bounded contiguous chunks avoid a second whole-model host copy.
            a=value.reshape(-1);b=other.reshape(-1)
            for start in range(0,a.numel(),262144):
                left=a[start:start+262144];right=b[start:start+262144]
                if not torch.equal(left.view(torch.uint8),right.view(torch.uint8)):raise RuntimeError('Complete/end checkpoint tensor bytes differ: '+key)
                if left.is_floating_point() and not bool(torch.isfinite(left).all()):raise RuntimeError('Non-finite final model state: '+key)
            checked+=1
        incompatible=model.load_state_dict(final,strict=True,assign=True)
        if incompatible.missing_keys or incompatible.unexpected_keys:raise RuntimeError('Strict final-state assignment failed')
        if any(v.device.type!='cpu' for v in model.state_dict().values()):raise RuntimeError('Full model failed to materialize on CPU')
        if not isinstance(model.model_1.pos_scale,torch.nn.Parameter) or not model.model_1.pos_scale.requires_grad:raise RuntimeError('Learned pos_scale was lost during load')
        proof.update(seed=binding['seed'],complete_and_end_tensors_byte_equal=checked,
            complete_checkpoint_sha256=binding['checkpoints']['checkpoint_complete.pth']['sha256'],
            final_checkpoint_sha256=binding['checkpoints']['weights_end.pth']['sha256'],
            strict=True,assign=True,weights_only=True,mmap=True,learned_pos_scale_preserved=True,
            source_type='independent local training, fixed final epoch',model_factory_author_checkpoint_schema=False)
        del complete,from_complete,final
    return model.eval(),proof,factory.no_network
