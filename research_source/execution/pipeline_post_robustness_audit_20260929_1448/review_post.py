"""Independent stdlib check of captured aggregate and T4/T5 artifacts.

No producer imports, model, images, cache, checkpoint or bootstrap rerun.
T5 and T4 visual-margin strata are recomputed from 66 real stored NPZ inputs.
Other T4 strata remain aggregate-level checks; bootstrap CIs are not reproduced.
"""
import ast
import bisect
import csv
import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import struct
import sys
import zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
RAW = HERE / 'a1'
COUNT = 0
NUMERIC = 0
EXTRA_BINDINGS = []
METRICS = ('r_at_1', 'r_at_5', 'r_at_10', 'r_at_20', 'official_trapezoid_mAP', 'MRR')
TASKS = {'university1652': {'university1652_drone_to_satellite': 37855,
    'university1652_satellite_to_drone': 701, 'university1652_street_to_satellite': 2579},
    'sues200': {**{f'sues200_uav_{h}m_to_satellite': 4000 for h in (150, 200, 250, 300)},
                **{f'sues200_satellite_to_uav_{h}m': 80 for h in (150, 200, 250, 300)}}}
CORRUPTIONS = ('gaussian_noise', 'gaussian_blur', 'brightness', 'contrast', 'center_occlusion', 'rotation')
LABELS = {'gaussian_noise': 'Gaussian noise', 'gaussian_blur': 'Gaussian blur', 'brightness': 'Brightness',
          'contrast': 'Contrast', 'center_occlusion': 'Center occlusion', 'rotation': 'Rotation'}
QUARTILES = ('q1_low', 'q2_mid_low', 'q3_mid_high', 'q4_high')


def require(value, message):
    global COUNT
    COUNT += 1
    if not value:
        raise AssertionError(message)


def near(actual, expected, label, tol=2e-12):
    global NUMERIC
    NUMERIC += 1
    require(math.isfinite(float(actual)) and math.isclose(float(actual), float(expected), rel_tol=tol, abs_tol=tol),
            f'{label}: {actual!r} != {expected!r}')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode())


def load(path):
    def unique(pairs):
        result = {}
        for name, value in pairs:
            require(name not in result, 'Duplicate JSON key')
            result[name] = value
        return result
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique,
        parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def sealed_payload(value):
    data = dict(value); expected = data.pop('payload_sha256')
    require(canonical(data) == expected, 'Canonical payload seal')


def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        require(len(fields) == len(set(fields)), 'Duplicate CSV field')
        return fields, list(reader)


def all_records(value):
    if isinstance(value, dict):
        if set(('path', 'sha256')).issubset(value):
            yield value
        for item in value.values():
            yield from all_records(item)
    elif isinstance(value, list):
        for item in value:
            yield from all_records(item)


def verify_capture():
    capture = load(RAW / 'CAPTURE.json')
    require(sha((RAW / 'CAPTURE.json').read_bytes()) ==
            '473d5fba90c3fc0d044733ffb19e1f2955f08df96f89d4c643ad54d6ff15ca09', 'Capture seal')
    for item in capture['bindings']:
        raw = Path(item['snapshot']).read_bytes()
        require(len(raw) == item['bytes'] and sha(raw) == item['sha256'], 'Captured bytes changed')
    state = load(RAW / 'pipeline_status.json')
    jobs = {j['id']: j for j in state['jobs']}
    for job, source, pid in [('robustness_aggregate', 'aggregate_formal_robustness.py', 43500),
                              ('query_analysis', 'run_transactions_query_analysis.py', 40968)]:
        row = jobs[job]
        require(row['status'] == 'completed' and row['exit_code'] == 0 and row['pid'] == pid, 'Original parent job status')
        require(sha((RAW / 'source' / source).read_bytes()) == row['entrypoint_sha256'], 'Frozen source entry SHA')
    return capture, {name: jobs[name] for name in ('robustness_aggregate', 'query_analysis')}


