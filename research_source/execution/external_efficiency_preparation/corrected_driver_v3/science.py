"""Actual scientific worker, imported only after the driver's release/resource gates.

There are no scientific imports at module scope. This file has not been run.
"""
from __future__ import annotations

import gc
import importlib.util
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import contract as k

def save_npy(np, path, value):
    with Path(path).open('xb') as f:
        np.save(f, value, allow_pickle=False)
    return k.record(path)

def save_npz(np, path, arrays):
    with Path(path).open('xb') as f:
        np.savez_compressed(f, **arrays)
    return k.record(path)

def load_components():
    path = k.COMPONENTS / 'measurement_components.py'
    k.require(k.sha(path) == k.COMPONENT_SHA, 'Measurement component bytes changed')
    spec = importlib.util.spec_from_file_location('pinned_corrected_components', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def sample_source(record, store):
    return {'image': k.record(record.absolute_path), 'relative_path': record.relative_path,
        'label': record.label, 'view': record.view, 'altitude': record.altitude,
        'evidence_index': record.evidence_index,
        'content_cache_float32': store.content_probs[record.evidence_index].tolist(),
        'style_cache_float32': store.style_probs[record.evidence_index].tolist(),
        'selection': 'first query in frozen official task order, chosen before observing timing'}

def real_inputs(r, record, store, transform):
    image = r.core.load_rgb(record.absolute_path)
    try:
        image_gpu = transform(image).unsqueeze(0).to(r.device)
    finally:
        image.close()
    content = r.torch.from_numpy(store.content_probs[record.evidence_index]).unsqueeze(0).to(r.device)
    style = r.torch.from_numpy(store.style_probs[record.evidence_index]).unsqueeze(0).to(r.device)
    return image_gpu, content, style

def raw_descriptor(r, components, model, query, store, transform, *,
                   clip_model=None, processor=None, prototypes=None, check_parity=False):
    """Real raw path -> CPU FP32 [1,D], using the same operations as corrected_v1.

    check_parity is performed outside timing. The timed pipeline still computes
    actual fresh probabilities, never substitutes the cached row for full.
    """
    np, t = r.numpy, r.torch
    image = r.core.load_rgb(query.absolute_path)
    try:
        if model.variant == 'full':
            observed = components._live_probabilities(r, image, clip_model, processor, prototypes)
            if check_parity:
                (content, style), parity = components.probability_parity(r, observed,
                    store.content_probs[query.evidence_index], store.style_probs[query.evidence_index])
            else:
                content = r.core._validate_probability_array(observed[0], 1, 11, 'content_probs')
                style = r.core._validate_probability_array(observed[1], 1, 10, 'style_probs')
                parity = None
        else:
            content = np.asarray(store.content_probs[query.evidence_index], dtype=np.float32).reshape(1, 11)
            style = np.asarray(store.style_probs[query.evidence_index], dtype=np.float32).reshape(1, 10)
            parity = {'status': 'not_applicable_visual'}
        image_gpu = transform(image).unsqueeze(0).to(r.device)
        value = components._encode(r, model, image_gpu, t.from_numpy(content).to(r.device),
                                   t.from_numpy(style).to(r.device)).float().cpu().numpy()
        return value, parity
    finally:
        image.close()

def ranking_timing(r, components, query_gpu, gallery_gpu, residents, scope):
    """FP32 full stable ranking, 5 warmups + 20 raw samples, without D2H.

    All-query timing is throughput of an entire query matrix, not query latency.
    The single-query row explicitly uses one preencoded query and full gallery.
    """
    t = r.torch
    components._require_cuda(r)
    components._require_resident_models(residents, ())
    k.require(query_gpu.dtype == t.float32 and gallery_gpu.dtype == t.float32,
              'Ranking must use actual FP32 stored descriptors')
    free_bytes, total_bytes = t.cuda.mem_get_info(r.device)
    elements = len(query_gpu) * len(gallery_gpu)
    explicit_bytes = 12 * elements  # FP32 score matrix + int64 result indices.
    sort_workspace_margin = 16 * elements + 256 * 1024**2
    k.require(free_bytes >= explicit_bytes + sort_workspace_margin,
              'Insufficient current CUDA headroom for full rank matrix and explicit unprofiled workspace margin')
    def op():
        return t.argsort(query_gpu @ gallery_gpu.T, dim=1, descending=True, stable=True)
    for _ in range(5):
        value = components._checked_call(r, op)
        del value
    t.cuda.synchronize(r.device)
    baseline_a, baseline_r = t.cuda.memory_allocated(r.device), t.cuda.memory_reserved(r.device)
    t.cuda.reset_peak_memory_stats(r.device)
    actual = components._checked_call(r, op)
    t.cuda.synchronize(r.device)
    peak_a, peak_r = t.cuda.max_memory_allocated(r.device), t.cuda.max_memory_reserved(r.device)
    # This actual rank matrix is retained on CPU and saved, not replaced by a mock hash.
    ranks_cpu = actual.cpu().numpy()
    del actual
    samples = []
    for _ in range(20):
        start, stop = t.cuda.Event(enable_timing=True), t.cuda.Event(enable_timing=True)
        start.record(t.cuda.current_stream(r.device))
        value = components._checked_call(r, op)
        stop.record(t.cuda.current_stream(r.device))
        stop.synchronize()
        samples.append(float(start.elapsed_time(stop)))
        del value
    summary = components.summarize_samples(samples)
    return {'scope': scope, 'clock': 'cuda_event', 'warmup_repetitions': 5, 'timing': summary,
        'queries': len(query_gpu), 'gallery': len(gallery_gpu),
        'matrix_queries_per_second': 1000.0 * len(query_gpu) / summary['median'],
        'index_dtype': 'float32', 'index_bytes': gallery_gpu.numel() * gallery_gpu.element_size(),
        'descriptor_dimensions': gallery_gpu.shape[1], 'inference_mode': True,
        'cuda_admission': {'free_bytes_observed': free_bytes, 'total_bytes_observed': total_bytes,
            'explicit_score_and_rank_bytes': explicit_bytes,
            'unprofiled_sort_workspace_margin_bytes': sort_workspace_margin,
            'margin_is_not_an_empirical_peak': True},
        'memory': {'baseline_allocated': baseline_a, 'baseline_reserved': baseline_r,
            'peak_allocated': peak_a, 'peak_reserved': peak_r,
            'peak_allocated_minus_baseline': peak_a - baseline_a,
            'definition': 'actual current-process CUDA total with models and both descriptor matrices resident',
            'declared_resident_models': list(residents)},
        'runtime_flags': components.runtime_flags(r)}, ranks_cpu

def load_clip(r, output):
    # This import can occur only inside the already gated, future scientific worker.
    import transformers
    from transformers import CLIPModel, CLIPProcessor
    clip = k.verify_snapshot()
    k.require(transformers.__version__ == '4.57.6', 'Frozen CLIP transformer version differs')
    model, info = CLIPModel.from_pretrained(clip['local_snapshot'], local_files_only=True,
        use_safetensors=False, output_loading_info=True)
    k.write_new(output / 'clip_loading_info.json', info)
    legacy = {'text_model.embeddings.position_ids', 'vision_model.embeddings.position_ids'}
    k.require(not info.get('missing_keys') and not info.get('mismatched_keys') and not info.get('error_msgs'),
              'CLIP learned-weight loading failed')
    k.require(set(info.get('unexpected_keys', [])) <= legacy, 'Unexpected CLIP learned weights')
    audit = k.read(k.HERE.parent / 'CLIP_OFFLINE_SOURCE_AUDIT_1721.json')
    expected = {x['name']: x for x in audit['checkpoint_archive']['tensor_metadata'] if x['name'] not in legacy}
    state = model.state_dict()
    k.require(set(state) == set(expected) and len(expected) == 398, 'CLIP learned state key set differs')
    for name, tensor in state.items():
        k.require(list(tensor.shape) == expected[name]['shape'] and tensor.dtype == r.torch.float32,
                  'CLIP learned-state shape/dtype changed: ' + name)
        k.require(bool(r.torch.isfinite(tensor).all()), 'Nonfinite CLIP learned weight: ' + name)
    for embeddings, width in ((model.text_model.embeddings, 77), (model.vision_model.embeddings, 50)):
        k.require(r.torch.equal(embeddings.position_ids.cpu(), r.torch.arange(width).reshape(1, width)),
                  'CLIP regenerated position buffer differs from source')
    processor = CLIPProcessor.from_pretrained(clip['local_snapshot'], local_files_only=True)
    k.require(type(processor.image_processor).__name__ == 'CLIPImageProcessor', 'CLIP image processor changed')
    k.require(type(processor.tokenizer).__name__ == 'CLIPTokenizerFast', 'CLIP tokenizer changed')
    k.require(type(model) is CLIPModel, 'Unexpected actual CLIP object identity')
    model.to(r.device).eval()
    # requires_grad flags remain the native preload flags. Frozen means it is not
    # optimized here; parameter inventory reports both meanings separately.
    k.write_new(output / 'clip_runtime_identity.json', {'class': type(model).__module__ + '.' + type(model).__name__,
        'object_id_in_this_process': id(model), 'learned_state_entries': len(state),
        'model_parameter_dtype': str(next(model.parameters()).dtype), 'source_revision': k.CLIP_REVISION,
        'source_snapshot': clip, 'config_name_or_path': model.config._name_or_path,
        'config_commit_hash_actual': getattr(model.config, '_commit_hash', None),
        'processor_class': type(processor.image_processor).__name__, 'tokenizer_class': type(processor.tokenizer).__name__,
        'transformers': transformers.__version__, 'transformers_file': transformers.__file__,
        'loading_info_artifact': k.record(output / 'clip_loading_info.json'),
        'actual_learned_shapes_finite_values_checked': True,
        'native_fp32_parameters_with_fp16_autocast': True})
    del state
    return model, processor

def verify_module_identity(module, relative_path):
    expected = (k.P / relative_path).resolve(strict=True)
    k.require(Path(module.__file__).resolve(strict=True) == expected, 'Imported a different scientific source: ' + relative_path)

def _run_case(plan, case_index, output):
    """Executable real scientific path. Caller MUST have completed worker gates."""
    import numpy as np
    import torch
    import torchvision
    import PIL
    sys.path.insert(0, str(k.P))
    from lgm_game_pytorch import formal_retrieval as core
    from lgm_game_pytorch import generate_clip_image_evidence as generator
    from experiments import aggregate_frozen_formal_results as aggregate
    from experiments import run_transactions_formal_efficiency as helpers
    for module, path in ((core, 'lgm_game_pytorch/formal_retrieval.py'),
                         (generator, 'lgm_game_pytorch/generate_clip_image_evidence.py'),
                         (aggregate, 'experiments/aggregate_frozen_formal_results.py'),
                         (helpers, 'experiments/run_transactions_formal_efficiency.py')):
        verify_module_identity(module, path)
    environment = k.PYTHON.parent.parent / 'Lib' / 'site-packages'
    for module in (np, torch, torchvision, PIL):
        k.require(Path(module.__file__).resolve().is_relative_to(environment.resolve()), 'Foreign scientific package imported')
    k.require(torch.cuda.is_available(), 'Actual CUDA unavailable')
    torch.cuda.set_device(plan['device_index'])
    device = torch.device('cuda', plan['device_index'])
    k.require(torch.cuda.current_device() == device.index, 'Actual CUDA event device differs')
    core.seed_everything(20260730)
    components = load_components()
    runtime = components.Runtime(torch, np, core, generator, device)
    case = plan['cases'][case_index]
    selected = [s for s in helpers.registered_specs(k.D)
                if s.dataset == case['dataset'] and s.variant == case['variant']]
    k.require(len(selected) == 1, 'Four-case registry selection is not unique')
    # Recomputes official per-query arrays and provenance before loading the checkpoint.
    valid = aggregate.validate_completed_run(selected[0], k.D, k.CORE_SHA)
    k.require(valid.checkpoint_sha256 == case['checkpoint']['sha256'], 'Validated checkpoint differs from plan')
    k.write_new(output / 'completed_source_validation.json', {'identifier': valid.spec.identifier,
        'checkpoint_sha256': valid.checkpoint_sha256, 'metrics_sha256': valid.metrics_sha256,
        'run_config_sha256': valid.run_config_sha256, 'input_artifacts': valid.input_artifacts,
        'protocol_membership_sha256': valid.protocol_membership_sha256,
        'scientific_validator': 'frozen aggregate.validate_completed_run', 'validated_utc': k.now()})
    model, config, checkpoint = helpers.load_model(valid, device)
    k.require(type(model) is core.FormalRetrievalModel and model.variant == case['variant'], 'Actual model identity differs')
    k.require(config['backbone'] == 'resnet18' and config['embed_dim'] == 512,
              'Primary model architecture changed')
    del checkpoint
    gc.collect()
    args = SimpleNamespace(delivery_root=k.D, university_root=Path(k.DATA_ROOTS['university1652']),
                           sues_root=Path(k.DATA_ROOTS['sues200']))
    store, tasks, context = helpers.build_dataset_context(args, case['dataset'])
    k.require(len(tasks) == (3 if case['dataset'] == 'university1652' else 8), 'Official task count changed')
    k.require(context['protocol_membership_sha256'] == valid.protocol_membership_sha256, 'Official task membership differs')
    k.write_new(output / 'actual_runtime.json', {'pid': os.getpid(), 'python': sys.executable,
        'gpu': helpers.gpu_snapshot(device.index), 'flags': components.runtime_flags(runtime),
        'formal_class': type(model).__module__ + '.' + type(model).__name__, 'formal_object_id': id(model),
        'model_config': config, 'context': context,
        'source_checkpoint': case['checkpoint'], 'actual_loaded_strict': True,
        'full_t6_complete': False, 'manuscript_result': False})
    _, transform = core.build_transforms(int(config['resize_size']), int(config['image_size']))
    unique = {record.relative_path.casefold(): record for task in tasks for record in (*task.query, *task.gallery)}
    records = [unique[key] for key in sorted(unique)]
    # Actual input image bytes are pinned before encoding, then rechecked at end.
    images = [{'relative_path': r.relative_path, 'label': r.label, 'view': r.view,
        'altitude': r.altitude, 'evidence_index': r.evidence_index, 'file': k.record(r.absolute_path)} for r in records]
    k.write_new(output / 'official_image_inventory.json', images)
    encoded = core.encode_records(model, records, store, transform, device,
        batch_size=plan['descriptor_batch_size'], workers=plan['descriptor_workers'], amp_enabled=True, seed=1)
    k.require(set(encoded) == set(unique), 'Descriptor coverage differs from all official query/gallery images')
    vectors = np.stack([encoded[r.relative_path.casefold()] for r in records])
    k.require(vectors.dtype == np.float32 and np.isfinite(vectors).all(), 'Invalid real descriptors')
    save_npy(np, output / 'all_official_descriptors_float32.npy', vectors)
    k.write_new(output / 'descriptor_rows.json', [r.relative_path for r in records])
    del vectors
    task_reports = []
    residents = {'formal_retrieval': model}
    for task in tasks:
        k.gpu_idle({os.getpid()})
        directory = output / task.name
        directory.mkdir(exist_ok=False)
        observed, arrays = core.rank_task(task, encoded, chunk_size=256)
        reported = helpers._reported_metrics(valid, task.name)
        k.write_new(directory / 'cached_official_metric_comparison.json', {'observed': observed, 'reported': reported,
            'scope': 'all official queries and gallery under original cached-evidence protocol',
            'relative_tolerance': 2e-6, 'absolute_tolerance': 2e-7})
        save_npz(np, directory / 'cached_official_per_query_arrays.npz', arrays)
        helpers._verify_full_gallery_metrics(observed, reported, task.name)
        k.write_new(directory / 'source.json', {'query': sample_source(task.query[0], store),
            'query_order': [r.relative_path for r in task.query], 'gallery_order': [r.relative_path for r in task.gallery],
            'task_protocol': task.protocol, 'complete_cached_official_metrics_passed': True})
        image_gpu, content, style = real_inputs(runtime, task.query[0], store, transform)
        component = components.measure_formal_component(runtime, model, image_gpu, content, style, resident_models=residents)
        k.write_new(directory / 'cached_formal_component.json', component)
        del image_gpu, content, style
        qgpu = torch.from_numpy(np.stack([encoded[r.relative_path.casefold()] for r in task.query])).to(device)
        ggpu = torch.from_numpy(np.stack([encoded[r.relative_path.casefold()] for r in task.gallery])).to(device)
        for name, queries in (('all_queries', qgpu), ('one_query', qgpu[:1])):
            timing, ranks = ranking_timing(runtime, components, queries, ggpu, residents,
                'preencoded FP32 ' + name + ' matrix multiply + full stable argsort on GPU; excludes descriptor production and D2H')
            k.write_new(directory / ('cached_ranking_' + name + '.json'), timing)
            save_npy(np, directory / ('cached_gpu_ranks_' + name + '.npy'), ranks)
            # Keep GPU and official CPU rank differences visible; CPU official
            # metrics remain attached only to the CPU implementation actually used.
            reference_top1 = arrays['top1_gallery_indices'] if name == 'all_queries' else arrays['top1_gallery_indices'][:1]
            k.write_new(directory / ('cached_gpu_cpu_top1_' + name + '.json'), {
                'equal_count': int(np.count_nonzero(ranks[:, 0] == reference_top1)),
                'query_count': len(ranks), 'gpu_rank_does_not_inherit_cpu_accuracy': True})
            del ranks, queries
        del qgpu, ggpu, arrays
        task_reports.append({'task': task.name, 'queries': len(task.query), 'gallery': len(task.gallery),
                             'cached_official_metrics_reproduced': True})
    clip_model = processor = prototypes = None
    if case['variant'] == 'full':
        clip_model, processor = load_clip(runtime, output)
        residents['frozen_clip'] = clip_model
        prototypes, setup = components.prepare_clip_prototypes(runtime, clip_model, processor)
        k.write_new(output / 'clip_text_prototype_setup.json', setup)
        save_npy(np, output / 'clip_content_prototypes.npy', prototypes[0].float().cpu().numpy())
        save_npy(np, output / 'clip_style_prototypes.npy', prototypes[1].float().cpu().numpy())
    for task in tasks:
        directory = output / task.name
        query = task.query[0]
        k.gpu_idle({os.getpid()})
        if case['variant'] == 'full':
            clip_timing = components.measure_clip_image_evidence(runtime, query.absolute_path, clip_model,
                processor, prototypes, resident_models=residents)
            k.write_new(directory / 'clip_image_evidence.json', clip_timing)
        raw = components.measure_raw_query(runtime, model, query.absolute_path, transform,
            store.content_probs[query.evidence_index], store.style_probs[query.evidence_index],
            resident_models=residents, clip_model=clip_model, processor=processor, prototypes=prototypes)
        k.write_new(directory / 'raw_query_descriptor_timing.json', raw)
        def encode_raw(check=False):
            return raw_descriptor(runtime, components, model, query, store, transform,
                clip_model=clip_model, processor=processor, prototypes=prototypes, check_parity=check)
        descriptor, parity = components._checked_call(runtime, lambda: encode_raw(True))
        save_npy(np, directory / 'actual_online_query_descriptor.npy', descriptor)
        k.write_new(directory / 'actual_online_query_parity.json', parity)
        source_vector = encoded[query.relative_path.casefold()]
        k.write_new(directory / 'online_vs_cached_descriptor.json', {
            'array_equal': bool(np.array_equal(descriptor[0], source_vector)),
            'max_abs_difference': float(np.abs(descriptor[0] - source_vector).max()),
            'online_batch_size': 1, 'cached_protocol_descriptor_batch_size': 128,
            'probability_parity_policy_unchanged': True})
        # Copy the mapping, never overwrite original cached vectors/metrics.
        online = dict(encoded)
        online[query.relative_path.casefold()] = descriptor[0]
        one = core.RetrievalTask(task.name, (query,), task.gallery, task.protocol)
        online_metrics, online_arrays = core.rank_task(one, online, chunk_size=1)
        k.write_new(directory / 'online_one_query_official_cpu_metrics.json', {'scope':
            'one actual online query against original cached-protocol full gallery; not dataset-wide online accuracy',
            'metrics': online_metrics})
        save_npz(np, directory / 'online_one_query_official_cpu_arrays.npz', online_arrays)
        ggpu = torch.from_numpy(np.stack([encoded[r.relative_path.casefold()] for r in task.gallery])).to(device)
        def image_to_ranks():
            vector, _ = encode_raw(False)
            q = torch.from_numpy(vector).to(device)
            return torch.argsort(q @ ggpu.T, dim=1, descending=True, stable=True).cpu().numpy()
        actual_ranks = components._checked_call(runtime, image_to_ranks)
        save_npy(np, directory / 'actual_online_gpu_ranking.npy', actual_ranks)
        composed = components.measure_operation(runtime, image_to_ranks, clock='synchronized_wall',
            scope='raw query file -> real descriptor -> H2D FP32 descriptor -> full cached-gallery FP32 similarity -> stable argsort -> CPU rank indices; excludes one-time text/gallery setup',
            resident_models=residents)
        k.write_new(directory / 'raw_query_to_ranked_results_timing.json', {
            'measurement': composed, 'gallery_source': 'actual original cached-protocol descriptor matrix',
            'gallery_images': len(task.gallery), 'gallery_index_bytes': ggpu.numel() * ggpu.element_size(),
            'actual_gpu_top1_equals_actual_online_official_cpu_top1': bool(actual_ranks[0, 0] == online_arrays['top1_gallery_indices'][0]),
            'whole_dataset_online_accuracy_measured': False, 'full_t6_complete': False})
        last, final_parity = components._checked_call(runtime, lambda: encode_raw(True))
        k.require(np.array_equal(last, descriptor), 'Online query descriptor changed during composition timing')
        k.write_new(directory / 'after_timing_probability_parity.json', final_parity)
        del ggpu, descriptor, online, online_arrays, actual_ranks, last
    for image in images:
        k.verify_record(image['file'])
    for item in plan['cache_and_split']:
        k.verify_record(item)
    k.verify_record(case['checkpoint'])
    k.frozen_sources()
    if case['variant'] == 'full':
        k.verify_snapshot()
    k.gpu_idle({os.getpid()})
    outputs = k.closed_case_artifacts(output)
    return {'status': 'completed_primary_case_only', 'dataset': case['dataset'], 'variant': case['variant'],
        'tasks': task_reports, 'task_count': len(tasks), 'output_artifacts': outputs,
        'full_t6_complete': False, 'manuscript_result': False,
        'online_accuracy_scope': 'one first query per official task against cached gallery',
        'external_efficiency_rows_completed': 0, 'scientific_process_actual_pid': os.getpid(),
        'completed_utc': k.now()}

def run_case(plan, case_index, output):
    """Capture real runtime failure diagnostics without converting failure to data."""
    try:
        return _run_case(plan, case_index, output)
    except BaseException:
        torch_module = sys.modules.get('torch')
        if torch_module is not None:
            try:
                device = torch_module.device('cuda', plan['device_index'])
                if torch_module.cuda.is_initialized():
                    k.write_new(output / 'actual_cuda_at_failure.json', {
                        'allocated': torch_module.cuda.memory_allocated(device),
                        'reserved': torch_module.cuda.memory_reserved(device),
                        'peak_allocated': torch_module.cuda.max_memory_allocated(device),
                        'peak_reserved': torch_module.cuda.max_memory_reserved(device),
                        'free_and_total_bytes': list(torch_module.cuda.mem_get_info(device)),
                        'diagnostic_only_not_efficiency_result': True, 'utc': k.now()})
            except BaseException as diagnostic_error:
                k.write_new(output / 'cuda_failure_diagnostic_error.json', {'error': str(diagnostic_error)})
        raise
