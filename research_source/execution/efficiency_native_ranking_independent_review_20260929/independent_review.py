"""Independent bounded source review; stdlib only, no scientific runtime."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EX = HERE.parent
SOURCE = EX / 'external_efficiency_preparation/newer_native_ranking_v1/ranking_bridge.py'
EXPECTED = sys.argv[1]
REPORT = HERE / 'INDEPENDENT_SOURCE_REVIEW.json'

def artifact(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

source = artifact(SOURCE)
assert source['sha256'] == EXPECTED, 'Source not the reviewed frozen candidate'
assert not REPORT.exists(), 'Immutable review report already exists'
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
before_modules = set(sys.modules)
spec = importlib.util.spec_from_file_location('_independent_bounded_native_ranking', SOURCE)
bridge = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bridge
spec.loader.exec_module(bridge)
scientific = ('numpy', 'torch', 'cv2', 'PIL', 'scipy', 'timm', 'torchvision', 'albumentations')
assert not [n for n in sys.modules if n.split('.')[0] in scientific]

class Matrix:
    """Integer arithmetic fixture; not NumPy or FP32/GPU parity evidence."""
    def __init__(self, rows): self.rows = [list(row) for row in rows]
    @property
    def T(self): return Matrix(zip(*self.rows))
    def __matmul__(self, rhs):
        columns = list(zip(*rhs.rows))
        return Matrix([[sum(a*b for a,b in zip(row,col)) for col in columns] for row in self.rows])
    def __neg__(self): return Matrix([[-x for x in row] for row in self.rows])

class SortingFixture:
    @staticmethod
    def argsort(values, *, axis, kind):
        assert axis == 1 and kind == 'stable'
        return [sorted(range(len(row)), key=lambda i: row[i]) for row in values.rows]

checks=[]
def record(name, **details): checks.append(dict(name=name, passed=True, **details))

# Distinct from the author's mocked-flow tests: the production full-sort
# expression computes actual integer dot products against every fixture row.
fixtures = [
    ('all_equal_ties_retain_full_gallery_order', [[1,0]], [[2,i] for i in range(73)], list(range(73))),
    ('positive_zero_negative_scores_keep_all_rows', [[1,2]], [[3,0],[1,1],[0,0],[-2,0],[0,2],[3,0]], [4,0,1,5,2,3]),
    ('late_best_row_not_lost_to_prefix_or_topk', [[1,0]], [[0,0] for _ in range(130)] + [[1,0]], [130]+list(range(130))),
]
for name,query,gallery,expected in fixtures:
    actual=bridge.full_stable_ranking(SortingFixture, Matrix(query), Matrix(gallery))
    assert actual == [expected], (name,actual)
    assert sorted(actual[0]) == list(range(len(gallery)))
    record(name, gallery_count=len(gallery), complete_permutation=True, real_numpy_or_fp32_test=False)

# This public guard must reject before touching a model, descriptor, path or
# output. A hostile sentinel exposes accidental access before that guard.
class Untouchable:
    def __getattribute__(self, name): raise AssertionError('Public blocked entry accessed '+name)
    def __fspath__(self): raise AssertionError('Public blocked entry accessed output path')

try:
    bridge.measure_task_ranking(Untouchable(), 'not-a-real-task', Untouchable(), Untouchable())
except RuntimeError as error:
    public_message=str(error)
    assert 'B=1' in public_message or 'B1' in public_message, public_message
else:
    raise AssertionError('Public measurement entry is executable')
record('public_entry_rejects_before_any_argument_or_runtime_access', rejection=public_message)

dependencies=bridge.verify_dependency_sources()
assert len(dependencies)==6
record('six_existing_native_dependency_bindings_unchanged', count=len(dependencies))

# Review text is a bounded static finding, not a scientific execution claim.
findings=[
    {'id':'public_b1_gate','conclusion':'Public measurement entry is unconditionally blocked pending immutable independently executed original B=1 evidence. Internal implementation is unreleased source preparation, not an admissible timing API.'},
    {'id':'loaded_slot','conclusion':'Internal entry checks the pinned LoadedSlot/native operations files, exact method/seed, strict loaded model object and 395 CAMP / 402 DAC state counts, same seed final checkpoint binding. Existing loader retains complete original strict model loading and learned CAMP pos_scale.'},
    {'id':'gallery','conclusion':'Prepared SHA-bound inventory/tasks select the first query and every gallery index in exact task order. Mapped completed same-seed descriptor artifact is freshly byte-bound and required to have inventory rows x 1024 FP32. No truncated gallery or top-k sorting is used.'},
    {'id':'query_content','conclusion':'Same-seed completed image_content_sha256.jsonl is freshly bound by artifact path/size/hash. Every ledger row must match the full inventory key/order/size with valid SHA256; selected raw image size/SHA must match its original completed encoding before native operations, and ledger/image bindings are rechecked afterward. Actual gallery image bytes are not reread/re-encoded here.'},
    {'id':'helper','conclusion':'Production sort expression is CPU inner product followed by descending stable full argsort, matching both pinned original helpers. One-query original helper checks top-1 and all positive positions, saves NPZ, then original validator recomputes recall/ranks and both official trapezoidal and rank-precision AP. This is one-query validation against a cached complete gallery.'},
    {'id':'timing','conclusion':'Descriptor-to-ranking scope excludes forward/decode/AP; raw-file-to-ranking includes original OpenCV/RGB/384 transform, blocking H2D, original FP16 forward/normalization, CPU FP32 descriptor and complete stable ranking. Existing synchronized-wall timer retains CUDA synchronization overhead and resident model accounting; model/gallery loading and AP bookkeeping remain outside timing.'},
    {'id':'persistence','conclusion':'Exclusive creation saves selected bindings, B1 descriptors, full before/after ranking arrays and one-query original helper evidence. Errors retain available descriptor arrays and failure JSON. No scientific output was produced by this review.'},
    {'id':'limitations','conclusion':'B1 independent executor/provenance, fresh-worker orchestration, release/resource/shared lock checks, full-gallery re-encoding/parity, full-dataset online accuracy and real launcher/interpreter exit proof remain future duties. Cached gallery source and false acceptance/full-T6/manuscript flags must remain explicit.'},
]
inspected=[
    EX/'external_efficiency_preparation/newer_native_ops_v1/native_ops.py',
    EX/'external_efficiency_preparation/newer_native_loader_v1/native_load.py',
    EX/'external_efficiency_preparation/newer_native_loader_v1/source_bindings.py',
    EX/'external_efficiency_preparation/corrected_v1/measurement_components.py',
    EX/'camp_preparation/run_camp_author_evaluation.py',
    EX/'dac_preparation/run_dac_author_evaluation.py',
    EX/'camp_independent_evaluation_v3/run_evaluation.py',
    EX/'dac_independent_evaluation_v2/run_evaluation.py',
]
author_report=EX/'external_efficiency_preparation/newer_native_ranking_v1/CONTROL_REVIEW_BINDING_FINAL.json'
author_data=json.loads(author_report.read_bytes())
assert author_data['source']==source and author_data['status']=='passed' and author_data['test_count']==5
assert artifact(author_data['script']['path'])==author_data['script']
assert artifact(author_data['previous_report']['path'])==author_data['previous_report']
assert artifact(SOURCE)==source
assert not [n for n in sys.modules if n.split('.')[0] in scientific]
result=dict(schema='independent-native-ranking-source-review.v1', started_utc=started,
    finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='passed_for_source_preparation_only',
    source=source, reviewer_script=artifact(__file__), inspected_sources=[artifact(p) for p in inspected],
    independent_controls=checks, findings=findings, blocking_issues=[],
    author_changed_interface_control_report=artifact(author_report), author_report_reviewed_not_rerun=True,
    public_measurement_entry_enabled=False, scientific_imports=[], scientific_execution=False,
    native_workers_or_launchers_executed=False, scientific_completion_claimed=False,
    real_numpy_fp32_or_gpu_parity_verified=False, fresh_gallery_verified=False,
    original_B1_executor_verified=False, scientific_acceptance=False, full_t6_complete=False,
    manuscript_result=False, scope='Single new ranking/timing source interface; old loader/ops suites were not rerun')
with REPORT.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps(artifact(REPORT),ensure_ascii=False))
