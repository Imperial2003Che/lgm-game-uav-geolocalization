"""Independent transcription review against adopted small CSVs. No scientific recomputation."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone
import csv,hashlib,json,re
R=Path(__file__).resolve().parent;O=R.parent.parent
M=O/'manuscript_evidence_revision_20260930_0202/manuscript'
T=M/'tables/evidence_20260930'
def desc(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
task_labels={'University D2S':'university1652_drone_to_satellite','University S2D':'university1652_satellite_to_drone','University Street2S':'university1652_street_to_satellite'}
for height in [150,200,250,300]:
 task_labels[rf'SUES U{height}$\to$S']=f'sues200_uav_{height}m_to_satellite'
 task_labels[rf'SUES S$\to$U{height}']=f'sues200_satellite_to_uav_{height}m'
variants=['visual','content','style','visual_content','visual_style','full']
official_paths=[O/'formal_results/formal_main_university1652_variants_source.csv',O/'formal_results/formal_main_sues200_variants_source.csv']
official_rows=rows(official_paths[0])+rows(official_paths[1]); official={(x['task'],x['variant']):x for x in official_rows}
transfer_path=O/'transfer_native_figures_20260929_1750/output/source_data/THREE_SEED_SUMMARY.csv'
transfer_rows=rows(transfer_path); transfer={(x['task'],x['variant']):x for x in transfer_rows}
sensitivity_path=O/'formal_results/formal_sensitivity_source.csv'
sensitivity_rows=rows(sensitivity_path); sensitivity={(x['task'],x['setting']):x for x in sensitivity_rows}
results=[];table_counts={}
def check_scalar(display,source_value,scale,table,task,column,field):
 value=Decimal(source_value)*Decimal(scale);token=display.replace('$','').strip()
 if token=='<0.001':
  ok=Decimal(0)<value<Decimal('0.0005')
 else:
  assert re.fullmatch(r'\d+\.\d{3}',token),(table,task,token)
  shown=Decimal(token);ok=abs(shown-value)<=Decimal('0.00050000000001')
  if shown==0:ok=ok and value==0
 results.append({'table':table,'task':task,'column':column,'field':field,'saved_value':source_value,'scale':scale,'displayed':display,'passed':ok})
def read_table(name):
 out={}
 for line in (T/name).read_text(encoding='utf-8').splitlines():
  if not line.startswith(('University ','SUES ')):continue
  parts=[x.strip() for x in line[:-2].split('&')]
  label=parts[0];assert label in task_labels,(name,label)
  assert label not in out,(name,label)
  out[label]=parts[1:]
 assert set(out)==set(task_labels),(name,set(out)^set(task_labels))
 table_counts[name]=len(out)
 return out
for filename,metric in [('official_r1.tex','r_at_1'),('official_map.tex','official_trapezoid_mAP')]:
 for label,cells in read_table(filename).items():
  task=task_labels[label];assert len(cells)==6
  for variant,cell in zip(variants,cells):
   source=official[task,variant];assert source['n_seeds']=='3' and source['seeds']=='1|2|3' and source['complete_seed_triplet']=='true'
   pair=cell.strip('$').split(r'\pm');assert len(pair)==2
   for display,stat in zip(pair,['mean','sample_sd']):
    field=f'{metric}_{stat}_pct';check_scalar(display,source[field],1,filename,task,variant,field)
for label,cells in read_table('transfer_all_tasks.tex').items():
 task=task_labels[label];assert len(cells)==6
 keys=[(metric,variant) for metric in ['r_at_1','official_trapezoid_mAP','MRR'] for variant in ['visual','full']]
 for (metric,variant),cell in zip(keys,cells):
  source=transfer[task,variant];assert source['n_seeds']=='3' and source['unit']=='fraction'
  assert source['target_dataset']==('university1652' if task.startswith('university') else 'sues200')
  assert source['source_dataset']!=source['target_dataset']
  pair=cell.strip('$').split(r'\pm');assert len(pair)==2
  for display,stat in zip(pair,['mean','sample_sd']):
   field=f'{metric}_{stat}';check_scalar(display,source[field],100,'transfer_all_tasks.tex',task,variant,field)
for filename,metric in [('sensitivity_r1.tex','r_at_1_pct'),('sensitivity_map.tex','official_trapezoid_mAP_pct')]:
 for label,cells in read_table(filename).items():
  task=task_labels[label];assert len(cells)==4
  for setting,display in zip(['full','backbone_resnet50','embed_dim_256','embed_dim_1024'],cells):
   source=sensitivity[task,setting];assert source['seed']=='1' and source['variant']=='full'
   check_scalar(display,source[metric],1,filename,task,setting,metric)
assert len(results)==484
formal_contrasts={metric:[task for task in task_labels.values() if Decimal(official[task,'full'][f'{metric}_mean_pct'])<Decimal(official[task,'visual'][f'{metric}_mean_pct'])] for metric in ['r_at_1','official_trapezoid_mAP']}
transfer_contrasts={metric:[task for task in task_labels.values() if Decimal(transfer[task,'full'][f'{metric}_mean'])<Decimal(transfer[task,'visual'][f'{metric}_mean'])] for metric in ['r_at_1','official_trapezoid_mAP','MRR']}
robust_path=O/'execution/pipeline_post_robustness_audit_20260929_1448/a1/aggregate/source_data/robustness_all_tasks_source.csv'
robust=rows(robust_path)
robust_counts={'rows':len(robust),'task_variant_groups':len({(x['task'],x['variant']) for x in robust}),'corrupted_task_evaluations':len({(x['task'],x['variant'],x['corruption'],x['severity_index']) for x in robust}),'R1_mAP_rows':sum(x['metric'] in ['r_at_1','official_trapezoid_mAP'] for x in robust),'seeds':sorted({x['seed'] for x in robust}),'all_clean_denominators_positive':all(Decimal(x['clean_fraction'])>0 for x in robust)}
frozen_forest=O/'formal_results/formal_visual_vs_full_forest_source.csv'
forest=rows(frozen_forest)
definitions={'official_R1_lower_tasks':len(formal_contrasts['r_at_1']),'official_mAP_lower_tasks':len(formal_contrasts['official_trapezoid_mAP']),'transfer_R1_lower_tasks':len(transfer_contrasts['r_at_1']),'transfer_mAP_lower_tasks':len(transfer_contrasts['official_trapezoid_mAP']),'transfer_MRR_lower_tasks':len(transfer_contrasts['MRR']),'official_test_family':sorted({x['holm_family_size'] for x in forest}),'official_test_rows':len(forest),'robustness':robust_counts}
checks=[all(x['passed'] for x in results),len(formal_contrasts['r_at_1'])==10,len(formal_contrasts['official_trapezoid_mAP'])==10,len(transfer_contrasts['r_at_1'])==11,len(transfer_contrasts['official_trapezoid_mAP'])==10,len(transfer_contrasts['MRR'])==10,robust_counts=={'rows':3960,'task_variant_groups':22,'corrupted_task_evaluations':660,'R1_mAP_rows':1320,'seeds':['1'],'all_clean_denominators_positive':True},len(forest)==33 and all(x['holm_family_size']=='33' for x in forest)]
report={'schema':'independent-manuscript-numeric-transcription-review.v1','utc':datetime.now(timezone.utc).isoformat(),'scope':'Direct parsing of actual five TeX tables; comparison to stored adopted CSV fields, units and task/variant labels. Stored row-count/sign checks only. No recomputation of seed means/SD, bootstrap, tests, queries, rankings or scientific outputs; author transcript/checker not used.','passed':all(checks),'scalar_count':len(results),'tables':{name:desc(T/name) for name in table_counts},'table_task_rows':table_counts,'sources':[desc(p) for p in official_paths+[transfer_path,sensitivity_path,robust_path,frozen_forest]],'definitions':definitions,'scalar_transcriptions':results,'science_executed':False,'producer_executed':False}
out=R/'NUMERIC_TRANSCRIPTION_REVIEW.json'
with out.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'report':desc(out),'passed':report['passed'],'scalar_count':len(results),'failed_cells':[x for x in results if not x['passed']],'definitions':definitions},ensure_ascii=True))
if not report['passed']:raise SystemExit(1)
