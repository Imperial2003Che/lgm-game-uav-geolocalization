"""Prepare the fixed Full audit from SHA-pinned accepted Visual sources; no science execution."""
import ast, difflib, hashlib, json
from pathlib import Path

HERE=Path(__file__).parent
BASE=HERE.parent/'robustness_audit_20260929_0946'
bindings=[]
for name,digest in [('review_visual1.py','5ee21f317aab75ef700115ed7f25faa958109b28338f5010591f1bfff9b375c0'),('review_visual1_addendum.py','c1bb9c85e22493f83246d2125f7066a32c8af46864bf6d39218fcd7c5c35a89b')]:
    data=(BASE/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest
    bindings.append(dict(path=str(BASE/name),sha256=digest,bytes=len(data)))
source=(BASE/'review_visual1.py').read_text(encoding='utf-8')
original=source
def change(old,new,count=1):
    global source
    assert source.count(old)==count,(old,source.count(old),count)
    source=source.replace(old,new)

change('University visual seed1','University full seed1')
change('university1652/visual/seed_1','university1652/full/seed_1',4)
change("'bounded-university-visual1-robustness-review-v1'","'bounded-university-full1-robustness-review-v1'")
change("'ROOT_BATCH10_ADOPTION_20260928.json'","'ROOT_BATCH6_ADOPTION_20260929.json'")
change("    report['inherited_authority']=dict(root=rootbind",'''    authority=prior['source_training_authority']
    training,trainbind=snap(authority['report_path'],expected=authority['report_sha256'])
    root_training,trb=snap(authority['historical_root_adoption']['path'],expected=authority['historical_root_adoption']['sha256'])
    check(root_training['accepted'] and root_training['audit_sha256']==trainbind['sha256'] and norm(root_training['audit_path'])==norm(trainbind['path']),'Full own root-to-training-report edge')
    check(training['passed'] and training['run_identifier']==prior['source_training_identifier'] and training['epochs_completed']==80 and training['original_training_completion_issues']==[],'Full own accepted training scope')
    accepted_best=training['artifacts_sha256_verified']['best.pt']
    check(accepted_best['sha256']==prior['inherited_checkpoint_SHA'] and accepted_best['bytes']==prior['checkpoint_stat_only']['bytes'],'Full historically fresh best.pt authority')
    check(officialrun['inherited_checkpoint_SHA']['specific_training_authority']==authority and officialrun['inherited_checkpoint_SHA']['specific_historical_artifact']==accepted_best,'Full official and T3 exact specific training authority agreement')
    official_root,orb=snap(official_ref['parent'],expected='c0735605a977e5ffcfd877e980a3773e9a747d4d7b4d68b9b682a0276f693fae')
    check(official_root['adopted_with_stated_inheritance_limits'] and official_root['independent_report']['sha256']==officialbind['sha256'],'Specific Full official root/report edge')
    report['specific_training_source_bindings']=dict(report=trainbind,root=trb,official_root=orb)
    report['inherited_authority']=dict(root=rootbind''')
change("limitation='Exact prior accepted source authority is inherited. Original initial12 inventory historical whole-file SHA edge remains missing. Current weight bytes are not proven by stat.'", "limitation='Full uses its own accepted Sep20 independent training artifact report and root edge, then exact BATCH6 official/T3 authority. The earlier initial12 inventory historical whole-file SHA gap elsewhere in the global chain is retained; it is not the authority for this Full checkpoint. Current weight bytes are not proven by stat.'")
change("    check(attempt['stderr']['bytes']==0,'Finished run stderr is not empty')", "    check(attempt['stderr']['bytes']==325 and attempt['stderr']['sha256']=='939bd35cd671fbdb659d92ea4ee845dd030ef5930dbcf00ef8b97d4cd299d146','Full closed stderr is the exact recorded slow-processor diagnostic')")
change('snapshot_20260929_094528494','snapshot_20260929_124603856')
change('d266ea69c29a212c982662c631bd1452ba1d4cc54887a91814018750544137e0','5d0667518c128d8ec26b97ad5de980c30743451c3c6e262d1bf75317c2730aa1')
change('@(27888,41564)','@(40820,43872)')
change("creation_utc=$_.CreationDate.ToUniversalTime().ToString('o');command", "creation_utc=$_.CreationDate.ToUniversalTime().ToString('o');creation_ticks=$_.CreationDate.ToUniversalTime().Ticks.ToString();command")
change("    report['old_worker_CIM_observation']=json.loads(cps.stdout);check(not report['old_worker_CIM_observation']['matches'],'Old worker PID number currently exists; identity review required')",'''    report['old_worker_CIM_observation']=json.loads(cps.stdout)
    old_ticks={40820:'639262647697707190',43872:'639262647698144490'}
    for row in report['old_worker_CIM_observation']['matches']:
        check(row['creation_ticks']!=old_ticks[row['pid']],'Original Full worker identity still exists; review required')
    report['old_worker_CIM_observation']['original_identity_ticks']=old_ticks
    report['old_worker_CIM_observation']['interpretation']='Original Full identities absent; any same numeric PID with different exact UTC ticks is a reused process. No historical dual-handle exit code is inferred.' ''')
change('51edb3f929b337ec3c129ad502336a5f5676ef15fbd606d760526b04a2dbfbd0','c7bfc6c41ccadf0f52cf79609a76ef921bf456c5d06334b78ece284a5b4c9ce1')
change("    check(cp.stat().st_size==prior['checkpoint_stat_only']['bytes'],'Checkpoint size matches prior adopted source metadata')", "    check(cp.stat().st_size==prior['checkpoint_stat_only']['bytes'] and os.path.samefile(cp,accepted_best['path']),'Full checkpoint exists, same file as own accepted artifact, size matches inherited metadata')")
change("        snap(evidence['meta_path'],expected=evidence['meta_sha256'])\n    check(manifest['clip_clean_reproduction_audit'] is None,'Visual variant does not use CLIP branch')",'''        cachemeta,cachemetabind=snap(evidence['meta_path'],expected=evidence['meta_sha256'])
    clip=json.loads((TREE/'clip_clean_reproduction_audit.json').read_text(encoding='utf-8-sig'))
    check(clip==manifest['clip_clean_reproduction_audit'],'Full diagnostic manifest/sidefile exact binding')
    check(canonical({k:v for k,v in clip.items() if k!='payload_sha256'})==clip['payload_sha256']=='d8788767a0bd22ef51e0b2a81218b762c5ede896e1668991caa9626b833db10c','Full diagnostic canonical payload')
    check(sha(TREE/'clip_clean_reproduction_audit.json')=='47b9e945ddb892048fa1fbcd0c5de69e89a5bb30b4809171ffa12fc5fcfd5c94','Pinned completed Full diagnostic bytes')
    check(clip['samples']==imm['encoding']['clip_clean_audit_samples']==64 and clip['selection_seed']==20260727 and clip['schema_version']==imm['schema_version'],'Full diagnostic scope/seed/schema')
    prov=clip['clip_provenance']
    check(prov['model_name']==cachemeta['model']['name']=='openai/clip-vit-base-patch32','Diagnostic/cache model')
    check(prov['revision']==prov['loaded_revision']==cachemeta['model']['revision_requested']==cachemeta['model']['revision_resolved']=='3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268','Diagnostic/cache fixed revision')
    check(prov['precision']==cachemeta['hardware']['precision']==cachemeta['run_configuration']['precision']=='fp16' and prov['local_files_only'] is True,'Match-cache actual fp16 declaration')
    for key in ('model_config_sha256','combined_candidates_sha256'):
        check(prov[key]==cachemeta['hashes'][key],'Diagnostic/cache provenance '+key)
    check(prov['probability_semantics']==cachemeta['probability_semantics'] and prov['transformers_version']==cachemeta['software']['transformers'],'Diagnostic/cache semantics/software declaration')
    for family in ('content','style'):
        vals=clip[family]
        check(set(vals)=={'mean_absolute_error','max_absolute_error','float16_exact_fraction'} and all(math.isfinite(x) for x in vals.values()),'Diagnostic numeric fields')
        check(0<=vals['mean_absolute_error']<=vals['max_absolute_error'] and 0<=vals['float16_exact_fraction']<=1,'Diagnostic structural ranges, not an acceptance threshold')
    report['full_clip_diagnostic']=dict(payload=clip,cache_metadata=cachemetabind,canonical_verified=True,
        sidefile_and_top_manifest_equal=True,numerical_error_recomputed=False,tolerance_gate_exists=False,
        limitation='Only producer diagnostic structure/provenance/sample-path binding is checked. No CLIP rerun or cached/online equivalence test. Clean evidence is cached while corrupted evidence is recomputed online; differences cannot be attributed solely to corruption.')''')
change("    check(len(querypaths)==41135 and len(gallerypaths)==52306,'Query/gallery union counts')",'''    check(len(querypaths)==41135 and len(gallerypaths)==52306,'Query/gallery union counts')
    auditpaths=sorted(querypaths,key=lambda p:hashlib.sha256(('20260727'+chr(0)+p).encode('utf-8')).hexdigest())[:64]
    check(canonical(auditpaths)==clip['sample_path_membership_sha256']=='039390fb104e00f586bf5a4858aa24675e2cd03f973c53588b2ec90f1e2bac13','Original deterministic CLIP diagnostic query-path sample membership')
    report['full_clip_diagnostic']['sample_paths']=auditpaths
    report['full_clip_diagnostic']['sample_path_selection_checked_without_image_bytes']=True''')
change("    evaluator=namespace('robustness_conditions_only'",'''        check(coverage['embedding_dim']==512 and coverage['embedding_storage_dtype_for_hash']=='little-endian float32' and coverage['query_content_style_evidence_mode']=='clean_cache','Complete clean coverage dtype/evidence path')
        check(re.fullmatch('[0-9a-f]{64}',coverage['encoded_feature_sha256']) is not None and coverage['elapsed_seconds']>=0,'Clean coverage declared feature hash/time')
    clean_manifest=json.loads((TREE/'clean/condition_manifest.json').read_text(encoding='utf-8-sig'))
    check(clean_manifest['query_coverage']==manifest['clean_query_coverage'],'Exact clean condition/top query coverage identity')
    evaluator=namespace('robustness_conditions_only' ''')
change("('university1652','visual',DATA", "('university1652','full',DATA")
change("    check(set(reader.fieldnames)==set(expected[0]) and (fields is None or reader.fieldnames==fields),'CSV columns '+str(path))", "    check(fields is not None and reader.fieldnames==fields and len(reader.fieldnames)==len(set(reader.fieldnames)) and set(reader.fieldnames)==set(expected[0]),'Exact ordered unique CSV columns '+str(path))")
change("def csv_check(path,expected,fields=None):",'''METRIC_FIELDS=['task','queries','gallery','query_identities','gallery_identities','r_at_1','r_at_5','r_at_10','r_at_20','official_trapezoid_mAP','MRR','mean_top1_margin','protocol']
DROP_FIELDS=['task','metric','clean','corrupted','absolute_drop_fraction','percentage_point_drop','relative_drop_fraction','relative_drop_percent']
SUMMARY_FIELDS=['corruption','severity_index','parameter','value','units']+DROP_FIELDS
def csv_check(path,expected,fields=None):''')
change("        cov=cm['query_coverage'];check(cov['path_membership_sha256']==canonical(querypaths),'Per-condition query union hash')",'''        check(metrics['unit']=='fraction' and metrics['AP_definition']=='Official trapezoidal interpolation used by the University-1652/SUES reference evaluator.','Top-level metric fraction/AP semantics')
        cov=cm['query_coverage'];check(cov['path_membership_sha256']==canonical(querypaths),'Per-condition query union hash')
        check(cov['query_content_style_evidence_mode']==('recomputed_from_corrupted_rgb_pixels' if corrupted else 'clean_cache') and cov['corruption_applied_before_all_model_preprocessing'] is corrupted,'Full clean-cache / corrupt-online pixel pathway declarations')
        check(cov['elapsed_seconds']>=0,'Condition encoded elapsed time declaration')''')
change("                check(a.dtype.kind==kind,'Array dtype kind '+key)",'''                check(a.dtype.kind==kind,'Array dtype kind '+key)
                if kind=='i':check(a.descr==('|i1' if key=='top1_correctness_transition_corrupted_minus_clean' else '<i8'),'Exact producer integer dtype '+key)
                if kind=='b':check(a.descr=='|b1','Exact producer boolean dtype '+key)''')
change("csv_check(d/'metrics.csv',ordered_metrics)","csv_check(d/'metrics.csv',ordered_metrics,METRIC_FIELDS)")
change("csv_check(d/'degradation_vs_clean.csv',degradation_rows)","csv_check(d/'degradation_vs_clean.csv',degradation_rows,DROP_FIELDS)")
change("csv_check(TREE/'robustness_summary.csv',all_summary)","csv_check(TREE/'robustness_summary.csv',all_summary,SUMMARY_FIELDS)")
change("    report.update(passed_with_stated_limits=True", "    check(not any(m in sys.modules for m in ('numpy','torch','pandas','scipy','PIL','matplotlib')),'No scientific modules imported')\n    report.update(passed_with_stated_limits=True")
change("'Checkpoint bytes/state and full evidence/image content not re-read; exact inherited accepted SHA does not prove current bytes. University visual initial12 inventory historical whole-file SHA edge gap remains.'", "'Checkpoint bytes/state and full evidence/image content not re-read; exact inherited accepted SHA does not prove current bytes. Full has its own historical independent training artifact report/root edge; initial12 inventory historical whole-file SHA gaps elsewhere in the global history remain and are not silently repaired.'")
change("'Visual variant only: CLIP clean reproduction audit is null and corrupted query evidence not_used_by_visual_variant. No Full-variant corruption claim is established by this run.'", "'Full64-sample CLIP diagnostic has no original numerical tolerance gate. Bound numerical errors are producer observations, not independent remeasurement, bitwise equivalence or a calibrated probability test. Clean cached evidence versus corrupted online CLIP mixes evidence-path and pixel-corruption effects; this is not a pure-corruption estimate or full-dataset onlineCLIP accuracy/efficiency measurement.'")
change("'Only seed1 visual at one dataset is accepted; no across-seed robustness inference, comparison with unfinished Full, or whole4-run pipeline completion.'", "'Only seed1 Full at University is accepted; no across-seed robustness SD/significance or whole4-run pipeline completion. No SUES result is included.'")

assert 'university1652/visual' not in source and "'university1652','visual'" not in source
assert 'clip_clean_reproduction_audit\'] is None' not in source
ast.parse(source)
out=HERE/'review_full1.py'
with out.open('x',encoding='utf-8',newline='\n') as f:f.write(source)
patch=''.join(difflib.unified_diff(original.splitlines(keepends=True),source.splitlines(keepends=True),fromfile=str(BASE/'review_visual1.py'),tofile=str(out)))
with (HERE/'FULL_FROM_VISUAL_SOURCE_DIFF.patch').open('x',encoding='utf-8',newline='\n') as f:f.write(patch)
bindings.append(dict(path=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bytes=out.stat().st_size))
with (HERE/'DERIVATION.json').open('x',encoding='utf-8') as f:json.dump(dict(source_bindings=bindings,original_scientific_sources_modified=False,integrated_addendum=['complete clean coverage','CSV exact ordered unique columns','producer integer/bool dtype','fraction/AP semantics','no scientific modules assert'],diff=dict(path=str(HERE/'FULL_FROM_VISUAL_SOURCE_DIFF.patch'),sha256=hashlib.sha256(patch.encode()).hexdigest())),f,indent=2)
print(json.dumps(bindings,ensure_ascii=True))