def audit_aggregate():
    root = RAW / 'aggregate'
    manifest = load(root / 'aggregation_manifest.json'); sealed_payload(manifest)
    config = load(root / 'aggregation_run_config.json'); immutable = config['immutable_config']
    require(canonical(immutable) == config['config_sha256'] == manifest['config_sha256'], 'Aggregate canonical config')
    require(manifest['status'] == 'completed' and manifest['flat_source_rows'] == 3960 and
            manifest['validated_input_run_count'] == manifest['expected_input_run_count'] == 4 and
            manifest['figure_count'] == 22 and manifest['task_aggregation_used'] is False, 'Aggregate matrix')
    actual_files = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} - {'aggregation_manifest.json'}
    require(set(manifest['artifacts']) == actual_files, 'Aggregate complete artifact set')
    for rel, item in manifest['artifacts'].items():
        raw = (root / rel).read_bytes()
        require(sha(raw) == item['sha256'] and len(raw) == item['bytes'], 'Aggregate artifact bytes')
    for field, name in [('aggregator_sha256', 'aggregate_formal_robustness.py'),
                        ('common_validator_sha256', 'formal_robustness_common.py')]:
        require(immutable[field] == sha((RAW / 'source' / name).read_bytes()), 'Aggregate frozen code')
    require(immutable['plot_metrics'] == ['r_at_1', 'official_trapezoid_mAP'] and immutable['png_dpi'] == 600,
            'Frozen plot config')
    nested = load(root / 'robustness_all_tasks.json')
    require(nested['run_count'] == 4 and nested['flat_row_count'] == 3960 and
            nested['task_aggregation_used'] is False and nested['official_tasks_remain_separate'] is True,
            'Aggregate JSON scope')
    fields, rows = csv_rows(root / 'source_data/robustness_all_tasks_source.csv')
    expected_keys = {(ds, var, task, corruption, s, metric) for ds in TASKS for var in ('visual', 'full')
                     for task in TASKS[ds] for corruption in CORRUPTIONS for s in range(1, 6) for metric in METRICS}
    index = {(r['dataset'], r['variant'], r['task'], r['corruption'], int(r['severity_index']), r['metric']): r for r in rows}
    require(len(rows) == len(index) == 3960 and set(index) == expected_keys, 'All aggregate keys')
    require(set(nested['results']) == set(TASKS), 'Exact nested dataset set')
    for ds in TASKS:
        require(set(nested['results'][ds]) == {'visual', 'full'}, 'Nested variant set')
        for variant in ('visual', 'full'):
            require(set(nested['results'][ds][variant]) == set(TASKS[ds]), 'Nested task set')
            for task in TASKS[ds]:
                node = nested['results'][ds][variant][task]
                require(set(node['corruptions']) == set(CORRUPTIONS), 'Nested family keys')
                for corruption in CORRUPTIONS:
                    require(set(node['corruptions'][corruption]) == set(map(str, range(1, 6))), 'Nested severity keys')
    for key, row in index.items():
        ds, variant, task, corruption, severity, metric = key
        node = nested['results'][ds][variant][task]
        values = node['corruptions'][corruption][str(severity)]
        clean, corrupt = node['clean'][metric], values['metrics'][metric]
        drop = clean - corrupt
        require(int(row['seed']) == 1 and int(row['queries']) == TASKS[ds][task], 'Aggregate seed/query count')
        for field, expected in [('clean_fraction', clean), ('corrupted_fraction', corrupt),
            ('absolute_drop_fraction', drop), ('percentage_point_drop', 100 * drop)]:
            near(float(row[field]), expected, 'Aggregate ' + field)
        for field, expected in [('relative_drop_fraction', drop / clean if clean else None),
                               ('relative_drop_percent', 100 * drop / clean if clean else None),
                               ('retained_percent_of_clean', 100 * corrupt / clean if clean else None)]:
            if expected is None:
                require(row[field] == '', 'Undefined relative/retained field must be empty')
            else:
                near(row[field], expected, 'Aggregate ' + field, 2e-10)
        declared = values['degradation_vs_clean'][metric]
        near(declared['clean'], clean, 'Nested clean')
        near(declared['corrupted'], corrupt, 'Nested corrupt')
        near(declared['absolute_drop_fraction'], drop, 'Nested drop')
    figure_index = load(root / 'figure_index.json')
    require(len(figure_index['figures']) == 22, 'Figure count')
    figure_keys = set(); svg_review = []
    for figure in figure_index['figures']:
        key = (figure['dataset'], figure['task'], figure['metric'])
        require(key not in figure_keys, 'Unique figure key'); figure_keys.add(key)
        actual_fields, figure_rows = csv_rows(root / figure['source_csv'])
        selected = [r for r in rows if (r['dataset'], r['task'], r['metric']) == key]
        selected.sort(key=lambda r: (('visual', 'full').index(r['variant']), CORRUPTIONS.index(r['corruption']), int(r['severity_index'])))
        require(actual_fields == fields and figure_rows == selected and len(selected) == 60, 'Figure source exact CSV/order')
        xml = ET.parse(root / figure['outputs']['svg'])
        tags = list(xml.getroot().iter())
        text_count = sum(n.tag.rsplit('}', 1)[-1] == 'text' for n in tags)
        image_count = sum(n.tag.rsplit('}', 1)[-1] == 'image' for n in tags)
        require(text_count > 0 and image_count == 0, 'Native SVG text/no raster')
        sizes = [float(m) for n in tags for m in re.findall(r'font-size:\s*([0-9.]+)', n.attrib.get('style', ''))]
        # Matplotlib may serialize shorthand font: 7px Arial rather than font-size.
        sizes += [float(m) for n in tags for m in re.findall(r'font:\s*(?:[^;]*? )?([0-9.]+)px', n.attrib.get('style', ''))]
        svg_review.append({'key': key, 'text_count': text_count, 'image_count': image_count,
                           'observed_style_sizes': sorted(set(sizes)), 'final_layout_or_geometry_validated': False})
    require(figure_keys == {(ds, task, metric) for ds in TASKS for task in TASKS[ds]
                           for metric in ('r_at_1', 'official_trapezoid_mAP')}, 'Exact figure coverage')
    for metric in ('r_at_1', 'official_trapezoid_mAP'):
        name = f'robustness_{metric.lower()}_task_tables.tex'
        text = (root / 'tables' / name).read_text(encoding='utf-8')
        table_rows = [line for line in text.splitlines() if line.startswith(('Visual &', 'Full &'))]
        expected = []
        for task in sorted(t for ds in TASKS for t in TASKS[ds]):
            ds = next(d for d in TASKS if task in TASKS[d])
            for variant in ('visual', 'full'):
                for corruption in CORRUPTIONS:
                    group = [index[ds, variant, task, corruption, s, metric] for s in range(1, 6)]
                    cells = [100 * float(group[0]['clean_fraction'])] + [100 * float(r['corrupted_fraction']) for r in group]
                    expected.append(f'{variant.title()} & {LABELS[corruption]} & ' + ' & '.join(f'{v:.2f}' for v in cells) + ' \\\\')
        require(table_rows == expected and len(table_rows) == 132, 'LaTeX table exact displayed values')
    return {'rows': 3960, 'new_artifacts': len(actual_files), 'figure_groups': 22, 'svg_review': svg_review,
        'input_run_adoption_reconciliation': 'Separate annex required, especially pending SUES Full root',
        'figure_limit': 'Source/CSV/text/raster/table consistency checked; exact plotted path geometry and final page preview not validated. Source fonts 6/7pt violate requested final minimum8pt, so these are not final figure delivery.'}


