"""Descriptive T3 results from exactly 12 adopted, sealed metrics; stdlib only."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
AUDIT = HERE.parent / 'transfer_audit_20260929_0647'
ROOT_PATH = AUDIT / 'ROOT_TRANSFER12_AND_NATIVE2_ADOPTION.json'
ROOT_SHA = 'fb7588357afa3e225b67088437233db397c067131fb8bc6adf97ce9ccbdd3bdd'
REVIEW_SHA = 'b0627920c9e8ab1da0dbc6d2d48795b3abe68cf3b79f7d7dba7afa9bba3847c7'
SEALED = AUDIT / 'attempt_20260929_055841_945130'
METRICS = ('r_at_1', 'official_trapezoid_mAP', 'MRR')
DIRECTIONS = (('university1652', 'sues200'), ('sues200', 'university1652'))
VARIANTS = ('visual', 'full')
SEEDS = (1, 2, 3)
EXPECTED_IDS = [f'{s}_to_{t}/{v}/seed_{n}' for s, t in DIRECTIONS for v in VARIANTS for n in SEEDS]
READS = []


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def guard(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        check(Path(os.fsdecode(args[0])).suffix.lower() not in ('.pt', '.pth', '.ckpt'),
              'Checkpoint byte access forbidden')


sys.addaudithook(guard)


def file_record(path):
    data = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read_bound(path, digest, size=None):
    p = Path(path)
    before = p.stat()
    data = p.read_bytes()
    after = p.stat()
    check((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Input changed during read')
    check(hashlib.sha256(data).hexdigest() == digest, f'SHA mismatch: {p}')
    check(size is None or len(data) == size, f'Size mismatch: {p}')
    READS.append({'path': str(p), 'bytes': len(data), 'sha256': digest})
    return json.loads(data.decode('utf-8-sig'))


def canonical_sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def write_csv(path, rows):
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(values):
    check(len(values) == 3 and all(math.isfinite(x) for x in values), 'Exactly three finite seeds required')
    return statistics.mean(values), statistics.stdev(values)


def main():
    started = datetime.now(timezone.utc).isoformat()
    # Existing outputs are never overwritten; failures remain reviewable.
    out = HERE / ('result_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    out.mkdir()
    root = read_bound(ROOT_PATH, ROOT_SHA)
    check(root['accepted'] is True and root['accepted_transfer_runs'] == 12 and root['accepted_transfer_tasks'] == 66,
          'Root acceptance scope mismatch')
    check(root['transfer_identifiers'] == EXPECTED_IDS, 'Root fixed scope mismatch')
    rb = root['independent_transfer_review']
    check(rb['sha256'] == REVIEW_SHA and Path(rb['path']) == SEALED / 'TRANSFER_REVIEW.json', 'Root review binding mismatch')
    review = read_bound(rb['path'], REVIEW_SHA, rb['bytes'])
    check(review['passed_with_stated_limits'] is True and review['accepted_transfer_runs'] == 12 and
          review['accepted_transfer_tasks'] == 66, 'Review acceptance mismatch')
    check([r['evaluation_id'] for r in review['runs']] == EXPECTED_IDS, 'Review fixed scope mismatch')
    bindings = {os.path.normcase(b['path']): b for b in root['bindings']}
    rows = []
    membership = {}
    run_inputs = []
    for ordinal, run in enumerate(review['runs'], 1):
        source, target = DIRECTIONS[(ordinal - 1) // 6]
        variant, seedstr = run['evaluation_id'].split('/')[1:]
        seed = int(seedstr.removeprefix('seed_'))
        candidates = [a for a in run['artifacts'] if Path(a['snapshot']).name == 'metrics.json']
        check(len(candidates) == 1, 'Expected exactly one sealed metrics JSON')
        artifact = candidates[0]
        snapshot = Path(artifact['snapshot'])
        check(snapshot == SEALED / f'r{ordinal:02d}' / 'metrics.json', 'Unexpected sealed metrics path')
        binding = bindings[os.path.normcase(str(snapshot))]
        check(binding['sha256'] == artifact['sha256'] and binding['bytes'] == artifact['bytes'], 'Root metrics binding mismatch')
        metrics = read_bound(snapshot, artifact['sha256'], artifact['bytes'])
        copy = dict(metrics)
        check(canonical_sha({k: v for k, v in copy.items() if k != 'payload_sha256'}) == copy['payload_sha256'],
              'Metrics canonical payload mismatch')
        check(metrics['schema_version'] == 'lgm-game.cross-dataset-metrics.v1' and metrics['unit'] == 'fraction' and
              metrics['full_gallery'] is True, 'Metrics contract mismatch')
        check((metrics['source_dataset'], metrics['target_dataset'], metrics['variant'], metrics['seed']) ==
              (source, target, variant, seed), 'Run identity mismatch')
        task_records = {t['task']: t for t in run['tasks']}
        check(set(metrics['results']) == set(task_records), 'Task identity mismatch')
        check(len(task_records) == (8 if target == 'sues200' else 3), 'Target task count mismatch')
        run_inputs.append({'evaluation_id': run['evaluation_id'], 'sealed_metrics': READS[-1],
                           'inherited_checkpoint_SHA': run['inherited_checkpoint_SHA'],
                           'source_training_authority': run['source_training_authority']})
        for task in sorted(task_records):
            result = metrics['results'][task]
            check(result['unit'] == 'fraction' and result['queries'] == task_records[task]['queries'] and
                  result['gallery'] == task_records[task]['gallery'], 'Task scale mismatch')
            scale = {k: result[k] for k in ('protocol', 'queries', 'gallery', 'query_identities', 'gallery_identities')}
            key = (source, target, task)
            check(key not in membership or membership[key] == scale, 'Cross-seed/variant protocol mismatch')
            membership[key] = scale
            row = {'source_dataset': source, 'target_dataset': target, 'task': task, 'variant': variant,
                   'seed': seed, **scale, 'unit': 'fraction'}
            for metric in METRICS:
                value = result[metric]
                check(isinstance(value, (int, float)) and not isinstance(value, bool) and
                      math.isfinite(value) and 0 <= value <= 1, 'Invalid rate metric')
                row[metric] = value
            rows.append(row)
    check(len(rows) == 66 and len(membership) == 11 and len(READS) == 14, 'Unexpected bounded scope')
    check(len({(r['source_dataset'], r['target_dataset'], r['task'], r['variant'], r['seed']) for r in rows}) == 66,
          'Duplicate seed row')

    groups, deltas = [], []
    for (source, target, task), scale in sorted(membership.items()):
        by_variant = {}
        for variant in VARIANTS:
            sample = sorted((r for r in rows if (r['source_dataset'], r['target_dataset'], r['task'], r['variant']) ==
                             (source, target, task, variant)), key=lambda r: r['seed'])
            check([r['seed'] for r in sample] == list(SEEDS), 'Seed set mismatch')
            by_variant[variant] = sample
            summary = {'source_dataset': source, 'target_dataset': target, 'task': task, 'variant': variant,
                       'n_seeds': 3, **scale, 'unit': 'fraction'}
            for metric in METRICS:
                mean, sd = summarize([r[metric] for r in sample])
                summary[metric + '_mean'] = mean
                summary[metric + '_sample_sd'] = sd
            groups.append(summary)
        delta = {'source_dataset': source, 'target_dataset': target, 'task': task,
                 'contrast': 'full_minus_visual', 'n_paired_seeds': 3, **scale, 'unit': 'fraction_difference'}
        for metric in METRICS:
            differences = [f[metric] - v[metric] for f, v in zip(by_variant['full'], by_variant['visual'])]
            mean, sd = summarize(differences)
            for seed, value in zip(SEEDS, differences):
                delta[f'{metric}_seed_{seed}_delta'] = value
            delta[metric + '_mean_delta'] = mean
            delta[metric + '_paired_sample_sd'] = sd
            delta[metric + '_mean_delta_x100'] = mean * 100
        deltas.append(delta)
    check(len(groups) == 22 and len(deltas) == 11, 'Group scope mismatch')
    limitation = list(root['transfer_limits']) + [
        'This aggregation reads only adopted sealed metrics; it does not rerun any completion gate, query audit, model, ranking or AP computation.',
        'Each group contains seed 1/2/3 equally weighted. Sample SD has denominator n-1=2; it is not SE or a confidence interval.',
        'Full-minus-Visual is descriptive within each identical transfer direction/task only, paired by seed number. No hypothesis test or significance claim.',
        'No pooling across retrieval tasks, altitudes, directions, datasets or query counts. Metrics remain fractions in machine-readable tables.',
        'Displayed R@1/mAP differences x100 are percentage points; MRR differences x100 are scaled MRR points, not relative percentage gains.'
    ]
    table_objects = {'SEED_RESULTS': rows, 'THREE_SEED_SUMMARY': groups, 'FULL_MINUS_VISUAL': deltas}
    for name, content in table_objects.items():
        write_json(out / (name + '.json'), content)
        write_csv(out / (name + '.csv'), content)
    # Round-trip tables verify that presentation does not change any machine value.
    for name, content in table_objects.items():
        check(json.loads((out / (name + '.json')).read_text(encoding='utf-8')) == content, 'JSON round-trip mismatch')
        with (out / (name + '.csv')).open(encoding='utf-8', newline='') as stream:
            parsed = list(csv.DictReader(stream))
        check(parsed == [{k: str(v) for k, v in row.items()} for row in content], 'CSV round-trip mismatch')

    labels = {'r_at_1': 'R@1', 'official_trapezoid_mAP': 'mAP', 'MRR': 'MRR'}
    md = ['# Adopted T3 transfer: three-seed descriptive results', '',
          'Scope: 12 accepted transfer runs, 66 task-seed rows, 22 task-variant groups and 11 within-task contrasts.',
          'Each cell is mean ± sample SD across seeds 1/2/3 (n−1 denominator). All three metrics below are multiplied by 100; the machine-readable files retain fractions.',
          '', '| Source → target | Task | Variant | R@1 ×100 | mAP ×100 | MRR ×100 |',
          '|---|---|---|---:|---:|---:|']
    for row in groups:
        cells = [f"{row[m+'_mean']*100:.4f} ± {row[m+'_sample_sd']*100:.4f}" for m in METRICS]
        md.append(f"| {row['source_dataset']} → {row['target_dataset']} | {row['task']} | {row['variant']} | " + ' | '.join(cells) + ' |')
    md += ['', '## Full minus Visual', '',
           'Each contrast is the mean of three same-number seed differences. Values below are 100 × the fraction difference: percentage points for R@1/mAP and scaled points for MRR. They are descriptive, without significance claims.',
           '', '| Source → target | Task | ΔR@1 | ΔmAP | ΔMRR |', '|---|---|---:|---:|---:|']
    for row in deltas:
        md.append(f"| {row['source_dataset']} → {row['target_dataset']} | {row['task']} | " +
                  ' | '.join(f"{row[m+'_mean_delta_x100']:+.4f}" for m in METRICS) + ' |')
    md += ['', '## Evidence and limits', '',
           f'Root adoption SHA256: `{ROOT_SHA}`. Transfer review SHA256: `{REVIEW_SHA}`.', '',
           *['- ' + text for text in limitation], '']
    (out / 'ANALYSIS.md').write_text('\n'.join(md), encoding='utf-8')
    outputs = [file_record(out / name) for name in sorted(p.name for p in out.iterdir())]
    report = {'schema': 'lgm-game.adopted-transfer-descriptive-aggregation.v1', 'started_utc': started,
              'finished_utc': datetime.now(timezone.utc).isoformat(), 'passed': True,
              'source': file_record(Path(__file__)), 'input_bindings': READS, 'run_inputs': run_inputs,
              'root_adoption_SHA': ROOT_SHA, 'independent_review_SHA': REVIEW_SHA,
              'metric_fields': list(METRICS), 'accepted_input_runs': 12, 'seed_task_rows': 66,
              'three_seed_groups': 22, 'within_task_contrasts': 11, 'sample_sd_ddof': 1,
              'aggregation': 'statistics.mean and statistics.stdev over exactly seed 1/2/3; equal seed weighting',
              'contrast': 'same-number seed Full minus Visual, then mean and sample SD; no task pooling',
              'csv_json_roundtrip_verified': True, 'inherited_validator_compatibility_limit': root['validator_compatibility_limit'],
              'limits': limitation, 'outputs': outputs, 'checkpoint_byte_reads': 0,
              'scientific_modules': [m for m in ('torch', 'numpy', 'pandas', 'scipy', 'matplotlib') if m in sys.modules],
              'scientific_execution': False, 'live_state_modified': False, 'new_figures_created': False}
    check(not report['scientific_modules'], 'Scientific library was imported')
    write_json(out / 'REPORT.json', report)
    write_json(out / 'DELIVERY.json', {'source': report['source'], 'report': file_record(out / 'REPORT.json'),
                                     'artifacts': outputs, 'inputs': READS})
    print(json.dumps({'output_dir': str(out), 'report': file_record(out / 'REPORT.json'),
                      'delivery': file_record(out / 'DELIVERY.json'), 'source': report['source'],
                      'groups': 22, 'contrasts': 11}, ensure_ascii=False))


if __name__ == '__main__':
    main()
