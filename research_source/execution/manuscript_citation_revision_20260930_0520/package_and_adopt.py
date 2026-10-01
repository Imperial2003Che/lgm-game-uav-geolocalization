"""Package only the new local draft and bounded review records."""
from pathlib import Path
import json,hashlib,datetime,zipfile,shutil
HERE=Path(__file__).resolve().parent; EX=HERE.parent; OUT=EX.parent
DEST=OUT/'manuscript_citation_revision_20260930_0520'; MAN=DEST/'manuscript'
IND=EX/'manuscript_citation_delta_review_20260930_0520'
OBS=EX/'heartbeat_observation_20260930_050928509'
def rec(p):
 b=p.read_bytes();return {'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(p.read_bytes())
def save(p,o):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
checked={}
def verify(r):
 p=Path(r['path'])
 if str(p) not in checked:checked[str(p)]=rec(p)
 assert checked[str(p)]==r,str(p)
 return r
def delivery(p,expected):
 assert rec(p)['sha256']==expected
 d=load(p)
 for r in d.get('files',d.get('records',[])):verify(r)
 return rec(p)
revision=load(HERE/'REVISION.json');ind=load(IND/'DELTA_REVIEW.json')
assert ind['accepted_for_delta_scope'] and ind['check_count']==53
assert ind['actual_after']==revision['after']
for r in revision['after']:verify(r)
for r in ind['scope_input_bindings']:verify(r)
verify(revision['parent_root'])
assert len(revision['after'])==32 and revision['unchanged_dependencies']==30
comp=load(HERE/'compile_1/COMPILE.json')
assert len(comp['commands'])==8 and comp['status']=='compiled'
for c in comp['commands']:assert c['exit_code']==0;verify(c['log'])
for r in comp['outputs']:verify(r)
for r in comp['input_texts']:verify(r)
visual=load(HERE/'ROOT_VISUAL_REVIEW.json')
assert visual['actual_viewed_count']==10 and len(visual['changed_pngs_actually_viewed'])==9
assert len(visual['same_pngs_as_accepted_parent'])==14
assert not visual['text_overlap_or_clipping_seen']
inputs=[
 delivery(IND/'DELIVERY.json','7e36ee2cfe982d2c66a6c6f75a4913720f9fea86dde69a4e3df4df7b1a95a6bb'),
 delivery(EX/'citation_open_fields_20260930_0509/DELIVERY.json','940fa65f9bd6c183045fa0e937a8d1c4fef5d0adcc13c8aa8803b5eebfe917a5'),
 delivery(EX/'citation_open_fields_20260930_0509/DELIVERY_ADDENDUM.json','c2f0792a35d5767f311d06c4d414dbabd852434a5bd598f05b5df7e58b4846f7'),
 delivery(EX/'citation_datasets_review_20260930_0509/DELIVERY.json','c35fb462e6abefa439c284c2ad9a414dd9e86ff9df4014da965e4d4e9e98f4b8'),
 delivery(EX/'citation_camp_dac_review_20260930_0509/DELIVERY.json','87a4b19f6399c67699951b416877cb5a1a26c9a19f7e5c0027810a19040af8cd'),
 delivery(EX/'citation_preprints_review_20260930_0509/DELIVERY.json','af29c52436b41fc28b24228ca6d6a56cb7a7cc449b07e41ac92b266622cb654c')]
obs=load(OBS/'ROOT_OBSERVATION_SEAL.json')
assert rec(OBS/'ROOT_OBSERVATION_SEAL.json')['sha256']=='385e7b38418c23185ac3e84152a177c7ac61e72d612ac8c969d42aff0569ac32'
# Fresh recheck of closed scientific state/log bytes at adoption; no state writes.
for r in obs['unchanged_state_and_closed_log_files']:verify(r)
assert len(obs['unchanged_state_and_closed_log_files'])==16
assert Path(obs['carrier']['path']).read_bytes()==b'0'
assert all(not Path(p).exists() for p in obs['attempts_absent_at_seal'])
assert not (Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch')/'analysis/transactions_t6_formal').exists()
scope={
 'schema':'local-citation-draft-delivery-scope.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'parent_root':revision['parent_root'],'revision':rec(HERE/'REVISION.json'),'independent_delta':rec(IND/'DELTA_REVIEW.json'),
 'root_compile':rec(HERE/'compile_1/COMPILE.json'),'root_visual':rec(HERE/'ROOT_VISUAL_REVIEW.json'),
 'research_deliveries':inputs,'changes':revision['changes'],
 'pages':{'main':17,'supplementary':6},'new_scientific_results':0,'new_scientific_figures':0,
 'root_scope':'Root AI reads of reports/prose/independent source, actual compilation and changed-page visual inspection; not a human or second independent science review.',
 'research_scope':[
 'Open-field research closes AQE pages/Efron DOI/name and supports new Holm/Fay citation changes; read original with wording addendum.',
 'Two dataset entries: literature agreement only, not local members or science validation;60-row cross-scope arithmetic remains unresolved, no numeric correction.',
 'CAMP/DAC future entries and36 author-reported rows72 values remain research-only, not inserted or accepted project results. Paper/code warmup/batch/AP distinctions retained.',
 'MGS v2/InfoGeo v5:20 displayed author-report values checked by root; MobileGeo primary access unsuccessful and inherited. Not full bibliography validation.'],
 'limitations':[
 'Main final p17 has one reference; final publication layout remains pending. Main4 underfull hbox; supplementary2 underfull hbox+3vbox; no overfull/undefined/?? or out-of-page spans.',
 'Initial bundled renderer failed missing fitz before output; same script succeeded with already installed Python311 PyMuPDF. No install.',
 'Original producer patch expands refs due to comparison newline conversion; independent ACTUAL_BYTE_DIFF.patch preserves actual byte line endings. Original sources/patch retained.',
 'Literature support does not validate project statistical implementation, model/ranking/AP, checkpoint bytes or bootstrap resampling.',
 'All parent negative results, frozen protocols, seed/metric/conditional-query caveats and historical SHA-chain gaps are inherited.',
 'Old full partner ZIP and previous draft ZIP were not read or overwritten. Overleaf unchanged. This is not final submission.'],
 'remaining':'T6, LOHO24fit192task, real interpretation, remaining Visio, author/independent baselines, extraDAC, full efficiency, final manuscript/Overleaf/submission advice.',
 'current_observation':rec(OBS/'ROOT_OBSERVATION_SEAL.json'),
 'fresh_at_adoption':'16 closed state/log bytes, one-byte carrier and four attempt absences checked. OS/GPU observation remains at05:09London; not a fresh execution admission.',
 'execution_release':False,'cleanup_authorized':False}
save(DEST/'DELIVERY_SCOPE.json',scope)
# Package the 32 accepted source copies, actual PDFs and reference output.
members={}
def add(p,name):assert name not in members;members[name]=p
for r in revision['after']:
 p=Path(r['path']);add(p,p.relative_to(DEST).as_posix())
for name in ['main.pdf','supplementary.pdf','main.bbl','supplementary.bbl']:add(MAN/name,'manuscript/'+name)
for name in ['README.md','DELIVERY_SCOPE.json']:add(DEST/name,name)
for name in ['derive_revision.py','REVISION.json','COMPLETE_DIFF.patch','record_root_review.py','ROOT_VISUAL_REVIEW.json','ROOT_EXECUTION_NOTES.json','ROOT_PRIMARY_ACCESS_ADDENDUM.json','package_and_adopt.py']:
 add(HERE/name,'provenance/root/'+name)
for p in sorted((HERE/'compile_1').iterdir()):
 if p.is_file():add(p,'provenance/compile/'+p.name)
for p in sorted((HERE/'preview_1').iterdir()):
 if p.is_file():add(p,'previews/'+p.name)
for p in sorted(IND.iterdir()):
 if p.is_file():add(p,'provenance/independent/'+p.name)
for name in ['compile_working_draft.py','render_and_inspect_pdf.py']:
 add(EX/'manuscript_compile_20260930_0202'/name,'provenance/compiler/'+name)
# Include compact research records only; full third-party paper PDFs, extracted
# paper text, author scripts and rendered paper pages stay as local research assets.
research_names={
 'citation_open_fields_20260930_0509':['OPEN_FIELDS_REVIEW.json','REVIEW.md','DELIVERY.json','DELIVERY_ADDENDUM.json','WORDING_ADDENDUM.json','WEB_EVIDENCE.json','CROSSREF_DIRECT_ACCESS.json','ADDITIONAL_DIRECT_ACCESS.json','PDF_DIRECT_ACCESS.json','PROPOSED_CITATION_ONLY.patch'],
 'citation_datasets_review_20260930_0509':['DATASET_CITATION_REVIEW.json','REVIEW.md','DELIVERY.json','PRIMARY_ACCESS.json'],
 'citation_camp_dac_review_20260930_0509':['CAMP_DAC_CITATION_REVIEW.json','REVIEW.md','DELIVERY.json','AUTHOR_REPORTED_ROWS.csv','PROPOSED_REFERENCES.bib','WEB_TOOL_ACCESS_LEDGER.json','DIRECT_PRIMARY_ACCESS.json','DIRECT_PRIMARY_ACCESS_2.json'],
 'citation_preprints_review_20260930_0509':['PREPRINT_REVIEW.json','REVIEW.md','DELIVERY.json']}
for folder,names in research_names.items():
 for name in names:
  p=EX/folder/name
  assert p.is_file(),str(p)
  add(p,'provenance/research/'+folder+'/'+name)
add(OBS/'ROOT_OBSERVATION_SEAL.json','provenance/observation/ROOT_OBSERVATION_SEAL.json')
manifest={'schema':'new-local-draft-zip-members.v1','members':[{'name':name,**rec(p)} for name,p in sorted(members.items())],
 'scope':'Only listed files. Research dependencies not copied are explicit external local bindings, not a self-contained science archive.'}
save(DEST/'PACKAGE_MEMBERS.json',manifest);add(DEST/'PACKAGE_MEMBERS.json','PACKAGE_MEMBERS.json')
zip_path=DEST/'LGM_GAME_Citation_Revised_Working_Draft_20260930.zip'
with zipfile.ZipFile(zip_path,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name,p in sorted(members.items()):z.write(p,name)
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None and set(z.namelist())==set(members)
 for name,p in members.items():
  b=z.read(name);r=rec(p);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
root={'schema':'root-local-citation-manuscript-adoption.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source':rec(Path(__file__)),'scope':rec(DEST/'DELIVERY_SCOPE.json'),'zip':rec(zip_path),'zip_members_verified':len(members),
 'manifest':rec(DEST/'PACKAGE_MEMBERS.json'),'main_pdf':rec(MAN/'main.pdf'),'supplementary_pdf':rec(MAN/'supplementary.pdf'),
 'revision':rec(HERE/'REVISION.json'),'independent':rec(IND/'DELIVERY.json'),'root_visual':rec(HERE/'ROOT_VISUAL_REVIEW.json'),
 'verified_unique_local_bindings':len(checked),'verified_bindings':list(checked.values()),
 'adopted_as':'Local working draft and bounded literature-research records; not final science, paper, Overleaf or submission',
 'source_delta_accepted':True,'actual_compile_accepted':True,'layout_accepted_for_local_draft_with_recorded_limitation':True,
 'science_accepted_new':False,'overleaf_updated':False,'final_submission':False,'automation_should_remain':True}
save(DEST/'ROOT_MANUSCRIPT_CITATION_ADOPTION.json',root)
print(json.dumps({'root':rec(DEST/'ROOT_MANUSCRIPT_CITATION_ADOPTION.json'),'zip':rec(zip_path),'members':len(members),'bindings':len(checked)},ensure_ascii=False))

