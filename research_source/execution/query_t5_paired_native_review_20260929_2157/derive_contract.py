"""Independent saved-small-table display contract; no original-query recomputation."""
from pathlib import Path
import ast
import csv
import datetime
from decimal import Decimal, getcontext
import hashlib
import json
import traceback

getcontext().prec = 50
HERE = Path(__file__).resolve().parent
UP = HERE.parent/'pipeline_post_robustness_audit_20260929_1448'
ROOT = UP/'ROOT_POST_ROBUSTNESS_ADOPTION.json'
QUERY = UP/'a1/query/transactions_t5_selective_calibration.json'
CSV = UP/'a1/query/transactions_t5_selective_comparisons.csv'
CAPTURE = UP/'a1/CAPTURE.json'
COUNT = 0


def check(value, message):
    global COUNT
    COUNT += 1
    if not value:
        raise AssertionError(message)


def bind(path):
    data = Path(path).read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),parse_float=Decimal)


def fraction(value, name):
    value = Decimal(str(value))
    check(value.is_finite() and 0 <= value <= 1, name+' fraction')
    return value


def main():
    check(bind(ROOT)['sha256']=='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a','Root exact pin')
    root=load(ROOT)
    check(root['accepted_with_stated_limits'] is True,'Bounded root acceptance')
    pins={str(Path(p['path'])):p for p in root['bindings']}
    paths=[CAPTURE,QUERY,CSV,UP/'README.md',UP/'REVIEW.json',UP/'a1/source/transactions_query_analysis.py',UP/'a1/source/run_transactions_query_analysis.py']
    raw=HERE/'raw';raw.mkdir(exist_ok=False)
    inputs=[]
    for p in paths:
        b=bind(p);expected=pins[str(p)]
        check(b['sha256']==expected['sha256'] and b['bytes']==expected['bytes'],'Exact adopted small binding '+p.name)
        dest=raw/p.name
        with dest.open('xb') as f:f.write(p.read_bytes())
        inputs.append({'source':b,'snapshot':bind(dest)})
    check(bind(QUERY)['sha256']=='033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc' and bind(QUERY)['bytes']==744943,'Exact saved T5')
    check(bind(CAPTURE)['sha256']=='473d5fba90c3fc0d044733ffb19e1f2955f08df96f89d4c643ad54d6ff15ca09','Exact capture')
    check(bind(CSV)['sha256']=='2dc5b6bf9fba1edbde657427f516e0b539b310fb93f49511444a2061e598b40e','Exact saved CSV')
    cap=load(CAPTURE)
    for p in [QUERY,CSV,*paths[5:]]:
        edges=[x for x in cap['bindings'] if str(Path(x['snapshot']))==str(p)]
        check(len(edges)==1,'One flat captured source edge')
        check(edges[0]['sha256']==bind(p)['sha256'] and edges[0]['bytes']==bind(p)['bytes'],'Capture/root small-source agreement')
    obj=load(QUERY)
    check(obj['schema_version']=='lgm-game.transactions-t5-selective-calibration.v1' and obj['status']=='completed' and obj['unit']=='fraction','Saved completed fraction schema')
    check(len(obj['native_rows'])==obj['registered_native_row_count']==66,'Native scope66 for shared N')
    check(len(obj['paired_comparisons'])==obj['registered_comparison_count']==132,'Paired scope132')
    tasks=['university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite']
    tasks += [t for h in (150,200,250,300) for t in (f'sues200_uav_{h}m_to_satellite',f'sues200_satellite_to_uav_{h}m')]
    coverages=[Decimal('0.5'),Decimal('0.75'),Decimal('0.9'),Decimal('1.0')]
    native={(r['task'],r['seed'],r['variant']):r for r in obj['native_rows']}
    expected_native={(t,s,v) for t in tasks for s in (1,2,3) for v in ('visual','full')}
    check(len(native)==66 and set(native)==expected_native,'Exact native identities')
    paired={(r['task'],r['seed'],r['requested_coverage']):r for r in obj['paired_comparisons']}
    check(len(paired)==132 and set(paired)=={(t,s,c) for t in tasks for s in (1,2,3) for c in coverages},'Exact paired task/seed/requested identities')
    with CSV.open(encoding='utf-8-sig',newline='') as f:
        source_csv=list(csv.DictReader(f))
    csvkey={(r['task'],int(r['seed']),Decimal(r['requested_coverage'])):r for r in source_csv}
    check(len(csvkey)==len(source_csv)==132 and set(csvkey)==set(paired),'Exact existing CSV coverage')
    records=[]
    for t in tasks:
        ds=t.split('_')[0]
        for seed in (1,2,3):
            v,f=native[t,seed,'visual'],native[t,seed,'full']
            n=v['risk_coverage']['queries']
            wanted={'university1652_drone_to_satellite':37855,'university1652_satellite_to_drone':701,'university1652_street_to_satellite':2579}.get(t,4000 if t.startswith('sues200_uav_') else 80)
            check(type(n) is int and n==f['risk_coverage']['queries']==wanted,'Both saved native N')
            digest=v['query_membership_sha256']
            check(digest==f['query_membership_sha256'] and len(digest)==64 and all(c in '0123456789abcdef' for c in digest),'Shared full-query digest; selected members not equated')
            for i,c in enumerate(coverages,1):
                r=paired[t,seed,c];z=r['coverage_constrained_success'];sc=csvkey[t,seed,c]
                check(r['dataset']==ds and sc['dataset']==ds,'Dataset and direction retained')
                check(z['definition']=='selected AND top1-correct over the common full query set','Full N utility definition')
                actual=fraction(r['realized_coverage'],'Stored actual coverage')
                k,overlap=r['selected_queries_per_variant'],r['visual_full_selected_query_overlap']
                check(type(k) is int and 1<=k<=n,'Saved selected count integer')
                check(type(overlap) is int and 0<=overlap<=k,'Saved overlap counts selected intersection')
                vr,fr=fraction(z['visual_rate'],'Stored Visual utility'),fraction(z['full_rate'],'Stored Full utility')
                check(vr<=actual and fr<=actual,'Saved full-denominator utility within actual coverage')
                for key,value in [('realized_coverage',actual),('visual_coverage_constrained_success',vr),('full_coverage_constrained_success',fr)]:
                    check(Decimal(sc[key])==value,'Saved JSON/CSV scalar exact equality '+key)
                check(int(sc['visual_full_selected_query_overlap'])==overlap,'Saved CSV overlap equality')
                # These are recorded from sources, never reconstructed from rates or arrays.
                records.append({'dataset':ds,'task':t,'seed':seed,'coverage_ordinal':i,'requested_coverage':str(c),
                    'realized_coverage':str(actual),'common_queries':n,'selected_queries_per_variant':k,
                    'visual_full_selected_query_overlap':overlap,'query_membership_sha256':digest,
                    'visual_rate':str(vr),'full_rate':str(fr),
                    'definition':z['definition']})
    check(len(records)==132,'Fixed new display records')
    source=paths[5].read_text(encoding='utf-8-sig');tree=ast.parse(source);snippets=[]
    for name in ('align_visual_full','_coverage_count','paired_coverage_comparison'):
        nodes=[x for x in ast.walk(tree) if isinstance(x,ast.FunctionDef) and x.name==name]
        check(len(nodes)==1,'One original function '+name)
        text=ast.get_source_segment(source,nodes[0])+'\n';dest=raw/(name+'.txt')
        with dest.open('x',encoding='utf-8') as f:f.write(text)
        snippets.append({'function':name,'original_source':bind(paths[5]),'snapshot':bind(dest),'execution':'Static text/AST only, not imported or run.'})
    assigns=[x for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id=='SELECTIVE_COVERAGES' for y in x.targets)]
    check(len(assigns)==1 and tuple(str(x) for x in ast.literal_eval(assigns[0].value))==('0.5','0.75','0.9','1.0'),'Original registered four coverages')
    report={'schema':'independent-t5-paired-display-contract.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'accepted_with_stated_limits':True,'source':bind(Path(__file__)),'root_adoption':bind(ROOT),'inputs':inputs,'checks':COUNT,
        'task_order':tasks,'coverages':[str(x) for x in coverages],
        'scope':{'pages':11,'seed_panels':33,'paired_rows':132,'points':264,'guide_segments':198,'count_overlap_table_rows':132},
        'records':records,'static_original_source_fragments':snippets,
        'semantic_findings':[
            'Requested coverages are50/75/90/100 percent; actual x copies realized_coverage times100. Stored k is shown as k/N per variant, not recomputed by this audit.',
            'Each variant ranks its own raw margin with stable query-order ties after Full alignment to Visual paths and equal labels. Both select the same saved k but may select different members; overlap is their selected-set intersection count, not success intersection.',
            'Y copies stored selected-AND-top1-correct rate over shared whole-query N, times100. It is not selective accuracy over k; rejected queries contribute false to the full utility vector.',
            'The original McNemar quantities concern paired utility variables across the common full query set. They are not drawn, recalculated or claimed significant here.',
            'Only four existing points per variant; lines are visual guides. No zero-coverage point, interpolation result, extrapolation, AURC, ECE, uncertainty or inferential statistic is added.',
            'Shared whole-query SHA/N are inherited from accepted native rows. New display audit only compares saved JSON/CSV scalars; it does not reconstruct selected identities or compute k/N, rates, differences, p-values or bootstrap estimates.'],
        'limits':[
            'Fixed 11tasks and three seeds separately; no pooling, SD/CI/bootstrap/p/Holm/significance display.',
            'Margin is not posterior confidence; these utility plots do not establish calibrated probabilities or causal benefit.',
            'No old66NPZ/model/weights/cache/image/science or prior-suite execution. Source authority gaps and all upstream SHA/ranking/AP/scalar tolerance limitations retained.',
            'Full source JSON preserves132paired inferential/other fields; untouched source carriage does not mean this figure audits or displays them.']}
    with (HERE/'DATA_CONTRACT.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'report':bind(HERE/'DATA_CONTRACT.json'),'checks':COUNT,'scope':report['scope']},ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except Exception:
        p=HERE/('REJECTED_CONTRACT_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')+'.json')
        with p.open('x',encoding='utf-8') as f:json.dump({'source':bind(Path(__file__)),'checks':COUNT,'error':traceback.format_exc()},f,indent=2)
        raise
