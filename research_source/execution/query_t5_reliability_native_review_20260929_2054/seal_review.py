"""Seal already executed figure checks and separately completed image inspection.

Only immutable byte binding, source-diff reproduction and documentation; never
reruns data/geometry/scientific suites. Visual judgments precede this script.
"""
from pathlib import Path
import datetime
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
WORK = HERE.parent.parent/'query_t5_reliability_native_figures_20260929_2054'
OUT = WORK/'output'
SEM = HERE.parent/'query_t5_reliability_semantics_review_20260929_2054'


def bind(path):
    data = Path(path).read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def equal(pin):
    current = bind(pin['path'])
    if current != pin:
        raise AssertionError('Changed after successful review: '+pin['path'])
    return current


def fixed(path, sha):
    result = bind(path)
    if result['sha256'] != sha:
        raise AssertionError('Fixed pin mismatch: '+str(path))
    return result


def write(name, payload):
    path = HERE/name
    with path.open('x',encoding='utf-8') as stream:
        json.dump(payload,stream,ensure_ascii=False,indent=2)
        stream.write('\n')
    return bind(path)


def snapshot(path):
    path = Path(path)
    data = path.read_bytes()
    dest = HERE/'raw_final'/path.name
    with dest.open('xb') as stream:
        stream.write(data)
    a,b = bind(path),bind(dest)
    if a['sha256'] != b['sha256'] or a['bytes'] != b['bytes']:
        raise AssertionError('Snapshot byte mismatch')
    return {'source':a,'snapshot':b}


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    contract_pin = fixed(HERE/'DATA_CONTRACT.json','33af44ed731e9a951d0514a11a4cf51c86f1694deadb20888cf5628ad61874c4')
    artifact_pin = fixed(HERE/'ARTIFACT_REVIEW.json','e77da40066132d34e4c2f8cf5c2c19aeb1bcda270533d5f0965a38be82cb3470')
    contract,actual = load(HERE/'DATA_CONTRACT.json'),load(HERE/'ARTIFACT_REVIEW.json')
    if contract['checks'] != 8793 or actual['checks'] != 82420:
        raise AssertionError('Executed scope changed')
    equal(contract['source']);equal(actual['source'])
    stable = [equal(p) for p in actual['bindings']]
    revision = load(WORK/'SOURCE_REVISION.json')
    for key in ('before','after','diff','executedSample'):
        equal(revision[key])
    before = Path(revision['before']['path']).read_text(encoding='utf-8')
    after = Path(revision['after']['path']).read_text(encoding='utf-8')
    reproduced = ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='build_reliability.mjs',tofile='build_reliability_v2.mjs'))
    if reproduced != Path(revision['diff']['path']).read_text(encoding='utf-8'):
        raise AssertionError('Complete producer source diff differs')
    build = load(WORK/'BUILD_REPORT.json')
    captions = (OUT/'CAPTIONS.md').read_text(encoding='utf-8-sig')
    for fig in build['figures']:
        heading = f"## Figure {fig['ordinal']}: {fig['title']}"
        if captions.count(heading) != 1 or captions.count(fig['caption']) != 1:
            raise AssertionError('Public caption differs from fixed read source/notes')
    semantic = [fixed(SEM/'REVIEW.json','89578f22d25b28934f11fcf9e80f2f02bfa1b452699a4fd94f18733cfe732c38'),
                fixed(SEM/'INTERPRETATION_ADDENDUM.json','07a988fb74ef55d56f3343b5784f8bbffa9e731b2da65452cd078f7c58f5a682')]
    semantic_files = [equal(load(SEM/'REVIEW.json')[k]) for k in ('review_markdown','sealing_source')]
    semantic_files += [equal(load(SEM/'INTERPRETATION_ADDENDUM.json')[k]) for k in ('markdown','sealing_source')]
    (HERE/'raw_final').mkdir(exist_ok=False)
    snapshots = [snapshot(p) for p in (WORK/'build/build_reliability.mjs',WORK/'build/build_reliability_v2.mjs',
                 WORK/'V1_SAMPLE_TO_FINAL_V2.patch',WORK/'SOURCE_REVISION.json',WORK/'INPUT_PROVENANCE.json',
                 OUT/'README.md',OUT/'CAPTIONS.md',OUT/'FIGURE_INDEX.csv')]
    source_review = write('SOURCE_REVIEW.json', {
        'schema':'independent-t5-reliability-native-static-source-review.v1','utc':stamp,
        'reviewer':'/root/sep29_eval_audit','accepted_with_stated_limits':True,
        'method':'Complete v1 builder and complete v1-to-v2 diff actually read; v2 differences byte-reproduced. Three original reliability/call functions read/extracted as text/AST only.',
        'sealing_source':bind(Path(__file__)),'producer_source_and_public_documents':snapshots,
        'original_source_fragments':contract['static_original_source_fragments'],
        'findings':[
            'The builder reads the exact adopted small T5 JSON and root/capture bindings, transcribes all990 saved bin rows to CSV and maps only140 occupied bins to scatter markers.',
            'Marker x is each stored within-bin mean fixed score, never the bin center. Marker y is stored empirical Top1 accuracy. Both remain fractions on0–1 axes; outlines preserve true coordinates without jitter or connecting series lines.',
            'All15 bin population rows per variant are carried and visibly displayed, including850 zeros. Empty mean/accuracy remain null; no artificial zero-accuracy markers or interpolation across missing bins.',
            '66 saved ECE fractions are only displayed to four decimals. No scientific score/bin membership/accuracy/gap/ECE or statistical uncertainty is recomputed.',
            'The original source defines clip(margin/2,0,1), min(int15score,14), upper-bin internal boundaries and final inclusion of1. Actual floating bin assignments are inherited, not reconstructed from printed edges.',
            'Full official query sets are shared, but each variant has its own score bins. Corresponding Visual/Full bin numbers do not establish common members.',
            'Gray y=x is numerical equality only; score is not a calibrated posterior or fitted probability. Lower fixed-score ECE does not establish higher retrieval accuracy or better probability calibration.',
            'V1 ran only two successful samples. Before any full final execution, v2 added a sixth visible interpretive footer and matching caption limitation, increased height585→604pt, and prohibited sample overwrite. Data,140 point mappings,990 count values and66 ECE source mappings are unchanged in the complete diff.',
            'Final public README was read completely. All eleven external captions are byte-equal strings to the fixed builder/notes captions; the common complete caption and all caption-relevant source changes were read.',
            'Separate static semantic reviewer reports are bound below; they do not execute this reviewer’s data/artifact checks or claim rendered-figure approval.'
        ],'separate_static_semantic_reports':semantic,'separate_static_semantic_support':semantic_files,
        'remaining_blockers':[],
        'limits':[
            'No producer checker imported or executed. Its assertion count is not independent evidence.',
            'No old NPZ/weights/cache/image/scientific-suite repetition. Prior typed-scalar reliability/ECE acceptance and all historical authority/model/ranking/AP limits remain inherited.',
            'No pooling/SD/CI/bootstrap/p-value/inferential claim. Some bins have very small populations; absence of uncertainty bars is not a precision guarantee.',
            'No assertion of zero clipping, ideal calibration or class-posterior meaning is justified by these figures.']})
    images = []
    for fig in actual['figures']:
        png = equal(fig['png'])
        observations = [
            'Complete final PPTX roundtrip PNG actually viewed with view_image(detail=original),1375×1611 pixels.',
            'Task/direction/height, seed1/2/3 columns, fraction units and outline-marker legend are clear; no title/axis/table/footer clipping or unwanted text overlap at this scale.',
            'All15 population rows remain visible, with gray0 counts separated from reliability observations. ECE fractions are visibly separate from the axes and remain four-decimal saved values.',
            'The sixth footer is readable and states that lower fixed-score ECE does not imply higher retrieval accuracy or better calibration.',
            'True small-score positions, boundary accuracy0/1 and overlapping observations are not displaced. The single gray diagonal is an equality reference, with no lines joining occupied bins.'
        ]
        if fig['ordinal'] == 3:
            observations.append('Street occupied observations near zero accuracy remain visible; they are distinct in meaning from the empty count0 rows. The very small saved ECE does not become a high-accuracy claim.')
        if fig['ordinal'] in (2,5,7,9,11):
            observations.append('Sparse one-occupied-bin series remain single markers, with all remaining empty rows retained; no fabricated full reliability curve is drawn.')
        if fig['ordinal'] in (4,6,8,10):
            observations.append('Small occupied counts down to1 and their real zero/one accuracies remain visible in the count table and scatter; no uncertainty or minimum-size guarantee is inferred.')
        images.append({'ordinal':fig['ordinal'],'task':fig['task'],'preview':png,'dimensions_px':fig['png_dimensions'],
                       'tool':'view_image','detail':'original','actual_visual_inspection':True,'result':'pass_at_stated_scale','observations':observations})
    visual_review = write('VISUAL_REVIEW.json', {
        'schema':'independent-t5-reliability-native-actual-visual-review.v1','utc_recorded':stamp,
        'reviewer':'/root/sep29_eval_audit','accepted_with_stated_limits':True,
        'sealing_source':bind(Path(__file__)),'artifact_review':artifact_pin,
        'method':'All eleven final PNGs actually viewed using view_image(original), in batches1–3,4–6,7–9,10–11. This sealer records prior judgments; it does not inspect pixels.',
        'images':images,'all_eleven_viewed':True,
        'preview_authority':'Fixed producer BUILD_REPORT and builder export/reimport the final PPTX and render each page on CPU; this reviewer neither rerendered nor opened Microsoft PowerPoint.',
        'finding':'No remaining visible layout blocker at original1375×1611 resolution. Honest overlaps/small-coordinate observations retained without jitter.',
        'limits':['Not a print-quality, accessibility or cross-version PowerPoint rendering guarantee.',
                  'Physical8pt claims come from SVG scale and actual PPT XML, not preview appearance. Shrinking the figure reduces effective font size.',
                  'Preview approval establishes no scientific correctness, calibration, significance or causal comparison.']})
    readme = HERE/'README.md'
    with readme.open('x',encoding='utf-8') as stream:
        stream.write('''# Independent T5 fixed margin-score reliability figure review

The eleven final native figures are accepted with explicit limits; root adoption is separate. New small-source contract checks passed first execution with8,793 assertions. Actual new CSV/SVG/PPT checks passed first execution with82,420 assertions. Neither suite was repeated. The figure producer’s own export checker was not executed by this reviewer and its count is not independent evidence.

Scope is66 task/seed/variant records ×15 saved bins =990 records, comprising140 occupied markers and850 empty bins without markers; all990 count values and66 saved ECE labels are shown. Eleven tasks have33 separate seed panels and33 numerical y=x references. The actual PPTX has2,824 individual native objects, including2,189 editable texts, with no raster/SVG/workbook/chart substitutes or groups. SVG/PPT physical size is181.9×213.077778mm and Arial minimum8pt. No PowerPoint application was opened.

The fixed score is clip((cosine Top1−Top2 margin)/2,0,1). It is not a posterior or fitted probability. Original bin assignment uses min(int(15score),14), with internal boundaries entering the upper bin and1 included in the last. The existing floating-point bins are carried, not reconstructed from display bounds. Occupied markers use stored within-bin mean score and empirical R@1, not bin centers; both axes remain0–1 fractions. Empty mean/accuracy stay null, never substituted with observed zero accuracy. All populations, including zeros and very small occupied counts, are visibly retained. Actual zero-accuracy occupied bins are real observations and are plotted.

ECE is copied from the saved JSON, rounded only for four-decimal labels. Neither ECE nor its weighted contributions are recomputed. Lower fixed-score ECE does not ensure higher retrieval accuracy or better probability calibration because accuracy and score both vary. The diagonal is numerical equality only. Visual/Full use the same whole query population but their score-bin members may differ. No seed/task/height/direction pooling, SD, CI, bootstrap, p-value or significance claim is added. Selective-risk/AURC/paired records remain in the exact source JSON but are outside this figure’s displayed scope.

The complete v1 builder and full v1-to-v2 diff were read. V1 produced two successful samples. Before the first full build, v2 added the visible lower-ECE caution/caption,19pt page height and a sample-overwrite refusal; original samples/source remain. No data/point mapping changed in the diff. V2 first full build and the independent two new suites passed. There was no independent execution failure or rejected final scientific value.

`VISUAL_REVIEW.json` records actual view_image(original) review of all11 final PPT-roundtrip PNGs at1375×1611. All headers, fractions, ECE labels, count rows and six footer lines were readable, with no visible clipping or unwanted text/data overlap. Small-x, accuracy0/1 and overlapping points were preserved without jitter. Preview review is distinct from programmed geometry checks and from separate producer/root inspections.

`SOURCE_REVIEW.json` also references the separate reviewer’s static semantics reports and addendum, not a second numeric execution. Upstream typed-scalar query/bin/ECE agreement is inherited, not rerun. No old66NPZ, weights, cache/image bytes, models, full rankings, all-positive-rank AP, bin assignments/means/gaps/ECE or bootstrap statistics were recomputed. All inherited SHA authority and historical metadata-chain gaps remain. This work neither resolves T6 nor changes live state, release, queue, source, locks, HANDOFF or automation.
''')
    sources = [bind(HERE/name) for name in ('derive_contract.py','review_artifacts.py','seal_review.py')]
    execution = {name:{'first_execution_exit_code':0,'checks':count,'stdout':bind(HERE/(name+'.stdout.log')),
                      'stderr':bind(HERE/(name+'.stderr.log')),'authority':'Observed real tool execution and immutable report; suite not repeated.'}
                 for name,count in (('contract',8793),('artifact',82420))}
    metadata = write('METADATA.json', {
        'schema':'independent-t5-reliability-native-review-metadata.v1','utc':stamp,'accepted_with_stated_limits':True,
        'scope':actual['totals'],'reports':[contract_pin,artifact_pin,source_review,visual_review],
        'readme':bind(readme),'sources':sources,'execution':execution,
        'new_artifact_bindings':stable,'final_small_snapshots':snapshots,'original_small_snapshots':contract['inputs'],
        'separate_static_semantics':semantic,'separate_static_semantic_support':semantic_files,
        'sealer_scope':'Only source/report/new-artifact byte stability, exact full source diff and public caption correspondence; no new scientific or repeated data/geometry suite.',
        'failures':'No independent contract/artifact failure. Producer v1 successful sample→v2 clarified caption/layout before first full build; no scientific failure.',
        'scientific_execution':False,'PowerPoint_opened':False})
    delivery = write('DELIVERY.json', {
        'schema':'independent-t5-reliability-native-review-delivery.v1','utc':stamp,'accepted_with_stated_limits':True,
        'scope':'11 final task figures,33 seed panels,990 saved bins:140 occupied markers and850 empty;66 saved ECE fractions; all11 PNGs actually viewed.',
        'data_contract':contract_pin,'artifact_review':artifact_pin,'source_review':source_review,'visual_review':visual_review,
        'metadata':metadata,'readme':bind(readme),'sources':sources,'figures_pptx':bind(OUT/'t5_reliability_native_editable_11figures.pptx'),
        'independent_execution_checks':{'small_source_contract':8793,'actual_new_artifacts':82420},
        'separate_static_semantics':semantic,'upstream_root':contract['root_adoption'],
        'interpretation_limits':['Fixed clipped margin score is not fitted calibration/posterior; no proof that actual clipping never occurred.',
            'Lower ECE does not imply better accuracy or probability calibration; y=x is numerical reference, not a quality endorsement.',
            'No empty-bin imputation, bin-center coordinate substitution, inter-bin line, pooling, SD/CI/p-value or significance claim.',
            'Variant-specific bins can contain different members; sparse counts imply no uncertainty guarantee.',
            'Stored adopted values only; no oldNPZ/model/ranking/AP/ECE/query suite repeated; all upstream SHA/chain limitations retained.',
            'Native flat objects and actual original-resolution previews; no Microsoft PowerPoint/print guarantee.'],
        'root_adoption':'Pending separate parent review/binding; no parent adoption claimed here.'})
    print(json.dumps({'delivery':delivery,'metadata':metadata,'source_review':source_review,'visual_review':visual_review,'sources':sources},ensure_ascii=False))


if __name__ == '__main__':
    main()
