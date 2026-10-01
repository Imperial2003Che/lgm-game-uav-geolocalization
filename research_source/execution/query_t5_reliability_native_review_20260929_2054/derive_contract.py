"""Independent new display contract for adopted T5 reliability small JSON.

No original arrays, scientific modules or producer imports. ECE and occupied-bin
means/accuracy are copied, never recomputed from queries or integrated bins.
"""
from pathlib import Path
import ast
import datetime
from decimal import Decimal, getcontext
import hashlib
import json
import traceback

getcontext().prec = 50
HERE = Path(__file__).resolve().parent
UP = HERE.parent / 'pipeline_post_robustness_audit_20260929_1448'
ROOT = UP / 'ROOT_POST_ROBUSTNESS_ADOPTION.json'
QUERY = UP / 'a1/query/transactions_t5_selective_calibration.json'
CAPTURE = UP / 'a1/CAPTURE.json'
ROOT_SHA = 'f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
QUERY_SHA = '033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc'
COUNT = 0


def check(value, message):
    global COUNT
    COUNT += 1
    if not value:
        raise AssertionError(message)


def bind(path):
    data = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_float=Decimal)


def D(value):
    return Decimal(str(value))


def fraction(value, name):
    value = D(value)
    check(value.is_finite() and 0 <= value <= 1, name + ' finite fraction')
    return value


