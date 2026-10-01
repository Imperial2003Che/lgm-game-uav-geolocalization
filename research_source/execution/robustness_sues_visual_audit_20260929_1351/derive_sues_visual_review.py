"""Derive fixed SUES Visual1 review from the accepted integrated Full source, without executing science."""
import ast, difflib, hashlib, json
from pathlib import Path

HERE=Path(__file__).parent
BASE=HERE.parent/'robustness_full_audit_20260929_1247'
parent=BASE/'review_full1.py'
raw=parent.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='e12125299612df0d68765b0ad744904a22015edd76a85b48a60759f3b3715d96'
source=raw.decode('utf-8');original=source
def change(old,new,count=1):
    global source
    assert source.count(old)==count,(old,source.count(old),count)
    source=source.replace(old,new)
def section(start,end,new):
    global source
    assert source.count(start)==source.count(end)==1,(start,end)
    a=source.index(start);b=source.index(end,a)
    source=source[:a]+new+source[b:]

change('University full seed1','SUES visual seed1')
change("datasets\\University-1652'", "datasets\\SUES-200'")
change('university1652/full/seed_1','sues200/visual/seed_1',4)
change("'bounded-university-full1-robustness-review-v1'","'bounded-sues-visual1-robustness-review-v1'")
change('corrupted_tasks=90,clean_tasks=3','corrupted_tasks=240,clean_tasks=8')
change("'ROOT_BATCH6_ADOPTION_20260929.json'","'ROOT_SUES_BATCH11_ADOPTION_20260929.json'")
section("    authority=prior['source_training_authority']", "    report['inherited_authority']=dict", '''    authority=prior['source_training_authority']
    training_batch,trainbind=snap(authority['report_path'],expected=authority['report_sha256'])
    check(training_batch['batch_passed'],'Specific adopted SUES training batch passed')
    entries=[r for r in training_batch['new_runs'] if r['run_identifier']==prior['source_training_identifier']]
    check(len(entries)==1,'Exactly one SUES Visual1 training authority member')
    training=entries[0]
    check(training['epochs_completed']==80 and training['last_epoch']==79 and training['original_training_completion_issues']==[] and training['optimizer_steps_each_epoch_from_original_config']==375,'SUES Visual1 accepted original 80x375 training completion')
    accepted_best=training['artifacts_sha256_verified']['best.pt']
    check(accepted_best['sha256']==prior['inherited_checkpoint_SHA'] and accepted_best['bytes']==prior['checkpoint_stat_only']['bytes'],'SUES Visual1 historically fresh best.pt authority')
    check(officialrun['inherited_checkpoint_SHA']['specific_training_authority']==authority and officialrun['inherited_checkpoint_SHA']['specific_historical_artifact']==accepted_best,'SUES official and T3 exact specific training authority agreement')
    official_root,orb=snap(official_ref['parent'],expected='657968ef1cf457bdc0b052c45cd0b2fd4f22dc687dc012d6f8482286e1fb052b')
    check(official_root['adopted_with_stated_inheritance_limits'] and official_root['independent_report']['sha256']==officialbind['sha256'],'Specific SUES official root/report edge')
    # Rebind only the small adopted ancestry needed for this specific training report.
    # This does not hash any old training weights or old official per-query artifacts.
    graph={norm(g['to_document']):g for g in official['inherited_training_acceptance_graph']}
    edge=graph[norm(trainbind['path'])];ancestry=[];seen=set()
    def has_ref(obj,path,digest):
        if isinstance(obj,dict):
            vals=list(obj.values())
            if digest in vals and any(isinstance(v,str) and v.lower().endswith('.json') and norm(v)==norm(path) for v in vals):return True
            return any(has_ref(v,path,digest) for v in vals if isinstance(v,(dict,list)))
        return isinstance(obj,list) and any(has_ref(v,path,digest) for v in obj)
    while True:
        check(edge['sha256']==(trainbind['sha256'] if not ancestry else edge['sha256']) and norm(edge['to_document']) not in seen,'Unique accepted ancestry node')
        seen.add(norm(edge['to_document']));ancestry.append(edge)
        parent_path=edge['from_document']
        if parent_path is None:
            check(Path(edge['to_document']).name=='ROOT_FIT_42_ADOPTION_20260928.json' and edge['sha256']=='ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87','Exact ROOT42 ancestry anchor')
            break
        parent_edge=graph[norm(parent_path)]
        parent_doc,parent_binding=snap(parent_path,expected=parent_edge['sha256'])
        check(has_ref(parent_doc,edge['to_document'],edge['sha256']),'Actual parent JSON contains precise path/SHA ancestry edge')
        edge=parent_edge
    report['specific_training_source_bindings']=dict(report=trainbind,official_root=orb,root42_ancestry=ancestry)
''')
change("limitation='Full uses its own accepted Sep20 independent training artifact report and root edge, then exact BATCH6 official/T3 authority. The earlier initial12 inventory historical whole-file SHA gap elsewhere in the global chain is retained; it is not the authority for this Full checkpoint. Current weight bytes are not proven by stat.'", "limitation='SUES Visual1 uses its own accepted Sep21 BATCH_COMPLETION_1611 member reached by actual ROOT42 ancestry, then specific SUES batch11 official/T3 authority. Historical initial12/visual_style1 whole-file SHA gaps elsewhere in the global chain are retained, not used as this checkpoint authority. Current weight bytes are not proven by stat.'")
change("    check(attempt['stderr']['bytes']==325 and attempt['stderr']['sha256']=='939bd35cd671fbdb659d92ea4ee845dd030ef5930dbcf00ef8b97d4cd299d146','Full closed stderr is the exact recorded slow-processor diagnostic')", "    check(attempt['stderr']['bytes']==0,'Completed SUES Visual stderr is empty')")
change('snapshot_20260929_124603856','snapshot_20260929_135047460')
change('5d0667518c128d8ec26b97ad5de980c30743451c3c6e262d1bf75317c2730aa1','e5c4d484bdb7e703b373863b60fb02cdd3f372bf307559f0d00df96a5bc9d950')
change('@(40820,43872)','@(24428,40060)')
change("old_ticks={40820:'639262647697707190',43872:'639262647698144490'}", "old_ticks={24428:'639262775229496270',40060:'639262775229943530'}")
change('Original Full worker identity','Original SUES Visual worker identity')
change('Original Full identities absent','Original SUES Visual identities absent')
change('c7bfc6c41ccadf0f52cf79609a76ef921bf456c5d06334b78ece284a5b4c9ce1','d19283877ee9967fc36ca82155564cdc5945a44f7633273e119a661bf684f6d9')
change('Full checkpoint exists, same file as own accepted artifact','SUES Visual checkpoint exists, same file as own accepted artifact')
change('8a2333d58dbb0ca56c5d5829159a32f294e11e686bb6b91d05098d4b170c2bc3','6c3a82fdcf59e401f5da4ed0f3d9dca99fdcbab0a46aa66fb47a055c832cdabd')
section("    clip=json.loads((TREE/'clip_clean_reproduction_audit.json')", "    corepath=source_table['core'][0]", '''    check(manifest['clip_clean_reproduction_audit'] is None,'SUES Visual intentionally does not initialize online CLIP')
    check('clip_clean_reproduction_audit.json' not in artifacts,'SUES Visual has no Full CLIP diagnostic artifact')

''')
section("    paths=[]\n", "    check(canonical(querypaths)==imm['query_path_membership_sha256']", '''    paths=[]
    for role in ('drone_view_512','satellite-view'):
        for p in (DATA/role).rglob('*'):
            if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png','.bmp','.webp'):paths.append(p.relative_to(DATA).as_posix())
    paths.sort();check(len(paths)==40200 and len(set(p.casefold() for p in paths))==40200,'Exact SUES full image path union')
    check(paths==[core['normalized_relative_path'](p) for p in paths],'Directory paths already normalized')
    sm=imm['sues_manifest']
    manifest_bytes,suesbind=snap(sm['path_or_source'],'SUES_OFFICIAL_TRAIN_IDS_RAW.yaml',expected='c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226')
    train_ids=re.findall(r'^\\s*-\\s*["]([0-9]{4})["]\\s*$',manifest_bytes.decode('utf-8'),flags=re.MULTILINE)
    check(tuple(train_ids)==core['SUES_OFFICIAL_TRAIN_IDS'] and len(set(train_ids))==120,'Exact ordered original 120 SUES training IDs')
    check(tuple(core['SUES_ALTITUDES'])==('150','200','250','300') and sm['sha256']==suesbind['sha256'] and sm['official_source_url']==core['SUES_MANIFEST_SOURCE'] and sm['train_id_count']==120 and sm['test_id_count']==80,'Four official heights and fixed manifest declaration')
    all_ids={f'{i:04d}' for i in range(1,201)};test_ids=all_ids-set(train_ids)
    check(len(test_ids)==80,'Official complementary 80 test IDs')
    records=core['derive_all_records'](types.SimpleNamespace(paths=paths),DATA,'sues200')
    check(len(records)==40200,'All SUES directory images belong to supported roles')
    tasks=core['build_official_evaluation_tasks'](records,'sues200',train_ids)
    check(len(tasks)==8 and core['protocol_membership_hash'](tasks)==imm['protocol_membership_sha256']=='1f543fb48416204dacfb5ac48b3bbf3ce4080ce164e75e7a86be748e3d798772','Exact SUES eight-task membership')
    for altitude in core['SUES_ALTITUDES']:
        forward=next(t for t in tasks if t.name==f'sues200_uav_{altitude}m_to_satellite')
        reverse=next(t for t in tasks if t.name==f'sues200_satellite_to_uav_{altitude}m')
        check((len(forward.query),len(forward.gallery),len(reverse.query),len(reverse.gallery))==(4000,200,80,10000),'Exact SUES direction scales')
        check({r.label for r in forward.query}=={r.label for r in reverse.query}==test_ids and {r.label for r in forward.gallery}=={r.label for r in reverse.gallery}==all_ids,'All 80 query IDs/all 200 gallery IDs retained')
        check(all(r.altitude==altitude and r.view=='drone' for r in forward.query+reverse.gallery),'Exact altitude and UAV role')
        check(all(r.view=='satellite' for r in forward.gallery+reverse.query),'Exact satellite role')
        counts=defaultdict(int)
        for rec in reverse.gallery:counts[rec.label]+=1
        check(set(counts)==all_ids and set(counts.values())=={50},'Each altitude has 50 UAV images per each of 200 IDs')
    pathfile=save('OFFICIAL_TEST_DIRECTORY_PATHS.json',json.dumps(paths,ensure_ascii=False).encode())
    report['directory_membership']=dict(path=str(pathfile),sha256=sha(pathfile),count=len(paths),image_bytes_read=False,source='Image directory-entry metadata from both official SUES roles; original pure core task builder.')
    report['sues_official_protocol']=dict(manifest=suesbind,train_ids=train_ids,test_ids=sorted(test_ids),heights=list(core['SUES_ALTITUDES']),tasks=8,all_200_gallery_ids_retained=True)
    querypaths=sorted({r.relative_path for t in tasks for r in t.query});gallerypaths=sorted({r.relative_path for t in tasks for r in t.gallery})
    check(len(querypaths)==16080 and len(gallerypaths)==40200 and set(querypaths)<=set(gallerypaths),'SUES query/gallery union counts and containment')
''')
change("('university1652','full',DATA","('sues200','visual',DATA")
change("cov['query_content_style_evidence_mode']==('recomputed_from_corrupted_rgb_pixels' if corrupted else 'clean_cache')", "cov['query_content_style_evidence_mode']==('not_used_by_visual_variant' if corrupted else 'clean_cache')")
change('Full clean-cache / corrupt-online pixel pathway declarations','SUES Visual clean/corrupt visual-only pixel pathway declarations')
change("len(task_reviews)==93 and len(all_summary)==540,'Fixed 93 tasks / 540 degradation records'", "len(task_reviews)==248 and len(all_summary)==1440,'Fixed 248 tasks / 1440 degradation records'")
change('accepted_corrupted_tasks=90,accepted_clean_tasks=3','accepted_corrupted_tasks=240,accepted_clean_tasks=8')
change('summary_rows=540','summary_rows=1440')
change("'Checkpoint bytes/state and full evidence/image content not re-read; exact inherited accepted SHA does not prove current bytes. Full has its own historical independent training artifact report/root edge; initial12 inventory historical whole-file SHA gaps elsewhere in the global history remain and are not silently repaired.'", "'Checkpoint bytes/state and full evidence/image content not re-read; exact inherited accepted SHA does not prove current bytes. SUES Visual1 has its own historical independent Sep21 batch member reached by ROOT42 ancestry. Historical initial12/visual_style1 whole-file SHA gaps elsewhere remain and are not silently repaired.'")
change("'Full64-sample CLIP diagnostic has no original numerical tolerance gate. Bound numerical errors are producer observations, not independent remeasurement, bitwise equivalence or a calibrated probability test. Clean cached evidence versus corrupted online CLIP mixes evidence-path and pixel-corruption effects; this is not a pure-corruption estimate or full-dataset onlineCLIP accuracy/efficiency measurement.'", "'SUES Visual intentionally skips online CLIP and has null clean reproduction audit. This does not establish any Full cached/online equivalence, Full corruption result or full-dataset onlineCLIP accuracy/efficiency.'")
change("'Only seed1 Full at University is accepted; no across-seed robustness SD/significance or whole4-run pipeline completion. No SUES result is included.'", "'Only SUES Visual seed1 is accepted; no across-seed robustness SD/significance or whole4-run pipeline completion. No SUES Full result is included.'")
assert 'university1652/full/seed_1' not in source and "('university1652','full'" not in source
assert "len(task_reviews)==248" in source and 'accepted_corrupted_tasks=240' in source
ast.parse(source)
output=HERE/'review_sues_visual1.py'
with output.open('x',encoding='utf-8',newline='\n') as f:f.write(source)
patch=''.join(difflib.unified_diff(original.splitlines(keepends=True),source.splitlines(keepends=True),fromfile=str(parent),tofile=str(output)))
dp=HERE/'SUES_VISUAL_FROM_FULL_SOURCE_DIFF.patch'
with dp.open('x',encoding='utf-8',newline='\n') as f:f.write(patch)
def binding(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
with (HERE/'DERIVATION.json').open('x',encoding='utf-8') as f:json.dump(dict(parent_source=binding(parent),source=binding(output),diff=binding(dp),scientific_sources_unchanged=True,scope='Only SUES Visual seed1 robustness; official four heights/eight directions and own Sep21 adopted training authority; integrated prior coverage/dtype/CSV checks retained'),f,indent=2)
print(json.dumps(dict(source=binding(output),diff=binding(dp)),ensure_ascii=True))
