"""Verify seven actual exited slots and collate their existing JSON/CSV evidence."""
from __future__ import annotations
import csv
import importlib.util
import math
from pathlib import Path
import statistics
import sys

import execution_contract as c

METRICS = ('r_at_1', 'r_at_5', 'r_at_10', 'r_at_20', 'official_trapezoid_mAP', 'MRR')
COUNTS = ('queries', 'gallery', 'query_identities', 'gallery_identities', 'descriptor_dimension')
SCOPES = ('gpu_forward_pair', 'gpu_input_to_cpu_descriptor', 'raw_file_to_cpu_descriptor', 'raw_file_to_complete_native_ranking')

def summary_function():
    _, k, b, _ = c.runtime_helpers()
    path = b.COMPONENTS / 'measurement_components.py'
    k.require(k.sha(path) == b.COMPONENT_SHA, 'Original timing summary source changed')
    spec = importlib.util.spec_from_file_location('external_t1_stdlib_timing_summary', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.summarize_samples

def verify_measurement(value, scope, summarize):
    _, k, _, _ = c.runtime_helpers()
    expected_clock = 'cuda_event' if scope == 'gpu_forward_pair' else 'synchronized_wall'
    k.require(value['clock'] == expected_clock and value['warmup_repetitions'] == 20 and value['inference_mode'] is True, 'Changed native timing scope/clock')
    timing = value['timing']
    samples = timing['raw_samples_ms']
    k.require(len(samples) == 100 and all(type(x) in (float, int) and math.isfinite(x) and x > 0 for x in samples), 'Missing actual hundred timing samples')
    k.require(summarize(samples) == timing, 'Timing summary differs from original recomputation')
    flags = value['runtime_flags']
    k.require(flags['native_amp'] is False and flags['cuda_autocast_enabled'] is False and flags['cpu_autocast_enabled'] is False, 'Native FP32/AMP scope changed')
    k.require(flags['explicit_device_index'] == flags['current_cuda_device_index'] == 0, 'Actual CUDA device differs')
    memory = value['memory']
    for key in ('baseline_allocated', 'baseline_reserved', 'peak_allocated', 'peak_reserved', 'peak_allocated_minus_baseline', 'peak_reserved_minus_baseline'):
        k.require(type(memory[key]) is int and memory[key] >= 0, 'Invalid actual allocator bytes')
    k.require(memory['peak_allocated'] - memory['baseline_allocated'] == memory['peak_allocated_minus_baseline'] and
              memory['peak_reserved'] - memory['baseline_reserved'] == memory['peak_reserved_minus_baseline'], 'Allocator differences inconsistent')
    return timing

def verify_slot(row, binding, plan_record, release_record):
    native, k, b, _ = c.runtime_helpers()
    k.require(row['status'] == 'completed' and type(row['launcher_exit_code']) is int and row['launcher_exit_code'] == 0 and
              type(row['worker_exit_code']) is int and row['worker_exit_code'] == 0, 'Slot launcher or actual worker did not exit0')
    k.require(row['run_id'] == binding['row']['run_id'], 'Wrong completed slot')
    for artifact in row['closed_control_artifacts']:
        k.verify_record(artifact)
    control = Path(row['control_directory']).resolve()
    expected_control = {control / name for name in ('request.json', 'launcher.json', 'worker_identity.json',
        'parent_observed.json', 'return_intent.json', 'stdout.log', 'stderr.log', 'lifecycle.json')}
    paths = [Path(item['path']).resolve() for item in row['closed_control_artifacts']]
    k.require(len(paths) == 8 and set(paths) == expected_control, 'Missing/duplicated actual closed control artifact')
    lifecycle, _ = c.bound(row['lifecycle']['path'], row['lifecycle'])
    k.require(Path(row['lifecycle']['path']) == control / 'lifecycle.json' and lifecycle['status'] == 'completed' and
        lifecycle['launcher_exit_code'] == row['launcher_exit_code'] == 0 and
        lifecycle['actual_worker_exit_code'] == row['worker_exit_code'] == 0 and
        lifecycle['actual_worker'] == row['worker_identity'] and lifecycle['native_result'] == row['native_result'] and
        lifecycle['retained_actual_handles_used'] is True, 'Actual lifecycle differs from completed slot row')
    request, _ = c.bound(control / 'request.json', lifecycle['request'])
    k.require(request['plan'] == plan_record and request['release'] == release_record and request['run_id'] == row['run_id'] and
              request['native_output'] == row['native_output'], 'Closed slot request differs from exact plan/release/run')
    handshake, _ = c.bound(control / 'worker_identity.json')
    k.require(handshake == row['worker_identity'], 'Recorded worker identity differs from actual closed handshake')
    result, result_record = c.bound(row['native_result']['path'], row['native_result'])
    output = Path(row['native_output']).resolve()
    k.require(Path(result_record['path']) == output / 'result.json' and output.parent == c.NATIVE / 'runs', 'Wrong native result location')
    k.require(result['status'] == 'completed_external_t1_slot_only' and result['run_id'] == row['run_id'] and
              result['task_count'] == 10 and result['full_t6_complete'] is False and result['manuscript_result'] is False and
              result['scientific_execution_performed'] is True, 'Native slot result incomplete/mislabelled')
    k.require(result['owner'] == row['worker_identity']['cim_identity'] and result['checkpoint'] == binding['checkpoint'], 'Native result identity/checkpoint differs')
    admission, _ = c.bound(result['admission']['path'], result['admission'])
    k.require(Path(result['admission']['path']) == output / 'admission.json' and admission['owner'] == result['owner'] and
              admission['plan'] == plan_record and admission['release'] == release_record, 'Native admission not bound to this exact launch')
    artifacts = result['closed_scientific_artifacts']
    actual_paths = {path.resolve() for path in (output / 'science').rglob('*') if path.is_file()}
    declared = [Path(item['path']).resolve() for item in artifacts]
    k.require(len(set(declared)) == len(declared) and set(declared) == actual_paths and all(p.is_relative_to(output / 'science') for p in declared), 'Scientific artifact set is incomplete/duplicated/outside slot')
    k.require(not any('failure' in p.name for p in declared), 'A failed scientific record remains in a supposedly completed slot')
    for item in artifacts:
        k.verify_record(item)
    k.require([x['task'] for x in result['full_gallery_results']] == list(b.EXPECTED_TASKS) and
              [x['task'] for x in result['timing_results']] == list(b.EXPECTED_TASKS), 'Exactly ten ordered task results/timings required')
    original = k.read(Path(binding['evaluation_dir']) / 'metrics.json')
    references = {x['task']: x for x in original['tasks']}
    summarize = summary_function()
    rows = []
    for full, timing_ref in zip(result['full_gallery_results'], result['timing_results']):
        task = full['task']
        metrics, reference = full['actual_full_gallery_metrics'], references[task]
        k.require(full['status'] == 'passed' and full['completed_reference'] == reference and full['actual_descriptor_fingerprints_exact'] is True, 'Full-gallery source/descriptor proof differs')
        k.require(all(metrics[key] == reference[key] for key in COUNTS), 'Actual full-gallery population differs')
        k.require(all(math.isfinite(float(metrics[key])) and math.isclose(float(metrics[key]), float(reference[key]), rel_tol=2e-6, abs_tol=2e-7) for key in METRICS), 'Actual six metrics fail original comparison')
        measurement_path = output / 'science' / task / 'sample' / 'measurements.json'
        k.require(Path(timing_ref['measurement']['path']) == measurement_path, 'Timing source path is not its task sample')
        measured, _ = c.bound(measurement_path, timing_ref['measurement'])
        k.require(measured['run_id'] == row['run_id'] and measured['checkpoint'] == binding['checkpoint'] and
                  measured['native_amp'] is False and measured['forward_count_per_image'] == 2 and
                  measured['ranking_measured'] is True and measured['gallery_rows'] == metrics['gallery'] and
                  measured['full_t6_complete'] is False and measured['full_dataset_online_accuracy_measured'] is False, 'Measured sample scope changed')
        k.require(measured['original_extractor_parity']['passed'] is True and measured['raw_pipeline_parity']['passed'] is True, 'Independent B1/native raw parity failed')
        k.require(measured['native_ranking_score_type'] == ('squared_l2' if binding['row']['framework'] == 'qdfl' else 'inner_product'), 'Native ranking score was substituted')
        k.verify_record(measured['input'])
        whole = measured['whole_model_parameters']
        trace = measured['observed_parameter_owner_and_partial_module_macs']
        partial = trace['partial_MACs']
        k.require(partial['total_FLOPs_available'] is False and partial['label'] == 'Conv2d/Linear module MACs (partial)', 'Partial MAC mislabeled total FLOPs')
        item = {'run_id': row['run_id'], 'method': binding['row']['method'], 'framework': binding['row']['framework'],
            'seed': binding['row']['seed'], 'task': task, 'unit_accuracy': 'fraction', **{key: metrics[key] for key in (*COUNTS, *METRICS)},
            'whole_model_parameter_elements': whole['whole_model_parameter_elements'],
            'observed_direct_owner_parameter_elements': trace['observed_direct_owner_parameter_elements'],
            'partial_Conv2d_Linear_MACs_both_forwards': partial['count_for_this_single_image_operation'],
            'b1_batch_exact_equal_diagnostic': measured['b1_vs_native_batch_difference']['exact_equal'],
            'measurement_path': str(measurement_path), 'checkpoint_sha256': binding['checkpoint']['sha256']}
        for scope in SCOPES:
            summary = verify_measurement(measured[scope], scope, summarize)
            for field in ('median', 'mean', 'sample_sd', 'IQR'):
                item[scope + '_' + field + '_ms'] = summary[field]
            for field in ('peak_allocated', 'peak_reserved'):
                item[scope + '_' + field + '_bytes'] = measured[scope]['memory'][field]
        rows.append(item)
    k.verify_record(result_record)
    return rows

def aggregate(plan, plan_record, release_record, bindings, slot_rows, output, parent, execution_source):
    _, k, b, _ = c.runtime_helpers()
    expected = [x['run_id'] for x in b.slots()]
    k.require(len(slot_rows) == 7 and [x['run_id'] for x in slot_rows] == expected and len(set(expected)) == 7, 'Exactly seven unique ordered completed slots required')
    rows = []
    for slot, binding in zip(slot_rows, bindings):
        rows.extend(verify_slot(slot, binding, plan_record, release_record))
    k.require(len(rows) == 70 and len({(row['run_id'], row['task']) for row in rows}) == 70, 'Expected exactly70 distinct fit/task rows')
    for artifact in (plan_record, release_record, execution_source):
        k.verify_record(artifact)
    csv_path = output / 'external_t1_70_task_efficiency.csv'
    with csv_path.open('x', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    seed_summary = []
    for task in b.EXPECTED_TASKS:
        group = [row for row in rows if row['method'] == 'QDFL' and row['task'] == task]
        k.require([row['seed'] for row in group] == [1, 2, 3], 'QDFL summary requires three actual independent seeds')
        fields = list(METRICS) + [scope + '_median_ms' for scope in SCOPES]
        seed_summary.append({'task': task, 'n_independent_training_seeds': 3,
            'values': {key: {'mean': statistics.mean(row[key] for row in group), 'sample_sd': statistics.stdev(row[key] for row in group),
                'per_seed': [row[key] for row in group]} for key in fields}})
    seeds_record = c.atomic_new_json(output / 'qdfl_three_seed_descriptive_summary.json',
        {'scope': 'descriptive across three actual fitted seeds; latency is one fixed query per task', 'tasks': seed_summary, 'significance_test_performed': False})
    result = {'schema': 'external-t1-seven-slot-efficiency-aggregate.v1', 'status': 'seven_native_slots_and_70_tasks_verified',
        'plan': plan_record, 'release': release_record, 'execution_source': execution_source,
        'controller': parent, 'parent_exit_not_observed': True, 'parent_exit0_required_by_final_T6_acceptor': True,
        'slots': slot_rows, 'slot_count': 7, 'task_count': 70, 'long_table': k.record(csv_path), 'qdfl_seed_summary': seeds_record,
        'full_t6_complete': False, 'manuscript_result': False, 'CAMP_DAC_efficiency_included': False,
        'scope': 'original FP32 native double-forward descriptors and complete galleries; four selected-query timing scopes; partial module MACs only',
        'own_parent_stdout_stderr_included': False, 'completed_utc': k.now()}
    for artifact in (plan_record, release_record, execution_source):
        k.verify_record(artifact)
    return c.atomic_new_json(output / 'aggregate.json', result)
