"""One new bounded root byte/metadata adoption. Never imports a candidate/checker."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = EX / 'b1_outer_observer_delivery_20260930_1834'
AUTHOR = EX / 'external_efficiency_preparation' / 'newer_native_b1_outer_observer_v1'
REVIEW = EX / 'newer_native_b1_outer_observer_review_20260930_1833'
OBS = EX / 'heartbeat_observation_20260930_1834'
MAX = 1024 * 1024
EXPECTED = {
    'outer_observer.py': (47752, '8dea1234eea9364480dcde0108b3263d38a2cbb6b842bcda775df085a0211aaa'),
    'README.md': (6803, 'f95b8b535896b6f220146c5d0f25ace67ce4b96661d1ec82670ac9f878060ffd'),
    'publish_source_metadata.py': (12052, '6b49a098a28db1379f0196fd40e64bbb281ddc4a1e35c8d9ab89c56b086400e0'),
    'SOURCE_MANIFEST.json': (3140, '33a9e89826828e9a53e706411c84c29dd5d3a2683870bbfb5ecd0920cf45c5a0'),
    'INTERFACE_CONTRACT.json': (4930, 'ea70d6097acec03f79949814e59dbdd4b54f3f0442a24165fdbd723f0c0b3d3c'),
    'AUTHOR_DELIVERY.json': (7808, 'e9eeca613fac5ea9226a164a2dca500441461abf10d285b6f76c91fafb8a0c4c'),
    'ACTUAL_AUTHOR_PUBLICATION_TOOL_RETURN.json': (2641, 'ed8604c6d7d8de691aa2b807fee9628594c7f78f015f2ef0aaa1814664e5332a'),
}
REVIEW_EXPECTED = {
    'OUTER_OBSERVER_REVIEW.json': (14859, 'c0e7091e82e7f39500b6fe140800634e955a8f92f785faa45eebc29767dd062b'),
    'OUTER_OBSERVER_REVIEW.md': (5287, '095d0392518a5506e7e6c9950018303c7260d0abccce503ee6055ed24adcd8e8'),
    'check_outer_observer_static_v1.py': (11458, '11eb942663bd3a73a55d23338e08c620a9ef003cabd1cae3e35774a18ba3194e'),
    'CHECK_RESULT.json': (8251, '7cf796fc5edc6657098fe1e672b59352ae9891e34213ced3e58f8cf284788585'),
    'ACTUAL_REVIEW_TOOL_RETURN.json': (9368, '9bcbbc879c014976be1a9792177d5f8701b6aa783e3808de0f59402f8c37fb52'),
    'SOURCE_READ_TOOL_RETURNS.json': (144234, 'aab3d2cef2899532da6dabfbc96431452c3f1e0896669e823119edfe0926a7ca'),
    'WAITING_FOR_AUTHOR_SEAL.md': (4420, 'd40f332d1fe522de473ddb29e94dafc5b1a740442eb5c2921a95ce1fd9099280'),
}
bindings, raws, labels = {}, {}, []

def check(label, value):
    if not value:
        raise ValueError(label)
    labels.append(label)

def read_new(path, expected=None):
    if str(path) in bindings:
        return raws[str(path)], bindings[str(path)]
    before = path.stat()
    if not 0 <= before.st_size <= MAX:
        raise ValueError('Metadata input exceeds one-MiB cap: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(before.st_size + 1)
        after = os.fstat(stream.fileno())
    if len(raw) != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('Metadata bytes changed during read: ' + str(path))
    rec = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected is not None:
        check('fixed_bytes_' + path.name, (rec['bytes'], rec['sha256']) == expected)
    bindings[str(path)], raws[str(path)] = rec, raw
    return raw, rec

def parse(raw):
    def pairs(items):
        data = {}
        for key, value in items:
            if key in data:
                raise ValueError('Duplicate metadata key')
            data[key] = value
        return data
    def reject(value):
        raise ValueError('Nonfinite metadata')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=reject)

def new_json(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX:
        raise ValueError('New report exceeds explicit one-MiB output cap')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def main():
    output = HERE / 'ROOT_CLOSED_OUTER_SOURCE_PREPARATION_ADOPTION.json'
    if output.exists():
        raise ValueError('Any existing root report refuses replay')
    for name, expected in EXPECTED.items():
        read_new(AUTHOR / name, expected)
    for name, expected in REVIEW_EXPECTED.items():
        read_new(REVIEW / name, expected)
    delivery_raw, delivery_rec = read_new(REVIEW / 'DELIVERY.json')
    seal_raw, seal_rec = read_new(REVIEW / 'ACTUAL_REVIEW_ARTIFACT_BINDING_TOOL_RETURN.json')
    for name in ('ACTUAL_ROOT_SOURCE_READ_TOOLS.json', 'ACTUAL_ROOT_INDEPENDENT_READ_TOOLS.json', 'ACTUAL_ROOT_REVIEW_SEALER_READ_TOOL.json'):
        read_new(HERE / name)
    observation_raw, observation_rec = read_new(OBS / 'ROOT_OBSERVATION_SEAL.json',
        (21851, '9d3fbfb3452c7d42d6a2959a65d65f187f935e4fdd268a9b36afc8798ff49a08'))
    read_new(OBS / 'ACTUAL_OBSERVATION_TOOLS.json')
    _, source_rec = read_new(Path(__file__).resolve())
    manifest = parse(raws[str(AUTHOR / 'SOURCE_MANIFEST.json')])
    author = parse(raws[str(AUTHOR / 'AUTHOR_DELIVERY.json')])
    review = parse(raws[str(REVIEW / 'OUTER_OBSERVER_REVIEW.json')])
    result = parse(raws[str(REVIEW / 'CHECK_RESULT.json')])
    receipt = parse(raws[str(REVIEW / 'ACTUAL_REVIEW_TOOL_RETURN.json')])
    delivery, seal, observation = parse(delivery_raw), parse(seal_raw), parse(observation_raw)
    actual_source = bindings[str(AUTHOR / 'outer_observer.py')]
    actual_author_inputs = [bindings[str(AUTHOR / name)] for name in EXPECTED]
    check('author_manifest_exact_selected_source', manifest['new_source_bindings'][0] == actual_source)
    check('independent_selected_and_seven_exact_inputs',
        review['selected_source'] == actual_source and review['new_input_bindings'] == result['input_bindings'] == actual_author_inputs)
    check('independent_actual_checker_receipt_binding',
        receipt['actual_return']['chunk_id'] == review['actual_reviewer_checker']['chunk_id'] == delivery['actual_checker_tool'] == 'd339b7'
        and receipt['actual_return']['exit_code'] == review['actual_reviewer_checker']['exit_code'] == delivery['actual_checker_exit'] == 0
        and parse(receipt['actual_return']['output'].encode('utf-8'))['result'] == bindings[str(REVIEW / 'CHECK_RESULT.json')])
    check('independent_delivery_exact_seven_artifacts',
        delivery['reviewer_artifact_bindings'] == parse(seal['actual_return']['output'].encode('utf-8'))
        and all(bindings[item['path']] == item for item in delivery['reviewer_artifact_bindings'])
        and seal['actual_return']['chunk_id'] == delivery['artifact_binding_tool'] == 'a7a76d'
        and seal['actual_return']['exit_code'] == delivery['artifact_binding_exit'] == 0)
    check('independent_scope_preparation_only', review['static_source_scope_complete'] is True
        and review['recommendation']['closed_source_preparation_adoption_recommended'] is True
        and delivery['closed_source_preparation_adoption_recommended'] is True
        and all(review[key] is False for key in ('candidate_imported_or_called', 'runtime_topology_validated',
            'immutable_physical_provenance_established', 'finite_historical_lineage_resolved',
            'actual_guardian_or_observer_exit_proven', 'scientific_measurement_admitted', 'B1_or_T6_complete')))
    check('author_source_only', author['execution_released'] is False and author['candidate_imported_or_called'] is False
        and author['guardian_runtime_derivative_or_producers_prepared_here'] is False)
    report = {
        'schema': 'root-b1-external-outer-observer-closed-source-preparation-adoption.v1',
        'utc': datetime.now(timezone.utc).isoformat(),
        'root_source': source_rec, 'selected_source': actual_source,
        'source_manifest': bindings[str(AUTHOR / 'SOURCE_MANIFEST.json')],
        'author_report': bindings[str(AUTHOR / 'AUTHOR_DELIVERY.json')],
        'independent_report': bindings[str(REVIEW / 'OUTER_OBSERVER_REVIEW.json')],
        'independent_delivery': delivery_rec, 'independent_artifact_seal_receipt': seal_rec,
        'fresh_readonly_observation_seal': observation_rec,
        'new_small_bindings': list(bindings.values()),
        'new_input_bindings_count': len(bindings),
        'local_metadata_binding_check_count': len(labels), 'local_metadata_binding_labels': labels,
        'root_method': 'AI full-text source/README/interface/publisher, independent checker/result/review and exact artifact-sealer command/receipt review; one bounded new byte/metadata adoption only. No candidate or checker is imported or replayed.',
        'root_read_scope_limits': 'Independent 144234B source-read transcript is byte-bound here; its outputs are not all separately re-emitted by root. Full independent substantive report/checker and complete selected source were root-read. Source reading/tool exit0 is not human or runtime/held exit review.',
        'root_full_source_read_tools': ['b99958', 'cc8e06', '9c4b97'],
        'root_full_explanations_and_method_tools': ['bf67b7', 'ae3da5', '0c4354', 'a0da9c', 'cabc7d', 'c63aff'],
        'author_publication_scope': {'actual_tool': 'b106a0', 'actual_exit_code': 0,
            'AST_FIRST_effect_functions': 17, 'None_pins': 4, 'science_runtime_or_control': False},
        'independent_checker_scope': {'actual_tool': 'd339b7', 'actual_exit_code': 0,
            'new_small_inputs': 7, 'new_source_AST': 1, 'local_relations': 17,
            'relation_breakdown': '7 fixed bytes +3 metadata +7 dormant IPC/exit/closure relations; not author 17 FIRST.',
            'author_FIRST_None_suite_replayed': False, 'candidate_or_API_execution': False},
        'independent_sealer_scope': 'a7a76d: seven new reviewer artifacts only, separate from checker.',
        'existing_small_author_bindings_inherited_not_rehashed_by_root': manifest['necessary_original_small_bindings'],
        'source_preparation_adopted': True,
        'approved_scope': 'Closed external guardian observer/actor source proposal only; no executable scientific integration.',
        'execution_released': False, 'runnable_topology_or_handshake_validated': False,
        'operative_six_role_policy_or_adjudication_adopted': False,
        'future_guardian_runtime_derivative_installed': False,
        'immutable_physical_or_finite_quiet_producers_adopted': False,
        'actual_guardian_launcher_or_interpreter_exit_proven': False,
        'actual_observer_own_exit_proven': False,
        'shared_byte_lock_ownership_or_release_authorized': False,
        'B1_scientific_artifact_admitted': False, 'T6_complete': False,
        'source_or_old_scientific_gate_opened': False,
        'remaining_limits': [
            'All 17 effect bodies/public/mode entries retain FIRST rejection, module CLI closed, all four execution/runtime/resource/finite-producer pins None. This adoption does not install pins or create runtime spec/bootstrap/release/intent/attempt.',
            'Original guardian_v3 has no READY/ACK bootstrap; separate reviewed future derivative and original native topology remain missing. Old guardian, quiet/role/bridge/worker/ranking sources remain sealed/refusing.',
            'Proposed acyclic common inputs/root/later release/final spec/READY-ACK associations are not operative scientific issuer authority or immutable physical evidence.',
            'Finite quiet consumer binds raw inventory/count/held query exit/lineage and sample dispositions; it does not reconstruct every row/null/time/filter or historical lineage. Current quiet candidate cannot emit its aggregate or clear finite unknowns by adding a pin.',
            'Actor independently recollects resource evidence; it does not reread both resource records carried in ACK. Complete independent ACK admission-record provenance has not passed.',
            'Dormant external retained launcher/interpreter live identities/full command/parent birth/ACK and actual DWORD-first/Popen-separate/closed-stream ordering have not been run. Return intent/reference close/current absence never supplies own actual exit0.',
            'No recursive observer layer prepared. An already external real parent still owes observer actual own exit. Held evidence retention is not shared OS byte-lock ownership; hard interruption/residual children require a fresh incident.',
            'Canonical byte consistency and cooperative CreateNew/flush/read sharing do not prove arbitrary writer history or all physical provenance.',
            'Scientific originals, fresh full gallery/ranking/parity/full image-to-ranking timing/onlineCLIP, original T6 and later scientific adoption remain incomplete.'
        ],
        'observation_scope': {
            'capture_time_utc': '2026-09-30T17:32:46.8231640Z',
            'same_boot_ticks': observation['boot_ticks'],
            'same_original_state_and_closed_logs': True,
            'original_scientific_owner_identified': False,
            'primary_actual_independent_own_exit': 'unknown',
            'narrow_CIM_is_empty': False,
            'GPU_query_rows': 26, 'exclusive_gate': False, 'T6_output_absent': True,
            'available_commit_measured': False,
            'observation_is_future_resource_or_execution_admission': False,
            'existing_user_Visio_attached_closed_or_modified': False
        },
        'new_scientific_runs_figures_manuscript_or_Overleaf': 0,
        'old_weights_NPZ_cache_images_large_ZIP_or_passed_suites_revisited': False
    }
    rec = new_json(output, report)
    print(json.dumps({'root_adoption': rec, 'new_small_bindings': len(bindings),
        'local_metadata_binding_checks': len(labels), 'source_preparation_adopted': True,
        'execution_released': False, 'B1_scientific_artifact_admitted': False, 'T6_complete': False},
        ensure_ascii=True, indent=2))

if __name__ == '__main__':
    main()

