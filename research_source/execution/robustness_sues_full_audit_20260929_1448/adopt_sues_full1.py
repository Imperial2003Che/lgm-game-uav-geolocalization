"""Root adoption of one independently reviewed SUES Full result, with stopped-incident context.

Only new result files and small authority metadata are read. No scientific imports
or checkpoint/cache/image bytes, state mutation or process launch for science.
"""
import base64
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
EX = HERE.parent
SEEN = {}

def require(value, label):
    if not value:
        raise AssertionError(label)

def bind(path, sha256, size=None):
    path = Path(path).absolute()
    key = str(path).casefold()
    require(path.suffix.lower() not in {'.pt', '.pth', '.ckpt'}, 'No checkpoint bytes')
    require('imtmn\\datasets\\' not in key and not ('evidence_cache' in key and path.suffix == '.npz'), 'No cache/image bytes')
    if key not in SEEN:
        raw = path.read_bytes()
        SEEN[key] = {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    result = SEEN[key]
    require(result['sha256'] == sha256 and (size is None or result['bytes'] == size), 'Binding: ' + str(path))
    return result

def B(item):
    return bind(item['path'], item['sha256'], item.get('bytes'))

def J(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def ref(value, path, sha):
    if isinstance(value, dict):
        strings = [v for v in value.values() if isinstance(v, str)]
        if sha in strings and any(v.casefold().replace('/', '\\') == str(path).casefold().replace('/', '\\') for v in strings):
            return True
        return any(ref(v, path, sha) for v in value.values())
    return isinstance(value, list) and any(ref(v, path, sha) for v in value)

def main():
    delivery_sha, contract_sha, static_sha = sys.argv[1:]
    rb = bind(HERE/'a1/REVIEW.json', '3cfaf28ba6caa7d0c12bcf65853dbb1c1a918363216287a6baf1d2c31b9abb78')
    mb = bind(HERE/'a1/METADATA.json', '710c0280f76a99cf379bc85f17467fef462fcb094f5d37cafdcc773b07f71c43')
    source = bind(HERE/'review_sues_full1.py', 'e6dc1126279ec05b40b89e279ae41a4863fbef0a88e0c7b87fd6d0a0febf9f13')
    diff = bind(HERE/'SUES_FULL_FROM_SUES_VISUAL_SOURCE_DIFF.patch', 'e8581e34b18519de920f6abf2be7c00e26dc7d1318557ce53df5fa7093a5096c')
    r, m = J(rb['path']), J(mb['path'])
    require(r['passed_with_stated_limits'] and (r['accepted_runs'], r['accepted_corrupted_conditions'], r['accepted_corrupted_tasks'], r['accepted_clean_tasks'], r['summary_rows']) == (1,30,240,8,1440), 'New scope')
    require(r['checkpoint_bytes_read'] == r['cache_or_image_bytes_read'] == 0 and not r['scientific_entrypoints_executed'] and not r['live_files_modified'] and r['scientific_modules'] == [] and r['original_completion_issues'] == [], 'Bounded execution')
    B(r['source']); B(m['source']); B(m['report'])
    for b in m['files']:
        require(Path(b['path']).is_relative_to(HERE/'a1'), 'Metadata local attempt only')
        B(b)
    for b in r['raw_evidence_bindings']:
        bind(b['snapshot'], b['sha256'], b['bytes']); B(b)
    for b in r['artifact_bindings']:
        B(b)
    B(r['directory_membership'])
    require(r['directory_membership']['count'] == 40200 and not r['directory_membership']['image_bytes_read'], 'Directory scope')
    protocol = r['sues_official_protocol']; B(protocol['manifest'])
    require(len(protocol['train_ids']) == 120 and len(protocol['test_ids']) == 80 and protocol['heights'] == ['150','200','250','300'] and protocol['tasks'] == 8 and protocol['all_200_gallery_ids_retained'], 'Frozen SUES membership')
    checkpoint = '7478740b013990c83c5c21f619bc89b2664ee70ff90fda18ab3b7ac420c870e9'
    identifier = 'formal_main/sues200/full/seed_1/resnet18/dim_512'
    manifest = J(r['manifest_binding']['path'])
    config = J(Path(r['manifest_binding']['path']).parent/'run_config.json')
    require(manifest['status'] == 'completed' and manifest['dataset'] == 'sues200' and manifest['variant'] == 'full' and manifest['completed_corruption_conditions'] == 30, 'Completed Full manifest')
    require(manifest['run_config_sha256'] == config['run_config_sha256'] == 'f5f1752ceb01cb8f9e28cf70712d8bd4f4045cbf1d44f53b4c07a7babf8f9f21', 'Canonical config')
    require(manifest['checkpoint']['checkpoint_sha256'] == config['immutable_config']['checkpoint']['checkpoint_sha256'] == checkpoint and config['immutable_config']['unique_query_images'] == 16080 and config['immutable_config']['unique_clean_gallery_images'] == 40200, 'Exact checkpoint and members')
    diag = r['full_clip_diagnostic']; B(diag['cache_metadata'])
    require(diag['canonical_verified'] and diag['sidefile_and_top_manifest_equal'] and diag['sample_path_selection_checked_without_image_bytes'] and not diag['numerical_error_recomputed'] and not diag['tolerance_gate_exists'], 'Diagnostic limited scope')
    require(diag['payload'] == manifest['clip_clean_reproduction_audit'] and diag['payload']['payload_sha256'] == '3069fcb2b0a9a19f0a201bb2993ff5b31ab43f1377b96dddfed8440fda82c1c4' and len(diag['sample_paths']) == 64, 'Full-specific diagnostic')
    ids = {(t['condition'],t['severity'],t['task']) for t in r['tasks']}
    require(len(ids) == len(r['tasks']) == 248 and len(r['original_functions']) == 52 and not any(f['body_changed'] for f in r['original_functions']), 'Exact tasks and original AST')
    for task in r['tasks']:
        expected = (4000,200) if task['task'].startswith('sues200_uav_') else (80,10000)
        require((task['queries'], task['gallery']) == expected, 'Task scale')
    inherited = [x for x in r['original_hash_queries'] if x['mode'] == 'exact_inherited_checkpoint_SHA_no_read']
    require(len(inherited) == 1 and inherited[0]['sha256'] == checkpoint and len(r['original_hash_queries']) == 716 and r['unique_artifact_count'] == 375 and len(r['raw_evidence_bindings']) == 407 and r['checks']['csv_tables'] == 62, 'Hash scope')
    require(r['inherited_authority']['source_training_identifier'] == identifier and r['inherited_authority']['checkpoint_sha256'] == checkpoint, 'Own training authority')
    tb = B(r['specific_training_source_bindings']['report']); training_batch = J(tb['path'])
    training = [x for x in training_batch['new_runs'] if x['run_identifier'] == identifier]
    require(training_batch['batch_passed'] and len(training) == 1, 'Unique adopted batch member')
    training = training[0]
    require(training['epochs_completed'] == 80 and training['last_epoch'] == 79 and training['optimizer_steps_each_epoch_from_original_config'] == 375 and training['original_training_completion_issues'] == [] and training['artifacts_sha256_verified']['best.pt']['sha256'] == checkpoint and training['artifacts_sha256_verified']['best.pt']['bytes'] == 172338603, 'Own 80 epoch evidence')
    chain = r['specific_training_source_bindings']['root42_ancestry']
    require(len(chain) == 7 and chain[0]['to_document'] == tb['path'] and chain[0]['sha256'] == tb['sha256'] and chain[-1]['sha256'] == 'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87' and chain[-1]['from_document'] is None, 'Training chain endpoints')
    for i,node in enumerate(chain):
        bind(node['to_document'], node['sha256'])
        if i+1 < len(chain):
            require(node['from_document'] == chain[i+1]['to_document'] and ref(J(node['from_document']), node['to_document'], node['sha256']), 'Actual path and SHA edge')
    ledger = J(r['original_parent_record']['ledger']['path']); finished = ledger['runs']['sues200/full/seed_1']
    require(finished == r['original_parent_record']['run_record'] and finished['status'] == 'completed_and_verified' and len(finished['attempts']) == 1 and finished['attempts'][0]['returncode'] == 0, 'Unchanged exact parent record')
    for key in ('stdout','stderr'): B(finished['attempts'][0][key])
    previous = bind(EX/'robustness_sues_visual_audit_20260929_1351/ROOT_SUES_VISUAL1_ADOPTION.json', 'a6795283cb384c77732bdb1e63af93d582d7844879f415e45ef38c8861d3af74')
    prior = J(previous['path'])
    require(prior['accepted_with_stated_limits'] and (prior['accepted_robustness_runs'], prior['accepted_corrupted_tasks'],prior['accepted_clean_tasks']) == (3,420,14), 'Prior accepted three')
    db = bind(HERE/'DELIVERY.json', delivery_sha); delivery = J(db['path'])
    require(delivery['passed_with_stated_limits'] and delivery['root_adoption_not_claimed'] and delivery['new_artifacts'] == 375 and not delivery['scientific_execution_performed'], 'Delivery scope')
    for b in delivery['files']: B(b)
    cb = bind(HERE/'contract_review/SUES_FULL_CONTRACT_REVIEW.json', contract_sha)
    sb = bind(HERE/'contract_review/SUES_FULL_SOURCE_STATIC_REVIEW.json', static_sha)
    contract, static = J(cb['path']), J(sb['path'])
    # These two schemas are independently read before this script is executed.
    for b in contract['source_and_small_file_bindings']: B(b['source']); B(b['snapshot'])
    require(not contract['live_state_modified'] and contract['scientific_imports'] == [] and not contract['scientific_acceptance'] and not contract['clip_numerical_values_independently_recomputed'] and not contract['clip_threshold_gate'], 'Read-only independent contract')
    require(contract['canonical_config_sha256'] == manifest['run_config_sha256'] and contract['inherited_checkpoint']['sha256'] == checkpoint and contract['parent_record'] == finished['attempts'][0] and contract['clip_diagnostic'] == diag['payload'], 'Contract exact result')
    B(static['review_markdown']); B(static['sealing_source'])
    B(static['candidate']); B(static['base']); B(static['contract_report'])
    require(static['blocking_findings'] == [] and not static['candidate_or_control_tests_executed'] and not static['scientific_acceptance'] and static['complete_diff_read'] and static['top_level_functions_and_classes_unchanged'], 'Independent static scope')
    incident = bind(EX/'efficiency_incident_20260929_1448/ROOT_INCIDENT_REVIEW_ADOPTION.json', 'e0595908f2dfa911d3cf4662333c80119452802635d185634d7ee9280e614031')
    pipeline_binding = bind(EX/'pipeline_status.json', '47fd31336b8e742da91891a87c28a0767989cb45c375aeb000854f50e37acf12')
    pipeline = J(pipeline_binding['path'])
    stage = next(x for x in pipeline['jobs'] if x['id'] == 'robustness')
    require(stage['status'] == 'completed' and stage['exit_code'] == 0 and stage['pid'] == 24120, 'Original robustness stage parent exit record')
    # Incident metadata is read as context, never used to substitute science acceptance.
    probe = r"$ids=@(33924,31992,14420,29784,30388,7584,33520,12896,7484,21652,24120,40780,37764,14260,43500,40968,23920); $all=@(Get-CimInstance Win32_Process); [ordered]@{time=(Get-Date).ToString('o'); matches=@($all|Where-Object {$_.ProcessId -in $ids}|ForEach-Object {[ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks.ToString();command=$_.CommandLine}})}|ConvertTo-Json -Depth 6 -Compress"
    proc = subprocess.run(['pwsh','-NoProfile','-EncodedCommand',base64.b64encode(probe.encode('utf-16-le')).decode()], capture_output=True, check=True)
    current = json.loads(proc.stdout.decode('utf-8-sig'))
    # A reused number must be reviewed separately; absence is not any exit-code proof.
    require(current['matches'] == [], 'Process number reappeared: inspect creation/command instead of assuming old owner')
    own = B({'path':str(Path(__file__).resolve()),'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    result = {'schema':'lgm.root.robustness-sues-full1-adoption.v1','time':dt.datetime.now().astimezone().isoformat(),
        'accepted_with_stated_limits':True,'source':own,'independent_review':rb,'metadata':mb,'review_source':source,'complete_source_diff':diff,'delivery':db,'contract_review':cb,'independent_source_static_review':sb,
        'previous_robustness_adoption':previous,'newly_accepted_runs':1,'newly_accepted_corrupted_conditions':30,'newly_accepted_corrupted_tasks':240,'newly_accepted_clean_tasks':8,
        'accepted_robustness_runs':4,'accepted_corrupted_conditions':120,'accepted_corrupted_tasks':660,'accepted_clean_tasks':22,'pipeline_whole_jobs_adopted':4,'robustness_pipeline_complete':True,
        'retained_training_fits':42,'retained_official_runs':42,'retained_official_tasks':231,'retained_transfer_runs':12,'retained_transfer_tasks':66,
        'actual_unique_file_checks':len(SEEN),'raw_snapshot_count':407,'unique_artifact_count':375,'bindings':list(SEEN.values()),'inherited_authority':r['inherited_authority'],'training_chain':chain,'sues_protocol':protocol,
        'full_clip_diagnostic':diag,'original_parent_record':r['original_parent_record'],'current_CIM':current,'incident_context':incident,'pipeline_status':pipeline_binding,'original_robustness_stage_record':stage,
        'limits':r['limits'] + contract['interpretation_limits'] + static['interpretation_limits'] + ['Only four robustness runs and their completed stage are accepted here; aggregate/query are separate pending audits. T6 failed its original GPU-exclusive gate; no recovery or state changes occur.'],
        'validator_compatibility':r['compatibility'],'float32_mean_check_limit':r['independent_mean_check'],
        'exit_limit':'Original parent subprocess.run return0 plus current PID absence; no independent launcher/interpreter dual-handle exit proof. Primary own exit code remains unknown.',
        'review_method':'Root read complete derived diff, critical source, independent contract/static source, bound all new raw/production artifacts and exact training ancestry, and reconciled parent record/current stopped incident. Old checkpoint/attachment suites not rerun.',
        'checkpoint_bytes_rehashed':0,'scientific_execution':False,'live_state_modified':False}
    out = HERE/'ROOT_SUES_FULL1_ADOPTION.json'
    with out.open('x',encoding='utf-8',newline='\n') as f: json.dump(result,f,ensure_ascii=False,indent=2); f.write('\n')
    print(json.dumps({'path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'checks':len(SEEN),'accepted_runs':4,'corrupted_tasks':660,'clean_tasks':22}))

if __name__ == '__main__':
    main()
