"""Real one-fit / ten-task worker. Scientific imports occur only after admission.

This source has not been scientifically executed. No generated descriptor or
default timing is a substitute for actual input/model/evaluation evidence.
"""
from __future__ import annotations
import gc
import importlib
import math
import os
from pathlib import Path

import driver_contract as d

METRICS = ('r_at_1', 'r_at_5', 'r_at_10', 'r_at_20', 'official_trapezoid_mAP', 'MRR')
COUNTS = ('queries', 'gallery', 'query_identities', 'gallery_identities', 'descriptor_dimension')
VIEW_ORDER = (('university1652', 'query_drone'), ('university1652', 'gallery_satellite'),
    ('university1652', 'query_satellite'), ('university1652', 'gallery_drone'),
    ('sues200', 'satellite_all'), ('sues200', 'drone_150_all'), ('sues200', 'drone_200_all'),
    ('sues200', 'drone_250_all'), ('sues200', 'drone_300_all'))

def compare_metrics(observed, expected, *, rtol, atol):
    """Same fixed six-field threshold as frozen completed-evaluation validation."""
    k = d.common()
    differences = {name: {'observed': observed[name], 'expected': expected[name],
        'passed': math.isfinite(float(observed[name])) and math.isclose(float(observed[name]),
             float(expected[name]), rel_tol=rtol, abs_tol=atol)} for name in METRICS}
    count_equal = {name: observed[name] == expected[name] for name in COUNTS}
    return {'metrics': differences, 'counts_equal': count_equal, 'rtol': rtol, 'atol': atol,
        'passed': all(x['passed'] for x in differences.values()) and all(count_equal.values())}

def scan_inputs(ctx, original):
    b, _, loader = d.adapters()
    args = loader.evaluator_arguments(ctx.binding, ctx.official)
    university, ui = original.scan_university1652_official_test(args.test_root, hash_contents=True)
    original.validate_university1652_test_inventory(ui)
    sues, si, test_ids = original.scan_sues200_official_test(args.sues_root, args.sues_manifest, hash_contents=True)
    original.validate_sues200_test_inventory(si)
    inventory = {'university1652': ui, 'sues200': si}
    original.validate_test_inventory_gate(args.test_inventory_gate, test_root=args.test_root,
        sues_root=args.sues_root, sues_manifest=args.sues_manifest,
        all_fits_gate_path=args.all_fits_gate, inventory=inventory)
    return {'university1652': university, 'sues200': sues}, tuple(test_ids), inventory

def save_array(np, path, value):
    with Path(path).open('xb') as stream:
        np.save(stream, value, allow_pickle=False)
    return d.common().record(path)

def save_arrays(np, path, arrays):
    with Path(path).open('xb') as stream:
        np.savez_compressed(stream, **arrays)
    return d.common().record(path)

def extract_views(ctx, original, views, output, completed):
    b, n, _ = d.adapters()
    np, k = ctx.runtime.numpy, d.common()
    paths, reports = {}, []
    declared = completed['descriptor_fingerprints']
    k.require(set(declared) == {dataset + '/' + role for dataset, role in VIEW_ORDER}, 'Completed view registry differs')
    for dataset, role in VIEW_ORDER:
        key, view = dataset + '/' + role, views[dataset][role]
        matrix = n.encode_official_view(ctx, view, role)
        k.require(matrix.dtype == np.float32 and matrix.ndim == 2 and matrix.shape[0] == len(view.paths)
                  and bool(np.isfinite(matrix).all()), 'Native full-view descriptor shape/type/finite check failed')
        path = output / (dataset + '__' + role + '.npy')
        artifact = save_array(np, path, matrix)
        rows = save_arrays(np, output / (dataset + '__' + role + '__rows.npz'),
                           {'paths': view.relative_paths, 'labels': view.labels})
        observed = {'shape': list(matrix.shape), 'dtype': str(matrix.dtype), 'sha256': original.descriptor_sha256(matrix)}
        proof = {'view': key, 'actual': observed, 'declared': declared[key], 'passed': observed == declared[key],
            'actual_array': artifact, 'actual_rows': rows, 'native_batch_size': b.BATCHES[ctx.binding['row']['config_id']],
            'workers': 0, 'original_qdfl_workers': 4, 'original_mccg_workers': 0}
        k.write_new(output / (dataset + '__' + role + '__parity.json'), proof)
        if not proof['passed']:
            error = ctx.components.MeasurementError('Full native batch descriptor fingerprint differs from completed official evaluation')
            error.evidence = proof  # The actual full array was closed and persisted above.
            raise error
        paths[key] = path
        reports.append(proof)
        del matrix
        gc.collect()
    return paths, reports

