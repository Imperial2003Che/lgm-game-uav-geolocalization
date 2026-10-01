"""Seal this independent review after actual view_image inspection of pages 1--22.

This script records observations already made by the reviewing agent. It does
not perform, infer, or replace visual inspection. Only stdlib and new figure
artifacts/small accepted metadata are read. Existing review files are immutable.
"""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import struct

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
WORK = BASE / 'robustness_native_figures_20260929_1650'
ROOT = HERE.parent / 'pipeline_post_robustness_audit_20260929_1448/ROOT_POST_ROBUSTNESS_ADOPTION.json'
PINS = {
    ROOT: 'f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a',
    HERE / 'DATA_CONTRACT.json': '23862cec0a5ff996cb34be45ab594d93a437b4bbbe09338d1978ae9def028dc4',
    HERE / 'ARTIFACT_REVIEW.json': 'bd5f71be759d43d9ac88e3a0a8f3421c86b8499997af947bdd5c98c47246527b',
    WORK / 'BUILD_REPORT.json': '91a3617b0a57a0d28dd3deb355472f24b2bdcbabd4731de0814ffb9fe975ae61',
    WORK / 'INPUT_PROVENANCE.json': '391a87f2b0d4b45ae325f1eb01492a139eace1e703da8bff3f4d2f69dc0603d3',
    WORK / 'build/build_robustness.mjs': '7f17a68579d38567737370ba35280211ca02d56f010e51a9aa8f84d225fb3fa4',
    WORK / 'output/robustness_native_editable_22figures.pptx': '3c754b27ecba7fb1de3bc78c4982fa18b3c68552e11b5d9b6240605e692f4ab4',
}

