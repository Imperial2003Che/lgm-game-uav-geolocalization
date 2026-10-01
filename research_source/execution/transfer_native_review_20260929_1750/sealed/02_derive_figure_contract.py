"""Independent incremental figure contract from adopted small T3 result tables.

No original metrics, query NPZ, weights/cache/images or scientific libraries are
read. Existing aggregation means/SD are inherited from the pinned root adoption;
the old aggregation suite and its calculations are deliberately not rerun.
"""
from pathlib import Path
import csv
import datetime
from decimal import Decimal, getcontext
import hashlib
import json

getcontext().prec = 50
HERE = Path(__file__).resolve().parent
EX = HERE.parent
ROOT = EX / 'transfer_results_20260929/ROOT_AGGREGATION_ADOPTION.json'
ROOT_SHA = 'a8867a9ebdf01061a55d143b79eff91196571c2275f4379902131a69dd4ce80c'
DATA = ROOT.parent / 'result_20260929_061052_519928'
METRICS = ('r_at_1', 'official_trapezoid_mAP', 'MRR')
COUNT = 0

def check(value, message):
    global COUNT
    COUNT += 1
    if not value:
        raise AssertionError(message)

def bind(path):
    data = Path(path).read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_float=Decimal)

def normalized(row):
    return {key: (Decimal(value) if isinstance(value, str) and key not in ('source_dataset','target_dataset','task','variant','protocol','unit','contrast') else value) for key, value in row.items()}

