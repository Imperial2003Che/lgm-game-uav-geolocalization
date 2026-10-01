"""Adopt inactive proposal preparation only, without running its publisher/checker."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os
HERE = Path(__file__).resolve().parent
EX = HERE.parent
P = EX / 'b1_predecessor_role_policy_20260930_1730'
R = EX / 'b1_predecessor_role_policy_review_20260930_1730'
CAP = 262144
bindings = []
raw = {}
def bind(path):
    path = Path(path)
    before = path.stat()
    assert 0 <= before.st_size <= CAP, str(path)
    with path.open('rb') as f: data = f.read(CAP + 1)
    after = path.stat()
    assert len(data) == before.st_size and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    record = dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    bindings.append(record); raw[str(path)] = data
    return record
items = [
 (P / 'ROLE_POLICY.json', 18011, 'a8f038875bd27e2bd393f6c30ae2cf198b5a0d78b690f9aace149ba576538609'),
 (P / 'POLICY_PREPARATION_REPORT.json', 46827, '8874d99df0b57e0c005a1a4d743f8e256e5819d83351c36ceae98a546281df05'),
 (P / 'README.md', 3622, '8e968650cb4e94ebc358be5baca94fcdbc09ddde058a4d3847d0e6ebe6a658a4'),
 (P / 'prepare_role_policy.py', 22727, 'fce3fff50d554397a38d4a71dfd7057753baccb26f6088b54e547b3cedaa6216'),
 (P / 'ACTUAL_POLICY_PUBLICATION_TOOL_RETURN.json', 2174, 'f80fee88f0005a1628c30ac90343ef1e7c9d817151e68243fa6d2324335dfc1a'),
 (R / 'ROLE_POLICY_REVIEW.json', 12911, '5f3852a3812b3b78706b80ab61f21a66412eb8324c6b031ad5744621d47fe1c0'),
 (R / 'ROLE_POLICY_REVIEW.md', 5105, 'fba04a91b45d9a7b1f92a61f51c485c5a434d00daa25efa39183e83fe6005e7b'),
 (R / 'CHECK_RESULT.json', 4226, 'aa25cbe58200523170323d8b149d33df0fb0823d5552880ebc8d37b40ca97b2e'),
 (R / 'ACTUAL_REVIEW_TOOL_RETURN.json', 9655, '54cee830bb97caa37a3aa1c0e0d49393bfe3095cbfeeaf8c279c371d59cd15a2'),
 (R / 'check_role_policy_v1.py', 9403, '7248b3a481ca1e64d68bc54fe342466f4a1ab45eda53308ac0bbb67cb4490394'),
 (EX / 'heartbeat_observation_20260930_1730/ROOT_OBSERVATION_SEAL.json', 13881, 'b6ee1af9cec28db29e767dde925e3f24e6314990e978dc54a1d4b8286e0d7561')]
for path, size, sha in items:
    record = bind(path)
    assert (record['bytes'], record['sha256']) == (size, sha), str(path)
source = bind(__file__)
policy = json.loads(raw[str(P / 'ROLE_POLICY.json')])
review = json.loads(raw[str(R / 'ROLE_POLICY_REVIEW.json')])
result = json.loads(raw[str(R / 'CHECK_RESULT.json')])
assert policy['schema'] == 'b1-predecessor-role-exit-policy-proposal.v1'
assert policy['not_schema'] == 'b1-predecessor-adjudication.v1'
assert [r['role'] for r in policy['roles']] == ['primary', 'pipeline7', 'extension4', 'authors20', 'independent9fit42eval', 'extra_DAC3fit30eval']
assert all(r['required_actual_exits_current'] is None and r['adjudication_current'] is None and r['execution_ready_current'] is False for r in policy['roles'])
assert all(policy[k] is False for k in ('policy_adopted', 'execution_adjudication_adopted', 'release_allowed', 'B1_scientific_execution_authorized'))
assert review['source_policy_preparation_adoption_recommended'] is True and review['operative_policy_adoption_recommended_now'] is False
assert result['all_checks_pass'] is True and result['check_count'] == 20
assert result['new_input_byte_bindings'] == bindings[:5]
assert policy['roles'][0]['historical_primary_independent_own_exit'] == 'unknown'
report = {
 'schema': 'root-inactive-b1-role-policy-preparation-adoption.v1',
 'utc': datetime.now(timezone.utc).isoformat(), 'source': source,
 'proposal_preparation_adopted': True, 'operative_policy_adopted': False,
 'execution_adjudication_adopted': False, 'historical_primary_exit_waived': False,
 'primary_own_independent_exit': 'unknown', 'current_role_exit_lists': [None] * 6,
 'old_scientific_adoption_retained': True, 'original_DAC_operational_scope_changed': False,
 'policy': bindings[0], 'independent_review': bindings[5], 'bindings': bindings,
 'method': {
  'root': 'AI full policy/README/publisher/actual publication receipt and independent report/checker text reading; preparation report selected four saved quote groups/inputs/performed scope. Bounded saved-byte and result association only.',
  'independent': 'One actual269ac8 exit0/.1798772s; only five new input bytes/SHA, one publisher AST and20 necessary local static assertions. Not scientific tests or human review.',
  'root_did_not_replay_independent20_or_old17_257_or_bridge21_162_deltas': True,
  'old_source_quote_bytes_freshly_verified_by_root_in_this_adoption': False,
  'inherited_research_scope': 'Prior accepted research-note root a2842ce7 and note c820362a retained. Six author-referenced sources serve distinct contexts; this does not renew their full runtime/scientific validation.',
  'physical_new_local_file_bindings': len(bindings)
 },
 'decisions': [
  'Reviewable inactive proposal is adopted as preparation. Its top schema, six null lists and descriptive future fields are not a consumable guardian adjudication.',
  'Primary historical independent own-exit obligation is still a future explicit root adjudication with exact original source/spec/plan/status mapping. No current empty list, waiver, exit0, or no-owner-to-exit conversion.',
  'Any first6 historical gap needs its own explicit original-contract disposition; no automatic primary exception or replay of accepted science.',
  'Five pending roles remain incomplete; extraDAC registration/status/plan mapping stays unknown. New actual actor evidence must follow applicable reviewed original/recovery/execution contracts.',
  'This prospective B1 policy does not alter existing DAC three-seed operational permission or demand invented missing fields in old receipts. Honest compatibility must be separately reviewed.',
  'OriginalT6 and ordered five layers plus extraDAC, real science adoption, initial/retained locks, fresh resource/release/native/ACK/exit/closure/quiet/outer-observer evidence remain owed.'
 ],
 'current_saved_observation': bindings[10],
 'observation_scope': 'Saved26rows gatefalse, same boot, ordinary existingVisio. This file adoption is not new OS/GPU admission and does not measure available commit.',
 'candidate_or_publisher_or_checker_executed': False,
 'science_API_native_COM_or_resource_change': False,
 'release_intent_attempt_shared_lock_or_live_state_action': False,
 'weights_NPZ_cache_images_old_big_ZIP_work': False,
 'B1_or_T6_scientific_execution_released': False,
 'new_scientific_result_or_figure_or_manuscript': False,
 'all_task_deliveries_complete': False, 'automation_retained': True
}
target = HERE / 'ROOT_ROLE_POLICY_PREPARATION_ADOPTION.json'
body = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
assert len(body) <= CAP
with target.open('xb') as f:
    f.write(body); f.flush(); os.fsync(f.fileno())
print(json.dumps(dict(path=str(target), bytes=len(body), sha256=hashlib.sha256(body).hexdigest()), ensure_ascii=False))