def npy(raw):
    require(raw[:6] == b'\x93NUMPY', 'NPY magic')
    version = raw[6:8]; require(version in (b'\x01\x00', b'\x02\x00', b'\x03\x00'), 'NPY version')
    width = 2 if version[0] == 1 else 4
    n = int.from_bytes(raw[8:8 + width], 'little')
    header = ast.literal_eval(raw[8 + width:8 + width + n].decode('utf-8' if version[0] == 3 else 'latin1').strip())
    require(set(header) == {'descr', 'fortran_order', 'shape'} and header['fortran_order'] is False and
            len(header['shape']) == 1, 'NPY vector/order')
    dtype, count = header['descr'], header['shape'][0]
    payload = raw[8 + width + n:]
    numeric = {'|b1': ('?', 1), '|i1': ('b', 1), '<i8': ('q', 8), '<i4': ('i', 4), '<f4': ('f', 4), '<f8': ('d', 8)}
    if dtype in numeric:
        code, size = numeric[dtype]
        require(len(payload) == count * size, 'NPY payload size')
        values = list(struct.unpack('<' + str(count) + code, payload))
    else:
        match = re.fullmatch(r'([<|])([US])([0-9]+)', dtype)
        require(match is not None, 'Supported fixed text NPY dtype')
        size = int(match[3]) * (4 if match[2] == 'U' else 1)
        require(len(payload) == count * size, 'Text payload length')
        encoding = 'utf-32-le' if match[2] == 'U' else 'utf-8'
        values = [payload[i:i + size].decode(encoding).rstrip('\x00') for i in range(0, len(payload), size)]
    return values, dtype


