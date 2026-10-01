"""Adopt the finite local text delta and its real compile/render; no science release."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, re, zipfile, zlib

HERE = Path(__file__).resolve().parent
EX = HERE.parent
OUT = EX.parent
TARGET = OUT / HERE.name
DRAFT = TARGET / 'manuscript'
records = {}

def read(p, limit=262144):
    p = Path(p).resolve()
    before = p.stat()
    assert 0 <= before.st_size <= limit, str(p)
    with p.open('rb') as f:
        raw = f.read(limit+1)
    after = p.stat()
    assert len(raw) == before.st_size and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    d = dict(path=str(p), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    records[str(p)] = d
    return raw, d

def obj(p):
    raw, d = read(p)
    return json.loads(raw), d

def verify(d, limit=262144):
    raw, actual = read(d['path'], limit)
    assert actual == d, d['path']
    return raw

def create(p, raw):
    with Path(p).open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())

args = argparse.ArgumentParser()
args.add_argument('--review', required=True)
args.add_argument('--review-sha256', required=True)
options = args.parse_args()
review, review_d = obj(options.review)
assert review_d['sha256'] == options.review_sha256
assert review['independent_AI_text_review'] is True and review['local_text_delta_review_complete'] is True
assert review['necessary_repair_found'] is False and review['scientific_evidence_or_execution_acceptance'] is False
review_directory = Path(options.review).resolve().parent
review_delivery, review_delivery_d = obj(review_directory/'DELTA_DELIVERY.json')
for d in review_delivery['artifacts']:
    verify(d)
review_artifact_receipt, review_artifact_receipt_d = obj(review_directory/'DELTA_ACTUAL_ARTIFACT_BINDING_TOOL_RETURN.json')
revision, revision_d = obj(HERE/'CONTEXT_REVISION.json')
assert revision_d['sha256'] == '5e81a3af697ea25a1614199bbde6a8962307b2d385b4cdc39bf11601ab2e421c'
changed = {x['name']:x for x in revision['changed']}
dependencies = []
for x in revision['source_dependencies']:
    name = Path(x['copied']['path']).name
    expected = changed[name]['after'] if name in changed else x['copied']
    verify(expected, 8_000_000)
    dependencies.append(expected)
assert len(dependencies) == 32
for x in changed.values():
    verify(x['before'])
    verify(x['patch'])
verify(revision['parent_root'])
verify(revision['citation_research'])
compiles, layouts = [], []
preview_records = []
for kind, name, pages in (('main','main',17), ('supplement','supplementary',6)):
    compile_report, compile_d = obj(HERE/(kind+'_compile_1')/'COMPILE.json')
    assert compile_report['status'] == 'compiled' and compile_report['input_texts_unchanged'] is True
    assert compile_report['compiler_installer_disabled'] is True and compile_report['shell_escape_disabled'] is True
    assert len(compile_report['commands']) == 4
    for c in compile_report['commands']:
        assert c['exit_code'] == 0 and c['document'] == name
        assert '-disable-installer' in c['args']
        if Path(c['args'][0]).name == 'pdflatex.exe':
            assert '-disable-write18' in c['args']
        verify(c['log'])
    for d in compile_report['outputs']:
        verify(d, 8_000_000)
    compiles.append(compile_d)
    layout, layout_d = obj(HERE/(kind+'_preview_1')/'PDF_LAYOUT.json')
    doc = layout['documents'][0]
    assert doc['pdf'] == compile_report['outputs'][0]
    assert len(layout['documents']) == 1 and doc['page_count'] == pages
    assert all(not p['out_of_page_spans'] and p['unresolved_double_question_marks'] == 0 for p in doc['pages'])
    assert not any(any(t in s.lower() for t in ('overfull','undefined','warning:')) for s in doc['latex_diagnostics'])
    assert len(doc['latex_diagnostics']) == (4 if kind == 'main' else 5)
    for p in doc['pages']:
        verify(p['png'], 2_000_000)
        preview_records.append(p['png'])
    verify(doc['extracted_text'])
    layouts.append(dict(binding=layout_d, document=doc))
assert len(preview_records) == 23
main_bbl, main_bbl_d = read(DRAFT/'main.bbl')
supp_bbl, supp_bbl_d = read(DRAFT/'supplementary.bbl')
assert main_bbl.count(b'\\bibitem{') == 44 and supp_bbl.count(b'\\bibitem{') == 3
assert main_bbl.count(b'\\bibitem{camp2024}') == main_bbl.count(b'\\bibitem{dac2024}') == 1
refs, refs_d = read(DRAFT/'refs.bib')
assert len(re.findall(rb'(?m)^@\w+\{', refs)) == 54

observation, observation_d = obj(EX/'heartbeat_observation_20260930_1936/ROOT_OBSERVATION_SEAL.json')
assert observation_d['sha256'] == '332af11d657a53b83054b82fbfbba7f4ea64ac69c20a5cb9397d8e7c18b54720'
for d in observation['unchanged_state_and_closed_log_files']:
    verify(d)
carrier = observation['carrier']
assert verify(dict(path=carrier['path'], bytes=carrier['bytes'], sha256=carrier['sha256'])) == b'0'
assert len(observation['unchanged_state_and_closed_log_files']) == 16
assert all(not Path(p).exists() for p in observation['attempts_absent_at_file_seal'])
assert not (Path('C:/项目/LGM-GAME-Partner-Delivery-20260724/lgm_game_pytorch/analysis/transactions_t6_formal')).exists()

visual = dict(schema='root-local-working-draft-visual-review.v1', utc=datetime.now(timezone.utc).isoformat(),
    reviewer='Root AI actually inspected all 23 original PNGs using tools.view_image, not human review.',
    main_pages=list(range(1,18)), supplementary_pages=list(range(1,7)), previews=preview_records,
    layout_reports=[x['binding'] for x in layouts],
    actual_view_order=['main17','main15-16','main1-4','main5-8','main9-12','main13-14+supp1-3','supp4-6'],
    visible_text_tables_figures_captions_no_new_overlap_or_crop=True,
    main_page17_only_last_two_reference_entries=True,
    disposition='Working-draft readability accepted; the sparse final reference page remains an explicit final-layout task. No font reduction or extra compile.',
    diagnostics={Path(x['document']['pdf']['path']).name:x['document']['latex_diagnostics'] for x in layouts},
    scientific_or_whole_bibliography_validation=False)
visual_path = HERE/'ROOT_VISUAL_REVIEW.json'
create(visual_path,(json.dumps(visual,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
_, visual_d = read(visual_path)
readme = '''# CAMP/DAC context working draft — 30 September 2026

This new local working draft adds two formal references and brief related-work descriptions for CAMP and DAC. It explicitly keeps author-checkpoint re-evaluation and independent training unfinished. No published performance values or new project results were inserted.

The editable manuscript sources, main.pdf (17 pages), supplementary.pdf (6 pages), real compilation records, 23 previews and finite source review are included. Main page 17 contains the last two references only; final page layout remains unfinished. All eight local MiKTeX compiler commands returned 0, with installation and shell escape disabled. Main has four underfull hboxes; supplementary has two underfull hboxes and three underfull vboxes. There are no final overfull/undefined-reference diagnostics or out-of-page text spans.

Scientific numbers, tables, figures, frozen settings, negative results and provenance/statistical limitations are inherited from the adopted parent. This is not a new experiment, complete figure delivery, final submission draft or an Overleaf update. T6, later experiments and final submission advice remain pending. The earlier sealed sources and packages were preserved.
'''
create(TARGET/'README_DELIVERY.md',readme.encode('utf-8'))
_, readme_d = read(TARGET/'README_DELIVERY.md')

package = [(Path(d['path']), 'manuscript/'+str(Path(d['path']).relative_to(DRAFT)).replace('\\','/')) for d in dependencies]
package += [(DRAFT/n,'manuscript/'+n) for n in ('main.pdf','supplementary.pdf','main.bbl','supplementary.bbl')]
package += [(TARGET/'README_DELIVERY.md','README_DELIVERY.md')]
for folder in ('main_preview_1','supplement_preview_1','main_compile_1','supplement_compile_1'):
    package += [(p,'records/'+folder+'/'+p.name) for p in sorted((HERE/folder).iterdir()) if p.is_file()]
for name in ('CONTEXT_REVISION.json','main.tex.patch','refs.bib.patch','derive_context_revision.py',
             'compile_main_only.py','compile_supplement_only.py','render_main_only.py','render_supplement_only.py',
             'ACTUAL_ROOT_TOOLS.json','ROOT_VISUAL_REVIEW.json','adopt_and_package_context.py'):
    package.append((HERE/name,'records/'+name))
package += [(Path(options.review),'review/'+Path(options.review).name)]
package += [(review_directory/n, 'review/'+n) for n in ('DELTA_READ_METHOD.json',
            'DELTA_DELIVERY.json', 'DELTA_ACTUAL_SOURCE_BINDING_TOOL_RETURN.json',
            'DELTA_ACTUAL_ARTIFACT_BINDING_TOOL_RETURN.json', 'DELTA_READ_TOOL_RETURNS.json')]
assert len({name for _,name in package}) == len(package)
member_index = []
zip_path = TARGET/'LGM_GAME_CAMP_DAC_Context_Working_Draft_20260930.zip'
with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p, name in package:
        raw, d = read(p, 8_000_000)
        z.writestr(name,raw)
        member_index.append(dict(member=name,bytes=len(raw),sha256=d['sha256'],crc32=zlib.crc32(raw)&0xffffffff))
with zipfile.ZipFile(zip_path) as z:
    assert z.namelist() == [x['member'] for x in member_index] and z.testzip() is None
    for d in member_index:
        raw = z.read(d['member'])
        assert len(raw) == d['bytes'] and hashlib.sha256(raw).hexdigest() == d['sha256']
        assert z.getinfo(d['member']).CRC == d['crc32']
_, zip_d = read(zip_path, 40_000_000)
_, source_d = read(__file__)
report = dict(schema='root-camp-dac-context-working-draft-adoption.v1',utc=datetime.now(timezone.utc).isoformat(),
    source=source_d, revision=revision_d, parent_root=revision['parent_root'], independent_delta_review=review_d,
    independent_delta_delivery=review_delivery_d, independent_actual_artifact_receipt=review_artifact_receipt_d,
    actual_compiles=compiles, actual_eight_compiler_exits_zero=True,
    actual_render_layouts=[x['binding'] for x in layouts], root_visual=visual_d,
    outputs=[x['document']['pdf'] for x in layouts], source_dependencies=dependencies,
    bibliography_entries=54, main_cited_references=44, supplementary_cited_references=3,
    source_delta_scope='Two related-work sentences plus two pending-evaluation sentences; two formal journal records appended. Thirty other manuscript dependencies inherited byte-identically.',
    new_published_or_project_numeric_values=0, scientific_numeric_validation_replayed=False,
    working_draft_adopted=True, final_manuscript=False, Overleaf_updated=False,
    zip=zip_d, zip_member_count=len(member_index), zip_members=member_index,
    readonly_observation=observation_d, live16_state_and_closed_log_files_unchanged_at_adoption=True,
    new_scientific_execution_or_result=False, execution_released=False, cleanup_authorized=False,
    automatic_followup_retained=True, local_bindings=list(records.values()),
    limits=['Only the local wording/reference delta is newly accepted; all scientific counts, statistics, figures and evidence limitations are inherited.',
        'The independent AI review concerns source delta and two BBL entries, not compilation, visual or scientific validation. Root performed real compilation and visual review separately.',
        'The sparse page17 bibliography remains a final-layout task; the draft is not a submission-ready paper.',
        'Copied compiler helper docstrings retain their historical wording. Actual supplementary commands with the changed shared refs.bib override that wording.',
        'Primary first-page reads confirm method descriptions and identity fields only; last-page pagination and other paper findings rely on the prior citation research, not a fresh whole-paper audit.',
        'The process/GPU snapshot is not future admission or missing independent exit evidence. No science, recovery, native training probe, COM, app closure or lock/state action occurred.',
        'No old large ZIP, model checkpoint, NPZ, cached feature or image-corpus read/hash, and no old scientific/control suite replay.'])
target=TARGET/'ROOT_CAMP_DAC_CONTEXT_ADOPTION.json'
create(target,(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
_, result = read(target)
print(json.dumps(dict(root=result,zip=zip_d,members=len(member_index),pages=[17,6]),ensure_ascii=False))
