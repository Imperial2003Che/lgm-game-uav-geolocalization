"""Independent chart data contract from adopted small CSVs; no producer import."""
from pathlib import Path
from decimal import Decimal,getcontext
import csv,hashlib,json,datetime
getcontext().prec=50
HERE=Path(__file__).absolute().parent
EX=HERE.parent
ROOT_REPORT=EX/'pipeline_post_robustness_audit_20260929_1448/ROOT_POST_ROBUSTNESS_ADOPTION.json'
ROOT_SHA='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
SEALED=EX/'pipeline_post_robustness_audit_20260929_1448/a1/aggregate'
FAMILIES=['gaussian_noise','gaussian_blur','brightness','contrast','center_occlusion','rotation']
METRICS=['r_at_1','official_trapezoid_mAP']
def binding(path):
    raw=path.read_bytes();return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def csvrows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))
def key(row):return tuple(row[name] for name in ('dataset','variant','seed','task','corruption','severity_index','metric'))
def main():
    assert binding(ROOT_REPORT)['sha256']==ROOT_SHA
    root=read(ROOT_REPORT);pins={r['path']:r for r in root['bindings']}
    used=[]
    def verify(path):
        actual=binding(path);assert pins[str(path)]==actual;used.append(actual);return actual
    indexpath=SEALED/'figure_index.json';verify(indexpath);index=read(indexpath)
    allpath=SEALED/'source_data/robustness_all_tasks_source.csv';verify(allpath);allrows=csvrows(allpath)
    assert len(allrows)==3960 and len({key(r) for r in allrows})==3960
    lookup={key(r):r for r in allrows}
    assert len(index['figures'])==22 and index['task_aggregation_used'] is False
    cards=[];assertions=4;number_checks=0
    for item in index['figures']:
        path=SEALED/item['source_csv'];verify(path);rows=csvrows(path)
        assert len(rows)==60 and item['metric'] in METRICS
        expected={(variant,family,str(severity)) for variant in ('visual','full') for family in FAMILIES for severity in range(1,6)}
        assert {(r['variant'],r['corruption'],r['severity_index']) for r in rows}==expected
        baselines={};parameters={}
        for row in rows:
            assert row==lookup[key(row)]
            assert row['dataset']==item['dataset'] and row['task']==item['task'] and row['metric']==item['metric'] and row['seed']=='1'
            C=Decimal(row['clean_fraction']);K=Decimal(row['corrupted_fraction'])
            assert C>0 and 0<=K<=1 and C<=1
            expected_values={'absolute_drop_fraction':C-K,'percentage_point_drop':(C-K)*100,
                'relative_drop_fraction':(C-K)/C,'relative_drop_percent':(C-K)/C*100,
                'retained_percent_of_clean':K/C*100}
            for field,value in expected_values.items():
                tolerance=Decimal('2e-15') if field in ('absolute_drop_fraction','relative_drop_fraction') else Decimal('1e-10')
                assert abs(Decimal(row[field])-value)<=tolerance,(path.name,field,row[field],str(value))
                number_checks+=1
            baselines.setdefault(row['variant'],set()).add(row['clean_fraction'])
            parameters[(row['corruption'],row['severity_index'])]=(row['parameter'],row['value'],row['units'])
            assertions+=4
        assert all(len(value)==1 for value in baselines.values()) and len(parameters)==30
        cards.append({'dataset':item['dataset'],'task':item['task'],'metric':item['metric'],'csv':binding(path),
          'row_count':60,'queries':sorted({r['queries'] for r in rows}),'gallery':sorted({r['gallery'] for r in rows}),
          'own_clean_fraction':{variant:next(iter(value)) for variant,value in baselines.items()},
          'own_clean_percent':{variant:str(Decimal(next(iter(value)))*100) for variant,value in baselines.items()},
          'retention_min':str(min(Decimal(r['retained_percent_of_clean']) for r in rows)),
          'retention_max':str(max(Decimal(r['retained_percent_of_clean']) for r in rows)),
          'retention_over_100_rows':sum(Decimal(r['retained_percent_of_clean'])>100 for r in rows),
          'parameter_sequences':{family:[{'severity':severity,'parameter':parameters[(family,str(severity))][0],
             'value':parameters[(family,str(severity))][1],'units':parameters[(family,str(severity))][2]} for severity in range(1,6)] for family in FAMILIES}})
        assertions+=3
    assert len({(r['task'],r['metric']) for r in cards})==22
    plotted={key(r) for r in allrows if r['metric'] in METRICS}
    assert len(plotted)==1320 and len(allrows)-len(plotted)==2640
    report={'schema':'independent-robustness-chart-data-contract.v1','time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'source':binding(Path(__file__)),'root_adoption':binding(ROOT_REPORT),'adopted_small_inputs':used,
      'assertions':assertions,'decimal_formula_checks':number_checks,'total_aggregate_rows':3960,
      'plotted_metric_rows':1320,'remaining_unplotted_four_metric_rows':2640,'figures':cards,
      'design_contract':{'each_chart':'one official task and one metric; 2 variants x6 corruptions x5 severities =60 source rows',
        'point_at_C':'definitionally 100, permitted only for nonzero own clean baseline',
        'retention_percent':'100*corrupted_fraction/own_clean_fraction; retain >100 without clipping',
        'absolute_percentage_point_drop':'100*(clean-corrupted); distinct from retained percentage of clean',
        'clean_label':'Show Visual/Full own absolute clean percentage beside each task figure; especially low-baseline street task',
        'font':'At final stated physical size every visible text >=8pt; axes start zero; no clipped markers or labels',
        'caption':'seed1 descriptive only, no pooling/error bars/CI/SD/significance; Full cached-clean versus online-corrupt evidence paths',
        'editability':'SVG native text/vector; PPT native shapes/text, no raster/image/svg embedding'},
      'limits':['This stage verifies only the adopted small CSV chart contract. New SVG/PPT artifacts have not yet been reviewed.',
         'Decimal50 reconstruction tolerances account for stored binary64 CSV serialization; no model/query/cache/weight/image rerun.',
         'All original evidence inheritance and Full cache/online limitations remain.']}
    with (HERE/'DATA_CONTRACT.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'report':binding(HERE/'DATA_CONTRACT.json'),'assertions':assertions,'formula_checks':number_checks},ensure_ascii=False))
if __name__=='__main__':main()
