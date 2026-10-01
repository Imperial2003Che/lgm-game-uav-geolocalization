"""Bounded descriptive SUES visual/full seed1 comparison after both adoptions.

Invocation requires the root's explicit Full adoption path AND exact SHA. Only
small SHA-bound sealed JSON/CSV inputs are opened; no science imports or arrays.
"""
import argparse
import csv
import datetime
from decimal import Decimal, getcontext
import hashlib
import io
import json
from pathlib import Path
import sys

getcontext().prec = 50
HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
VISUAL_ROOT = EXECUTION / 'robustness_sues_visual_audit_20260929_1351/ROOT_SUES_VISUAL1_ADOPTION.json'
VISUAL_SHA = 'a6795283cb384c77732bdb1e63af93d582d7844879f415e45ef38c8861d3af74'
VISUAL_TREE = VISUAL_ROOT.parent / 'a1/r'
TASKS = {
    'sues200_uav_150m_to_satellite': (4000, 200),
    'sues200_satellite_to_uav_150m': (80, 10000),
    'sues200_uav_200m_to_satellite': (4000, 200),
    'sues200_satellite_to_uav_200m': (80, 10000),
    'sues200_uav_250m_to_satellite': (4000, 200),
    'sues200_satellite_to_uav_250m': (80, 10000),
    'sues200_uav_300m_to_satellite': (4000, 200),
    'sues200_satellite_to_uav_300m': (80, 10000),
}
METRICS = ('r_at_1', 'official_trapezoid_mAP', 'MRR')
ALL_DROP_METRICS = ('r_at_1', 'r_at_5', 'r_at_10', 'r_at_20', 'official_trapezoid_mAP', 'MRR')
CONDITIONS = ('gaussian_noise', 'gaussian_blur', 'brightness', 'contrast', 'center_occlusion', 'rotation')
AP_DEFINITION = 'Official trapezoidal interpolation used by the University-1652/SUES reference evaluator.'
DROP_COLUMNS = ['task', 'metric', 'clean', 'corrupted', 'absolute_drop_fraction',
                'percentage_point_drop', 'relative_drop_fraction', 'relative_drop_percent']
LIMITS = [
    'SUES-200, visual and full, seed1 only: 240 corrupted task/condition pairs and 8 clean task pairs. No multi-seed SD, confidence interval, significance or general robustness superiority is inferred.',
    'No pooling across tasks, corruption families or severity levels. Every result remains a matched task/condition/severity/seed comparison. Higher raw Full-minus-Visual means a higher saved metric; a positive drop difference means Full has a larger absolute clean-to-corrupt decrease, whose interpretation also depends on the clean baselines.',
    'Full clean content/style probabilities come from the cache and corrupted-query evidence is generated online. Full clean-to-corrupt differences therefore include an evidence-path change as well as image corruption, and cannot be interpreted as pure corruption effects.',
    'The Full 64-sample clean CLIP diagnostic has no numerical equivalence threshold and does not establish bitwise parity or that differences are negligible for ranking. Visual ignores content/style evidence.',
    'Checkpoint bytes, cache contents and image contents are inherited from the exact prior accepted scientific provenance. This comparison does not reread or rehash them, and metadata/stat stability does not prove current bytes. The historical initial12/visual_style1 whole-file SHA edge gaps elsewhere in the global evidence history and all other limitations in the two adopted root reports remain; the two SUES checkpoints have their own specific accepted training authorities.',
    'The prior artifact reviews use typed stdlib compatibility for original completion AST bodies, not a native NumPy/model rerun. Their stored float32 AP/RR/margin aggregate comparisons use tolerated scalar binary64 means; they do not recompute AP from every positive rank, full rankings, corrupted pixels or features.',
    'This computation reads only saved small JSON/CSV summaries. No per-query arrays, model, science library, GPU, cache, image, checkpoint, live state or frozen producer source is opened or changed. Original worker returncode/absence evidence is not an independently captured launcher/interpreter dual-handle exit proof.',
    'The four robustness runs were adopted separately. This two-run descriptive comparison does not itself re-audit that stage or complete the seven-stage pipeline. Prior adopted official and transfer negative findings retain their original scope and are not displaced by this seed1 comparison.',
]
CHECKS = 0
INPUTS = []
SEEN = {}


def require(condition, label):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise ValueError(label)


def key(path):
    return str(Path(path).resolve()).casefold()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reject_constant(value):
    raise ValueError('Nonfinite JSON constant: ' + value)


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        require(name not in result, 'Duplicate JSON key: ' + name)
        result[name] = value
    return result


