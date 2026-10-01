"""Bounded root adoption of a static remaining-work inventory, not execution."""
from pathlib import Path
import datetime, hashlib, json

W=Path(__file__).absolute().parent
EX=W.parent
checks=0
bound={}
def ck(ok,why):
    global checks
    checks+=1
    if not ok: raise AssertionError(why)
def binding(p):
    p=Path(p); ck(p.suffix.lower() not in ('.pt','.npz','.npy','.jpg','.jpeg'),'Small source only')
    data=p.read_bytes(); ck(len(data)<2_000_000,'Small file')
    return dict(path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
def admit(row):
    actual=binding(row['path']); ck(all(actual[k]==row[k] for k in ('bytes','sha256')),'Exact SHA/size')
    bound[str(Path(row['path'])).casefold()]=actual
def read(p,sha=None):
    b=binding(p)
    if sha:ck(b['sha256']==sha,'Pinned input')
    admit(b);return json.loads(Path(p).read_text(encoding='utf-8-sig'))

target=W/'ROOT_DEPENDENCY_REVIEW_ADOPTION.json'
ck(not target.exists(),'Exclusive report')
r=read(W/'REVIEW.json','bbd7485dcf7d4ad28013bd6c46c402a27ebff2e6c972e40030c7a23d2f5daf67')
for row in r['source_and_small_file_bindings']+[r['review_markdown'],r['sealing_source']]:admit(row)
ck(len(r['source_and_small_file_bindings'])==17 and r['scientific_execution'] is False,'Bounded17 source review')
plan=read(EX/'extension_plan.json');state=read(EX/'extension_status.json')
ck(state['status']==r['extension']['status']=='preceding_pipeline_interrupted','Current extension stopped')
ck([(x['id'],x['command']) for x in plan['jobs']]==[(x['id'],x['command']) for x in r['extension']['jobs']],'Exact ordered scientific commands')
ck(all(x['status']=='pending' for x in state['jobs']),'All four pending')
pkg=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch')
m=read(pkg/'experiments/transactions_t2_heldout_matrix.json')
ck(m['registered_run_count']==len(m['runs'])==24 and m['epochs']==80,'24 additional80-epoch LOHO fits')
ck({(x['heldout_altitude_m'],x['variant'],x['seed']) for x in m['runs']}=={(h,v,s) for h in ('150','200','250','300') for v in ('visual','full') for s in (1,2,3)},'Full LOHO factorial')
ck(r['loho']['all_scope_tasks']==24*4*2==192 and r['loho']['heldout_tasks']==24*2==48 and r['loho']['seen_height_tasks']==24*3*2==144,'Registered task arithmetic')
ck(r['loho']['included_in_primary_42_fits'] is False and r['loho']['actual_completion_accepted_here'] is False,'No completed-fit inflation')
for p in r['configured_path_observations']:ck(Path(p['path']).exists()==p['exists']==False,'Configured outputs still absent')
t5=read(EX/'pipeline_post_robustness_audit_20260929_1448/a1/query/transactions_t5_selective_calibration.json','033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc')
ck(len(t5['native_rows'])==66 and all(len(x['calibration']['reliability_bins'])==15 for x in t5['native_rows']),'66 saved records/990 fixed bins, no recomputation')
ck(r['visio']['matching_file_count']==0 and r['visio']['completion_claim'] is False,'Bounded reported filename inventory, not a fresh whole-computer search')
admit(binding(Path(__file__)))
report=dict(schema='root-remaining-delivery-static-adoption.v1',time=datetime.datetime.now().astimezone().isoformat(),accepted_with_stated_limits=True,
    independent_review=binding(W/'REVIEW.json'),source=binding(Path(__file__)),checks=checks,unique_files=len(bound),bindings=list(bound.values()),
    root_read_scope='Complete independent JSON, Markdown and sealer; original extension predecessor, full LOHO registry, LOHO train/evaluation task/output blocks, real-visualization selection and gate, and margin-reliability helper blocks. Sources read only, not imported or executed.',
    scope={'additional_LOHO_fits_pending':24,'all_height_tasks_pending':192,'heldout_tasks':48,'seen_height_tasks':144,'saved_T5_reliability_records_available':66,'fixed_bins_available':990},
    no_scientific_execution=True,no_queue_release_or_state_change=True,
    limits=['24 LOHO fits are additional to completed42. Pending output absence is not a new scientific failure.',
            'Original real visualization remains gated CUDA inference and Grad-CAM; no synthetic features or heatmaps accepted.',
            'Visio absence is the independent bounded outputs filename inventory only, not a whole-computer/archive/application assessment.',
            'Reliability/ECE is a possible next small-table graphical delivery, not completed graphics or new inference. Empty-bin nulls and fixed-score, non-posterior interpretation must persist.',
            'No repeat of old scientific/control audits, no new GPU/native/recovery/lock operation, and no change to five-layer serial dependencies.'])
with target.open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'report':binding(target),'checks':checks},ensure_ascii=False))
