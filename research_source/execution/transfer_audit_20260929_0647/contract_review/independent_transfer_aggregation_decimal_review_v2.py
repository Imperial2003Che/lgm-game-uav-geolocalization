"""Independent stdlib/Decimal50 verification of an existing adopted T3 aggregation."""
from __future__ import annotations
import csv, hashlib, json, os, sys
from collections import defaultdict
from decimal import Decimal, localcontext, getcontext
from pathlib import Path
from datetime import datetime, timezone

HERE=Path(__file__).parent
EX=HERE.parents[1]
RESULT=EX/'transfer_results_20260929/result_20260929_061052_519928'
AGG=EX/'transfer_results_20260929/aggregate_transfer.py'
ADOPTION=EX/'transfer_audit_20260929_0647/ROOT_TRANSFER12_AND_NATIVE2_ADOPTION.json'
METRICS=('r_at_1','official_trapezoid_mAP','MRR')
DIRS=(('university1652','sues200'),('sues200','university1652'))
VARS=('visual','full')
SEEDS=(1,2,3)
EXPECTED_IDS=[f'{s}_to_{t}/{v}/seed_{n}' for s,t in DIRS for v in VARS for n in SEEDS]
getcontext().prec=50
READS={}
ERRORS=[]
CHECKS=defaultdict(int)
MAX_ABS=Decimal(0)
TOL=Decimal('5e-16')

def guard(event,args):
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        if Path(os.fsdecode(args[0])).suffix.lower() in ('.pt','.pth','.ckpt'):
            raise AssertionError('Weight access forbidden')
sys.addaudithook(guard)

def require(ok,msg):
    CHECKS['assertions']+=1
    if not ok: raise AssertionError(msg)

def read(path,expected=None,size=None):
    p=Path(path)
    key=str(p)
    if key not in READS:
        data=p.read_bytes()
        READS[key]={'path':key,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'data':data}
    r=READS[key]
    require(expected is None or r['sha256']==expected,'SHA mismatch: '+str(p))
    require(size is None or r['bytes']==size,'Size mismatch: '+str(p))
    return r['data']

def jread(path,expected=None,size=None):
    return json.loads(read(path,expected,size).decode('utf-8-sig'),parse_float=Decimal)

def close(actual,expected,label,scale=1):
    global MAX_ABS
    a=actual if isinstance(actual,Decimal) else Decimal(actual)
    b=expected if isinstance(expected,Decimal) else Decimal(expected)
    diff=abs(a-b)
    MAX_ABS=max(MAX_ABS,diff)
    require(a.is_finite() and b.is_finite() and diff<=TOL*scale,label+f': {a} != {b}; abs={diff}')
    CHECKS['decimal_numeric_comparisons']+=1

def stats(values):
    require(len(values)==3,'n=3')
    with localcontext() as ctx:
        ctx.prec=50
        mean=sum(values,Decimal(0))/Decimal(3)
        sd=(sum(((x-mean)**2 for x in values),Decimal(0))/Decimal(2)).sqrt()
        return +mean,+sd

def key(row,variant=True,seed=False):
    k=(row['source_dataset'],row['target_dataset'],row['task'])
    if variant:k+=(row['variant'],)
    if seed:k+=(row['seed'],)
    return k

