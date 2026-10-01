from pathlib import Path
import hashlib,json,datetime
HERE=Path(__file__).resolve().parent; EX=HERE.parent;OUT=EX.parent
DEST=OUT/'manuscript_citation_revision_20260930_0520'
def rec(p):
 b=p.read_bytes(); return {'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,obj):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def load(p):return json.loads(p.read_bytes())
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
layout=load(HERE/'preview_1/PDF_LAYOUT.json')
old=EX/'manuscript_compile_20260930_0202/preview_2'
comp=load(HERE/'compile_1/COMPILE.json')
assert comp['status']=='compiled' and len(comp['commands'])==8
assert all(x['exit_code']==0 for x in comp['commands'])
assert comp['input_texts_unchanged']
viewed={f'main-{i:02d}.png' for i in [7,8,9,10,11,12,13,15,16,17]}
same=[];different=[]
for d in layout['documents']:
 assert d['page_count']==(17 if Path(d['pdf']['path']).name=='main.pdf' else 6)
 assert not any('Overfull' in s or 'undefined' in s.lower() for s in d['latex_diagnostics'])
 for p in d['pages']:
  assert p['out_of_page_spans']==[] and p['unresolved_double_question_marks']==0
  png=Path(p['png']['path']); before=old/png.name
  row={'current':rec(png),'prior':rec(before) if before.exists() else None}
  if row['prior'] and row['prior']['sha256']==row['current']['sha256']:same.append(row)
  else:
   assert png.name in viewed
   different.append(row)
assert len(same)==14 and len(different)==9
save(HERE/'ROOT_VISUAL_REVIEW.json',{
 'schema':'root-targeted-manuscript-pdf-review.v1','utc':now,
 'method':'Root AI actually inspected original-resolution tool-displayed page images; no human review.',
 'layout':rec(HERE/'preview_1/PDF_LAYOUT.json'),'compiler_report':rec(HERE/'compile_1/COMPILE.json'),
 'compiler_source':rec(EX/'manuscript_compile_20260930_0202/compile_working_draft.py'),
 'renderer_source':rec(EX/'manuscript_compile_20260930_0202/render_and_inspect_pdf.py'),
 'same_pngs_as_accepted_parent':same,'changed_pngs_actually_viewed':different,
 'additional_unchanged_page_actually_viewed':'main-15.png',
 'actual_viewed_count':10,'new_total_pages':23,'text_overlap_or_clipping_seen':False,
 'unresolved_layout_item':'Main p17 contains only the final AQE reference. Accepted as an explicit local-working-draft limitation, not final publication layout. No font reduction or second compile.',
 'diagnostics':{Path(d['pdf']['path']).name:d['latex_diagnostics'] for d in layout['documents']},
 'limits':['Same PNG bytes support image equality, not new reading of all unchanged pages.',
           'No independent second-agent compile or visual inspection; its review covers source delta only.',
           'Old public-baseline figures and scientific claims remain inherited from the parent; these page views are not new scientific validation.']})
save(HERE/'ROOT_EXECUTION_NOTES.json',{
 'utc':now,'compiler':'Installed MiKTeX; automatic installer and shell escape disabled; 8 new-draft commands each actual subprocess exit0.',
 'renderer_failed_first':{'runtime':r'C:\Users\17703\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
 'command':'render_and_inspect_pdf.py --draft new manuscript --output preview_1','tool_exit_code':1,
 'error':"ModuleNotFoundError: No module named 'fitz'",'stage':'top-level import, before parsing arguments or creating preview directory',
 'record_type':'Root summary of actual tool output; not a previously captured stdout file'},
 'renderer_succeeded':{'runtime':r'C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe',
 'reason':'Read-only module discovery confirmed already installed fitz; no installation.',
 'same_script_and_arguments':True,'tool_exit_code':0,'result':'17 main and6 supplementary PNG rendered'},
 'auxiliary_read_error':'A combined read used README.md for the CAMP/DAC report; actual filename REVIEW.md was subsequently read. No artifact changed.',
 'tool_exit_scope':'Compiler subprocess return codes and tool returns are reported; no held Windows handles or scientific/native exit proof claimed.',
 'science_executed':False,'COM_executed':False,'scientific_libraries_imported':False})
save(HERE/'ROOT_PRIMARY_ACCESS_ADDENDUM.json',{
 'utc':now,'method':'Root direct web tool reads after agent literature review',
 'access':[
 {'url':'https://doi.org/ra/10.2307/4615733','result':'tool inaccessible; root relies on bound agent successful direct HTTP response, not a root success'},
 {'url':'https://journal.r-project.org/articles/RJ-2010-008/','result':'success; title/byline/date, central doubled-tail expression, theta=.5 equivalence and paired conditional binomial read'},
 {'url':'https://www.jstor.org/stable/i412579','result':'success issue record; author/article stable link'},
 {'url':'https://arxiv.org/abs/2605.07099','result':'later root reread failed; earlier successful v5 reading remains in separately sealed preprint review'}],
 'time_precision':'Calls occurred after turn observations and before this record; exact per-request UTC was not captured.',
 'effect':'Supports local citation revision only; no project statistical implementation validation and no claim that Holm DOI never historically existed.'})
print(json.dumps({'visual':rec(HERE/'ROOT_VISUAL_REVIEW.json'),'compile_commands':8,'pages':23},ensure_ascii=False))