def load_arrays(path):
    expected = {'margin', 'correct', 'per_query_official_trapezoid_AP', 'reciprocal_rank', 'query_paths',
                'query_labels', 'top1_gallery_indices', 'top1_gallery_paths', 'top1_gallery_labels'}
    with zipfile.ZipFile(path) as z:
        require(set(z.namelist()) == {n + '.npy' for n in expected} and len(z.namelist()) == 9, 'NPZ field set')
        parsed = {name: npy(z.read(name + '.npy')) for name in expected}
    data = {n: v[0] for n, v in parsed.items()}
    count = len(data['correct']); require(count > 0 and all(len(v) == count for v in data.values()), 'NPZ lengths')
    require(parsed['correct'][1] == '|b1', 'Boolean correctness')
    for key in ('query_paths', 'top1_gallery_paths'):
        data[key] = [s.strip().replace('\\', '/').casefold() for s in data[key]]
    require(len(set(data['query_paths'])) == count and all(data['query_paths']), 'Unique normalized queries')
    require(data['correct'] == [q == g for q, g in zip(data['query_labels'], data['top1_gallery_labels'])], 'Correctness versus labels')
    for key in ('per_query_official_trapezoid_AP', 'reciprocal_rank', 'margin'):
        require(all(math.isfinite(v) for v in data[key]), 'Finite stored values')
    return data


def exact_mcnemar_log10(a, b):
    require(type(a) is int and type(b) is int and min(a, b) >= 0, 'Nonnegative integer discordance')
    n = a + b
    if n == 0:
        return 0.0
    term = 1; total = 1
    for i in range(1, min(a, b) + 1):
        term = term * (n - i + 1) // i
        total += term
    return min(0.0, math.log10(2 * total) - n * math.log10(2.0))


def p_text(value):
    if value >= -300:
        return f'{min(1.0, 10.0 ** value):.12g}'
    exp = math.floor(value)
    return f'{10.0 ** (value-exp):.8f}e{exp:+d}'


def check_holm(records, family):
    sorted_rows = sorted(enumerate(records), key=lambda p: p[1]['exact_two_sided_mcnemar_log10_p'])
    running = -math.inf
    for rank, (_, row) in enumerate(sorted_rows):
        running = max(running, min(0.0, row['exact_two_sided_mcnemar_log10_p'] + math.log10(len(records) - rank)))
        near(row['holm_adjusted_log10_p'], running, 'Holm value')
        require(row['holm_adjusted_p'] == p_text(running) and row['holm_family'] == family and
                row['holm_family_size'] == len(records) and row['holm_status'] == 'complete' and
                row['reject_holm_0_05'] == (running < math.log10(.05)), 'Holm metadata and decision')


def official_authority(cfg):
    # Follow only the explicit adopted prior-evaluation chain, never arbitrary
    # same-named rejected reports or scientific attachment paths.
    raw = (RAW / 'authority/official.json').read_bytes(); node = load(RAW / 'authority/official.json')
    blobs = [raw]; seen = set()
    while 'inherited_previous_eval_adoption' in node:
        item = node['inherited_previous_eval_adoption']
        if 'path' not in item:
            break
        path = Path(item['path']).resolve(strict=True)
        require(path.is_relative_to(HERE.parent) and path.suffix == '.json' and path.name.startswith('ROOT_'), 'Only accepted metadata chain')
        require(str(path) not in seen, 'Adoption cycle'); seen.add(str(path))
        data = path.read_bytes(); require(sha(data) == item['sha256'], 'Accepted predecessor SHA')
        target = RAW / 'authority' / path.name
        with target.open('xb') as stream:
            stream.write(data)
        EXTRA_BINDINGS.append({'path': str(path), 'snapshot': str(target), 'sha256': sha(data), 'bytes': len(data)})
        blobs.append(data); node = json.loads(data)
    indexed = {}
    for blob in blobs:
        for record in all_records(json.loads(blob)):
            indexed.setdefault(record['sha256'], []).append(record)
    bound = 0; missing = []
    for item in cfg['input_artifacts']:
        found = [r for r in indexed.get(item['sha256'], []) if r.get('bytes') == item['bytes'] and
                 Path(r['path']).resolve() == Path(item['path']).resolve()]
        if found:
            bound += 1
        else:
            missing.append({k: item[k] for k in ('dataset', 'variant', 'seed', 'task', 'sha256')})
    return {'metadata_nodes': len(blobs), 'exact_input_path_sha_size_bindings': bound, 'not_directly_found': missing,
        'all_12_run_identifiers_adopted': all(f'formal_main/{ds}/{v}/seed_{s}/resnet18/dim_512' in
             load(RAW / 'authority/official.json')['accepted_run_identifiers'] for ds in TASKS for v in ('visual', 'full') for s in (1,2,3))}


