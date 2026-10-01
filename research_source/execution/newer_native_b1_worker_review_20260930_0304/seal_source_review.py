"""Seal AI-agent source review from bytes/AST only; never import producer code."""
from pathlib import Path
from datetime import datetime, timezone
import ast, difflib, hashlib, json

R=Path(__file__).resolve().parent; E=R.parent
W=E/'external_efficiency_preparation/newer_native_b1_worker_v1'
def pin(p):
    p=Path(p); raw=p.read_bytes()
    return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def readj(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(name,value):
    p=R/name
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
    return pin(p)
manifest=readj(W/'SOURCE_MANIFEST.json')
assert pin(W/'SOURCE_MANIFEST.json')['sha256']=='9f5e40ed7ddd3f35ce48247d37dcb00923f9dae6955b2c89d96261c296460bb3'
for row in manifest['files']+manifest['original_source_references']+[manifest['prior_B1_root_adoption']]:
    assert pin(row['path'])==row,row['path']
assert manifest['current_source']==pin(W/'reference_worker.py')
static=readj(R/'STATIC_BINDING_REVIEW.json')
assert static['source']==manifest['current_source']
blocks=readj(W/'ORIGINAL_CALL_BLOCKS.json')
block_checks=[]
for b in blocks['blocks']:
    p=Path(b['source']['path']);assert pin(p)==b['source']
    text=p.read_bytes().decode('utf-8-sig')
    node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==b['function'])
    snippet=''.join(text.splitlines(True)[node.lineno-1:node.end_lineno])
    assert b['start_line']==node.lineno and b['end_line']==node.end_lineno
    assert snippet==b['exact_source_block'] and hashlib.sha256(snippet.encode()).hexdigest()==b['block_utf8_sha256']
    block_checks.append({'method':b['method'],'function':b['function'],'source':b['source'],
                         'start_line':node.lineno,'end_line':node.end_lineno,'exact_block_matches':True})
assert len(block_checks)==6
for row in blocks['runtime_prefix_metadata']:
    assert pin(row['prepared']['path'])==row['prepared']
    p=readj(row['prepared']['path'])
    assert row['runtime_prefix']==p['runtime']['prefix'] and row['python']==p['python']
old=(W/'PRE_ROOT_REVIEW_reference_worker.py.txt').read_text(encoding='utf-8')
new=(W/'reference_worker.py').read_text(encoding='utf-8')
expected=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='PRE_ROOT_REVIEW_reference_worker.py.txt',tofile='reference_worker.py'))
assert (W/'ROOT_REVIEW_REVISION.patch').read_text(encoding='utf-8')==expected
expected=''.join(difflib.unified_diff([],new.splitlines(True),fromfile='/dev/null',tofile='reference_worker.py'))
assert (W/'FULL_NEW_SOURCE.patch').read_text(encoding='utf-8')==expected
initial=readj(W/'NEW_STDLIB_CHECKS.json'); delta=readj(W/'ROOT_REVISION_STDLIB_CHECKS.json')
assert initial['passed'] and len(initial['checks'])==29 and initial['source']==pin(W/'PRE_ROOT_REVIEW_reference_worker.py.txt') | {'path':str(W/'reference_worker.py')}
assert delta['passed'] and len(delta['checks'])==5 and delta['source']==pin(W/'reference_worker.py')