def main():
    check(bind(ROOT)['sha256'] == ROOT_SHA, 'Exact adopted root')
    root = load(ROOT)
    check(root['status'] == 'root_adopted_descriptive_transfer_statistics', 'Root status')
    adopted = {str(Path(row['path'])): row for row in root['bindings']}
    raw = HERE / 'raw'
    raw.mkdir(exist_ok=False)
    files = []
    for name in ('THREE_SEED_SUMMARY.csv', 'THREE_SEED_SUMMARY.json', 'SEED_RESULTS.csv', 'SEED_RESULTS.json',
                 'FULL_MINUS_VISUAL.csv', 'FULL_MINUS_VISUAL.json'):
        path = DATA / name
        actual = bind(path)
        expected = adopted[str(path)]
        check(actual['sha256'] == expected['sha256'] and actual['bytes'] == expected['bytes'], 'Adopted table bytes '+name)
        snapshot = raw / name
        with snapshot.open('xb') as stream:
            stream.write(path.read_bytes())
        files.append({'source': actual, 'snapshot': bind(snapshot)})
    tables = {}
    for stem, expected_count in (('THREE_SEED_SUMMARY',22), ('SEED_RESULTS',66), ('FULL_MINUS_VISUAL',11)):
        rows_json = load(DATA / (stem+'.json'))
        with (DATA / (stem+'.csv')).open(encoding='utf-8-sig', newline='') as stream:
            rows_csv = [normalized(row) for row in csv.DictReader(stream)]
        check(len(rows_json) == len(rows_csv) == expected_count, stem+' scope')
        for left, right in zip(rows_json, rows_csv):
            check(left == right, stem+' exact CSV/JSON values and order')
        tables[stem] = rows_json
    seeds = tables['SEED_RESULTS']
    summary = tables['THREE_SEED_SUMMARY']
    contrasts = tables['FULL_MINUS_VISUAL']
    source_target_tasks = {}
    groups = []
    for row in summary:
        key = (row['source_dataset'], row['target_dataset'], row['task'], row['variant'])
        source, target, task, variant = key
        check(source != target and {source,target} == {'university1652','sues200'}, 'Distinct actual train/eval domains')
        check(task.startswith(target+'_'), 'Retrieval task belongs to evaluation domain')
        check(variant in ('visual','full') and row['unit']=='fraction' and row['n_seeds']==3, 'Fixed variant/seeds/fraction')
        members = [seed for seed in seeds if tuple(seed[k] for k in ('source_dataset','target_dataset','task','variant')) == key]
        check(len(members)==3 and {seed['seed'] for seed in members}=={1,2,3}, 'Exact adopted three seed membership')
        for seed in members:
            for field in ('protocol','queries','gallery','query_identities','gallery_identities','unit'):
                check(seed[field] == row[field], 'No protocol/count pooling '+field)
        source_target_tasks.setdefault((source,target), set()).add(task)
        mapped=[]
        for metric in METRICS:
            mean, sd = Decimal(str(row[metric+'_mean'])), Decimal(str(row[metric+'_sample_sd']))
            check(mean.is_finite() and sd.is_finite() and 0 <= mean <= 1 and 0 <= sd, 'Finite adopted mean/sampleSD')
            values=[{'seed': seed['seed'], 'fraction': str(seed[metric]), 'x100': str(Decimal(str(seed[metric]))*100)} for seed in members]
            mapped.append({'metric':metric, 'mean_fraction':str(mean), 'sample_sd_fraction':str(sd),
                           'mean_x100':str(mean*100), 'sample_sd_x100':str(sd*100),
                           'lower_x100':str((mean-sd)*100), 'upper_x100':str((mean+sd)*100),
                           'seed_points':values, 'display_unit': 'MRR x100 (scaled reciprocal rank)' if metric=='MRR' else 'percent',
                           'interval_kind':'mean plus/minus adopted sample SD, n=3; not CI or SE'})
        groups.append({'source_dataset':source,'target_dataset':target,'task':task,'variant':variant,
                       'protocol':row['protocol'],'queries':row['queries'],'gallery':row['gallery'],
                       'metrics':mapped})
    check({key:len(value) for key,value in source_target_tasks.items()} == {('university1652','sues200'):8, ('sues200','university1652'):3}, 'Two pages have 8 and3 separate retrievaltasks')
    check(len({(g['source_dataset'],g['target_dataset'],g['task'],g['variant']) for g in groups})==22, 'No duplicated group')
    by_task={}
    for row in summary:
        by_task.setdefault((row['source_dataset'],row['target_dataset'],row['task']),{})[row['variant']]=row
    signs=[]
    for row in contrasts:
        key=(row['source_dataset'],row['target_dataset'],row['task'])
        pair=by_task[key]
        check(set(pair)=={'visual','full'}, 'Each task has both variants')
        result={'source_dataset':key[0],'target_dataset':key[1],'task':key[2]}
        for metric in METRICS:
            delta=Decimal(str(row[metric+'_mean_delta_x100']))
            # Check descriptive direction only. Do not recalculate the adopted
            # paired statistics or call the former 2699-check scientific suite.
            diff=Decimal(str(pair['full'][metric+'_mean']))-Decimal(str(pair['visual'][metric+'_mean']))
            check((delta>0)-(delta<0)==(diff>0)-(diff<0), 'Adopted descriptive direction')
            result[metric+'_full_minus_visual_x100']=str(delta)
        signs.append(result)
    check(sum(Decimal(v['r_at_1_full_minus_visual_x100'])<0 for v in signs)==11, 'All11 negative R1 means retained')
    check(sum(Decimal(v['official_trapezoid_mAP_full_minus_visual_x100'])<0 for v in signs)==10, '10negative mAP means retained')
    limits=root['limits']+[
        'This new figure-contract check reads only adopted six small CSV/JSON tables and root metadata, not original sealed run metrics or raw scientific inputs.',
        'No old 2699-check aggregation suite, mean/SD recomputation, model/query/NPZ/weight/cache/image access or science execution occurred.',
        'Plot means and sample SD are inherited from the root-adopted aggregation; newly mapped x100 display values and bounds do not introduce inferential statistics.',
        'Training-domain transfer direction and retrieval query-to-gallery direction must be distinct visible labels.',
        'Absolute R@1/mAP x100 are percentages; MRR x100 is scaled reciprocal rank, not accuracy percent. SD scales by the same100 factor.',
        'All task/height/direction results remain separate, including small street metrics, zero sampleSD and Full-negative results.',
        'This report is a pre-artifact contract; final geometry/editability/fonts and actual rendered PNG viewing are separate pending checks.',
    ]
    report={'schema':'independent-transfer-native-figure-contract.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'passed_incremental_adopted_table_to_figure_contract','source':bind(Path(__file__)),
            'root_adoption':bind(ROOT),'adopted_small_tables':files,'checks':COUNT,
            'scope':{'pages':2,'retrieval_tasks':11,'task_variant_groups':22,'three_seed_metric_cells':66,'seed_task_rows':66,'metrics':list(METRICS)},
            'groups':groups,'descriptive_contrasts':signs,'limits':limits}
    path=HERE/'DATA_CONTRACT.json'
    with path.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'checks':COUNT,'report':bind(path)},ensure_ascii=False))

if __name__=='__main__':
    main()
