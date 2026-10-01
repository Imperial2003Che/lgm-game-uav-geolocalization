"""Independent bounded byte/delta review. Never import or execute the producer."""
from pathlib import Path
from datetime import datetime
import hashlib, json, difflib, re

HERE=Path(__file__).resolve().parent
EX=HERE.parent
OUT=EX.parent
OLD=OUT/'manuscript_evidence_revision_20260930_0202'/'manuscript'
NEW=OUT/'manuscript_citation_revision_20260930_0520'/'manuscript'
DER=EX/'manuscript_citation_revision_20260930_0520'
CIT=EX/'citation_open_fields_20260930_0509'
checks=[]
def ck(x,s):
    if not x: raise AssertionError(s)
    checks.append(s)
def rec(p):
    b=p.read_bytes()
    return {'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def w(p,b):
    with p.open('xb') as f: f.write(b)
def js(p,obj):w(p,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def load(p):return json.loads(p.read_text(encoding='utf-8'))

revision=load(DER/'REVISION.json')
prior_list_path=EX/'manuscript_revision_scope_20260930_0202'/'layout_revision_a1'/'REVISION.json'
prior=load(prior_list_path)['final_sources']
ck(len(prior)==32,'Parent accepted source list has exactly32 dependencies')
ck(prior==revision['before'],'Producer before list equals accepted parent list')
ck(rec(prior_list_path)==revision['parent_source_list'],'Parent source-list binding matches')
ck(rec(DER/'derive_revision.py')==revision['source'],'Read producer source binding matches; no execution')
ck(rec(DER/'COMPLETE_DIFF.patch')==revision['complete_diff'],'Saved producer diff binding matches')
before_actual=[]; after_actual=[]; changed=[]; unchanged=[]; total=0
for record in prior:
    parent_path=Path(record['path']); rel=parent_path.relative_to(OLD)
    a=parent_path.read_bytes(); b=(NEW/rel).read_bytes(); total+=len(a)+len(b)
    ar=rec(parent_path); br=rec(NEW/rel)
    ck(ar==record,'Parent source matches adopted bytes: '+str(rel))
    before_actual.append(ar); after_actual.append(br)
    if a==b: unchanged.append(str(rel))
    else: changed.append(str(rel))
ck(after_actual==revision['after'],'All32 actual new file bindings equal producer after list')
ck(sorted(changed)==['main.tex','refs.bib'],'Only main.tex and refs.bib differ')
ck(len(unchanged)==30,'Thirty other dependencies are byte-identical')

oldmain=(OLD/'main.tex').read_bytes(); newmain=(NEW/'main.tex').read_bytes()
oldrefs=(OLD/'refs.bib').read_bytes(); newrefs=(NEW/'refs.bib').read_bytes()
newcitation=br'\cite{mcnemar1947,fay2010exact}, with Holm correction'
oldcitation=br'\cite{mcnemar1947}, with Holm correction'
oldpara=('brightness, and reduced contrast follow ImageNet-C-style families\n'
         '\\cite{commoncorruptions2019}; center occlusion and rotation are\n'
         'author-defined transformations. Each has five fixed severities.').encode()
newpara=('brightness, and reduced contrast are adaptations of ImageNet-C corruption\n'
         'families \\cite{commoncorruptions2019}. The implemented brightness perturbation\n'
         'darkens images; these family names do not imply identical transformations or\n'
         'severity parameters to ImageNet-C. Center occlusion and rotation are\n'
         'author-defined transformations. Each has five fixed severities.').encode()
ck(newmain.count(newcitation)==1 and oldmain.count(oldcitation)==1,'Exactly one McNemar citation addition')
ck(newmain.count(newpara)==1 and oldmain.count(oldpara)==1,'Exactly one adaptation wording replacement')
ck(newmain.replace(newcitation,oldcitation).replace(newpara,oldpara)==oldmain,
   'Reversing only two approved textual replacements recovers every original main byte')

def entries(text):
    starts=list(re.finditer(r'^@\w+\{([^,]+),',text,re.M))
    return {m.group(1):text[m.start():starts[i+1].start() if i+1<len(starts) else len(text)].strip()
            for i,m in enumerate(starts)}
olde=entries(oldrefs.decode()); newe=entries(newrefs.decode()); proposed=entries((CIT/'PROPOSED_REFERENCES.bib').read_text(encoding='utf-8'))
ck(set(newe)-set(olde)=={'fay2010exact'} and not(set(olde)-set(newe)),'Only Fay reference key added; no reference removed')
norm=lambda x:' '.join(x.split())
ck(norm(newe['fay2010exact'])==norm(proposed['fay2010exact']),'Actual Fay entry exactly matches proposed fields after whitespace normalization')
ck(norm(newe['holm1979'])==norm(proposed['holm1979']),'Actual Holm entry exactly matches proposed fields after whitespace normalization')
pos=newrefs.index(b'\n@article{fay2010exact,')
prefix=newrefs[:pos]
ck(prefix.replace(b'  url     = {https://www.jstor.org/stable/4615733}',b'  doi     = {10.2307/4615733}')==oldrefs,
   'Removing appended Fay and reversing only Holm identifier recovers every original refs byte')
ck(all(newe[k]==v for k,v in olde.items() if k!='holm1979'),'All other bibliography entries retain exact decoded text')
for entry in load(CIT/'DELIVERY_ADDENDUM.json')['files']:
    ck(rec(Path(entry['path']))==entry,'Review addendum dependency matches: '+Path(entry['path']).name)
for record in load(CIT/'DELIVERY.json').get('files',[]):
    # This independent delta task binds the delivery itself; it does not re-run the literature suite.
    pass
wording=load(CIT/'WORDING_ADDENDUM.json')
ck(rec(Path(wording['report']['path']))==wording['report'],'Wording addendum binds original report unchanged')
ck('currently non-resolving DOI' in wording['correction'],'Current DOI negative-result correction read with original report')

actual_patch=b''; normalized=''; producer_reconstructed=''; newline_counts={}
for name,a,b in [('main.tex',oldmain,newmain),('refs.bib',oldrefs,newrefs)]:
    actual_patch+=b''.join(difflib.diff_bytes(difflib.unified_diff,a.splitlines(True),b.splitlines(True),
        fromfile=('parent/manuscript/'+name).encode(),tofile=('revised/manuscript/'+name).encode()))
    normalized+=''.join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),
        fromfile='parent/manuscript/'+name,tofile='revised/manuscript/'+name))
    producer_reconstructed+=''.join(difflib.unified_diff(a.decode().splitlines(True),(NEW/name).read_text(encoding='utf-8').splitlines(True),
        fromfile='parent/manuscript/'+name,tofile='revised/manuscript/'+name))
    newline_counts[name]={'old_crlf':a.count(b'\r\n'),'new_crlf':b.count(b'\r\n'),
                         'old_lf_total':a.count(b'\n'),'new_lf_total':b.count(b'\n')}
