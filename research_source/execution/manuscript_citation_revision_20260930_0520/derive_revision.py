"""One new local citation/protocol-wording revision, preserving sealed parent."""
from pathlib import Path
import hashlib,json,datetime,difflib
OUT=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914')
EX=OUT/'execution'; HERE=Path(__file__).resolve().parent
BASE=OUT/'manuscript_evidence_revision_20260930_0202'/'manuscript'
DEST=OUT/'manuscript_citation_revision_20260930_0520'
def rec(p):
 b=p.read_bytes();return {'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def js(p,d):write(p,(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
parent=OUT/'manuscript_evidence_revision_20260930_0202'/'ROOT_MANUSCRIPT_ADOPTION.json'
assert rec(parent)['sha256']=='91263e81e5b8ed3abb18cfa2feb856fae1855da1d4d44bdcbc79f641b003438c'
source_list=EX/'manuscript_revision_scope_20260930_0202'/'layout_revision_a1'/'REVISION.json'
entries=json.loads(source_list.read_text(encoding='utf-8'))['final_sources']
assert len(entries)==32
assert not DEST.exists()
DEST.mkdir()
before=[]
for r in entries:
 p=Path(r['path']); rel=p.relative_to(BASE);assert rec(p)==r
 write(DEST/'manuscript'/rel,p.read_bytes());before.append(r)
main=DEST/'manuscript'/'main.tex'; refs=DEST/'manuscript'/'refs.bib'
mb=main.read_bytes();rb=refs.read_bytes()
old=r'\cite{mcnemar1947}, with Holm correction'
new=r'\cite{mcnemar1947,fay2010exact}, with Holm correction'
assert mb.count(old.encode())==1
mt=mb.decode().replace(old,new)
oldblock="""brightness, and reduced contrast follow ImageNet-C-style families
\\cite{commoncorruptions2019}; center occlusion and rotation are
author-defined transformations. Each has five fixed severities."""
newblock="""brightness, and reduced contrast are adaptations of ImageNet-C corruption
families \\cite{commoncorruptions2019}. The implemented brightness perturbation
darkens images; these family names do not imply identical transformations or
severity parameters to ImageNet-C. Center occlusion and rotation are
author-defined transformations. Each has five fixed severities."""
assert mt.count(oldblock)==1
mt=mt.replace(oldblock,newblock)
rt=rb.decode();old='  doi     = {10.2307/4615733}';new='  url     = {https://www.jstor.org/stable/4615733}'
assert rt.count(old)==1;rt=rt.replace(old,new)
assert 'fay2010exact' not in rt
rt+=r"""
@article{fay2010exact,
  author  = {Michael P. Fay},
  title   = {Two-sided Exact Tests and Matching Confidence Intervals for Discrete Data},
  journal = {The R Journal},
  volume  = {2},
  number  = {1},
  pages   = {53--58},
  year    = {2010},
  doi     = {10.32614/RJ-2010-008},
  url     = {https://journal.r-project.org/articles/RJ-2010-008/}
}
"""
main.write_bytes(mt.encode());refs.write_bytes(rt.encode())
diff=''
for p,b in [(main,mb),(refs,rb)]:
 diff+=''.join(difflib.unified_diff(b.decode().splitlines(True),p.read_text(encoding='utf-8').splitlines(True),fromfile='parent/manuscript/'+p.name,tofile='revised/manuscript/'+p.name))
write(HERE/'COMPLETE_DIFF.patch',diff.encode())
after=[rec(DEST/'manuscript'/Path(r['path']).relative_to(BASE)) for r in entries]
changes=[Path(a['path']).name for a,b in zip(after,before) if a['sha256']!=b['sha256']]
assert sorted(changes)==['main.tex','refs.bib']
readme="""# Local citation-revised working draft — 2026-09-30

This is a local working revision, not the final submission or an Overleaf update.
It derives from the accepted 02:02 evidence draft. Only main.tex and refs.bib
change: Holm's currently unresolvable DOI is replaced by the official JSTOR
stable URL; Fay (2010) is added for the conditional exact McNemar formulation;
the brightness/corruption-family wording explicitly describes project adaptations.
No scientific result, figure, table, training parameter, uncertainty claim,
historical provenance limitation or experiment completion status is changed.

The original evidence draft and its ZIP remain intact. Thirty other source
dependencies are copied byte-for-byte from the parent's accepted 32-file list.
The reference review supports the formula, not independent validation of this
project's statistical implementation. It does not establish historical DOI
registration or a pinned 2019 ImageNet-C implementation.

Pending T6, LOHO, real interpretation figures, further Visio figures, author and
independently trained baselines, extra DAC, efficiency, final manuscript,
Overleaf and submission advice remain pending under their existing gates.
See provenance and compilation records in this package for exact scope.
"""
write(DEST/'README.md',readme.encode())
report={'schema':'lgm-targeted-citation-revision.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
'parent_root':rec(parent),'parent_source_list':rec(source_list),'source':rec(Path(__file__)),'before':before,'after':after,
'changed_sources':changes,'unchanged_dependencies':30,'complete_diff':rec(HERE/'COMPLETE_DIFF.patch'),
'changes':['Holm current DOI replaced with official stable URL','Fay 2010 added beside McNemar 1947','Clarify brightness reduction and corruption-family adaptations, without claiming pinned historical equivalence'],
'science_changed':False,'statistics_recomputed':False,'overleaf_updated':False,'final_submission':False}
js(HERE/'REVISION.json',report)
print(json.dumps({'dest':str(DEST),'changed':changes,'unchanged':30},ensure_ascii=False))

