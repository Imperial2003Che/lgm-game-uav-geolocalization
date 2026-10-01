"""Focused static-review gap closure on the sealed visual1 audit; stdlib only."""
import ast, csv, hashlib, io, json, re, struct, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).parent
BASE=HERE/'a1'
OUT=HERE/'addendum'
OUT.mkdir()
READS=[]
COUNT=0

def check(value,message):
    global COUNT
    COUNT+=1
    if not value:raise AssertionError(message)
def read(path,digest=None,size=None):
    path=Path(path);data=path.read_bytes();actual=hashlib.sha256(data).hexdigest()
    check(digest is None or actual==digest,'Input SHA mismatch '+str(path))
    check(size is None or len(data)==size,'Input size mismatch '+str(path))
    READS.append(dict(path=str(path),sha256=actual,bytes=len(data)))
    return data
review=json.loads(read(BASE/'REVIEW.json','0966fa78f680c26ef4dc58a891671790852b00596a4f763194a6b3c102b87855'))
metadata=json.loads(read(BASE/'METADATA.json','74e97d61889df751df5fef12ba8aefdfb1bdeaf64350ac3c6f034539fb76968d'))
read(HERE/'review_visual1.py','5ee21f317aab75ef700115ed7f25faa958109b28338f5010591f1bfff9b375c0')
check(review['passed_with_stated_limits'] is True and review['scientific_modules']==[],'Base scope/modules')
check((review['accepted_runs'],review['accepted_corrupted_conditions'],review['accepted_corrupted_tasks'],review['accepted_clean_tasks'])==(1,30,90,3),'Base scope')
bindings={b['path']:b for b in metadata['files']}
CACHE={}
def bound(relative):
    path=BASE/'r'/relative
    if str(path) not in CACHE:
        b=bindings[str(path)];CACHE[str(path)]=read(path,b['sha256'],b['bytes'])
    return CACHE[str(path)]
def doc(relative):return json.loads(bound(relative).decode('utf-8-sig'))
def header(npz,name):
    with zipfile.ZipFile(io.BytesIO(npz)) as z:
        with z.open(name+'.npy') as f:
            check(f.read(6)==b'\x93NUMPY','NPY magic')
            version=f.read(2);check(version in (b'\x01\x00',b'\x02\x00'),'NPY version')
            size=struct.unpack('<H' if version[0]==1 else '<I',f.read(2 if version[0]==1 else 4))[0]
            return ast.literal_eval(f.read(size).decode('latin1'))

manifest=doc('robustness_manifest.json')
config=doc('run_config.json')['immutable_config']
clean=doc('clean/condition_manifest.json')
check(clean['query_coverage']==manifest['clean_query_coverage'],'Exact clean coverage dict identity')
for field,count,pathsha in [('clean_query_coverage',41135,config['query_path_membership_sha256']),('clean_gallery_coverage',52306,config['gallery_path_membership_sha256'])]:
    c=manifest[field]
    check(c['expected_unique_images']==c['encoded_unique_images']==count and c['coverage_fraction']==1.0 and c['missing_images']==c['extra_images']==0 and c['complete'] is True,'Clean coverage completeness')
    check(c['path_membership_sha256']==pathsha and c['embedding_dim']==512 and c['embedding_storage_dtype_for_hash']=='little-endian float32','Clean coverage binding/type')
    check(c['query_content_style_evidence_mode']=='clean_cache' and c['pixels_decoded_for_every_active_visual_embedding'] is True and c['corruption_applied_before_all_model_preprocessing'] is False,'Clean provenance flags')
    check(re.fullmatch('[0-9a-f]{64}',c['encoded_feature_sha256']) is not None and c['elapsed_seconds']>=0,'Clean declared feature hash/time')

metricfields=['task','queries','gallery','query_identities','gallery_identities','r_at_1','r_at_5','r_at_10','r_at_20','official_trapezoid_mAP','MRR','mean_top1_margin','protocol']
dropfields=['task','metric','clean','corrupted','absolute_drop_fraction','percentage_point_drop','relative_drop_fraction','relative_drop_percent']
summaryfields=['corruption','severity_index','parameter','value','units']+dropfields
csvcount=0
def csv_header(relative,expected):
    global csvcount
    actual=next(csv.reader(io.StringIO(bound(relative).decode('utf-8-sig'))))
    check(actual==expected and len(actual)==len(set(actual)),'Exact ordered/unique CSV fields '+str(relative));csvcount+=1

npz_count=0
metric_count=0
for folder in [Path('clean')]+[Path('conditions')/c['name']/f'severity_{severity:02d}' for c in config['corruption_matrix'] for severity in range(1,6)]:
    metrics=doc(folder/'metrics.json')
    check(metrics['unit']=='fraction' and metrics['AP_definition']=='Official trapezoidal interpolation used by the University-1652/SUES reference evaluator.','Top-level metric/AP semantics')
    metric_count+=1
    csv_header(folder/'metrics.csv',metricfields)
    corrupted=folder!=Path('clean')
    if corrupted:csv_header(folder/'degradation_vs_clean.csv',dropfields)
    for task,scale in config['official_task_scale'].items():
        data=bound(folder/'per_query_arrays'/(task+'_per_query.npz'))
        for field in ['first_positive_rank_zero_based','top1_gallery_indices']+(['clean_first_positive_rank_zero_based'] if corrupted else []):
            h=header(data,field);check(h['descr']=='<i8' and h['shape']==(scale['queries'],) and h['fortran_order'] is False,'Exact producer int64 '+field)
        if corrupted:
            h=header(data,'top1_correctness_transition_corrupted_minus_clean')
            check(h['descr']=='|i1' and h['shape']==(scale['queries'],) and h['fortran_order'] is False,'Signed transition int8')
        npz_count+=1
csv_header('robustness_summary.csv',summaryfields)
check((npz_count,metric_count,csvcount)==(93,31,62),'Focused fixed scope')
check(not any(m in sys.modules for m in ('numpy','torch','PIL','pandas','scipy','matplotlib')),'No scientific modules')
report=dict(schema='bounded-visual1-review-gap-closure-v1',completed_utc=datetime.now(timezone.utc).isoformat(),passed=True,
    source=dict(path=str(Path(__file__)),sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
    base_review_sha256=READS[0]['sha256'],base_metadata_sha256=READS[1]['sha256'],input_bindings=READS,
    assertions=COUNT,npz_header_files=93,metrics_semantics_files=31,csv_order_unique_headers=62,
    closed_gaps=['Clean condition/top-level query coverage exact equality; full clean query/gallery coverage declarations',
        'Original exact CSV column order with no duplicates','Producer int64 rank/top1/clean-rank and signed int8 transition',
        'Top-level fraction unit and exact official trapezoidal AP definition','Explicit no-scientific-import assertion'],
    array_values_rechecked=False,original_gate_reexecuted=False,checkpoint_or_cache_or_image_bytes_read=False,
    prior_audit_or_scientific_files_modified=False,limits=review['limits'],
    note='V1 source and passed bounded report are retained unmodified. This addendum closes independent post-review structural checks; root adoption should bind both. No changed scientific data, model execution, or new robustness condition.')
p=OUT/'REVIEW_ADDENDUM.json'
with p.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source=report['source'],assertions=COUNT,inputs=len(READS)),ensure_ascii=False))
