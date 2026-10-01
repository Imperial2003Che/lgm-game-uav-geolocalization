"""Finish preserved scope candidate after protected-IEEE field parser rejection."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re
HERE=Path(__file__).resolve().parent;EX=HERE.parent;OUT=EX.parent
DRAFT=OUT/'manuscript_ieee_reference_scope_20260930_2155/manuscript'
PARENT=OUT/'manuscript_ieee_reference_display_20260930_2145/manuscript'
KEYS=('lpn2022','sdpl2024','vlgeo2026','eagle2025','r2ploc2025','rendering2025')
def binding(p,raw=None):
    p=Path(p)
    if raw is None:raw=p.read_bytes()
    return dict(path=str(p.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def create(p,raw):
    with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def field(s,name):
    m=re.search(r'\b'+re.escape(name)+r'\s*=\s*\{',s);assert m
    start=m.end();depth=1
    for i in range(start,len(s)):
        if s[i]=='{':depth+=1
        elif s[i]=='}':
            depth-=1
            if depth==0:return s[start:i]
    raise AssertionError('unterminated field')
ap=EX/'manuscript_ieee_reference_display_20260930_2145/AUTHOR_DISPLAY_REVISION.json'
araw=ap.read_bytes();assert binding(ap,araw)['sha256']=='b52f16e381b3ed8ebdb714fd610c18bee502572520f974bb4c88c357e73c684b'
a=json.loads(araw)
expected=[r['copied'] if r['relative']!='main.tex' else a['changed_main'] for r in a['source_dependencies']]+[a['new_control']]
copies=[]
for e in expected:
    relative=Path(e['path']).relative_to(PARENT);p=DRAFT/relative;raw=p.read_bytes()
    comparison=raw.replace(b'\\bibliographystyle{IEEEtran_lgm_display}',b'\\bibliographystyle{IEEEtran}',1) if relative.as_posix()=='main.tex' else raw
    assert len(comparison)==e['bytes'] and hashlib.sha256(comparison).hexdigest()==e['sha256']
    copies.append(dict(relative=relative.as_posix(),inherited=e,actual=binding(p,raw)))
bst_before=(HERE/'IEEEtran.bst.before').read_bytes();bst_new=(DRAFT/'IEEEtran_lgm_display.bst').read_bytes()
guard=(b'          cite$ "lpn2022" = cite$ "sdpl2024" = or\n'+b'          cite$ "vlgeo2026" = or cite$ "eagle2025" = or\n'+b'          cite$ "r2ploc2025" = or cite$ "rendering2025" = or and\n')
if b'\r\n' in bst_before:guard=guard.replace(b'\n',b'\r\n')
assert bst_new.count(guard)==1 and bst_new.replace(guard,b'',1)==bst_before
refs=(DRAFT/'refs.bib').read_text(encoding='utf-8');venues=[]
for key in KEYS:
    m=re.search(r'@\w+\{'+key+r',(.*?)(?=\n@|\Z)',refs,re.S);assert m
    journal_raw=field(m[1],'journal');journal_display=journal_raw.replace('{','').replace('}','')
    authors=field(m[1],'author');names=re.split(r'\s+and\s+',authors.strip())
    assert journal_display.startswith('IEEE ') and len(names)>6
    assert not re.search(r'\beditor\s*=',m[1])
    venues.append(dict(key=key,journal_raw=journal_raw,journal_display=journal_display,author_count=len(names),no_editor_field=True))
supp=(PARENT/'supplementary.pdf').read_bytes();assert binding(PARENT/'supplementary.pdf',supp)==a['copied_supplement']
create(DRAFT/'supplementary.pdf',supp)
helpers=[]
for name in ('compile_main_only.py','render_main_only.py'):
    src=EX/'manuscript_ieee_reference_display_20260930_2145'/name;raw=src.read_bytes()
    create(HERE/name,raw);helpers.append(dict(parent=binding(src,raw),copy=binding(HERE/name,raw)))
report=dict(schema='local-scoped-ieee-author-display-revision.v2',utc=datetime.now(timezone.utc).isoformat(),source=binding(__file__),
    preceding_candidate=binding(ap,araw),adopted_parent=a['parent_root'],source_dependencies=copies,
    changed_main=binding(DRAFT/'main.tex'),main_delta=binding(HERE/'main.tex.patch'),preserved_bst=binding(HERE/'IEEEtran.bst.before',bst_before),
    derived_bst=binding(DRAFT/'IEEEtran_lgm_display.bst',bst_new),complete_bst_delta=binding(HERE/'IEEEtran_lgm_display.bst.patch'),
    selected_ieee_reference_venues=venues,allowlist=list(KEYS),helper_sources=helpers,copied_supplement=binding(DRAFT/'supplementary.pdf',supp),
    source_dependency_count=34,refs_metadata_and_all_authors_unchanged=True,non_ieee_authors_not_forced_to_etal=True,
    retained_adopted_clearpage=True,font_or_scientific_change=False,compilation_completed=False,pagination_improved=False,
    final_manuscript=False,Overleaf_updated=False,
    predecessor_failure='Consumed derive_scoped_author_display.py tool4325bc exited1 after files and BST delta were written, at journal regex that stopped at nested {IEEE}; files/source preserved and not replayed.',
    continuation='New braced-depth reader recognizes protected IEEE without changing field bytes. Once binds 33 copied inputs, validates exact three-line BST addition, then copies previously unreached helpers and unchanged supplement.',
    limits=['Explicit six-key derived IEEEtran style, not unmodified standard style or general venue classifier; future changed keys need review.',
        'Only these six IEEE journals with >6 authors and no editor fields use first-author et al. Other entries retain ordinary full author output.',
        'Actual BBL and pagination require compilation/delta/visual review. Original17-page adopted parent and all preceding candidates remain unchanged.',
        'Six-page supplement is inherited without compilation. Official rule support is IEEE search-index text, not a full live PDF direct read.',
        'No whole bibliography metadata or scientific validation; all negative results, frozen protocol and pending experiments unchanged.'])
create(HERE/'SCOPED_DISPLAY_REVISION.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(report=binding(HERE/'SCOPED_DISPLAY_REVISION.json'),draft=str(DRAFT),venues=venues),ensure_ascii=False))
