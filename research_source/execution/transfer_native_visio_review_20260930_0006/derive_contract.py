"""Independent small-input T3 display contract; no producer imports or science runs."""
import collections
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

BASE=Path(__file__).resolve().parent
OUT=BASE.parent.parent
OLD=OUT/'transfer_native_figures_20260929_1750'
DATA=OLD/'output'
checks=0
def ck(v,label):
    global checks
    checks+=1
    if not v: raise AssertionError(label)
def close(a,b,label): ck(abs(float(a)-float(b))<1e-9,label)
def binding(p):
    b=p.read_bytes()
    return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def dump(name,v):
    with (BASE/name).open('x',encoding='utf-8',newline='\n') as f: json.dump(v,f,ensure_ascii=False,indent=2); f.write('\n')
adoption=json.loads((OLD/'ROOT_TRANSFER_NATIVE_ADOPTION.json').read_text(encoding='utf-8'))
ck(adoption['accepted'] is True,'adopted old SVG source')
bound={str(Path(x['path'])):x for x in adoption['bindings']}
paths=[DATA/'FIGURE_INDEX.json',DATA/'README.md',DATA/'CAPTIONS.md']+sorted((DATA/'source_data').glob('*'))+sorted((DATA/'native_svg').glob('*.svg'))+sorted(DATA.glob('*.pptx'))
bindings=[binding(OLD/'ROOT_TRANSFER_NATIVE_ADOPTION.json')]
for p in paths:
    got=binding(p); expect=bound[str(p)]
    ck(got['sha256']==expect['sha256'] and got['bytes']==expect['bytes'],'adopted bytes '+p.name)
    bindings.append(got)
summary=list(csv.DictReader((DATA/'source_data/THREE_SEED_SUMMARY.csv').open(encoding='utf-8-sig',newline='')))
seeds=list(csv.DictReader((DATA/'source_data/SEED_RESULTS.csv').open(encoding='utf-8-sig',newline='')))
ck(len(summary)==22 and len(seeds)==66,'22 summary groups and 66 seed-task rows')
rows={(r['source_dataset'],r['target_dataset'],r['task'],r['variant']):r for r in summary}
ck(len(rows)==22,'unique summary keys')
idx=json.loads((DATA/'FIGURE_INDEX.json').read_text(encoding='utf-8'))
figures=[]
metrics=['r_at_1','official_trapezoid_mAP','MRR']
for fi in idx['figures']:
    svg=DATA/fi['svg']; root=ET.parse(svg).getroot()
    prim=[e for e in root.iter() if e.tag.rsplit('}',1)[-1] not in ('svg','title','desc','g')]
    byid={e.attrib['id']:e for e in prim}
    ck(len(byid)==len(prim),'unique primitive ids '+fi['id'])
    ck(set(e.tag.rsplit('}',1)[-1] for e in prim)<={'rect','line','circle','text'},'native primitive tags')
    ck(not any('transform' in e.attrib for e in root.iter()),'no implicit transformations')
    fonts=[float(e.attrib['font-size']) for e in prim if e.tag.endswith('text')]
    ck(min(fonts)==8 and set(fonts)=={8,9,10},'8/9/10 point fonts')
    close(root.attrib['width'][:-2],181.9,'physical width')
    close(root.attrib['height'][:-2],fi['heightMm'],'physical height')
    vb=list(map(float,root.attrib['viewBox'].split()))
    close(vb[2]/float(root.attrib['width'][:-2]),72/25.4,'physical point x scale')
    close(vb[3]/float(root.attrib['height'][:-2]),72/25.4,'physical point y scale')
    ck(byid['training-evaluation-direction'].text==fi['title'],'direction title')
    ck(byid['MRR/heading'].text=='MRR × 100','MRR is scaled rank, not percentage')
    metric_values=[]
    for metric in metrics:
        axis=next(a for a in fi['axes'] if a['metric']==metric)
        ck(axis['min']==0,'zero axis')
        line=byid[metric+'/axis']
        close(line.attrib['x1'],axis['x'],'axis left'); close(line.attrib['x2'],axis['x']+axis['width'],'axis right')
        for task in fi['tasks']:
            for variant in ('visual','full'):
                r=rows[(fi['sourceDataset'],fi['targetDataset'],task,variant)]
                ck(r['n_seeds']=='3' and r['unit']=='fraction','stored units and three seeds')
                mean=float(r[metric+'_mean']); sd=float(r[metric+'_sample_sd'])
                key=task+'/'+variant+'/'+metric
                bar=byid[key+'/sd-line']; marker=byid[key+'/mean']; text=byid[key+'/value']
                display=f'{mean*100:.3f} ± {sd*100:.3f}'
                ck(text.text==display,'visible mean/SD '+key)
                expected=axis['x']+100*mean/axis['max']*axis['width']
                center=float(marker.attrib['cx']) if variant=='visual' else float(marker.attrib['x'])+float(marker.attrib['width'])/2
                close(center,expected,'mean coordinate '+key)
                lo=axis['x']+100*(mean-sd)/axis['max']*axis['width']
                hi=axis['x']+100*(mean+sd)/axis['max']*axis['width']
                close(bar.attrib['x1'],lo,'full SD left '+key);close(bar.attrib['x2'],hi,'full SD right '+key)
                ck(lo>=axis['x']-1e-9 and hi<=axis['x']+axis['width']+1e-9,'unclipped full interval '+key)
                for cap,expectedx in [('sd-cap-left',lo),('sd-cap-right',hi)]:
                    close(byid[key+'/'+cap].attrib['x1'],expectedx,'cap '+key)
                    close(byid[key+'/'+cap].attrib['x2'],expectedx,'cap vertical '+key)
                seedrows=[s for s in seeds if (s['source_dataset'],s['target_dataset'],s['task'],s['variant'])==(fi['sourceDataset'],fi['targetDataset'],task,variant)]
                ck(sorted(int(s['seed']) for s in seedrows)==[1,2,3],'seed identifiers '+key)
                metric_values.append(dict(task=task,variant=variant,metric=metric,meanFraction=r[metric+'_mean'],sampleSdFraction=r[metric+'_sample_sd'],display=display,seedValues=[dict(seed=int(s['seed']),value=s[metric]) for s in seedrows]))
    with zipfile.ZipFile(DATA/fi['pptx']) as z:
        nr=ET.fromstring(z.read('ppt/notesSlides/notesSlide1.xml'))
        notes='\n'.join(nr.itertext())
    for name in ['THREE_SEED_SUMMARY.csv','SEED_RESULTS.csv','FULL_MINUS_VISUAL.csv']:
        ck((DATA/'source_data'/name).read_text(encoding='utf-8-sig') in notes,'exact CSV in original notes '+name)
    ck(fi['caption'] in notes,'full caption retained')
    notes_path=BASE/(fi['id']+'_expected_notes.txt')
    with notes_path.open('x',encoding='utf-8',newline='\n') as f:f.write(notes)
    figures.append(dict(id=fi['id'],sourceDataset=fi['sourceDataset'],targetDataset=fi['targetDataset'],widthMm=fi['widthMm'],heightMm=fi['heightMm'],viewBox=vb,expectedNativeShapes=len(prim),expectedTexts=len(fonts),primitiveCounts=dict(collections.Counter(e.tag.rsplit('}',1)[-1] for e in prim)),tasks=fi['tasks'],axes=fi['axes'],values=metric_values,notes=binding(notes_path),svg=binding(svg),primitives=[dict(ordinal=i+1,tag=e.tag.rsplit('}',1)[-1],attrs=dict(e.attrib),text=''.join(e.itertext()) if e.tag.endswith('text') else '') for i,e in enumerate(prim)]))
