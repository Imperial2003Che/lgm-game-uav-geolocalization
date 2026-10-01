"""Restrict author-display control to six reviewed IEEE reference keys."""
from pathlib import Path
from datetime import datetime, timezone
import difflib,hashlib,json,os,re
HERE=Path(__file__).resolve().parent
EX=HERE.parent;OUT=EX.parent
PARENT=OUT/'manuscript_ieee_reference_display_20260930_2145/manuscript'
TARGET=OUT/'manuscript_ieee_reference_scope_20260930_2155'
KEYS=('lpn2022','sdpl2024','vlgeo2026','eagle2025','r2ploc2025','rendering2025')
def binding(p,raw=None):
    p=Path(p)
    if raw is None:raw=p.read_bytes()
    return dict(path=str(p.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def create(p,raw):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
authority=EX/'manuscript_ieee_reference_display_20260930_2145/AUTHOR_DISPLAY_REVISION.json'
araw=authority.read_bytes();abind=binding(authority,araw)
assert abind['sha256']=='b52f16e381b3ed8ebdb714fd610c18bee502572520f974bb4c88c357e73c684b'
a=json.loads(araw)
expected=[r['copied'] if r['relative']!='main.tex' else a['changed_main'] for r in a['source_dependencies']]+[a['new_control']]
assert len(expected)==33 and not TARGET.exists()
TARGET.mkdir();draft=TARGET/'manuscript';draft.mkdir();copies=[]
for e in expected:
    p=Path(e['path']);relative=p.relative_to(PARENT)
    raw=p.read_bytes();assert binding(p,raw)==e
    create(draft/relative,raw);copies.append(dict(relative=relative.as_posix(),inherited=e,copied=binding(draft/relative,raw)))
main=(draft/'main.tex').read_bytes()
assert main.count(b'\\bibliographystyle{IEEEtran}')==1
changed=main.replace(b'\\bibliographystyle{IEEEtran}',b'\\bibliographystyle{IEEEtran_lgm_display}',1)
create(HERE/'main.tex.before',main);(draft/'main.tex').write_bytes(changed)
patch=''.join(difflib.unified_diff(main.decode().splitlines(keepends=True),changed.decode().splitlines(keepends=True),fromfile='global-candidate/main.tex',tofile='scoped/main.tex')).encode()
create(HERE/'main.tex.patch',patch)
bstsrc=Path(r'C:\Users\17703\AppData\Local\Programs\MiKTeX\bibtex\bst\ieeetran\IEEEtran.bst')
bst=bstsrc.read_bytes();assert len(bst)<100000
matches=list(re.finditer(rb'          is\.forced\.et\.al and and\r?\n',bst))
assert len(matches)==1
anchor=matches[0].group()
guard=(b'          cite$ "lpn2022" = cite$ "sdpl2024" = or\n'
       b'          cite$ "vlgeo2026" = or cite$ "eagle2025" = or\n'
       b'          cite$ "r2ploc2025" = or cite$ "rendering2025" = or and\n')
if anchor.endswith(b'\r\n'):guard=guard.replace(b'\n',b'\r\n')
derived=bst.replace(anchor,anchor+guard,1)
assert derived.replace(anchor+guard,anchor,1)==bst
create(HERE/'IEEEtran.bst.before',bst)
create(draft/'IEEEtran_lgm_display.bst',derived)
bstpatch=''.join(difflib.unified_diff(bst.decode().splitlines(keepends=True),derived.decode().splitlines(keepends=True),fromfile='installed/IEEEtran.bst',tofile='derived/IEEEtran_lgm_display.bst')).encode()
create(HERE/'IEEEtran_lgm_display.bst.patch',bstpatch)
refs=(draft/'refs.bib').read_text(encoding='utf-8');venues=[]
for key in KEYS:
    entry=re.search(r'@\w+\{'+re.escape(key)+r',(.*?)(?=\n@|\Z)',refs,re.S)
    assert entry
    journal=re.search(r'journal\s*=\s*\{([^}]+)\}',entry[1])
    assert journal and journal[1].startswith('IEEE ')
    assert not re.search(r'\beditor\s*=',entry[1])
    venues.append(dict(key=key,journal=journal[1],no_editor_field=True))
supp=(PARENT/'supplementary.pdf').read_bytes()
e=a['copied_supplement'];assert binding(PARENT/'supplementary.pdf',supp)==e
create(draft/'supplementary.pdf',supp)
helpers=[]
for name in ('compile_main_only.py','render_main_only.py'):
    p=EX/'manuscript_ieee_reference_display_20260930_2145'/name
    raw=p.read_bytes();create(HERE/name,raw);helpers.append(dict(parent=binding(p,raw),copy=binding(HERE/name,raw)))
report=dict(schema='local-scoped-ieee-author-display-revision.v1',utc=datetime.now(timezone.utc).isoformat(),source=binding(__file__),
    preceding_candidate=abind,adopted_parent=a['parent_root'],source_dependencies=copies,changed_main=binding(draft/'main.tex'),
    main_delta=binding(HERE/'main.tex.patch'),installed_bst=binding(bstsrc,bst),preserved_bst=binding(HERE/'IEEEtran.bst.before',bst),
    derived_bst=binding(draft/'IEEEtran_lgm_display.bst',derived),complete_bst_delta=binding(HERE/'IEEEtran_lgm_display.bst.patch'),
    selected_ieee_reference_venues=venues,allowlist=list(KEYS),helper_sources=helpers,copied_supplement=binding(draft/'supplementary.pdf',supp),
    source_dependency_count=34,refs_metadata_and_all_authors_unchanged=True,non_ieee_authors_not_forced_to_etal=True,
    retained_adopted_clearpage=True,font_or_scientific_change=False,compilation_completed=False,pagination_improved=False,
    final_manuscript=False,Overleaf_updated=False,
    limits=['This is an explicit six-key derived IEEEtran style, not unmodified standard IEEEtran or a universal venue classifier. Future changed keys need review.',
        'Only author display for the six current IEEE journal entries can change; no editors are present in these six. Non-IEEE entries retain the ordinary full author output.',
        'Source fields, scientific content and cited key order are inherited; actual BBL and pagination still require compilation and delta/visual checks.',
        'The original 17-page adopted parent and both preceding candidates remain intact. Supplementary PDF is unchanged and not recompiled.',
        'Official rule support is indexed IEEE Reference Guide text, not a newly downloaded/directly read full PDF. No whole bibliography or science acceptance.'])
create(HERE/'SCOPED_DISPLAY_REVISION.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(report=binding(HERE/'SCOPED_DISPLAY_REVISION.json'),draft=str(draft),main=report['changed_main'],bst=report['derived_bst']),ensure_ascii=False))
