"""Adopt the compiled local manuscript, without reopening old science assets."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

HERE=Path(__file__).resolve().parent
EX=HERE.parent
OUT=EX.parent
DEST=OUT/'manuscript_evidence_revision_20260930_0202'
AUTHOR=EX/'manuscript_revision_scope_20260930_0202'
REVIEW=EX/'manuscript_evidence_review_20260930_0202'
OBS=EX/'heartbeat_observation_20260930_020247156'
pins={}
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def pin(p):
    p=Path(p)
    assert p.suffix.lower() not in ('.pt','.pth','.npz'),str(p)
    if str(p) not in pins:
        b=p.read_bytes()
        assert len(b)<25_000_000,str(p)
        pins[str(p)]={'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    return pins[str(p)]
def verify(b):
    a=pin(b['path'])
    assert (a['bytes'],a['sha256'])==(b['bytes'],b['sha256']),b['path']
    return a
def bindings(obj):
    if isinstance(obj,dict):
        if {'path','bytes','sha256'}<=obj.keys(): yield obj
        for v in obj.values(): yield from bindings(v)
    elif isinstance(obj,list):
        for v in obj: yield from bindings(v)

author=load(AUTHOR/'DELIVERY.json')
content=load(REVIEW/'CONTENT_REVIEW.json')
independent=load(REVIEW/'DELIVERY.json')
method=load(REVIEW/'REVIEW_METHOD_ADDENDUM.json')
numeric=load(REVIEW/'NUMERIC_TRANSCRIPTION_REVIEW.json')
query=load(REVIEW/'query_review/QUERY_FRAGMENT_REVIEW.json')
assert content['passed'] and independent['passed'] and not content['unresolved_content_findings']
assert len(content['seal_checks'])==50 and all(c['passed'] for c in content['seal_checks'])
assert numeric['passed'] and numeric['scalar_count']==484 and query['passed']
assert method['checks_rerun'] is False and 'AI agent' in method['corrected_method']
for b in method['original_bindings']+content['final_text_source_bindings']+independent['review_artifacts']:
    verify(b)
verify(independent['report'])
revision=load(AUTHOR/'layout_revision_a1/REVISION.json')
for b in revision['final_sources']: verify(b)
assert len(revision['final_sources'])==32

compile_report=load(HERE/'attempt_2/COMPILE.json')
assert compile_report['status']=='compiled' and compile_report['input_texts_unchanged']
assert len(compile_report['commands'])==8 and all(c['exit_code']==0 for c in compile_report['commands'])
for b in compile_report['input_texts']+compile_report['outputs']: verify(b)
visual=load(HERE/'ROOT_VISUAL_REVIEW.json')
assert visual['all_final_pages_actually_viewed'] and visual['accepted_pages']==22
layout=load(HERE/'preview_2/PDF_LAYOUT.json')
assert [d['page_count'] for d in layout['documents']]==[16,6]
for d in layout['documents']:
    verify(d['pdf'])
    assert all('Overfull' not in s and 'undefined' not in s.lower() for s in d['latex_diagnostics'])
    for p in d['pages']:
        assert not p['out_of_page_spans'] and p['unresolved_double_question_marks']==0
        verify(p['png'])

package=load(HERE/'PACKAGE_CHECK.json')
manifest=load(DEST/'PACKAGE_MANIFEST.json')
assert package['passed'] and len(package['members'])==185 and len(manifest['members'])==184
verify(package['archive']);verify(package['manifest'])
members={m['archive_path']:m for m in package['members']}
for b in manifest['members']:
    verify(b)
    z=members[b['archive_path']]
    assert (z['bytes'],z['sha256'])==(b['bytes'],b['sha256'])
assert members['PACKAGE_MANIFEST.json']['sha256']==package['manifest']['sha256']
# Only the eight packaged small data files are checked against already read
# authorities. Do not recursively reopen their referenced models or old suites.
authority_paths=[AUTHOR/'AUTHOR_INTEGRATION.json',REVIEW/'NUMERIC_TRANSCRIPTION_REVIEW.json',REVIEW/'query_review/QUERY_FRAGMENT_REVIEW.json',EX/'pipeline_post_robustness_audit_20260929_1448/ROOT_POST_ROBUSTNESS_ADOPTION.json']
known={}
for p in authority_paths:
    obj=load(p);pin(p)
    for b in bindings(obj): known[str(Path(b['path']))]=b
data=[]
for b in manifest['members']:
    if b['archive_path'].startswith('source_data/'):
        expected=known.get(str(Path(b['path'])))
        assert expected is not None,b['path']
        assert (b['bytes'],b['sha256'])==(expected['bytes'],expected['sha256'])
        data.append({'archive_path':b['archive_path'],'authority_binding':expected})
assert len(data)==8

observation=load(OBS/'OBSERVATION_WRAPPER_INCLUDED.json')
assert len(observation['files'])==16
for b in observation['files']: verify(b)
verify(observation['carrier'])
assert Path(observation['carrier']['path']).read_bytes()==b'0'
for p in (OBS/'ROOT_OBSERVATION_SEAL.json',OBS/'OBSERVATION_WRAPPER_INCLUDED.json'):
    pin(p)
for p in (AUTHOR/'DELIVERY.json',REVIEW/'DELIVERY.json',REVIEW/'CONTENT_REVIEW.json',REVIEW/'REVIEW_METHOD_ADDENDUM.json',HERE/'attempt_1/COMPILE.json',HERE/'attempt_2/COMPILE.json',HERE/'ROOT_VISUAL_REVIEW.json',HERE/'PACKAGE_CHECK.json',HERE/'preview_2/PDF_LAYOUT.json',Path(__file__)):
    pin(p)

result={
 'schema':'root-local-working-manuscript-adoption.v1',
 'utc':datetime.now(timezone.utc).isoformat(),
 'accepted':True,
 'scope':'Actual compiled local working manuscript, existing-evidence transcription, independent AI content review, root PDF visual review and new ZIP delivery. No scientific or submission-final acceptance.',
 'archive':package['archive'],'pdfs':compile_report['outputs'],'page_counts':[16,6],
 'source_dependencies':32,'new_tables':5,'independent_displayed_scalar_checks':484,
 'independent_final_checks_inherited_not_rerun':50,
 'independent_review':pin(REVIEW/'CONTENT_REVIEW.json'),
 'mandatory_method_addendum':pin(REVIEW/'REVIEW_METHOD_ADDENDUM.json'),
 'producer_delivery':pin(AUTHOR/'DELIVERY.json'),
 'root_visual_review':pin(HERE/'ROOT_VISUAL_REVIEW.json'),
 'package_check':pin(HERE/'PACKAGE_CHECK.json'),
 'archive_validation':'The root packager actually read all 185 ZIP members once, checking decompression CRC plus exact size/SHA and member set. This adoption verifies its bound report and archive hash; it does not repeat decompression.',
 'packaged_small_data_authorities':data,
 'compilation':'Two actual full pdflatex/bibtex/pdflatex/pdflatex passes per document; final eight commands exit 0. Installed MiKTeX, automatic installation and shell escape disabled. No producer build.py invocation.',
 'resolved_layout_findings':['Original 17-page main had an overfull float page and bibliography blank area; three preserved source amendments changed table placement, bibliography clearpage and duplicate caption text. No numeric or font-size change.','Final main16/supp6 all 22 PNG pages were actually viewed at original detail by root.'],
 'remaining_diagnostics':'Final main has four Underfull hbox messages; supplement has two Underfull hbox and three Underfull vbox messages. No Overfull/undefined citations or missing cross-references found.',
 'current_16_state_log_files_unchanged':[pin(b['path']) for b in observation['files']],
 'carrier':pin(observation['carrier']['path']),
 'observation_scope':'02:02 London double CIM observation and GPU26 rows remain prior snapshot evidence, not future execution permission. Latest adoption checks only the 16 closed small files and carrier again.',
 'new_scientific_runs':0,'new_native_figures':0,'overleaf_updated':False,'submission_ready':False,
 'release_or_intent_or_COM_or_cleanup_executed':False,'prior_full_partner_zip_read_or_modified':False,
 'limits':['Official Full 10/11 tasks lower R@1/mAP; all11 transfer tasks lower mean R@1 retained.','Three-seed sample SD and single-seed sensitivity/corruption remain distinct; no pooling, new CI or significance.','Full cached-clean versus online-corrupt, query subset denominators, nonposterior margins, saved AURC and empty-bin nulls retained.','Upstream checkpoint SHA inheritance, historical missing chain edges and no new model/fullrank/AP/bootstrap-resampling validation remain.','Unchanged historical public-baseline results, old figure PDFs and literature are inherited; no fresh scientific or bibliographic validation is claimed.','T6/LOHO24fit192task/remaining Visio/features/baselines/efficiency/final Overleaf and submission work remain outstanding.'],
 'source':pin(Path(__file__)),
 'unique_bound_files':list(pins.values())}
dest=DEST/'ROOT_MANUSCRIPT_ADOPTION.json'
with dest.open('x',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'root':pin(dest),'unique_bound_files':len(result['unique_bound_files']),'archive':package['archive']},ensure_ascii=False))
