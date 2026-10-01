"""Read-only bounded review of two completed pipeline jobs; stdlib only."""
import ast
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import struct
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
EX = HERE.parent
ROOT = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
AG = ROOT / 'lgm_game_pytorch/results/formal_matrix_aggregate'
FIG = EX.parent / 'formal_results'
RAW = HERE / 'raw'
RAW.mkdir(exist_ok=False)
bindings = []


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def capture(path):
    path = Path(path)
    require(path.suffix.lower() not in ('.pt', '.pth', '.npz', '.npy'), 'No weight/old array reads')
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            'File changed while snapshotting: ' + str(path))
    digest = hashlib.sha256(data).hexdigest()
    backup = RAW / (str(len(bindings)).zfill(3) + '_' + path.name)
    with backup.open('xb') as stream:
        stream.write(data)
    record = {'path': str(path), 'bytes': len(data), 'sha256': digest,
              'snapshot': str(backup), 'mtime_ns': after.st_mtime_ns}
    bindings.append(record)
    return data, record


def read_json(path):
    data, record = capture(path)
    return json.loads(data.decode('utf-8-sig')), record


def read_csv_bytes(data):
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))


def canonical(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), default=str).encode('utf-8')).hexdigest()


def payload_ok(payload):
    body = dict(payload); expected = body.pop('payload_sha256')
    require(canonical(body) == expected, 'Canonical payload hash differs')


def equivalent(a, b):
    if isinstance(b, bool):
        return str(a).lower() == str(b).lower()
    if isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-10)
    if str(a) == str(b):
        return True
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-10)
    except (ValueError, TypeError):
        return False


def compare_rows(actual, expected, keys):
    index = {tuple(str(row[key]) for key in keys): row for row in expected}
    require(len(index) == len(expected) == len(actual), 'Row count or unique keys differs')
    for row in actual:
        key = tuple(str(row[key]) for key in keys)
        require(key in index, 'Unexpected output data key')
        for field, value in index[key].items():
            require(field in row and equivalent(row[field], value), 'Output data differs: ' + field)


def dt(value):
    return datetime.fromisoformat(value)


