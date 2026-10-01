"""CAMP/DAC inference primitives; no model loader, launcher or scientific imports.

The future caller supplies the strict, completed independent model, its native
runtime and transform, real B=1 reference arrays, and serial/resource admission.
These primitives alone cannot establish a completed efficiency experiment.
"""
from dataclasses import dataclass
import ast
import hashlib
from pathlib import Path

EXECUTION = Path(__file__).resolve().parents[2]
SOURCES = {
    'CAMP': ('camp_independent_evaluation_v3/run_evaluation.py',
             '81724bf96c01bb030efc1e2b10b3ebcd5a92935b975f729174a2677c11b8fc19',
             'camp_preparation/run_camp_author_evaluation.py',
             'cd26c3d4fc68f084e2c3fa4cbb772f80ee311cf5952851af976109bd5203f1bd'),
    'DAC': ('dac_independent_evaluation_v2/run_evaluation.py',
            '300714f02b21b3f038bb6364a31f80250ac7bfce771c1ced2ee5b8ab455710f8',
            'dac_preparation/run_dac_author_evaluation.py',
            'f8de2675234011077f4b0455ea2732daab288a625a95138dc5bdf388727633c8'),
}
COMPONENT_PATH = EXECUTION / 'external_efficiency_preparation/corrected_v1/measurement_components.py'
COMPONENT_SHA = 'a967746f177de58b2d45e910d96063b6e55bbc42675dc692c4798acaf0f6546f'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def verify_source_recipe(method):
    require(method in SOURCES, 'Only CAMP and DAC independent models are covered')
    name, expected, helper_name, helper_expected = SOURCES[method]
    path, helper = EXECUTION / name, EXECUTION / helper_name
    raw, helper_raw = path.read_bytes(), helper.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, 'Frozen encoding source changed')
    require(hashlib.sha256(helper_raw).hexdigest() == helper_expected, 'Frozen transform source changed')
    require(digest(COMPONENT_PATH) == COMPONENT_SHA, 'Frozen measurement helper changed')
    tree = ast.parse(raw.decode('utf-8-sig'))
    encode = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'encode_seed')
    expected_amp = ast.parse("with torch.autocast('cuda',dtype=torch.float16):\n descriptor=F.normalize(model(batch)[-2],dim=-1)").body[0]
    require(sum(ast.dump(n) == ast.dump(expected_amp) for n in ast.walk(encode)) == 1,
            'Original FP16 normalization/feature selection block changed')
    expected_transfer = ast.parse('values=descriptor.to(torch.float32).cpu().numpy()').body[0]
    require(sum(ast.dump(n) == ast.dump(expected_transfer) for n in ast.walk(encode)) == 1,
            'Original FP32 conversion/CPU transfer order changed')
    transform = next(n for n in ast.parse(helper_raw.decode('utf-8-sig')).body
                     if isinstance(n, ast.FunctionDef) and n.name == 'make_validation_transform')
    return {'method': method, 'encoder_path': str(path), 'encoder_sha256': expected,
            'transform_path': str(helper), 'transform_sha256': helper_expected,
            'transform_ast_sha256': hashlib.sha256(ast.dump(transform).encode()).hexdigest(),
            'measurement_components_sha256': COMPONENT_SHA,
            'source_verified_only': True, 'numerical_parity_executed': False}