def mean(values):
    return math.fsum(values) / len(values)


def query_audit():
    root = RAW / 'query'; cfg = load(root / 'transactions_query_analysis_config.json')
    cfg_sha = sha((root / 'transactions_query_analysis_config.json').read_bytes())
    manifest = load(root / 'transactions_query_analysis_manifest.json'); sealed_payload(manifest)
    status = load(root / 'transactions_query_analysis_status.json')
    require(status['status'] == manifest['status'] == 'completed' and status['manifest_sha256'] ==
            sha((root / 'transactions_query_analysis_manifest.json').read_bytes()), 'Query completion binding')
    require(cfg['bootstrap'] == {'confidence': .95, 'samples': 10000, 'seed': 20260730, 'unit': 'paired official query'} and
            cfg['minimum_stratum_queries_for_claim'] == 100 and cfg['calibration']['bins'] == 15, 'Frozen statistical settings')
    for field, filename in [('analysis_code_sha256', 'run_transactions_query_analysis.py'),
                            ('primitive_code_sha256', 'transactions_query_analysis.py'),
                            ('protocol_sha256', 'TRANSACTIONS_EXTENSION_PROTOCOL.md')]:
        require(cfg[field] == sha((RAW / 'source' / filename).read_bytes()), 'Frozen query source binding')
    require(cfg_sha == manifest['config_sha256'] == status['config_sha256'], 'Query config SHA')
    for name in ('t4', 't5', 't4_csv', 't5_csv'):
        actual = root / Path(manifest[name + '_path']).name
        require(sha(actual.read_bytes()) == manifest[name + '_sha256'], 'Query output SHA')
    t4 = load(root / 'transactions_t4_strata.json'); t5 = load(root / 'transactions_t5_selective_calibration.json')
    sealed_payload(t4); sealed_payload(t5)
    require(t4['source_config_sha256'] == t5['source_config_sha256'] == cfg_sha, 'Statistical config identity')
    pairs = {(ds, task, seed) for ds in TASKS for task in TASKS[ds] for seed in (1,2,3)}
    factors = {(factor, level) for factor in ('content_entropy_quartile', 'style_entropy_quartile', 'visual_margin_quartile') for level in QUARTILES}
    factors |= {('visual_semantic_top1_identity_agreement', level) for level in ('agree','disagree')}
    t4_index = {(r['dataset'],r['task'],r['seed'],r['factor'],r['level']):r for r in t4['rows']}
    require(len(t4['rows']) == len(t4_index) == 462 and set(t4_index) == {p+f for p in pairs for f in factors}, 'T4 exact keys')
    native = {(r['dataset'],r['task'],r['seed'],r['variant']):r for r in t5['native_rows']}
    comparison = {(r['dataset'],r['task'],r['seed'],r['requested_coverage']):r for r in t5['paired_comparisons']}
    require(len(t5['native_rows']) == len(native) == 66 and set(native) == {p+(v,) for p in pairs for v in ('visual','full')}, 'T5 native exact keys')
    require(len(t5['paired_comparisons']) == len(comparison) == 132 and set(comparison) == {p+(c,) for p in pairs for c in (.5,.75,.9,1.)}, 'T5 comparison exact keys')
    inputs = {}
    for idx, item in enumerate(cfg['input_artifacts']):
        path = RAW / f'query_inputs/{idx:03d}.npz'
        require(sha(path.read_bytes()) == item['sha256'] and path.stat().st_size == item['bytes'], 'Stored NPZ source binding')
        key = (item['dataset'],item['task'],item['seed'],item['variant'])
        require(key not in inputs, 'Unique NPZ key'); inputs[key] = load_arrays(path)
    require(set(inputs) == set(native), 'NPZ exact keys')
    t4_inference = []
    for row in t4['rows']:
        summary = row['summary']; count = summary['queries']; eligible = count >= 100
        require(summary['minimum_queries_for_claim'] == 100 and summary['performance_claim_eligible'] == eligible, 'Stratum claim threshold')
        if count == 0:
            require(summary['metrics'] is None and summary['top1_discordance'] is None, 'Empty stratum withheld')
            continue
        for metric in ('r_at_1','official_trapezoid_mAP','MRR'):
            val = summary['metrics'][metric]
            near(val['full_minus_visual'], val['full'] - val['visual'], 'Declared stratum mean difference')
            require(0 <= val['visual'] <= 1 and 0 <= val['full'] <= 1, 'Stratum metric range')
            ci = val['paired_bootstrap_95ci']
            require((ci is None) if not eligible else (isinstance(ci,list) and len(ci)==2 and -1 <= ci[0] <= ci[1] <= 1), 'CI withheld/range only')
        discord = summary['top1_discordance']
        if eligible:
            near(discord['exact_two_sided_mcnemar_log10_p'], exact_mcnemar_log10(discord['visual_only_correct'],discord['full_only_correct']), 'Exact integer binomial McNemar', 2e-8)
            require(discord['exact_two_sided_mcnemar_p'] == p_text(discord['exact_two_sided_mcnemar_log10_p']), 'Raw p serialization')
            t4_inference.append(discord)
        else:
            require(discord['exact_two_sided_mcnemar_log10_p'] is None and discord['exact_two_sided_mcnemar_p'] is None and discord['holm_status'] == 'withheld_below_100_query_claim_threshold', 'Small stratum test withheld')
    for pair in sorted(pairs):
        ds, task, seed = pair; n = TASKS[ds][task]
        visual = inputs[pair+('visual',)]; full_orig = inputs[pair+('full',)]
        lookup = {path:i for i,path in enumerate(full_orig['query_paths'])}
        require(set(lookup) == set(visual['query_paths']), 'Visual/full exact query membership')
        order = [lookup[path] for path in visual['query_paths']]
        full = {name:[values[i] for i in order] for name,values in full_orig.items()}
        require(visual['query_labels'] == full['query_labels'] and len(order)==n, 'Aligned labels/count')
        values = {'visual':visual, 'full':full}; selections = {}
        for variant, data in values.items():
            declared = native[pair+(variant,)]
            require(declared['query_membership_sha256'] == canonical(sorted(zip(data['query_paths'],data['query_labels']))), 'Native query membership SHA')
            ranking = sorted(range(n), key=lambda i:-data['margin'][i]); correct = data['correct']
            risk = declared['risk_coverage']; require(risk['queries']==n and len(risk['rows'])==10, 'Risk-coverage count')
            errors=0; prefixes=[]
            for position, index in enumerate(ranking,1):
                errors += not correct[index]; prefixes.append(errors/position)
            near(risk['AURC_discrete_all_prefixes'],mean(prefixes),'AURC from all actual prefixes')
            for i,row in enumerate(risk['rows'],1):
                coverage=i/10; count=min(n,max(1,math.ceil(coverage*n))); selected=ranking[:count]
                require(row['requested_coverage']==coverage and row['selected_queries']==count and
                        row['selection_index_membership_sha256']==canonical(sorted(selected)), 'Risk selection exact')
                near(row['realized_coverage'],count/n,'Realized coverage')
                accuracy=sum(correct[j] for j in selected)/count
                near(row['selective_r_at_1'],accuracy,'Selective accuracy'); near(row['selective_risk'],1-accuracy,'Selective risk')
            cal=declared['calibration']; require(cal['bins']==15 and cal['fitted_calibration_parameter'] is False,'Unfitted calibration')
            confidence=[min(1.,max(0.,v/2)) for v in data['margin']]
            bins=[[] for _ in range(15)]
            for i,v in enumerate(confidence): bins[min(int(v*15),14)].append(i)
            ece=0.
            require(len(cal['reliability_bins'])==15,'Complete calibration bins')
            for i,(indices,row) in enumerate(zip(bins,cal['reliability_bins'])):
                require(row['bin']==i+1 and row['count']==len(indices),'Calibration bin/count')
                near(row['lower_inclusive'],i/15,'Bin lower'); near(row['upper_inclusive_only_for_last_bin'],(i+1)/15,'Bin upper')
                if indices:
                    accuracy=sum(correct[j] for j in indices)/len(indices); conf=mean([confidence[j] for j in indices])
                    contribution=len(indices)/n*abs(accuracy-conf); ece+=contribution
                    near(row['accuracy'],accuracy,'Bin accuracy'); near(row['mean_fixed_normalized_margin_confidence'],conf,'Bin confidence')
                else:
                    contribution=0.; require(row['accuracy'] is None and row['mean_fixed_normalized_margin_confidence'] is None,'Empty bin null')
                near(row['weighted_absolute_gap'],contribution,'Bin contribution')
            near(cal['ECE'],ece,'ECE from real margins')
            selections[variant]={c:set(ranking[:min(n,max(1,math.ceil(c*n)))]) for c in (.5,.75,.9,1.)}
        for coverage in (.5,.75,.9,1.):
            row=comparison[pair+(coverage,)]; count=min(n,max(1,math.ceil(coverage*n)))
            vset,fset=selections['visual'][coverage],selections['full'][coverage]
            vu={i for i in vset if visual['correct'][i]}; fu={i for i in fset if full['correct'][i]}
            require(row['selected_queries_per_variant']==count and row['visual_full_selected_query_overlap']==len(vset&fset),'Paired selected count/overlap')
            near(row['realized_coverage'],count/n,'Paired coverage')
            for field,val in [('visual_selective_r_at_1',len(vu)/count),('full_selective_r_at_1',len(fu)/count),
                              ('full_minus_visual_selective_r_at_1',(len(fu)-len(vu))/count)]: near(row[field],val,'Paired '+field)
            success=row['coverage_constrained_success']; a,b=len(vu-fu),len(fu-vu)
            require(success['visual_only_success']==a and success['full_only_success']==b,'Actual coverage utility discordance')
            for field,val in [('visual_rate',len(vu)/n),('full_rate',len(fu)/n),('full_minus_visual_rate',(len(fu)-len(vu))/n)]: near(success[field],val,'Utility '+field)
            near(success['exact_two_sided_mcnemar_log10_p'],exact_mcnemar_log10(a,b),'Actual T5 McNemar',2e-8)
            require(success['exact_two_sided_mcnemar_p']==p_text(success['exact_two_sided_mcnemar_log10_p']),'T5 p text')
        sorted_margin=sorted(visual['margin']); cuts=[]
        for p in (.25,.5,.75):
            pos=(n-1)*p; i=int(pos); cuts.append(sorted_margin[i]+(sorted_margin[min(i+1,n-1)]-sorted_margin[i])*(pos-i))
        assignments=[bisect.bisect_left(cuts,v) for v in visual['margin']]
        for quartile,level in enumerate(QUARTILES):
            row=t4_index[pair+('visual_margin_quartile',level)]; selected=[i for i,q in enumerate(assignments) if q==quartile]
            require(row['membership_sha256']==canonical(sorted(visual['query_paths'][i] for i in selected)),'Actual margin stratum membership')
            require(row['summary']['queries']==len(selected),'Actual margin stratum count')
            for actual,expected in zip(row['metadata']['quartile_cutpoints'],cuts): near(actual,expected,'Margin cutpoint')
            if not selected: continue
            summary=row['summary']; d=summary['top1_discordance']
            require(d['visual_only_correct']==sum(visual['correct'][i] and not full['correct'][i] for i in selected) and
                    d['full_only_correct']==sum(full['correct'][i] and not visual['correct'][i] for i in selected),'Actual margin discordance')
            for metric,field in [('r_at_1','correct'),('official_trapezoid_mAP','per_query_official_trapezoid_AP'),('MRR','reciprocal_rank')]:
                for variant in ('visual','full'): near(summary['metrics'][metric][variant],mean([values[variant][field][i] for i in selected]),'Actual margin '+metric)
    check_holm(t4_inference,'T4 eligible visual-versus-full stratum R@1 comparisons')
    check_holm([r['coverage_constrained_success'] for r in t5['paired_comparisons']],'T5 coverage-constrained visual-versus-full comparisons')
    check_query_csv(root,t4,t5)
    authority=official_authority(cfg)
    return {'source_npz':66,'task_seed_pairs':33,'T4_rows':462,'T4_margin_strata_recomputed':132,
        'T4_other_strata_membership_and_values_recomputed':False,'T4_eligible_Holm_family':len(t4_inference),
        'T5_native_query_recomputed':66,'T5_paired_query_recomputed':132,
        'bootstrap_CI_recomputed':False,'source_authority':authority,
        'limits':['T4 entropy/semantic memberships and associated values are only aggregate/CSV/threshold consistency checked; no cache/image content is read.',
                  'All bootstrap intervals are retained producer values, checked only for eligibility/nulls/finite bounds, not resampled or independently accepted inference.',
                  'T4 McNemar recomputed from saved discordance counts, with actual query recount only for 132 visual-margin strata. T5 selection/calibration/AURC/discordance are independently recomputed from actual NPZ values.',
                  'Exact binomial integer sums replace producer lgamma/logsumexp; log10 agreement uses absolute/relative2e-8, ordinary means use math.fsum within2e-12; not bitwise NumPy reductions.',
                  'Saved AP/RR/margins are audited as source values; no model/full ranking/all-positive-rank AP recomputation or current checkpoint/cache/image SHA verification. All historical authority gaps remain.']}