ck(producer_reconstructed.encode()==(DER/'COMPLETE_DIFF.patch').read_bytes(),
   'Entire saved producer diff independently reconstructed; read_text universal-newline conversion explains expanded refs hunk')
w(HERE/'ACTUAL_BYTE_DIFF.patch',actual_patch)

scope_inputs=[DER/'derive_revision.py',DER/'REVISION.json',DER/'COMPLETE_DIFF.patch',prior_list_path,
 CIT/'REVIEW.md',CIT/'OPEN_FIELDS_REVIEW.json',CIT/'DELIVERY.json',CIT/'DELIVERY_ADDENDUM.json',CIT/'WORDING_ADDENDUM.json',
 CIT/'PROPOSED_REFERENCES.bib',EX/'citation_foundations_review_20260930_0405'/'REVIEW.md',
 EX/'citation_foundations_review_20260930_0405'/'ROOT_PRIMARY_ACCESS_ADDENDUM.md']
report={'schema':'lgm-independent-citation-manuscript-delta-review.v1','created_local':datetime.now().astimezone().isoformat(),
 'reviewer':'AI subagent /root/boot_contract_0405, independent of revision producer; not external human review',
 'accepted_for_delta_scope':True,'method':'Read complete5419-byte producer source and current citation prose/reports; independently compare actual old/new32 source dependencies; reverse exactly the approved changes and reconstruct full saved patch. No producer import/execution, web, scientific/COM run, compiler or visual inspection.',
 'changes_reviewed':[
  {'item':'Holm','assessment':'Replace only currently non-resolving DOI with official JSTOR stable URL, as the new research/addendum recommends. Does not claim never historically registered.'},
  {'item':'Fay','assessment':'Add matching2010 entry and one citation key beside McNemar1947. Formula remains in existing prose; source support is distinct from project computation/assumption/result validation.'},
  {'item':'brightness','assessment':'Explicitly says project images are darkened and families/severities are adaptations. Agrees with previous local reduced-brightness prose and cited current-master direction difference; does not claim a pinned2019 source comparison.'}],
 'scientific_numbers_tables_parameters_changed':False,'reason_for_science_scope':'All other main bytes recover exactly;30 dependencies including all original tables/figures/supplementary are byte-identical. This is change detection, not renewed scientific validation.',
 'actual_changed_sources':changed,'byte_identical_dependencies':unchanged,'source_pair_bytes_read':total,
 'newline_counts':newline_counts,
 'producer_diff_limitation':'Saved COMPLETE_DIFF.patch compares before decoded preserved newline endings against after read_text universal-newline conversion. Its broad refs hunk is a representation artifact; actual copied CRLF lines remain. ACTUAL_BYTE_DIFF.patch preserves both real byte line endings.',
 'checks':checks,'check_count':len(checks),'source':rec(Path(__file__)),
 'scope_input_bindings':[rec(p) for p in scope_inputs], 'actual_before':before_actual,'actual_after':after_actual,
 'actual_byte_diff':rec(HERE/'ACTUAL_BYTE_DIFF.patch'),
 'not_done':['independent compilation','independent PDF/page/figure visual review','484-number retranscription','old scientific/control suite rerun','web rebrowse','model/data/cache/weight inspection','Overleaf update'],
 'limitations':'Acceptance is only the minimal source delta and exact source-copy scope. Root must separately validate compilation/layout. Existing evidence-chain and experimental limitations remain. One attempted read of ROOT_ACCESS_ADDENDUM.json was absent; actual ROOT_PRIMARY_ACCESS_ADDENDUM.md was located and read; no evidence was inferred from the absent path.'}