def decode_json(data):
    return json.loads(data.decode('utf-8-sig'), parse_float=Decimal,
                      parse_constant=reject_constant, object_pairs_hook=unique_object)


def descriptor(path, data):
    return {'path': str(Path(path).resolve()), 'sha256': sha(data), 'bytes': len(data)}


def read_bound(path, digest, size=None, role='input'):
    path = Path(path).resolve()
    require(path.is_relative_to(EXECUTION), 'Input outside execution directory')
    require(path.suffix.lower() in ('.json', '.csv'), 'Input extension not allowed')
    require(path.stat().st_size <= 4 * 1024 * 1024, 'Input exceeds small-artifact bound')
    data = path.read_bytes()
    require(sha(data) == digest, 'SHA mismatch: ' + str(path))
    if size is not None:
        require(len(data) == size, 'Size mismatch: ' + str(path))
    ident = key(path)
    if ident in SEEN:
        require(SEEN[ident]['sha256'] == digest, 'Conflicting input identity')
    else:
        item = descriptor(path, data)
        item['role'] = role
        item['_data'] = data
        INPUTS.append(item)
        SEEN[ident] = item
    return data


def adoption(path, digest):
    root = decode_json(read_bound(path, digest, role='accepted_root'))
    require(root.get('accepted_with_stated_limits') is True, 'Root did not accept with limits')
    require(isinstance(root.get('bindings'), list), 'Missing adopted path/SHA/size bindings')
    index = {}
    for item in root['bindings']:
        require(set(('path', 'sha256', 'bytes')).issubset(item), 'Incomplete adopted binding')
        ident = key(item['path'])
        if ident in index:
            require((index[ident]['sha256'], index[ident]['bytes']) ==
                    (item['sha256'], item['bytes']), 'Conflicting adopted path bindings')
        index[ident] = item
    return root, index


def load_admitted(tree, relative, index):
    path = (tree / relative).resolve()
    require(path.is_relative_to(tree), 'Escaped sealed input tree')
    require(key(path) in index, 'Input is not directly bound by root: ' + str(path))
    item = index[key(path)]
    return read_bound(path, item['sha256'], item['bytes'], 'sealed_summary')


def number(value, label):
    require(isinstance(value, (int, Decimal)) and not isinstance(value, bool), label + ': nonnumeric')
    result = Decimal(value)
    require(result.is_finite(), label + ': nonfinite')
    return result


def close_decimal(actual, expected, scale, label):
    # Published decimals round IEEE binary64 producer arithmetic. 5e-16 is
    # an absolute fraction-unit reconciliation tolerance; x100 fields carry
    # the same tolerance multiplied by 100. It never gates a scientific claim.
    require(abs(number(actual, label) - expected) <= Decimal('5e-16') * scale, label)


def decimal_text(value):
    return format(value, 'f')


def metric_document(doc, task_scales, condition, label):
    require(doc['schema_version'] == 'lgm-game.image-level-robustness.v1', label + ': schema')
    require(doc['unit'] == 'fraction' and doc['AP_definition'] == AP_DEFINITION, label + ': units/AP')
    require(doc['full_gallery'] is True and doc['clean_gallery_for_every_condition'] is True, label + ': gallery')
    require(doc['condition'] == condition, label + ': exact condition')
    require(set(doc['results']) == set(TASKS), label + ': exact task keys')
    for task, result in doc['results'].items():
        require(result['unit'] == 'fraction', label + ': task units')
        for field, val in task_scales[task].items():
            require(result[field] == val, label + ': task metadata ' + field)
        for metric in METRICS:
            require(0 <= number(result[metric], metric) <= 1, label + ': metric range')


