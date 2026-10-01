"""Continue only the preserved LF source copy after the CRLF assertion failure."""
from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json, os

HERE = Path(__file__).resolve().parent
EX = HERE.parent
OUT = EX.parent
PARENT = OUT/'manuscript_camp_dac_context_20260930_1948'
TARGET = OUT/'manuscript_reference_pagination_20260930_2138'
DRAFT = TARGET/'manuscript'
def binding(p, raw=None):
    p=Path(p)
    if raw is None: raw=p.read_bytes()
    return dict(path=str(p.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def create(p, raw):
    with p.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
rootpath=PARENT/'ROOT_CAMP_DAC_CONTEXT_ADOPTION.json'
rootraw=rootpath.read_bytes()
rootbind=binding(rootpath,rootraw)
assert rootbind['sha256']=='af7fa415e13b790fb26abe6f25e857c5164ec331648de3078d0f3146b9ef15d8'
root=json.loads(rootraw)
copies=[]
for expected in root['source_dependencies']:
    relative=Path(expected['path']).resolve().relative_to((PARENT/'manuscript').resolve())
    actual=binding(DRAFT/relative)
    assert actual['bytes']==expected['bytes'] and actual['sha256']==expected['sha256']
    copies.append(dict(relative=relative.as_posix(),inherited=expected,copied=actual))
assert len(copies)==32
oldmain=(DRAFT/'main.tex').read_bytes()
assert b'\r' not in oldmain
old=b'\\FloatBarrier\n\\clearpage\n% Start the bibliography on a normal page after flushing the remaining floats.\n'
new=b'\\FloatBarrier\n% Preserve the float barrier without an extra forced page before the bibliography.\n'
assert oldmain.count(old)==1
newmain=oldmain.replace(old,new,1)
assert newmain.replace(new,old,1)==oldmain
create(HERE/'main.tex.before',oldmain)
(DRAFT/'main.tex').write_bytes(newmain)
patch=''.join(difflib.unified_diff(oldmain.decode().splitlines(keepends=True),newmain.decode().splitlines(keepends=True),fromfile='parent/main.tex',tofile='candidate/main.tex')).encode()
create(HERE/'main.tex.patch',patch)
suppbind=next(r for r in root['outputs'] if Path(r['path']).name=='supplementary.pdf')
suppraw=Path(suppbind['path']).read_bytes()
assert binding(suppbind['path'],suppraw)==suppbind
create(DRAFT/'supplementary.pdf',suppraw)
helpers=[]
for name in ('compile_main_only.py','render_main_only.py'):
    src=EX/'manuscript_camp_dac_context_20260930_1948'/name
    raw=src.read_bytes();create(HERE/name,raw)
    helpers.append(dict(original=binding(src,raw),copy=binding(HERE/name,raw),unchanged=True))
report=dict(schema='local-reference-pagination-candidate.v2',utc=datetime.now(timezone.utc).isoformat(),source=binding(__file__),
    parent_root=rootbind,source_dependencies=copies,changed_main=binding(DRAFT/'main.tex'),old_main=binding(HERE/'main.tex.before'),
    complete_delta=binding(HERE/'main.tex.patch'),unchanged_dependency_count=31,inherited_supplement=suppbind,
    copied_supplement=binding(DRAFT/'supplementary.pdf',suppraw),helper_sources=helpers,
    predecessor_failure='Consumed derive_pagination_candidate.py exited1 at CRLF-only anchor after source copies; main stayed parent-exact. The source, tool return and partial directory are preserved.',
    continuation_method='Actual main has 856 LF and no CR; new script pins all copied source bytes once, then applies only the exact LF anchor. No replay of predecessor derivation.',
    scope='Remove only explicit clearpage after retained FloatBarrier; update adjacent layout comment.',scientific_numeric_or_protocol_change=False,
    bibliography_change=False,font_change=False,content_change=False,parent_changed=False,compilation_completed=False,pagination_improved=False,
    working_draft_adopted=False,final_manuscript=False,Overleaf_updated=False,
    limits=['Candidate outcome requires actual compilation and affected-page visual review; no assumed 16 pages.',
        'All scientific content, negative results and pending work inherit the adopted parent unchanged.',
        'Six-page supplement PDF inherited unchanged; not newly compiled. No scientific/control suite, old ZIP or checkpoint read/run.'])
create(HERE/'PAGINATION_CANDIDATE.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(report=binding(HERE/'PAGINATION_CANDIDATE.json'),draft=str(DRAFT),changed=report['changed_main']),ensure_ascii=False))