def check_query_csv(root,t4,t5):
    _, rows=csv_rows(root/'transactions_t4_strata.csv'); require(len(rows)==462,'T4 CSV count')
    for actual,row in zip(rows,t4['rows']):
        summary=row['summary']; metrics=summary.get('metrics') or {}; discordance=summary.get('top1_discordance') or {}
        expected={key:row[key] for key in ('dataset','task','seed','factor','level','membership_sha256')}
        expected.update(queries=summary['queries'],performance_claim_eligible=summary['performance_claim_eligible'],holm_adjusted_p=discordance.get('holm_adjusted_p',''))
        for metric,short in [('r_at_1','r_at_1'),('official_trapezoid_mAP','mAPtrap'),('MRR','MRR')]:
            for source in ('visual','full','full_minus_visual'): expected[source+'_'+short]=metrics.get(metric,{}).get(source,'')
        require(actual=={k:str(v) for k,v in expected.items()},'Exact T4 CSV JSON serialization/order')
    _,rows=csv_rows(root/'transactions_t5_selective_comparisons.csv'); require(len(rows)==132,'T5 CSV count')
    for actual,row in zip(rows,t5['paired_comparisons']):
        expected={key:row[key] for key in ('dataset','task','seed','requested_coverage','realized_coverage','visual_selective_r_at_1','full_selective_r_at_1','full_minus_visual_selective_r_at_1','visual_full_selected_query_overlap')}
        success=row['coverage_constrained_success']
        for prefix in ('visual','full','full_minus_visual'): expected[prefix+'_coverage_constrained_success']=success[prefix+'_rate']
        expected['holm_adjusted_p']=success['holm_adjusted_p']
        require(actual=={k:str(v) for k,v in expected.items()},'Exact T5 CSV JSON serialization/order')