js(HERE/'DELTA_REVIEW.json',report)
readme='''# Independent citation manuscript delta review

Accepted within source-delta scope: two files changed, and the other30 accepted source dependencies are byte-identical. Actual Fay/Holm entries agree with the new reference proposal and its wording addendum. Brightness is explicitly described as a project adaptation, consistent with the earlier bounded current-source evidence.

Reversing only the two approved main.tex replacements recovers every old main byte. Removing appended Fay and reversing only Holm's identifier recovers every old refs byte. Tables, figures, supplementary text, scientific numbers and parameters were unchanged; this does not repeat their scientific validation.

The producer's44,244-byte COMPLETE_DIFF.patch expands refs because its after read uses universal-newline conversion. This is a diff representation issue; the actual refs lines were not all normalized. ACTUAL_BYTE_DIFF.patch is the independent comparison preserving real old/new line endings. The sealed producer patch remains untouched.

This AI-agent review did not run the producer, science/COM, previous484 checks, a compiler, new web searches, or PDF visual review. Compilation/layout acceptance is the root's separate responsibility. No manuscript was edited by this reviewer.
'''
w(HERE/'REVIEW.md',readme.encode())
files=[rec(HERE/n) for n in ['check_delta.py','ACTUAL_BYTE_DIFF.patch','DELTA_REVIEW.json','REVIEW.md']]
js(HERE/'DELIVERY.json',{'schema':'lgm-independent-citation-delta-delivery.v1','created_local':datetime.now().astimezone().isoformat(),
 'files':files,'accepted_for_delta_scope':True,'independent_compilation':False,'independent_visual_review':False,
 'check_count':len(checks),'new_literature_or_science_validation':False})
print(normalized)
print(json.dumps({'checks':len(checks),'report':rec(HERE/'DELTA_REVIEW.json'),'delivery':rec(HERE/'DELIVERY.json')},ensure_ascii=False))
