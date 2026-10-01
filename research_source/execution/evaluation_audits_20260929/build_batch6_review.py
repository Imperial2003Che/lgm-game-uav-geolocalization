"""Generate review derivative; no live experiment mutations or checkpoint access."""
from pathlib import Path
import difflib
import hashlib

here = Path(__file__).parent
old = here.parent / 'evaluation_audits_20260928/review_batch10.py'
base = old.read_text(encoding='utf-8')
assert hashlib.sha256(old.read_bytes()).hexdigest() == 'ef3a63b378d1d7846d87a5faf51a045de98b9b3b7064361c5556603167294c9e'
s = base.replace('Fixed ten new University evaluation runs.', 'Fixed six new University visual_style/full evaluation runs.')
s = s.replace("('batch10_' + STAMP)", "('batch6_' + STAMP)")
s = s.replace("[('content', 3)] + [(v, s) for v in ('style', 'visual', 'visual_content') for s in (1, 2, 3)]", "[(v, s) for v in ('visual_style', 'full') for s in (1, 2, 3)]")
s = s.replace("'requested_evaluation_runs': 10, 'requested_retrieval_tasks': 30", "'requested_evaluation_runs': 6, 'requested_retrieval_tasks': 18")
a = s.index("    prior_eval = js(snapshot(")
b = s.index("    root42_path =", a)
s = s[:a] + '''    previous_dir = EX / 'evaluation_audits_20260928'
    prior_path = previous_dir / 'ROOT_BATCH10_ADOPTION_20260928.json'
    prior_sha = '155610032a4e1951527206ee47c4366fbb202a7c175006209913cee86902173e'
    prior_eval = js(snapshot(prior_path, expected=prior_sha)[0])
    check(prior_eval['adopted_with_stated_inheritance_limits'] and prior_eval['accepted_total_evaluation_runs'] == 12 and prior_eval['accepted_total_retrieval_tasks'] == 36, 'Prior twelve-run adoption invalid')
    report['previous_eval_adoption'] = {'path':str(prior_path),'sha256':prior_sha,'accepted_runs':12,'accepted_tasks':36,'old_evaluation_artifacts_rehashed':False}
    snapshot(previous_dir / 'review_batch10.py', expected='ef3a63b378d1d7846d87a5faf51a045de98b9b3b7064361c5556603167294c9e')
    snapshot(HERE / 'REVIEW_BATCH6_SOURCE_DIFF.patch')
''' + s[b:]
a = s.index("    inventory_path =")
b = s.index("    runner_path =", a)
s = s[:a] + '''    # Specific later-trained fits use actual historical artifact reports, not the initial inventory.
    authority_reports = {}
    authority_rows = {}
    specific_sources = [
        ('visual_style', 1, 'VISUAL_STYLE_SEED1_COMPLETION_20260914.json', 'c899a2c99b0c90b865806eab41556fff4bea6bd56656a71073d5a60b294745f1', None, None),
        ('visual_style', 2, 'status_write_incident_20260920_0138/COMPLETED_FIT_REVIEW_20260920.json', '93890643b3649b7b53951566ed573d494c5f78016954546853bfc416886afb5b', 'state_write_recovery_20260920_0138/ROOT_ADOPTION_20260920.json', '871c6b014a48463af26e1624badad591db191f8a57aedf5687e8636f3ec95f97'),
        ('visual_style', 3, 'completion_audits_20260920/VISUAL_STYLE_SEED3_COMPLETION.json', '1810ff728ca2e09abca49d298d02fd1dfd120ec3186ee3f514dc7c6e8b924cf9', 'completion_audits_20260920/ROOT_SEED3_ADOPTION_20260920.json', '4ea57f0956af59749dd93c151108414f94e749d7ccb10fa8e75834b4c6196e7f'),
        ('full', 1, 'completion_audits_20260920/FULL_SEED1_COMPLETION.json', '61b2c2019d33ebcf192fbc73321f8667ef5daee9cd8e02bb87c6b4f862a0dd09', 'completion_audits_20260920/ROOT_FULL_SEED1_ADOPTION_20260920.json', '772133fee742bb3b26825eb8e3c05760cf4ace5e28f22d729c013841be84a018'),
        ('full', 2, 'completion_audits_20260920/FULL_SEED2_COMPLETION.json', 'ec116f025e590d4392322fcaef04923fa92d40c88afa909ca4ea7f6120594b16', 'completion_audits_20260920/ROOT_FULL_SEED2_ADOPTION_20260921.json', '0474c03baf3170dab96b297b9d426bd6b6ce1e7ad30fe5525cab2651bf6a8437'),
        ('full', 3, 'completion_audits_20260921/BATCH_COMPLETION_1611.json', 'f88259d145316e76b36f63130800f2a47f91c0cbdf863fd9cabb2381bbca0bb2', None, None),
    ]
    for variant, seed, relative, digest, adoption_relative, adoption_sha in specific_sources:
        source_path = EX / relative
        source = js(snapshot(source_path, expected=digest)[0])
        if (variant, seed) == ('full', 3):
            check(source['batch_passed'], 'Specific full3 historical batch rejected')
            entry = next(r for r in source['new_runs'] if r['run_identifier'] == 'formal_main/university1652/full/seed_3/resnet18/dim_512')
            check(any(g['to_document'] == str(source_path) and g['sha256'] == digest for g in graph), 'Full3 report not reached by adopted chain')
        else:
            entry = source
        if (variant, seed) == ('visual_style', 1):
            check(entry['status'] == 'new_complete_fit_artifacts_verified' and entry['epochs_completed'] == 80 and entry['final_epoch_zero_based'] == 79, 'Seed1 original artifact audit not complete')
        else:
            check(entry['original_training_completion_issues'] == [] and entry['epochs_completed'] == 80 and entry['last_epoch'] == 79, 'Specific original training completion issues')
            check((variant, seed) == ('full', 3) or entry['passed'], 'Specific training audit did not pass')
        authority = {'report_path':str(source_path),'report_sha256':digest,'historical_report_checkpoint_hashes_fresh_when_report_created':True,'independent_report': (variant,seed) not in (('visual_style',1),('visual_style',2))}
        if adoption_relative:
            adoption_path = EX / adoption_relative
            adoption = js(snapshot(adoption_path, expected=adoption_sha)[0])
            if variant == 'visual_style' and seed == 2:
                check(any(p == source_path and h == digest for p,h in refs(adoption)), 'Detached completion not bound by recovery adoption')
            else:
                check(adoption['accepted'] and Path(adoption['audit_path']) == source_path and adoption['audit_sha256'] == digest, 'Legacy root adoption exact report edge')
            authority['historical_root_adoption'] = {'path':str(adoption_path),'sha256':adoption_sha,'exact_report_edge_verified':True}
        if (variant,seed) == ('visual_style',1):
            authority['historical_report_sha_edge_found'] = False
            authority['limitation'] = 'Sep14 report is current-SHA-bound matching corroboration; no separate historical whole-report SHA edge found. Accepted ROOT42 identifier and SHA-linked adopted ledger supply inherited checkpoint authority.'
        authority_reports[(variant,seed)] = entry
        authority_rows[(variant,seed)] = authority
    report['specific_training_report_authorities'] = list(authority_rows.values())
    report['initial_inventory_not_used'] = True
''' + s[b:]
s = s.replace("targets = {('content', 3)} | {(v, s) for v in ('style', 'visual', 'visual_content') for s in (1, 2, 3)}", "targets = {(v, s) for v in ('visual_style', 'full') for s in (1, 2, 3)}")
s = s.replace("len(specs) == 10", "len(specs) == 6").replace("Fixed ten-run scope", "Fixed six-run scope")
s = s.replace("parent = js(snapshot(EX / 'status.json', 'PARENT_STATUS_RAW.json')[0])", "parent = js(snapshot(HERE / 'PRE_RECOVERY_PARENT_STATUS_20260929.json', 'PARENT_STATUS_RAW.json', expected='9990d0fe954a55f57673ba1498a30c1250b6c50fd1c4b935fa6f8c1df653bfed')[0])")
a = s.index("        entry = next(r for r in inventory['runs']")
b = s.index("\n    def scoped_sha", a)
s = s[:a] + '''        entry = authority_reports[(spec.variant, spec.seed)]
        artifacts = entry['verified_artifacts'] if (spec.variant,spec.seed) == ('visual_style',1) else entry['artifacts_sha256_verified']
        art = artifacts['best.pt']
        record = ledger['runs'][spec.identifier]
        check(record['checkpoint_sha256'] == art['sha256'], 'Adopted ledger versus specific historical checkpoint SHA disagreement')
        current = stat(path)
        check(current['bytes'] == art['bytes'], 'Checkpoint size changed')
        allowed[os.path.normcase(os.path.abspath(path))] = (path, current, record['checkpoint_sha256'])
        cp_records[spec.identifier] = {'path':str(path),'inherited_sha256':record['checkpoint_sha256'],'specific_historical_artifact':art,'specific_training_authority':authority_rows[(spec.variant,spec.seed)],'inherited_ledger_record':record,'stat_before':current,'limitation':'Current checkpoint metadata stability cannot establish current bytes. Inherited SHA is bound by accepted ledger and matches specific historical training artifact report.'}
        # Rebind small current training artifacts to the actual historical audit values.
        for name in ('run_config.json','history.json','run.log'):
            old_art = artifacts[name]
            snapshot(Path(spec.run_dir) / name, f'{spec.variant}_seed{spec.seed}/training_authority/{name}', expected=old_art['sha256'])
            check((Path(spec.run_dir) / name).stat().st_size == old_art['bytes'], 'Historical small training artifact size mismatch')
        if (spec.variant,spec.seed) == ('visual_style',1):
            manifest_digest = entry['manifest_sha256']
        elif (spec.variant,spec.seed) == ('visual_style',2):
            manifest_digest = entry['run_manifest']['sha256']
        else:
            historical_manifest = entry['manifest_raw_snapshot']
            manifest_digest = historical_manifest['sha256']
            snapshot(historical_manifest['snapshot'], f'{spec.variant}_seed{spec.seed}/historical_manifest.json', expected=manifest_digest)
        manifest_data, _ = snapshot(Path(spec.run_dir) / 'run_manifest.json', f'{spec.variant}_seed{spec.seed}/training_authority/run_manifest.json', expected=manifest_digest)
        historical_match = js(manifest_data)
        if 'manifest_payload_sha256' in entry:
            check(historical_match['payload_sha256'] == entry['manifest_payload_sha256'] and historical_match['run_config_sha256'] == entry['run_config_sha256'], 'Specific historical manifest/config canonical bindings')
''' + s[b:]
s = s.replace("[11940,31708,28140,29260,29896,30828,3088,11088,14564,1920]", "[12564,7896,28100,18364,16816,31052]")
s = s.replace("'accepted_evaluation_run_count':10,'accepted_retrieval_task_count':30,'fresh_evaluation_artifact_count':70,'inherited_previous_evaluation_run_count':2,'inherited_previous_retrieval_task_count':6,'accepted_total_evaluation_run_count_with_this_batch':12,'accepted_total_retrieval_task_count_with_this_batch':36", "'accepted_evaluation_run_count':6,'accepted_retrieval_task_count':18,'fresh_evaluation_artifact_count':42,'inherited_previous_evaluation_run_count':12,'inherited_previous_retrieval_task_count':36,'accepted_total_evaluation_run_count_with_this_batch':18,'accepted_total_retrieval_task_count_with_this_batch':54")
s = s.replace("Historical initial-12 inventory whole-file SHA was not found linked in the traversed acceptance chain; current snapshot is corroboration only.", "Visual_style seed1 original Sep14 whole-report historical SHA edge was not found; currently bound report is corroboration. Accepted ROOT42 identifier and adopted Sep22 ledger supply inherited checkpoint authority. Other five specific reports have verified historical root/chain edges.")
s = s.replace("Exactly ten new runs, thirty new tasks; two prior runs/six prior tasks inherited by adoption SHA, no other evaluation accepted.", "Exactly six new runs, eighteen new tasks; twelve prior runs/thirty-six prior tasks inherited by adoption SHA, no other evaluation accepted.")
s = s.replace("BATCH10_EVALUATION_REVIEW.json", "BATCH6_EVALUATION_REVIEW.json")
assert "inventory['runs']" not in s and 'initial_inventory_not_used' in s
new = here / 'review_batch6.py'
new.write_text(s, encoding='utf-8', newline='\n')
diff = ''.join(difflib.unified_diff(base.splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(new)))
(here / 'REVIEW_BATCH6_SOURCE_DIFF.patch').write_text(diff,encoding='utf-8',newline='\n')
print(new)
print(hashlib.sha256(new.read_bytes()).hexdigest())
