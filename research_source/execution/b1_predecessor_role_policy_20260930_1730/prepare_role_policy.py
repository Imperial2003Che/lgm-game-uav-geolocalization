"""Publish only a bounded, inactive role-policy proposal from saved source research.

This ordinary metadata publisher does not import a candidate, capture a process,
generate b1-predecessor-adjudication.v1, or grant execution authority.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = Path(__file__).resolve().parent
PREP = EX / 'external_efficiency_preparation'
CAP = 256 * 1024
bindings = []

def bounded(path):
    size = path.stat().st_size
    if not 0 < size <= CAP:
        raise ValueError('Only named small sources/reports are permitted')
    with path.open('rb') as stream:
        raw = stream.read(size + 1)
    if len(raw) != size:
        raise ValueError('Input size changed')
    descriptor = {'path': str(path), 'bytes': size, 'sha256': hashlib.sha256(raw).hexdigest()}
    bindings.append(descriptor)
    return raw.decode('utf-8-sig'), descriptor

def quote(text, path, start, end):
    lines = text.splitlines()
    return {'path': str(path), 'start_line': start, 'end_line': end,
            'text': '\n'.join(f'{n}:{lines[n-1]}' for n in range(start, end + 1))}

root_path = EX / 'b1_slot_bridge_root_adoption_20260930_1647/ROOT_PREDECESSOR_CONTRACT_RESEARCH_ADOPTION.json'
note_path = EX / 'predecessor_exit_contract_note_20260930_1647/PREDECESSOR_EXIT_CONTRACT_NOTE.json'
guardian_path = PREP / 'newer_native_b1_guardian_v1/guardian_v3.py'
camp_path = EX / 'camp_training_execution_v2/contracts.py'
dac_path = EX / 'dac_training_control_v2/run_dac_stage.py'
root_text, root_record = bounded(root_path)
note_text, note_record = bounded(note_path)
guardian_text, guardian_record = bounded(guardian_path)
camp_text, camp_record = bounded(camp_path)
dac_text, dac_record = bounded(dac_path)
_, publisher_record = bounded(Path(__file__))
root = json.loads(root_text)
note = json.loads(note_text)
if root['note'] != note_record or not root['research_note_adopted'] or root['execution_adjudication_adopted']:
    raise ValueError('Only the exact adopted research note, with no execution adjudication, is usable')

historical_refs = {
    r['id']: r for r in note['exact_source_references']
    if r['id'] in {'original_pipeline_primary_gate', 'original_successor_gates',
                   'corrected_future_driver_gate', 'dac_five_layer_operational_gate',
                   'accepted_training_scope', 'existing_b1_source_boundary'}
}

def role(name, status_file, required_status, order, completion, actor_requirements, extra_missing):
    return {
        'role': name, 'order': order,
        'original_status_path': str(EX / status_file) if status_file is not None else None,
        'required_completed_status': required_status,
        'science_completion_required': completion,
        'actual_new_actor_coverage_required': actor_requirements,
        'exit_generation_rule': 'After real complete/adopted results: enumerate every actual new actor under the separately reviewed lifecycle topology; join each exact held live identity with its actual signaled successful exit and closed-stream/quiet boundary. Use exact immutable descriptors and saved_exit_relation-compatible records only if provenance and complete fields are really present. Do not derive this list from current PID absence, saved job return0, worker intent, or a candidate boolean.',
        'required_actual_exits_current': None,
        'adjudication_current': None,
        'empty_exit_list_allowed_for_this_pending_role': False,
        'scope_complete_current': False,
        'execution_ready_current': False,
        'missing': extra_missing,
    }

roles = [{
    'role': 'primary', 'order': 1,
    'original_status_path': str(EX / 'status.json'),
    'required_completed_status': 'completed',
    'science_completion_required': 'Already accepted42fit=36formal_main+6sensitivity,80epochs, and own official42run231task adoption. Preserve each actual original root and its inherited limits; this policy does not repeat science checks.',
    'historical_primary_independent_own_exit': 'unknown',
    'historical_independent_own_DWORD_was_explicit_original_operational_input': False,
    'root_decision_required': 'A future independently reviewed root may explicitly adjudicate ONLY the historical primary own independent-exit obligation as not required under the original completed-and-nonlive operational contract. It must bind original source/spec/plan/status, adopted scientific scope and separate observed no-owner facts, preserve unknown, and decide compatibility with the new B1 historical requirement. This proposal does not make that decision.',
    'required_actual_exits_current': None,
    'adjudication_current': None,
    'empty_exit_list_currently_published': False,
    'future_empty_list_condition': 'Only a separately adopted primary-specific adjudication that explicitly finds no original-contract actual-held-exit obligation for the covered historical actors may publish an empty list for that precisely bounded historical scope. It cannot waive new primary/resume actors, prove any exit0, or stand in for incomplete scientific completion. If any applicable obligation is found, retain null/pending until real evidence or another explicitly reviewed resolution exists.',
    'actual_new_actor_coverage_required': 'Any future real primary/resume actor, if separately authorized for unfinished work, must have actual external controller/launcher/interpreter identity and retained-handle exits/closed streams. This policy proposes no primary replay or resumed completed science.',
    'scope_complete_current': 'Original scientific adoption retained; future B1 role adjudication not complete.',
    'execution_ready_current': False,
    'missing': ['Explicit limited primary root adjudication and policy adoption',
                'Exact guardian original_spec/original_plan/source_authority mapping for source-defined primary matrix; do not fabricate a historical plan file or substitute this policy as original_plan',
                'Fresh current boot/source/state/no-owner observations from an actual future admission; no snapshot is future permission'],
}]
roles.append(role('pipeline7', 'pipeline_status.json', 'ready_for_extension_preparation', 2,
    'All seven original jobs in original order, including original formal_efficiency_componentT6, plus per-job scientific adoption in its own scope. Existing first6 remain accepted, stage7 has no measurement and must really execute under the adopted T6 recovery contract.',
    ['Actual new T6 recovery guardian and real pipeline controller/launcher, observed externally where required',
     'Original stage7 scientific launcher and actual interpreter, with separate held exits and closed append-log ranges',
     'Every actually captured relevant redirector/descendant required by the reviewed topology; unknown/uncaptured required descendants block'],
    ['OriginalT6 real success/output/adoption', 'Real recovered pipeline completion and all applicable captured exits/log closure',
     'Explicit separate disposition of any first6 historical independent-exit gaps if the new B1 policy requires them; no automatic primary exception, no replay, no fabricated held receipts']))
roles.append(role('extension4', 'extension_status.json', 'registered_extensions_finished_review_pending', 3,
    'All four original extension jobs: real visualizations;24LOHO fits;192heldout/seen tasks;sevenT1fits70eval plus required native profiles. Exact registered order/commands/plan/source and adopted results.',
    ['Real new extension supervisor/controller observed externally',
     'Every new job launcher and actual interpreter, plus relevant captured descendants and scientific profile/train/eval actors within the job'],
    ['Four actual jobs/results/adoption', 'Applicable real new actor exit/closed-log/quiet evidence']))
roles.append(role('authors20', 'latest_baseline_status.json', 'latest_baselines_finished_review_pending', 4,
    'Exactly two registered author-checkpoint evaluation jobs and20official tasks, with actual author-weight rather than independent-training scope. Bind the original latest plan SHA80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e.',
    ['Real new latest-author supervisor/controller observed externally',
     'Both real evaluation launchers/interpreters and all relevant captured descendants'],
    ['Actual20task results/adoption', 'Two successful job records and required actual owner exits/closed logs']))
roles.append(role('independent9fit42eval', 'independent_comparison_status.json', 'independent_comparisons_finished_review_pending', 5,
    'Original independentv2 three jobs: matched-two-view6fits12eval;CAMP3fits;CAMP30eval, plus five native resource prechecks. Matched two-view and CAMP three-seed protocols unchanged; bind original plana5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49.',
    ['Real new independent supervisor/controller observed externally',
     'Every real precheck/profile/fit/evaluation launcher and actual interpreter under the exact reviewed job topology'],
    ['Actual9fits42eval and required profiles/results/adoption', 'Every applicable new actor identity/exit/closed-log/quiet record', 'Actual CAMP CompletedInputs/completion for six-slot B1 input binding']))
roles.append(role('extra_DAC3fit30eval', None, None, 6,
    'Five original layers really complete first; then extraDAC profile1/train1/profile2/train2/profile3/train3 and30independent official evaluations under fixed_three_seed. ExtraDAC is outside the original five-layer plan and is not implied by independentv2 completion.',
    ['Real new registered outer DAC serial supervisor/controller, with its exit externally observed',
     'Each actual native profile/train/evaluation launcher and interpreter under DACcontrol_v2/evaluation_v2',
     'Any actual captured relevant descendant required by the separately reviewed topology'],
    ['Registration and exact state/spec/plan source mapping for the future extraDAC queue', 'Actual3fits30eval/profile results/adoption',
     'Real per-stage launcher/interpreter and outer-owner exit/closed-stream evidence', 'Actual DAC CompletedInputs/completion; prepared alone is insufficient']))

policy = {
    'schema': 'b1-predecessor-role-exit-policy-proposal.v1',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'document_kind': 'inactive policy/source preparation for future independent/root review',
    'not_schema': 'b1-predecessor-adjudication.v1',
    'research_authority': root_record, 'base_note': note_record,
    'research_note_adopted': True, 'policy_adopted': False,
    'execution_adjudication_adopted': False, 'release_allowed': False,
    'B1_scientific_execution_authorized': False,
    'roles': roles,
    'global_exit_record_generation': [
        'Use the actual applicable original/recovery/execution contract to enumerate expected role-labelled actors before launch. The actual topology must be independently reviewed; do not assign historical PIDs to current actors.',
        'For every actually new actor: capture live image/complete command/creation integer ticks/parent relation; retain the actual external OS handles through signaled exits. Capture controller own exit from outside that controller; its aggregate cannot prove its own exit.',
        'Read actual unsigned DWORD and actual exit/creation integer times from the same continuously retained handle. Require actual success0 where the relevant completed job contract requires0. Unknown, absence, forced termination, API failure, source/control fixture success, or parent-onlyPopen0 never becomes interpreter/controller0.',
        'Only after both scientific launcher/interpreter and applicable controller/relevant descendant exits, close actual stdout/stderr and bind the immutable exact final bytes/log ranges; preserve append prefixes and all partial/failed attempts. Require the reviewed post-exit quiet boundary and externally observed outer guardian exit.',
        'Build each required_actual_exits entry from actual immutable record descriptor plus exact captured identity, in fixed reviewed actor order. Deduplicate only the same actually demonstrated actor identity without losing launcher/interpreter role coverage; never invent distinct PIDs or missing short-lived children.',
        'Guardian saved_exit_relation requires identity match, signaled wait_result0, positive matching pid/creation integer times, actual unsignedDWORD0, actual exit integer times and same_retained_handle_pid_creation_verifiedtrue. It is only a saved association check; producer/observer provenance and closures must be independently established by the adjudication root.',
        'Existing old lifecycle receipt schemas are not silently cast into this saved_exit shape. If required full identity/tick/handle fields were not captured, preserve the old actual receipt and the missing-field limitation. Use only an independently reviewed honest compatibility bridge for genuinely equivalent captured evidence; no missing values or handle provenance may be filled.',
        'Until all obligations and actor coverage for a role are satisfied and its science adopted, required_actual_exits remains null/pending in inactive policy data, not empty. A live adjudication must not be generated from these inactive role rows.',
    ],
    'future_root_adjudication_required_fields': {
        'schema': 'b1-predecessor-adjudication.v1',
        'role': 'One exact role in guardian_v3 order',
        'science_adopted': 'True only from actual per-role scoped adoption, not this policy',
        'scope_complete': 'True only after full original role scope really completes',
        'exit_requirement_adjudicated': 'True only from new explicit independent/root policy decision with bound evidence',
        'absence_is_exit_proof': False,
        'status': 'Exact immutable actual status descriptor at final accepted scope',
        'original_spec': 'Exact real registered spec/source-defined contract descriptor; no invented historical file',
        'original_plan': 'Exact real frozen plan descriptor or explicit reviewed source-defined-plan mapping; not this policy',
        'source_authority': 'Exact independently adopted original/scientific/source authority; no caller-selected shortcut',
        'required_actual_exits': 'Actual role-specific list generated only after these policy decisions/evidence; no list is generated now',
    },
    'empty_list_policy': {
        'default': 'Reject for any pending role or new actor obligation',
        'primary_historical_only': 'Potential explicitly reviewed root decision; not approved by this proposal',
        'propagation_to_other_roles': False,
        'unknown_exit_remains': 'unknown, never numeric0',
    },
    'nonbypass_dependencies': [
        'Original five layers in order, then separately extraDAC3fit30eval; originalT6 not replaced by corrected_driver/B1/metadata/control fixtures.',
        'Current boot/source/state/source pins, current complete emptyGPU query and valid integer available_commit_bytes=commit_limit_bytes-committed_bytes>=26GiB at initial/pre-spawn/preACK gates; resource floor is not a runtime kill threshold.',
        'Existing carrier byte locks retained by real owners, all required locks, actual native environment probe under T6 contract, TTL/release evidence and real child exits/closed streams; no source/policy adoption substitutes physical admission.',
        'B1 distinct authority/release/IPC/quiet collector/external observer and actual native-venv topology remain required. T6 seven-field release and B1 old eight-field candidate association do not authorize this new scope.',
        'All original negative results, frozen training/evaluation parameters and historical scientific evidence limits remain. No completed science rerun, application closure, parameter reduction or resource purchase is proposed.',
    ],
    'old_source_and_gate_mutation': False,
    'old_science_adoption_retained': True,
}

source_quotes = [
    quote(guardian_text, guardian_path, 132, 149),
    quote(guardian_text, guardian_path, 309, 326),
    quote(camp_text, camp_path, 80, 106),
    quote(dac_text, dac_path, 268, 282),
]
report = {
    'schema': 'b1-predecessor-role-policy-preparation-report.v1',
    'created_utc': policy['created_utc'],
    'method': 'Independent AI limited saved source/field reading and inactive policy authorship. No human, API, candidate, science, native or old-suite execution. No current physical admission.',
    'latest_handoff_read': 'Actual tool85ef31 read latest16:04UTC journal and new root research adoption; journal is neither hashed nor modified here.',
    'new_saved_inputs_bound': bindings,
    'input_binding_count': len(bindings),
    'inherited_old_source_quotes': historical_refs,
    'old_source_binding_scope': 'Original quote groups/descriptors inherited from the exactly bound adopted note. No repetition of17source checks,257quoted-line checker or root/control/science suites.',
    'new_necessary_source_quotes': source_quotes,
    'roles_proposed': [r['role'] for r in roles],
    'live_required_actual_exits_generated': False,
    'all_six_inactive_role_exit_lists_are_null': True,
    'primary_science_retained_own_exit_unknown': True,
    'pending_roles_get_no_empty_list_waiver': True,
    'scientific_predecessors_complete': False,
    'policy_source_adopted': False,
    'execution_adjudication_adopted': False,
    'execution_runnable_released': False,
    'performed': {'bounded_local_source_read_and_new_metadata_write': True,
        'candidate_import_or_call': False, 'API_CIM_GPU_memory_COM_or_scientific_call': False,
        'old_suite_or17source_checker': False, 'weight_NPZ_cache_image_old_ZIP_read_or_hash': False,
        'original_state_plan_root_gate_pin_HANDOFF_change': False,
        'release_intent_attempt_or_shared_lock_action': False, 'notification': False},
    'actual_read_tool_chunks': ['85ef31', 'af8c43', 'aacfcd'],
    'scope': 'The finite role policy is now reviewable, not an execution adjudication, a live guardian plan or a scientific delivery.',
}

md = '''# Inactive B1 predecessor role policy

This is an AI-authored source/policy proposal for future independent/root review. It creates no `b1-predecessor-adjudication.v1`, actual exit record, release, live plan or permission. All six proposed `required_actual_exits_current` fields are null.

| Exact guardian role | Historical/completion scope | Future exit-list rule |
|---|---|---|
| primary | Accepted42fit and own official adoption retained; primary own held exit remains unknown. Original operational gate did not require that historical top-level input. | Only an explicitly adopted primary-specific root policy may find that covered historical independent own exit was not required. It may then publish the precisely bounded historical list; this proposal publishes no empty list or waiver. New actors cannot use that decision. |
| pipeline7 | First6 accepted; original stage7T6 unmeasured. All7 original jobs must really finish. | Actual new T6/pipeline controller, scientific launcher/interpreter and relevant captured descendants, actual success exits, append-log closure and quiet boundary. Any first6 historical gap needs separate explicit disposition, not the primary exception. |
| extension4 | Four original jobs, including24LOHO fits192tasks andT1sevenfits70eval/profiles. | Every actual new supervisor/job/scientific actor under reviewed topology; no empty waiver for pending work. |
| authors20 | Two author-weight jobs20tasks, exact original latest plan. | Actual supervisor and evaluation launcher/interpreter/required descendants; do not mix independent-training evidence. |
| independent9fit42eval | Three originalv2 jobs9fits42eval and required native prechecks. | All actual supervisor/profile/train/eval actor exit and closed-log evidence; real CAMP completion required. |
| extra_DAC3fit30eval | After all five original layers; separate profile1/train1/profile2/train2/profile3/train3 plus30eval. | Register its exact future state/spec/plan first. Actual outer and each profile/train/eval launcher/interpreter exits, closures and real DAC completion. Prepared is insufficient. |

Final entries must join immutable actual external-observer records with exact live identities retained continuously through true signaled DWORD exits. Guardian `saved_exit_relation` checks saved associations only: it does not establish original capture provenance, complete actor coverage, independent observer ownership or closed logs. A parent Popen0, absence, self intent, CPU control or unknown required actor cannot supply another actor exit0. Older receipt formats cannot gain missing tick/command/handle fields through renaming.

The separate root adjudication must bind real status, original_spec, original_plan and source_authority, and decide `science_adopted`, `scope_complete` and `exit_requirement_adjudicated` from actual adopted evidence. Exact primary source-defined plan mapping and future extraDAC registration remain unresolved; no historical plan file is fabricated. Null stays pending; incomplete pipeline/extension/latest/independent/extraDAC never gets an empty-list waiver.

OriginalT6/five-layer/extraDAC ordering, fresh current boot/source/state, completely emptyGPU and integer26GiB available commit, retained real byte-lock owners, native environment, releases/TTL, ACK/dual-held exits/closed-stream and quiet/external-guardian boundaries remain separate requirements. Current snapshots, adopted policy, retained old science and closed source are not execution authority. No old source/state/plan/root/gate/pin/HANDOFF is changed; all scientific adoption and negative-result limits remain.
'''

def write_new(path, value):
    raw = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if len(raw) > CAP:
        raise ValueError('Output too large before CreateNew')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

outputs = [write_new(HERE / 'ROLE_POLICY.json', policy),
           write_new(HERE / 'POLICY_PREPARATION_REPORT.json', report),
           write_new(HERE / 'README.md', md.encode('utf-8'))]
print(json.dumps({'outputs': outputs, 'input_bindings': len(bindings),
    'scope': 'ordinary stdlib inactive policy metadata publication only; no candidate or adjudication execution'}, ensure_ascii=False))
