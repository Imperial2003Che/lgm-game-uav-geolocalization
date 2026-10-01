"""One new working-draft delivery; no scientific execution or old ZIP reads."""
import hashlib
import json
import os
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914')
EX = OUT / 'execution'
NAME = 'manuscript_ieee_reference_scope_20260930_2155'
WORK = EX / NAME
DRAFT = OUT / NAME
MANUSCRIPT = DRAFT / 'manuscript'
REVIEW = EX / 'ieee_reference_author_display_review_20260930_2142'
PARENT = OUT / 'manuscript_camp_dac_context_20260930_1948'
PARENT_EX = EX / PARENT.name
OBS = EX / 'heartbeat_observation_20260930_2130'
ZIP = DRAFT / 'LGM_GAME_Reference_Layout_Working_Draft_20260930.zip'
ROOT = DRAFT / 'ROOT_REFERENCE_LAYOUT_ADOPTION.json'
UTC = lambda: datetime.now(timezone.utc).isoformat()
bound = {}
members = {}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read_bound(path, expected=None, limit=20_000_000):
    path = Path(path)
    size = path.stat().st_size
    assert 0 <= size <= limit, (str(path), size, limit)
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    assert len(raw) == size and len(raw) <= limit
    record = {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}
    if expected is not None:
        assert record == {k: expected[k] for k in record}, (record, expected)
    prior = bound.setdefault(str(path), record)
    assert prior == record
    return raw, record

def pinned_json(path, digest):
    raw, record = read_bound(path, limit=200_000)
    assert record['sha256'] == digest, record
    return json.loads(raw), record

