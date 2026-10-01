"""One closed-source root adoption, without importing candidate or rerunning checks."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, os
HERE = Path(__file__).resolve().parent
EX = HERE.parent
Q = EX / 'external_efficiency_preparation/newer_native_b1_quiet_collector_v1'
R = EX / 'newer_native_b1_quiet_collector_review_20260930_1730'
CAP = 262144
records, saved = {}, {}
def bind(path, expected=None):
    path = Path(path); key = str(path)
    if key not in records:
        before = path.stat(); assert 0 <= before.st_size <= CAP, key
        with path.open('rb') as f:
            data = f.read(before.st_size + 1); after = os.fstat(f.fileno())
        assert len(data) == before.st_size and (before.st_size,before.st_mtime_ns,before.st_ino) == (after.st_size,after.st_mtime_ns,after.st_ino)
        saved[key] = data
        records[key] = dict(path=key,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    if expected is not None: assert records[key] == expected, key
    return records[key]
def load(path):
    bind(path)
    return json.loads(saved[str(Path(path))])
report = load(R / 'QUIET_COLLECTOR_REVIEW.json')
bind(R / 'QUIET_COLLECTOR_REVIEW.json',dict(path=str(R/'QUIET_COLLECTOR_REVIEW.json'),bytes=14843,sha256='e4872cc9e95e2158b4e0e90f3c9e40232a06befca6329df915ec974977f3f989'))
for edge in report['input_bindings']:
    assert Path(edge['path']).parent == Q
    bind(edge['path'],edge)
artifact_receipt = load(R / 'ACTUAL_REVIEW_ARTIFACT_BINDING_TOOL_RETURN.json')
assert artifact_receipt['actual_return']['chunk_id'] == '7c578c' and artifact_receipt['actual_return']['exit_code'] == 0
edges = json.loads(artifact_receipt['actual_return']['output'])
assert len(edges) == 6
for edge in edges:
    assert Path(edge['path']).parent == R
    bind(edge['path'],edge)
result = load(R / 'CHECK_RESULT.json')
actual = load(R / 'ACTUAL_REVIEW_TOOL_RETURN.json')
manifest = load(Q / 'SOURCE_MANIFEST.json')
interface = load(Q / 'INTERFACE_CONTRACT.json')
author = load(Q / 'AUTHOR_DELIVERY.json')
assert report['recommendation']['closed_source_preparation_adoption_recommended'] is True
assert report['recommendation']['operative_collector_adoption_recommended'] is False
assert report['recommendation']['execution_adjudication_adoption_recommended'] is False
assert result['counts']['local_relation_assertions'] == 23 and len(result['passed_static_relation_labels']) == 23
assert result['counts']['new_small_input_files_read_and_hashed_once'] == 7
assert result['input_bindings'] == report['input_bindings']
assert actual['actual_return']['chunk_id'] == 'c60a17' and actual['actual_return']['exit_code'] == 0
actual_output = json.loads(actual['actual_return']['output'])
assert actual_output['result'] == records[str(R / 'CHECK_RESULT.json')]
assert actual_output['counts'] == result['counts']
assert report['selected_source'] == records[str(Q / 'quiet_collector.py')]
assert interface['selected_collector_source'] == report['selected_source']
assert interface['current_reviewed_pins'] == dict(REVIEWED_QUIET_EXECUTION_AUTHORITY_PIN=None,REVIEWED_FINITE_SLOT_LINEAGE_METHOD_PIN=None,REVIEWED_GUARDIAN_INTEGRATION_SOURCE_PIN=None)
assert manifest['execution_released'] is False and author['runtime_query_validated'] is False
assert report['guardian_integration_installed'] is False and report['finite_actual_slot_history_resolved'] is False
obs = bind(EX / 'heartbeat_observation_20260930_1730/ROOT_OBSERVATION_SEAL.json',dict(path=str(EX/'heartbeat_observation_20260930_1730/ROOT_OBSERVATION_SEAL.json'),bytes=13881,sha256='b6ee1af9cec28db29e767dde925e3f24e6314990e978dc54a1d4b8286e0d7561'))
policy = bind(HERE / 'ROOT_ROLE_POLICY_PREPARATION_ADOPTION.json',dict(path=str(HERE/'ROOT_ROLE_POLICY_PREPARATION_ADOPTION.json'),bytes=7789,sha256='ed61f0c15a206a47450e0ab5b21699f5f3c752cd0f4bde430ae68c234384488e'))
source = bind(__file__)
adoption = {
 'schema':'root-closed-b1-quiet-source-preparation-adoption.v1',
 'utc':datetime.now(timezone.utc).isoformat(),'source':source,
 'closed_source_preparation_adopted':True,
 'operative_collector_adopted':False,'execution_adjudication_adopted':False,
 'runnable_collector_or_runtime_query_topology_validated':False,
 'finite_actual_slot_history_resolved':False,'guardian_integration_installed':False,
 'guardian_unobserved_descendants_cleared':False,
 'shared_lock_owned_or_release_authorized':False,
 'B1_or_T6_scientific_execution_released':False,
 'scientific_measurement_or_new_figure_or_manuscript':False,
 'selected_source':report['selected_source'],
 'independent_review':records[str(R/'QUIET_COLLECTOR_REVIEW.json')],
 'new_local_bindings':list(records.values()),'new_local_binding_count':len(records),
 'methods':{
  'root':'AI complete38,671B source read in three actual tool slices aef1fe/faae20/d7acce; full interface/README/author manifest/delivery/sealer/actual receipt, independent checker/result/report/MD and two actual return files read. SOURCE_READ_TOOL_RETURNS.json byte-bound only, not claimed full root transcript reading.',
  'author':'One3b0ea2 exit0/.1803495s source/metadata sealer;11 effect-FIRST/CLI and3None AST checks. Candidate and APIs were not run.',
  'independent':'Onec60a17 exit0/.2028972s;7 bounded new file byte/SHA reads,4metadataJSON+1savedauthorstdout,1quiet AST,1embeddedquery SHA and23 local static relation assertions.7c578c seals6 reviewer artifacts only. No mirror replay of author11FIRST/3None.',
  'root_did_not_rerun_author_or_independent_checks_or_import_candidate':True,
  'old_guardian_helper_bridge_and_science':'Only necessary original guardian blocks previously root text-read; helper/bridge/root metadata bindings inherited from already adopted sources. No new old-source hashes, scientific weights/data or old SCI/control suites.'
 },
 'interpretation_limits':result['important_limits']+[
  'All effect/public/private/CLI entries remain unconditional FIRST rejects and three execution pins None. No startup runner, live inventory, READY/ACK, native probe or actual quiet observation from this source exists.',
  'Dormant parent live confirmations precede ACK; consumer only schema/nonce/rawrequestSHA/PID/read-only, not independent full held birth/image/parent or exact keyset/canonical. Do not claim immutable physical authority or complete canonical IPC.',
  'New finite-slot evidence selects raw component events by path; existing helper does not emit the new aggregate schema. Full producer/declaration/raw IPC/live-observer provenance must be supplied by a new reviewed integration.',
  'The actual slot/query spawn-window residual stays true, no unobserved_descendants=false. Captured real exits and current reachable-parent observations cannot supply an uncaptured short-lived historical exit; no arbitrary unrelated past-process proof is demanded.',
  'Null actual commands remain unknown, numeric reuse is not old actor/exit, and original guardian still rejects the missing collector. The inactive six-role proposal is not a new execution adjudication or historical exit waiver.',
  'Fresh physical boot/resources/release/locks/native actor topology/outer held observer/closed logs/immutable scientific gate/full gallery ranking parity timing onlineCLIP and originalT6/five layers/extraDAC remain required.'
 ],
 'inactive_role_policy_preparation':policy,'saved_current_observation':obs,
 'saved_observation_is_not_new_OS_GPU_or_memory_admission':True,
 'science_API_native_COM_or_live_state_action_by_root':False,
 'all_task_deliveries_complete':False,'automation_retained':True
}
target = HERE / 'ROOT_QUIET_SOURCE_PREPARATION_ADOPTION.json'
body = (json.dumps(adoption,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
assert len(body) <= CAP
with target.open('xb') as f: f.write(body); f.flush(); os.fsync(f.fileno())
print(json.dumps(dict(path=str(target),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),new_local_binding_count=len(records)),ensure_ascii=False))