def main():
    capture, jobs=verify_capture()
    aggregate=audit_aggregate(); query=query_audit()
    require(not any(n.split('.')[0] in {'numpy','torch','PIL','matplotlib','scipy','cv2'} for n in sys.modules),'No science imports')
    result={'schema':'post-robustness-independent-bounded-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'passed_with_stated_limits':True,'root_adoption_pending':True,'aggregate_SUES_Full_input_adoption_pending':True,
        'source':{'path':str(Path(__file__).resolve()),'sha256':sha(Path(__file__).read_bytes())},
        'capture':{'path':str(RAW/'CAPTURE.json'),'sha256':sha((RAW/'CAPTURE.json').read_bytes())},
        'assertions':COUNT,'numerical_comparisons':NUMERIC,'aggregate':aggregate,'query':query,
        'metadata_chain_additions':EXTRA_BINDINGS,'parent_stage_records':jobs,
        'original_parent_exit_only_not_independent_dual_handle_proof':True,'scientific_imports':[],
        'weights_cache_images_read':False,'old_science_jobs_or_suites_rerun':False,'live_state_modified':False,
        'limits':['Aggregate numerical/table/source-CSV consistency is checked here; full 4-run root-adopted input reconciliation is a separate mandatory annex.',
                  'Producer manuscript_result fields and stage exit0 are not independently established scientific acceptance.',
                  'Original aggregate figures are not final 8pt editable-paper figure delivery; no final Overleaf/publication update is made.']}
    target=HERE/'REVIEW.json'
    with target.open('x',encoding='utf-8',newline='\n') as handle: json.dump(result,handle,indent=2,ensure_ascii=False);handle.write('\n')
    print(json.dumps({'report':str(target),'sha256':sha(target.read_bytes()),'assertions':COUNT,'comparisons':NUMERIC,
                      'official_exact_npz_bindings':query['source_authority']['exact_input_path_sha_size_bindings']}))


if __name__=='__main__':
    main()
