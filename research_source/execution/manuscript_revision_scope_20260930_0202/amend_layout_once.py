"""Three requested local TeX fixes after real compilation; no compilation here."""
from pathlib import Path
import difflib
import hashlib
import json
from datetime import datetime, timezone

HERE = Path(__file__).absolute().parent
NEW = HERE.parent.parent / 'manuscript_evidence_revision_20260930_0202/manuscript'
STAGE = HERE / 'layout_revision_a1'
BASE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_label_revision_20260914\manuscript')
assert not STAGE.exists()
edits = [
    ('tables/evidence_20260930/official_map.tex', b'Official official trapezoidal mAP', b'Official trapezoidal mAP'),
    ('tables/formal_best_fusion_comparison_table.tex', b'\\begin{table*}[!t]', b'\\begin{table*}[!p]'),
    ('main.tex', b'\\FloatBarrier\n% Bibliography balancing must be reviewed after compiling this expanded local draft.',
     b'\\FloatBarrier\n\\clearpage\n% Start the bibliography on a normal page after flushing the remaining floats.')]
planned = []
for name, before, after in edits:
    raw = (NEW / name).read_bytes()
    assert raw.count(before) == 1
    planned.append((name, raw, raw.replace(before, after, 1)))
STAGE.mkdir()
def bind(path):
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
def exclusive(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
changes = []
for name, before, after in planned:
    old_path = STAGE / 'before' / name
    exclusive(old_path, before)
    assert (NEW / name).read_bytes() == before
    (NEW / name).write_bytes(after)
    patch = b''.join(difflib.diff_bytes(difflib.unified_diff, before.splitlines(True), after.splitlines(True),
        fromfile=('before/' + name).encode(), tofile=('after/' + name).encode()))
    patch_path = STAGE / (name.replace('/', '__') + '.patch')
    exclusive(patch_path, patch)
    changes.append(dict(before=bind(old_path), after=bind(NEW / name), diff=bind(patch_path)))
old_fragment = (HERE / 'semantic_results_before_terminology.tex').read_bytes()
new_fragment = (HERE / 'semantic_results.tex').read_bytes()
exclusive(STAGE / 'SEMANTIC_TERMINOLOGY.patch', b''.join(difflib.diff_bytes(difflib.unified_diff,
    old_fragment.splitlines(True), new_fragment.splitlines(True), fromfile=b'fragment_before.tex', tofile=b'fragment_final.tex')))
author = json.loads((HERE / 'AUTHOR_INTEGRATION.json').read_text(encoding='utf-8'))
all_patches = []
for item in author['source_dependencies']:
    target = Path(item['path'])
    relative = target.relative_to(NEW)
    source = BASE / relative
    before = source.read_bytes() if source.is_file() else b''
    after = target.read_bytes()
    if before != after:
        all_patches.append(b''.join(difflib.diff_bytes(difflib.unified_diff, before.splitlines(True), after.splitlines(True),
            fromfile=('base/' + relative.as_posix() if source.is_file() else '/dev/null').encode(),
            tofile=('working/' + relative.as_posix()).encode())))
exclusive(HERE / 'FINAL_COMPLETE_MANUSCRIPT_DIFF.patch', b''.join(all_patches))
report = dict(schema='local-manuscript-layout-revision.v1', utc=datetime.now(timezone.utc).isoformat(),
    reasons=['Root actual first compilation: p11 overflow from three top floats; move historical fusion Table VII to float-page placement.',
        'Root actual p16/17 bibliography preview: start bibliography after FloatBarrier plus clearpage, without shrinking type.',
        'Independent content review: remove duplicate Official in mAP caption.'],
    source=bind(Path(__file__).absolute()), changes=changes,
    full_base_to_final_diff=bind(HERE / 'FINAL_COMPLETE_MANUSCRIPT_DIFF.patch'),
    final_sources=[bind(Path(item['path'])) for item in author['source_dependencies']],
    semantic_terminology_diff=bind(STAGE / 'SEMANTIC_TERMINOLOGY.patch'),
    scientific_values_changed=False, font_or_figure_scale_changed=False,
    compilation_executed=False, old_sources_or_first_compile_artifacts_modified=False)
exclusive(STAGE / 'REVISION.json', (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps(bind(STAGE / 'REVISION.json'), ensure_ascii=True))
