"""Real, lazy-runtime T6 measurement components; no scientific imports here.

These functions are deliberately not an experiment launcher. The separate CLI
refuses execution until an independently reviewed serial/registration driver
exists. Runtime objects must be the source-pinned real libraries and models.
"""
from dataclasses import dataclass
import math
from pathlib import Path
import statistics
import time
from typing import Any, Callable, Mapping

ENCODING_WARMUP = 20
ENCODING_REPETITIONS = 100
PROBABILITY_PARITY = "exact float16-cache values after the frozen float32 validation; no tolerance relaxation"


class MeasurementError(RuntimeError):
    pass


class ProbabilityParityError(MeasurementError):
    def __init__(self, evidence):
        super().__init__("Live CLIP probabilities differ from the registered cached query")
        self.evidence = evidence


@dataclass(frozen=True)
class Runtime:
    """Injected real dependencies; this module never imports or constructs them."""
    torch: Any
    numpy: Any
    core: Any
    clip_generator: Any
    device: Any


def linear_quantile(values, q):
    if not values or not 0 <= q <= 1:
        raise MeasurementError("Invalid quantile input")
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize_samples(samples):
    values = [float(x) for x in samples]
    if not values or any(not math.isfinite(x) or x <= 0 for x in values):
        raise MeasurementError("Measured latency must be finite and positive")
    q1, q3 = linear_quantile(values, .25), linear_quantile(values, .75)
    return {"unit": "ms", "raw_samples_ms": values, "repetitions": len(values),
            "median": statistics.median(values), "q1": q1, "q3": q3,
            "IQR": q3-q1, "minimum": min(values), "maximum": max(values),
            "mean": statistics.mean(values),
            "sample_sd": statistics.stdev(values) if len(values) > 1 else None}


def _require_cuda(runtime):
    t = runtime.torch
    if runtime.device.type != "cuda" or not t.cuda.is_available():
        raise MeasurementError("Real CUDA runtime required; no CPU timing substitution")
    if runtime.device.index is None or t.cuda.current_device() != runtime.device.index:
        raise MeasurementError("CUDA events must use the explicitly selected measurement device")


def _require_resident_models(resident_models, required):
    if not resident_models:
        raise MeasurementError("Declare the actual resident models")
    identities = [id(model) for model in resident_models.values()]
    if len(identities) != len(set(identities)):
        raise MeasurementError("Declare each shared resident model object once")
    if any(id(model) not in identities for model in required):
        raise MeasurementError("Resident declaration omits an actual measured model")


def _checked_call(runtime, operation):
    t = runtime.torch
    with t.inference_mode():
        if t.is_grad_enabled():
            raise MeasurementError("Inference timing has autograd enabled")
        result = operation()
        if result is None:
            raise MeasurementError("Measured operation returned no real result")
        def check(value):
            if isinstance(value, t.Tensor) and value.requires_grad:
                raise MeasurementError("Measured tensor retained an autograd graph")
            if isinstance(value, (tuple, list)):
                for item in value:
                    check(item)
            elif isinstance(value, dict):
                for item in value.values():
                    check(item)
        check(result)
        return result


