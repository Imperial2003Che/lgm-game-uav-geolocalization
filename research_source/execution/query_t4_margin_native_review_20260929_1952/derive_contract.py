"""New T4 margin figure display contract from adopted small JSON/CSV only.

No old query arrays, weights, caches, images, producer imports or scientific
statistics are executed. This contract copies saved means and eligibility.
"""
from pathlib import Path
from decimal import Decimal, getcontext
import ast
import csv
import datetime
import hashlib
import json
import traceback

getcontext().prec=50
HERE=Path(__file__).resolve().parent
UP=HERE.parent/'pipeline_post_robustness_audit_20260929_1448'
ROOT=UP/'ROOT_POST_ROBUSTNESS_ADOPTION.json'
CAPTURE=UP/'a1/CAPTURE.json'
JSON=UP/'a1/query/transactions_t4_strata.json'
CSV=UP/'a1/query/transactions_t4_strata.csv'
ROOT_SHA='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
T4_SHA='42090c4ffdafedbfffd8ed2439e1e59756f0876e2c7ae612a87031a574b28cc8'
CSV_SHA='bc1725e7d5a1ce298f2de579240d65ced823b57d0d2af8bcb077a9d697d66530'
LEVELS=['q1_low','q2_mid_low','q3_mid_high','q4_high']
METRICS=['r_at_1','official_trapezoid_mAP','MRR']
COUNT=0

def check(v,message):
    global COUNT
    COUNT+=1
    if not v:raise AssertionError(message)

def bind(path):
    data=Path(path).read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'),parse_float=Decimal)
def D(value):return Decimal(str(value))

