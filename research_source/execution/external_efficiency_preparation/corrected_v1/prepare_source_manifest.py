"""Source-only sealing. No plan registration, release, data/model load or run."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
def artifact(path):
    path=Path(path).resolve()
    with path.open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':digest}

target=HERE/'SOURCE_MANIFEST.json'
if target.exists():raise RuntimeError('Refuse overwriting source preparation')
review=json.loads((PARENT/'SCOPE_INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
keys=('formal_t6','primitives','formal_model','clip_generator','clip_metadata')
frozen=[]
for key in keys:
    declared=review['sources'][key]
    actual=artifact(declared['path'])
    if actual!=declared:raise RuntimeError('Original reviewed source changed: '+key)
    frozen.append(actual)
sues_meta=Path(review['sources']['clip_metadata']['path']).with_name('sues200_clip_image_evidence.meta.json')
for path in (Path(review['sources']['clip_metadata']['path']),sues_meta):
    meta=json.loads(path.read_text(encoding='utf-8'))
    if meta['model']['name']!='openai/clip-vit-base-patch32' or meta['model']['revision_resolved']!='3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268':
        raise RuntimeError('Existing CLIP cache model/revision differs')
    if meta['run_configuration']['precision']!='fp16':raise RuntimeError('Existing CLIP precision differs')
frozen += [artifact(sues_meta),artifact(PARENT/'SCOPE_INDEPENDENT_REVIEW.json'),artifact(PARENT/'CORRECTIVE_MEASUREMENT_PLAN.md')]
checks=json.loads((HERE/'STDLIB_REVIEW.json').read_text(encoding='utf-8'))
if checks['check_count']!=30 or checks['scientific_imports'] or checks['real_gpu_test_executed']:
    raise RuntimeError('Expected 30 standard-library-only component checks')
names=('measurement_components.py','runner.py','check_stdlib.py','prepare_source_manifest.py','README.md','STDLIB_REVIEW.json')
files=[artifact(HERE/name) for name in names]
manifest={'schema':'corrected-t6-component-source-preparation.v1',
    'status':'components_prepared_not_executable_not_registered','created_utc':datetime.now(timezone.utc).isoformat(),
    'files':files,'frozen_sources':frozen,'stdlib_check_count':30,
    'implemented':['native inference-mode formal cached GPU encoder','native CLIP image-evidence wall path',
        'one-time 11+10 text prototypes','raw image to CPU FP32 query descriptor',
        'actual measured raw latency samples and resident-inclusive memory baseline/peak',
        'whole-model and observed direct-owner parameters; Formal expected active set checked',
        'honestly labelled Conv2d/Linear module MACs (partial)',
        'explicit current CUDA-device equality and required resident-model object identities'],
    'not_implemented':['immutable experiment registration and prior process/release/GPU-exclusive gates',
        'verified final-checkpoint and offline CLIP snapshot loading in isolated correct environment',
        'case/sample/cache/transform binding and immutable successful/failure output persistence',
        'full-query/gallery metric equivalence, all required dataset/view/checkpoint rows',
        'image-to-ranked-results, single/all-query ranking and gallery-scale timing',
        'T1/external baseline efficiency implementations and complete T6 aggregation'],
    'fixed_candidate_protocol':{'encoding_warmup':20,'encoding_timed_repetitions':100,
        'probability_parity':'exact elementwise equality after original float16 cache quantization and original float32 validation; no renormalization or tolerance relaxation',
        'parity_scope':'selected query only, not full-dataset online equivalence',
        'clip_model':'openai/clip-vit-base-patch32','clip_revision':'3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268',
        'clip_precision':'native fp16 autocast; original output float16 then validator float32',
        'clip_residency':'full CLIP model including text tower retained after prototype setup',
        'total_FLOPs_available':False},
    'review_status':'30 deterministic/AST/mock checks passed; parent static review findings on device and resident identity addressed; independent full-run acceptance pending',
    'scientific_imports':[],'real_model_loaded':False,'checkpoint_loaded':False,'GPU_executed':False,
    'experiment_registered':False,'active_release_created':False,'real_efficiency_results_created':False,
    'manuscript_result':False,'full_t6_complete':False}
blocked={'torch','numpy','PIL','scipy','matplotlib','cv2','timm','transformers','pptx'}
if any(x.split('.')[0] in blocked for x in sys.modules):raise RuntimeError('Scientific module imported during source seal')
target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_manifest':artifact(target),'status':manifest['status'],'check_count':30},ensure_ascii=True))