def task_specs(test_ids, views, np):
    """Select official 80 SUES query IDs; all 200 gallery IDs remain present."""
    ids = set(test_ids)
    yield ('university1652_drone_to_satellite', 'university1652', 'query_drone', 'gallery_satellite', None,
           'official test/query_drone -> test/gallery_satellite')
    yield ('university1652_satellite_to_drone', 'university1652', 'query_satellite', 'gallery_drone', None,
           'official test/query_satellite -> test/gallery_drone')
    satellite = views['sues200']['satellite_all']
    sat_indices = np.flatnonzero(np.asarray([x in ids for x in satellite.labels.tolist()], dtype=np.bool_))
    d.common().require(len(sat_indices) == 80, 'SUES satellite query count differs')
    for altitude in (150, 200, 250, 300):
        role = 'drone_' + str(altitude) + '_all'
        drone = views['sues200'][role]
        drone_indices = np.flatnonzero(np.asarray([x in ids for x in drone.labels.tolist()], dtype=np.bool_))
        d.common().require(len(drone_indices) == 4000, 'SUES UAV query count differs')
        yield (f'sues200_uav_{altitude}m_to_satellite', 'sues200', role, 'satellite_all', drone_indices,
               'official 80 test IDs as query; all 200 satellite IDs in gallery')
        yield (f'sues200_satellite_to_uav_{altitude}m', 'sues200', 'satellite_all', role, sat_indices,
               f'official 80 test IDs as query; all 200 {altitude}m UAV IDs in gallery')

def make_task(ctx, original, spec, views, paths):
    name, dataset, qrole, grole, indices, protocol = spec
    np = ctx.runtime.numpy
    qview, gview = views[dataset][qrole], views[dataset][grole]
    qmap = np.load(paths[dataset + '/' + qrole], mmap_mode='r', allow_pickle=False)
    gmap = np.load(paths[dataset + '/' + grole], mmap_mode='r', allow_pickle=False)
    subset = slice(None) if indices is None else indices
    task = original.DescriptorTask(name=name, protocol=protocol,
        query_descriptors=qmap[subset], query_labels=qview.labels[subset], query_paths=qview.relative_paths[subset],
        gallery_descriptors=gmap, gallery_labels=gview.labels, gallery_paths=gview.relative_paths,
        score_type='squared_l2' if ctx.family == 'qdfl' else 'inner_product')
    first_source = 0 if indices is None else int(indices[0])
    return task, (qmap, gmap), qview.paths[first_source], qrole

def close_maps(maps):
    for value in maps:
        value._mmap.close()

def native_full_ranking(np, descriptor, gallery, gallery_squared_norm, score_type):
    """Actual CPU NumPy native score + complete stable ranking, as official code.

    All gallery descriptors/norms are precomputed gallery state. No gallery
    encoding or per-query AP bookkeeping is charged to online query latency.
    """
    dot_products = descriptor @ gallery.T
    if score_type == 'squared_l2':
        query_squared_norm = np.sum(descriptor * descriptor, axis=1, dtype=np.float32)
        squared_distance = query_squared_norm[:, None] + gallery_squared_norm[None, :] - np.float32(2.0) * dot_products
        scores = -squared_distance
    elif score_type == 'inner_product':
        scores = dot_products
    else:
        raise ValueError('Unsupported original native ranking score type')
    return np.argsort(-scores, axis=1, kind='stable')

