"""Independent small-source display contract for new native Visio conversion.
No producer imports; no old scientific validation or seed-statistic recomputation.
"""
from pathlib import Path
import csv, datetime, hashlib, io, json, traceback, xml.etree.ElementTree as E
from decimal import Decimal

W=Path(__file__).resolve().parent
BASE=W.parent.parent
S=BASE/'formal_results_native_20260929'
P=BASE/'formal_main_native_ppt_20260929_1548'
NS={'s':'http://www.w3.org/2000/svg'}
checks=0
def ck(v,m):
 global checks
 checks+=1
 if not v: raise AssertionError(m)
def desc(p):
 b=Path(p).read_bytes()
 return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def save(p,x):
 with Path(p).open('x',encoding='utf-8',newline='\n') as f: json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def pinned(p,h):
 d=desc(p);ck(d['sha256']==h,str(p));return d
def main():
 roots=[pinned(P/'ROOT_DELIVERY_ADOPTION.json','4d01ad9310e8d726e7a0b5e9852142a51f56a079a30e386d814161f8b328787b'),pinned(S/'ROOT_NATIVE_SVG_REVIEW.json','ac010cc27c27fa94a9fdd3e860af84c330a8e4cc6efa3c66b2e6a8000d6253ca'),pinned(S/'PRIMARY_CLAIM_REVIEW.json','0e29cdb0412b148100788b02276e9a9ef4a7aed4a1f5d892fb088a0ff184cdb6')]
 adopted=json.loads(Path(roots[0]['path']).read_bytes())
 bound={x['path']:x for x in adopted['bindings']}
 inputs=roots[:];figs=[]
 variants=['visual','content','style','visual_content','visual_style','full']
 tasks={'university1652':['university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite'], 'sues200':[t for h in [150,200,250,300] for t in [f'sues200_uav_{h}m_to_satellite',f'sues200_satellite_to_uav_{h}m']]}
 negative=0
 for ds in tasks:
  sv=S/'v2'/f'formal_main_{ds}_variants_native.svg';cv=S/'v2'/f'formal_main_{ds}_variants_source.csv'
  for f in [sv,cv]:
   d=desc(f);ck(d==bound[str(f)],'root selected binding '+str(f));inputs.append(d)
  rows=list(csv.DictReader(io.StringIO(cv.read_text(encoding='utf-8-sig'))))
  ck(len(rows)==len(tasks[ds])*6,'display rows');by={(r['task'],r['variant']):r for r in rows}
  ck(set(by)=={(t,v) for t in tasks[ds] for v in variants},'task variants')
  for r in rows:
   ck(r['dataset']==ds and r['n_seeds']=='3' and r['seeds']=='1|2|3' and r['complete_seed_triplet'].lower()=='true','saved three-seed complete row')
  tree=E.fromstring(sv.read_bytes());vb=[float(x) for x in tree.attrib['viewBox'].split()]
  width=float(tree.attrib['width'].removesuffix('mm'));height=float(tree.attrib['height'].removesuffix('mm'))
  ck(width==181.9,'physical width');primitives=[]
  def walk(el,path):
   tag=el.tag.rsplit('}',1)[-1];path=path+([el.attrib['id']] if 'id' in el.attrib else [])
   ck('transform' not in el.attrib,'no unhandled transform')
   if tag in ('rect','line','circle','polygon','text'):
    primitives.append({'ordinal':len(primitives)+1,'shape_name':'SVG_'+str(len(primitives)+1).zfill(4),'tag':tag,'ancestors':path,'attrs':el.attrib,'text':''.join(el.itertext()) if tag=='text' else None})
    if tag=='text':
     ck(float(el.attrib['font-size'])*width/vb[2]*72/25.4>=8-1e-8,'physical SVG font >=8pt')
   else: ck(tag in ('svg','g','title','desc'),'unsupported native primitive '+tag)
   for child in el: walk(child,path)
  walk(tree,[])
  groups={g.attrib['id']:g for g in tree.findall('.//s:g',NS) if 'id' in g.attrib}
  for i,t in enumerate(tasks[ds]):
   for v in variants:
    r=by[t,v]
    for prefix,m,s in [('cell','r_at_1_mean_pct','r_at_1_sample_sd_pct'),('interval','official_trapezoid_mAP_mean_pct','official_trapezoid_mAP_sample_sd_pct')]:
     g=groups[f'{prefix}-{i}-{v}'];ck(g.attrib['data-task']==t and g.attrib['data-variant']==v,'SVG group key')
     ck(Decimal(g.attrib['data-mean'])==Decimal(r[m]) and Decimal(g.attrib['data-sd'])==Decimal(r[s]),'saved CSV mean/SD to SVG display attrs')
   vr,fr=by[t,'visual'],by[t,'full']
   negative+=int(Decimal(fr['r_at_1_mean_pct'])<Decimal(vr['r_at_1_mean_pct']) and Decimal(fr['official_trapezoid_mAP_mean_pct'])<Decimal(vr['official_trapezoid_mAP_mean_pct']))
  figs.append({'dataset':ds,'svg':desc(sv),'csv':desc(cv),'width_mm':width,'height_mm':height,'viewbox':vb,'tasks':tasks[ds],'variants':variants,'saved_display_rows':rows,'primitives':primitives,'shapes':len(primitives),'texts':sum(p['tag']=='text' for p in primitives),'cells':len(rows),'intervals':len(rows)})
 cap=S/'v2/CAPTIONS.md';cd=desc(cap);ck(cd==bound[str(cap)],'exact historical caption');inputs.append(cd)
 ck(negative==10,'preserve ten of eleven lower Full means')
 ck(sum(x['shapes'] for x in figs)==785 and sum(x['texts'] for x in figs)==216,'actual SVG primitive count, includes both backgrounds')
 out={'status':'passed_new_visio_display_contract','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':desc(__file__),'checks':checks,'input_bindings':inputs,'figures':figs,'negative_task_count':negative,'scope':{'figures':2,'r1_cells':66,'map_intervals':66,'texts':216,'svg_primitives_including_backgrounds':785},'limits':['New conversion display contract only; existing CSV means and sample SD are not recomputed from seeds.','R@1 percent heatmap and official trapezoidal mAP percent mean +/- sample SD; not CI. No pooling or significance.','All six variants, eleven tasks and four SUES heights retained; Full lower than Visual for both means on ten tasks, low absolute street exception.','Exact historical source caption is preserved; new Visio notes must describe only these two completed Visio figures.','Inherited checkpoint/cache/image SHA and historical provenance gaps remain; no scientific source, model, weights, NPZ, cache or image dataset reads.','No producer module or old validation suite was executed.']}
 save(W/'DATA_CONTRACT.json',out)
 print(json.dumps({'report':desc(W/'DATA_CONTRACT.json'),'checks':checks}))
if __name__=='__main__':
 try:main()
 except Exception:
  save(W/'DERIVATION_FAILURE.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':desc(__file__),'checks':checks,'traceback':traceback.format_exc()});raise
