"""Derive single-run SUES review without importing scientific modules."""
from pathlib import Path
import hashlib
import difflib

here = Path(__file__).parent
old = here / 'review_batch6.py'
base = old.read_text(encoding='utf-8')
assert hashlib.sha256(old.read_bytes()).hexdigest() == '80bbbaf3f3f1c36ae9b6dfcf149bc2bb3ff64aede5c4e1bcb5275e37658d41f0'
s = base.replace('Fixed six new University visual_style/full evaluation runs.', 'Fixed SUES content seed1 evaluation; eight official height/direction tasks.')
s = s.replace('import os\n', 'import os\nimport re\n')
s = s.replace("DATA = Path(r'C:\\项目\\IMTMN\\datasets\\University-1652')", "DATA = Path(r'C:\\项目\\IMTMN\\datasets\\SUES-200')")
s = s.replace("('batch6_' + STAMP)", "('sues_content_seed1_' + STAMP)")
s = s.replace("'dataset': 'university1652', 'targets': [(v, s) for v in ('visual_style', 'full') for s in (1, 2, 3)], 'requested_evaluation_runs': 6, 'requested_retrieval_tasks': 18", "'dataset': 'sues200', 'targets': [('content', 1)], 'requested_evaluation_runs': 1, 'requested_retrieval_tasks': 8")
a=s.index("    previous_dir =")
b=s.index("    root42_path =",a)
s=s[:a]+'''    prior_path = HERE / 'ROOT_BATCH6_ADOPTION_20260929.json'
    prior_sha = 'c0735605a977e5ffcfd877e980a3773e9a747d4d7b4d68b9b682a0276f693fae'
    prior_eval = js(snapshot(prior_path, expected=prior_sha)[0])
    check(prior_eval['adopted_with_stated_inheritance_limits'] and prior_eval['accepted_total_evaluation_runs'] == 18 and prior_eval['accepted_total_retrieval_tasks'] == 54, 'Prior eighteen-run adoption invalid')
    report['previous_eval_adoption'] = {'path':str(prior_path),'sha256':prior_sha,'accepted_runs':18,'accepted_tasks':54,'old_evaluation_artifacts_rehashed':False}
    snapshot(HERE / 'review_batch6.py', expected='80bbbaf3f3f1c36ae9b6dfcf149bc2bb3ff64aede5c4e1bcb5275e37658d41f0')
    snapshot(HERE / 'REVIEW_SUES_CONTENT_SEED1_SOURCE_DIFF.patch')
''' + s[b:]
a=s.index("    # Specific later-trained")
b=s.index("    runner_path =",a)
s=s[:a]+'''    # This exact fit is a new_runs member of the adopted BATCH1611, not an initial inventory entry.
    training_source = documents['BATCH_COMPLETION_1611.json']
    check(training_source['batch_passed'], 'Adopted SUES training batch did not pass')
    training_entry = next(r for r in training_source['new_runs'] if r['run_identifier'] == 'formal_main/sues200/content/seed_1/resnet18/dim_512')
    check(training_entry['original_training_completion_issues'] == [] and training_entry['epochs_completed'] == 80 and training_entry['last_epoch'] == 79 and training_entry['optimizer_steps_each_epoch_from_original_config'] == 375, 'SUES content1 training completion')
    authority_reports = {('content',1):training_entry}
    authority_rows = {('content',1):{'report_path':str(EX / 'completion_audits_20260921/BATCH_COMPLETION_1611.json'),'report_sha256':'f88259d145316e76b36f63130800f2a47f91c0cbdf863fd9cabb2381bbca0bb2','historical_report_checkpoint_hashes_fresh_when_report_created':True,'independent_report':True,'exact_report_edge_verified_by_root42_chain':True}}
    report['specific_training_report_authorities'] = list(authority_rows.values())
    report['initial_inventory_not_used'] = True
''' + s[b:]
s=s.replace("targets = {(v, s) for v in ('visual_style', 'full') for s in (1, 2, 3)}", "targets = {('content',1)}")
s=s.replace("s.dataset == 'university1652'", "s.dataset == 'sues200'")
s=s.replace("len(specs) == 6", "len(specs) == 1").replace('Fixed six-run scope','Fixed SUES content1 scope')
s=s.replace("parent = js(snapshot(HERE / 'PRE_RECOVERY_PARENT_STATUS_20260929.json', 'PARENT_STATUS_RAW.json', expected='9990d0fe954a55f57673ba1498a30c1250b6c50fd1c4b935fa6f8c1df653bfed')[0])", "parent = js(snapshot(EX / 'status.json', 'PARENT_STATUS_RAW.json')[0])")
s=s.replace("frozen = ledger['frozen_inputs']['university1652']", "frozen = ledger['frozen_inputs']['sues200']")
s=s.replace("runner.DatasetSpec('university1652'", "runner.DatasetSpec('sues200'")
a=s.index("    check(len(evidence_paths)")
b=s.index("    membership_sha =",a)
s=s[:a]+'''    check(len(evidence_paths) == len(set(evidence_paths)) == 40200, 'SUES evidence paths rows/uniqueness')
    core_source = (PKG / 'lgm_game_pytorch/formal_retrieval.py').read_text(encoding='utf-8')
    constants = {}
    for node in ast.parse(core_source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('SUES_ALTITUDES','SUES_OFFICIAL_TRAIN_IDS','SUES_MANIFEST_SOURCE'):
                    constants[target.id] = ast.literal_eval(node.value)
    check(constants['SUES_ALTITUDES'] == ('150','200','250','300'), 'Frozen four SUES heights')
    sues_manifest_path = PKG / 'manifests/sues200_official_train_ids.yaml'
    sues_manifest_bytes, sues_binding = snapshot(sues_manifest_path, 'SUES_OFFICIAL_TRAIN_IDS_RAW.yaml', expected='c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226')
    train_ids = re.findall(r'^\\s*-\\s*["]([0-9]{4})["]\\s*$', sues_manifest_bytes.decode('utf-8'), flags=re.MULTILINE)
    check(tuple(train_ids) == constants['SUES_OFFICIAL_TRAIN_IDS'] and len(set(train_ids)) == 120, 'Exact original official fixed120 training IDs')
    all_ids = {f'{i:04d}' for i in range(1,201)}
    test_ids = all_ids - set(train_ids)
    check(len(test_ids) == 80, 'Official complementary80 test IDs')
    files = sorted(p for role in ('drone_view_512','satellite-view') for p in (DATA / role).rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png','.bmp','.webp'))
    relative = [p.relative_to(DATA).as_posix() for p in files]
    check(relative == sorted(evidence_paths), 'SUES actual filesystem/evidence full membership')
    metadata = [{'path':r,'bytes':p.stat().st_size} for r,p in zip(relative,files)]
    def label(path):
        parts = path.split('/')
        check(parts[0] in ('drone_view_512','satellite-view') and parts[1] in all_ids, 'SUES role/identity path')
        return parts[1]
    satellite_all = sorted(p for p in relative if p.startswith('satellite-view/'))
    check(len(satellite_all) == 200 and {label(p) for p in satellite_all} == all_ids, 'Full200 satellite gallery')
    satellite_query = [p for p in satellite_all if label(p) in test_ids]
    drone_paths = [p for p in relative if p.startswith('drone_view_512/')]
    check(all(re.sub(r'[^0-9]','',p.split('/')[2]) in constants['SUES_ALTITUDES'] for p in drone_paths), 'Unexpected SUES altitude')
    tasks=[]
    for altitude in constants['SUES_ALTITUDES']:
        drone_all = sorted(p for p in drone_paths if re.sub(r'[^0-9]','',p.split('/')[2]) == altitude)
        check(len(drone_all) == 10000 and {label(p) for p in drone_all} == all_ids, 'Full200 UAV gallery at '+altitude)
        check(all(sum(label(p) == identity for p in drone_all) == 50 for identity in all_ids), '50 UAV images per identity at '+altitude)
        drone_query = [p for p in drone_all if label(p) in test_ids]
        check(len(drone_query) == 4000 and len(satellite_query) == 80 and {label(p) for p in drone_query} == test_ids, 'Exact80 testquery identity membership')
        tasks.extend([
            {'name':f'sues200_uav_{altitude}m_to_satellite','protocol':'official 80 test IDs as query; all 200 satellite IDs in gallery','query':drone_query,'gallery':satellite_all},
            {'name':f'sues200_satellite_to_uav_{altitude}m','protocol':f'official 80 test IDs as query; all 200 {altitude}m UAV IDs in gallery','query':satellite_query,'gallery':drone_all},
        ])
    report['sues_official_protocol'] = {'manifest_binding':sues_binding,'original_frozen_core_constants_parsed_via_AST_without_import':True,'official_source_url':constants['SUES_MANIFEST_SOURCE'],'train_ids':train_ids,'test_ids':sorted(test_ids),'heights':list(constants['SUES_ALTITUDES']),'directions':['uav_to_satellite','satellite_to_uav'],'tasks':8,'all200_gallery_ids_retained':True}
''' + s[b:]
s=s.replace("artifacts = entry['verified_artifacts'] if (spec.variant,spec.seed) == ('visual_style',1) else entry['artifacts_sha256_verified']", "artifacts = entry['artifacts_sha256_verified']")
a=s.index("        if (spec.variant,spec.seed) == ('visual_style',1):")
b=s.index("        manifest_data, _ =",a)
s=s[:a]+'''        historical_manifest = entry['manifest_raw_snapshot']
        manifest_digest = historical_manifest['sha256']
        snapshot(historical_manifest['snapshot'], f'{spec.variant}_seed{spec.seed}/historical_manifest.json', expected=manifest_digest)
''' + s[b:]
s=s.replace("check(manifest['amp'] is True, 'Frozen evaluation AMP')", "check(manifest['amp'] is True, 'Frozen evaluation AMP')\n            check(manifest['sues_manifest']['sha256'] == sues_binding['sha256'] == config['immutable_config']['sues_manifest']['sha256'], 'SUES train/eval official split hash matches actual frozen manifest')\n            check(manifest['sues_manifest']['train_id_count'] == 120 and manifest['sues_manifest']['test_id_count'] == 80 and manifest['sues_manifest']['official_source_url'] == constants['SUES_MANIFEST_SOURCE'], 'SUES manifest provenance/counts')")
s=s.replace("len(artifact_records) == 7, 'Expected all seven evaluation artifacts'", "len(artifact_records) == 12, 'Expected all twelve SUES evaluation artifacts'")
s=s.replace("p.split('/')[2]", "label(p)") if False else s
# Replace the University label component only in the unchanged common per-query checking block.
a=s.index("            task_checks = []")
b=s.index("            events =",a)
part=s[a:b].replace("p.split('/')[2]", "label(p)").replace("g[i].split('/')[2]", "label(g[i])")
s=s[:a]+part+s[b:]
s=s.replace("[12564,7896,28100,18364,16816,31052]", "[20376]")
s=s.replace("'accepted_evaluation_run_count':6,'accepted_retrieval_task_count':18,'fresh_evaluation_artifact_count':42,'inherited_previous_evaluation_run_count':12,'inherited_previous_retrieval_task_count':36,'accepted_total_evaluation_run_count_with_this_batch':18,'accepted_total_retrieval_task_count_with_this_batch':54", "'accepted_evaluation_run_count':1,'accepted_retrieval_task_count':8,'fresh_evaluation_artifact_count':12,'inherited_previous_evaluation_run_count':18,'inherited_previous_retrieval_task_count':54,'accepted_total_evaluation_run_count_with_this_batch':19,'accepted_total_retrieval_task_count_with_this_batch':62")
s=s.replace("Visual_style seed1 original Sep14 whole-report historical SHA edge was not found; currently bound report is corroboration. Accepted ROOT42 identifier and adopted Sep22 ledger supply inherited checkpoint authority. Other five specific reports have verified historical root/chain edges.", "This SUES fit has a specific original completion report reached by the adopted ROOT42 chain and matches adopted Sep22 checkpoint ledger. Prior eighteen-run adoption retains its own historical-source limitations.")
s=s.replace("Exactly six new runs, eighteen new tasks; twelve prior runs/thirty-six prior tasks inherited by adoption SHA, no other evaluation accepted.", "Exactly one new SUES contentseed1 run and eight height/direction tasks; eighteen prior runs/fifty-four tasks inherited by adoption SHA, no other evaluation accepted.")
s=s.replace("BATCH6_EVALUATION_REVIEW.json", "SUES_CONTENT_SEED1_EVALUATION_REVIEW.json")
assert "s.dataset == 'university1652'" not in s and "inventory['runs']" not in s
new=here/'review_sues_content_seed1.py'
new.write_text(s,encoding='utf-8',newline='\n')
(here/'REVIEW_SUES_CONTENT_SEED1_SOURCE_DIFF.patch').write_text(''.join(difflib.unified_diff(base.splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(new))),encoding='utf-8',newline='\n')
print(new)
print(hashlib.sha256(new.read_bytes()).hexdigest())