def measure_task_sample(ctx, original, task, image_path, role, output):
    _, n, _ = d.adapters()
    np, k, c, r = ctx.runtime.numpy, d.common(), ctx.components, ctx.runtime
    # Exact original B=1 vs actual native batch comparison is not relaxed.
    measured, observed, raw = n.measure_sample(ctx, image_path, role,
        expected_official_descriptor=task.query_descriptors[:1])
    save_array(np, output / 'actual_b1_descriptor.npy', observed)
    save_array(np, output / 'actual_raw_descriptor.npy', raw)
    gallery = task.gallery_descriptors
    gallery_norm = np.sum(gallery * gallery, axis=1, dtype=np.float32)
    def operation():
        descriptor = n.raw_image_descriptor(ctx, image_path, role)
        return native_full_ranking(np, descriptor, gallery, gallery_norm, task.score_type)
    expected_rank = native_full_ranking(np, raw, gallery, gallery_norm, task.score_type)
    actual_rank = c._checked_call(r, operation)
    save_array(np, output / 'native_expected_full_ranking.npy', expected_rank)
    save_array(np, output / 'raw_actual_full_ranking_before.npy', actual_rank)
    k.require(bool(np.array_equal(actual_rank, expected_rank)), 'Actual raw-query complete ranking differs before timing')
    raw_ranking = c.measure_operation(r, operation, clock='synchronized_wall',
        scope='B=1 raw image file -> RGB/native transform/pin/H2D -> two native FP32 forwards -> official CPU descriptor -> native NumPy FP32 scores against entire official gallery -> full stable argsort; gallery descriptors/norms precomputed; excludes model loading and AP bookkeeping',
        resident_models={'native_t1_model': ctx.model})
    after_rank = c._checked_call(r, operation)
    save_array(np, output / 'raw_actual_full_ranking_after.npy', after_rank)
    k.require(bool(np.array_equal(after_rank, expected_rank)), 'Actual raw-query complete ranking differs after timing')
    # Re-evaluate the real online descriptor through the independent official
    # function too, preserving its true output instead of copying batch metrics.
    online_task = original.DescriptorTask(name=task.name, protocol=task.protocol,
        query_descriptors=raw, query_labels=task.query_labels[:1], query_paths=task.query_paths[:1],
        gallery_descriptors=gallery, gallery_labels=task.gallery_labels, gallery_paths=task.gallery_paths,
        score_type=task.score_type)
    online_metrics, online_arrays = original.evaluate_descriptor_task(online_task, chunk_size=128)
    save_arrays(np, output / 'actual_online_one_query_arrays.npz', online_arrays)
    k.require(int(online_arrays['top1_gallery_indices'][0]) == int(expected_rank[0, 0]),
              'Native timed ranking differs from official online evaluator top1')
    k.verify_record(measured['input'])
    measured.update({'raw_file_to_complete_native_ranking': n.clean_measurement_metadata(ctx, raw_ranking),
        'ranking_measured': True, 'full_gallery_metrics_recomputed_here': True,
        'gallery_rows': int(gallery.shape[0]), 'gallery_state': 'actual full native batch descriptors mmap + precomputed FP32 squared norms',
        'full_t6_complete': False, 'online_one_query_metrics': online_metrics,
        'sampling_rule': 'first query in each frozen official task order; not dataset mean query latency',
        'raw_file_cache_state': 'warmed operating-system cache after actual 20 warmup queries; not cold disk latency',
        'full_dataset_online_accuracy_measured': False})
    return measured

