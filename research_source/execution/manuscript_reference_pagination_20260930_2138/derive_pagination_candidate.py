"""One new layout candidate; preserve all scientific and bibliographic bytes."""
from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json, os

HERE = Path(__file__).resolve().parent
EX = HERE.parent
OUT = EX.parent
PARENT = OUT / 'manuscript_camp_dac_context_20260930_1948'
TARGET = OUT / 'manuscript_reference_pagination_20260930_2138'

def binding(p, raw=None):
    p = Path(p)
    if raw is None:
        raw = p.read_bytes()
    return dict(path=str(p.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def create(p, raw):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())

rootpath = PARENT / 'ROOT_CAMP_DAC_CONTEXT_ADOPTION.json'
rootraw = rootpath.read_bytes()
rootbind = binding(rootpath, rootraw)
assert rootbind['bytes'] == 75910
assert rootbind['sha256'] == 'af7fa415e13b790fb26abe6f25e857c5164ec331648de3078d0f3146b9ef15d8'
root = json.loads(rootraw)
assert not TARGET.exists()
TARGET.mkdir()
draft = TARGET / 'manuscript'
draft.mkdir()
assert len(root['source_dependencies']) == 32
copies = []
oldmain = None
for expected in root['source_dependencies']:
    source = Path(expected['path']).resolve()
    relative = source.relative_to((PARENT/'manuscript').resolve())
    assert 0 < expected['bytes'] < 8_000_000
    raw = source.read_bytes()
    assert binding(source, raw) == expected
    destination = draft / relative
    create(destination, raw)
    copies.append(dict(relative=relative.as_posix(), inherited=expected, copied=binding(destination, raw)))
    if relative.as_posix() == 'main.tex':
        oldmain = raw
assert oldmain is not None
old = b'\\FloatBarrier\r\n\\clearpage\r\n% Start the bibliography on a normal page after flushing the remaining floats.\r\n'
new = b'\\FloatBarrier\r\n% Preserve the float barrier without an extra forced page before the bibliography.\r\n'
assert oldmain.count(old) == 1
newmain = oldmain.replace(old, new, 1)
assert newmain.replace(new, old, 1) == oldmain
create(HERE/'main.tex.before', oldmain)
(draft/'main.tex').write_bytes(newmain)
patch = ''.join(difflib.unified_diff(oldmain.decode('utf-8').splitlines(keepends=True),
    newmain.decode('utf-8').splitlines(keepends=True), fromfile='parent/main.tex',
    tofile='candidate/main.tex')).encode('utf-8')
create(HERE/'main.tex.patch', patch)
# Unchanged supplement PDF is explicitly inherited, not compiled in this attempt.
suppbind = next(r for r in root['outputs'] if Path(r['path']).name == 'supplementary.pdf')
suppraw = Path(suppbind['path']).read_bytes()
assert binding(suppbind['path'], suppraw) == suppbind
create(draft/'supplementary.pdf', suppraw)
helpercopies = []
for name in ('compile_main_only.py', 'render_main_only.py'):
    source = EX/'manuscript_camp_dac_context_20260930_1948'/name
    raw = source.read_bytes()
    create(HERE/name, raw)
    helpercopies.append(dict(original=binding(source, raw), copy=binding(HERE/name, raw), unchanged=True))
report = dict(schema='local-reference-pagination-candidate.v1', utc=datetime.now(timezone.utc).isoformat(),
    source=binding(__file__), parent_root=rootbind, source_dependencies=copies,
    changed_main=binding(draft/'main.tex'), old_main=binding(HERE/'main.tex.before'),
    complete_delta=binding(HERE/'main.tex.patch'), unchanged_dependency_count=31,
    inherited_supplement=suppbind, copied_supplement=binding(draft/'supplementary.pdf', suppraw),
    helper_sources=helpercopies,
    scope='Remove only the explicit clearpage immediately after the retained FloatBarrier, and update the adjacent layout comment.',
    scientific_numeric_or_protocol_change=False, bibliography_change=False,
    font_change=False, content_change=False, parent_changed=False,
    compilation_completed=False, pagination_improved=False, working_draft_adopted=False,
    final_manuscript=False, Overleaf_updated=False,
    limits=['This candidate is not an assumed reduction from 17 pages. Only an actual new compilation and affected-page review can establish its outcome.',
        'No prior successful scientific or control suite, numerical transcription review, old ZIP or checkpoint is rerun/read.',
        'All negative results, scientific limitations, pending experiments and citations remain byte-identical outside the local layout delta.',
        'The unchanged six-page supplement is inherited from its adopted parent and is not newly compiled.'])
create(HERE/'PAGINATION_CANDIDATE.json', (json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(report=binding(HERE/'PAGINATION_CANDIDATE.json'), draft=str(draft), changed=report['changed_main']),ensure_ascii=False))
