"""Save a bounded source-only predecessor contract note; call no candidates."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = Path(__file__).resolve().parent
P = EX / 'external_efficiency_preparation'
CAP = 256 * 1024
bindings = []
texts = {}

def read_small(path):
    path = Path(path)
    size = path.stat().st_size
    if not 0 < size <= CAP:
        raise ValueError('Source-only note bounded input: ' + str(path))
    raw = path.read_bytes()
    if len(raw) != size:
        raise ValueError('Input size changed: ' + str(path))
    item = {'path': str(path), 'bytes': size, 'sha256': hashlib.sha256(raw).hexdigest()}
    bindings.append(item)
    texts[str(path)] = raw.decode('utf-8-sig')
    return item

def excerpt(path, start, end):
    lines = texts[str(path)].splitlines()
    return {'path': str(path), 'start_line': start, 'end_line': end,
            'lines': [{'line': n, 'text': lines[n - 1]} for n in range(start, end + 1)]}

paths = {
    'next_scope': EX / 'b1_integrated_controller_scope_20260930_1343/NEXT_INTEGRATION_SCOPE.json',
    'resource_addendum': EX / 'b1_integrated_controller_scope_20260930_1343/RESOURCE_RELEASE_SCOPE_ADDENDUM.json',
    'pipeline': EX / 'supervise_pipeline.py',
    'extensions': EX / 'supervise_extensions.py',
    'latest': EX / 'supervise_latest_baselines_path_compat_v1.py',
    'independent': EX / 'supervise_independent_comparisons_path_compat_v1.py',
    'wrapper': EX / 'run_controller_with_state_retry_v2.py',
    'primary': EX / 'continue_formal_matrix_path_compat_v1.py',
    'corrected': P / 'corrected_driver_v3/contract.py',
    'dac': EX / 'dac_training_control_v2/dac2_gates.py',
    'b1': P / 'newer_native_b1_contract_v1/b1_contract.py',
    'loader': P / 'newer_native_loader_v1/source_bindings.py',
    'guardian': P / 'newer_native_b1_guardian_v1/guardian_v3.py',
    'guardian_addendum': P / 'newer_native_b1_guardian_v1/SOURCE_REVIEW_ADDENDUM_V3.json',
    'training_root': EX / 'completion_audits_20260928/ROOT_FIT_42_ADOPTION_20260928.json',
    'primary_state': EX / 'status.json',
}
for key, path in paths.items():
    read_small(path)
read_small(Path(__file__))
state = json.loads(texts[str(paths['primary_state'])])
training_root = json.loads(texts[str(paths['training_root'])])
guardian_addendum = json.loads(texts[str(paths['guardian_addendum'])])

references = [
    {'id': 'wrapper_roles', 'meaning': 'The actual state-I/O v2 wrapper targets these five registered controllers; its declared changes are writer retries only.',
     'excerpts': [excerpt(paths['wrapper'], 14, 20), excerpt(paths['wrapper'], 34, 35)]},
    {'id': 'primary_completion_writer', 'meaning': 'The primary writes completed before its own Python process exits. Child event return codes are different from this controller own exit.',
     'excerpts': [excerpt(paths['primary'], 192, 203)]},
    {'id': 'original_pipeline_primary_gate', 'meaning': 'Original primary-to-pipeline gate checks completed and no still-alive controller, not a saved primary held DWORD0.',
     'excerpts': [excerpt(paths['pipeline'], 75, 80), excerpt(paths['pipeline'], 89, 93), excerpt(paths['pipeline'], 101, 107)]},
    {'id': 'original_successor_gates', 'meaning': 'Each successor checks successful saved job records plus no alive predecessor/nested owner and exact plan. These are operational owner boundaries, not independent historical exit receipts.',
     'excerpts': [excerpt(paths['extensions'], 103, 111), excerpt(paths['latest'], 108, 120),
                  excerpt(paths['independent'], 108, 129)]},
    {'id': 'corrected_future_driver_gate', 'meaning': 'exited() returns True on no current PID, or on creation after recorded finish. Five-state predecessor() checks saved child events/jobs. No top-level primary own exit receipt is demanded here; this source is not original stage7 and cannot replace T6.',
     'excerpts': [excerpt(paths['corrected'], 31, 40), excerpt(paths['corrected'], 134, 147),
                  excerpt(paths['corrected'], 277, 299)]},
    {'id': 'dac_five_layer_operational_gate', 'meaning': 'DAC serial_gate requires all five states/registered jobs and rejects existing nested failed return codes. exited() checks current non-live/reuse; it does not require a missing top-level primary held exit field to be created.',
     'excerpts': [excerpt(paths['dac'], 117, 140), excerpt(paths['dac'], 169, 200)]},
    {'id': 'dac_current_child_handles', 'meaning': 'DAC ProcessObservation reads its actual captured worker DWORD. That prospective own-child requirement is not historical proof for the primary.',
     'excerpts': [excerpt(paths['dac'], 33, 50)]},
    {'id': 'accepted_training_scope', 'meaning': 'Training adoption expressly accepts its evidence with no independent training dual-handle exit proof. This limitation remains accepted and does not invalidate42 fits.',
     'excerpts': [excerpt(paths['training_root'], 235, 247)]},
    {'id': 'existing_b1_source_boundary', 'meaning': 'B1 loader says future actual predecessor exits/release/resources/lock are required; contract says these are unimplemented and all public gates reject. There is no implemented inherited B1 primary-unknown waiver.',
     'excerpts': [excerpt(paths['loader'], 1, 5), excerpt(paths['b1'], 28, 34), excerpt(paths['b1'], 295, 304)]},
    {'id': 'guardian_proposed_adjudication', 'meaning': 'The new closed guardian proposal expects separately adopted role-scoped adjudication, not completed+absence relabelled exit0. required_actual_exits is an original-contract requirement list, but empty-list shape is not authorization to waive an obligation.',
     'excerpts': [excerpt(paths['guardian'], 309, 326)]},
]

report = {
    'schema': 'predecessor-exit-contract-research-note.v1',
    'utc': datetime.now(timezone.utc).isoformat(),
    'method': 'Independent AI bounded local byte/source-line reading and saved field analysis. No human review, candidate import/call, parser/API/process control, scientific execution, or old-suite run.',
    'handoff_read': {'path': str(EX / 'HANDOFF.md'), 'scope': 'Latest16:12 working-draft/bridge record and15:17:27.200118UTC late partial-review record were actually read in tool4d8fb5; no whole journal fresh hash or mutation.'},
    'finding': {
        'original_operational_contract_requires_primary_top_level_independent_DWORD0': False,
        'original_operational_contract_has_completed_and_nonlive_owner_route': True,
        'that_route_proves_historical_primary_exit0': False,
        'current_B1_inherited_executable_adjudication_or_waiver_exists_in_read_sources': False,
        'new_narrow_predecessor_policy_and_root_adjudication_required_before_B1': True,
        'conclusion': 'Existing original queue/DAC/corrected-driver source supports a narrow historical requirement finding: primary own independently captured exit0 was not an explicit input of those operational gates. That can support a later role-specific not-required-under-original-operational-scope decision, while retaining primary own exit unknown. It does not itself satisfy the later B1 actual-exit/authority interface. Define and independently review a new explicit predecessor policy plus actual root adjudication; do not manufacture an exit receipt, replay science, modify old state/plan/adoption, or issue a release from this note.'
    },
    'three_distinct_scopes': {
        'scientific_adoption': '42fit/official42run231task remain accepted within their own adopted evidence limits. Original root explicitly records primary exit unobserved and training/interpreter handle limitations. Newer proposal does not retroactively invalidate scientific completion.',
        'old_queue_operation': 'Completed jobs/events and current absence/non-live or valid post-finish PID reuse were operational serialization inputs. Operational no-owner evidence is not success DWORD or independent launcher/interpreter exit proof; old PID checks are not recommended as new live identity machinery.',
        'new_B1_proposal': 'Source-only B1 and guardian/bridge retain FIRST unconditional rejection and incomplete authority interfaces. Distinct role-scoped predecessor adjudication is proposed but has not been adopted or implemented as an executable historical exception.'
    },
    'saved_current_primary_fields': {
        'status': state.get('status'), 'stage': state.get('stage'),
        'controller_pid_historical_only': state.get('controller_pid'),
        'started_utc': state.get('started_utc'), 'finished_utc': state.get('finished_utc'),
        'top_level_exit_code_present': 'exit_code' in state,
        'top_level_exit_code': state.get('exit_code'),
        'active_present': 'active' in state,
        'saved_event_count': len(state.get('events', [])),
        'saved_event_exit_values': sorted({str(x.get('exit_code')) for x in state.get('events', [])}),
        'interpretation': 'Saved24 event return codes concern that launch segment. They do not encode the controller own exit, all42 scientific fits, or fresh current process identity.'
    },
    'training_root_fields': {
        'adopted': training_root.get('adopted'),
        'completed_fit_count': training_root.get('completed_fit_count'),
        'accepted_evaluations_by_this_train_adoption': training_root.get('accepted_evaluations_by_this_train_adoption'),
        'independently_held_training_exit_handles': training_root.get('independently_held_training_exit_handles'),
        'interpreter_exit_code_observed': training_root.get('interpreter_exit_code_observed'),
        'exit_evidence_basis': training_root.get('exit_evidence_basis')
    },
    'official_root_limited_text_read': {
        'path': str(EX / 'evaluation_audits_20260929/ROOT_OFFICIAL42_AND_PIPELINE2_ADOPTION_20260929.json'),
        'bytes_from_stat': 677924,
        'sha256_inherited_from_HANDOFF_not_new_hash': '3b2bb1629f5b769fcd956c08068fa8ab2c947c9b36898a4bec2742e21110c17e',
        'read_lines': '6160–6185 in actual tool9276c6; relevant fields6170–6172',
        'primary_exit_code_observed': False,
        'independent_interpreter_exit_codes_observed': False,
        'old_process_evidence_literal': 'Original parent Popen completed exit0 plus later absence or proved newer numeric-PID reuse; no original dual-handle/interpreter exit proof',
        'scope': 'Selected saved root fields read, not all1142 attachments, old weights, arrays, or a renewed official-result validation.'
    },
    'guardian_status_read_from_closed_addendum': {
        'source_adopted': guardian_addendum['source_adopted'],
        'execution_released': guardian_addendum['execution_released'],
        'runnable_guardian_complete': guardian_addendum['runnable_guardian_complete'],
        'all_effect_entries_FIRST_closed': guardian_addendum['all_effect_entries_FIRST_closed'],
        'missing_interfaces': guardian_addendum['material_interfaces_still_missing']
    },
    'minimal_future_review_path': [
        'Write a new source-only per-role predecessor requirement policy, quoting original status/spec/plan/source/adoption and explicitly distinguishing child saved return codes, current no-owner evidence and separately retained historical exit records. Preserve all original files.',
        'For primary only, submit the documented absence of an original top-level independent DWORD input for a limited root adjudication: scientific completion retained, own exit unknown, no-owner observational evidence separate, historical independent exit not fabricated. Whether this may meet a new B1 historical requirement must be explicitly decided in the new policy, not inferred from a boolean or empty required_actual_exits list.',
        'For each later actually executed layer, capture the required controller/launcher/interpreter exits and closed logs under its actual reviewed recovery/execution contract. Do not apply a historical-primary exception to new actors or uncompleted jobs.',
        'After originalT6 and all other original five-layer/extraDAC obligations really complete and are adopted, bind the reviewed policy and each actual role adjudication into a separately reviewed B1 authority/plan/IPC path. Keep initial resource/release/live retained locks and current native/observer requirements independent.'
    ],
    'still_missing': [
        'No primary historical independently captured own exit has been supplied, and it remains unknown.',
        'OriginalT6 remains unmeasured; extension4, author20, independent9fit42eval and extraDAC3fit30eval completion/adoption/required exit records are not established by this note.',
        'No adopted executable B1 historical predecessor policy/adjudication root or compatible complete IPC/quiet collector/external guardian observer/native-venv topology is supplied.',
        'No current OS/GPU/memory measurement, emptyGPU/26GiB admission, retained shared locks, fresh release, six CompletedInputs/request/nonce/spec/bootstrap or scientific outputs are supplied.'
    ],
    'exact_source_references': references,
    'input_bindings': bindings,
    'unique_input_binding_count': len(bindings),
    'actual_read_tool_chunks': ['4d8fb5', '1263d4', 'f14676', 'e22d3a', '161cbc', '8be48b', '9276c6', '0bd9c5', 'ee64c6', '859932'],
    'read_tool_nonzero_scope': 'Tool9276c6 returned1 because a final rg searched a nonexisting dac_training_control_v2/serial_release.py path. Actual correct dac2_gates.py was then located and read in ee64c6/859932. This was a filename search miss, not candidate/API/science failure. Source reads in9276c6 completed.',
    'performed': {
        'only_local_bounded_source_and_saved_field_read': True,
        'new_note_files_written': True,
        'candidate_or_science_import_or_call': False,
        'API_process_COM_GPU_or_memory_query': False,
        'old_tests_or_suites': False,
        'weight_NPZ_cache_image_old_archive_read_or_hash': False,
        'scientific_completion_revalidated': False,
        'source_state_plan_root_HANDOFF_mutation': False,
        'shared_lock_action': False,
        'release_intent_attempt_created': False,
        'execution_adjudication_adopted': False,
        'B1_or_SCI_execution_authorized': False,
        'notification_sent': False
    }
}

md = f'''# Primary predecessor exit: narrow contract note

Actual local note time: {report['utc']}. Independent AI source/byte reading only; no candidate, API, science, old suite, release or HANDOFF action.

The original queue and DAC five-layer operational contracts do **not** require a stored independently held DWORD0 for the primary controller itself. They require successful saved jobs/events and no still-live predecessor owner (or proved numeric PID reuse). This provides a basis for a later limited contract adjudication, while primary own exit remains **unknown**. It is not historical exit0 evidence.

- `supervise_pipeline.py:75–80,89–93`: primary completed; prevent transition if controller remains alive.
- `corrected_driver_v3/contract.py:134–147,277–299`: no current PID or creation after saved finish satisfies its operational `exited`; primary events must be completed with saved0. This later source cannot replace originalT6.
- `dac_training_control_v2/dac2_gates.py:117–140,169–200`: all five completed states/registered jobs, no nested saved failures and no live original owners; no missing primary top-level held-exit field is demanded. Its `ProcessObservation:33–50` concerns captured prospective children.
- `ROOT_FIT_42_ADOPTION_20260928.json:235–247` retains training adoption despite explicitly absent independent training/interpreter handles. Official root `:6170–6172` records primary exit unobserved. Accepted42fit/official42run231task are unchanged.
- `newer_native_loader_v1/source_bindings.py:1–5` and `newer_native_b1_contract_v1/b1_contract.py:28–34,295–304` leave actual predecessor exit/release/lock admission unimplemented and public gates closed.
- Unadopted `guardian_v3.py:309–326` proposes separately adopted `b1-predecessor-adjudication.v1`. An empty `required_actual_exits` list is not permission to waive an actual requirement.

There is no executable inherited B1 exception/adjudication in the read sources. The minimum next path is a separately reviewed role-scoped predecessor policy and root adjudication binding the real old source/spec/plan/status/scientific adoption. It may explicitly decide that primary historical independent own exit was not required under the original operational scope, while keeping that exit unknown and no-owner observation separate. This decision must be made in the new B1 policy; this note does not approve it. New actually executed actors must still supply their applicable retained exit/closed-log evidence.

OriginalT6, later layers and extraDAC must first really complete with their applicable acceptance/exit evidence. B1 still lacks adopted authority/IPC/quiet collector/external observer/native topology, current emptyGPU/26GiB admission, retained locks, release and six complete real inputs. No old state, plan, adoption or scientific result is changed; no replay/exit0 fabrication is proposed.

The JSON contains exact absolute paths, quoted source lines and {len(bindings)} necessary small-file byte bindings. Official root SHA is inherited from HANDOFF, not rehashed; only its selected saved scope fields were read. Full bibliography, scientific data, checkpoints and old archives were not reviewed.
'''

def save_new(path, raw):
    if len(raw) > CAP:
        raise ValueError('Output too large before CreateNew')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

result = []
result.append(save_new(HERE / 'PREDECESSOR_EXIT_CONTRACT_NOTE.json', (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')))
result.append(save_new(HERE / 'PREDECESSOR_EXIT_CONTRACT_NOTE.md', md.encode('utf-8')))
print(json.dumps({'outputs': result, 'input_bindings': len(bindings), 'scope': 'ordinary stdlib note save only, no execution authority'}, ensure_ascii=False))