def main():
    check(bind(ROOT)['sha256'] == ROOT_SHA, 'Root exact adopted hash')
    root = load(ROOT)
    check(root['accepted_with_stated_limits'] is True, 'Bounded accepted root')
    root_map = {str(Path(b['path'])): b for b in root['bindings']}
    paths = [CAPTURE, QUERY, UP/'README.md', UP/'REVIEW.json',
             UP/'a1/source/transactions_query_analysis.py', UP/'a1/source/run_transactions_query_analysis.py']
    raw = HERE/'raw'
    raw.mkdir(exist_ok=False)
    inputs = []
    for path in paths:
        actual, expected = bind(path), root_map[str(path)]
        check(actual['sha256'] == expected['sha256'] and actual['bytes'] == expected['bytes'], 'Root input binding '+path.name)
        dest = raw/path.name
        with dest.open('xb') as stream:
            stream.write(path.read_bytes())
        inputs.append({'source': actual, 'snapshot': bind(dest)})
    check(bind(QUERY)['sha256'] == QUERY_SHA, 'Exact source T5 JSON')
    check(bind(CAPTURE)['sha256'] == '473d5fba90c3fc0d044733ffb19e1f2955f08df96f89d4c643ad54d6ff15ca09', 'Capture pin')
    capture = load(CAPTURE)
    for path in (QUERY, *paths[4:]):
        matches = [b for b in capture['bindings'] if str(Path(b['snapshot'])) == str(path)]
        check(len(matches) == 1, 'One exact flat capture edge')
        check(matches[0]['sha256'] == bind(path)['sha256'] and matches[0]['bytes'] == bind(path)['bytes'], 'Capture/root/input byte agreement')
    obj = load(QUERY)
    check(obj['schema_version'] == 'lgm-game.transactions-t5-selective-calibration.v1' and obj['status'] == 'completed' and obj['unit'] == 'fraction', 'Original completed fraction schema')
    native = obj['native_rows']
    check(len(native) == obj['registered_native_row_count'] == 66, 'Native scope66')
    check(len(obj['paired_comparisons']) == obj['registered_comparison_count'] == 132, 'Paired records outside displayed scope')
    task_order = ['university1652_drone_to_satellite', 'university1652_satellite_to_drone', 'university1652_street_to_satellite']
    task_order += [t for h in (150, 200, 250, 300) for t in (f'sues200_uav_{h}m_to_satellite', f'sues200_satellite_to_uav_{h}m')]
    expected_keys = {(task.split('_')[0], task, seed, variant) for task in task_order for seed in (1, 2, 3) for variant in ('visual', 'full')}
    keyed = {(r['dataset'], r['task'], r['seed'], r['variant']): r for r in native}
    check(len(keyed) == len(native) and set(keyed) == expected_keys, 'Exact task/seed/variant identities')
    records, bins_flat = [], []
    occupied = empty = 0
    for task in task_order:
        dataset = task.split('_')[0]
        for seed in (1, 2, 3):
            for variant in ('visual', 'full'):
                row = keyed[(dataset, task, seed, variant)]
                n = row['risk_coverage']['queries']
                wanted_n = {'university1652_drone_to_satellite':37855, 'university1652_satellite_to_drone':701, 'university1652_street_to_satellite':2579}.get(task, 4000 if task.startswith('sues200_uav_') else 80)
                check(type(n) is int and n == wanted_n, 'Saved per-task N')
                digest = row['query_membership_sha256']
                check(len(digest) == 64 and all(ch in '0123456789abcdef' for ch in digest), 'Inherited full-query membership digest')
                cal = row['calibration']
                check(cal['confidence_definition'] == 'clip(cosine_top1_minus_top2_margin / 2, 0, 1)' and cal['fitted_calibration_parameter'] is False, 'Fixed non-fitted score definition')
                check(cal['bins'] == 15 and len(cal['reliability_bins']) == 15, 'Fifteen original bins')
                ece = fraction(cal['ECE'], 'Saved ECE')
                bb = []
                for index, b in enumerate(cal['reliability_bins'], 1):
                    check(set(b) == {'bin','lower_inclusive','upper_inclusive_only_for_last_bin','count','accuracy','mean_fixed_normalized_margin_confidence','weighted_absolute_gap'}, 'Exact bin fields')
                    check(type(b['bin']) is int and b['bin'] == index, 'Original bin order')
                    lo, hi = fraction(b['lower_inclusive'], 'Lower bin bound'), fraction(b['upper_inclusive_only_for_last_bin'], 'Upper bin bound')
                    check(abs(lo-Decimal(index-1)/15) <= Decimal('1e-16') and abs(hi-Decimal(index)/15) <= Decimal('1e-16'), 'Stored fixed fifteenth bounds; serialization only')
                    count = b['count']
                    check(type(count) is int and 0 <= count <= n, 'Integer bin population')
                    gap = fraction(b['weighted_absolute_gap'], 'Stored weighted gap')
                    acc, mean = b['accuracy'], b['mean_fixed_normalized_margin_confidence']
                    if count == 0:
                        check(acc is None and mean is None and gap == 0, 'Empty bin null/null/zero contribution preserved')
                        empty += 1
                    else:
                        check(acc is not None and mean is not None, 'Occupied bin requires both values')
                        acc, mean = fraction(acc, 'Accuracy'), fraction(mean, 'Mean fixed score')
                        check(lo-Decimal('2e-16') <= mean <= hi+Decimal('2e-16'), 'Stored occupied mean lies within saved bin bounds')
                        occupied += 1
                    saved = {'dataset':dataset,'task':task,'seed':seed,'variant':variant,'queries':n,
                             'query_membership_sha256':digest,'bin':index,'count':count,
                             'lower_inclusive':str(lo),'upper_bound':str(hi),'upper_inclusive':index == 15,
                             'accuracy':None if acc is None else str(acc),
                             'mean_fixed_normalized_margin_confidence':None if mean is None else str(mean),
                             'weighted_absolute_gap':str(gap),'ECE_fraction':str(ece),'occupied':count > 0}
                    bb.append(saved)
                    bins_flat.append(saved)
                check(sum(b['count'] for b in bb) == n, 'Stored populations partition full task N')
                records.append({'dataset':dataset,'task':task,'seed':seed,'variant':variant,'queries':n,
                                'query_membership_sha256':digest,'ECE_fraction':str(ece),
                                'occupied_bins':sum(b['occupied'] for b in bb),'bins':bb})
            check(keyed[(dataset,task,seed,'visual')]['query_membership_sha256'] == keyed[(dataset,task,seed,'full')]['query_membership_sha256'], 'Whole-query identities equal; per-bin members not asserted equal')
    check(len(records) == 66 and len(bins_flat) == 990 and occupied+empty == 990, 'Complete fixed display scope')
    snippets = []
    selections = {paths[4]: ('calibration_confidence_from_margin','calibration_summary'), paths[5]:('_native_t5_row',)}
    for path, names in selections.items():
        source = path.read_text(encoding='utf-8-sig')
        tree = ast.parse(source)
        for name in names:
            nodes = [node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name == name]
            check(len(nodes) == 1, 'One original static function '+name)
            snippet = ast.get_source_segment(source,nodes[0])+'\n'
            dest = raw/(name+'.txt')
            with dest.open('x',encoding='utf-8') as stream:
                stream.write(snippet)
            snippets.append({'original_source':bind(path),'function':name,'snapshot':bind(dest),'execution':'Not executed or imported; text/AST extraction only.'})
    report = {'schema':'independent-t5-reliability-display-contract.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'accepted_with_stated_limits':True,'status':'passed_saved_small_source_to_reliability_display_contract',
              'source':bind(Path(__file__)),'root_adoption':bind(ROOT),'inputs':inputs,'checks':COUNT,
              'task_order':task_order,'scope':{'pages':11,'seed_panels':33,'native_series':66,'bins':990,'occupied_points':occupied,'empty_bins':empty,'saved_ECE_labels':66},
              'records':records,'static_original_source_fragments':snippets,
              'semantic_findings':[
                  'Fixed score is clip(raw cosine top1-minus-top2 margin/2,0,1), not fitted calibration or a posterior probability.',
                  'Original indices=min(int(score*15),14) for nonnegative scores: lower inclusive, upper exclusive except last including1; floating arithmetic is original NumPy, not reconstructed here.',
                  'Empty bins retain count0, null mean/accuracy and zero weighted contribution. They must not be drawn as accuracy0 observations.',
                  'Occupied x=stored mean fixed score and y=stored accuracy, both fractions. Any y=x line is numerical equality only, not proof of calibration.',
                  'The same whole query set is used by two variants, but each uses its own score-defined bins. Per-bin membership need not match.',
                  'ECE and weighted gaps are saved source values. No ECE sum, query-level score, mean/accuracy, bin membership or uncertainty is recomputed in this display audit.'
              ],'limits':[
                  'Only small adopted JSON/source metadata and new figure artifacts; no old66NPZ or scientific suite repeated.',
                  'The root adopted prior scalar/typed stdlib reliability/ECE agreement within2e-12; inherited, not a new NumPy-bitwise or model/full-ranking/AP proof.',
                  'No pooling, bin merging, CI/SD/bootstrap/p-values/significance or posterior claim. Sparse/empty bins are retained, not imputed.',
                  'Inherited checkpoint/cache/image SHA authority, historical chain gaps and stored margins/AP/RR limitations remain.',
                  'T4 and paired/selective T5 fields outside reliability scope are not newly accepted or plotted.']}
    with (HERE/'DATA_CONTRACT.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'report':bind(HERE/'DATA_CONTRACT.json'),'checks':COUNT,'scope':report['scope']},ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        path = HERE/('REJECTED_CONTRACT_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')+'.json')
        with path.open('x',encoding='utf-8') as stream:
            json.dump({'source':bind(Path(__file__)),'checks':COUNT,'error':traceback.format_exc()},stream,indent=2)
        raise
