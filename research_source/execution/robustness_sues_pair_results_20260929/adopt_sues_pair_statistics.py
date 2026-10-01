"""Root independent exact rational reconciliation of admitted descriptive pairs."""
import argparse, csv, hashlib, io, json
from pathlib import Path
from fractions import Fraction
from decimal import Decimal
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
checks=0; bindings={}
def need(ok,message):
    global checks
    checks+=1
    if not ok: raise ValueError(message)
def verify(d):
    p=Path(d['path']).resolve()
    need(p.suffix.lower() in ('.json','.csv','.md','.py','.patch'), 'small-file extension')
    need(p.stat().st_size < 4*1024*1024,'small-file limit')
    data=p.read_bytes(); h=hashlib.sha256(data).hexdigest()
    need(h==d['sha256'] and ('bytes' not in d or len(data)==d['bytes']),str(p))
    bindings[str(p).casefold()]={'path':str(p),'sha256':h,'bytes':len(data)}
    return data
def doc(data): return json.loads(data.decode('utf-8-sig'),parse_float=Decimal)
def q(x): return Fraction(str(x))
def main():
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);p.add_argument('--sha',required=True);args=p.parse_args()
    report=doc(verify({'path':args.report,'sha256':args.sha})); out=Path(args.report).parent
    need(report['calculation_complete_with_stated_limits'] and report['root_comparison_adoption_pending'],'producer result status')
    need(report['input_count']==128 and report['metric_rows']==744 and report['corrupted_task_pairs']==240 and report['clean_task_pairs']==8,'scope')
    need(not report['scientific_imports'] and not report['live_state_modified'] and not report['pooling_or_inference'] and report['checkpoint_cache_image_array_bytes_read']==0,'execution scope')
    need(report['source']['sha256']=='289a86c83b6815c1cfe2b81bb3c289c6ac0a0cb8546976d23754d5d54600f39a','fixed source')
    need(report['visual_root']['sha256']=='a6795283cb384c77732bdb1e63af93d582d7844879f415e45ef38c8861d3af74' and report['full_root']['sha256']=='abe0d740103c44792f134ac69816030e40947170f2c245c0e6e37efda0190596','exact adopted roots')
    verify(report['source'])
    for d in report['derivation_files']:verify(d)
    delivery=doc(verify({'path':str(out/'DELIVERY.json'),'sha256':'7e414f0aae41589f2e69f961bf995e09ff059c57c9e44125f3f504b51f0cdabf'}))
    need(delivery['report']['sha256']==args.sha,'delivery report')
    admitted={}
    for d in (report['visual_root'],report['full_root']):
        r=doc(verify(d));need(r['accepted_with_stated_limits'],'accepted upstream root')
        for b in r['bindings']:admitted[str(Path(b['path']).resolve()).casefold()]=b
    metrics={};raws={}
    for d in report['inputs']:
        data=verify(d);sp={'path':d['snapshot'],'sha256':d['sha256'],'bytes':d['bytes']};verify(sp)
        if d['role']=='sealed_summary':
            ix=admitted.get(str(Path(d['path']).resolve()).casefold());need(ix is not None and ix['sha256']==d['sha256'] and ix['bytes']==d['bytes'],'direct upstream admission')
        path=Path(d['path'])
        if path.name=='metrics.json':
            v='visual' if 'robustness_sues_visual_audit_20260929_1351' in path.parts else 'full'
            m=doc(data);c=m['condition'];k=(v,c['name'],int(c.get('severity_index',0)))
            need(k not in metrics,'unique input metric condition');metrics[k]=m
        raws[str(path)]=data
    need(len(metrics)==62,'exact admitted metric files')
    arts={Path(d['path']).name:(d,verify(d)) for d in report['artifacts']}
    pairs=doc(arts['paired_tasks.json'][1]);rows=pairs['rows']
    csvrows=list(csv.DictReader(io.StringIO(arts['paired_metrics.csv'][1].decode('utf-8'))))
    need(len(rows)==248 and len(csvrows)==744,'output row counts')
    flat={(r['task'],r['condition'],int(r['severity_index']),r['metric']):r for r in csvrows}
    need(len(flat)==744,'unique flattened keys')
    expected={(t,n,s) for (v,n,s),m in metrics.items() if v=='visual' for t in m['results']}
    seen=set(); comparisons=0
    for row in rows:
        t,n,s=row['task'],row['condition'],row['severity_index'];need((t,n,s) not in seen,'unique paired key');seen.add((t,n,s))
        need(row['dataset']=='sues200' and row['seed']==1,'fixed dataset seed')
        vm=metrics['visual',n,s];fm=metrics['full',n,s]
        need(vm['condition']==fm['condition'],'exact paired condition')
        need(set(row['metrics'])=={'r_at_1','official_trapezoid_mAP','MRR'},'metric keys')
        for label in ('queries','gallery'):
            need(row[label]==vm['results'][t][label]==fm['results'][t][label],'paired task scale')
        for k,r in row['metrics'].items():
            a=q(metrics['visual','clean',0]['results'][t][k]);b=q(metrics['full','clean',0]['results'][t][k]);c=q(vm['results'][t][k]);d=q(fm['results'][t][k])
            vals={'visual_clean':a,'full_clean':b,'visual_condition':c,'full_condition':d,'full_minus_visual_clean':b-a,'full_minus_visual_condition':d-c,'visual_clean_minus_condition_drop':a-c,'full_clean_minus_condition_drop':b-d,'full_minus_visual_drop_difference':(b-d)-(a-c)}
            f=flat[t,n,s,k]
            for field in ('dataset','seed','task','condition','severity_index','queries','gallery'):
                need(f[field]==str(row[field]),'CSV paired metadata '+field)
            for field,val in vals.items():
                for suffix,scale in (('_fraction',1),('_scaled100',100)):
                    need(q(r[field+suffix])==val*scale and f[field+suffix]==r[field+suffix],'exact rational reconciliation '+field+suffix);comparisons+=1
            need(r['scaled100_value_unit']==('MRR_times_100' if k=='MRR' else 'percent'),'value unit')
            need(r['scaled100_difference_unit']==('MRR_times_100_units' if k=='MRR' else 'percentage_points'),'difference unit')
            for field,val in r.items():need(f[field]==str(val),'CSV JSON matched metric field')
    need(seen==expected and len(expected)==248,'full exact matched scope')
    summary={}
    for t in sorted({k[0] for k in expected}):
        summary[t]={}
        for m in ('r_at_1','official_trapezoid_mAP','MRR'):
            d=[q(r['metrics'][m]['full_minus_visual_condition_fraction']) for r in rows if r['task']==t and r['condition']!='clean']
            summary[t][m]={'positive':sum(x>0 for x in d),'zero':sum(x==0 for x in d),'negative':sum(x<0 for x in d),'interpretation':'Signs across 30 separate conditions; no pooled score, uncertainty or significance.'}
    result={'schema':'lgm.root.robustness-pair-statistics-adoption.v1','time':datetime.now(timezone.utc).isoformat(),'accepted_descriptive_statistics_with_limits':True,'independent_method':'Root read complete producer source, independently reconciled all 13392 numeric fraction/scaled fields using exact rational arithmetic from SHA-bound upstream summaries, and checked CSV/JSON and task matching. No producer re-execution.','source':{'path':str(Path(__file__).resolve()),'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'producer_report':{'path':args.report,'sha256':args.sha},'checks':checks,'numeric_field_reconciliations':comparisons,'input_count':128,'clean_task_pairs':8,'corrupted_task_pairs':240,'metric_rows':744,'bindings':list(bindings.values()),'per_task_sign_description':summary,'limits':report['limits'],'scientific_execution':False,'checkpoint_cache_image_array_bytes_read':0,'comparison_itself_reaudits_whole_stage':False}
    target=HERE/'ROOT_PAIR_STATISTICS_ADOPTION.json'
    with target.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'checks':checks,'numeric_fields':comparisons,'signs':summary},ensure_ascii=False))
if __name__=='__main__':main()