def measure_operation(runtime, operation: Callable, *, clock: str, scope: str,
                      resident_models: Mapping[str, Any]):
    """Measure real samples and a separate warmed, resident-inclusive peak.

    No averaged/default memory substitutes. The memory difference is relative
    to this process's actual live allocation, not an activation-only claim.
    """
    _require_cuda(runtime)
    if clock not in {"cuda_event", "synchronized_wall"}:
        raise MeasurementError("Explicit CUDA-event or synchronized-wall clock required")
    _require_resident_models(resident_models, ())
    for model in resident_models.values():
        if model.training:
            raise MeasurementError("Every resident model must be in eval mode")
    t = runtime.torch
    for _ in range(ENCODING_WARMUP):
        value = _checked_call(runtime, operation)
        del value
    t.cuda.synchronize(runtime.device)
    baseline_allocated = int(t.cuda.memory_allocated(runtime.device))
    baseline_reserved = int(t.cuda.memory_reserved(runtime.device))
    t.cuda.reset_peak_memory_stats(runtime.device)
    value = _checked_call(runtime, operation)
    t.cuda.synchronize(runtime.device)
    peak_allocated = int(t.cuda.max_memory_allocated(runtime.device))
    peak_reserved = int(t.cuda.max_memory_reserved(runtime.device))
    del value
    samples = []
    for _ in range(ENCODING_REPETITIONS):
        if clock == "cuda_event":
            start, stop = t.cuda.Event(enable_timing=True), t.cuda.Event(enable_timing=True)
            start.record()
            value = _checked_call(runtime, operation)
            stop.record()
            stop.synchronize()
            elapsed = float(start.elapsed_time(stop))
        else:
            t.cuda.synchronize(runtime.device)
            start = time.perf_counter_ns()
            value = _checked_call(runtime, operation)
            t.cuda.synchronize(runtime.device)
            elapsed = (time.perf_counter_ns() - start) / 1_000_000.0
        del value
        samples.append(elapsed)
    return {"scope": scope, "clock": clock, "warmup_repetitions": ENCODING_WARMUP,
            "timing": summarize_samples(samples), "inference_mode": True,
            "memory": {"unit": "bytes", "baseline_allocated": baseline_allocated,
                       "baseline_reserved": baseline_reserved, "peak_allocated": peak_allocated,
                       "peak_reserved": peak_reserved,
                       "peak_allocated_minus_baseline": peak_allocated-baseline_allocated,
                       "peak_reserved_minus_baseline": peak_reserved-baseline_reserved,
                       "definition": "warmed current-process total peak including live models, inputs and allocator state",
                       "declared_resident_models": list(resident_models)},
            "runtime_flags": runtime_flags(runtime)}


def runtime_flags(runtime):
    t = runtime.torch
    return {"torch": t.__version__, "numpy": runtime.numpy.__version__,
            "cuda_runtime": t.version.cuda, "device": str(runtime.device),
            "explicit_device_index": runtime.device.index,
            "current_cuda_device_index": int(t.cuda.current_device()),
            "float32_matmul_precision": t.get_float32_matmul_precision(),
            "cuda_matmul_allow_tf32": bool(t.backends.cuda.matmul.allow_tf32),
            "cudnn_allow_tf32": bool(t.backends.cudnn.allow_tf32),
            "cudnn_benchmark": bool(t.backends.cudnn.benchmark),
            "cudnn_deterministic": bool(t.backends.cudnn.deterministic),
            "deterministic_algorithms": bool(t.are_deterministic_algorithms_enabled()),
            "native_formal_autocast": "CUDA float16 via frozen core.amp_context",
            "native_clip_autocast": "CUDA float16 via frozen generator helper"}


def parameter_inventory(model, *, optimization_role):
    """Deduplicate shared Parameter objects; don't equate requires_grad to use."""
    unique, names = {}, {}
    for name, parameter in model.named_parameters(remove_duplicate=False):
        identity = id(parameter)
        names.setdefault(identity, []).append(name)
        unique[identity] = parameter
    rows = [{"names": names[key], "elements": int(p.numel()), "dtype": str(p.dtype),
             "bytes": int(p.numel()*p.element_size()), "requires_grad_flag": bool(p.requires_grad)}
            for key, p in unique.items()]
    buffers = {}
    for name, value in model.named_buffers(remove_duplicate=False):
        buffers.setdefault(id(value), {"name": name, "elements": int(value.numel()),
                           "dtype": str(value.dtype), "bytes": int(value.numel()*value.element_size())})
    return {"whole_model_parameter_elements": sum(r["elements"] for r in rows),
            "whole_model_parameter_bytes": sum(r["bytes"] for r in rows),
            "requires_grad_flag_elements": sum(r["elements"] for r in rows if r["requires_grad_flag"]),
            "optimization_role": optimization_role,
            "deduplication": "Parameter object identity; alias names retained",
            "parameters": rows, "buffers": list(buffers.values()),
            "buffer_bytes": sum(x["bytes"] for x in buffers.values())}