def load_variant(variant, tree, index):
    cfg = decode_json(load_admitted(tree, 'run_config.json', index))
    cfg_i = cfg['immutable_config']
    manifest = decode_json(load_admitted(tree, 'robustness_manifest.json', index))
    require(cfg_i['dataset'] == manifest['dataset'] == 'sues200', 'Dataset')
    require(cfg_i['checkpoint']['variant'] == manifest['variant'] == variant, 'Variant')
    require(cfg_i['checkpoint']['seed'] == 1 and manifest['checkpoint'] == cfg_i['checkpoint'], 'Seed/checkpoint metadata')
    require(manifest['status'] == 'completed', 'Manifest is not completed')
    require(manifest['run_config_sha256'] == cfg['run_config_sha256'], 'Run config identity')
    require(manifest['expected_corruption_conditions'] == manifest['completed_corruption_conditions'] == 30,
            'Condition count')
    require(manifest['condition_count_complete'] is True, 'Condition completeness')
    scales = cfg_i['official_task_scale']
    require(set(scales) == set(TASKS), 'Task scale keys')
    for task, (queries, gallery) in TASKS.items():
        require((scales[task]['queries'], scales[task]['gallery']) == (queries, gallery), 'Task scales')
    matrix = cfg_i['corruption_matrix']
    require(len(matrix) == 6 and {c['name'] for c in matrix} == set(CONDITIONS), 'Corruption families')
    expected = {}
    for c in matrix:
        require(len(c['values']) == 5, 'Severity count')
        for severity, value in enumerate(c['values'], 1):
            condition = {k: v for k, v in c.items() if k != 'values'}
            condition.update(kind='corruption', severity_index=severity, value=value,
                             corruption_seed=cfg_i['corruption_seed'], query_only=True, gallery='clean')
            expected[c['name'], severity] = condition
    clean_condition = {'kind': 'clean', 'name': 'clean', 'query_pixels': 'decoded without corruption', 'gallery': 'clean'}
    clean = decode_json(load_admitted(tree, 'clean/metrics.json', index))
    metric_document(clean, scales, clean_condition, variant + ' clean')
    require(clean['degradation_vs_clean'] is None, 'Clean degradation must be null')
    data = {('clean', 0): clean}
    for (name, severity), condition in expected.items():
        rel = f'conditions/{name}/severity_{severity:02d}/'
        doc = decode_json(load_admitted(tree, rel + 'metrics.json', index))
        metric_document(doc, scales, condition, variant + ' ' + rel)
        require(set(doc['degradation_vs_clean']) == set(TASKS), 'Drop task keys')
        csv_bytes = load_admitted(tree, rel + 'degradation_vs_clean.csv', index)
        reader = csv.DictReader(io.StringIO(csv_bytes.decode('utf-8-sig'), newline=''))
        require(reader.fieldnames == DROP_COLUMNS, 'Drop CSV columns and order')
        rows = list(reader)
        csv_index = {(r['task'], r['metric']): r for r in rows}
        require(len(rows) == len(csv_index) == 48, 'Drop CSV row count/unique keys')
        require(set(csv_index) == {(t, m) for t in TASKS for m in ALL_DROP_METRICS}, 'Drop CSV exact keys')
        for task in TASKS:
            require(set(doc['degradation_vs_clean'][task]) == set(ALL_DROP_METRICS), 'Drop JSON metric keys')
            for metric in METRICS:
                raw_clean = number(clean['results'][task][metric], metric)
                raw_corrupt = number(doc['results'][task][metric], metric)
                drop = raw_clean - raw_corrupt
                record = doc['degradation_vs_clean'][task][metric]
                expected_drop = {'clean': raw_clean, 'corrupted': raw_corrupt,
                                 'absolute_drop_fraction': drop, 'percentage_point_drop': drop * 100}
                require(set(record) == set(DROP_COLUMNS[2:]), 'Drop field set')
                for field, expected_value in expected_drop.items():
                    scale = Decimal(100) if field == 'percentage_point_drop' else Decimal(1)
                    close_decimal(record[field], expected_value, scale, 'Published JSON ' + field)
                for field in DROP_COLUMNS[2:]:
                    # Relative drops are carried by producer but are not used in
                    # this comparison; only CSV/JSON serialization consistency.
                    csv_value = csv_index[task, metric][field]
                    if record[field] is None:
                        require(csv_value == '', 'CSV null consistency')
                    else:
                        require(Decimal(csv_value) == number(record[field], field), 'CSV/JSON exact decimal agreement')
        data[name, severity] = doc
    require(len(data) == 31, 'Exact condition count')
    return cfg_i, manifest, data


