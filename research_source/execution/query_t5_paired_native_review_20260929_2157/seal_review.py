"""Seal completed independent paired-figure checks and actual image inspection.

Only new report/source/artifact byte stability and full source-diff/document
correspondence. No old data/science or repeated display/geometry suite.
"""
from pathlib import Path
import datetime
import difflib
import hashlib
import json

HERE=Path(__file__).resolve().parent
WORK=HERE.parent.parent/'query_t5_paired_native_figures_20260929_2157'
OUT=WORK/'output'
SEM=HERE.parent/'query_t5_paired_semantics_review_20260929_2157'


def bind(p):
    b=Path(p).read_bytes()
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}


def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def unchanged(pin):
    b=bind(pin['path'])
    if b!=pin:raise AssertionError('Changed binding: '+pin['path'])
    return b


def fixed(p,sha):
    b=bind(p)
    if b['sha256']!=sha:raise AssertionError('Fixed pin mismatch '+str(p))
    return b


def write(name,obj):
    p=HERE/name
    with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
    return bind(p)


def snapshot(p):
    p=Path(p);b=p.read_bytes();dest=HERE/'raw_final'/p.name
    with dest.open('xb') as f:f.write(b)
    return {'source':bind(p),'snapshot':bind(dest)}


def main():
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    contract_pin=fixed(HERE/'DATA_CONTRACT.json','43c3ce79fe7eea96cb1644c7db77f7c95abe89dfa6b9fc232968c713321f9451')
    actual_pin=fixed(HERE/'ARTIFACT_REVIEW.json','dd3524bb542b9d0dbd6cd8326e795cc3da9d2cd8bb2d98ab8b9c27e21e0d829a')
    contract,actual=load(contract_pin['path']),load(actual_pin['path'])
    if contract['checks']!=1681 or actual['checks']!=46122:raise AssertionError('Executed scope changed')
    unchanged(contract['source']);unchanged(actual['source'])
    stable=[unchanged(x) for x in actual['bindings']]
    revision=load(WORK/'SOURCE_REVISION.json')
    for key in ('before','after','diff','executedSample'):unchanged(revision[key])
    before=Path(revision['before']['path']).read_text(encoding='utf-8')
    after=Path(revision['after']['path']).read_text(encoding='utf-8')
    diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='build_paired.mjs',tofile='build_paired_v2.mjs'))
    if diff!=Path(revision['diff']['path']).read_text(encoding='utf-8'):raise AssertionError('Complete source diff differs')
    build=load(WORK/'BUILD_REPORT.json');caps=(OUT/'CAPTIONS.md').read_text(encoding='utf-8-sig')
    for fig in build['figures']:
        if caps.count(f"## Figure {fig['ordinal']}: {fig['title']}")!=1 or caps.count(fig['caption'])!=1:
            raise AssertionError('Public caption differs from complete read builder/notes')
    sem=fixed(SEM/'REVIEW.json','8e6107b6e80673c49f27b59fb6dce8ea1d7374a3dc23c3a4ddadb5cb7b1bd92b')
    semantic_support=[unchanged(load(sem['path'])[k]) for k in ('review_markdown','sealing_source')]
    prior=HERE.parent/'query_t5_reliability_native_review_20260929_2054/review_artifacts.py'
    prior_pin=fixed(prior,'98bf97497b6317b8500ca518ab3d5e40490a3f37e930133f407d00351e7d60f4')
    oldtext=prior.read_text(encoding='utf-8');newtext=(HERE/'review_artifacts.py').read_text(encoding='utf-8')
    def helper(t):return t[t.index('def native_xml('):t.index('def main():')].strip()
    if helper(oldtext)!=helper(newtext):raise AssertionError('Declared reused native helper not identical')
    (HERE/'raw_final').mkdir(exist_ok=False)
    snapshots=[snapshot(p) for p in (WORK/'build/build_paired.mjs',WORK/'build/build_paired_v2.mjs',WORK/'V1_SAMPLE_TO_FINAL_V2.patch',WORK/'SOURCE_REVISION.json',WORK/'INPUT_PROVENANCE.json',OUT/'README.md',OUT/'CAPTIONS.md',OUT/'FIGURE_INDEX.csv')]
    source_review=write('SOURCE_REVIEW.json',{
        'schema':'independent-t5-paired-native-static-source-review.v1','utc':utc,'reviewer':'/root/sep29_eval_audit','accepted_with_stated_limits':True,
        'method':'Complete v1 builder and complete v1-to-v2 diff actually read. Full diff byte-reproduced; original alignment/count/paired function fragments and caller/coverage constant read statically, not imported.',
        'sealing_source':bind(Path(__file__)),'producer_sources_and_public_documents':snapshots,
        'original_static_fragments':contract['static_original_source_fragments'],'separate_static_semantics':sem,'separate_static_support':semantic_support,
        'native_xml_helper_derivation':{'source':prior_pin,'exact_function_text_equal':True,'old_task_or_suite_executed':False},
        'findings':[
            'The builder transcribes exactly132 paired source rows and matching native full-query N/digest. Two full-N utility rates and realized coverage are direct source values scaled only for percentage display.',
            'Paired original coverage50/75/90/100 is distinct from native ten-point risk coverage. Plot x is stored realized coverage; requested labels and saved k/N table are explicitly separate.',
            'Each variant independently selects top k raw-margin queries with stable aligned query-order ties. Saved overlap is selected-set intersection, not shared success. Same k does not imply same selected members.',
            'Y is selected AND correct over common full N, never selective accuracy over k. Unselected utilities are false without declaring their underlying predictions wrong. More full-N success at higher coverage can follow mechanically from more selected queries.',
            'Only264 registered markers and198 adjacent guide segments are allowed. No artificial origin, extrapolation, fitted curve, area metric, CI, SD, p/Holm annotation or pooling.',
            'Complete v1 sample source/output is retained. Before the first final build, v2 added264 visible three-decimal success percentages for low-value readability, nominal headings/V/F labels, raised467→534pt, moved footers384→448pt, extended caption and refused sample overwrite. Existing data and marker/guide coordinates did not change in the full diff.',
            'V2 source contains only small saved k/ceil and coverage k/N consistency assertions beyond transcription; this is not a fresh original-query scientific reconstruction. This independent display review itself does not compute saved k/N, selection, utility rates, overlap, p-values or uncertainty.',
            'Public README read completely; all11 public captions equal exact already-read builder/notes strings. Separate semantic review is static only, not another numeric/geometry or visual execution.'
        ],'remaining_blockers':[],
        'limits':contract['limits']+['No producer checker called or imported. Its counts are not this independent reviewer’s evidence.']})
    images=[]
    for fig in actual['figures']:
        p=unchanged(fig['png'])
        obs=['Final PPTX roundtrip PNG actually viewed with view_image(detail=original) at1375×1424 pixels.',
             'Task/direction/height and all three separate seeds are clear. The 0–100 axes, full-N denominator label, variant outlines and six explanatory footer lines are readable without visible clipping or unwanted text overlap.',
             'Requested labels, actual k/N and selected-set overlap table are visibly separate from success-rate values. The264 saved percentages have explicit V/F rows and three decimal places.',
             'Exactly four existing observations start near50 percent, with no drawn zero-origin segment. True overlaps/crossings and unfavorable Full values are retained without jitter.']
        if fig['ordinal']==3:obs.append('Street points honestly remain near the axis bottom; all low saved percentages are readable in the new V/F numeric block, rather than hidden by changing the axes.')
        if fig['ordinal'] in (5,7,9,11):obs.append('Reverse SUES task N=80 and its exact40/60/72/80 selections are readable; coincident or crossing saved variant points remain unshifted, and no inferential precision is asserted.')
        images.append({'ordinal':fig['ordinal'],'task':fig['task'],'preview':p,'dimensions_px':fig['png_dimensions'],'actual_visual_inspection':True,'tool':'view_image','detail':'original','result':'pass_at_stated_scale','observations':obs})
    visual_review=write('VISUAL_REVIEW.json',{
        'schema':'independent-t5-paired-native-actual-visual-review.v1','utc_recorded':utc,'reviewer':'/root/sep29_eval_audit','accepted_with_stated_limits':True,
        'sealing_source':bind(Path(__file__)),'artifact_review':actual_pin,
        'method':'All11 final PNGs actually viewed at original resolution in batches1–3,4–6,7–9,10–11. This sealer records prior image judgments; it does not inspect pixels.',
        'images':images,'all_eleven_viewed':True,
        'preview_authority':'Producer fixed builder/receipt exported final PPTX then imported/rendered every slide on CPU. This independent reviewer did not rerender or open Microsoft PowerPoint.',
        'limits':['Not a print or cross-version PowerPoint rendering guarantee. Physical8pt evidence comes from SVG scaling and actual OOXML.',
                  'True data overlap is deliberately retained. Preview approval adds no scientific, causal, significance, uncertainty or calibration evidence.']})
    readme=HERE/'README.md'
    with readme.open('x',encoding='utf-8') as f:f.write('''# Independent T5 paired coverage-constrained-success native figure audit

The eleven final native figures are accepted with stated limits; parent root adoption remains separate. The new saved-small-source display contract passed first execution with1,681 checks. The actual new CSV/SVG/PPT/notes check passed first execution with46,122 checks. Neither suite was repeated and no producer checker was called. All11 final PNGs were actually viewed at original1375×1424 pixels, separately from programmed checks and producer/root inspection.

Scope:132 saved paired rows,11 tasks,33 seed panels,264 true markers,198 adjacent guide segments,132 requested/count/overlap table rows and264 visible three-decimal success percentages. The actual deck has2,431 flat native objects including1,518 editable texts; no images, embedded SVG, workbooks, chart objects or groups substitute for data. Physical size181.9×188.383333mm; Arial minimum8pt in both physical SVG scaling and actual native OOXML. Shrinking output reduces effective font size.

X copies saved realized coverage×100. Requested50/75/90/100 labels and actual saved k/N are separate. The75% point is an existing paired observation, not native70/80 interpolation. Y copies coverage_constrained_success.visual_rate/full_rate×100: selected AND Top-1-correct queries divided by the shared full query count N. It is not selective accuracy over selected k. Both variants independently choose their own top k raw-margin queries with stable aligned query-order ties, so same k does not imply same members. Overlap counts jointly selected queries, not common correctness. Unselected utilities are false without asserting wrong underlying predictions. At100%, the source definition reduces to full-task R@1.

Only four existing markers are drawn per variant, with connecting segments explicitly visual guides. No artificial origin, extrapolation, intermediate-data claim or area statistic is created. Higher coverage includes more queries, so more full-N success does not itself establish improved ranking. All seeds, tasks, directions and heights remain distinct; unfavorable Full values and true crossings/overlaps remain. No CI, SD, bootstrap, p/Holm, significance, causal or posterior-confidence claim is displayed. The original McNemar compares full-N utility variables; it is not a direct test of selective accuracies on different selected subsets. Original inferential fields are merely retained in the exact complete source JSON.

The full v1 builder and full v1→v2 diff were read. V1 produced two successful samples; source and outputs remain. Before the first full final build, v2 added visible success-value rows for low street values, adjusted page height/footer and extended the caption while leaving source values/marker/guide coordinates unchanged. It refuses to overwrite old samples. There was no failed independent contract/artifact execution or rejected scientific value in this figure audit. SOURCE_REVIEW also binds the distinct third-party static semantics report, which did not run numeric or figure checks.

Saved raw fraction values match the adopted JSON/CSV exactly using Decimal. Scaled percent columns allow only1e−12 absolute serialization difference; SVG geometry1e−8pt and PPT2EMU tolerances are presentation/export limits. Original query selection, k/N, utility rates, overlaps, p-values, means, bootstrap or other scientific statistics were not recomputed. No old66NPZ, checkpoint/cache/image bytes, models, full rankings or all-positive AP were accessed. All historical source-chain/SHA inheritance and upstream typed-scalar limits remain. No live state, owner, GPU/native process, locks, recovery, release, HANDOFF or automation was touched.

Actual original-scale visual inspection found no remaining clipping or unwanted text overlap. The street values remain near zero on common0–100 axes and are readable in explicit numeric rows. SUES reverse N=80 counts and true coincident/crossing points remain. Visual review is neither a print guarantee nor scientific validation. Parent adoption is a later, independent action.
''')
    sources=[bind(HERE/n) for n in ('derive_contract.py','review_artifacts.py','seal_review.py')]
    execution={name:{'first_execution_exit_code':0,'checks':cnt,'stdout':bind(HERE/(name+'.stdout.log')),'stderr':bind(HERE/(name+'.stderr.log')),'evidence':'Actual tool exit0 and immutable successful report; not rerun.'} for name,cnt in (('contract',1681),('artifact',46122))}
    metadata=write('METADATA.json',{
        'schema':'independent-t5-paired-native-review-metadata.v1','utc':utc,'accepted_with_stated_limits':True,'scope':actual['totals'],
        'reports':[contract_pin,actual_pin,source_review,visual_review],'readme':bind(readme),'sources':sources,'execution':execution,
        'new_artifact_bindings':stable,'final_small_snapshots':snapshots,'original_small_snapshots':contract['inputs'],
        'separate_static_semantics':sem,'separate_static_support':semantic_support,
        'sealer_scope':'Only byte stability of already-reviewed new files, complete source diff and public captions; no new scientific or repeated data/geometry checks.',
        'failure_history':'No independent contract/artifact failure; successful v1 sample retained before pre-final v2 readability revision.',
        'scientific_execution':False,'PowerPoint_opened':False})
    delivery=write('DELIVERY.json',{
        'schema':'independent-t5-paired-native-review-delivery.v1','utc':utc,'accepted_with_stated_limits':True,
        'scope':'11 final task pages,33 separate seed panels,132 paired rows,264 markers and visible success values,198 guide segments; all11 PNGs actually viewed.',
        'data_contract':contract_pin,'artifact_review':actual_pin,'source_review':source_review,'visual_review':visual_review,'metadata':metadata,'readme':bind(readme),'sources':sources,
        'figures_pptx':bind(OUT/'t5_paired_native_editable_11figures.pptx'),'independent_execution_checks':{'small_source_contract':1681,'actual_new_artifacts':46122},
        'separate_static_semantics':sem,'upstream_root':contract['root_adoption'],
        'interpretation_limits':contract['limits']+['Y uses shared full N, not selective k; variant-specific selected members differ and overlap counts selection only.',
            'Actual coverage coordinates and four original observations only; no origin, interpolated science, area metric, uncertainty or inference.',
            'All direct saved values; no old science/query/ratio/rate/p/CI/model/ranking/AP/weights/cache/image recomputation. Physical/preview checks are not Microsoft PowerPoint or print guarantees.'],
        'root_adoption':'Pending independent parent review; no root adoption claimed by this deliverable.'})
    print(json.dumps({'delivery':delivery,'metadata':metadata,'source_review':source_review,'visual_review':visual_review,'sources':sources},ensure_ascii=False))


if __name__=='__main__':main()