def bind(path):
    path = Path(path)
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def write_json(name, value):
    with (HERE / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return bind(HERE / name)

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def main():
    for path, expected in PINS.items():
        assert bind(path)['sha256'] == expected, str(path)
    build = load(WORK / 'BUILD_REPORT.json')
    contract = load(HERE / 'DATA_CONTRACT.json')
    artifact = load(HERE / 'ARTIFACT_REVIEW.json')
    assert build['figureCount'] == len(build['figures']) == 22
    assert artifact['assertions'] == 90810
    assert artifact['totals'] == {'figures': 22, 'markers': 1584, 'segments': 1320, 'texts': 2102, 'native_shapes': 7042}
    # Freeze current new artifacts after inspection; this is byte stability, not
    # a rerun of either the old scientific suite or the new geometry checks.
    for rec in artifact['bindings']:
        current = bind(rec['path'])
        assert current['bytes'] == rec['bytes'] and current['sha256'] == rec['sha256']
    sample = WORK / 'build/build_robustness_sample.mjs'
    final = WORK / 'build/build_robustness.mjs'
    sample_text = sample.read_text(encoding='utf-8')
    final_text = final.read_text(encoding='utf-8')
    token = 'figureReports.push({ordinal:fig.ordinal,task:fig.task'
    assert sample_text.count(token) == 1
    assert sample_text.replace(token, 'figureReports.push({ordinal:fig.ordinal,stem:fig.stem,task:fig.task') == final_text
    diff = ''.join(difflib.unified_diff(sample_text.splitlines(True), final_text.splitlines(True),
                                      fromfile=str(sample), tofile=str(final)))
    with (HERE / 'INDEPENDENT_SAMPLE_TO_FINAL.patch').open('x', encoding='utf-8') as stream:
        stream.write(diff)
    viewed = []
    raw = HERE / 'raw'
    raw.mkdir(exist_ok=False)
    for rec, expected in zip(build['figures'], artifact['figures']):
        assert (rec['ordinal'], rec['task'], rec['metric']) == (expected['ordinal'], expected['task'], expected['metric'])
        png = Path(rec['preview']['path'])
        pin = bind(png)
        assert pin['sha256'] == rec['preview']['sha256'] and pin['bytes'] == rec['preview']['bytes']
        data = png.read_bytes()
        assert data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR'
        width, height = struct.unpack('>II', data[16:24])
        assert (width, height) == (1375, 1247)
        snap = raw / png.name
        with snap.open('xb') as stream:
            stream.write(data)
        assert bind(snap)['sha256'] == pin['sha256']
        findings = [
            'Title, task direction/height, metric, own-clean values, six panels, legend, ticks and all four visible limitation lines are readable.',
            'No apparent text clipping, missing glyphs, overlapping labels or clipped markers in this actual full-page PNG.',
            'Blue-circle Visual and orange-square Full encoding is consistent, including near-overlapping data points.',
        ]
        if rec['ordinal'] == 5:
            findings.append('The observed Visual brightness peak at 150% is fully visible below the common 160% maximum; non-monotonic curves and low absolute clean values remain visible.')
        viewed.append({'ordinal': rec['ordinal'], 'task': rec['task'], 'metric': rec['metric'],
                       'image': pin, 'snapshot': bind(snap), 'native_dimensions_px': [width, height],
                       'actually_viewed': True, 'method': 'tools.view_image detail=original, separate full-page image, no contact-sheet substitution',
                       'findings': findings, 'blocking_visual_issue': None})
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    visual = write_json('VISUAL_REVIEW.json', {
        'schema': 'independent-native-robustness-visual-review.v1', 'utc': now,
        'scope': 'All 22 final PPT round-trip PNG renders; pages 1--22 actually displayed to and inspected by /root/sep29_eval_audit in six tool calls (1--4, 5--8, 9--12, 13--16, 17--20, 21--22).',
        'visual_judgment_origin': 'Reviewing agent; this sealing script records prior manual observations and hashes, not an automated visual judge.',
        'build_report': bind(WORK / 'BUILD_REPORT.json'), 'pptx': bind(WORK / 'output/robustness_native_editable_22figures.pptx'),
        'viewed_final_pages': viewed, 'result': 'No blocking visual issue found in all 22 actual final full-page renders.',
        'limits': ['The renderer was the producer artifact-tool PPT reimport renderer; Microsoft PowerPoint was not launched by this review.',
                   'Inspection is of these 1375x1247 renders, not a print proof or a claim about every office suite.',
                   'PNG previews are raster previews only; the SVG/PPT deliverables were independently verified as native vector/shapes/text.',
                   'Earlier sample-page viewing does not substitute for this final 22-page visual inspection.'],
        'sealing_source': bind(Path(__file__)),
    })
    source_review = write_json('SOURCE_REVIEW.json', {
        'schema': 'independent-native-robustness-source-review.v1', 'utc': now,
        'producer_sample_source': bind(sample), 'producer_final_source': bind(final),
        'independently_generated_diff': bind(HERE / 'INDEPENDENT_SAMPLE_TO_FINAL.patch'),
        'read_scope': 'Full sample producer source was read before final; final line 124 and complete independently computed sample-to-final diff were read. Diff is exactly one added stem:fig.stem report field.',
        'change': 'Readable final preview filename; no chart layout, data, text, scientific calculation or rendering-path change.',
        'source_execution': 'Producer source/checker was not imported or executed by this independent reviewer.',
        'artifact_scope': 'Actual final SVG/PPT/CSV are verified by independently written review_native.py; source review alone is not artifact acceptance.',
        'sealing_source': bind(Path(__file__)),
    })
    small_sources = [ROOT, HERE / 'derive_contract.py', HERE / 'review_native.py', Path(__file__),
                     HERE / 'DATA_CONTRACT.json', HERE / 'ARTIFACT_REVIEW.json',
                     WORK / 'BUILD_REPORT.json', WORK / 'INPUT_PROVENANCE.json', sample, final]
    snapshots = []
    for ordinal, path in enumerate(small_sources, 1):
        data = path.read_bytes()
        dst = raw / f'{ordinal:02d}_{path.name}'
        with dst.open('xb') as stream:
            stream.write(data)
        assert bind(path)['sha256'] == bind(dst)['sha256']
        snapshots.append({'original': bind(path), 'snapshot': bind(dst)})
    limits = [
        'Only existing adopted seed-1 results are illustrated; no additional experiment was run and no independent model/full-ranking/AP/CLIP-cache reproduction is claimed.',
        'No across-task pooling, multiple-seed SD, confidence interval or significance claim. 1320 plotted rows are exactly the two plotted metrics from 3960 six-metric aggregate rows.',
        'Retention is 100*corrupted/own-clean; C=100 is defined only for the checked positive clean values. A retention advantage or smaller drop does not establish higher absolute corrupted accuracy.',
        'Full clean CLIP uses cached evidence and corrupted-query CLIP is online. Curves mix evidence-path differences and image corruption. The 64-sample diagnostic has no equivalence threshold.',
        'All upstream inherited checkpoint/cache/image checks and historical evidence-chain gaps remain. This artifact audit does not close those gaps.',
        'PPT charts are editable flat native shapes and text, not native Excel chart objects/workbooks. Original Microsoft PowerPoint was not opened.',
        'Physical font >=8pt follows actual SVG dimensions/viewBox and PPT XML; actual final PNG visual scope is separately documented.',
        'No old scientific/weight/cache/image/NPZ tests or scientific imports were repeated. Earlier 5350/6600 data checks and new 90810 artifact assertions each ran once.',
    ]
    metadata = write_json('METADATA.json', {
        'schema': 'independent-native-robustness-review-metadata.v1', 'utc': now,
        'root_adoption': bind(ROOT), 'small_file_snapshots': snapshots,
        'data_contract_report': bind(HERE / 'DATA_CONTRACT.json'),
        'artifact_report': bind(HERE / 'ARTIFACT_REVIEW.json'),
        'visual_report': visual, 'source_review': source_review,
        'scope': {'figures': 22, 'plotted_source_rows': 1320, 'aggregate_source_rows': 3960,
                  'data_contract_assertions': 5350, 'decimal50_formula_checks': 6600,
                  'artifact_assertions': 90810, **artifact['totals']},
        'execution': {'data_contract_first_run_exit_code': 0, 'artifact_first_run_exit_code': 0,
                      'actual_final_png_views': 22, 'scientific_execution': False, 'PowerPoint_opened': False,
                      'producer_files_modified': False, 'root_or_live_state_modified': False},
        'limits': limits,
    })
    readme = '''# Independent review of 22 native robustness figures

Accepted within the scope and limitations below. The complete 22 SVG figures and
22-page PPT deck map to the already adopted 22 source CSVs: 1320 rows for R@1 and
official trapezoidal mAP, selected exactly from the 3960-row six-metric aggregate.

`DATA_CONTRACT.json` records 5350 independent assertions and 6600 Decimal50 formula
checks. `ARTIFACT_REVIEW.json` records 90,810 new artifact assertions: direct CSV to
SVG marker/segment geometry, actual PPT XML shapes/text/geometry, axes, units,
colors, labels, all source mapping, exact CSV in notes and physical fonts >=8pt.
There are 1584 markers, 1320 data segments, 2102 editable texts and 7042 native PPT
shapes. No raster image substitutes are embedded in the SVG/PPT deliverables.

`VISUAL_REVIEW.json` separately records actual full-page viewing of every final
PPT-rendered PNG, pages 1--22, at native 1375x1247 resolution using view_image with
detail=original. No blocking cropping/overlap/label issue was found. This is not a
Microsoft PowerPoint or print-proof claim. The visual report contains exact PNG
hashes and sealed byte copies. Page 5 retains the true 150% maximum within a 160%
axis. Other >100% values and non-monotonic trends are also retained.

`SOURCE_REVIEW.json` and the independent diff bind the final source to its actual
sample backup. The only change adds the filename stem to report metadata. No
producer code was imported or executed by this independent reviewer.

Seed 1 is descriptive only. There is no task pooling, seed SD, CI or significance
claim. Retention uses each variant's own clean baseline; it is not absolute
accuracy, and a retention advantage does not establish an accuracy advantage.
The absolute clean values are visible. Full clean CLIP is cached and corrupted
query CLIP is online, so image and evidence-path effects are mixed. The 64-sample
diagnostic has no numerical-equivalence threshold. Upstream checkpoint/cache/
image inheritance and historical chain gaps remain. No weights, raw scientific
images/cache/NPZ, model, ranking, AP or scientific suite were rerun here.

PPT editability means native flat shapes and text, not an Excel chart/workbook.
The prior formula checks and the current geometry checks were each run once.
The sealing step checks byte stability and records actual observations; it does
not repeat the scientific or formula suites. No live state, original source,
producer deliverable, HANDOFF or automation was modified by this review.
'''
    with (HERE / 'README.md').open('x', encoding='utf-8') as stream:
        stream.write(readme)
    delivery = write_json('DELIVERY.json', {
        'schema': 'independent-native-robustness-review-delivery.v1', 'utc': now,
        'accepted_with_stated_limits': True,
        'metadata': metadata, 'readme': bind(HERE / 'README.md'),
        'data_contract': bind(HERE / 'DATA_CONTRACT.json'),
        'artifact_review': bind(HERE / 'ARTIFACT_REVIEW.json'), 'visual_review': visual,
        'source_review': source_review, 'independent_diff': bind(HERE / 'INDEPENDENT_SAMPLE_TO_FINAL.patch'),
        'review_sources': [bind(HERE / name) for name in ('derive_contract.py', 'review_native.py', 'seal_review.py')],
        'artifact_bindings': artifact['bindings'], 'final_preview_bindings': [v['image'] for v in viewed],
        'limits': limits,
    })
    print(json.dumps({'delivery': delivery, 'metadata': metadata, 'visual': visual, 'source_review': source_review}, ensure_ascii=False))

if __name__ == '__main__':
    main()