@dataclass
class Operations:
    """Dependencies are injected only by a future admitted scientific worker."""
    method: str
    runtime: object
    cv2: object
    functional: object
    model: object
    transform: object
    components: object

    def forward_gpu(self, batch):
        t = self.runtime.torch
        # Preserve the official no_grad context even when the shared timer
        # wraps its operation in inference_mode. Do not silently change modes.
        with t.inference_mode(False), t.no_grad(), t.autocast('cuda', dtype=t.float16):
            return self.model(batch)[-2]

    def descriptor_gpu(self, batch):
        t = self.runtime.torch
        with t.inference_mode(False), t.no_grad(), t.autocast('cuda', dtype=t.float16):
            return self.functional.normalize(self.model(batch)[-2], dim=-1)

    def descriptor_cpu(self, batch):
        descriptor = self.descriptor_gpu(batch)
        return descriptor.to(self.runtime.torch.float32).cpu().numpy()

    def cpu_image(self, path):
        np, cv = self.runtime.numpy, self.cv2
        raw = Path(path).read_bytes()
        decoded = cv.imdecode(np.frombuffer(raw, dtype=np.uint8), cv.IMREAD_COLOR)
        require(decoded is not None, 'Native OpenCV image decode failed')
        # Original INTER_LINEAR_EXACT/Albumentations transform is supplied by
        # the caller from the pinned helper; no PIL/BICUBIC substitution.
        image = self.transform(image=cv.cvtColor(decoded, cv.COLOR_BGR2RGB))['image']
        return self.runtime.torch.stack([image])

    def raw_descriptor_cpu(self, path):
        # Match the original blocking .to call. No pinning, TTA or non_blocking
        # option is added to the CAMP/DAC pipeline.
        batch = self.cpu_image(path).to('cuda:0')
        return self.descriptor_cpu(batch)


def validate_descriptor(ops, array):
    np = ops.runtime.numpy
    require(array.shape == (1, 1024) and array.dtype == np.dtype('float32'),
            'Expected one native 1024-dimensional CPU FP32 descriptor')
    require(bool(np.isfinite(array).all()), 'Nonfinite descriptor')
    require(float(np.max(np.abs(np.linalg.norm(array, axis=1)-1))) <= 2e-3,
            'Descriptor violates original normalization check')


def compare_arrays(ops, actual, reference, *, exact, scope):
    try:
        validate_descriptor(ops, actual)
        validate_descriptor(ops, reference)
    except Exception as cause:
        error = ops.components.MeasurementError('Native descriptor validation failed')
        error.evidence = {'scope': scope, 'validation_error': str(cause), 'used_as_exact_gate': exact}
        error.actual_descriptor_array = actual.copy()
        error.expected_descriptor_array = reference.copy()
        raise error from cause
    np = ops.runtime.numpy
    evidence = {'scope': scope, 'exact_array_equal': bool(np.array_equal(actual, reference)),
                'maximum_absolute_difference': float(np.max(np.abs(actual-reference))),
                'different_elements': int(np.count_nonzero(actual != reference)),
                'used_as_exact_gate': exact}
    if exact and not evidence['exact_array_equal']:
        error = ops.components.MeasurementError('Native B=1 descriptor parity failed')
        error.evidence = evidence
        error.actual_descriptor_array = actual.copy()
        error.expected_descriptor_array = reference.copy()
        raise error
    return evidence


def measurement_metadata(record):
    flags = dict(record['runtime_flags'])
    flags.pop('native_formal_autocast', None)
    flags.pop('native_clip_autocast', None)
    flags.update(native_autocast='CUDA float16, including normalization', native_flip_tta=False)
    return {**record, 'inference_mode': False, 'gradient_context': 'native torch.no_grad',
            'shared_timer_outer_inference_mode': True, 'runtime_flags': flags}


