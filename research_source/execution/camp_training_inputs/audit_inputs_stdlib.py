"""Check recorded image inventory and three real preparation plans without image decoding."""
from pathlib import Path
from collections import Counter
import datetime,hashlib,json,sys
HERE=Path(__file__).resolve().parent
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
path=HERE/'university_train_content_manifest.json'
data=json.loads(path.read_text(encoding='utf-8'))
assert data['split']=='train' and data['identity_count']==701
rows=data['files'];paths=[r['path'] for r in rows]
assert len(paths)==len(set(paths))==38555
counts=Counter(p.split('/')[0] for p in paths)
assert counts=={'satellite':701,'drone':37854}
ids={v:{p.split('/')[1] for p in paths if p.startswith(v+'/')} for v in counts}
assert ids['satellite']==ids['drone'] and len(ids['drone'])==701
for row in rows:
    assert row['bytes']>0 and len(row['sha256'])==64
    assert not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
plans=[];comparables=[]
for seed in (1,2,3):
    planpath=HERE/f'seed_{seed}_plan.json'
    plan=json.loads(planpath.read_text(encoding='utf-8'))
    assert plan['seed']==seed
    assert plan['data_manifest_sha256']==sha(path)
    assert Path(plan['data_manifest_path']).resolve()==path.resolve()
    assert not Path(plan['output_directory']).exists(),'No training output should exist at preparation stage'
    assert plan['protocol']['num_workers']==0 and plan['protocol']['epochs']==1
    assert plan['protocol']['microbatch_pairs']==24 and plan['protocol']['gradient_accumulation']==1
    assert plan['environment']['packages']['torch']=='2.11.0+cu126'
    assert plan['environment']['packages']['numpy']=='2.4.4'
    comparable={k:v for k,v in plan.items() if k not in ('seed','created_utc','output_directory')}
    comparables.append(comparable)
    plans.append({'seed':seed,'path':str(planpath),'sha256':sha(planpath),'output_directory':plan['output_directory'],'package_count':len(plan['environment']['packages'])})
assert comparables[0]==comparables[1]==comparables[2]
assert not any(name in sys.modules for name in ('torch','numpy','scipy','PIL','matplotlib'))
report={'status':'input_preparation_verified_not_trained','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest':str(path),'manifest_sha256':sha(path),'file_count':len(rows),'counts_by_view':dict(counts),'unique_identities':701,'total_image_bytes':sum(r['bytes'] for r in rows),'image_contents_hashed_by':'original prepare_or_train.py inventory, stdlib streaming SHA256','image_decoding_performed':False,'scientific_modules_imported':[],'plans':plans,'plan_differences_only':['seed','created_utc','output_directory'],'note':'An early make-plan invocation before inventory completion failed with FileNotFoundError; it created no plan. These three plans were generated only after inventory exited successfully, using pretrained SHA read directly from verified metadata.'}
(HERE/'INPUT_VERIFICATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
