"""Seal previously executed new-figure checks and actual model visual inspection.

This sealer records visual judgments made with view_image(original), not an
automated image-quality test. It only binds stable small/new artifact bytes.
"""
from pathlib import Path
import datetime
import hashlib
import json

HERE=Path(__file__).resolve().parent
WORK=HERE.parent.parent/'query_t5_native_figures_20260929_1856'
OUT=WORK/'output_v2'

def bind(path):
    path=Path(path);data=path.read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(name,payload):
    path=HERE/name
    with path.open('x',encoding='utf-8') as stream:
        json.dump(payload,stream,ensure_ascii=False,indent=2);stream.write('\n')
    return bind(path)

def equal(pin):
    current=bind(pin['path'])
    if current!=pin:
        raise AssertionError('Changed since review: '+pin['path'])
    return current

def snapshot(path):
    path=Path(path)
    dest=HERE/'raw_final'/path.name
    data=path.read_bytes()
    with dest.open('xb') as stream:
        stream.write(data)
    if bind(path)['sha256']!=bind(dest)['sha256']:
        raise AssertionError('Snapshot not byte-exact')
    return {'source':bind(path),'snapshot':bind(dest)}

def main():
    stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (HERE/'raw_final').mkdir(exist_ok=False)
    data_contract=bind(HERE/'DATA_CONTRACT.json')
    artifact_review=bind(HERE/'ARTIFACT_REVIEW.json')
    if data_contract['sha256']!='f206b96dd669daf93cc849b91e29e78c036ca351ecbd539d43c06490d5ac2af2':
        raise AssertionError('Contract changed')
    if artifact_review['sha256']!='e4c9881e3abf65a6bad1160d8f43e545018ddfeaf8dbe57bbbfb986602085cdd':
        raise AssertionError('Artifact review changed')
    contract=load(HERE/'DATA_CONTRACT.json')
    actual=load(HERE/'ARTIFACT_REVIEW.json')
    if contract['checks']!=6422 or actual['checks']!=57983:
        raise AssertionError('Wrong scope')
    equal(contract['source']);equal(actual['source'])
    stable_bindings=[equal(x) for x in actual['bindings']]
    producer_files=[WORK/'build/build_t5.mjs',WORK/'build/build_t5_v2.mjs',
                    WORK/'V1_TO_V2.patch',WORK/'SOURCE_REVISION.json',
                    WORK/'INPUT_PROVENANCE_V2.json',OUT/'README.md',OUT/'CAPTIONS.md']
    final_small_snapshots=[snapshot(p) for p in producer_files]
    revision=load(WORK/'SOURCE_REVISION.json')
    for field in ('before','after','diff','v1Build','v2Build'):
        equal(revision[field])
    source_review=write('SOURCE_REVIEW.json',{
        'schema':'independent-t5-native-static-source-review.v1','utc':stamp,
        'accepted_with_stated_limits':True,'reviewer':'/root/sep29_eval_audit',
        'method':'Actual complete source and complete derivation diff read; no producer code/checker imported or executed.',
        'sealing_source':bind(Path(__file__)),
        'source_and_document_snapshots':final_small_snapshots,
        'findings':[
            'The final v2 builder derives only eleven pages from the exact adopted small T5 JSON/CSV and root/capture metadata.',
            'All 66 native task/seed/variant rows feed 660 markers at realized coverage times100 and selective risk times100. Nominal requests only define source counts; they are not substituted for actual horizontal coordinates.',
            'Saved discrete all-prefix AURC fractions are displayed separately with four decimals, without reconstructing query ordering or integrating the ten plotted points.',
            'Native132 paired comparisons including75% coverage are carried byte-exact and not plotted. No bootstrap CI/inference, fitted calibration, pooling or scientific rerun occurs in the builder.',
            'The complete v1-to-v2 diff changes panel x spacing155 to158pt and width140 to126pt plus independent v2 output/receipt names. Data-mapping expressions and captions are unchanged in that diff.',
            'The original v1 source/output remain available. Root/producer reported the v1 street-endpoint/inter-panel100label overlap; this reviewer independently inspected all v2 images but did not visually inspect v1.',
            'Full README and all eleven external captions clarify clean official-query scope, variant-specific selected subsets, conditional selected-query risk, and separation from paired coverage-constrained success.',
            'SVG and PPT consist of native flat text and geometric objects. Actual bytes/geometry/units were independently checked in ARTIFACT_REVIEW; source reading is not a substitute for that execution.'
        ],
        'remaining_blockers':[],
        'limits':[
            'This source review does not execute the producer export checker or rely on its assertion count as independent evidence.',
            'Upstream query recomputation and all inherited source/SHA limitations are taken from the pinned adopted review; no old NPZ/model/cache/image/checkpoint or scientific tests were repeated.',
            'Separate selected subsets mean two curves at equal coverage are descriptive conditional accuracies, not a common-subset paired test.',
            'Margin is not a posterior or calibrated probability; guide segments do not add observations.']})
    perpage=[]
    for figure in actual['figures']:
        pin=equal(figure['png'])
        observations=[
            'Full page actually viewed with view_image detail=original at1375×1021 pixels.',
            'Dataset/task/height/direction and N title readable; separate seed1/2/3 panels and both variant encodings visible.',
            'No visible title/axis/legend/AURC/footer clipping or unwanted text-to-data overlap at this viewing scale.',
            'All-prefix AURC fraction labels visibly separated from percentage axes; bottom interpretation lines readable.',
            'Nonmonotonic/crossing/coincident source marks remain unchanged; visual closeness of true data is not treated as a source error.'
        ]
        if figure['ordinal']==3:
            observations.append('Near100% street risks are retained. Panel-end points no longer intrude into the next seed panel100axis label; no claim of nearzero risk is implied.')
        if figure['ordinal']==9:
            observations.append('Seed1 Visual first point at zero risk is visibly retained at the axis; no invented zero-coverage point is added.')
        perpage.append({'ordinal':figure['ordinal'],'task':figure['task'],'preview':pin,
                        'dimensions_px':figure['png_dimensions'],'tool':'view_image','detail':'original',
                        'actual_visual_inspection':True,'result':'pass_at_stated_scale','observations':observations})
    visual_review=write('VISUAL_REVIEW.json',{
        'schema':'independent-t5-native-actual-visual-review.v1','utc_recorded':stamp,
        'accepted_with_stated_limits':True,'reviewer':'/root/sep29_eval_audit',
        'sealing_source':bind(Path(__file__)),'artifact_review':artifact_review,
        'method':'Actual view_image(original) calls viewed all eleven final v2 PPTX roundtrip PNGs, in batches pages1–3,4–7,8–11. The sealer does not perform visual inspection.',
        'images':perpage,'all_eleven_viewed':True,
        'preview_generation_authority':'Pinned producer BUILD_REPORT_V2 and fully read builder export the finalized PPTX, re-import it, and render every page on CPU. Reviewer did not rerender or open Microsoft PowerPoint.',
        'findings':'No remaining visible layout blocker at original1375×1021 previews. Final v2 objects/values are independently bound in ARTIFACT_REVIEW.',
        'limits':[
            'This is image inspection at the recorded original pixel resolution, not a physical-print, accessibility or cross-version Microsoft PowerPoint rendering guarantee.',
            'Physical font sizes are independently verified from SVG scale and PPT XML, not inferred from preview readability. Shrinking figures will reduce effective type size.',
            'No visual claim establishes scientific model/ranking/AP correctness or uncertainty; inherited evidence limits remain.']})
    readme=HERE/'README.md'
    readme.write_text('''# Independent T5 native figure review — final v2

The new v2 eleven-page figure set is accepted with the explicit limits below. This directory is an independent review; later root adoption is separate.

`DATA_CONTRACT.json` records the first successful 6,422-check small-source/display-contract execution. `ARTIFACT_REVIEW.json` records the first successful 57,983-check actual v2 CSV/SVG/PPT execution. Neither suite was repeated. The original 66 query NPZs, old query-statistic suite, science/model/GPU, weights, caches and images were not read or run.

The independently checked display scope is 11 task pages, 33 separate seed panels, 66 native variant series, 660 source-mapped markers, 594 adjacent guide segments, 66 saved all-prefix AURC labels, 2,244 native PPT objects including 572 editable texts. SVG physical size is 181.9 ×135.113889mm and actual PPT/SVG font size is at least8pt. The deck uses flat geometric/text objects, not an Excel chart workbook or embedded raster.

Actual coordinates use saved realized coverage and saved selective risk, each times100. Requested coverage is not substituted for ceil-selected count/N. AURC uses the saved upstream all-prefix fraction; this review maps and rounds that value but does not recompute it or integrate the ten points. The132 paired comparison records, including75% requests, are carried unchanged and are not plotted. No pooling, SD/CI, bootstrap, p-values or significance are added. Margin is a ranking score, not a calibrated posterior.

`SOURCE_REVIEW.json` binds the full read builder and v1-to-v2 diff. The first v1 layout is retained by the producer and is not the deliverable; it was rejected by root/producer for a street-endpoint/inter-panel label overlap. Independent review here directly inspects v2, without claiming a v1 visual inspection. `VISUAL_REVIEW.json` records actual original-resolution inspection of all11 final PPT-roundtrip PNGs at1375×1021. Street near100% risk and the SUES250m reverse zero-risk point are retained; no remaining visible clipping or unwanted label/data overlap was seen.

The figures are clean official-query selective-risk results, not corruption robustness curves. Visual and Full rank/select their own subsets; equal realized coverage need not select the same queries. The plots describe conditional selected-query risk, not a common-membership paired comparison or the separate coverage-constrained success statistic. This is explicitly documented in the full external captions/README. All inherited checkpoint/cache/image SHA, historical chain, saved-value/model/full-ranking/AP and unresampled-bootstrap limits remain unchanged.

The figure producer's own checker is not an independent execution. Microsoft PowerPoint was not opened. Preview inspection is not a guarantee of physical-print appearance or all PowerPoint versions. No scientific file, process, recovery release, live state, HANDOFF or automation was changed.
''',encoding='utf-8')
    source_descriptors=[bind(HERE/name) for name in ('derive_contract.py','review_artifacts.py','seal_review.py')]
    metadata=write('METADATA.json',{
        'schema':'independent-t5-native-review-metadata.v1','utc':stamp,
        'accepted_with_stated_limits':True,
        'scope':actual['totals'],
        'reports':[data_contract,artifact_review,source_review,visual_review],
        'review_readme':bind(readme),'sources':source_descriptors,
        'execution':{
            'data_contract':{'first_execution_exit_code':0,'checks':6422,'authority':'Observed tool execution and immutable DATA_CONTRACT; no repeated suite.'},
            'artifact_review':{'first_execution_exit_code':0,'checks':57983,
                               'stdout':bind(HERE/'artifact_review.stdout.log'),
                               'stderr':bind(HERE/'artifact_review.stderr.log')},
            'sealer':'Only final byte-stability and provenance binding; no second data/geometry/scientific suite.'},
        'final_actual_artifact_bindings':stable_bindings,
        'final_small_snapshots':final_small_snapshots,
        'original_small_snapshots':contract['inputs'],
        'failures':'No independent contract/artifact execution failure. Producer v1 layout correction is preserved separately and is not a scientific failure.',
        'scientific_execution':False,'PowerPoint_opened':False})
    delivery=write('DELIVERY.json',{
        'schema':'independent-t5-native-review-delivery.v1','utc':stamp,
        'accepted_with_stated_limits':True,
        'scope':'Final v2 eleven T5 task figures,33seed panels,66native rows/660points; all eleven actually viewed.',
        'data_contract':data_contract,'artifact_review':artifact_review,
        'source_review':source_review,'visual_review':visual_review,'metadata':metadata,
        'readme':bind(readme),'sources':source_descriptors,
        'figures_pptx':bind(OUT/'t5_selective_native_editable_11figures_v2.pptx'),
        'independent_execution_checks':{'small_source_contract':6422,'actual_new_artifacts':57983},
        'upstream_root':contract['root_adoption'],
        'interpretation_limits':[
            'No scientific or prior66NPZ/query/AURC/bootstrap suite repeated; stored adopted small values only.',
            'Native ten observations/guide segments and separate saved all-prefix AURC; paired132/75% not plotted.',
            'No pooling/SD/CI/inferential claim. Margin is not calibrated probability. Variant-selected query memberships may differ.',
            'Clean official-query selective-risk scope, separate from corruption robustness.',
            'Native flat objects; no PowerPoint runtime or physical-print guarantee. All upstream source/SHA/ranking/AP limitations retained.'],
        'root_adoption':'Pending parent independent binding/review; this report does not assert parent adoption.'})
    print(json.dumps({'delivery':delivery,'metadata':metadata,'source_review':source_review,
                      'visual_review':visual_review,'sources':source_descriptors},ensure_ascii=False))

if __name__=='__main__':
    main()