def measure_sample(ops, image_path, reference_b1, *, completed_batch_descriptor=None):
    """Measure a real future sample; return arrays for caller-owned persistence.

    reference_b1 must come from the original independently executed B=1 path.
    Native batch-16 versus B=1 differences remain diagnostics, not tolerances
    replacing the exact B=1 gate. Full-gallery and ranking are caller duties.
    """
    source_before = verify_source_recipe(ops.method)
    path = Path(image_path).resolve(strict=True)
    image_sha = digest(path)
    t, c, runtime = ops.runtime.torch, ops.components, ops.runtime
    require(runtime.device.type == 'cuda' and runtime.device.index == 0, 'Native CUDA device 0 required')
    require(not ops.model.training and all(p.dtype == t.float32 for p in ops.model.parameters()),
            'Expected the actual complete native eval model with FP32 parameters')
    require(t.get_num_threads() == 1 and ops.cv2.getNumThreads() == 1, 'Native CPU thread settings differ')
    require(t.backends.cudnn.benchmark and not t.backends.cudnn.deterministic,
            'Native evaluator cuDNN settings differ')
    require(not t.is_grad_enabled() and not t.is_inference_mode_enabled(),
            'Caller must use original no_grad context, outside inference_mode')
    batch = ops.cpu_image(path).to('cuda:0')
    actual = ops.descriptor_cpu(batch)
    parity = compare_arrays(ops, actual, reference_b1, exact=True, scope='adapter B=1 versus original B=1')
    batch_diagnostic = None
    if completed_batch_descriptor is not None:
        batch_diagnostic = compare_arrays(ops, actual, completed_batch_descriptor, exact=False,
                                          scope='B=1 versus completed native batch; diagnostic only')
    residents = {'independent_native_model': ops.model}
    trace = c.trace_parameters_and_partial_macs(runtime, ops.model, lambda: ops.forward_gpu(batch))
    forward = c.measure_operation(runtime, lambda: ops.forward_gpu(batch), clock='cuda_event',
        scope='resident B=1 GPU image -> one complete native forward -> selected unnormalized GPU feature; excludes normalization, CPU transfer and decode',
        resident_models=residents)
    descriptor = c.measure_operation(runtime, lambda: ops.descriptor_cpu(batch), clock='synchronized_wall',
        scope='B=1 GPU image -> one native forward -> FP16 normalization -> FP32 cast -> CPU descriptor',
        resident_models=residents)
    del batch
    raw = c.measure_operation(runtime, lambda: ops.raw_descriptor_cpu(path), clock='synchronized_wall',
        scope='warm-file B=1 read -> OpenCV decode/RGB -> native 384 transform -> blocking H2D -> native forward/normalization -> CPU FP32 descriptor; excludes gallery ranking/model loading',
        resident_models=residents)
    raw_array = ops.raw_descriptor_cpu(path)
    raw_parity = compare_arrays(ops, raw_array, reference_b1, exact=True, scope='raw-file B=1 versus original B=1')
    require(digest(path) == image_sha and verify_source_recipe(ops.method) == source_before,
            'Input image or source changed during measurements')
    result = {'method': ops.method, 'source': source_before, 'input_path': str(path), 'input_sha256': image_sha,
        'forward_count_per_image': 1, 'native_amp': True, 'flip_tta': False,
        'gpu_forward': measurement_metadata(forward),
        'gpu_input_to_cpu_descriptor': measurement_metadata(descriptor),
        'raw_file_to_cpu_descriptor': measurement_metadata(raw),
        'original_B1_parity': parity, 'raw_B1_parity': raw_parity,
        'native_batch_diagnostic': batch_diagnostic,
        'whole_model_parameters': c.parameter_inventory(ops.model, optimization_role='complete independently trained model; original requires_grad flags retained'),
        'observed_parameter_owner_and_partial_module_macs': trace,
        'MAC_label': 'Conv2d/Linear module MACs (partial); one actual native forward',
        'full_gallery_metrics_recomputed_here': False, 'ranking_measured': False,
        'full_t6_complete': False, 'manuscript_result': False,
        'required_caller_checks': 'strict complete checkpoint; exact source/environment/transform; membership and B1 provenance; all predecessors/process exits; release/resources/GPU lock; immutable results/failure arrays'}
    return result, {'actual_B1': actual.copy(), 'raw_B1': raw_array.copy(),
                    'reference_B1': reference_b1.copy(),
                    'native_batch': None if completed_batch_descriptor is None else completed_batch_descriptor.copy()}
