"""Read existing immutable inputs and construct original DAC defaults using stdlib."""
import argparse
import ast
from dataclasses import dataclass
import json
import os
from pathlib import Path
from common_runtime import HERE, no_network, sha_file

def configuration_class():
    tree = ast.parse((HERE / 'train_university_train_only.py').read_text(encoding='utf-8'))
    node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Configuration')
    namespace = {'argparse': argparse, 'dataclass': dataclass, 'os': os}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'DAC-original-Configuration', 'exec'), namespace)
    return namespace['Configuration']

def make_configuration():
    return configuration_class()()

def configuration_defaults():
    return json.loads(json.dumps(vars(make_configuration())))

def references():
    return json.loads((HERE / 'INPUT_REFERENCES.json').read_text(encoding='utf-8'))

def verify_reference_files(check_pretrained_bytes=False):
    reference = references()
    if sha_file(reference['data_manifest_path']) != reference['data_manifest_sha256']:
        raise RuntimeError('Existing complete University content manifest changed')
    if check_pretrained_bytes and sha_file(reference['pretrained']['path']) != reference['pretrained']['sha256']:
        raise RuntimeError('Original Meta initialization bytes changed')
    # This function never rescans or decodes the actual training images.
    return reference

def construct_model_cpu(output_directory, seed=1):
    """A future explicit CPU compatibility probe; not training and not a saved plan.

    Returns (model, config, run). Construction performs real strict Meta initialization,
    so the caller must deliberately budget memory before calling this function.
    This function has not been executed during preparation.
    """
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('Explicit CPU probe requires CUDA_VISIBLE_DEVICES empty before any scientific import')
    from dac_train_runtime import DACTrainRun, SCIENTIFIC_SOURCE, verify_scientific_source
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    reference = verify_reference_files(check_pretrained_bytes=True)
    config = make_configuration()
    plan = {'method': 'DAC', 'seed': seed, 'source_directory': str(SCIENTIFIC_SOURCE),
        'output_directory': str(output), 'train_root': reference['train_root'],
        'pretrained': reference['pretrained'], 'official_configuration_defaults': configuration_defaults()}
    run = DACTrainRun(plan, output / 'not_a_registered_plan', output / 'no_resource_profile')
    run.configure(config)
    if str(SCIENTIFIC_SOURCE) not in __import__('sys').path:
        __import__('sys').path.insert(0, str(SCIENTIFIC_SOURCE))
    verify_scientific_source()
    with no_network():
        from sample4geo.utils import setup_system
        setup_system(seed=config.seed, cudnn_benchmark=config.cudnn_benchmark,
            cudnn_deterministic=config.cudnn_deterministic)
        model = run.make_model(config)
    import torch
    if any(tensor.device.type != 'cpu' for tensor in model.state_dict().values()):
        raise RuntimeError('This explicit compatibility constructor must remain on CPU')
    if torch.cuda.is_initialized():
        raise RuntimeError('Explicit CPU constructor unexpectedly initialized CUDA')
    run.cpu_data_config = model.get_config()
    return model, config, run

def normal_dataset_cpu(config, run):
    """Return the unchanged normal DAC loader; caller applies run.image_boundary()."""
    from sample4geo.dataset.university import U1652DatasetTrain, get_transforms
    from dac_train_runtime import verify_scientific_source
    verify_scientific_source()
    data_config = run.cpu_data_config
    _, satellite, drone = get_transforms((config.img_size, config.img_size),
        mean=data_config['mean'], std=data_config['std'])
    return U1652DatasetTrain(str(run.train_root / 'satellite'), str(run.train_root / 'drone'),
        transforms_query=satellite, transforms_gallery=drone,
        prob_flip=config.prob_flip, shuffle_batch_size=config.batch_size)
