"""Derive a new IEEE author-display draft from the adopted parent bytes."""
from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json, os

HERE=Path(__file__).resolve().parent
EX=HERE.parent
OUT=EX.parent
PARENT=OUT/'manuscript_camp_dac_context_20260930_1948'
COPIED=OUT/'manuscript_reference_pagination_20260930_2138/manuscript'
PRIOR=EX/'manuscript_reference_pagination_20260930_2138'
TARGET=OUT/'manuscript_ieee_reference_display_20260930_2145'
def binding(p,raw=None):
    p=Path(p)
    if raw is None:raw=p.read_bytes()
    return dict(path=str(p.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def create(p,raw):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
rootpath=PARENT/'ROOT_CAMP_DAC_CONTEXT_ADOPTION.json'
rootraw=rootpath.read_bytes()
rootbind=binding(rootpath,rootraw)
assert rootbind['sha256']=='af7fa415e13b790fb26abe6f25e857c5164ec331648de3078d0f3146b9ef15d8'
root=json.loads(rootraw)
assert not TARGET.exists()
TARGET.mkdir();draft=TARGET/'manuscript';draft.mkdir()
copies=[];oldmain=None
for expected in root['source_dependencies']:
    relative=Path(expected['path']).resolve().relative_to((PARENT/'manuscript').resolve())
    source=PRIOR/'main.tex.before' if relative.as_posix()=='main.tex' else COPIED/relative
    raw=source.read_bytes()
    actual=binding(source,raw)
    assert actual['bytes']==expected['bytes'] and actual['sha256']==expected['sha256']
    create(draft/relative,raw)
    copies.append(dict(relative=relative.as_posix(),parent_authority=expected,actual_local_copy=actual,copied=binding(draft/relative,raw)))
    if relative.as_posix()=='main.tex':oldmain=raw
assert len(copies)==32 and oldmain is not None
assert oldmain.count(b'\\begin{document}\n')==1
assert oldmain.count(b'\\bibliography{refs}')==1
newmain=oldmain.replace(b'\\begin{document}\n',b'\\begin{document}\n\\bstctlcite{IEEEAuthorDisplayControl}\n',1)
newmain=newmain.replace(b'\\bibliography{refs}',b'\\bibliography{ieee_controls,refs}',1)
assert newmain.replace(b'\\bstctlcite{IEEEAuthorDisplayControl}\n',b'',1).replace(b'\\bibliography{ieee_controls,refs}',b'\\bibliography{refs}',1)==oldmain
assert b'\\FloatBarrier\n\\clearpage\n' in newmain
create(HERE/'main.tex.before',oldmain)
(draft/'main.tex').write_bytes(newmain)
patch=''.join(difflib.unified_diff(oldmain.decode().splitlines(keepends=True),newmain.decode().splitlines(keepends=True),fromfile='adopted-parent/main.tex',tofile='new/main.tex')).encode()
create(HERE/'main.tex.patch',patch)
control=b'''@IEEEtranBSTCTL{IEEEAuthorDisplayControl,
  CTLuse_forced_etal = {yes},
  CTLmax_names_forced_etal = {6},
  CTLnames_show_etal = {1}
}
'''
create(draft/'ieee_controls.bib',control)
supp_expected=next(r for r in root['outputs'] if Path(r['path']).name=='supplementary.pdf')
supp_raw=(COPIED/'supplementary.pdf').read_bytes()
supp_actual=binding(COPIED/'supplementary.pdf',supp_raw)
assert (supp_actual['bytes'],supp_actual['sha256'])==(supp_expected['bytes'],supp_expected['sha256'])
create(draft/'supplementary.pdf',supp_raw)
helpers=[]
for name in ('compile_main_only.py','render_main_only.py'):
    raw=(PRIOR/name).read_bytes();create(HERE/name,raw)
    helpers.append(dict(source=binding(PRIOR/name,raw),copy=binding(HERE/name,raw)))
report=dict(schema='local-ieee-author-display-revision.v1',utc=datetime.now(timezone.utc).isoformat(),
    source=binding(__file__),parent_root=rootbind,source_dependencies=copies,changed_main=binding(draft/'main.tex'),
    old_main=binding(HERE/'main.tex.before'),complete_delta=binding(HERE/'main.tex.patch'),new_control=binding(draft/'ieee_controls.bib'),
    unchanged_parent_dependency_count=31,source_dependency_count_after=33,helper_sources=helpers,
    inherited_supplement=supp_expected,copied_supplement=binding(draft/'supplementary.pdf',supp_raw),
    scope='Standard IEEEtran BST control: references with more than six authors display the first author followed by et al.; keep full author metadata in unchanged refs.bib.',
    retained_parent_clearpage=True,scientific_numeric_or_protocol_change=False,bibliographic_metadata_change=False,
    font_change=False,old_sources_changed=False,compilation_completed=False,pagination_improved=False,
    final_manuscript=False,Overleaf_updated=False,
    limits=['Actual page count and bibliography output must be checked after compilation; no assumed page reduction.',
        'The control applies only to main.tex; supplementary.tex and its refs.bib input are unchanged, and its adopted six-page PDF is inherited without recompilation.',
        'This is an author-display format change, not whole-bibliography, cited-work scientific or project-science validation.',
        'All frozen protocols, negative results and provenance limitations are inherited; no old ZIP, model weight, NPZ, cache or dataset corpus read/run.'])
create(HERE/'AUTHOR_DISPLAY_REVISION.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(report=binding(HERE/'AUTHOR_DISPLAY_REVISION.json'),draft=str(draft),changed_main=report['changed_main']),ensure_ascii=False))