def main():
    primary, primary_record = read_json(EX / 'status.json')
    pipeline, pipeline_record = read_json(EX / 'pipeline_status.json')
    process, process_record = read_json(HERE / 'PROCESS_OBSERVATION.json')
    old_launch, _ = read_json(EX / 'host_recovery_20260929_0341/primary_launch.json')
    active = {row['pid']: row for row in process['actual']}
    require(primary['status'] == 'completed' and primary['controller_pid'] == 33924 and
            33924 not in active and old_launch['launcher_pid'] == 31992 and 31992 not in active,
            'Primary completion/absence observation differs')
    require(pipeline['supervisor_pid'] == 14420 and pipeline['primary_status'] == 'completed' and
            pipeline['status'] == 'running_post_training' and pipeline['active_stage'] == 'cross_dataset_transfer',
            'Pipeline transition differs')
    for pid, parent, ticks in ((14420, 29784, '639262477073457420'),
                              (29784, 34104, '639262477073052210'),
                              (20604, 14420, '639262533797593290'),
                              (39488, 20604, '639262533797816820')):
        require(active[pid]['parent_pid'] == parent and active[pid]['creation_utc_ticks'] == ticks,
                'Observed process identity differs')
    require('--role' in active[14420]['command_line'] and 'pipeline' in active[14420]['command_line'],
            'Pipeline actual command differs')
    jobs = pipeline['jobs']
    require(len(jobs) == 7 and [j['id'] for j in jobs[:3]] ==
            ['formal_aggregate', 'formal_figures', 'cross_dataset_transfer'], 'Pipeline job order differs')
    require(dt(primary['finished_utc']) < dt(jobs[0]['started_utc']) < dt(jobs[0]['finished_utc']) <=
            dt(jobs[1]['started_utc']) < dt(jobs[1]['finished_utc']) <= dt(jobs[2]['started_utc']),
            'Predecessor/child completion sequence differs')
    sources = {}
    for filename in ('supervise_pipeline.py', 'continue_formal_matrix.py',
                     'continue_formal_matrix_path_compat_v1.py', 'run_controller_with_state_retry_v2.py'):
        data, record = capture(EX / filename)
        sources[filename] = record
        ast.parse(data.decode('utf-8-sig'))
    stdout = {}
    for job in jobs[:2]:
        require(job['status'] == 'completed' and job['exit_code'] == 0 and job['pid'] not in active,
                'Job lacks original parent success or old PID absence')
        source, record = capture(job['command'][1])
        require(record['sha256'] == job['entrypoint_sha256'], 'Executed source pin changed')
        sources[Path(job['command'][1]).name] = record
        data, _ = capture(EX / ('stage_logs/' + job['id'] + '.stdout.log'))
        stdout[job['id']] = json.loads(data.decode('utf-8').strip())
        stderr, _ = capture(EX / ('stage_logs/' + job['id'] + '.stderr.log'))
        require(not stderr, 'Stage stderr not empty')
    for filename in ('primary.stdout.log', 'primary.stderr.log'):
        data, _ = capture(EX / 'host_recovery_20260929_0341' / filename)
        require(not data, 'New primary control log not empty')

    aggregate, aggregate_record = read_json(AG / 'aggregate_manifest.json'); payload_ok(aggregate)
    require(aggregate['schema_version'] == 'lgm-game.formal-aggregate.v1' and
            aggregate['status'] == 'complete' and aggregate['allow_partial'] is False and
            aggregate['matrix'] == {'completed_pairwise_tests': 33, 'expected_main_runs': 36,
                'expected_pairwise_tests': 33, 'expected_sensitivity_runs': 6,
                'valid_main_runs': 36, 'valid_sensitivity_runs': 6}, 'Aggregate completion contract differs')
    require(stdout['formal_aggregate']['payload_sha256'] == aggregate['payload_sha256'], 'Aggregate stdout differs')
    outputs = {}
    require(len(aggregate['output_artifacts']) == 16, 'Aggregate output count differs')
    for row in aggregate['output_artifacts']:
        data, rec = capture(AG / row['path'])
        require(rec['sha256'] == row['sha256'] and rec['bytes'] == row['bytes'], 'Aggregate output hash/size differs')
        outputs[row['path']] = data
    tables = {name: read_csv_bytes(data) for name, data in outputs.items() if name.endswith('.csv')}
    result = json.loads(outputs['aggregate_results.json'])
    audit = json.loads(outputs['matrix_completeness_audit.json'])
    require(audit['global_issues'] == [] and audit['incomplete_runs'] == audit['invalid_runs'] == 0 and
            audit['mode'] == 'fail_closed' and len(audit['run_audit']) == 42 and
            all(r['status'] == 'valid' for r in audit['run_audit']), 'Matrix audit incomplete')
    for prefix in ('aggregator', 'formal_script', 'ledger', 'protocol', 'runner'):
        _, rec = capture(aggregate['provenance'][prefix + '_path'])
        require(rec['sha256'] == aggregate['provenance'][prefix + '_sha256'], 'Aggregate source input binding differs')
    raw = tables['main_metrics_by_seed.csv']; summaries = tables['main_three_seed_mean_sample_sd.csv']
    metrics = ('r_at_1', 'r_at_5', 'r_at_10', 'r_at_20', 'official_trapezoid_mAP', 'MRR')
    tasks = aggregate['task_policy']
    variants = ('visual', 'content', 'style', 'visual_content', 'visual_style', 'full')
    expected = {(dataset, task, variant, str(seed)) for dataset in ('university1652', 'sues200')
                for task in tasks[dataset + '_tasks'] for variant in variants for seed in (1, 2, 3)}
    require(len(raw) == 198 and {(r['dataset'], r['task'], r['variant'], r['seed']) for r in raw} == expected,
            'Raw exact 36-run task/seed matrix differs')
    require(len(summaries) == 66, 'Summary count differs')
    for row in summaries:
        selected = [r for r in raw if all(r[k] == row[k] for k in ('dataset', 'task', 'variant'))]
        require(len(selected) == 3 and sorted(r['seed'] for r in selected) == ['1', '2', '3'] and
                row['n_seeds'] == '3' and row['seeds'] == '1|2|3' and row['complete_seed_triplet'] == 'true',
                'Summary seed triplet differs')
        for metric in metrics:
            observations = [float(r[metric + '_pct']) for r in selected]
            require(all(math.isfinite(v) and 0 <= v <= 100 for v in observations), 'Invalid raw metric')
            require(equivalent(row[metric + '_mean_pct'], statistics.fmean(observations)) and
                    equivalent(row[metric + '_sample_sd_pct'], statistics.stdev(observations)),
                    'Independent three-seed mean/sample SD differs')
    compare_rows(summaries, result['main_three_seed_summary'], ('dataset', 'task', 'variant'))
    sensitivity = tables['sensitivity_metrics.csv']; reference = tables['sensitivity_with_main_reference.csv']
    require(len(sensitivity) == 33 and len(reference) == 44 and all(r['seed'] == '1' for r in reference),
            'Sensitivity count/seed differs')
    compare_rows(sensitivity, result['sensitivity_runs'], ('dataset', 'task', 'setting'))
    compare_rows(reference, result['sensitivity_with_main_reference'], ('dataset', 'task', 'setting'))
    for row in reference:
        candidates = raw if row['setting'] == 'full' else sensitivity
        source = [r for r in candidates if r['dataset'] == row['dataset'] and r['task'] == row['task']
                  and r['seed'] == '1' and r['setting'] == row['setting']]
        require(len(source) == 1 and all(equivalent(row[m+'_pct'], source[0][m+'_pct']) for m in metrics),
                'Sensitivity/reference source metric differs')
    inventory = tables['input_artifact_sha256.csv']
    require(len(inventory) == aggregate['input_artifact_count'] == 572, 'Aggregate input inventory count differs')
    require(len({(r['run_identifier'], r['role'], r['path']) for r in inventory}) == 572, 'Duplicate input binding')
    for row in raw + sensitivity:
        identifier = '/'.join((row['family'], row['dataset'], row['variant'], 'seed_'+row['seed'],
                               row['backbone'], 'dim_'+row['embed_dim']))
        bound = [r for r in inventory if r['run_identifier'] == identifier]
        for field, role in (('checkpoint_sha256', 'selected_checkpoint'), ('metrics_sha256', 'evaluation_metrics')):
            require(any(r['role'] == role and r['sha256'] == row[field] for r in bound), 'Raw metric input binding differs')
        require(any(r['sha256'] == row['per_query_arrays_sha256'] for r in bound), 'Raw per-query input binding differs')
    require(sum(r['role'] == 'selected_checkpoint' and r['verification'] == 'computed' for r in inventory) == 42 and
            sum(r['role'] == 'last_checkpoint' and r['verification'] == 'declared_manifest_hash_and_file_presence'
                for r in inventory) == 42, 'Producer checkpoint verification labels differ')
    bootstrap = tables['visual_vs_full_paired_bootstrap.csv']; mcnemar = tables['visual_vs_full_exact_mcnemar_holm.csv']
    for rows, key in ((bootstrap, 'visual_vs_full_paired_bootstrap'), (mcnemar, 'visual_vs_full_exact_mcnemar_holm')):
        require(len(rows) == 33, 'Pairwise family incomplete')
        compare_rows(rows, result[key], ('dataset', 'task', 'seed'))
    require(all(r['bootstrap_samples'] == '10000' for r in bootstrap) and
            all(r['holm_family_size'] == '33' and r['holm_status'] == 'complete' for r in mcnemar),
            'Pairwise protocol differs')

    figures, figures_record = read_json(FIG / 'formal_figure_manifest.json'); payload_ok(figures)
    require(figures['status'] == 'completed' and len(figures['figure_contracts']) == 5 and
            len(figures['artifacts']) == 20 and figures['png_dpi'] == 600 and
            figures['input']['aggregate_manifest_sha256'] == aggregate_record['sha256'] and
            figures['analysis_code']['sha256'] == jobs[1]['entrypoint_sha256'], 'Figure completion/input binding differs')
    require(stdout['formal_figures']['payload_sha256'] == figures['payload_sha256'], 'Figure stdout differs')
    for filename, digest in figures['input']['aggregate_csv_sha256'].items():
        require(hashlib.sha256(outputs[filename]).hexdigest() == digest, 'Figure aggregate CSV input binding differs')
    exports = []
    for row in figures['artifacts']:
        data, rec = capture(FIG / row['path'])
        require(rec['sha256'] == row['sha256'] and rec['bytes'] == row['bytes'], 'Figure artifact hash/size differs')
        detail = {'path': row['path'], 'role': row['role']}
        if row['role'] == 'svg':
            xml = ET.fromstring(data)
            texts = [n for n in xml.iter() if n.tag.rsplit('}', 1)[-1] == 'text']
            images = [n for n in xml.iter() if n.tag.rsplit('}', 1)[-1] == 'image']
            require(xml.tag.endswith('svg') and texts and not images, 'SVG has no editable text or embeds raster')
            detail.update(editable_text_nodes=len(texts), embedded_raster_nodes=len(images))
        elif row['role'] == 'pdf':
            require(data.startswith(b'%PDF-') and b'%%EOF' in data[-1024:], 'PDF framing invalid')
        elif row['role'] == 'png':
            require(data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR', 'PNG header invalid')
            width, height = struct.unpack('>II', data[16:24]); require(min(width, height) >= 1000, 'PNG undersized')
            detail.update(width=width, height=height, nonblank_visual_inspection_performed=False)
        elif row['role'] == 'source_data':
            rows = read_csv_bytes(data); require(len(rows) == row['rows'], 'Figure source row count differs')
            if row['figure'].startswith('formal_main_'):
                dataset = 'sues200' if 'sues200' in row['figure'] else 'university1652'
                compare_rows(rows, [r for r in summaries if r['dataset'] == dataset], ('dataset', 'task', 'variant'))
            elif row['figure'] == 'formal_sues_altitude_curves':
                compare_rows(rows, [r for r in summaries if r['dataset'] == 'sues200'], ('dataset', 'task', 'variant'))
            elif row['figure'] == 'formal_sensitivity':
                compare_rows(rows, reference, ('dataset', 'task', 'setting'))
            else:
                merged = []
                for b in bootstrap:
                    m = next(r for r in mcnemar if all(r[k] == b[k] for k in ('dataset', 'task', 'seed')))
                    merged.append(dict(b, **{k:m[k] for k in ('holm_adjusted_log10_p', 'holm_adjusted_p',
                        'reject_holm_0_05', 'holm_family_size', 'visual_correct_full_wrong', 'visual_wrong_full_correct')}))
                compare_rows(rows, merged, ('dataset', 'task', 'seed'))
        exports.append(detail)
    return {'status': 'passed_bounded_two_job_review', 'scope': ['formal_aggregate', 'formal_figures'],
        'primary': {'status': primary['status'], 'finished_utc': primary['finished_utc'],
            'actual_owner_and_launcher_absent': True, 'direct_process_exit_code_observed': False,
            'last_child_event': primary['events'][-1],
            'evidence_limit': 'Primary wrote completed after legacy.main returned; no saved own/interpreter exit code. Pipeline guard subsequently saw owner not alive.'},
        'pipeline': {'status': pipeline['status'], 'active_stage': pipeline['active_stage'],
            'first_two_jobs': jobs[:2], 'whole_pipeline_completed': False,
            'exit_evidence': 'Original Popen child.returncode=0 and current PID absence; no independent dual-handle/interpreter exit code.'},
        'aggregate': {'manifest': aggregate_record, 'rows': {'main_by_seed': 198, 'main_summaries': 66,
            'sensitivity': 33, 'sensitivity_with_reference': 44, 'paired_tests': 33},
            'independent_mean_and_sample_sd_checks': 792, 'input_inventory_rows': 572,
            'output_artifacts_verified': 16,
            'producer_best_hashes': 'Pinned executed aggregator computes42 best.pt hashes; original output inventory records computed. This audit does not reopen/check those weight bytes.',
            'producer_last_hashes': '42 last.pt declarations plus presence, not actual content hashes.'},
        'figures': {'manifest': figures_record, 'figure_count': 5, 'artifacts_verified': 20,
            'source_csvs_match_aggregate': True, 'exports': exports, 'powerpoint_or_visio_created': False,
            'publication_layout_or_visual_readability_reviewed': False},
        'sources': sources,
        'limits': ['No old42 weights or old evaluation arrays/metrics reopened; no model/metric/ranking rerun.',
            'Aggregate raw metrics linked to its recorded input inventory, not fresh independently rehashed upstream contents.',
            'Bootstrap/McNemar values checked for schema and CSV/JSON/figure consistency, not independently rerun from queries.',
            'SVG XML editable text and no raster verified; no visual/page-by-page or font-size acceptance.',
            'Only first two of seven jobs reviewed; cross_dataset_transfer still running, no later-stage completion claim.'],
        'scientific_imports': sorted({n.split('.')[0] for n in sys.modules} & {'torch','numpy','PIL','cv2','matplotlib'}),
        'scientific_execution': False, 'live_files_changed': False, 'recovery_or_validateonly': False}


try:
    review = main()
except BaseException as error:
    review = {'status': 'failed', 'error': type(error).__name__ + ': ' + str(error)}
    raise
finally:
    review['created_utc'] = datetime.now(timezone.utc).isoformat()
    review['bindings'] = bindings
    review['script'] = {'path': str(Path(__file__).resolve()),
        'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with (HERE / 'REVIEW.json').open('x', encoding='utf-8') as stream:
        json.dump(review, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
print(json.dumps({'status': review['status'], 'bindings': len(bindings), 'report': str(HERE / 'REVIEW.json')}))
