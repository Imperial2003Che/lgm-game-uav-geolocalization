"""Adopt and package the actually compiled format-only local working draft; no science release."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,zipfile,zlib,re

HERE=Path(__file__).resolve().parent
EX=HERE.parent
OUT=EX.parent
NEW=OUT/'manuscript_reference_format_20260930_1538'
DRAFT=NEW/'manuscript'
PEER=EX/'manuscript_reference_format_review_20260930_1538'
OBS=EX/'continuation_observation_20260930_153427732'
PARENT_PREVIEW=EX/'manuscript_citation_revision_20260930_0520/preview_1'
cache={}
def raw(p,cap=32*1024*1024):
    p=Path(p).resolve()
    if p not in cache:
        n=p.stat().st_size;assert 0<=n<=cap,str(p)
        with p.open('rb') as f: b=f.read(cap+1)
        assert len(b)==n and len(b)<=cap,str(p)
        cache[p]=b
    return cache[p]
def bind(p):
    p=Path(p).resolve();b=raw(p)
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def verify(d): assert bind(d['path'])==d,d['path']
def read(p): return json.loads(raw(p,256*1024))
def save(p,value):
    b=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    with p.open('xb') as f: f.write(b);f.flush();os.fsync(f.fileno())
    cache[p.resolve()]=b
    return bind(p)

revision=read(HERE/'REFERENCE_FORMAT_REVISION.json')
dependency=read(HERE/'SUPPLEMENT_DEPENDENCY_ADDENDUM.json')
peer=read(PEER/'INDEPENDENT_FORMAT_REVIEW.json')
supp_peer=read(PEER/'INDEPENDENT_SUPPLEMENT_FORMAT_ADDENDUM.json')
assert peer['status']=='source_delta_and_bbl_preservation_pass'
assert peer['bbl_comparison']['new_main_bibitem_count']==42
assert peer['changed_journal_fields']==17 and peer['bibtex_entries_after']==52
assert supp_peer['status']=='pass'
verify(revision['parent_root']);verify(revision['parent_external_addendum'])
verify(revision['new_refs']);verify(dependency['preserved_inherited_PDF'])
unchanged_sources=[]
for item in revision['inherited_copies']:
    if item['relative']=='supplementary.pdf':
        assert item['inherited_parent']['sha256']==dependency['preserved_inherited_PDF']['sha256']
        continue
    verify(item['new_copy'])
    assert item['new_copy']['sha256']==item['inherited_parent']['sha256']
    assert item['new_copy']['bytes']==item['inherited_parent']['bytes']
    unchanged_sources.append(item['new_copy'])
assert len(unchanged_sources)==31
compiles=[read(HERE/'compile_1/COMPILE.json'),read(HERE/'supplement_compile_1/COMPILE.json')]
for c in compiles:
    assert c['status']=='compiled' and c['input_texts_unchanged'] is True
    assert c['compiler_installer_disabled'] is True and c['shell_escape_disabled'] is True
    assert len(c['commands'])==4 and all(x['exit_code']==0 for x in c['commands'])
    for x in c['commands']:verify(x['log'])
    for d in c['outputs']:verify(d)

layout_paths=[HERE/'preview_1/PDF_LAYOUT.json',HERE/'supplement_preview_1/PDF_LAYOUT.json']
pages=[];layouts=[]
for lp,expected_count in zip(layout_paths,[16,6]):
    layout=read(lp)['documents'][0];verify(layout['pdf'])
    assert layout['page_count']==expected_count
    assert all(not p['out_of_page_spans'] and p['unresolved_double_question_marks']==0 for p in layout['pages'])
    assert not any(any(w in line for w in ['Overfull','undefined','Undefined','Warning:']) for line in layout['latex_diagnostics'])
    for p in layout['pages']:
        verify(p['png'])
        old=PARENT_PREVIEW/Path(p['png']['path']).name
        before=bind(old)
        same=before['sha256']==p['png']['sha256']
        expected_same=p['number']<expected_count
        assert same==expected_same,(str(lp),p['number'])
        pages.append({'document':Path(layout['pdf']['path']).stem,'page':p['number'],
            'new_png':p['png'],'parent_png':before,'exact_preview_bytes_unchanged':same,
            'root_actual_original_image_review_this_turn':not same,
            'review':('Root AI actually viewed original-resolution preview: all references visible, legible, no clipping or overlap.' if not same else 'Exact unchanged PNG; prior adopted visual review inherited, not repeated.')})
    layouts.append(layout)
assert sum(x['exact_preview_bytes_unchanged'] for x in pages)==20
assert sum(x['root_actual_original_image_review_this_turn'] for x in pages)==2
visual=save(HERE/'ROOT_VISUAL_REVIEW.json',{'schema':'root-format-draft-visual-review.v1','utc':datetime.now(timezone.utc).isoformat(),
    'method':'Root AI tool image review, not a human reviewer. Two changed pages actually viewed original resolution; twenty unchanged PNGs identified by exact SHA.',
    'pages':pages,'main_pages':16,'supplementary_pages':6,'orphan_AQE_page_removed':True,
    'source_font_size_and_page_geometry_unchanged':True,'main_underfull_hbox':4,'supp_underfull_hbox':2,'supp_underfull_vbox':3,
    'no_overfull_undefined_double_question_marks_or_out_of_page_spans':True,
    'not_scientific_validation':True,'parent_supplement_inheritance_decision_superseded_by_actual_compile':True})
obs=read(OBS/'ROOT_OBSERVATION_SEAL.json')
assert obs['execution_released'] is False and obs['gpu_gate_satisfied'] is False
for d in obs['unchanged_state_and_closed_log_files']:verify(d)
assert Path(obs['carrier']['path']).read_bytes()==b'0'
assert all(not Path(p).exists() for p in obs['attempts_absent_at_seal'])

readme=NEW/'README_DELIVERY.md'
with readme.open('x',encoding='utf-8',newline='\n') as f:
    f.write('# Local working draft: reference format update\n\n'
        'The main PDF is now16 pages and the supplementary PDF6 pages. Both were actually compiled with the installed MiKTeX, automatic package installation and shell escape disabled. All42 main references and3 supplementary references remain. Only17 journal-title fields in the52-entry BibTeX library use three standard IEEE abbreviations; the31 other source dependencies are exact copies. Main page1–15 and supplement page1–5 previews are identical to the adopted parent; the two changed reference pages were reviewed. Existing underfull diagnostics remain.\n\n'
        'The supplement also depends on the changed shared bibliography, so the initial inherit-only plan was superseded and it was separately compiled. The original inherited PDF and the initial revision record remain preserved in execution.\n\n'
        'This is a local working draft, not the final scientific manuscript or final Overleaf delivery. T6, LOHO, fresh explanatory figures, author/independent baselines, full efficiency and remaining native-app figure acceptance remain pending. Scientific negative results, frozen protocols and inherited evidence limitations stay in the unchanged text. No new science was run; no weights, NPZ, cache/image corpus or old delivery ZIP was read. The existing Overleaf review project is unchanged.\n')
    f.flush();os.fsync(f.fileno())

inputs=[HERE/'REFERENCE_FORMAT_REVISION.json',HERE/'SUPPLEMENT_DEPENDENCY_ADDENDUM.json',HERE/'REVIEW_SOURCE_DERIVATIONS.json',
    HERE/'ACTUAL_EXECUTION_TOOLS.json',HERE/'ACTUAL_SUPPLEMENT_TOOLS.json',HERE/'compile_1/COMPILE.json',HERE/'supplement_compile_1/COMPILE.json',
    *layout_paths,PEER/'INDEPENDENT_FORMAT_REVIEW.json',PEER/'INDEPENDENT_FORMAT_REVIEW.md',PEER/'BBL_ONLY.patch',
    PEER/'INDEPENDENT_SUPPLEMENT_FORMAT_ADDENDUM.json',OBS/'ROOT_OBSERVATION_SEAL.json',HERE/'ROOT_VISUAL_REVIEW.json',Path(__file__).resolve()]
core=save(NEW/'ROOT_MANUSCRIPT_REFERENCE_FORMAT_ADOPTION.json',{
    'schema':'root-local-reference-format-working-draft-adoption.v1','utc':datetime.now(timezone.utc).isoformat(),
    'scope':'Format-only local draft adoption; scientific acceptance inherited with limits, no final manuscript or Overleaf release.',
    'source':bind(__file__),'parent_root':revision['parent_root'],'parent_external_addendum':revision['parent_external_addendum'],
    'format_revision':bind(HERE/'REFERENCE_FORMAT_REVISION.json'),'supplement_dependency_addendum':bind(HERE/'SUPPLEMENT_DEPENDENCY_ADDENDUM.json'),
    'unchanged31_source_dependencies':unchanged_sources,'new_refs':revision['new_refs'],
    'actual_compiles':[bind(HERE/'compile_1/COMPILE.json'),bind(HERE/'supplement_compile_1/COMPILE.json')],
    'outputs':[c['outputs'][0] for c in compiles],'main_pages':16,'supplementary_pages':6,
    'BibTeX_library_entries':52,'journal_fields_changed':17,'main_references':42,'supplement_references':3,
    'independent_review_scope':'Independent AI source/BBL delta only, not compilation, visual review, whole bibliography correctness or science.',
    'root_visual_review':visual,'sources_and_local_inputs':[bind(p) for p in inputs],
    'readonly_observation':bind(OBS/'ROOT_OBSERVATION_SEAL.json'),'live16_state_log_bytes_unchanged_at_adoption':True,
    'new_scientific_execution_or_result':False,'final_paper':False,'Overleaf_updated':False,'execution_released':False,'cleanup_authorized':False,
    'automatic_followup_retained':True,
    'inherited_limits':['All negative results and source evidence limitations remain. No new484-scalar or scientific/control suite replay.',
        'Parent source dependencies and their science are inherited; this formatting delta does not independently establish their truth.',
        'Prior incomplete checkpoint-SHA edges, no fresh model/full-ranking/AP revalidation, and no independent bootstrap resampling remain.',
        'Readonly process/GPU snapshot is not future admission. No exit code is inferred from absence or reused PID. Existing user Visio is not owned or closed.',
        'Eight actual compiler commands all returned0; ordinary helper/tool completion is not scientific held dual-process exit evidence.',
        'Historical initial manifest and compiler docstrings do not override the later explicit supplement dependency addendum and actual supplementary commands.'],
    'delivery_readme':bind(readme)})

members={}
def add(p,name):
    assert name not in members,name
    members[name]=(Path(p).resolve(),raw(p),bind(p))
for d in unchanged_sources+[revision['new_refs']]+[c['outputs'][0] for c in compiles]:
    p=Path(d['path']);add(p,'manuscript/'+p.relative_to(DRAFT).as_posix())
for name in ['main.bbl','supplementary.bbl']:add(DRAFT/name,'manuscript/'+name)
add(readme,'README_DELIVERY.md');add(Path(core['path']),'ROOT_MANUSCRIPT_REFERENCE_FORMAT_ADOPTION.json')
for p in sorted(HERE.rglob('*')):
    if p.is_file() and p.suffix.lower() in {'.py','.json','.patch','.txt','.png'}:
        add(p,'provenance/root/'+p.relative_to(HERE).as_posix())
for p in sorted(PEER.iterdir()):
    if p.is_file() and p.suffix.lower() in {'.py','.json','.patch','.md','.txt'}:
        add(p,'provenance/independent/'+p.name)
zip_path=NEW/'LGM_GAME_Reference_Format_Working_Draft_20260930.zip'
with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name,(p,b,d) in sorted(members.items()):archive.writestr(name,b)
verified=[]
with zipfile.ZipFile(zip_path,'r') as archive:
    assert sorted(archive.namelist())==sorted(members)
    for name,(p,expected,d) in sorted(members.items()):
        actual=archive.read(name);info=archive.getinfo(name)
        assert actual==expected and info.file_size==len(expected)
        assert info.CRC==(zlib.crc32(expected)&0xffffffff)
        verified.append({'member':name,'bytes':len(actual),'sha256':hashlib.sha256(actual).hexdigest(),'CRC32':info.CRC,'source':d})
delivery=save(NEW/'DELIVERY.json',{'schema':'local-reference-format-draft-delivery.v1','utc':datetime.now(timezone.utc).isoformat(),
    'root_adoption':core,'zip':bind(zip_path),'verified_member_count':len(verified),'members':verified,
    'scope':'New small local working draft and editable LaTeX package; old ZIP archives untouched. No final scientific or Overleaf delivery.',
    'pdfs':[c['outputs'][0] for c in compiles],'pages':[16,6],'visual_review':visual})
print(json.dumps({'root':core,'delivery':delivery,'zip':bind(zip_path),'members':len(verified)},ensure_ascii=False))