def run_slot(plan, binding, output):
    """Caller has already admitted exact release/plan/PIDs/environment/resources."""
    b, n, loader = d.adapters()
    k = d.common()
    ctx = loader.load_native_slot(binding, device_index=plan['device_index'])
    np = ctx.runtime.numpy
    original = importlib.import_module('external_baselines.official_descriptor_evaluation')
    k.require(Path(original.__file__).resolve() == b.EXT / 'official_descriptor_evaluation.py', 'Wrong official ranking module')
    k.write_new(output / 'runtime_identity.json', n.immutable_runtime_evidence(ctx))
    views, test_ids, inventory = scan_inputs(ctx, original)
    k.write_new(output / 'input_inventory_before.json', inventory)
    completed = k.read(Path(binding['evaluation_dir']) / 'metrics.json')
    expected_tasks = {item['task']: item for item in completed['tasks']}
    k.require(set(expected_tasks) == set(b.EXPECTED_TASKS), 'Completed task set changed')
    descriptors = output / 'descriptors'
    descriptors.mkdir(exist_ok=False)
    paths, fingerprints = extract_views(ctx, original, views, descriptors, completed)
    specs = list(task_specs(test_ids, views, np))
    k.require([x[0] for x in specs] == list(b.EXPECTED_TASKS), 'Official task order changed')
    full_results = []
    # Preserve all complete-gallery evidence before starting strict online-B1
    # parity. An online mismatch must not erase the already-computed batch proof.
    for spec in specs:
        case = output / spec[0]
        case.mkdir(exist_ok=False)
        task, maps, _, _ = make_task(ctx, original, spec, views, paths)
        try:
            metrics, arrays = original.evaluate_descriptor_task(task, chunk_size=128)
            save_arrays(np, case / 'actual_full_gallery_per_query.npz', arrays)
            parity = compare_metrics(metrics, expected_tasks[task.name],
                rtol=plan['full_gallery_metric_rtol'], atol=plan['full_gallery_metric_atol'])
            result = {'task': task.name, 'actual_full_gallery_metrics': metrics, 'completed_reference': expected_tasks[task.name],
                'comparison': parity, 'actual_descriptor_fingerprints_exact': True, 'status': 'passed' if parity['passed'] else 'failed'}
            k.write_new(case / 'full_gallery_metrics.json', result)
            k.require(parity['passed'], 'Full official gallery metrics differ from completed evaluation')
            full_results.append(result)
            del arrays, task
        finally:
            close_maps(maps)
            gc.collect()
    k.write_new(output / 'all_ten_full_gallery_metrics.json', {'task_count': len(full_results), 'tasks': full_results,
        'full_t6_complete': False, 'manuscript_result': False})
    timings = []
    for spec in specs:
        task, maps, image_path, role = make_task(ctx, original, spec, views, paths)
        sample = output / spec[0] / 'sample'
        sample.mkdir(exist_ok=False)
        try:
            k.write_new(sample / 'selected_query.json', {'task': task.name, 'role': role,
                'image': k.record(image_path), 'query_relative_path': str(task.query_paths[0]),
                'query_label': str(task.query_labels[0]), 'full_gallery_rows': int(task.gallery_descriptors.shape[0])})
            timing = measure_task_sample(ctx, original, task, image_path, role, sample)
            k.write_new(sample / 'measurements.json', timing)
            timings.append({'task': task.name, 'measurement': k.record(sample / 'measurements.json')})
            del task
        except BaseException as error:
            # v2 arrays are copied out before measure_sample returns on failure.
            d.failure_artifacts(sample, error)
            raise
        finally:
            close_maps(maps)
            gc.collect()
    _, _, inventory_after = scan_inputs(ctx, original)
    k.write_new(output / 'input_inventory_after.json', inventory_after)
    k.require(inventory_after == inventory, 'Official input bytes changed during execution')
    b.verify_binding(binding)
    k.gpu_idle({os.getpid()})
    d.verify_sources()
    return {'status': 'completed_external_t1_slot_only', 'run_id': binding['row']['run_id'],
        'checkpoint': binding['checkpoint'], 'task_count': 10, 'full_gallery_results': full_results,
        'descriptor_fingerprints': fingerprints, 'timing_results': timings,
        'scientific_execution_performed': True, 'full_t6_complete': False, 'manuscript_result': False,
        'coverage': 'one actual fit, ten complete official gallery tasks; four latency scopes per selected query',
        'not_implemented': ['seven-slot automatic serial scheduling', 'merged primary/external T6 table',
            'CAMP/DAC efficiency rows', 'full-operation FLOPs', 'full-dataset online B=1 accuracy',
            'cold-disk latency', 'measured host RAM peak'],
        'closed_scientific_artifacts': [k.record(path) for path in sorted(output.rglob('*')) if path.is_file()],
        'parent_logs_excluded': True}