sections=[
 {'topic':'Execution remains closed for all ordinary caller arguments',
  'judgment':'PASS for source-only boundary',
  'evidence':'All five public/private original-import/scientific entries begin with the unconditional _closed_execution_admission raise. The module CLI also raises. No boolean, dict, permit, class, path, parent receipt or successful candidate can return from that gate. Direct access to the dormant scientific function does not bypass it.',
  'lines':'54-55, 180-181, 191-193, 207-209, 327-336'},
 {'topic':'Missing parent, predecessor, release, resource and lock integration',
  'judgment':'Explicitly unimplemented; execution is NOT approved',
  'evidence':'MISSING_ADMISSION and README name immutable launch/request, current boot-bound release, actual predecessor exits, resource admission, retained shared GPU byte lock, separate launcher/interpreter identities/handles, pre-science acknowledgement, both actual exits and closed streams. No body path manufactures these from worker self-report. This version deliberately cannot run after valid-looking caller input; a new reviewed controller/version is required.'},
 {'topic':'Old gates and original source preservation',
  'judgment':'PASS',
  'evidence':'All 13 pre-read old source/contract bindings remain unchanged, including old B1 and ranking public rejection. Original CAMP/DAC encoder byte identities and complete encode_seed ASTs are recorded independently. No old source or manuscript was edited.'},
 {'topic':'Original prepared seal precedes B1 derivation',
  'judgment':'PASS by static data/control-flow review',
  'evidence':'The body first invokes the original completed-input binder; that binder calls original read_prepared/verify_seal before returning. request_from_completed rebinds before forming its derivative. The body then independently checks the saved original seal and original protocol.verify_seal(prepared) before calling adopted derive_b1_prepared. The later original read_prepared again reads the unmodified saved file. No derived object is passed to read_prepared or verify_seal.'},
 {'topic':'Unique in-memory batch16 to batch1 difference',
  'judgment':'PASS after root revision',
  'evidence':'Canonical reverse comparison now distinguishes JSON int/bool/float changes outside batch_size. Both batch values require exact int type. The original file descriptor/canonical hash and derived canonical hash remain separate. The derived copied payload_sha256 is retained only as explicitly invalid historical metadata; the envelope does not claim to reseal a new scientific protocol. Exact rebuilt canonical request bytes plus LF are required.'},
 {'topic':'Original scientific call and strict loading',
  'judgment':'PASS for static interface; unexecuted',
  'evidence':'The only encode call is package.evaluator.encode_seed(derived, inputs.seed_binding(rebuilt[seed]), rebuilt[selected_rows], native, log). It uses the original loaded module, not extracted/recompiled encoder code or a native-operations measurement loader. The original loaders retain CAMP395 learned pos_scale and DAC402 classifier heads/DSA, complete/end-state equality, strict=True/assign=True/weights_only=True/mmap=True. The existing pinned binder source_evidence path-alias adapter is inherited; no new scientific/loader/save monkeypatch is introduced.'},
 {'topic':'Actual prepared runtime fields and native processing',
  'judgment':'PASS for static compatibility; runtime not probed',
  'evidence':'Both actual small prepared manifests contain runtime.prefix and python at the paths used by the body. The two original runtime_snapshot definitions return that prefix plus executable/version/distributions/interpreter SHA. Their metadata subprocess uses importlib.metadata and does not import scientific packages. The worker compares the whole snapshot and thread environment before the original encoder; it does not establish current resource admission. Original encoder retains OpenCV BGR-to-RGB, original validation transform, FP16 CUDA forward/F.normalize, FP32 CPU 1024 descriptors, finite/norm checks and no_network scope.'},
 {'topic':'Fresh native/output directories and four-artifact contract',
  'judgment':'PASS for static interface',
  'evidence':'Native destination is a new one-level b1_reference_runs child inside the corresponding original evaluation root, matching original local_output/save confinement; control output is a distinct fresh worker/runs child with the same run name. No save/path guard is rewritten. Four actual native directory entries must exactly equal descriptors.npy, image_content_sha256.jsonl, strict_complete_final_load.json, runtime_actual.json. Their descriptors feed the unmodified adopted candidate checker, including selected content/order, method/seed/state counts/checkpoint SHAs, runtime fields and bounded normalized NPY checks. No gallery or ranking operation is added.'},
 {'topic':'DAC snapshot lifetime',
  'judgment':'PASS for static scope',
  'evidence':'The original completed binder already opens its own snapshot scope. The worker adds original snapshot_scope around original read_prepared, original encoder and artifact checking, calls unchanged_inputs before and after encoding, and separately rechecks inputs/request/source bindings. The review explicitly inspected contract_snapshots.py: scope exit resets the context and is not itself a byte-revalidation guarantee.'},
 {'topic':'Logging, failure and execution claims',
  'judgment':'PASS with documented runtime limits',
  'evidence':'encode.log is opened exclusively, flushed/fsynced and closed before candidate artifacts are bound. Candidate/consistency/return_intent JSON is exclusive and flushed. Return intent explicitly denies actual process-exit observation, closed parent streams, independent execution, measurement, fresh gallery, online accuracy and T6/manuscript results. On body exception, partial native bytes remain and only sizes are listed; no partial descriptor hashing, delete, retry or process termination occurs. Failure logging may itself fail and is not an unconditional durable-report guarantee; only a future external parent can capture actual exit and stream closure. No such behavior was run here.'},
 {'topic':'Bounded control reading',
  'judgment':'PASS after root revision',
  'evidence':'The final helper rejects wrong/oversized actual stat before opening; reads at most declared size plus one; checks identity/size/mtime before-after, length and SHA, then rejects duplicate/nonfinite JSON. The first source only bounded the declared descriptor and could hash an oversized actual file; the preserved final diff fixes that path.'},
 {'topic':'Producer validation evidence and scope',
  'judgment':'Read and bound, not rerun or inflated',
  'evidence':'29 synthetic pure-data/AST/new closed-gate controls belong to the preserved first source 5b888a1e. Five affected checks belong to final eed9b25b and cover canonical int/bool/float changes and bounded actual-size reads. This is not a 34-case final full-suite rerun or runtime-body proof. Both checker scripts were read statically; this independent reviewer never imported/called the worker, original binder, original encoder, controls or scientific packages.'},
]
report={
 'schema':'independent-native-b1-worker-source-review.v1',
 'utc':datetime.now(timezone.utc).isoformat(),
 'reviewer':'Independent AI agent reviewing tool-returned source text and raw-byte/AST inspection; no external human reviewer',
 'decision':'PASS as closed source preparation only; NOT execution approval',
 'source_review_passed':True,'execution_approved':False,'runtime_body_executed_or_validated':False,
 'unresolved_source_findings':[],
 'scope':'Entire new reference_worker.py, complete first-to-final two-function diff, README/interface map/sealer/checker sources, old B1 contract and relevant complete original read_prepared/encode_seed/strict-loader/snapshot implementations. Source-only future-body compatibility review is distinct from working lifecycle integration or actual scientific validation.',
 'current_source':manifest['current_source'],'producer_manifest':pin(W/'SOURCE_MANIFEST.json'),
 'producer_files_bound':manifest['files'],
 'independent_static_report':pin(R/'STATIC_BINDING_REVIEW.json'),
 'initial_contract_checklist':pin(R/'INPUT_CHECKLIST.json'),
 'independent_complete_amendment':pin(R/'INDEPENDENT_FINAL_AMENDMENT.patch'),
 'exact_original_source_blocks_verified':block_checks,
 'review':sections,
 'resolved_root_findings':[
   {'finding':'Ordinary dict equality accepts non-batch int/bool/float semantic changes in the pure envelope.', 'resolution':'canonical(reverse)==canonical(prepared); two synthetic negative cases reported on final source.'},
   {'finding':'Declared-size limit alone does not bound actual control content hashing.', 'resolution':'Actual stat and byte limit checked before open; bounded read and before-after identity checks; three affected checks reported.'}],
 'remaining_execution_obligations':['Implement and separately review exact immutable controller/worker protocol and current boot-bound release.', 'Establish completed predecessors and separately observed actual exits.', 'Establish current resource admission and acquire/retain the shared GPU byte lock.', 'Observe fresh launcher/interpreter identities and creation ticks/commands/parentage with retained OS handles; acknowledge before science.', 'Observe both actual exits and close streams before lifecycle sealing.', 'Validate actual native invocation under the admitted environment. Fresh full-gallery re-encoding/parity and full-dataset online accuracy remain separate work.'],
 'reviewer_actions':{'producer_or_old_module_imports':False,'worker_or_checker_execution':False,'scientific_imports_or_assets':False,'old_suite_rerun':False,'COM_or_process_control':False,'manuscript_state_plan_release_or_automation_edits':False,'only_writes_under':str(R)},
 'interpretation':'The source contains an unreachable original-encoder invocation path and explicit missing integration. Closing those gaps requires a new reviewed source/controller version; this report is not a permission token, runnable-worker validation or new result.'}
