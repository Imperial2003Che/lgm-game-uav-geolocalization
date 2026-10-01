"""Derive fixed nine-run audit, preserving SUES validation and checkpoint restrictions."""
from pathlib import Path
import hashlib
import difflib

here = Path(__file__).parent
old = here / 'review_sues_batch11.py'
base = old.read_text(encoding='utf-8')
assert hashlib.sha256(old.read_bytes()).hexdigest() == 'a1e79940cb32c2ed1e97a7cc87cb9199526ece5bd88ca6674ee7a8a506fe3c65'
s = base.replace('Fixed eleven new SUES evaluations;', 'Fixed nine new SUES main/sensitivity evaluations;')
s = s.replace("('sues_batch11_' + STAMP)", "('sues_batch9_' + STAMP)")
s = s.replace("'targets': [('content',2),('content',3)] + [(v,n) for v in ('style','visual','visual_content') for n in (1,2,3)], 'requested_evaluation_runs': 11, 'requested_retrieval_tasks': 88", "'main_targets': [(v,n) for v in ('visual_style','full') for n in (1,2,3)], 'sensitivity_targets': [('resnet50',512),('resnet18',256),('resnet18',1024)], 'requested_evaluation_runs': 9, 'requested_retrieval_tasks': 72")
a = s.index('    prior_path =')
b = s.index('    root42_path =', a)
s = s[:a] + '''    prior_path = HERE / 'ROOT_SUES_BATCH11_ADOPTION_20260929.json'
    prior_sha = '657968ef1cf457bdc0b052c45cd0b2fd4f22dc687dc012d6f8482286e1fb052b'
    prior_eval = js(snapshot(prior_path, expected=prior_sha)[0])
    check(prior_eval['adopted_with_stated_inheritance_limits'] and prior_eval['accepted_total_evaluation_runs'] == 30 and prior_eval['accepted_total_retrieval_tasks'] == 150, 'Prior thirty-run adoption invalid')
    report['previous_eval_adoption'] = {'path':str(prior_path),'sha256':prior_sha,'accepted_runs':30,'accepted_tasks':150,'old_evaluation_artifacts_rehashed':False}
    snapshot(HERE / 'review_sues_batch11.py', expected='a1e79940cb32c2ed1e97a7cc87cb9199526ece5bd88ca6674ee7a8a506fe3c65')
    snapshot(HERE / 'REVIEW_SUES_BATCH9_SOURCE_DIFF.patch')
''' + s[b:]
s = s.replace("('FULL_SEED2_COMPLETION.json','SUES_VISUAL_CONTENT_SEED2_COMPLETION.json')", "('FULL_SEED2_COMPLETION.json','SUES_VISUAL_CONTENT_SEED2_COMPLETION.json','SUES_BACKBONE_RESNET50_SEED1_COMPLETION.json','SUES_EMBED_DIM_256_SEED1_COMPLETION.json','SUES_EMBED_DIM_1024_SEED1_COMPLETION.json')")
a = s.index('    # Bind each later-trained fit')
b = s.index('    runner_path =', a)
s = s[:a] + '''    # The complete identifier disambiguates main fullseed1 and all three sensitivity fits.
    targets = {f'formal_main/sues200/{v}/seed_{n}/resnet18/dim_512' for v in ('visual_style','full') for n in (1,2,3)}
    sensitivity_authorities = {
        'formal_sensitivity/sues200/full/seed_1/resnet50/dim_512': ('SUES_BACKBONE_RESNET50_SEED1_COMPLETION.json','cf4e41df6db70baaf3e7dbb9ca235edd20bb7a55c0918a28dec9f186192c381b','ROOT_FIT_40_ADOPTION_20260928.json','f3a6d7a2d3bec664c5cb6fd3f2ae7d0d2f7d5a1cb1bda82c337c6a575f062488',40),
        'formal_sensitivity/sues200/full/seed_1/resnet18/dim_256': ('SUES_EMBED_DIM_256_SEED1_COMPLETION.json','68d37cb7f5dc09d0dec190ac3c30fb128c01bb8de1a3c7f1101edfcdaa24541e','ROOT_FIT_41_ADOPTION_20260928.json','e5f1c6512f829a66e9dc73915627d985aec174dfe7f4226696b631298369bd05',41),
        'formal_sensitivity/sues200/full/seed_1/resnet18/dim_1024': ('SUES_EMBED_DIM_1024_SEED1_COMPLETION.json','5136b0acd9cc7bcc67d6d49a41fff5476b40d2f647c0b0239a95bed691d84475','ROOT_FIT_42_ADOPTION_20260928.json','ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87',42),
    }
    targets.update(sensitivity_authorities)
    authority_reports, authority_rows, authority_ledgers = {}, {}, {}
    for identifier in sorted(targets):
        if identifier in sensitivity_authorities:
            source_name, report_pin, root_name, root_pin, fit_count = sensitivity_authorities[identifier]
            root_doc = documents[root_name]
            check(root_doc['adopted'] and root_doc['completed_fit_count'] == fit_count and identifier in root_doc['completed_fit_ids'], 'Specific sensitivity root adoption')
            check(any(Path(g['to_document']).name == root_name and g['sha256'] == root_pin for g in graph), 'Specific sensitivity adoption graph pin')
            check(root_doc['independent_report']['sha256'] == report_pin and Path(root_doc['independent_report']['path']).name == source_name, 'Sensitivity independent report is not exact root adoption target')
        else:
            variant, seed = identifier.split('/')[2], int(identifier.split('/')[3].split('_')[1])
            source_name = 'BATCH_COMPLETION_0013.json' if variant == 'visual_style' and seed in (1,2) else 'BATCH_COMPLETION_0944.json'
            report_pin = 'd0c73981bd2679d2d569bd37715f332384f9f2e62fa14290aa23ed659fef50e1' if source_name == 'BATCH_COMPLETION_0013.json' else '2183ab32674d171f0d7ce15ea96b5e72b1990ad7071404e89403108f28f96a25'
        source = documents[source_name]
        check(source['batch_passed'], 'Specific adopted training batch failed')
        entries = [r for r in source['new_runs'] if r['run_identifier'] == identifier]
        check(len(entries) == 1, 'Exact unique training report member')
        entry = entries[0]
        check(entry['run_identifier'] == identifier and entry['original_training_completion_issues'] == [] and entry['epochs_completed'] == 80 and entry['last_epoch'] == 79 and entry['optimizer_steps_each_epoch_from_original_config'] == 375, 'Specific SUES training completion')
        source_edges = [g for g in graph if Path(g['to_document']).name == source_name]
        check(len(source_edges) == 1 and source_edges[0]['actual_sha256_verified'] and source_edges[0]['sha256'] == report_pin, 'Training authority not reached through adopted ROOT42 chain with exact SHA')
        edge = source_edges[0]
        if identifier in sensitivity_authorities:
            historical_ledger = source['ledger_raw_snapshot']
            ledger_bytes, ledger_binding = snapshot(historical_ledger['snapshot'], 'training_ledgers/' + Path(historical_ledger['snapshot']).name, expected=historical_ledger['sha256'])
            check(len(ledger_bytes) == historical_ledger['bytes'], 'Specific adopted ledger snapshot size')
            fit_ledger = js(ledger_bytes)
            check(fit_ledger['frozen_inputs'] == ledger['frozen_inputs'] and fit_ledger['registered_registry_sha256'] == ledger['registered_registry_sha256'], 'Specific sensitivity ledger frozen inputs/registry')
            ledger_authority = {'path':historical_ledger['snapshot'],'sha256':historical_ledger['sha256'],'explicit_adopted_document_edge_verified':True,'fresh_snapshot_binding':ledger_binding}
        else:
            fit_ledger = ledger
            ledger_authority = report['inherited_checkpoint_sha_source']
        authority_reports[identifier] = entry
        authority_ledgers[identifier] = fit_ledger
        authority_rows[identifier] = {'report_path':edge['to_document'],'report_sha256':edge['sha256'],'run_identifier':identifier,'historical_report_checkpoint_hashes_fresh_when_report_created':True,'independent_report':True,'exact_report_edge_verified_by_root42_chain':True,'checkpoint_ledger_authority':ledger_authority}
    report['specific_training_report_authorities'] = list(authority_rows.values())
    report['initial_inventory_not_used'] = True
''' + s[b:]
s = s.replace("specs = [s for s in main if s.dataset == 'sues200' and (s.variant, s.seed) in targets]", "specs = [s for s in main + sensitivity if s.dataset == 'sues200' and s.identifier in targets]")
s = s.replace("check(len(specs) == 11 and {(s.variant, s.seed) for s in specs} == targets, 'Fixed eleven-run SUES scope')", "check(len(specs) == 9 and {s.identifier for s in specs} == targets, 'Fixed nine-run SUES scope')\n    check(sum(s.family == 'formal_main' for s in specs) == 6 and sum(s.family == 'formal_sensitivity' for s in specs) == 3, 'Exact six main and three sensitivity runs')")
s = s.replace("authority_reports[(spec.variant, spec.seed)]", "authority_reports[spec.identifier]")
s = s.replace("authority_rows[(spec.variant,spec.seed)]", "authority_rows[spec.identifier]")
s = s.replace("record = ledger['runs'][spec.identifier]", "record = authority_ledgers[spec.identifier]['runs'][spec.identifier]")
s = s.replace("f'{spec.variant}_seed{spec.seed}/", "f'{spec.identifier}/")
s = s.replace("launcher_numbers == [33892,35044,23980,30140,15024,9620,34464,32728,35396,36160,35544]", "launcher_numbers == [31464,35064,5708,23096,34716,23312,29988,12788,36492]")
s = s.replace("'accepted_evaluation_run_count':11,'accepted_retrieval_task_count':88,'fresh_evaluation_artifact_count':132,'inherited_previous_evaluation_run_count':19,'inherited_previous_retrieval_task_count':62,'accepted_total_evaluation_run_count_with_this_batch':30,'accepted_total_retrieval_task_count_with_this_batch':150", "'accepted_evaluation_run_count':9,'accepted_retrieval_task_count':72,'fresh_evaluation_artifact_count':108,'inherited_previous_evaluation_run_count':30,'inherited_previous_retrieval_task_count':150,'accepted_total_evaluation_run_count_with_this_batch':39,'accepted_total_retrieval_task_count_with_this_batch':222")
s = s.replace('Each of these eleven SUES fits has a specific original completion report reached by the adopted ROOT42 chain and matches the adopted Sep22 checkpoint ledger. Prior nineteen-run adoption retains its own historical-source limitations.', 'Each of these nine SUES fits has its specific original completion report reached by the adopted ROOT42 chain. Six main fits match the adopted Sep22 checkpoint ledger; each sensitivity fit matches its own completion-report-bound historical ledger. Prior thirty-run adoption retains its own historical-source limitations.')
s = s.replace('Exactly eleven new SUES runs and eighty-eight height/direction tasks; nineteen prior runs/sixty-two tasks inherited by adoption SHA, no visual_style/full or other evaluation accepted.', 'Exactly nine new SUES runs and seventy-two height/direction tasks; thirty prior runs/one-hundred-fifty tasks inherited by adoption SHA. The three University sensitivity evaluations are outside this batch; this report does not accept all42 evaluation runs.')
s = s.replace('SUES_BATCH11_EVALUATION_REVIEW.json', 'SUES_BATCH9_EVALUATION_REVIEW.json')
assert 'authority_reports[(spec.variant' not in s
assert 'authority_rows[(spec.variant' not in s
assert "f'{spec.variant}_seed{spec.seed}/" not in s
compile(s, '<derived-audit>', 'exec')
new = here / 'review_sues_batch9.py'
with new.open('x', encoding='utf-8', newline='\n') as f:
    f.write(s)
with (here / 'REVIEW_SUES_BATCH9_SOURCE_DIFF.patch').open('x', encoding='utf-8', newline='\n') as f:
    f.write(''.join(difflib.unified_diff(base.splitlines(True), s.splitlines(True), fromfile=str(old), tofile=str(new))))
print(new)
print(hashlib.sha256(new.read_bytes()).hexdigest())
