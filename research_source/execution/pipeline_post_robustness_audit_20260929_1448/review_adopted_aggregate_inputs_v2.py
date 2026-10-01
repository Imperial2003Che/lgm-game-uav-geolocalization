"""Additive four-adopted-run source reconciliation; stdlib only, one execution.

Requires the root's actual SUES Full adoption path and expected SHA argument.
Never opens weight, cache, image or NPZ bytes. Does not rerun review_post.py.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
OUT = HERE / 'adopted_inputs_v2'
CHECKS = 0
BINDINGS = []
METRICS = ('r_at_1', 'r_at_5', 'r_at_10', 'r_at_20', 'official_trapezoid_mAP', 'MRR')
CORRUPTIONS = ('gaussian_noise', 'gaussian_blur', 'brightness', 'contrast', 'center_occlusion', 'rotation')
ROOTS = (
    ('university1652', 'visual', 'robustness_audit_20260929_0946', 'ROOT_VISUAL1_ADOPTION.json',
     '81ec5d80b7370ae5dc79c3f12e0633b88ade73be3422ec155ea11def68713cc6'),
    ('university1652', 'full', 'robustness_full_audit_20260929_1247', 'ROOT_FULL1_ADOPTION.json',
     'ea8c3065092db79c67005b6b6aa1b54a5433ba39ae4b143504f09618f98fd1f5'),
    ('sues200', 'visual', 'robustness_sues_visual_audit_20260929_1351', 'ROOT_SUES_VISUAL1_ADOPTION.json',
     'a6795283cb384c77732bdb1e63af93d582d7844879f415e45ef38c8861d3af74'))


def require(value, message):
    global CHECKS
    CHECKS += 1
    if not value:
        raise AssertionError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), default=str).encode())


def parse(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'duplicate JSON key')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def norm(path):
    return str(Path(path)).replace('/', '\\').casefold()


def bound_read(path, sha256, size=None, snapshot=None, authority=None):
    path = Path(path)
    require(path.suffix.lower() in ('.json', '.csv', '.py'), 'only small metadata input types')
    raw = path.read_bytes()
    require(digest(raw) == sha256, f'input SHA: {path}')
    require(size is None or len(raw) == size, f'input bytes: {path}')
    item = {'path': str(path), 'sha256': sha256, 'bytes': len(raw)}
    if snapshot:
        target = OUT / snapshot
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
        item['snapshot'] = str(target)
    if authority:
        item['authority'] = authority
    BINDINGS.append(item)
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sues-full-root', required=True, type=Path)
    parser.add_argument('--sues-full-root-sha', required=True)
    args = parser.parse_args()
    require(args.sues_full_root.parent == EX / 'robustness_sues_full_audit_20260929_1448',
            'exact requested root directory')
    require(len(args.sues_full_root_sha) == 64 and all(c in '0123456789abcdef' for c in args.sues_full_root_sha),
            'explicit SHA required')
    OUT.mkdir(exist_ok=False)
    prior = parse(bound_read(HERE / 'REVIEW.json',
        'e350ca764a7b6a053afbab3062eee6412306685ffeb2c5b9185578896ff451bc'))
    require(prior['passed_with_stated_limits'] is True, 'prior bounded checks passed')
    authority = prior['query']['source_authority']
    require(authority['exact_input_path_sha_size_bindings'] == 66 and
            authority['not_directly_found'] == [] and authority['all_12_run_identifiers_adopted'] is True,
            'mandatory exact official input authority')
    capture = parse(bound_read(HERE / 'a1/CAPTURE.json',
        '473d5fba90c3fc0d044733ffb19e1f2955f08df96f89d4c643ad54d6ff15ca09'))
    cap = {norm(x['snapshot']): x for x in capture['bindings']}
    def captured(relative):
        path = HERE / 'a1/aggregate' / relative
        item = cap[norm(path)]
        return bound_read(path, item['sha256'], item['bytes'], authority='main immutable capture')
    agg_config = parse(captured('aggregation_run_config.json'))['immutable_config']
    aggregate = parse(captured('robustness_all_tasks.json'))
    rows = list(csv.DictReader(captured('source_data/robustness_all_tasks_source.csv').decode('utf-8-sig').splitlines()))
    flat = {(r['dataset'], r['variant'], r['task'], r['corruption'], int(r['severity_index']), r['metric']): r for r in rows}
    require(len(flat) == len(rows) == 3960, 'complete unique main-reviewed flat rows')
    roots = list(ROOTS) + [('sues200', 'full', args.sues_full_root.parent.name,
                          args.sues_full_root.name, args.sues_full_root_sha)]
    task_count = 0
    matched_clean = 0
    matched_corrupt = 0
    run_reports = []
    alias_checks = []
    for dataset, variant, folder, root_name, root_sha in roots:
        root_path = EX / folder / root_name
        root = parse(bound_read(root_path, root_sha, snapshot=f'{dataset}/{variant}/ROOT.json'))
        require(root['accepted_with_stated_limits'] is True, 'root accepted_with_stated_limits')
        index = {norm(x['path']): x for x in root['bindings']}
        require(len(index) == len(root['bindings']), 'root binding unique paths')
        tree = root_path.parent / 'a1/r'
        def adopted(relative):
            source = tree / relative
            record = index[norm(source)]
            return bound_read(source, record['sha256'], record['bytes'],
                snapshot=f'{dataset}/{variant}/{relative}', authority=f'{root_path}#{root_sha}')
        manifest_raw = adopted('robustness_manifest.json')
        manifest = parse(manifest_raw)
        payload = dict(manifest); payload_sha = payload.pop('payload_sha256')
        require(canonical(payload) == payload_sha, 'run manifest payload seal')
        config = parse(adopted('run_config.json'))
        immutable = config['immutable_config']
        declared = agg_config['input_manifests'][f'{dataset}/{variant}/seed_1']
        declared_path = Path(declared['path'])
        expected_declared = Path(r'C:\项目\LGM\02_代码与实验\正式实验工程\lgm_game_pytorch\runs\formal_robustness') / dataset / variant / 'seed_1/robustness_manifest.json'
        expected_alias = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_robustness') / dataset / variant / 'seed_1/robustness_manifest.json'
        require(norm(declared_path) == norm(expected_declared), 'exact producer manifest path')
        production_manifest = index[norm(expected_alias)]
        require(os.path.samefile(declared_path, expected_alias), 'junction alias must be same file, not same bytes')
        alias_checks.append({'declared_path': str(declared_path), 'adopted_original_path': str(expected_alias),
                             'actual_samefile': True, 'current_bytes_rehashed': False})
        require(production_manifest['sha256'] == declared['sha256'] == digest(manifest_raw) and
                production_manifest['bytes'] == len(manifest_raw), 'original path and snapshot manifest binding')
        require(canonical(immutable) == config['run_config_sha256'] == manifest['run_config_sha256'] ==
                declared['run_config_sha256'], 'canonical config matches aggregate origin')
        require(immutable['dataset'] == manifest['dataset'] == dataset and
                immutable['checkpoint']['variant'] == manifest['variant'] == variant and
                immutable['checkpoint']['seed'] == 1 and manifest['status'] == 'completed', 'run identity')
        for aggregate_key, source_key in [('evaluator', 'robustness_evaluator'),
                ('formal_retrieval', 'formal_retrieval'), ('frozen_protocol', 'frozen_protocol')]:
            require(agg_config['shared_fingerprints'][aggregate_key] ==
                    immutable['sources'][source_key]['sha256'], 'frozen science fingerprint inherited')
        require(agg_config['shared_fingerprints']['corruption_matrix'] == canonical(immutable['corruption_matrix']),
                'frozen corruption matrix')
        tasks = set(immutable['official_task_scale'])
        require(set(aggregate['results'][dataset][variant]) == tasks, 'all official task keys')
        task_count += len(tasks)
        def metrics(relative):
            raw = adopted(relative)
            item = manifest['artifacts'][relative]
            require(digest(raw) == item['sha256'] and len(raw) == item['bytes'], 'metric also bound by run manifest')
            value = parse(raw)
            require(set(value['results']) == tasks and value['unit'] == 'fraction' and
                    value['full_gallery'] is True and value['clean_gallery_for_every_condition'] is True,
                    'complete fraction full-gallery task metrics')
            return value
        clean = metrics('clean/metrics.json')
        require(clean['condition']['kind'] == clean['condition']['name'] == 'clean', 'clean input identity')
        for task in tasks:
            require(aggregate['results'][dataset][variant][task]['clean'] == clean['results'][task],
                    'all clean fields exact adopted values')
            matched_clean += 1
        matrix = {x['name']: x for x in immutable['corruption_matrix']}
        require(set(matrix) == set(CORRUPTIONS), 'six fixed families')
        for corruption in CORRUPTIONS:
            for severity in range(1, 6):
                value = metrics(f'conditions/{corruption}/severity_{severity:02d}/metrics.json')
                condition = value['condition']; spec = matrix[corruption]
                require(condition['kind'] == 'corruption' and condition['name'] == corruption and
                        condition['severity_index'] == severity and condition['value'] == spec['values'][severity-1]
                        and condition['corruption_seed'] == immutable['corruption_seed'] == 20260727 and
                        condition['query_only'] is True and condition['gallery'] == 'clean', 'corruption identity')
                for field in ('parameter', 'units', 'implementation', 'display_name'):
                    require(condition[field] == spec[field], 'frozen condition description')
                require(set(value['degradation_vs_clean']) == tasks, 'complete adopted degradation tasks')
                for task in tasks:
                    node = aggregate['results'][dataset][variant][task]['corruptions'][corruption][str(severity)]
                    require(node['metrics'] == value['results'][task] and
                            node['degradation_vs_clean'] == value['degradation_vs_clean'][task],
                            'all corrupt and degradation fields exact adopted values')
                    matched_corrupt += 1
                    for metric in METRICS:
                        row = flat[(dataset, variant, task, corruption, severity, metric)]
                        require(int(row['queries']) == value['results'][task]['queries'] and
                                int(row['gallery']) == value['results'][task]['gallery'], 'CSV task scale')
                        for field, expected in [('checkpoint_sha256', immutable['checkpoint']['checkpoint_sha256']),
                            ('robustness_run_config_sha256', config['run_config_sha256']),
                            ('evaluator_sha256', immutable['sources']['robustness_evaluator']['sha256']),
                            ('frozen_protocol_sha256', immutable['sources']['frozen_protocol']['sha256']),
                            ('parameter', condition['parameter']), ('units', condition['units']),
                            ('corruption_display', condition['display_name'])]:
                            require(row[field] == expected, 'CSV inherited identity and exact condition fields')
                        require(float(row['value']) == condition['value'], 'CSV fixed corruption value')
        run_reports.append({'dataset': dataset, 'variant': variant, 'seed': 1, 'root': str(root_path),
            'root_sha256': root_sha, 'metrics_files': 31, 'tasks': len(tasks),
            'clean_tasks': len(tasks), 'corrupt_tasks': 30 * len(tasks)})
    require(task_count == matched_clean == 22 and matched_corrupt == 660, 'exact adopted totals')
    report = {'schema': 'adopted-aggregate-input-reconciliation.v1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'passed': True,
        'root_adoption_pending': True, 'aggregate_SUES_Full_input_adoption_pending': False,
        'source': {'path': str(Path(__file__).resolve()), 'sha256': digest(Path(__file__).read_bytes())},
        'assertions': CHECKS, 'run_reports': run_reports, 'clean_task_records': matched_clean,
        'corrupt_task_records': matched_corrupt, 'metric_files': 124,
        'input_bindings': BINDINGS, 'actual_junction_identity_checks': alias_checks,
        'prior_official_input_authority_mandatory_gate': authority,
        'limits': ['Joint adoption requires the unmodified main REVIEW and this annex.',
            'Existing query statistics limitations remain: bootstrap not resampled; entropy/semantic memberships not recomputed.',
            'No old science suite, NPZ, model, cache, image or checkpoint bytes are read by this annex.',
            'Upstream checkpoint/cache/image evidence and historical metadata-chain gaps remain inherited.',
            'Robustness is seed1 only, with no multi-seed SD or significance. No task/severity pooling.',
            'Full clean cached evidence and corrupted-query online CLIP differ in evidence path; diagnostic64 has no numerical parity gate.',
            'Producer figures are source-bound but not final geometry/layout-validated or minimum8pt-compliant.',
            'Root adoption is separate; original stage parent exit0 is not independent dual-handle exit proof.']}
    with (OUT / 'RECONCILIATION.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'passed': True, 'assertions': CHECKS, 'bindings': len(BINDINGS),
                      'report_sha256': digest((OUT / 'RECONCILIATION.json').read_bytes())}))


if __name__ == '__main__':
    main()