save('SOURCE_REVIEW.json',report)
md='''# Independent AI-agent static review

PASS as closed source preparation only. Execution is not approved, and the scientific body has not been executed or runtime-validated.

The final worker is 17414 bytes, SHA256 eed9b25b1204edbcf5172ea2fb24e272b7ff39103f98448e554a3dae779b7f46. All five public/private import/scientific entries begin with unconditional rejection. Caller objects or candidate output cannot admit execution; old public refusal gates and original source bytes remain unchanged.

The entire new source and complete final amendment were read. Static review confirms the original completed-input/seal route, the unique batch16-to1 in-memory derivative, unchanged original encoder/strict-loader interface, actual prepared runtime.prefix fields, original-root output confinement, four-artifact candidate format, and DAC snapshot scope with explicit before/after revalidation. Both root findings were resolved: canonical comparison preserves JSON types, and actual control size is bounded before content reads.

The dormant invocation path has been inspected beyond its closed gate. This is still not an integrated runnable worker: actual predecessor exits, current release/resources, the shared GPU lock and externally observed fresh launcher/interpreter lifecycle remain missing. Worker return intent and candidate consistency do not prove process exit, fresh galleries, online accuracy, T6 or a manuscript result. Failure logging is best effort and requires future independent parent exit capture.

Producer reports 29 synthetic checks on the preserved first source plus five affected checks on final source. They were read and bound, not rerun. Independent work used only source text, small saved metadata, hashes and AST parsing; no producer/original/scientific module was imported or executed, no scientific asset opened, and no prior suite repeated. This review was performed by an AI agent, with no external human reviewer.

SOURCE_REVIEW.json records scope, findings, exact source bindings and remaining execution obligations. DELIVERY.json binds the review artifacts.
'''
with (R/'REVIEW.md').open('x',encoding='utf-8',newline='\n') as f:f.write(md)
delivery={'schema':'independent-native-b1-worker-review-delivery.v1','utc':datetime.now(timezone.utc).isoformat(),
 'source_review_passed':True,'execution_approved':False,
 'report':pin(R/'SOURCE_REVIEW.json'),'source':manifest['current_source'],
 'producer_manifest':pin(W/'SOURCE_MANIFEST.json'),
 'review_artifacts':[pin(R/n) for n in ['REVIEW.md','INPUT_CHECKLIST.json','STATIC_BINDING_REVIEW.json','INDEPENDENT_FINAL_AMENDMENT.patch','inspect_source_static.py','seal_source_review.py']]}
save('DELIVERY.json',delivery)
print(json.dumps({'report':pin(R/'SOURCE_REVIEW.json'),'delivery':pin(R/'DELIVERY.json'),'execution_approved':False},ensure_ascii=True))
