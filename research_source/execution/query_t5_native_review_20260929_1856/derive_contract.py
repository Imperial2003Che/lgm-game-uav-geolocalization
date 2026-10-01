"""New T5 figure-only contract from adopted small aggregate JSON/CSV.

Never opens old query NPZ, original scientific metrics, weights/cache/images or
imports producer/scientific modules. Prior audit results are inherited, not run.
"""
from pathlib import Path
import csv
import datetime
from decimal import Decimal, ROUND_CEILING, getcontext
import hashlib
import json

getcontext().prec=50
HERE=Path(__file__).resolve().parent
UP=HERE.parent/'pipeline_post_robustness_audit_20260929_1448'
ROOT=UP/'ROOT_POST_ROBUSTNESS_ADOPTION.json'
ROOT_SHA='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
CAPTURE=UP/'a1/CAPTURE.json'
QUERY=UP/'a1/query/transactions_t5_selective_calibration.json'
COMPARE=UP/'a1/query/transactions_t5_selective_comparisons.csv'
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
def close(a,b):check(abs(D(a)-D(b))<=Decimal('2e-15'),f'Stored arithmetic {a} {b}')

def main():
    check(bind(ROOT)['sha256']==ROOT_SHA,'Exact root SHA')
    root=load(ROOT)
    check(root['accepted_with_stated_limits'] is True,'Adopted bounded source')
    rootmap={str(Path(b['path'])):b for b in root['bindings']}
    chosen=[CAPTURE,QUERY,COMPARE,UP/'README.md',UP/'REVIEW.json']
    raw=HERE/'raw';raw.mkdir(exist_ok=False)
    inputs=[]
    for path in chosen:
        actual=bind(path);wanted=rootmap[str(path)]
        check(actual['sha256']==wanted['sha256'] and actual['bytes']==wanted['bytes'],'Exact root path/SHA/size '+path.name)
        destination=raw/path.name
        with destination.open('xb') as stream:stream.write(path.read_bytes())
        inputs.append({'source':actual,'snapshot':bind(destination)})
    check(bind(CAPTURE)['sha256']=='473d5fba90c3fc0d044733ffb19e1f2955f08df96f89d4c643ad54d6ff15ca09','Capture pin')
    check(bind(QUERY)['sha256']=='033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc','T5pin')
    check(bind(COMPARE)['sha256']=='2dc5b6bf9fba1edbde657427f516e0b539b310fb93f49511444a2061e598b40e','Comparisonpin')
    capture=load(CAPTURE)
    for path in (QUERY,COMPARE):
        matches=[b for b in capture['bindings'] if str(Path(b['snapshot']))==str(path)]
        check(len(matches)==1,'One exactflatcapture snapshotedge')
        check(matches[0]['sha256']==bind(path)['sha256'] and matches[0]['bytes']==bind(path)['bytes'],'Capture matchesroot')
    obj=load(QUERY)
    check(obj['schema_version']=='lgm-game.transactions-t5-selective-calibration.v1' and obj['status']=='completed' and obj['unit']=='fraction','Frozen T5 aggregate schema/unit')
    native=obj['native_rows'];paired=obj['paired_comparisons']
    check(len(native)==obj['registered_native_row_count']==66 and len(paired)==obj['registered_comparison_count']==132,'Accepted scope66/132')
    task_order=['university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite']
    task_order += [t for h in (150,200,250,300) for t in (f'sues200_uav_{h}m_to_satellite',f'sues200_satellite_to_uav_{h}m')]
    keys={(r['dataset'],r['task'],r['seed'],r['variant']) for r in native}
    expected={(task.split('_')[0],task,seed,variant) for task in task_order for seed in (1,2,3) for variant in ('visual','full')}
    check(len(keys)==len(native) and keys==expected,'All11tasks x3seeds x2variants')
    records=[];point_count=0
    for task in task_order:
        dataset=task.split('_')[0]
        for seed in (1,2,3):
            for variant in ('visual','full'):
                row=next(r for r in native if (r['dataset'],r['task'],r['seed'],r['variant'])==(dataset,task,seed,variant))
                rc=row['risk_coverage'];n=rc['queries']
                expectedn={'university1652_drone_to_satellite':37855,'university1652_satellite_to_drone':701,'university1652_street_to_satellite':2579}.get(task,4000 if task.startswith('sues200_uav_') else 80)
                check(type(n) is int and n==expectedn,'Per-task original querycount')
                check(rc['ranking']=='descending raw cosine Top-1 margin with stable query-order ties','Marginordering exactsemantic')
                check(row['calibration']['confidence_definition']=='clip(cosine_top1_minus_top2_margin / 2, 0, 1)' and row['calibration']['fitted_calibration_parameter'] is False,'Confidenceis fixedmargin not fittedprobability')
                check(len(rc['rows'])==10,'Ten native requestedcoveragepoints')
                points=[]
                for index,point in enumerate(rc['rows'],1):
                    requested=D(point['requested_coverage']);realized=D(point['realized_coverage'])
                    check(requested==Decimal(index)/10,'Nativecoverageorder0.1to1.0')
                    k=int((requested*n).to_integral_value(rounding=ROUND_CEILING))
                    check(type(point['selected_queries']) is int and point['selected_queries']==k,'Exactceil selectedcount')
                    close(realized,Decimal(k)/n)
                    risk=D(point['selective_risk']);accuracy=D(point['selective_r_at_1'])
                    check(0<=risk<=1 and 0<=accuracy<=1,'Finiteriskaccuracyfraction')
                    close(risk,Decimal(1)-accuracy)
                    check(len(point['selection_index_membership_sha256'])==64,'Inheritedmembershiphashfield')
                    points.append({'requested_fraction':str(requested),'realized_fraction':str(realized),
                        'requested_percent':str(requested*100),'realized_percent':str(realized*100),
                        'selected_queries':k,'queries':n,'risk_fraction':str(risk),'risk_percent':str(risk*100),
                        'selective_r_at_1_fraction':str(accuracy),'selection_index_membership_sha256':point['selection_index_membership_sha256']})
                    point_count+=1
                aurc=D(rc['AURC_discrete_all_prefixes'])
                check(aurc.is_finite() and 0<=aurc<=1,'Stored all-prefix AURC fraction')
                records.append({'dataset':dataset,'task':task,'seed':seed,'variant':variant,'queries':n,'points':points,
                                'AURC_discrete_all_prefixes_fraction':str(aurc),
                                'query_membership_sha256':row['query_membership_sha256']})
    with COMPARE.open(encoding='utf-8-sig',newline='') as stream:csvrows=list(csv.DictReader(stream))
    check(len(csvrows)==132,'PairedCSV132rows')
    pairkeys=set()
    for row,csvrow in zip(paired,csvrows):
        key=(row['dataset'],row['task'],row['seed'],D(row['requested_coverage']))
        check(key not in pairkeys,'Pairedkeyunique');pairkeys.add(key)
        check(key[3] in (Decimal('.5'),Decimal('.75'),Decimal('.9'),Decimal('1')),'Fourpaired coverages are not native tenpointcurve')
        flat={field:row[field] for field in ('dataset','task','seed','requested_coverage','realized_coverage','visual_selective_r_at_1','full_selective_r_at_1','full_minus_visual_selective_r_at_1','visual_full_selected_query_overlap')}
        cc=row['coverage_constrained_success']
        flat.update(visual_coverage_constrained_success=cc['visual_rate'],full_coverage_constrained_success=cc['full_rate'],full_minus_visual_coverage_constrained_success=cc['full_minus_visual_rate'],holm_adjusted_p=cc['holm_adjusted_p'])
        check(set(flat)==set(csvrow),'PairedCSVexactcolumns')
        for field,value in flat.items():
            check((str(value)==csvrow[field]) if isinstance(value,str) else (D(value)==D(csvrow[field])),'ExactpairedCSVJSONserialization '+field)
    check(point_count==660,'660nativeplottedpoints')
    check(pairkeys=={(task.split('_')[0],task,seed,c) for task in task_order for seed in (1,2,3) for c in map(Decimal,('.5','.75','.9','1'))},'Pairedexact132keys')
    report={'schema':'independent-t5-native-figure-contract.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status':'passed_small_source_to_display_contract','source':bind(Path(__file__)),'root_adoption':bind(ROOT),'inputs':inputs,'checks':COUNT,
      'scope':{'native_rows':66,'native_curve_points':660,'all_prefix_AURC_source_labels':66,'paired_coverage_rows_not_plotted':132,'task_pages':11,'seed_panels':33},
      'task_order':task_order,'records':records,
      'design_contract':{'x_coordinate':'100 * stored realized_coverage = 100 * ceil(requested*N)/N within storedbinary64 tolerance',
       'x_label':'Actual selected queries (%)','y_coordinate':'100 * selective_risk','y_label':'Selective error rate (%)',
       'confidence':'Raw cosine Top1 minus Top2 margin, stable ties, not posterior probability or fittedcalibration',
       'curve_semantics':'Ten registered points per seed/task/variant connected only as visual guides; stored all-prefix AURC separately labeled as a source value, not recomputed or equated to area under ten plotted points.',
       'inference':'No bootstrap CI/errorbands, p-values, significance, seedpooling or taskpooling in the figure.'},
      'limits':root['query']['limits']+[
       'Only adopted root/readme/review/capture and T5aggregateJSON/comparisonCSV small files read. No66NPZ re-audit or oldscientifictests performed.',
       'Stored margin/correctness/querymembership evidence is inherited. The graph mapping does not newly validate query selection/model/rank/AP/cache/checkpoints.',
       'Allbootstrap intervals remain producer-only and are omitted from plots; no inference or significance claim is newly produced.',
       'Risk and selectedcounts are mapped exactly to the adopted aggregate. Marginconfidence is not a posterior probability.',
       'This contract is prior to new artifact geometry/font/editability and actual visualinspection acceptance.']}
    with (HERE/'DATA_CONTRACT.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'report':bind(HERE/'DATA_CONTRACT.json'),'checks':COUNT},ensure_ascii=False))

if __name__=='__main__':main()
