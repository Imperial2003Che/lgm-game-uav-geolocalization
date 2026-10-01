"""Derive one new local working draft; no scientific data or sealed parent edits."""
from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json, os

EX = Path(__file__).resolve().parent.parent
OUT = EX.parent
HERE = Path(__file__).resolve().parent
PARENT = OUT / 'manuscript_reference_format_20260930_1538'
TARGET = OUT / 'manuscript_camp_dac_context_20260930_1948'

def binding(p, raw=None):
    p = Path(p)
    if raw is None:
        raw = p.read_bytes()
    return dict(path=str(p.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def create(p, raw):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

authority_path = PARENT / 'ROOT_MANUSCRIPT_REFERENCE_FORMAT_ADOPTION.json'
authority_raw = authority_path.read_bytes()
authority_d = binding(authority_path, authority_raw)
assert authority_d['bytes'] == 19925
assert authority_d['sha256'] == '12acbee506d53a95b873786601eaee87f8d0dede15a1d09639c4a274667590e5'
authority = json.loads(authority_raw)
assert not TARGET.exists(), 'Existing derivative target cannot be replaced'
TARGET.mkdir()
draft = TARGET / 'manuscript'
draft.mkdir()
dependencies = authority['unchanged31_source_dependencies'] + [authority['new_refs']]
assert len(dependencies) == 32
copied = []
old = {}
for expected in dependencies:
    source = Path(expected['path']).resolve()
    relative = source.relative_to((PARENT / 'manuscript').resolve())
    assert 0 < expected['bytes'] < 8_000_000
    raw = source.read_bytes()
    assert binding(source, raw) == expected
    dest = draft / relative
    create(dest, raw)
    copied.append(dict(relative=str(relative), inherited=expected, copied=binding(dest, raw)))
    if relative.as_posix() in ('main.tex', 'refs.bib'):
        old[relative.as_posix()] = raw

main_raw = old['main.tex']
nl = b'\r\n' if main_raw.count(b'\r\n') == main_raw.count(b'\n') else b'\n'
anchor = b'units address the displacement, scale, and appearance changes between' + nl + b'views.'
assert main_raw.count(anchor) == 1
related = (
    b'CAMP combines contrastive attribute mining with position-aware partitioning' + nl +
    b'\\cite{camp2024}. DAC combines a domain space alignment module for' + nl +
    b'fine-grained features with cross-batch scene consistency \\cite{dac2024}.'
)
new_main = main_raw.replace(anchor, anchor + nl + nl + related, 1)
protocol_anchor = b'and efficiency results are not represented as completed experiments here.'
assert new_main.count(protocol_anchor) == 1
protocol = (
    b'Author-checkpoint re-evaluation and independent training for CAMP and DAC' + nl +
    b'remain unfinished. Their published results are distinct from the completed' + nl +
    b'project evaluations.'
)
new_main = new_main.replace(protocol_anchor, protocol_anchor + nl + protocol, 1)

new_entries = b'''\n@article{camp2024,
  author = {Qiong Wu and Yi Wan and Zhi Zheng and Yongjun Zhang and Guangshuai Wang and Zhenyang Zhao},
  title = {{CAMP}: A Cross-View Geo-Localization Method Using Contrastive Attributes Mining and Position-Aware Partitioning},
  journal = {IEEE Trans. Geosci. Remote Sens.},
  year = {2024},
  volume = {62},
  pages = {1--14},
  note = {Art. no. 5637614},
  doi = {10.1109/TGRS.2024.3448499}
}
@article{dac2024,
  author = {Panwang Xia and Yi Wan and Zhi Zheng and Yongjun Zhang and Jiwei Deng},
  title = {Enhancing Cross-View Geo-Localization With Domain Alignment and Scene Consistency},
  journal = {IEEE Trans. Circuits Syst. Video Technol.},
  year = {2024},
  volume = {34},
  number = {12},
  pages = {13271--13281},
  doi = {10.1109/TCSVT.2024.3443510}
}
'''
assert b'@article{camp2024,' not in old['refs.bib'] and b'@article{dac2024,' not in old['refs.bib']
new_refs = old['refs.bib'] + new_entries
# Only new derivative main/refs are edited; copied original bytes are retained externally.
for name, raw in (('main.tex', new_main), ('refs.bib', new_refs)):
    create(HERE / (name + '.before'), old[name])
    (draft / name).write_bytes(raw)
    patch = ''.join(difflib.unified_diff(
        old[name].decode('utf-8').splitlines(keepends=True),
        raw.decode('utf-8').splitlines(keepends=True),
        fromfile='parent/' + name, tofile='new/' + name)).encode('utf-8')
    create(HERE / (name + '.patch'), patch)

citation_path = EX / 'citation_camp_dac_review_20260930_0509/CAMP_DAC_CITATION_REVIEW.json'
cit_raw = citation_path.read_bytes()
cit_d = binding(citation_path, cit_raw)
assert cit_d['sha256'] == '99d268c7c5831d9a571a1fc6c4e06bc8992896b1ec03b746b7451232a5972c9d'
report = dict(schema='local-camp-dac-context-revision.v1', utc=datetime.now(timezone.utc).isoformat(),
    source=binding(__file__), parent_root=authority_d, citation_research=cit_d,
    source_dependencies=copied,
    changed=[dict(name=n, before=binding(HERE/(n+'.before')), after=binding(draft/n),
        patch=binding(HERE/(n+'.patch'))) for n in ('main.tex','refs.bib')],
    unchanged_dependency_count=30,
    library_entries_before=52, library_entries_after=54,
    scope='Two related-work sentences, two pending-evaluation sentences, and two formal journal BibTeX entries only.',
    method='Necessary 32 manuscript source dependencies copied and checked against the adopted parent; no old ZIP, checkpoint, NPZ, cache or image corpus read. Root separately read both saved primary PDF first-page text for the new method descriptions and bibliographic fields.',
    scientific_data_changed=False, old_sources_changed=False, compilation_completed=False,
    final_manuscript=False, Overleaf_updated=False,
    limits=['All scientific numbers, tables, figures, frozen protocols, negative results, incomplete provenance edges and resampling limitations are inherited unchanged.',
        'No literature numerical result is inserted or used to accept a pending local evaluation.',
        'Bibliographic metadata and article pagination derive from the saved primary-source review; this is not a whole-bibliography audit.'])
create(HERE/'CONTEXT_REVISION.json', (json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(report=binding(HERE/'CONTEXT_REVISION.json'), draft=str(draft), changed=report['changed']), ensure_ascii=False))
