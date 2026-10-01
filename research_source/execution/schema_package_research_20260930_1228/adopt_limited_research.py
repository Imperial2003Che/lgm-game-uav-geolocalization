"""Seal new citation/format research only; never execute producer or validate science."""
from pathlib import Path
import base64, csv, datetime as dt, hashlib, io, json, os

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = Path(__file__).resolve().parent
ICLR = EX / 'citation_iclr_open_fields_20260930_1212'
FEAS = EX / 'offline_native_xsd_feasibility_20260930_1212'
OBS = EX / 'heartbeat_observation_20260930_1219'
MSIREVIEW = EX / 'schema_msi_file_table_review_20260930_1255'
INPUTS = []

def read(p, sha=None, cap=256*1024):
    n = p.stat().st_size
    if not 0 <= n <= cap:
        raise ValueError('Named research input bound: '+str(p))
    with p.open('rb') as f:
        b = f.read(cap+1)
    if len(b) != n or len(b) > cap:
        raise ValueError('Actual research input length: '+str(p))
    d = {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
    if sha is not None and d['sha256'] != sha:
        raise ValueError('Exact research input changed: '+str(p))
    INPUTS.append(d)
    return b, d

def obj(p, sha=None, cap=256*1024):
    b, d = read(p, sha, cap)
    return json.loads(b), d

def require(ok, reason):
    if not ok:
        raise ValueError(reason)

fields, fields_d = obj(ICLR/'FIELD_REVIEW.json', '385078fb76529f8121cb3200bb52fc56947142baa69cf9f251cc43bd3de7e3ad')
blocks, blocks_d = obj(ICLR/'LOCAL_SCOPED_BIBTEX_BLOCKS.json', '53a44d93bfd68d06b0c8d75d35e54e7dc846cdcfff248be0c838fa31c88ceec3')
refs, refs_d = read(Path(blocks['current_refs']['path']), '5aa4d85644e26e04f5d2895389d72c2e2cd8d63eeffc59613115f8b527e526e7', 32*1024)
require(refs_d == blocks['current_refs'], 'Current scoped reference descriptor')
for b in blocks['three_blocks']:
    actual = refs[b['start_byte_offset']:b['end_byte_offset_exclusive']]
    require(actual == base64.b64decode(b['raw_block_base64'], validate=True)
            and actual.decode('utf8') == b['raw_block_utf8']
            and len(actual) == b['bytes'] and hashlib.sha256(actual).hexdigest() == b['sha256'],
            'Exact three displayed local blocks')
table_bytes, table_d = read(ICLR/'FIELD_TABLE.csv', '6ec4fce794b83878d4519061c9a50a2634ff7f66ccf2d482f7fb04f0b3fa89f1')
rows = list(csv.DictReader(io.StringIO(table_bytes.decode('utf8-sig'))))
require(len(rows) == fields['scope_field_rows'] == 12 and len(blocks['three_blocks']) == 3, 'New scoped counts')
for r in rows:
    entry = next(e for e in fields['entries'] if e['key'] == r['key'])
    f = entry['current_fields'][r['field']]
    value = f['local_value'] if r['field'] == 'publication_type' else f['local']['normalized_value']
    require(r['actual_local_value'] == value and r['status'] == f['status']
            and r['confirmed_difference'] == 'false' and f['confirmed_difference'] is False,
            'CSV matches new field report')
require(fields['result']['conference_ordinal_gaps_closed'] == 3
        and fields['result']['publisher_role_unknown'] == 3
        and fields['result']['confirmed_field_errors'] == 0
        and fields['result']['all_bibliography_verified'] is False, 'Partial citation conclusions')

feas, feas_d = obj(FEAS/'XSD_FEASIBILITY_REVIEW.json', '542af1d70509ccbe9a2da9f90501e49526381ce7b1cbd9247010c0e397f56cc9')
download, download_d = obj(HERE/'OFFICIAL_SDK_DATA_DOWNLOAD_V3.json', '2bd2a0cc9e277698075adf6e68d4f766bb320ec98b43cc5c67dd9be786879b3e')
extract, extract_d = obj(HERE/'SDK_INERT_PAYLOAD_EXTRACTION.json', '63aec3b764c293fe5479c1c875c4ecef3152f9cc2aac1f835c181ffe12196386')
cab, cab_d = obj(FEAS/'SDK_INNER_CAB_REVIEW.json', 'ec588535780606784ed4bf301f1e01a493cf80a53e57cf25c84e510e5ac516b5')
msi, msi_d = obj(HERE/'SDK_READONLY_FILE_TABLE_v2.json', 'df0fe3f9d594707336cd5fdf5c6f083822fc07a1c412643f4dca5a3760c17f77')
peer, peer_d = obj(MSIREVIEW/'SDK_SAVED_FILE_TABLE_REVIEW.json', '03c79bfb48ab8c69503afc53a37c760b3d4ddce2173846f26638b82734939c27')
source, source_d = read(HERE/'read_sdk_file_table_v2.py', 'f4e48a61dc54911f6aa04e9e08873d4e124437e22fabf5b97613b4585628df27', 16*1024)
require(msi['source'] == source_d and msi['status'] == 'completed' and msi['query_completed'] is True,
        'Actual saved read-only query and executed source')
require(msi['file_row_count'] == len(msi['all_file_rows']) == 236
        and msi['schema_named_rows'] == [] and len(msi['closed_native_database_handles']) == 238
        and msi['database_before'] == msi['database_after']
        and msi['secondary_close_errors'] == [] and msi['post_read_errors'] == [] and msi['primary_error'] is None,
        'Saved MSI scope/counts/closed API results')
require(peer['all_selected_checks_pass'] is True and peer['exact_key_size_pair_matches'] == 236,
        'Independent saved-value reconciliation, not repeat API execution')
require(all(msi[k] is False for k in ('installer_run','action_sequence_or_custom_action_run','Office_COM','downloaded_code_executed','schema_validation')),
        'Data query does not claim installer/schema/science')
chm_extract, chm_extract_d = obj(HERE/'SDK_SINGLE_CHM_DATA_EXTRACTION.json', 'd456c43573525ac4379ea55f3e428f5011c687ffecd5bd7551b376bf51da6a2b')
require(chm_extract['status'] == 'completed' and chm_extract['documentation_data']['bytes'] == 6764354
        and chm_extract['documentation_data']['sha256'] == '19a74be23751db246fdf047d49a187187074113ad9095febd0cb640dba465a4a',
        'New inert documentation data extraction')

# This is a saved limited data result, never a validator/probe/producer invocation.
chm_path = HERE/'chm_directory_attempt_v1'/'SDK_CHM_DIRECTORY_CANDIDATE.json'
chm_failure = HERE/'chm_directory_attempt_v1'/'SDK_CHM_DIRECTORY_FAILURE.json'
require(chm_path.exists() != chm_failure.exists(), 'Exactly one actual CHM directory outcome')
chm, chm_d = obj(chm_path if chm_path.exists() else chm_failure, cap=8*1024*1024)
chm_completed = chm.get('directory_complete') is True and chm.get('result') == 'directory_listing_candidate'
require(chm['schema_validation'] is False and chm['Office_COM'] is False
        and chm['scientific_execution'] is False and chm['member_payload_extracted_or_decompressed'] is False,
        'CHM directory scope only')
if chm_completed:
    require(len(chm['members']) == chm['member_count'] == 4312 and chm['pmgl_count'] == 58
            and chm['pmgi_count'] == 1 and len(chm['chunks']) == 59
            and chm['input_actual'] == chm_extract['documentation_data']
            and chm['container_bytes_read_for_sha256'] is True,
            'New saved directory count and actual container binding')
chm_peer, chm_peer_d = obj(EX/'schema_chm_directory_static_review_20260930_1228'/'SAVED_VALUES_REVIEW.json',
                        'ad767dbec06ff042d296bb03efbb7da3d0fe9d8bacfdd93b8e51b766c920b6c1')
require(chm_peer['result'] == 'saved_values_relations_accepted'
        and chm_peer['bindings'][0] == chm_d
        and chm_peer['summary']['members'] == 4312
        and chm_peer['CHM_read_or_hashed'] is False
        and chm_peer['schema_validation'] is False,
        'Peer saved-directory relations and explicitly inherited container descriptor')

observation, observation_d = obj(OBS/'ROOT_OBSERVATION_SEAL.json', '5161e88944263b9e92bcde644a97122ffa82d4b8b71ee69d97ee3a7ac111484b')
require(observation['boot_ticks'] == 639263337875000000 or observation['boot_ticks'] == '639263337875000000', 'Saved current boot')
require(observation['gpu_exit_code'] == 0 and observation['gpu_rows'] == 25
        and observation['gpu_gate_satisfied'] is False and observation['execution_released'] is False
        and observation['cleanup_authorized'] is False and observation['new_scientific_result'] is False,
        'Saved snapshot does not release execution')

additional = [
    ICLR/'REVIEW.md', ICLR/'DELIVERY.json', ICLR/'PRIMARY_ACCESS.json',
    ICLR/'DIRECT_PUBLIC_METADATA_ACCESS.json', ICLR/'fetch_public_metadata.py', ICLR/'seal_iclr_field_review.py',
    FEAS/'DELIVERY.json', HERE/'ACTUAL_DATA_TOOL_RECEIPT.json', HERE/'ROOT_WEB_RESEARCH_SCOPE.json',
    HERE/'SDK_CABINET_HEADER_INSPECTION.json', HERE/'DATA_DOWNLOAD_MARKER.json',
    HERE/'DATA_DOWNLOAD_MARKER_V2.json', HERE/'DATA_DOWNLOAD_FAILURE_V2.json', HERE/'DATA_DOWNLOAD_MARKER_V3.json',
    HERE/'acquire_sdk_data.py', HERE/'acquire_sdk_data_v2.ps1', HERE/'acquire_sdk_data_v3.ps1',
    HERE/'derive_download_v3.py', HERE/'DOWNLOAD_V3_DELTA.patch', HERE/'inspect_sdk_cabinets.py',
    HERE/'extract_sdk_cab_data.py', HERE/'extract_sdk_chm_data.py', HERE/'read_sdk_file_table.py',
    HERE/'read_sdk_file_table_v1_to_v2.patch', MSIREVIEW/'review_saved_msi_table.py',
    HERE/'list_chm_directory.py', HERE/'list_chm_directory_v2.py', HERE/'list_chm_directory_v3.py',
    HERE/'list_chm_directory_v4.py', HERE/'list_chm_directory_v1_to_v2.patch',
    HERE/'list_chm_directory_v2_to_v3.patch', HERE/'list_chm_directory_v3_to_v4.patch',
    HERE/'ACTUAL_CHM_DIRECTORY_TOOL_RECEIPT.json',
    EX/'schema_chm_directory_static_review_20260930_1228'/'STATIC_REVIEW.json',
    EX/'schema_chm_directory_static_review_20260930_1228'/'SOURCE_BINDINGS.json',
    OBS/'seal_observation.py', OBS/'SEALER_PATH_ONLY.patch',
    OBS/'OBSERVATION_WRAPPER_INCLUDED.json', Path(__file__).resolve()]
for p in additional:
    read(p)

report = {
    'schema': 'lgm.root-limited-citation-format-research-adoption.v1',
    'adopted_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'root_method': 'Root read new sources, complete deltas and selected reports; actual SDK data actions were executed by root once. New3block/12field transcription and saved-data scope checks only. No old suite/weights/archive/native68 reopening.',
    'inputs': INPUTS, 'binding_count': len(INPUTS),
    'citation': {'report': fields_d, 'actual_refs': refs_d, 'exact_blocks': blocks_d, 'field_table': table_d,
        'previous_ordinal_gaps_closed': 3, 'confirmed_errors': 0, 'publisher_roles_unknown': 3,
        'literal_current_OpenReview_Cite_unknown': True, 'all_bibliography_verified': False,
        'manuscript_changed_or_recompiled': False},
    'format': {'initial_feasibility': feas_d, 'actual_download': download_d, 'outer_inert_extraction': extract_d,
        'inner_cab_header_review': cab_d, 'actual_readonly_msi_result': msi_d, 'saved_value_peer_review': peer_d,
        'source': source_d, 'actual_CHM_data_extraction': chm_extract_d, 'actual_CHM_directory_outcome': chm_d,
        'CHM_saved_value_peer_review': chm_peer_d,
        'CHM_directory_listing_completed': chm_completed,
        'CHM_schema_filename_candidates': chm.get('filename_candidates', []),
        'CHM_directory_scope': 'Saved4312 members,58PMGL/1PMGI; whole container SHA read, no member content/LZX/PMGI decoding. Opaque HTML names remain content-unknown. chm_directory_attempt_v1 is consumed, no replay/deletion.',
        'containers_byte_bindings': 'New data descriptor SHA/size inherited from actual acquisition/extraction/query/listing results. This adoption does not rehash PE/CAB/MSI/CHM payloads.',
        'complete_correct_2012_schema_obtained': False, 'full_XSD_validation': False, 'Visio_application_validation': False,
        'schema_availability_limit': 'No separately named XSD in saved236 installed filenames. Directory candidates may identify documentation filenames, not decoded HTML/schema bytes or full import closure; absence does not prove schemas never distributed.'},
    'actual_saved_observation': observation_d,
    'snapshot_scope': 'Captured12:15/12:16London, not fresh OS/resource admission at adoption time; available_commit not measured. GPU25/gatefalse; same stopped science/currentboot/ordinary Visio. No release or cleanup.',
    'scientific_execution_or_acceptance_added': False, 'new_figure_or_manuscript_delivery': False,
    'Overleaf_updated': False, 'final_submission_advice_delivered': False, 'all_task_completed': False,
    'limits': ['Independent reviewers read saved source/API values; no human review, second held API/process evidence or independent scientific execution.',
        'Data/API close returns and ordinary tool exits are not scientific launcher/interpreter exit evidence.',
        'Source failure branches are statically reviewed, not dynamically tested by successful paths; hard interruption cannot ensure finally or reporting.',
        'Initial no-download research reports retain their original temporal scope; later data extraction/query is an external addition, never a rewritten historical report.',
        'No installer, downloaded SDK/member code, COM/Office, scientific library/GPU/native probe, lock/release/intent/state or user-app action.',
        'All negative results/frozen science/provenance gaps remain; source prep or data research does not complete T6/LOHO/baselines/full efficiency/application/final paper/Overleaf.']}
body = (json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode('utf8')
require(len(body) <= 128*1024, 'Small root report size before write')
out = HERE/'ROOT_LIMITED_RESEARCH_ADOPTION.json'
with out.open('xb') as f:
    f.write(body); f.flush(); os.fsync(f.fileno())
print(json.dumps({'path': str(out), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                  'binding_count': len(INPUTS), 'scientific_execution_added': False}, ensure_ascii=False))
