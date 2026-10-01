"""Generate a bounded new audit from the already reviewed University audit."""
from pathlib import Path
import difflib
import hashlib

HERE=Path(__file__).parent
base=HERE/'review_batch6.py'
target=HERE/'review_university_sensitivity3.py'
old=base.read_text(encoding='utf-8')
assert hashlib.sha256(base.read_bytes()).hexdigest()=='80bbbaf3f3f1c36ae9b6dfcf149bc2bb3ff64aede5c4e1bcb5275e37658d41f0'
text=old.replace('Fixed six new University visual_style/full evaluation runs.', 'Fixed three new University sensitivity evaluation runs.')
text=text.replace("('batch6_' + STAMP)", "('university_sensitivity3_' + STAMP)")
text=text.replace("'targets': [(v, s) for v in ('visual_style', 'full') for s in (1, 2, 3)], 'requested_evaluation_runs': 6, 'requested_retrieval_tasks': 18", "'targets': [(label, 1) for label in ('backbone_resnet50', 'embed_dim_256', 'embed_dim_1024')], 'requested_evaluation_runs': 3, 'requested_retrieval_tasks': 9")
start=text.index('    previous_dir =')
end=text.index("    runner_path =",start)
text=text[:start]+'''    prior_path = HERE / 'ROOT_SUES_BATCH11_ADOPTION_20260929.json'
    prior_sha = '657968ef1cf457bdc0b052c45cd0b2fd4f22dc687dc012d6f8482286e1fb052b'
    prior_eval = js(snapshot(prior_path, expected=prior_sha)[0])
    check(prior_eval['adopted_with_stated_inheritance_limits'] and prior_eval['accepted_total_evaluation_runs'] == 30 and prior_eval['accepted_total_retrieval_tasks'] == 150, 'Prior thirty-run adoption invalid')
    report['previous_eval_adoption'] = {'path':str(prior_path),'sha256':prior_sha,'accepted_runs':30,'accepted_tasks':150,'old_evaluation_artifacts_rehashed':False}
    snapshot(HERE / 'review_batch6.py', expected='80bbbaf3f3f1c36ae9b6dfcf149bc2bb3ff64aede5c4e1bcb5275e37658d41f0')
    snapshot(HERE / 'REVIEW_UNIVERSITY_SENSITIVITY3_SOURCE_DIFF.patch')
    root42_path = EX / 'completion_audits_20260928/ROOT_FIT_42_ADOPTION_20260928.json'
    root42_sha = 'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87'
    queue = [(root42_path, root42_sha, None)]
    graph, documents, seen = [], {}, set()
    while queue:
        path, expected, parent = queue.pop(0)
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        data, binding = snapshot(path, expected=expected)
        obj = js(data)
        documents[path.name] = obj
        graph.append({'from_document': parent, 'to_document': key, 'sha256': expected, 'actual_sha256_verified': True})
        # Only traverse the exact six later-fit roots to ROOT37; old main-fit
        # attachments are outside this new sensitivity evaluation audit.
        for dest, digest in refs(obj):
            if dest.name.startswith('ROOT_FIT_') and 'ADOPTION' in dest.name and dest.suffix == '.json':
                queue.append((dest, digest, key))
    required = ['ROOT_FIT_42_ADOPTION_20260928.json', 'ROOT_FIT_41_ADOPTION_20260928.json', 'ROOT_FIT_40_ADOPTION_20260928.json', 'ROOT_FIT_39_ADOPTION_20260928.json', 'ROOT_FIT_38_ADOPTION_20260928.json', 'ROOT_FIT_37_ADOPTION_20260927.json']
    check(all(name in documents for name in required), 'Inherited ROOT42-to-ROOT37 acceptance chain incomplete')
    check(all(documents[name]['adopted'] is True for name in required), 'Training root was not adopted')
    report['inherited_training_acceptance_graph'] = graph
    authority_reports, authority_rows, authority_ledgers = {}, {}, {}
    specific_sources = [
        ('formal_sensitivity/university1652/full/seed_1/resnet50/dim_512', 'ROOT_FIT_37_ADOPTION_20260927.json', 'completion_audits_20260927/BACKBONE_RESNET50_SEED1_COMPLETION.json', '140e3d91bd72b410874f6573b3d1ff21511801857d3b6043159d35d4c751f30d'),
        ('formal_sensitivity/university1652/full/seed_1/resnet18/dim_256', 'ROOT_FIT_38_ADOPTION_20260928.json', 'completion_audits_20260928/EMBED_DIM_256_SEED1_COMPLETION.json', 'a2652bf21befcf705152dead686d26dcb72be08f59857f724bc3d89a2f340324'),
        ('formal_sensitivity/university1652/full/seed_1/resnet18/dim_1024', 'ROOT_FIT_39_ADOPTION_20260928.json', 'completion_audits_20260928/EMBED_DIM_1024_SEED1_COMPLETION.json', 'f81c3eaa40918f630914b2d2c42f14eafa6abbadaed743f22711b10bfe0b14a3'),
    ]
    for identifier, root_name, relative, digest in specific_sources:
        source_path = EX / relative
        adoption = documents[root_name]
        check(adoption['independent_report']['path'] == str(source_path) and adoption['independent_report']['sha256'] == digest, 'Exact specific completion report edge missing')
        source = js(snapshot(source_path, expected=digest)[0])
        check(source['batch_passed'] and source['requested_new_fit_count'] == 1 and source['new_fits_fully_artifact_verified'] == 1, 'Specific training report not passed')
        matching = [r for r in source['new_runs'] if r['run_identifier'] == identifier]
        check(len(matching) == 1 and len(source['new_runs']) == 1, 'Specific training authority scope differs')
        entry = matching[0]
        check(entry['original_training_completion_issues'] == [] and entry['epochs_completed'] == 80 and entry['last_epoch'] == 79, 'Specific original training completion issues')
        check(identifier in adoption['completed_fit_ids'] and identifier in documents['ROOT_FIT_42_ADOPTION_20260928.json']['completed_fit_ids'], 'Training ID not in specific and final adopted roots')
        ledger_item = source['ledger_raw_snapshot']
        specific_ledger = js(snapshot(ledger_item['snapshot'], expected=ledger_item['sha256'])[0])
        check(source['registered_registry_sha256'] == specific_ledger['registered_registry_sha256'] and source['frozen_inputs_match'] is True, 'Specific source/registry/frozen binding invalid')
        record = specific_ledger['runs'][identifier]
        check(record['checkpoint_sha256'] == entry['artifacts_sha256_verified']['best.pt']['sha256'], 'Specific adopted ledger checkpoint differs from original artifact audit')
        authority_reports[identifier] = entry
        authority_ledgers[identifier] = specific_ledger
        authority_rows[identifier] = {'report_path':str(source_path),'report_sha256':digest,'historical_report_checkpoint_hashes_fresh_when_report_created':True,'independent_report':True,'root_adoption_document':root_name,'exact_root_report_edge_verified':True,'ledger_snapshot':ledger_item,'ledger_record':record}
    ledger = next(iter(authority_ledgers.values()))
    check(all(item['frozen_inputs'] == ledger['frozen_inputs'] and item['registered_registry_sha256'] == ledger['registered_registry_sha256'] for item in authority_ledgers.values()), 'Three adopted ledgers disagree on frozen inputs/registry')
    report['specific_training_report_authorities'] = list(authority_rows.values())
    report['inherited_checkpoint_sha_source'] = 'Each exact ROOT37/38/39 adopted independent report and that report SHA-bound ledger; all reached by final ROOT42 adoption chain'
    report['initial_inventory_not_used'] = True
''' + text[end:]
text=text.replace("    targets = {(v, s) for v in ('visual_style', 'full') for s in (1, 2, 3)}\n    specs = [s for s in main if s.dataset == 'university1652' and (s.variant, s.seed) in targets]\n    check(len(specs) == 6 and {(s.variant, s.seed) for s in specs} == targets, 'Fixed six-run scope')", "    targets = {row[0] for row in specific_sources}\n    specs = [s for s in sensitivity if s.dataset == 'university1652' and s.identifier in targets]\n    check(len(specs) == 3 and {s.identifier for s in specs} == targets, 'Fixed three sensitivity-run scope')")
text=text.replace("    parent = js(snapshot(HERE / 'PRE_RECOVERY_PARENT_STATUS_20260929.json', 'PARENT_STATUS_RAW.json', expected='9990d0fe954a55f57673ba1498a30c1250b6c50fd1c4b935fa6f8c1df653bfed')[0])", "    parent = js(snapshot(EX / 'status.json', 'PARENT_STATUS_RAW.json')[0])\n    check(parent['status'] == 'completed' and parent['exit_code'] == 0, 'Primary is not recorded completed')")
start=text.index('    allowed, cp_records = {}, {}')
end=text.index('    def scoped_sha(path):',start)
text=text[:start]+'''    allowed, cp_records = {}, {}
    for spec in specs:
        label = Path(spec.run_dir).parent.name
        path = Path(spec.run_dir / 'best.pt')
        entry = authority_reports[spec.identifier]
        artifacts = entry['artifacts_sha256_verified']
        art = artifacts['best.pt']
        record = authority_ledgers[spec.identifier]['runs'][spec.identifier]
        check(record['checkpoint_sha256'] == art['sha256'], 'Specific adopted ledger versus historical checkpoint SHA disagreement')
        check(Path(art['path']) == path, 'Specific checkpoint path differs')
        current = stat(path)
        check(current['bytes'] == art['bytes'], 'Checkpoint size changed')
        allowed[os.path.normcase(os.path.abspath(path))] = (path, current, art['sha256'])
        cp_records[spec.identifier] = {'path':str(path),'inherited_sha256':art['sha256'],'specific_historical_artifact':art,'specific_training_authority':authority_rows[spec.identifier],'inherited_ledger_record':record,'stat_before':current,'limitation':'Current checkpoint metadata stability cannot establish current bytes. Inherited SHA is bound by exact ROOT37/38/39 report and its adopted ledger, reached by ROOT42.'}
        for name in ('run_config.json','history.json','run.log'):
            old_art = artifacts[name]
            snapshot(Path(spec.run_dir) / name, f'{label}_seed{spec.seed}/training_authority/{name}', expected=old_art['sha256'])
            check((Path(spec.run_dir) / name).stat().st_size == old_art['bytes'], 'Historical small training artifact size mismatch')
        historical_manifest = entry['manifest_raw_snapshot']
        manifest_digest = historical_manifest['sha256']
        snapshot(historical_manifest['snapshot'], f'{label}_seed{spec.seed}/historical_manifest.json', expected=manifest_digest)
        manifest_data, _ = snapshot(Path(spec.run_dir) / 'run_manifest.json', f'{label}_seed{spec.seed}/training_authority/run_manifest.json', expected=manifest_digest)
        historical_match = js(manifest_data)
        check(historical_match['payload_sha256'] == entry['manifest_payload_sha256'] and historical_match['run_config_sha256'] == entry['run_config_sha256'], 'Specific historical manifest/config canonical bindings')

''' + text[end:]
text=text.replace("mode = 'inherited_adopted_ledger_SHA_NOT_fresh_checkpoint_hash'", "mode = 'inherited_exact_adopted_training_report_and_ledger_SHA_NOT_fresh_checkpoint_hash'")
text=text.replace('        for spec in specs:\n            run =', '        for spec in specs:\n            label = Path(spec.run_dir).parent.name\n            run =')
text=text.replace('{spec.variant}_seed{spec.seed}', '{label}_seed{spec.seed}')
oldcheck="            check(len(events) == 1 and events[0]['status'] == 'completed' and events[0]['exit_code'] == 0, 'Parent Popen completion event')"
newcheck=oldcheck+'''
            expected_command = runner.evaluation_command(project_paths.FrozenProjectPath(PKG / 'lgm_game_pytorch/formal_retrieval.py'), dataset, spec)
            expected_compat = [expected_command[0], str(compat / 'run_formal_worker.py'), '--path-compat-sha256', '11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1'] + expected_command[2:]
            check(events[0]['command'] == expected_compat, 'Original frozen evaluation command differs')
'''
text=text.replace(oldcheck,newcheck)
text=text.replace("check(launcher_numbers == [12564,7896,28100,18364,16816,31052], 'Fixed parent launcher event numbers')", "check(launcher_numbers == [35132,34416,36576], 'Fixed parent launcher event numbers')")
start=text.index("    report.update({'runs':results,")
end=text.index("    forbidden =",start)
text=text[:start]+'''    check(len([q for q in queries if q['mode'].startswith('inherited_')]) == 3 and len([q for q in queries if q['mode'] == 'fresh_non_checkpoint_byte_hash']) == 6, 'Original validator hash query counts differ')
    report.update({'runs':results,'original_validator_hash_queries':queries,'known_old_launcher_CIM_observation':cim,'independent_windows_exit_handles_held':False,'old_interpreter_identity_known':False,'interpreter_exit_codes_observed':False,'exit_evidence_basis':'Original parent Popen exit0 events and this later CIM observation of known launcher PID numbers only; a reused PID is not proof of original process survival; no original launcher CreationDate or interpreter identity observed by this audit.','accepted_evaluation_run_count':3,'accepted_retrieval_task_count':9,'fresh_evaluation_artifact_count':21,'inherited_previous_evaluation_run_count':30,'inherited_previous_retrieval_task_count':150,'accepted_total_evaluation_run_count_with_this_batch':33,'accepted_total_retrieval_task_count_with_this_batch':159,'all_42_evaluations_accepted':False,'paper_means_or_conclusions_created':False,'evaluation_rerun_or_rank_recomputation':False,'limitations':['Checkpoint SHA inherited from each exact ROOT37/38/39 adopted independent completion report and its explicitly SHA-bound ledger, all reached through ROOT42; not freshly hashed.','Checkpoint size/mtime/stat stability cannot establish current byte identity.','Evidence cache SHA and full image-content inventory SHA inherited; official path membership and metadata counts independently checked.','Per-query stored arrays checked and aggregate consistency verified; no full distance matrix/reranking or recomputation of AP from all positive ranks.','Exactly three new sensitivity runs and nine new tasks; thirty prior runs/150 prior tasks inherited by adoption SHA without rereading old attachments. Other concurrent audit batches are not included or accepted here.']})
''' + text[end:]
text=text.replace("'BATCH6_EVALUATION_REVIEW.json'", "'UNIVERSITY_SENSITIVITY3_EVALUATION_REVIEW.json'")
assert "('visual_style'" not in text
compile(text,str(target),'exec')
with target.open('x',encoding='utf-8',newline='\n') as f: f.write(text)
diff=''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile=str(base),tofile=str(target)))
with (HERE/'REVIEW_UNIVERSITY_SENSITIVITY3_SOURCE_DIFF.patch').open('x',encoding='utf-8',newline='\n') as f:f.write(diff)
print(hashlib.sha256(target.read_bytes()).hexdigest())