def dump_json(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    path.write_bytes(data)
    return descriptor(path, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-root', required=True, type=Path)
    parser.add_argument('--full-root-sha', required=True)
    parser.add_argument('--full-sealed-tree', required=True, type=Path)
    args = parser.parse_args()
    require(len(args.full_root_sha) == 64 and all(c in '0123456789abcdef' for c in args.full_root_sha), 'Explicit lowercase Full adoption SHA required')
    require(args.full_root.resolve().parent == EXECUTION / 'robustness_sues_full_audit_20260929_1448', 'Full root location')
    require(args.full_sealed_tree.resolve() == args.full_root.resolve().parent / 'a1/r', 'Full sealed tree location')
    visual_root, vi = adoption(VISUAL_ROOT, VISUAL_SHA)
    full_root, fi = adoption(args.full_root, args.full_root_sha)
    vc, vm, visual = load_variant('visual', VISUAL_TREE, vi)
    fc, fm, full = load_variant('full', args.full_sealed_tree.resolve(), fi)
    for field in ('dataset', 'data_root', 'evidence_caches', 'sues_manifest', 'protocol_membership_sha256',
                  'image_inventory', 'official_task_scale', 'unique_query_images', 'unique_clean_gallery_images',
                  'query_path_membership_sha256', 'gallery_path_membership_sha256', 'corruption_matrix',
                  'corruption_seed', 'ranking', 'encoding'):
        require(vc[field] == fc[field], 'Matched protocol field: ' + field)
    require(set(visual) == set(full), 'Exact condition keys matched')
    paired = []
    flat = []
    order = [('clean', 0)] + [(c, s) for c in CONDITIONS for s in range(1, 6)]
    for condition, severity in order:
        vd, fd = visual[condition, severity], full[condition, severity]
        require(vd['condition'] == fd['condition'], 'Paired exact condition')
        require(set(vd['results']) == set(fd['results']) == set(TASKS), 'Paired exact task keys')
        for task in TASKS:
            common = {'dataset': 'sues200', 'seed': 1, 'task': task,
                      'condition': condition, 'severity_index': severity,
                      'queries': TASKS[task][0], 'gallery': TASKS[task][1]}
            row = dict(common, condition_definition={k: decimal_text(v) if isinstance(v, Decimal) else v
                                                    for k, v in vd['condition'].items()}, metrics={})
            for metric in METRICS:
                vclean = number(visual['clean', 0]['results'][task][metric], metric)
                fclean = number(full['clean', 0]['results'][task][metric], metric)
                veval = number(vd['results'][task][metric], metric)
                feval = number(fd['results'][task][metric], metric)
                vdlt, fdlt = vclean - veval, fclean - feval
                values = {'visual_clean': vclean, 'full_clean': fclean,
                          'visual_condition': veval, 'full_condition': feval,
                          'full_minus_visual_clean': fclean - vclean,
                          'full_minus_visual_condition': feval - veval,
                          'visual_clean_minus_condition_drop': vdlt,
                          'full_clean_minus_condition_drop': fdlt,
                          'full_minus_visual_drop_difference': fdlt - vdlt}
                require(values['full_minus_visual_drop_difference'] ==
                        values['full_minus_visual_clean'] - values['full_minus_visual_condition'], 'Difference of differences identity')
                metrics = {'metric': metric,
                           'scaled100_value_unit': 'MRR_times_100' if metric == 'MRR' else 'percent',
                           'scaled100_difference_unit': 'MRR_times_100_units' if metric == 'MRR' else 'percentage_points'}
                for name, value in values.items():
                    metrics[name + '_fraction'] = decimal_text(value)
                    metrics[name + '_scaled100'] = decimal_text(value * 100)
                row['metrics'][metric] = metrics
                flat.append(dict(common, **metrics))
            paired.append(row)
    require(len(paired) == 248 and len(flat) == 744, 'Final row counts')
    require(len({(r['task'], r['condition'], r['severity_index']) for r in paired}) == 248, 'Unique output keys')
    require(len(INPUTS) == 128, 'Exactly two roots + four config/manifest + 122 numerical inputs')
    require(not any(k in sys.modules for k in ('numpy', 'torch', 'PIL', 'pandas', 'scipy')), 'No scientific modules loaded')
    now = datetime.datetime.now(datetime.timezone.utc)
    out = HERE / ('result_' + now.strftime('%Y%m%d_%H%M%S_%f'))
    out.mkdir(exist_ok=False)
    inputdir = out / 'inputs'
    inputdir.mkdir()
    for idx, item in enumerate(INPUTS):
        data = item.pop('_data')
        saved = inputdir / (f'{idx:03d}_' + Path(item['path']).name)
        saved.write_bytes(data)
        item['snapshot'] = str(saved)
    artifacts = []
    artifacts.append(dump_json(out / 'paired_tasks.json', {'schema': 'lgm.robustness.seed1-paired-tasks.v1',
        'scope': {'dataset': 'sues200', 'seed': 1, 'clean_task_pairs': 8, 'corrupted_task_pairs': 240,
                  'metrics_per_pair': 3, 'comparison': 'Full minus Visual'},
        'number_encoding': 'Decimal strings from published JSON decimal values; arithmetic uses Decimal precision50.',
        'rows': paired, 'limits': LIMITS}))
    csvfile = out / 'paired_metrics.csv'
    with csvfile.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    artifacts.append(descriptor(csvfile, csvfile.read_bytes()))
    readme = '''# SUES-200 Visual vs Full: seed1 only

The two root-adopted completed runs are paired by the exact task, corruption family,
severity, parameters, seed and protocol membership. There are 8 clean task pairs
and 240 corrupted task/condition pairs. paired_tasks.json contains 248 paired rows;
paired_metrics.csv expands them into 744 rows (3 metrics per pair). Four heights
(150, 200, 250 and 300 m) and both directions remain separate. UAV-to-satellite
tasks use 4000 queries and 200 gallery images; satellite-to-UAV tasks use 80
queries and 10000 gallery images. All 200 gallery identities are retained.

All numeric output values are decimal strings in JSON and ordinary decimal cells
in CSV. Saved metric JSON decimals are parsed directly with Decimal precision50.
No averaging or pooling is performed. Source degradation CSV/JSON values are
checked against clean-minus-condition subtraction with an absolute fraction-unit
tolerance of 5e-16 (5e-14 for x100 fields) to allow binary64 producer rounding.
This is a serialization/arithmetic consistency check, not a scientific threshold.

r_at_1 and official_trapezoid_mAP scaled100 values are percentages, with differences
in percentage points. MRR scaled100 values and differences are MRR x100 units.
The common suffix _fraction retains the source's unit label for all three metrics.
mAP uses the official trapezoidal AP definition, not non-interpolated AP.

full_minus_visual_condition is Full condition metric minus Visual condition metric.
For clean rows the condition is clean, severity is 0 and both drop fields are 0.
full_minus_visual_drop_difference = (Full clean - Full condition)
minus (Visual clean - Visual condition); positive means Full's absolute decrease
is larger. It also equals the clean raw difference minus the condition raw difference.
A smaller drop alone does not imply better corrupted accuracy; compare both metrics
and clean baselines for the same task/condition row.

## Evidence and interpretation limits

'''+ '\n\n'.join('- ' + v for v in LIMITS) + '\n'
    readmefile = out / 'README.md'
    readmefile.write_text(readme, encoding='utf-8', newline='\n')
    artifacts.append(descriptor(readmefile, readmefile.read_bytes()))
    source_data = Path(__file__).read_bytes()
    derivation_files = [descriptor(HERE / name, (HERE / name).read_bytes()) for name in
                        ('DERIVATION.json', 'SUES_FROM_UNIVERSITY_SOURCE_DIFF.patch', 'derive_compare_sues.py')]
    report = {'schema': 'lgm.robustness.seed1-pair-comparison.report.v1', 'computed_utc': now.isoformat(),
        'calculation_complete_with_stated_limits': True, 'root_comparison_adoption_pending': True,
        'source': descriptor(__file__, source_data), 'argv': sys.argv, 'derivation_files': derivation_files,
        'visual_root': {'path': str(VISUAL_ROOT), 'sha256': VISUAL_SHA},
        'full_root': {'path': str(args.full_root.resolve()), 'sha256': args.full_root_sha},
        'input_count': len(INPUTS), 'inputs': INPUTS, 'artifacts': artifacts,
        'checks': CHECKS, 'clean_task_pairs': 8, 'corrupted_task_pairs': 240, 'metric_rows': 744,
        'decimal_precision': 50, 'checkpoint_cache_image_array_bytes_read': 0,
        'scientific_imports': [], 'live_state_modified': False, 'pooling_or_inference': False,
        'inherited_root_limits': {'visual': visual_root.get('limits'), 'full': full_root.get('limits')},
        'limits': LIMITS}
    report_desc = dump_json(out / 'REPORT.json', report)
    delivery = dump_json(out / 'DELIVERY.json', {'report': report_desc, 'artifacts': artifacts,
        'source': report['source'], 'derivation_files': derivation_files, 'root_comparison_adoption_pending': True})
    print(json.dumps({'output': str(out), 'report': report_desc, 'delivery': delivery,
                      'checks': CHECKS, 'inputs': len(INPUTS), 'paired_rows': len(paired), 'metric_rows': len(flat)}))


if __name__ == '__main__':
    main()