def write_new(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return read_bound(path, limit=200_000)[1]

def add(path, name, expected=None):
    assert name not in members and not name.startswith('/') and '..' not in Path(name).parts
    raw, record = read_bound(path, expected)
    members[name] = (raw, record)
    return record

assert not ZIP.exists() and not ROOT.exists()
revision, revision_record = pinned_json(WORK / 'SCOPED_DISPLAY_REVISION.json', '4bcb8181980aaf43a3aac46b2fcd5f526a0c38fa121b1484ccafc68bfe6bd083')
parent, parent_record = pinned_json(PARENT / 'ROOT_CAMP_DAC_CONTEXT_ADOPTION.json', 'af7fa415e13b790fb26abe6f25e857c5164ec331648de3078d0f3146b9ef15d8')
independent, independent_record = pinned_json(REVIEW / 'SOURCE_SCOPE_ADDENDUM.json', '8bcdbc8235c9f8b2a95409b461bfb87210b0b4421ceccbc7107b6503baf5dbfd')
observation, observation_record = pinned_json(OBS / 'ROOT_OBSERVATION_SEAL.json', 'f0fb009f6ac62b5fad95939e42027e97c1742c34bc215ae4094e646ec84212b4')
compile_raw, compile_record = read_bound(WORK / 'compile_main_attempt_1/COMPILE.json', limit=200_000)
compile_report = json.loads(compile_raw)
assert len(compile_report['commands']) == 4
assert all(item['exit_code'] == 0 for item in compile_report['commands'])
assert compile_report['input_texts_unchanged'] is True
assert compile_report['compiler_installer_disabled'] is True and compile_report['shell_escape_disabled'] is True
assert independent['bbl_delta']['regular_reference_count'] == 44
assert independent['source_review']['refs_byte_identical_to_adopted_1948'] is True
assert set(independent['bbl_delta']['exactly_six_entry_bodies_changed']) == set(revision['allowlist'])
assert len(independent['bbl_delta']['other_38_entry_bodies_exact_byte_unchanged']) == 38
for item in independent['inputs']:
    read_bound(item['path'], item, limit=200_000)

sources = []
for item in revision['source_dependencies']:
    path = Path(item['actual']['path'])
    assert path.is_relative_to(MANUSCRIPT)
    assert path.relative_to(MANUSCRIPT).as_posix() == item['relative'].replace('\\', '/')
    sources.append(add(path, 'manuscript/' + path.relative_to(MANUSCRIPT).as_posix(), item['actual']))
sources.append(add(revision['derived_bst']['path'], 'manuscript/IEEEtran_lgm_display.bst', revision['derived_bst']))
assert len(sources) == 34
main = members['manuscript/main.tex'][0]
restored = main.replace(b'\\bstctlcite{IEEEAuthorDisplayControl}\n', b'', 1)
restored = restored.replace(b'\\bibliographystyle{IEEEtran_lgm_display}', b'\\bibliographystyle{IEEEtran}', 1)
restored = restored.replace(b'\\bibliography{ieee_controls,refs}', b'\\bibliography{refs}', 1)
assert sha(restored) == '5f20b79e9dc3e369b5b4cc8fee86b66cff8acbceb5bf0016bdbcc570993a3a85'
assert b'\\clearpage\n' in main
assert members['manuscript/refs.bib'][1]['sha256'] == '8403472bc99049a410e0c17b5dd1860fcd4bab7919ed4809e5a4258d3226d06a'
old_bst, old_bst_record = read_bound(WORK / 'IEEEtran.bst.before', limit=200_000)
assert old_bst_record['sha256'] == '314f0ece704568faf827011bac498650691b2b5ee06320720830e782416d5a5f'
new_bst = members['manuscript/IEEEtran_lgm_display.bst'][0]
guard = (b'          cite$ "lpn2022" = cite$ "sdpl2024" = or\n'
         b'          cite$ "vlgeo2026" = or cite$ "eagle2025" = or\n'
         b'          cite$ "r2ploc2025" = or cite$ "rendering2025" = or and\n')
assert new_bst.count(guard) == 1 and new_bst.replace(guard, b'', 1) == old_bst

layout_raw, layout_record = read_bound(WORK / 'main_preview_1/PDF_LAYOUT.json', limit=200_000)
layout = json.loads(layout_raw)['documents'][0]
assert layout['page_count'] == 16 and len(layout['pages']) == 16
assert all(not page['out_of_page_spans'] and page['unresolved_double_question_marks'] == 0 for page in layout['pages'])
old_layout, old_layout_record = pinned_json(PARENT_EX / 'main_preview_1/PDF_LAYOUT.json', 'b1f5dd378bc2c2e250e1931267f5a1695f859a1874ea011a1dcc081bedb7ecc1')
old_pages = old_layout['documents'][0]['pages']
assert all(a['png']['sha256'] == b['png']['sha256'] for a, b in zip(layout['pages'][:15], old_pages[:15]))
parent_visual, parent_visual_record = pinned_json(PARENT_EX / 'ROOT_VISUAL_REVIEW.json', '4b32cba043950f713fc475233e256c87fcd999cd5312d4612a8ac675fa9c4d52')
pdf_record = add(layout['pdf']['path'], 'manuscript/main.pdf', layout['pdf'])
assert pdf_record['sha256'] == '5c9ff9ab71417826490ea101cd23088094b55f7a42d2acbf22acb3567e82495f'
supp_path = MANUSCRIPT / 'supplementary.pdf'
supp_record = add(supp_path, 'manuscript/supplementary.pdf', {'path': str(supp_path), 'bytes': 273344, 'sha256': '34b94ffde568cb2f32b72f7b0905bec28cd2bdc83c8b30728b21cabad0a7e2f3'})
for page in layout['pages']:
    add(page['png']['path'], f"previews/main-{page['number']:02d}.png", page['png'])
visual_record = write_new(WORK / 'ROOT_VISUAL_REVIEW.json', {
    'schema': 'root-scoped-reference-layout-visual-review.v1', 'utc': UTC(),
    'new_main_layout': layout_record, 'parent_layout': old_layout_record, 'parent_actual_visual_review': parent_visual_record,
    'new_main_pages': 16, 'first_15_new_png_hashes_equal_saved_adopted_parent': True,
    'actual_original_viewed_final_main_pages_this_turn': [16],
    'page_16_findings': 'Two complete columns; references 1-44 remain ordered and complete, including the final two entries. No visible overlapping or clipped text in the actual original preview.',
    'unchanged_pages_visual_scope': 'First 15 pages inherit the adopted parent actual visual review through exact saved PNG hashes; old PNG files were not reread or rehashed. The unchanged six-page supplement inherits the adopted review and was not recompiled or freshly viewed.',
    'all_main_saved_layout_spans_inside_page': True, 'unresolved_double_question_marks': 0,
    'font_and_scientific_source_unchanged': True, 'new_all_page_manual_or_AI_visual_review_claimed': False,
    'reviewer': 'root AI, not human review'})

evidence_names = ['SCOPED_DISPLAY_REVISION.json', 'ROOT_ACTUAL_TOOLS.json', 'ROOT_RULE_INDEX_EVIDENCE.json', 'ROOT_VISUAL_REVIEW.json', 'main.tex.patch', 'IEEEtran_lgm_display.bst.patch', 'derive_scoped_author_display.py', 'finalize_braced_venue_fields.py', 'compile_main_only.py', 'render_main_only.py', 'adopt_and_package_scoped.py', 'IEEEtran.bst.before']
for name in evidence_names:
    add(WORK / name, 'evidence/root/' + name)
add(WORK / 'main_preview_1/PDF_LAYOUT.json', 'evidence/root/PDF_LAYOUT.json', layout_record)
add(WORK / 'compile_main_attempt_1/COMPILE.json', 'evidence/compile/COMPILE.json', compile_record)
for command in compile_report['commands']:
    add(command['log']['path'], 'evidence/compile/' + Path(command['log']['path']).name, command['log'])
for filename in ['main.bbl', 'main.blg', 'main.log']:
    add(MANUSCRIPT / filename, 'evidence/compile/' + filename)
for name in ['SOURCE_SCOPE_ADDENDUM.json', 'check_scoped_source_and_bbl_delta.py', 'SCOPE_DELTA_ACTUAL_TOOL_RECEIPT.json', 'IEEE_AUTHOR_DISPLAY_REVIEW.md', 'SELECTED_AUTHORS_AND_LOCAL_BST.json', 'LOCAL_READ_ACTUAL_TOOL_RECEIPT.json']:
    add(REVIEW / name, 'evidence/independent/' + name)
add(OBS / 'ROOT_OBSERVATION_SEAL.json', 'evidence/observation/ROOT_OBSERVATION_SEAL.json', observation_record)
add(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json', 'evidence/observation/OBSERVATION_WRAPPER_INCLUDED.json', observation['observation'])
add(observation['stopped_observation']['path'], 'evidence/observation/STOPPED_OBSERVATION.json', observation['stopped_observation'])
add(OBS / 'ACTUAL_TOOL_RETURNS.json', 'evidence/observation/ACTUAL_TOOL_RETURNS.json')

# Current file bytes are checked again only; no fresh OS, GPU or commit admission is implied.
for item in observation['unchanged_state_and_closed_log_files']:
    read_bound(item['path'], item, limit=200_000)
carrier = observation['carrier']
raw, carrier_record = read_bound(carrier['path'], carrier)
assert raw == b'0'
assert all(not Path(path).exists() for path in observation['attempts_absent_at_file_seal'])
assert not Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal').exists()

readme = '''# LGM-GAME reference-layout working draft, 2026-09-30

This local working draft has a newly compiled 16-page main PDF and the unchanged,
previously adopted six-page supplement. All scientific text, numbers, fonts,
figures and negative-result limitations inherit the adopted 1948 working draft.
It is not the final submission manuscript; pending experiments are still pending.
Overleaf has not been updated, and the previous delivered archives are preserved.

The main bibliography keeps the 44 references and their order. Six current IEEE
journal references with more than six authors display the first author and et al.
The complete author metadata remains in refs.bib. Other references, including
CLIP, Mixed Precision Training and MobileGeo, retain their original author display.
The derived IEEEtran_lgm_display.bst preserves the original copyright and differs
only by a three-line six-key guard. This is an explicit current-key list, not a
general publication classifier. New reference keys need a separate format review.
Include ieee_controls.bib and the derived BST when rebuilding main.tex; the
supplement continues to use the original style. No smaller fonts were introduced.

Installed MiKTeX compiled main.tex with pdflatex-bibtex-pdflatex-pdflatex: all four
commands returned 0, automatic installation and shell escape were disabled.
The final main log has four underfull hbox diagnostics and no overfull or undefined
reference diagnostics. This is not a zero-diagnostic claim. Supplement diagnostics
and the prior independent evidence limitations are inherited, not rerun.

All 16 new main previews were rendered. The first 15 exactly match the saved
adopted-parent PNG hashes and inherit its visual review; the changed last page was
actually inspected at original resolution by the root AI. The six supplement
pages inherit the adopted visual review. This does not claim new human review.
The independent AI review checks source and bibliography differences; it did not
independently compile, render or inspect PDFs.

The clearpage-removal trial remained 17 pages with poor column balance and was
not adopted. The global author-shortening trial reached 16 pages but included
non-IEEE references and was not adopted. The final scoped derivation first failed
on a nested-brace field parser after writing partial files; that source and
failure are retained. A different continuation parsed those six protected fields
and finalized the candidate. No used derivation or passing suite was replayed.

The current observation is a historical snapshot, not scientific execution
permission. No release, intent, native scientific probe, GPU measurement,
COM automation, cleanup, lock or scientific-state mutation occurred. T6, LOHO,
explanation figures, later baseline experiments and complete efficiency results
still require real execution under the unchanged original admission contracts.

This ZIP contains editable sources, PDFs, previews and bounded evidence. The
external ROOT_REFERENCE_LAYOUT_ADOPTION.json binds the ZIP and its members;
the root report is outside the ZIP to avoid circular self-binding.
'''
with (DRAFT / 'README.md').open('xb') as stream:
    stream.write(readme.encode('utf-8')); stream.flush(); os.fsync(stream.fileno())
add(DRAFT / 'README.md', 'README.md')
with zipfile.ZipFile(ZIP, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name, (raw, _) in members.items():
        archive.writestr(name, raw)
zip_member_records = []
with zipfile.ZipFile(ZIP, 'r') as archive:
    infos = archive.infolist()
    assert len(infos) == len(members) and {info.filename for info in infos} == set(members)
    for info in infos:
        actual = archive.read(info.filename)
        expected_raw, expected = members[info.filename]
        assert actual == expected_raw
        assert info.file_size == expected['bytes'] and sha(actual) == expected['sha256']
        assert info.CRC == (zlib.crc32(actual) & 0xffffffff)
        zip_member_records.append({'name': info.filename, 'bytes': len(actual), 'sha256': sha(actual), 'crc32': info.CRC})
_, zip_record = read_bound(ZIP, limit=30_000_000)
root_report = {
    'schema': 'root-reference-layout-working-draft-adoption.v1', 'utc': UTC(),
    'adopted_parent': parent_record, 'scoped_source_revision': revision_record,
    'independent_source_and_bbl_scope_review': independent_record,
    'observation_snapshot': observation_record, 'root_visual_review': visual_record,
    'source_dependencies': sources, 'source_dependency_count': 34,
    'main_pdf': pdf_record, 'main_pages': 16, 'supplementary_pdf': supp_record, 'supplementary_pages': 6,
    'supplement_recompiled_this_turn': False, 'compile_report': compile_record,
    'final_main_compile_command_count': 4, 'final_main_compile_all_exit_zero': True,
    'main_underfull_hbox_count': 4, 'main_overfull_or_undefined': False,
    'author_metadata_complete_and_unchanged': True, 'regular_reference_count': 44,
    'reference_order_unchanged': True, 'six_current_ieee_keys_with_shortened_display': revision['allowlist'],
    'other_38_bbl_entry_bodies_byte_unchanged': True, 'six_title_to_end_suffixes_whitespace_normalized_equal': True,
    'fonts_and_scientific_source_restored_exact_parent_sha256': sha(restored),
    'zip': zip_record, 'zip_members': zip_member_records,
    'bounded_file_bindings': list(bound.values()),
    'current_16_state_log_bytes_and_carrier_unchanged_at_packaging': True,
    'new_os_or_gpu_or_commit_admission_at_packaging': False,
    'working_draft_adopted': True, 'final_submission_manuscript': False,
    'new_scientific_result': False, 'scientific_execution_released': False,
    'new_native_figures': False, 'Overleaf_updated': False, 'automation_complete': False,
    'trial_outcomes': {
        'LF_clearpage_candidate': 'Original CRLF anchor derivation exit1; different LF continuation exit0. Compiled 17 pages, poor column balance; not adopted.',
        'global_display_candidate': 'Compiled 16 pages; non-IEEE author-display scope too broad; not adopted. Independent checker had a wrapped-name parser failure with a cached-text correction, not a rerun.',
        'scoped_display_candidate': 'First protected-brace parser derivation exit1 with partial files retained; different scoped finalizer exit0; final four compiler commands exit0 and 16 pages. Source review and working-draft delivery are separate from scientific execution.'},
    'limits': ['Root and independent reviewers are AI, not human reviewers.',
        'The current six-key venue decisions use preserved source metadata and a limited official indexed reference rule, not a new complete bibliography audit.',
        'The final compiler helper checks text inputs; root additionally checks the derived BST bytes against the pinned source before packaging. This is not arbitrary-writer exclusion.',
        'Only changed final main page 16 was actually viewed for this final candidate; exact saved hashes inherit the adopted review for the other 15 and the unchanged supplement.',
        'All adopted-parent scientific limitations, negative results, pending experiments and evidence-chain gaps remain. Old large archives, model weights, NPZ/cache and dataset image corpora were not reread or rehashed.']}
root_record = write_new(ROOT, root_report)
print(json.dumps({'root': root_record, 'zip': zip_record, 'zip_member_count': len(members), 'input_and_zip_binding_count': len(root_report['bounded_file_bindings']), 'main_pdf': pdf_record, 'supplementary_pdf': supp_record}, ensure_ascii=False))