ck(sum(len(f['values']) for f in figures)==66,'all 66 displayed summaries')
ck(sum(f['expectedNativeShapes'] for f in figures)==487,'487 including both backgrounds')
ck(sum(f['expectedTexts'] for f in figures)==144,'144 text objects')
for task in {r['task'] for r in summary}:
    rr={r['variant']:r for r in summary if r['task']==task}
    ck(float(rr['full']['r_at_1_mean'])<float(rr['visual']['r_at_1_mean']),'negative Full mean R1 '+task)
report=dict(schema='independent-t3-visio-input-display-contract.v1',utc=dt.datetime.now(dt.timezone.utc).isoformat(),passed=True,checks=checks,source=binding(Path(__file__)),inputs=bindings,figures=figures,scope=dict(summaryGroups=22,metricSummaries=66,seedTaskRows=66,nativeShapes=487,nativeTexts=144),limits=['Small adopted inputs only; no original NPZ, weights, images, caches or metrics traversal; no scientific suite or aggregation rerun.','No recomputation of means, SD or inference: saved numbers are only multiplied by 100 for label/coordinate comparisons.','Sample SD denominator 2; not SE, CI or significance; no cross-task, height, direction or seed pooling.','R1/mAP display percentages; MRR scaled by 100; official trapezoidal AP semantics and inherited evidence limitations retained.','VSDX, true COM execution, export and visual acceptance remain pending; no COM was launched by this reviewer.'])
dump('DATA_CONTRACT.json',report)
print(json.dumps(dict(passed=True,checks=checks,scope=report['scope'],contract=binding(BASE/'DATA_CONTRACT.json')),ensure_ascii=False))