def main():
    check(bind(ROOT)['sha256']==ROOT_SHA,'Exact root')
    root=load(ROOT);check(root['accepted_with_stated_limits'] is True,'Bounded root adoption')
    rootmap={str(Path(b['path'])):b for b in root['bindings']}
    chosen=[CAPTURE,JSON,CSV,UP/'README.md',UP/'REVIEW.json',
            UP/'a1/source/run_transactions_query_analysis.py',UP/'a1/source/transactions_query_analysis.py']
    raw=HERE/'raw';raw.mkdir(exist_ok=False)
    inputs=[]
    for path in chosen:
        actual=bind(path);wanted=rootmap[str(path)]
        check(actual['sha256']==wanted['sha256'] and actual['bytes']==wanted['bytes'],'Root exact small-file source '+path.name)
        destination=raw/path.name
        with destination.open('xb') as stream:stream.write(path.read_bytes())
        inputs.append({'source':actual,'snapshot':bind(destination)})
    check(bind(CAPTURE)['sha256']=='473d5fba90c3fc0d044733ffb19e1f2955f08df96f89d4c643ad54d6ff15ca09','Capture pin')
    check(bind(JSON)['sha256']==T4_SHA and bind(CSV)['sha256']==CSV_SHA,'Frozen T4 small-file pins')
    capture=load(CAPTURE)
    for path in (JSON,CSV,*chosen[-2:]):
        matches=[b for b in capture['bindings'] if str(Path(b['snapshot']))==str(path)]
        check(len(matches)==1,'Exact capture edge')
        check(matches[0]['sha256']==bind(path)['sha256'] and matches[0]['bytes']==bind(path)['bytes'],'Capture/root edge agrees')
    query=load(JSON)
    check(query['schema_version']=='lgm-game.transactions-t4-strata.v1' and query['status']=='completed' and query['unit']=='fraction','Actual completed fraction schema')
    check(len(query['rows'])==query['registered_row_count']==query['observed_row_count']==462,'Upstream462 strata scope')
    check(query['minimum_queries_for_performance_claim']==100,'Frozen threshold is100, not30')
    task_order=['university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite']
    task_order += [t for h in (150,200,250,300) for t in (f'sues200_uav_{h}m_to_satellite',f'sues200_satellite_to_uav_{h}m')]
    selected=[r for r in query['rows'] if r['factor']=='visual_margin_quartile']
    keys={(r['dataset'],r['task'],r['seed'],r['level']) for r in selected}
    expected={(t.split('_')[0],t,s,l) for t in task_order for s in (1,2,3) for l in LEVELS}
    check(len(selected)==len(keys)==132 and keys==expected,'Fixed exact132 Visual-margin strata')
    excluded={f:sum(r['factor']==f for r in query['rows']) for f in ('content_entropy_quartile','style_entropy_quartile','visual_semantic_top1_identity_agreement')}
    check(excluded=={'content_entropy_quartile':132,'style_entropy_quartile':132,'visual_semantic_top1_identity_agreement':66},'Other330 explicitly excluded, not re-audited')
    with CSV.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);csv_fields=reader.fieldnames;csv_all=list(reader)
    check(len(csv_all)==462,'Upstream CSV retained whole462rows')
    csv_selected=[r for r in csv_all if r['factor']=='visual_margin_quartile']
    csv_map={(r['dataset'],r['task'],int(r['seed']),r['level']):r for r in csv_selected}
    check(len(csv_map)==len(csv_selected)==132 and set(csv_map)==keys,'Exact132 CSV margin keys')
    records=[];eligible_counts={True:0,False:0};display_values=0
    for task in task_order:
        dataset=task.split('_')[0]
        expected_n={'university1652_drone_to_satellite':37855,'university1652_satellite_to_drone':701,'university1652_street_to_satellite':2579}.get(task,4000 if task.startswith('sues200_uav_') else 80)
        for seed in (1,2,3):
            group=[r for r in selected if r['task']==task and r['seed']==seed]
            check(sum(r['summary']['queries'] for r in group)==expected_n,'StoredquartileNs cover exacttaskN; no membership recompute')
            cuts=group[0]['metadata']['quartile_cutpoints']
            check(len(cuts)==3 and all(D(c).is_finite() for c in cuts) and cuts==sorted(cuts),'Saved finite ordered cuts')
            for index,level in enumerate(LEVELS,1):
                row=next(r for r in group if r['level']==level)
                summary=row['summary'];n=summary['queries'];eligible=summary['performance_claim_eligible']
                check(type(n) is int and n>0,'Actual nonempty savedstratum')
                check(type(eligible) is bool and summary['minimum_queries_for_claim']==100 and eligible==(n>=100),'Exact saved eligibility display contract')
                check(row['metadata']['quartile_cutpoints']==cuts,'Same savedcuts within taskseed')
                check(row['metadata']['boundary_rule']=='linear quantiles; values equal to a cutpoint enter the lower interval','Visible boundary semantics')
                check(len(row['membership_sha256'])==64,'Saved inherited membership digest')
                if not eligible:
                    check(summary['warning']=='descriptive values retained below the registered 100-query claim threshold; confidence interval and hypothesis test withheld','Originalbelow100warning')
                    check(n==20 and task.startswith('sues200_satellite_to_uav_'),'Actual fourreverseSUES tasks below100')
                csvrow=csv_map[(dataset,task,seed,level)]
                flat={'dataset':dataset,'task':task,'seed':seed,'factor':'visual_margin_quartile','level':level,'queries':n,
                      'performance_claim_eligible':eligible,'membership_sha256':row['membership_sha256'],
                      'holm_adjusted_p':summary['top1_discordance'].get('holm_adjusted_p')}
                metrics=[]
                for metric,short in zip(METRICS,('r_at_1','mAPtrap','MRR')):
                    item=summary['metrics'][metric]
                    for variant in ('visual','full'):
                        value=D(item[variant]);check(value.is_finite() and 0<=value<=1,'Saved finite metric fraction')
                        flat[variant+'_'+short]=item[variant]
                        metrics.append({'metric':metric,'variant':variant,'fraction':str(value),'display_x100':str(value*100)})
                        display_values+=1
                    flat['full_minus_visual_'+short]=item['full_minus_visual']
                    # Below-threshold nulls are exposed as a display restriction;
                    # no CI, discordance or test probability is recalculated.
                    if not eligible:check(item['paired_bootstrap_95ci'] is None,'Withheld CI stays unplotted/null')
                check(set(flat)==set(csv_fields),'Exact existing CSVmargin columns')
                for field,value in flat.items():
                    if value is None:check(csvrow[field]=='','Null CSV field')
                    elif type(value) is bool:check(csvrow[field]==str(value),'Eligibility CSV flag')
                    elif isinstance(value,str):check(csvrow[field]==value,'Source CSV exact string '+field)
                    else:check(D(csvrow[field])==D(value),'Source CSV exact numeric '+field)
                eligible_counts[eligible]+=1
                records.append({'dataset':dataset,'task':task,'seed':seed,'factor':'visual_margin_quartile',
                    'level':level,'quartile_index':index,'queries':n,'task_queries':expected_n,
                    'performance_claim_eligible':eligible,'minimum_queries_for_claim':100,
                    'membership_sha256':row['membership_sha256'],'quartile_cutpoints':[str(D(c)) for c in cuts],
                    'boundary_rule':row['metadata']['boundary_rule'],'metrics':metrics,
                    'warning':summary.get('warning')})
    check(eligible_counts=={True:84,False:48} and display_values==792,'Actual132 strata eligibility and792displayvalues')
    # Bind exact AST source fragments actually read as a static semantic contract.
    # These function bodies are neither imported nor executed by this review.
    fragments=[]
    targets={'run_transactions_query_analysis.py':('_strata_for_pair','_load_aligned_pair'),
             'transactions_query_analysis.py':('quartile_assignment','align_visual_full','_paired_metric_matrix','stratum_summary')}
    for filename,names in targets.items():
        path=raw/filename;source=path.read_text(encoding='utf-8-sig');lines=source.splitlines(keepends=True)
        tree=ast.parse(source)
        for name in names:
            found=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name]
            check(len(found)==1,'Unique sourcecontractfunction '+name)
            node=found[0];body=''.join(lines[node.lineno-1:node.end_lineno]);dest=raw/(name+'.txt')
            with dest.open('x',encoding='utf-8') as stream:stream.write(body)
            fragments.append({'source_file':bind(path),'function':name,'line':node.lineno,'end_line':node.end_lineno,'fragment':bind(dest),'executed':False})
    result={'schema':'independent-t4-margin-figure-contract.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'passed_saved_small_source_to_margin_display_contract','source':bind(Path(__file__)),
        'root_adoption':bind(ROOT),'inputs':inputs,'checks':COUNT,'task_order':task_order,'level_order':LEVELS,'metric_order':METRICS,
        'scope':{'source_rows':462,'plotted_margin_strata':132,'excluded_other_strata':330,'metric_variant_points':792,
                 'eligible_strata':84,'below_100_descriptive_only_strata':48,'pages':11,'seed_metric_panels':99},
        'records':records,'static_original_source_fragments':fragments,
        'semantic_findings':[
            'Visual raw cosine Top1-minus-Top2 margin defines all four quartiles for eachtask/seed. Linear cuts, ties to lower interval; ordinal quartile positions are not raw-margin axis values.',
            'Original source aligns Full paths/labels to Visual then applies one Visual-defined mask to bothvariant metric matrices. These T4 strata compare the same memberqueries, unlike T5 variant-specific selected subsets.',
            'Saved R@1 and official trapezoid mAP fractions display as percentages; MRR×100 is scaledMRR, not accuracypercentage.',
            'Original performance claim threshold is100. Actual48 ineligible strata are allN20 reverseSUES; show visibleN anddescriptive-only/claim-ineligible warning. Threshold eligibility does not establish significance or authorize superiority claims.',
            'Allseed/task/height/direction levels remain separate; no CIs/SD/p-values/significance/pooledmean. Entropy/semantic330rows remainnotplotted.'],
        'limits':root['query']['limits']+[
            'No old66NPZ/query/mean/membership/quantile/bootstrap suite re-executed. Original132margin recount and source alignment are inherited from root-adopted review.',
            'This new contract checks only saved132rows/CSVexact serialization, membership-reference labels, N/eligibility and direct×100 displaymapping. It doesnot freshverify underlying queries.',
            'Allcurrent checkpoint/cache/image bytes, historicalSHAchain, storedAP/RR/margin/model/fullranking limitsremain inherited.',
            'Actualnewfigure geometry/fonts/nativeobjectsandallpagevisual require separate acceptance.']}
    with (HERE/'DATA_CONTRACT.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'report':bind(HERE/'DATA_CONTRACT.json'),'checks':COUNT,'scope':result['scope']},ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except Exception:
        error=traceback.format_exc()
        name='REJECTED_CONTRACT_ATTEMPT_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')+'.json'
        with (HERE/name).open('x',encoding='utf-8') as stream:json.dump({'source':bind(Path(__file__)),'checks':COUNT,'error':error},stream,indent=2)
        raise
