"""Fixed eleven-run derivative; no experiment execution or checkpoint access."""
from pathlib import Path
import hashlib
import difflib

here=Path(__file__).parent
old=here/'review_sues_content_seed1.py'
base=old.read_text(encoding='utf-8')
assert hashlib.sha256(old.read_bytes()).hexdigest() == 'a0dbe9e3de6e7075aaa73681ca7b9a7562d6c663c4eb70f106090424b9e9057c'
s=base.replace('Fixed SUES content seed1 evaluation; eight official height/direction tasks.', 'Fixed eleven new SUES evaluations; eight official height/direction tasks per run.')
s=s.replace("('sues_content_seed1_' + STAMP)","('sues_batch11_' + STAMP)")
s=s.replace("'targets': [('content', 1)], 'requested_evaluation_runs': 1, 'requested_retrieval_tasks': 8", "'targets': [('content',2),('content',3)] + [(v,n) for v in ('style','visual','visual_content') for n in (1,2,3)], 'requested_evaluation_runs': 11, 'requested_retrieval_tasks': 88")
a=s.index("    prior_path =")
b=s.index("    root42_path =",a)
s=s[:a]+'''    prior_path = HERE / 'ROOT_SUES_CONTENT_SEED1_ADOPTION_20260929.json'
    prior_sha = '7acf3313c7d3950a3da9f0fe13166b9536dd5615f5b0137eaf09a25cd621e715'
    prior_eval = js(snapshot(prior_path, expected=prior_sha)[0])
    check(prior_eval['adopted_with_stated_inheritance_limits'] and prior_eval['accepted_total_evaluation_runs'] == 19 and prior_eval['accepted_total_retrieval_tasks'] == 62, 'Prior nineteen-run adoption invalid')
    report['previous_eval_adoption'] = {'path':str(prior_path),'sha256':prior_sha,'accepted_runs':19,'accepted_tasks':62,'old_evaluation_artifacts_rehashed':False}
    snapshot(HERE / 'review_sues_content_seed1.py', expected='a0dbe9e3de6e7075aaa73681ca7b9a7562d6c663c4eb70f106090424b9e9057c')
    snapshot(HERE / 'REVIEW_SUES_BATCH11_SOURCE_DIFF.patch')
''' + s[b:]
s=s.replace("dest.name == 'FULL_SEED2_COMPLETION.json'", "dest.name in ('FULL_SEED2_COMPLETION.json','SUES_VISUAL_CONTENT_SEED2_COMPLETION.json')")
a=s.index("    # This exact fit")
b=s.index("    runner_path =",a)
s=s[:a]+'''    # Bind each later-trained fit to its actual accepted report, not an initial inventory entry.
    targets = {('content',2),('content',3)} | {(v,n) for v in ('style','visual','visual_content') for n in (1,2,3)}
    authority_reports, authority_rows = {}, {}
    for variant, seed in sorted(targets):
        identifier = f'formal_main/sues200/{variant}/seed_{seed}/resnet18/dim_512'
        if (variant,seed) == ('visual_content',2):
            source_name = 'SUES_VISUAL_CONTENT_SEED2_COMPLETION.json'
            source = documents[source_name]
            check(source['passed'], 'Specific SUES visual_content2 original training audit')
            entry = source
            steps = entry['optimizer_steps_each_epoch']
        else:
            source_name = 'BATCH_COMPLETION_0013.json' if (variant,seed) == ('visual_content',3) else 'BATCH_COMPLETION_1611.json'
            source = documents[source_name]
            check(source['batch_passed'], 'Adopted SUES training batch did not pass')
            entries = [r for r in source['new_runs'] if r['run_identifier'] == identifier]
            check(len(entries) == 1, 'Exact unique training report member')
            entry = entries[0]
            steps = entry['optimizer_steps_each_epoch_from_original_config']
        check(entry['run_identifier'] == identifier and entry['original_training_completion_issues'] == [] and entry['epochs_completed'] == 80 and entry['last_epoch'] == 79 and steps == 375, 'Specific SUES training completion')
        source_edges = [g for g in graph if Path(g['to_document']).name == source_name]
        check(len(source_edges) == 1 and source_edges[0]['actual_sha256_verified'], 'Training authority not reached through adopted ROOT42 chain')
        edge = source_edges[0]
        authority_reports[(variant,seed)] = entry
        authority_rows[(variant,seed)] = {'report_path':edge['to_document'],'report_sha256':edge['sha256'],'run_identifier':identifier,'historical_report_checkpoint_hashes_fresh_when_report_created':True,'independent_report':True,'exact_report_edge_verified_by_root42_chain':True}
    report['specific_training_report_authorities'] = list(authority_rows.values())
    report['initial_inventory_not_used'] = True
''' + s[b:]
s=s.replace("    targets = {('content',1)}\n","")
s=s.replace("len(specs) == 1", "len(specs) == 11").replace('Fixed SUES content1 scope','Fixed eleven-run SUES scope')
s=s.replace("launcher_numbers == [20376]", "launcher_numbers == [33892,35044,23980,30140,15024,9620,34464,32728,35396,36160,35544]")
s=s.replace("'accepted_evaluation_run_count':1,'accepted_retrieval_task_count':8,'fresh_evaluation_artifact_count':12,'inherited_previous_evaluation_run_count':18,'inherited_previous_retrieval_task_count':54,'accepted_total_evaluation_run_count_with_this_batch':19,'accepted_total_retrieval_task_count_with_this_batch':62", "'accepted_evaluation_run_count':11,'accepted_retrieval_task_count':88,'fresh_evaluation_artifact_count':132,'inherited_previous_evaluation_run_count':19,'inherited_previous_retrieval_task_count':62,'accepted_total_evaluation_run_count_with_this_batch':30,'accepted_total_retrieval_task_count_with_this_batch':150")
s=s.replace('This SUES fit has a specific original completion report reached by the adopted ROOT42 chain and matches adopted Sep22 checkpoint ledger. Prior eighteen-run adoption retains its own historical-source limitations.', 'Each of these eleven SUES fits has a specific original completion report reached by the adopted ROOT42 chain and matches the adopted Sep22 checkpoint ledger. Prior nineteen-run adoption retains its own historical-source limitations.')
s=s.replace('Exactly one new SUES contentseed1 run and eight height/direction tasks; eighteen prior runs/fifty-four tasks inherited by adoption SHA, no other evaluation accepted.', 'Exactly eleven new SUES runs and eighty-eight height/direction tasks; nineteen prior runs/sixty-two tasks inherited by adoption SHA, no visual_style/full or other evaluation accepted.')
s=s.replace('SUES_CONTENT_SEED1_EVALUATION_REVIEW.json','SUES_BATCH11_EVALUATION_REVIEW.json')
assert "targets = {('content',1)}" not in s
new=here/'review_sues_batch11.py'
new.write_text(s,encoding='utf-8',newline='\n')
(here/'REVIEW_SUES_BATCH11_SOURCE_DIFF.patch').write_text(''.join(difflib.unified_diff(base.splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(new))),encoding='utf-8',newline='\n')
print(new)
print(hashlib.sha256(new.read_bytes()).hexdigest())