def trace_parameters_and_partial_macs(runtime, model, operation, *, formal=False):
    """Real forward hooks, intentionally partial operation coverage.

    For the frozen FormalRetrievalModel, assert exactly all parameters except
    its training similarity logit_scale are owned by actually called modules.
    For CLIP, report observed direct-owner parameters, not an unsupported claim
    that a hook proves every parameter of arbitrary functional code is used.
    """
    t = runtime.torch
    handles, active, called, mac_rows = [], set(), [], {}
    all_names = {id(p): name for name, p in model.named_parameters()}
    sizes = {id(p): int(p.numel()) for p in model.parameters()}
    def make_hook(name):
        def hook(module, inputs, output):
            if t.is_grad_enabled():
                raise MeasurementError("Trace was not in inference mode")
            called.append(name)
            for parameter in module.parameters(recurse=False):
                active.add(id(parameter))
            if isinstance(module, t.nn.Conv2d):
                if not isinstance(output, t.Tensor):
                    raise MeasurementError("Conv2d output is not a Tensor")
                count = output.numel()*(module.in_channels//module.groups)*math.prod(module.kernel_size)
            elif isinstance(module, t.nn.Linear):
                if not isinstance(output, t.Tensor):
                    raise MeasurementError("Linear output is not a Tensor")
                count = output.numel()*module.in_features
            else:
                return
            row = mac_rows.setdefault(name, {"module": name, "calls": 0, "MACs": 0})
            row["calls"] += 1
            row["MACs"] += int(count)
        return hook
    for name, module in model.named_modules():
        handles.append(module.register_forward_hook(make_hook(name)))
    try:
        output = _checked_call(runtime, operation)
        del output
    finally:
        for handle in handles:
            handle.remove()
    if not active or not mac_rows:
        raise MeasurementError("No actual parameter/MAC trace was observed")
    if formal:
        expected = {key for key, name in all_names.items() if name != "logit_scale"}
        if active != expected:
            raise MeasurementError("Frozen formal encode active parameter set changed")
    return {"observed_direct_owner_parameter_elements": sum(sizes[key] for key in active),
            "observed_parameter_names": sorted(all_names[key] for key in active),
            "excluded_whole_model_parameter_names": sorted(all_names[key] for key in all_names.keys()-active),
            "formal_expected_set_verified": formal, "called_module_names": called,
            "partial_MACs": {"label": "Conv2d/Linear module MACs (partial)",
                "count_for_this_single_image_operation": sum(x["MACs"] for x in mac_rows.values()),
                "module_rows": list(mac_rows.values()),
                "total_FLOPs_available": False,
                "excluded_operations": ["functional or fused projections", "attention QK and AV matmuls",
                    "einsum", "functional convolutions/deform sampling", "normalization", "pooling",
                    "activation", "elementwise operations", "memory transfers", "image preprocessing"]}}


def _encode(runtime, model, image_gpu, content_gpu, style_gpu):
    t = runtime.torch
    if t.is_grad_enabled() or model.training:
        raise MeasurementError("Native encode requires eval + inference_mode")
    with runtime.core.amp_context(runtime.device, True):
        value = model.encode_image(image_gpu, content_gpu, style_gpu)
    if value.requires_grad or value.ndim != 2 or value.shape[0] != 1:
        raise MeasurementError("Expected one real graph-free descriptor")
    return value


def _descriptor_evidence(runtime, descriptor):
    n = runtime.numpy
    values = n.asarray(descriptor)
    if values.ndim != 2 or values.shape[0] != 1 or values.dtype != n.float32 or not n.isfinite(values).all():
        raise MeasurementError("Final descriptor must be finite CPU float32 [1,D]")
    return {"shape": list(values.shape), "dtype": str(values.dtype),
            "bytes_per_image": int(values.nbytes), "l2_norm": float(n.linalg.norm(values[0]))}


def measure_formal_component(runtime, model, image_gpu, content_gpu, style_gpu, *, resident_models):
    _require_resident_models(resident_models, (model,))
    model.eval()
    operation = lambda: _encode(runtime, model, image_gpu, content_gpu, style_gpu)
    value = _checked_call(runtime, operation)
    descriptor = value.float().cpu().numpy()
    evidence = _descriptor_evidence(runtime, descriptor)
    del value
    trace = trace_parameters_and_partial_macs(runtime, model, operation, formal=True)
    measured = measure_operation(runtime, operation, clock="cuda_event",
        scope="batch1 cached-evidence formal encode: GPU image+probabilities to normalized GPU descriptor; excludes CLIP and all input/output transfers",
        resident_models=resident_models)
    return {"component": "formal_cached_gpu_encode", "measurement": measured,
            "descriptor": evidence, "parameters": parameter_inventory(model, optimization_role="trained retrieval model"),
            "trace": trace, "manuscript_result": False, "full_t6_complete": False}


def prepare_clip_prototypes(runtime, clip_model, processor):
    """Measure the one-time 11+10 text prototype creation, not 21 image passes."""
    clip_model.eval()
    g, t = runtime.clip_generator, runtime.torch
    _require_cuda(runtime)
    t.cuda.synchronize(runtime.device)
    started = time.perf_counter_ns()
    with t.inference_mode():
        content = g._encode_text_prototypes(clip_model, processor, g.CONTENT_CANDIDATES,
                                          runtime.device, t.float16, t)
        style = g._encode_text_prototypes(clip_model, processor, g.STYLE_CANDIDATES,
                                        runtime.device, t.float16, t)
        logit_scale = float(clip_model.logit_scale.detach().float().exp().clamp(max=100.0).cpu())
    t.cuda.synchronize(runtime.device)
    elapsed_ms = (time.perf_counter_ns()-started)/1_000_000.0
    if content.shape[0] != 11 or style.shape[0] != 10 or elapsed_ms <= 0:
        raise MeasurementError("Native CLIP prototype preparation changed")
    evidence = {"scope": "one-time tokenizer + text H2D + original text encoder + L2 normalize + scale extraction",
                "clock": "synchronized_wall", "one_observed_setup_ms": elapsed_ms,
                "timing_repetitions": 1, "content_shape": list(content.shape), "style_shape": list(style.shape),
                "prototype_bytes": int(content.numel()*content.element_size()+style.numel()*style.element_size()),
                "logit_scale": logit_scale, "text_tower_remains_resident": True,
                "model_loading_included": False}
    return (content, style, logit_scale), evidence


def _live_probabilities(runtime, image, clip_model, processor, prototypes):
    content, style, scale = prototypes
    g, t = runtime.clip_generator, runtime.torch
    return g._infer_probabilities([image], clip_model, processor, content, style,
                                  scale, runtime.device, t.float16, t)


def probability_parity(runtime, observed, cached_content, cached_style):
    """Fixed exact check after the SAME native float16->float32 validator.

    The frozen validator validates row sums; it does not renormalize them.
    Failure evidence contains actual values and differences for later review.
    """
    n = runtime.numpy
    result, evidence = [], {"policy": PROBABILITY_PARITY, "comparison_scope": "one selected query only", "families": {}}
    for name, width, live, cached in zip(("content_probs", "style_probs"), (11,10), observed, (cached_content,cached_style)):
        if n.asarray(live).dtype != n.float16:
            raise MeasurementError("Original CLIP generator did not return float16 cache values")
        values = runtime.core._validate_probability_array(live, 1, width, name)
        expected = n.asarray(cached, dtype=n.float32).reshape(1,width)
        runtime.core._validate_probability_array(expected, 1, width, name)
        diff = n.abs(values-expected)
        exact = bool(n.array_equal(values, expected))
        evidence["families"][name] = {"exact": exact, "live_float32": values.tolist(),
            "cached_float32": expected.tolist(), "max_abs_difference": float(diff.max()),
            "different_element_count": int(n.count_nonzero(diff))}
        result.append(values)
    evidence["passed"] = all(x["exact"] for x in evidence["families"].values())
    if not evidence["passed"]:
        raise ProbabilityParityError(evidence)
    return tuple(result), evidence


def measure_clip_image_evidence(runtime, image_path, clip_model, processor, prototypes, *, resident_models):
    _require_resident_models(resident_models, (clip_model,))
    clip_model.eval()
    def operation():
        image = runtime.core.load_rgb(Path(image_path))
        try:
            return _live_probabilities(runtime, image, clip_model, processor, prototypes)
        finally:
            image.close()
    trace = trace_parameters_and_partial_macs(runtime, clip_model, operation)
    measured = measure_operation(runtime, operation, clock="synchronized_wall",
        scope="raw image path to original CLIP float16 content/style CPU arrays: read/decode, CLIP processor, H2D, one image forward, normalization, 21 prototype similarities, two softmax, D2H and float16 quantization; excludes one-time text setup",
        resident_models=resident_models)
    return {"component": "clip_image_evidence_from_raw_image", "measurement": measured,
            "parameters": parameter_inventory(clip_model, optimization_role="frozen pretrained CLIP; no optimization during retrieval training"),
            "trace": trace, "manuscript_result": False, "full_t6_complete": False}


def measure_raw_query(runtime, model, image_path, eval_transform, cached_content, cached_style,
                      *, resident_models, clip_model=None, processor=None, prototypes=None):
    """Real raw-image -> CPU FP32 descriptor. This is NOT image-to-ranked-results.

    Full uses the original CLIP generator including its FP16 CPU cache boundary;
    no optimized all-GPU shortcut is silently substituted for this native path.
    """
    t, n = runtime.torch, runtime.numpy
    if model.variant not in {"visual", "full"}:
        raise MeasurementError("Only the registered visual/full main variants are implemented")
    required = (model, clip_model) if model.variant == "full" else (model,)
    _require_resident_models(resident_models, required)
    model.eval()
    if model.variant == "full":
        if clip_model is None or processor is None or prototypes is None:
            raise MeasurementError("Full raw query requires real CLIP and fixed prototypes")
        clip_model.eval()
    def operation(check_parity=False):
        image = runtime.core.load_rgb(Path(image_path))
        try:
            if model.variant == "full":
                observed = _live_probabilities(runtime, image, clip_model, processor, prototypes)
                if check_parity:
                    (content, style), proof = probability_parity(runtime, observed, cached_content, cached_style)
                else:
                    content = runtime.core._validate_probability_array(observed[0],1,11,"content_probs")
                    style = runtime.core._validate_probability_array(observed[1],1,10,"style_probs")
                    proof = None
            else:
                content = n.asarray(cached_content, dtype=n.float32).reshape(1,11)
                style = n.asarray(cached_style, dtype=n.float32).reshape(1,10)
                proof = {"status": "not_applicable_visual_ignores_semantic_inputs"}
            image_gpu = eval_transform(image).unsqueeze(0).to(runtime.device)
            c = t.from_numpy(content).to(runtime.device)
            s = t.from_numpy(style).to(runtime.device)
            descriptor = _encode(runtime, model, image_gpu, c, s).float().cpu().numpy()
            return descriptor, proof
        finally:
            image.close()
    first, parity_before = _checked_call(runtime, lambda: operation(True))
    descriptor_evidence = _descriptor_evidence(runtime, first)
    measured = measure_operation(runtime, operation, clock="synchronized_wall",
        scope="raw image file to normalized CPU float32 descriptor; includes read/decode, original CLIP evidence for full, native preprocessing, transfers, fusion, final D2H; excludes gallery search and text setup",
        resident_models=resident_models)
    last, parity_after = _checked_call(runtime, lambda: operation(True))
    if not n.array_equal(first, last):
        raise MeasurementError("Repeated raw-query descriptor changed under fixed native inference")
    return {"component": "raw_query_to_cpu_descriptor", "variant": model.variant,
            "measurement": measured, "descriptor": descriptor_evidence,
            "cached_probability_parity_before": parity_before, "cached_probability_parity_after": parity_after,
            "accuracy_scope": "selected query only; no dataset-wide online accuracy equivalence claimed",
            "image_to_ranked_results_measured": False, "manuscript_result": False, "full_t6_complete": False}