report={'schema':'lgm.independent-transfer-aggregation-decimal-review.v1','created_utc':datetime.now(timezone.utc).isoformat(),'method':'Independent Decimal precision 50 arithmetic, sample variance divided by 2; no aggregation source imported or executed.','result_directory':str(RESULT),'passed':False,'findings':[]}
try:
    read(AGG,'d981b45c7ab7f1e4d7e018635771b63d84d307a14cdc2bcc5b4e5ec1f2e99bd3')
    main=jread(RESULT/'REPORT.json','22d8578b17fa7d71bd2078a630b62b8e8e45c3082a7b86f608580bd0a4478c7c')
    delivery=jread(RESULT/'DELIVERY.json','d8fd7ab801ffb61f448f4bc12cc68f03d95e7f53a141d6ea0096bc96f4541c22')
    require(main['passed'] is True and (main['accepted_input_runs'],main['seed_task_rows'],main['three_seed_groups'],main['within_task_contrasts'])==(12,66,22,11),'Aggregation report fixed scope')
    require(main['metric_fields']==list(METRICS) and main['sample_sd_ddof']==1,'Metrics/ddof contract')
    require(main['source']==delivery['source'],'Source seals equal')
    require(Path(main['source']['path'])==AGG,'Exact source path')
    read(main['source']['path'],main['source']['sha256'],main['source']['bytes'])
    require(Path(delivery['report']['path'])==RESULT/'REPORT.json','Report seal path')
    read(delivery['report']['path'],delivery['report']['sha256'],delivery['report']['bytes'])
    require(delivery['artifacts']==main['outputs'],'Output seal declarations agree')
    require(delivery['inputs']==main['input_bindings'],'Input seal declarations agree')
    expected_out={n+e for n in ('SEED_RESULTS','THREE_SEED_SUMMARY','FULL_MINUS_VISUAL') for e in ('.json','.csv')}|{'ANALYSIS.md'}
    require({Path(b['path']).name for b in main['outputs']}==expected_out and len(main['outputs'])==7,'Exact 7 output artifacts')
    for b in main['outputs']:
        require(Path(b['path']).parent==RESULT,'Output directory scope')
        read(b['path'],b['sha256'],b['bytes'])
    root=jread(ADOPTION,'fb7588357afa3e225b67088437233db397c067131fb8bc6adf97ce9ccbdd3bdd')
    require(root['accepted'] is True and root['transfer_identifiers']==EXPECTED_IDS,'Root adoption exact 12')
    rb=root['independent_transfer_review']
    review=jread(rb['path'],rb['sha256'],rb['bytes'])
    require(review['passed_with_stated_limits'] is True and [r['evaluation_id'] for r in review['runs']]==EXPECTED_IDS,'Final adopted review scope')
    require(rb['sha256']==main['independent_review_SHA'] and main['root_adoption_SHA']==READS[str(ADOPTION)]['sha256'],'Adopted ancestry')
    output_rows=jread(RESULT/'SEED_RESULTS.json')
    groups=jread(RESULT/'THREE_SEED_SUMMARY.json')
    contrasts=jread(RESULT/'FULL_MINUS_VISUAL.json')
    require((len(output_rows),len(groups),len(contrasts))==(66,22,11),'Actual output lengths')
    seed_index={key(r,seed=True):r for r in output_rows}
    group_index={key(r):r for r in groups}
    contrast_index={key(r,variant=False):r for r in contrasts}
    require((len(seed_index),len(group_index),len(contrast_index))==(66,22,11),'Unique output identities')
    input_bindings={str(Path(b['path'])):b for b in main['input_bindings']}
    require(len(input_bindings)==14,'Exactly 14 input bindings')
    for b in (root['independent_transfer_review'],):
        require(str(Path(b['path'])) in input_bindings,'Review input included')
    truth={}
    scales={}
    expected_tasks={
        'university1652':('university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite'),
        'sues200':tuple(n for a in ('150','200','250','300') for n in (f'sues200_uav_{a}m_to_satellite',f'sues200_satellite_to_uav_{a}m'))}
    for ordinal,run in enumerate(review['runs'],1):
        direction,variant,seedpart=run['evaluation_id'].split('/')
        source,target=direction.split('_to_'); seed=int(seedpart[5:])
        require((source,target) in DIRS and variant in VARS and seed in SEEDS,'Fixed source/run identity')
        bindings=[b for b in run['artifacts'] if Path(b['snapshot']).name=='metrics.json']
        require(len(bindings)==1,'One metrics snapshot')
        b=bindings[0]
        require(Path(b['snapshot']).parent.name==f'r{ordinal:02d}','Snapshot ordinal')
        ib=input_bindings[str(Path(b['snapshot']))]
        require((ib['sha256'],ib['bytes'])==(b['sha256'],b['bytes']),'Input metric binding agrees with adopted review')
        obj=jread(b['snapshot'],b['sha256'],b['bytes'])
        require((obj['source_dataset'],obj['target_dataset'],obj['variant'],obj['seed'])==(source,target,variant,seed),'Metrics identity')
        require(obj['schema_version']=='lgm-game.cross-dataset-metrics.v1' and obj['unit']=='fraction' and obj['full_gallery'] is True,'Metrics schema')
        require(obj['AP_definition']=='Official trapezoidal interpolation used by the frozen University-1652/SUES evaluator.','Exact AP definition')
        require(set(obj['results'])==set(expected_tasks[target]),'Exact target tasks')
        for task,result in obj['results'].items():
            k=(source,target,task,variant,seed)
            require(k not in truth,'No duplicate input task')
            scale={f:result[f] for f in ('protocol','queries','gallery','query_identities','gallery_identities')}
            if target=='university1652':
                suffix=task.removeprefix('university1652_')
                qp,gp,q,g={'drone_to_satellite':('query_drone','gallery_satellite',37855,951),'satellite_to_drone':('query_satellite','gallery_drone',701,51355),'street_to_satellite':('query_street','gallery_satellite',2579,951)}[suffix]
                expected_scale=dict(protocol=f'official test/{qp} -> test/{gp}',queries=q,gallery=g,query_identities=701,gallery_identities=951)
            elif task.startswith('sues200_uav_'):
                expected_scale=dict(protocol='official 80 test IDs as query; all 200 satellite IDs in gallery',queries=4000,gallery=200,query_identities=80,gallery_identities=200)
            else:
                alt=task.removeprefix('sues200_satellite_to_uav_').removesuffix('m')
                expected_scale=dict(protocol=f'official 80 test IDs as query; all 200 {alt}m UAV IDs in gallery',queries=80,gallery=10000,query_identities=80,gallery_identities=200)
            require(scale==expected_scale,'Actual transfer protocol/scale')
            require(k[:3] not in scales or scales[k[:3]]==scale,'Stable protocol across variants/seeds')
            scales[k[:3]]=scale
            expected=dict(source_dataset=source,target_dataset=target,task=task,variant=variant,seed=seed,**scale,unit='fraction',**{m:result[m] for m in METRICS})
            require(seed_index[k]==expected,'Exact seed row from sealed metrics')
            require(all(Decimal(0)<=result[m]<=Decimal(1) for m in METRICS),'Metric bounds')
            truth[k]={m:result[m] for m in METRICS}
    require(len(truth)==66 and set(truth)==set(seed_index),'All seed rows independently reproduced')
    for task_key,scale in scales.items():
        for variant in VARS:
            k=task_key+(variant,); out=group_index[k]
            expected_meta=dict(source_dataset=task_key[0],target_dataset=task_key[1],task=task_key[2],variant=variant,n_seeds=3,**scale,unit='fraction')
            numeric={m+s for m in METRICS for s in ('_mean','_sample_sd')}
            require({a:b for a,b in out.items() if a not in numeric}==expected_meta,'Group exact metadata')
            for m in METRICS:
                values=[truth[k+(s,)][m] for s in SEEDS]
                mean,sd=stats(values)
                close(out[m+'_mean'],mean,'Group mean '+str(k)+m)
                close(out[m+'_sample_sd'],sd,'Group sampleSD '+str(k)+m)
                CHECKS['group_metric_summaries']+=1
        out=contrast_index[task_key]
        numeric={m+s for m in METRICS for s in ('_seed_1_delta','_seed_2_delta','_seed_3_delta','_mean_delta','_paired_sample_sd','_mean_delta_x100')}
        expected_meta=dict(source_dataset=task_key[0],target_dataset=task_key[1],task=task_key[2],contrast='full_minus_visual',n_paired_seeds=3,**scale,unit='fraction_difference')
        require({a:b for a,b in out.items() if a not in numeric}==expected_meta,'Contrast exact metadata')
        for m in METRICS:
            values=[truth[task_key+('full',s)][m]-truth[task_key+('visual',s)][m] for s in SEEDS]
            mean,sd=stats(values)
            for s,value in zip(SEEDS,values):close(out[f'{m}_seed_{s}_delta'],value,'Same-seed delta')
            close(out[m+'_mean_delta'],mean,'Delta mean')
            close(out[m+'_paired_sample_sd'],sd,'Paired sampleSD')
            close(out[m+'_mean_delta_x100'],mean*100,'Delta x100',scale=100)
            CHECKS['paired_metric_summaries']+=1
    for stem,objects in [('SEED_RESULTS',output_rows),('THREE_SEED_SUMMARY',groups),('FULL_MINUS_VISUAL',contrasts)]:
        with (RESULT/(stem+'.csv')).open(encoding='utf-8',newline='') as f:
            reader=csv.DictReader(f); parsed=list(reader)
            require(set(reader.fieldnames)==set(objects[0]),'CSV exact fields')
        require(len(parsed)==len(objects),'CSV row count')
        for csvrow,obj in zip(parsed,objects):
            require(set(csvrow)==set(obj),'CSV exact row schema')
            for field,value in obj.items():
                if isinstance(value,(int,Decimal)):
                    require(Decimal(csvrow[field])==Decimal(value),'CSV/JSON exact numeric text equality')
                else:require(csvrow[field]==value,'CSV/JSON string equality')
        CHECKS['csv_json_tables']+=1
    text=read(RESULT/'ANALYSIS.md').decode('utf-8')
    require('n−1 denominator' in text and 'without significance claims' in text,'Presentation scope/SD declaration')
    require('percentage points for R@1/mAP and scaled points for MRR' in text,'Delta displayed units')
    require(not any(m in sys.modules for m in ('numpy','torch','pandas','scipy','matplotlib')),'No scientific imports')
    report.update(passed=True,scope=dict(accepted_runs=12,seed_task_rows=66,task_variant_groups=22,group_metric_summaries=66,paired_task_contrasts=11,paired_metric_summaries=33,seed_deltas=99),numeric_method=dict(precision=50,sample_sd_denominator=2,absolute_tolerance_fraction=str(TOL),absolute_tolerance_x100=str(TOL*100),max_abs_difference=str(MAX_ABS)),seal_verified=dict(source=True,report=True,delivery=True,output_artifacts=7,sealed_metrics=12),checks=dict(CHECKS),scientific_imports=[],weight_bytes_read=0,aggregation_source_executed=False,existing_outputs_modified=False)
    companion=read(EX/'transfer_results_20260929/README.md','58bf8762dddface66fd67db0c2b85540a77e849310002611f98e7eb86d2c8a85').decode('utf-8-sig')
    require('trapezoid' in companion.lower(),'Companion AP definition clarification')
    report['findings']=[]
    report['presentation_note']='Original ANALYSIS.md mAP shorthand is explicitly clarified by sealed companion README.md as official trapezoidal mAP.'
    report['checks']=dict(CHECKS)
    report['checker_revision_note']='V1 verification report retained. V2 scales tolerance by 100 for x100 display fields and explicitly sets the global Decimal context to precision 50; no producer rerun or output changes.'
except Exception as exc:
    report.update(error=repr(exc),checks=dict(CHECKS),max_abs_difference=str(MAX_ABS))
finally:
    report['inputs_read']=[{k:v for k,v in r.items() if k!='data'} for r in READS.values()]
    report['review_source']={'path':str(Path(__file__)),'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out=HERE/'INDEPENDENT_TRANSFER_AGGREGATION_DECIMAL_REVIEW_V2_20260929.json'
    with out.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({'passed':report['passed'],'report':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'max_abs_difference':report.get('numeric_method',{}).get('max_abs_difference',report.get('max_abs_difference')),'checks':report.get('checks'),'error':report.get('error')},ensure_ascii=True))

