"""Seal executed T4 display checks and separately performed actual image review.

Only byte binding and documentation happen here. This script neither performs
visual inspection nor reruns the data/geometry checks or any scientific suite.
"""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
WORK = HERE.parent.parent / 'query_t4_margin_native_figures_20260929_1952'
OUT = WORK / 'output'


def bind(path):
    path = Path(path)
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(name, payload):
    path = HERE / name
    with path.open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return bind(path)


def equal(pin):
    current = bind(pin['path'])
    if current != pin:
        raise AssertionError('Changed since executed review: ' + pin['path'])
    return current


def snapshot(path):
    path = Path(path)
    dest = HERE / 'raw_final' / path.name
    with dest.open('xb') as stream:
        stream.write(path.read_bytes())
    a, b = bind(path), bind(dest)
    if a['sha256'] != b['sha256'] or a['bytes'] != b['bytes']:
        raise AssertionError('Snapshot mismatch')
    return {'source': a, 'snapshot': b}


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data_pin, artifact_pin = bind(HERE / 'DATA_CONTRACT.json'), bind(HERE / 'ARTIFACT_REVIEW.json')
    if data_pin['sha256'] != 'bf1d5a1c96e59924ab3169dadd6857794b757175d4ebf0c345892807268dc43e':
        raise AssertionError('Contract pin changed')
    if artifact_pin['sha256'] != '716f6d0996e29747611dfd492463a219121ba360cf8c41403d4b0a27d19babcb':
        raise AssertionError('Artifact review pin changed')
    contract, actual = load(HERE / 'DATA_CONTRACT.json'), load(HERE / 'ARTIFACT_REVIEW.json')
    if contract['checks'] != 4299 or actual['checks'] != 89023:
        raise AssertionError('Unexpected executed scope')
    equal(contract['source'])
    equal(actual['source'])
    stable_bindings = [equal(p) for p in actual['bindings']]
    (HERE / 'raw_final').mkdir(exist_ok=False)
    final_snapshots = [snapshot(p) for p in (
        WORK / 'build/build_t4.mjs', WORK / 'INPUT_PROVENANCE.json',
        OUT / 'README.md', OUT / 'CAPTIONS.md', OUT / 'FIGURE_INDEX.json')]
    source_review = write('SOURCE_REVIEW.json', {
        'schema': 'independent-t4-margin-native-static-source-review.v1', 'utc': stamp,
        'reviewer': '/root/sep29_eval_audit', 'accepted_with_stated_limits': True,
        'method': 'Complete producer builder and frozen original key source functions read as text; no producer/scientific module imported or executed.',
        'sealing_source': bind(Path(__file__)), 'producer_source_and_document_snapshots': final_snapshots,
        'original_source_fragments': contract['static_original_source_fragments'],
        'findings': [
            'Only the saved 132 visual_margin_quartile strata are mapped to eleven pages: three seed columns and three metric rows per page. The other330 entropy/semantic strata remain in exact source copies but are not plotted.',
            'Original _load_aligned_pair/align_visual_full align Full to Visual query paths and labels. _strata_for_pair derives assignments from Visual raw margin, and stratum_summary/_paired_metric_matrix apply one identical selected mask to both variants.',
            'Original quartile_assignment uses linear 25/50/75 percentiles and left-side searchsorted: cutpoint ties enter the lower interval. The figure does not recompute these bins, boundaries, counts or members.',
            'The actual registered threshold is100 queries:84 selected strata pass only that count gate;48 SUES satellite-to-UAV strata have N20 and are false. N20 dagger and a visible N<100 descriptive-only explanation are present.',
            'R@1 and official trapezoidal mAP are displayed as saved fractions times100 and labelled percent; MRR times100 is explicitly labelled scaled MRR. All axes remain0–100 and all792 saved values are also printed to three decimals.',
            'The categorical Q1–Q4 x positions do not assert equal numerical margin widths. Native adjacent segments are guides, not fitted curves or extra observations.',
            'No pooled statistic, SD, CI, bootstrap, p-value or significance is drawn. No new scientific means, membership or model/ranking/AP computation occurs in the builder.',
            'The same builder source was used for the two-page sample and final eleven-page output, with output scope controlled by --sample. There was no producer source revision or rejected candidate reported for this figure task.',
            'The external README and captions explicitly preserve same-membership, Visual-anchored conditional interpretation, threshold100, excluded330 strata, unresampled-bootstrap and upstream evidence limits.',
            'The builder makes native flat PPT text/geometric objects and SVG vector primitives. Actual exported bytes are independently verified in ARTIFACT_REVIEW; this static review does not replace that execution.'
        ], 'remaining_blockers': [],
        'limits': [
            'Same-member masked comparison is anchored on Visual itself; it is not causal/mechanistic attribution or independent calibration evidence. Raw margin is not a posterior.',
            'The upstream132 query-level margin recomputations are inherited from the adopted root, not executed here. Other330 cache-derived strata and upstream bootstrap intervals are not newly validated or plotted.',
            'Stored AP/RR/margins, checkpoint/cache/image SHA authority and historical chain gaps remain inherited. No old NPZ, checkpoint, cache, image, model or complete ranking/AP computation was read or run.',
            'No producer checker result is counted as independent review execution.'
        ]})
    per_page = []
    for figure in actual['figures']:
        pin = equal(figure['png'])
        for key in ('svg', 'source_csv'):
            equal(figure[key])
        observations = [
            'Entire final page actually viewed with view_image(detail=original),1375×1619 pixels.',
            'Dataset, retrieval direction and height labels readable; separate seeds1/2/3 and three metric units remain clear.',
            'All Q1–Q4/N labels and the blue-circle Visual/orange-square Full encodings are visible. V/F numeric rows preserve the values despite the common0–100 axes.',
            'No visible title, plot, tick, numeric-row or footer clipping and no unwanted text/data overlap at this original-resolution viewing scale.',
            'Real nonmonotonic, crossing or coincident marks are retained; categorical guide segments do not imply a continuous margin axis.'
        ]
        if figure['ordinal'] == 3:
            observations.append('Street values remain near the zero baseline on honest0–100 axes; printed three-decimal values make the low results readable without changing scale.')
        if figure['ordinal'] in (5, 7, 9, 11):
            observations.append('Every seed displays four20-dagger counts. The visible N<100/performance_claim_eligible=false/descriptive-only footer resolves their eligibility status.')
        per_page.append({'ordinal': figure['ordinal'], 'task': figure['task'], 'preview': pin,
                         'dimensions_px': figure['png_dimensions'], 'tool': 'view_image', 'detail': 'original',
                         'actual_visual_inspection': True, 'result': 'pass_at_stated_scale', 'observations': observations})
    visual_review = write('VISUAL_REVIEW.json', {
        'schema': 'independent-t4-margin-native-actual-visual-review.v1', 'utc_recorded': stamp,
        'reviewer': '/root/sep29_eval_audit', 'accepted_with_stated_limits': True,
        'sealing_source': bind(Path(__file__)), 'artifact_review': artifact_pin,
        'method': 'Actual view_image(original) calls on all eleven final PPTX roundtrip PNGs, in batches1–3,4–6,7–9,10–11. This sealer records judgments already made; it does not inspect images.',
        'all_eleven_viewed': True, 'images': per_page,
        'preview_generation_authority': 'Pinned producer BUILD_REPORT and read builder export the final PPTX, re-import it, and render each page on CPU. Independent reviewer did not rerender or open Microsoft PowerPoint.',
        'findings': 'No remaining visible layout blocker at the recorded original resolution. Compact numerical rows remain readable; all physical font and native geometry claims are checked separately in the artifact report.',
        'limits': ['Preview inspection is not a physical-print, accessibility or cross-version PowerPoint rendering guarantee.',
                   'Physical font sizes come from actual SVG scales and PPT XML, not apparent preview size. Reducing width reduces the effective font size.',
                   'Visual inspection neither validates scientific model/ranking/AP correctness nor adds uncertainty or significance.']})
    readme = HERE / 'README.md'
    with readme.open('x', encoding='utf-8') as stream:
        stream.write('''# Independent T4 shared Visual-margin figure review

The final eleven-page native figure set is accepted with the stated limits. Parent root adoption is a separate decision.

`DATA_CONTRACT.json` records the first successful 4,299-check adopted-small-source/display contract execution. `ARTIFACT_REVIEW.json` records the first successful 89,023-check new CSV/SVG/PPT artifact execution. Neither suite was repeated. No producer checker was imported/executed and its count is not independent evidence. No old NPZ/query-statistic suite, scientific package, model, GPU, weights, cache or image dataset was read or run.

Scope:132 saved Visual-margin strata from11 tasks × three seeds × four quartiles,99 panels,792 points and printed metric values,594 guide segments,132 N labels including48 N20 dagger flags. The PPTX contains4,851 native editable shapes including2,354 text objects, without raster/group/chart substitutes. Both SVG and actual OOXML use at least8 physical points at181.9mm width. Height is214.136111mm. The792 plotted fractions/N/flags, geometries, units, labels, source CSVs and speaker notes were independently checked.

The original frozen source aligns Full to Visual queries, derives quartile assignments from Visual raw margin using linear cutpoints and lower-interval ties, then applies exactly the same selected members to both variants. Saved cutpoints/counts/membership SHA are displayed/carried, not reconstructed here. Q1–Q4 are ordered categories; segments are guides, not equal numerical margin intervals or fitted curves. This is a Visual-anchored conditional comparison, not causal/mechanistic attribution or independent calibration evidence. Margin is not a posterior.

The registered count threshold is100:84 strata pass the count gate only;48 satellite-to-UAV SUES strata have N20 and performance_claim_eligible=false. All48 are visibly flagged and remain descriptive only. Eligibility is not significance. No seed/task/height pooling, SD, CI, bootstrap, p-value or inferential claim is added. The other330 entropy/semantic strata and inferential source fields remain in exact source copies but are not plotted or newly accepted by this figure review.

R@1 and official trapezoidal mAP fractions are scaled by100 and labelled percent; MRR×100 is explicitly scaled MRR. Axes remain0–100, and three-decimal printed values preserve readable low street results. The source-value-to-display CSV comparison allows2e-14 absolute display-unit serialization roundoff, geometry1e-8pt and XML2EMU. These are export-mapping bounds, not scientific tolerances.

`SOURCE_REVIEW.json` records complete builder/key-original-function text review. `VISUAL_REVIEW.json` separately records actual original-resolution1375×1619 inspection of every final PPT-roundtrip PNG. All directions/heights, street low values, seeds, N20 daggers and footnotes were readable; no visible clipping or unwanted label/data overlap was found. There was no requested candidate revision or independent contract/artifact failure. The sample and full output used the same unchanged builder.

Upstream132 margin-mask/query recomputations are inherited from the adopted root, not repeated. Stored AP/RR/margin values, inherited checkpoint/cache/image SHA and historical chain gaps, absence of model/full-ranking/all-positive-rank AP recomputation, and unresampled bootstrap limits remain. This is clean official-query analysis, not corruption robustness. Microsoft PowerPoint was not opened; previews do not guarantee print or every PowerPoint version. No live process, scientific state/source, recovery release, HANDOFF or automation was changed.
''')
    sources = [bind(HERE / n) for n in ('derive_contract.py', 'review_artifacts.py', 'seal_review.py')]
    execution = {}
    for prefix, checks in (('contract', 4299), ('artifact', 89023)):
        execution[prefix] = {'first_execution_exit_code': 0, 'checks': checks,
                             'stdout': bind(HERE / (prefix + '.stdout.log')),
                             'stderr': bind(HERE / (prefix + '.stderr.log')),
                             'authority': 'Observed tool execution and immutable report; no repeated suite.'}
    metadata = write('METADATA.json', {
        'schema': 'independent-t4-margin-native-review-metadata.v1', 'utc': stamp,
        'accepted_with_stated_limits': True, 'scope': actual['totals'],
        'reports': [data_pin, artifact_pin, source_review, visual_review],
        'review_readme': bind(readme), 'sources': sources, 'execution': execution,
        'sealer_scope': 'Only immutable report/source/new-artifact byte stability and final provenance; no second data/geometry/scientific suite.',
        'final_actual_artifact_bindings': stable_bindings, 'final_small_snapshots': final_snapshots,
        'original_small_snapshots': contract['inputs'],
        'failure_record': 'No independent contract/artifact execution failure and no rejected producer candidate in this figure task.',
        'scientific_execution': False, 'PowerPoint_opened': False})
    delivery = write('DELIVERY.json', {
        'schema': 'independent-t4-margin-native-review-delivery.v1', 'utc': stamp,
        'accepted_with_stated_limits': True,
        'scope': 'Eleven T4 task pages;132 shared Visual-margin quartiles,99 panels,792 points; all eleven PNGs actually viewed.',
        'data_contract': data_pin, 'artifact_review': artifact_pin, 'source_review': source_review,
        'visual_review': visual_review, 'metadata': metadata, 'readme': bind(readme), 'sources': sources,
        'figures_pptx': bind(OUT / 't4_margin_native_editable_11figures.pptx'),
        'independent_execution_checks': {'small_source_contract': 4299, 'actual_new_artifacts': 89023},
        'upstream_root': contract['root_adoption'],
        'interpretation_limits': [
            'Only adopted saved small values and new figure artifacts; no old NPZ/query/quantile/member/bootstrap or scientific suite repeated.',
            'Same Visual-defined members, lower-interval ties; Visual-anchored conditional comparison, not causal/calibrated/mechanistic evidence.',
            '84 eligible is only a count gate.48 N20 strata are visibly descriptive-only below100; no inference, pooling, SD/CI/p-values.',
            'The330 other entropy/semantic strata are preserved in original files but not plotted or newly accepted here.',
            'Clean official-query scope and all upstream SHA/chain/stored AP/RR/model/full-ranking limits retained.',
            'Native flat objects and actual original previews; no PowerPoint runtime or physical-print guarantee.'],
        'root_adoption': 'Pending parent independent review/binding; this report does not assert parent adoption.'})
    print(json.dumps({'delivery': delivery, 'metadata': metadata, 'source_review': source_review,
                      'visual_review': visual_review, 'sources': sources}, ensure_ascii=False))


if __name__ == '__main__':
    main()
