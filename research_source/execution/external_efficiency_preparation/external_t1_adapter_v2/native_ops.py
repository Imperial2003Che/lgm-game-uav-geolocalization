"""Injected-runtime native descriptor/measurement interfaces for all seven T1 slots.

No scientific import occurs in this module. Outputs are computed from the loaded
native model; no timing, memory or descriptor default can substitute for a run.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

import bindings as b

@dataclass
class NativeContext:
    runtime: object
    components: object
    official: object
    model: object
    transform: object
    binding: dict
    identity: dict

    @property
    def family(self):
        return self.binding['row']['framework']

def precision_state(context):
    t = context.runtime.torch
    return {'native_amp': False, 'cuda_autocast_enabled': bool(t.is_autocast_enabled('cuda')),
        'cpu_autocast_enabled': bool(t.is_autocast_enabled('cpu')),
        'float32_matmul_precision': t.get_float32_matmul_precision(),
        'cuda_matmul_allow_tf32': bool(t.backends.cuda.matmul.allow_tf32),
        'cudnn_allow_tf32': bool(t.backends.cudnn.allow_tf32),
        'cudnn_benchmark': bool(t.backends.cudnn.benchmark),
        'cudnn_deterministic': bool(t.backends.cudnn.deterministic),
        'deterministic_algorithms': bool(t.are_deterministic_algorithms_enabled()),
        'deterministic_warn_only': bool(t.is_deterministic_algorithms_warn_only_enabled()),
        'tensor_parameter_dtype': str(next(context.model.parameters()).dtype)}

def require_native(context, images=None):
    k, t, r = b.common(), context.runtime.torch, context.runtime
    context.components._require_cuda(r)
    k.require(not context.model.training and not t.is_grad_enabled(), 'Native encoding requires eval + inference_mode')
    k.require(not t.is_autocast_enabled('cuda') and not t.is_autocast_enabled('cpu'),
              'T1 original inference has AMP disabled; inherited autocast is forbidden')
    expected = context.identity['native_precision_after_load']
    k.require(precision_state(context) == expected, 'Native precision/runtime flags changed after model loading')
    if images is not None:
        size = b.SIZES[context.binding['row']['config_id']]
        k.require(images.dtype == t.float32 and images.device == r.device and
                  images.ndim == 4 and tuple(images.shape[1:]) == (3, *size),
                  'Images must be original-size FP32 tensors on the explicit CUDA device')

def forward_pair(context, images, role):
    """GPU image -> raw original and mirrored native outputs, exactly two forwards."""
    b.role_kind(role)
    require_native(context, images)
    t, model = context.runtime.torch, context.model
    if context.family == 'qdfl':
        original = model(images)
        mirrored = model(t.flip(images, dims=(3,)))
    else:
        original = context.official._view_output(model, images, role)
        mirrored = context.official._view_output(model, t.flip(images, dims=(3,)), role)
    b.common().require(isinstance(original, t.Tensor) and isinstance(mirrored, t.Tensor), 'Native outputs are not tensors')
    b.common().require(not original.requires_grad and not mirrored.requires_grad, 'Native output retained an autograd graph')
    return original, mirrored

def native_descriptor(context, images, role):
    """GPU image -> actual native normalized CPU FP32 descriptor matrix.

    QDFL: CPU(original)/norm + CPU(raw mirror), then CPU normalize.
    MCCG: GPU(original + mirror), original sqrt(parts) normalize, then D2H.
    """
    original, mirrored = forward_pair(context, images, role)
    if context.family == 'qdfl':
        cpu = context.official.qdfl_postprocess(original, mirrored)
    else:
        cpu = context.official.mccg_postprocess(original + mirrored).cpu()
    np = context.runtime.numpy
    value = np.ascontiguousarray(cpu.numpy(), dtype=np.float32)
    b.common().require(value.ndim == 2 and value.shape[0] == images.shape[0] and np.isfinite(value).all(),
                       'Native descriptor is incomplete/nonfinite')
    return value

def raw_image_descriptor(context, image_path, role):
    """Raw file -> decode/RGB/native transform -> pin/H2D -> native CPU descriptor.

    The PIL class is taken from the already loaded real native environment, not
    generated imagery. The transform is the original official evaluator's object.
    """
    require_native(context)
    image_module = context.identity['_PIL_Image_module']
    with image_module.open(Path(image_path)) as source:
        rgb = source.convert('RGB')
    try:
        cpu = context.transform(rgb).unsqueeze(0)
        # Mirrors the official DataLoader's pinned-memory H2D boundary. Here the
        # pinning cost is included in the raw single-query pipeline measurement.
        images = cpu.pin_memory().to(device=context.runtime.device, non_blocking=True)
        return native_descriptor(context, images, role)
    finally:
        rgb.close()

def immutable_runtime_evidence(context):
    return {key: value for key, value in context.identity.items() if not key.startswith('_')}

def official_single_batch(context, images_cpu, role):
    """Independent call into frozen official extraction, not this adapter loop."""
    t = context.runtime.torch
    class OneBatch:
        dataset = tuple(range(images_cpu.shape[0]))
        def __iter__(self):
            yield images_cpu, t.arange(images_cpu.shape[0], dtype=t.int64)
    if context.family == 'qdfl':
        return context.official.extract_qdfl_descriptors(context.model, OneBatch(), context.runtime.device,
                                                        horizontal_flip=True)
    return context.official.extract_mccg_descriptors(context.model, OneBatch(), context.runtime.device, role)

def descriptor_parity(context, observed, expected, scope):
    np = context.runtime.numpy
    same_shape = observed.shape == expected.shape
    evidence = {'scope': scope, 'policy': 'exact array equality; no tolerance relaxation',
        'observed_shape': list(observed.shape), 'expected_shape': list(expected.shape),
        'observed_dtype': str(observed.dtype), 'expected_dtype': str(expected.dtype),
        'passed': bool(same_shape and observed.dtype == expected.dtype and np.array_equal(observed, expected))}
    if same_shape:
        evidence.update(max_abs_difference=float(np.abs(observed - expected).max()),
                        different_element_count=int(np.count_nonzero(observed != expected)))
    if not evidence['passed']:
        error = context.components.MeasurementError('Actual native descriptor differs from frozen official extractor')
        error.evidence = evidence
        # Independent CPU-array copies are intentionally outside JSON evidence.
        # The caller persists both on failure even when measure_sample never returns.
        error.actual_descriptor_array = observed.copy()
        error.expected_descriptor_array = expected.copy()
        raise error
    return evidence

def clean_measurement_metadata(context, measured):
    # Shared helpers were written for the primary method and include two descriptive
    # AMP labels. Remove those inapplicable labels rather than misreport T1 as FP16.
    flags = dict(measured['runtime_flags'])
    flags.pop('native_formal_autocast', None)
    flags.pop('native_clip_autocast', None)
    flags.update(precision_state(context))
    return {**measured, 'runtime_flags': flags}

def mccg_shared_route_proof(context, images, role):
    """Observe actual both-forward traffic through one shared model_1 instance."""
    if context.family != 'mccg':
        return {'status': 'not_applicable_qdfl_single_input_model'}
    model = context.model
    b.common().require(hasattr(model, 'model_1') and not hasattr(model, 'model_2'),
                       'Expected MCCG two_view_net with only shared model_1')
    seen = []
    handle = model.model_1.register_forward_pre_hook(lambda owner, args: seen.append(id(owner)))
    try:
        context.components._checked_call(context.runtime, lambda: forward_pair(context, images, role))
    finally:
        handle.remove()
    b.common().require(seen == [id(model.model_1), id(model.model_1)], 'MCCG branch sharing/forward count changed')
    return {'role': role, 'view_kind': b.role_kind(role), 'actual_shared_model_1_id': id(model.model_1),
        'observed_original_and_mirror_owner_ids': seen,
        'parameter_inventory_counts_one_model_object': True,
        'the_other_view_role_must_be_measured_separately': True}

def measure_sample(context, image_path, role, *, expected_official_descriptor=None):
    """Real B=1 measurements; caller owns immutable output and failure persistence.

    A successful sample cannot establish full-gallery accuracy or a complete T6.
    An optional descriptor from completed official batch extraction is compared
    exactly and can fail due to batch-shape differences; it is never substituted.
    """
    k, r, c = b.common(), context.runtime, context.components
    b.role_kind(role)
    path = Path(image_path).resolve(strict=True)
    source_before = k.record(path)
    k.gpu_idle({os.getpid()})
    image_module = context.identity['_PIL_Image_module']
    with image_module.open(path) as image:
        rgb = image.convert('RGB')
    try:
        cpu = context.transform(rgb).unsqueeze(0).pin_memory()
    finally:
        rgb.close()
    images = cpu.to(device=r.device, non_blocking=True)
    residents = {'native_t1_model': context.model}
    original = official_single_batch(context, cpu, role)
    observed = c._checked_call(r, lambda: native_descriptor(context, images, role))
    parity = descriptor_parity(context, observed, original, 'new B=1 adapter against original B=1 official extractor')
    batch_parity = None
    if expected_official_descriptor is not None:
        batch_parity = descriptor_parity(context, observed, expected_official_descriptor,
                                        'B=1 adapter against caller-provided actual completed official descriptor')
    shared = mccg_shared_route_proof(context, images, role)
    trace = c.trace_parameters_and_partial_macs(r, context.model, lambda: forward_pair(context, images, role))
    gpu = c.measure_operation(r, lambda: forward_pair(context, images, role), clock='cuda_event',
        scope='B=1 resident FP32 image -> native original forward + GPU horizontal flip + mirrored forward; excludes normalization, CPU transfers, decode and preprocessing',
        resident_models=residents)
    host = c.measure_operation(r, lambda: native_descriptor(context, images, role), clock='synchronized_wall',
        scope='B=1 GPU input -> both native forwards -> exact official normalization and final CPU FP32 descriptor; QDFL CPU normalization and both D2H transfers included',
        resident_models=residents)
    # Input tensors above are explicitly freed before timing the raw path.
    del images, cpu
    raw = c.measure_operation(r, lambda: raw_image_descriptor(context, path, role), clock='synchronized_wall',
        scope='B=1 raw file -> decode/RGB -> original transform -> pinned CPU tensor -> H2D -> two native forwards -> official postprocess -> CPU FP32 descriptor; excludes gallery ranking and model loading',
        resident_models=residents)
    raw_descriptor = c._checked_call(r, lambda: raw_image_descriptor(context, path, role))
    raw_parity = descriptor_parity(context, raw_descriptor, original, 'raw pipeline against original B=1 official extractor')
    k.verify_record(source_before)
    k.gpu_idle({os.getpid()})
    result = {'run_id': context.binding['row']['run_id'], 'method': context.binding['row']['method'],
        'framework': context.family, 'role': role, 'input': source_before, 'runtime': immutable_runtime_evidence(context),
        'checkpoint': context.binding['checkpoint'], 'native_amp': False, 'forward_count_per_image': 2,
        'gpu_forward_pair': clean_measurement_metadata(context, gpu),
        'gpu_input_to_cpu_descriptor': clean_measurement_metadata(context, host),
        'raw_file_to_cpu_descriptor': clean_measurement_metadata(context, raw),
        'descriptor': c._descriptor_evidence(r, observed), 'original_extractor_parity': parity,
        'completed_batch_descriptor_parity': batch_parity, 'raw_pipeline_parity': raw_parity,
        'whole_model_parameters': c.parameter_inventory(context.model, optimization_role='independently trained T1 model; native requires_grad flags retained'),
        'observed_parameter_owner_and_partial_module_macs': trace, 'shared_view_routing': shared,
        'parameter_activity_label': 'observed direct module owners; not complete active-parameter coverage',
        'MAC_label': 'Conv2d/Linear module MACs (partial), includes both forwards',
        'uncovered_operations': ['attention QK/AV', 'fused/functional projections', 'CycleFC deform_conv2d',
            'CCR einsum and other functional operations', 'normalization, pooling, activation and elementwise operations'],
        'native_ranking_score_type': 'squared_l2' if context.family == 'qdfl' else 'inner_product',
        'ranking_measured': False, 'full_gallery_metrics_recomputed_here': False,
        'training_domain': 'University-1652', 'SUES200_role': 'zero-shot transfer, no target-domain training',
        'full_t6_complete': False, 'manuscript_result': False}
    return result, observed, raw_descriptor

def encode_official_view(context, view, role):
    """Actual complete-view native extractor for future full-gallery integration.

    Uses the frozen evaluation batch size and workers=0 for this analysis process.
    The original QDFL evaluations used four workers; input order/math remain the
    original source implementation. MCCG already used zero workers.
    """
    from torch.utils.data import DataLoader
    b.role_kind(role)
    loader = DataLoader(context.official.FrozenPathDataset(view, context.transform),
        batch_size=b.BATCHES[context.binding['row']['config_id']], shuffle=False, num_workers=0,
        pin_memory=True, drop_last=False, persistent_workers=False)
    if context.family == 'qdfl':
        return context.official.extract_qdfl_descriptors(context.model, loader, context.runtime.device, horizontal_flip=True)
    return context.official.extract_mccg_descriptors(context.model, loader, context.runtime.device, role)
