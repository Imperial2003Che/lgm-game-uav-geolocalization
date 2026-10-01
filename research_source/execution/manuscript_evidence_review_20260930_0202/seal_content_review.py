"""Seal an independent static manuscript review; no producer/scientific execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, difflib

R = Path(__file__).resolve().parent
O = R.parent.parent
P = R.parent / 'manuscript_revision_scope_20260930_0202'
M = O / 'manuscript_evidence_revision_20260930_0202/manuscript'
B = O.parent / 'paper_label_revision_20260914/manuscript'

def pin(p):
    p = Path(p)
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def readj(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def writej(name, obj):
    p = R / name
    with p.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return pin(p)

numeric = readj(R / 'NUMERIC_TRANSCRIPTION_REVIEW.json')
query = readj(R / 'query_review/QUERY_FRAGMENT_REVIEW.json')
checklist = readj(R / 'INPUT_CHECKLIST.json')
author = readj(P / 'AUTHOR_INTEGRATION.json')
layout = readj(P / 'layout_revision_a1/REVISION.json')
checks = []

def check(name, condition, evidence):
    checks.append({'name': name, 'passed': bool(condition), 'evidence': evidence})
    if not condition:
        raise AssertionError(name)

check('Existing independent numeric review passed 484 displayed scalars',
      numeric['passed'] and numeric['scalar_count'] == 484,
      pin(R / 'NUMERIC_TRANSCRIPTION_REVIEW.json'))
check('Existing narrow independent query fragment review passed', query['passed'],
      pin(R / 'query_review/QUERY_FRAGMENT_REVIEW.json'))

# Narrow amendments only. The 484-cell comparison is not rerun.
for c in layout['changes']:
    for label in ['before', 'after', 'diff']:
        check('Layout byte binding: ' + label + ': ' + Path(c[label]['path']).name,
              pin(c[label]['path']) == c[label], c[label])

map_before = P / 'layout_revision_a1/before/tables/evidence_20260930/official_map.tex'
map_after = M / 'tables/evidence_20260930/official_map.tex'
check('mAP table amendment is only duplicate-caption deletion',
      map_before.read_bytes().replace(b'Official official trapezoidal', b'Official trapezoidal') == map_after.read_bytes(),
      {'before': pin(map_before), 'after': pin(map_after)})
main_before = P / 'layout_revision_a1/before/main.tex'
main_after = M / 'main.tex'
old = b'% Bibliography balancing must be reviewed after compiling this expanded local draft.'
new = b'\\clearpage\n% Start the bibliography on a normal page after flushing the remaining floats.'
check('Main amendment is only clearpage and explanatory comment',
      main_before.read_bytes().replace(old, new) == main_after.read_bytes(),
      {'before': pin(main_before), 'after': pin(main_after)})
fusion_before = P / 'layout_revision_a1/before/tables/formal_best_fusion_comparison_table.tex'
fusion_after = M / 'tables/formal_best_fusion_comparison_table.tex'
check('Historical fusion table amendment is only !t to !p',
      fusion_before.read_bytes().replace(b'\\begin{table*}[!t]', b'\\begin{table*}[!p]', 1) == fusion_after.read_bytes(),
      {'before': pin(fusion_before), 'after': pin(fusion_after)})
for name, old_pin in numeric['tables'].items():
    table_path = M / 'tables/evidence_20260930' / name
    comparison_path = map_before if name == 'official_map.tex' else table_path
    observed = pin(comparison_path)
    check('Previously checked numeric table preserved: ' + name,
          observed['sha256'] == old_pin['sha256'] and observed['bytes'] == old_pin['bytes'],
          {'reviewed': old_pin, 'final': pin(table_path), 'caption_only_change': name == 'official_map.tex'})

sem_before = P / 'semantic_results_before_terminology.tex'
sem_final = M / 'results/semantic_results.tex'
check('Main fragment query bytes preserved; only training-run terminology changes',
      sem_before.read_bytes().replace(b'42 trained configurations', b'42 completed training runs') == sem_final.read_bytes(),
      {'reviewed_fragment': pin(sem_before), 'final': pin(sem_final)})
fragment_bindings = {Path(x['path']).name: x for x in query['bindings'] if Path(x['path']).suffix == '.tex'}
check('Initial query-reviewed main fragment binding retained',
      pin(sem_before)['sha256'] == fragment_bindings['semantic_results.tex']['sha256'], pin(sem_before))
suppfrag = M / 'results/supplementary_evidence.tex'
check('Query-reviewed supplementary fragment unchanged in final assembly',
      pin(suppfrag)['sha256'] == fragment_bindings['supplementary_evidence.tex']['sha256'], pin(suppfrag))

# Read/hash only the small source/config/manifest evidence for the added best.pt sentence.
best_evidence = [x for x in author['inputs'] if Path(x['path']).name in
                 ['formal_retrieval.py', 'run_frozen_formal_matrix.py', 'run_manifest.json', 'run_config.json']]
check('Four exact best.pt supporting sources present', len(best_evidence) == 4, best_evidence)
for expected in best_evidence:
    check('best.pt source binding: ' + Path(expected['path']).name, pin(expected['path']) == expected, expected)
manifest = readj(next(x['path'] for x in best_evidence if Path(x['path']).name == 'run_manifest.json'))
config = readj(next(x['path'] for x in best_evidence if Path(x['path']).name == 'run_config.json'))
check('Small run example matches fixed final epoch with no validation/test selection',
      manifest['epochs_completed'] == 80 and manifest['best_epoch'] == 79
      and manifest['best_validation_mAP'] is None and manifest['test_protocol_was_evaluated'] is False
      and config['immutable_config']['selection']['patience'] == 0
      and config['immutable_config']['validation_ids'] == [],
      'Example only; overall 42-run acceptance remains inherited from the root official adoption. No checkpoint opened.')

# Final bindings for all text source dependencies, excluding inherited figure PDFs.
text_sources = [x for x in layout['final_sources'] if Path(x['path']).suffix.lower() != '.pdf']
for expected in text_sources:
    check('Final text source matches producer frozen pin: ' + str(Path(expected['path']).relative_to(M)),
          pin(expected['path']) == expected, expected)
local_readme = M / 'README_LOCAL_WORKING_DRAFT.md'
final_text_bindings = [pin(x['path']) for x in text_sources] + [pin(local_readme)]

# Preserve complete final logical diff against the actual copied baseline; no producer execution.
diffs = []
for current in sorted(M.rglob('*.tex')):
    rel = current.relative_to(M)
    prior = B / rel
    a = prior.read_text(encoding='utf-8').splitlines(True) if prior.exists() else []
    b = current.read_text(encoding='utf-8').splitlines(True)
    if a != b:
        diffs.append(''.join(difflib.unified_diff(a, b, fromfile='actual_base/' + rel.as_posix(), tofile='final/' + rel.as_posix())))
for name in ['README_OVERLEAF.md', 'README_LOCAL_WORKING_DRAFT.md']:
    prior = B / name
    a = prior.read_text(encoding='utf-8').splitlines(True) if prior.exists() else []
    b = (M / name).read_text(encoding='utf-8').splitlines(True)
    if a != b:
        diffs.append(''.join(difflib.unified_diff(a, b, fromfile='actual_base/' + name, tofile='final/' + name)))
with (R / 'FINAL_LOGICAL_DIFF.patch').open('x', encoding='utf-8', newline='\n') as f:
    f.write(''.join(diffs))

claims = [
 {'claim': '42 completed runs = 36 main + six seed-1 sensitivity; 231 official run-task records = 198 + 33; 66 main three-seed task-variant groups.', 'judgment': 'PASS', 'authority': 'official root adoption plus adopted main/sensitivity small tables'},
 {'claim': 'All 11 tasks and six main variants, all sensitivity settings and all 22 transfer groups retained. Stored equal-seed means and sample SD (n-1=2); single-fit sensitivity has no SD.', 'judgment': 'PASS', 'authority': '484 direct displayed-scalar checks; no recalculation of means or SD'},
 {'claim': 'Official Full lower mean R@1 and trapezoidal mAP on 10/11 tasks; all eight SUES tasks lower. Street2S exception is retained at low absolute accuracy.', 'judgment': 'PASS', 'authority': 'stored per-task summary sign comparisons, including main abstract/contributions/results/discussion/conclusion'},
 {'claim': 'Official illustrative R@1 values Full/Visual: D2S 32.300/37.864%, S2D 44.175/54.303%, Street2S .969/.788%; Street2S mAP 2.267/1.906%.', 'judgment': 'PASS', 'authority': 'stored adopted CSV values and three-decimal display'},
 {'claim': 'Transfer 12 source-model evaluations, 66 seed-task records, 22 groups; Full mean R@1 lower on all 11 target tasks, mAP/MRR lower on 10.', 'judgment': 'PASS', 'authority': 'transfer root adoption and adopted summary/contrast CSVs'},
 {'claim': 'Transfer Street2S positive mAP .040 percentage points and MRR .105 scaled points; Full R@1 .233% with actual zero sample SD versus Visual .258%.', 'judgment': 'PASS', 'authority': 'saved transfer contrasts and summaries; fraction-to-display scale 100, MRR not described as accuracy percentage'},
 {'claim': 'Official mAP is trapezoidal; descriptive seed SD is not CI/SE/significance; tasks, directions, heights, and seeds are not newly pooled.', 'judgment': 'PASS', 'authority': 'all five captions, new result modules, protocol and conclusion'},
 {'claim': 'Seed-1 corruption: four dataset-variant runs, six families, five severities, 11 tasks, 660 corrupted evaluations, 22 clean references, 3960 six-metric rows, 1320 R@1/mAP plot rows.', 'judgment': 'PASS', 'authority': 'stored adopted robustness rows and root post-robustness adoption; no scientific recomputation'},
 {'claim': 'Retention 100 corrupt/own-clean differs from absolute accuracy and percentage-point drop; >100 is permitted; supplied clean denominators positive.', 'judgment': 'PASS', 'authority': 'stored CSV denominator checks and explicit formulas'},
 {'claim': 'Full clean cached-CLIP vs corrupt online-CLIP path; 64-image diagnostic has no numerical equivalence gate; no causal pixel-only, multi-seed robustness, or compensating-advantage claim.', 'judgment': 'PASS', 'authority': 'root post-robustness adoption and original figure scope; retained in protocol, results, supplement and discussion'},
 {'claim': 'T4 Visual shared quartiles: 132 margin strata, 84 count-eligible and 48 SUES satellite-to-UAV groups of 20; threshold 100; entropy/semantic membership outside independent recount.', 'judgment': 'PASS', 'authority': 'independent narrow QUERY_FRAGMENT_REVIEW plus exact final-fragment preservation'},
 {'claim': 'T5 separate memberships, ceil(cN), selected-k risk versus selected-and-correct/common-N success; overlap means membership, full coverage ordinary R@1.', 'judgment': 'PASS', 'authority': 'independent narrow query semantic review and exact final fragments'},
 {'claim': 'T5 66 native series, 660 points, 132 paired records at .5/.75/.9/1; saved all-prefix AURC is not a ten-point trapezoid; 990 bins = 140 occupied + 850 empty, null empty means.', 'judgment': 'PASS', 'authority': 'independent narrow query stored-field checks'},
 {'claim': 'Margin score clip((s1-s2)/2,0,1), fraction ECE, no probability/calibration advantage; official 33, T4 eligible284 and T5 paired132 scopes remain distinct.', 'judgment': 'PASS', 'authority': 'official stored family rows plus query narrow review and adopted root scope'},
 {'claim': 'Root prior query audit recount covers 132 margin strata and T5 66/132; T4 tests checked saved discordance counts; bootstrap retained without independent resampling or new significance.', 'judgment': 'PASS', 'authority': 'upstream root post-robustness adoption; this manuscript reviewer performed none of those query/statistical recomputations'},
 {'claim': 'best.pt is final completed epoch in the no-validation fixed protocol, not performance-based selection.', 'judgment': 'PASS', 'authority': 'formal_retrieval.py 2163-2173/2276-2282; frozen-matrix checker 347-354/445-449; one bound small run manifest/config; 42-run scope inherited'},
 {'claim': 'Historical public-baseline numeric findings and inferential limits retain their separate scope; they are not semantic-fusion gains or new efficiency experiments.', 'judgment': 'PASS', 'authority': 'all logical manuscript changes inspected; inherited historical numeric text/table cells unchanged, only one table placement changed'},
 {'claim': 'This is a local working draft; external comparisons/efficiency and other work remain pending; no Overleaf or final-submission claim.', 'judgment': 'PASS', 'authority': 'main/supp visible draft labels and both current README files'}
]

report = {
 'schema': 'independent-manuscript-content-review.v1',
 'utc': datetime.now(timezone.utc).isoformat(),
 'decision': 'PASS for adopted-evidence transcription and new manuscript claims in the bound local working draft',
 'passed': True, 'unresolved_content_findings': [],
 'scope': 'Independent static review of all new/changed prose, five new tables, and full logical differences from the actual copied September 14 baseline. Existing adopted small evidence only; no new science or publication approval.',
 'baseline_correction': {'actual_base': str(B), 'record': pin(R / 'BASELINE_BINDING_ADDENDUM.json'), 'explanation': 'Initial checklist old_main points to a different historical copy; that checklist is preserved. The addendum and this final review use the actual paper_label_revision_20260914 baseline. Main differences between the two old copies were two captions; supplements/result placeholder matched.'},
 'skill_application': 'Anti-defensive writing used only for concise, claim-evidence-matched narrative. Negative findings and scientific scope limits are retained explicitly.',
 'review_methods': ['Human reading of complete logical old/new prose changes, all new modules/captions and three final amendment diffs.', 'Independent direct comparison of 484 actual TeX scalar displays with saved adopted fields and task/variant/unit mapping; producer transcript and checker not used.', 'Peer narrow query review of small saved records; final exact content adoption confirmed here.', 'Only byte-binding and narrow final-change checks executed at seal; no repeated 484-cell review.'],
 'numeric_review': pin(R / 'NUMERIC_TRANSCRIPTION_REVIEW.json'),
 'query_review': pin(R / 'query_review/QUERY_FRAGMENT_REVIEW.json'),
 'initial_checklist': pin(R / 'INPUT_CHECKLIST.json'),
 'final_logical_diff': pin(R / 'FINAL_LOGICAL_DIFF.patch'),
 'final_amendments': {'revision': pin(P / 'layout_revision_a1/REVISION.json'), 'resolved_finding': 'Removed duplicate Official in official mAP caption.', 'layout_only': ['Historical fusion table !t to !p', 'clearpage before bibliography plus explanatory comment'], 'numeric_cells_changed': False},
 'claim_review': claims,
 'seal_checks': checks,
 'final_text_source_bindings': final_text_bindings,
 'actual_baseline_bindings': [pin(B / n) for n in ['main.tex', 'supplementary.tex', 'results/semantic_results.tex']],
 'best_pt_small_evidence': best_evidence,
 'authority_bindings_inherited_from_initial_read': {k:v for k,v in checklist['sources'].items() if k not in ['old_main','old_supplement','old_empty_result_module','handoff']},
 'producer_sidecars': [pin(P / n) for n in ['AUTHOR_INTEGRATION.json','DELIVERY.json','FINAL_COMPLETE_MANUSCRIPT_DIFF.patch']],
 'not_performed': ['No producer execution or manuscript edit.', 'No model/NPZ/weight/cache/image-content scan, ranking/metric/mean/SD/bootstrap/statistical recomputation, old suite rerun, or new training.', 'No compilation or PDF visual review by this reviewer. Root owns those independently; its messages report final main16p/supp6p and no overfull/undefined labels.', 'No new independent validation of unchanged historical public-baseline science or inherited figure PDFs.', 'No COM, unknown-process access/control, HANDOFF/state/automation/Overleaf change.'],
 'limits': ['Conclusions apply to the exact final text bytes listed here.', 'Upstream adoption and historical provenance limitations remain inherited; this does not close missing large-asset hash chains.', 'Content PASS is not a claim that pending experiments are complete or that the paper is submission-ready.']
}
writej('CONTENT_REVIEW.json', report)
md = '''# Independent content review — PASS

The bound local working draft faithfully transcribes the adopted small tables and retains the negative results: Full is lower on 10/11 official tasks for mean R@1 and trapezoidal mAP, and on all 11 transfer tasks for mean R@1. No unresolved content blocker remains.

The actual copied baseline is `outputs/paper_label_revision_20260914/manuscript`; `BASELINE_BINDING_ADDENDUM.json` corrects the initial checklist without rewriting it. Complete logical changes and the final three limited amendments were read. The duplicate “Official” caption was corrected; the other two amendments only change float/bibliography placement.

`NUMERIC_TRANSCRIPTION_REVIEW.json` independently compared all 484 displayed scalar values in the five actual TeX tables with adopted CSV fields. It checked task/variant mapping, units, fraction scaling, rounding and true-zero handling. Final byte checks show those cells unchanged. No seed mean, SD or science result was recomputed.

The main/supplement preserve sample-SD limits, seed-1 corruption scope, the cached/online CLIP evidence-path difference, and the absence of a numerical parity gate. T4/T5 definitions preserve conditional memberships, k versus N denominators, all-prefix AURC, empty-bin nulls and bootstrap/audit limits. The independent narrow query review was read and its exact query text is retained in the final assembly. The added best.pt sentence is supported by small source/protocol/run evidence without reading checkpoints.

Historical public-baseline results remain separate. The work is explicitly a local draft, with pending comparisons and other experiments. This review does not attest compilation, PDF layout, unchanged historical science or large-asset byte integrity; root owns compilation and visual inspection separately. No producer, scientific suite, COM, Overleaf or automation was run or modified.

`CONTENT_REVIEW.json` supplies the claim-by-claim review, final exact source bindings and evidence scope. `DELIVERY.json` binds this report and the review artifacts.
'''
with (R / 'REVIEW.md').open('x', encoding='utf-8', newline='\n') as f:
    f.write(md)
delivery = {
 'schema': 'independent-manuscript-review-delivery.v1',
 'utc': datetime.now(timezone.utc).isoformat(),
 'passed': True,
 'report': pin(R / 'CONTENT_REVIEW.json'),
 'review_artifacts': [pin(R / x) for x in ['REVIEW.md','seal_content_review.py','NUMERIC_TRANSCRIPTION_REVIEW.json','verify_manuscript_numbers.py','INPUT_CHECKLIST.json','BASELINE_BINDING_ADDENDUM.json','FINAL_LOGICAL_DIFF.patch','query_review/QUERY_FRAGMENT_REVIEW.json','query_review/review_query_fragments.py']],
 'final_text_source_bindings': final_text_bindings,
 'producer_delivery': pin(P / 'DELIVERY.json'),
 'scope': 'Independent content review only; root compilation/layout/package acceptance is separate.'
}
writej('DELIVERY.json', delivery)
print(json.dumps({'passed': True, 'report': pin(R / 'CONTENT_REVIEW.json'), 'delivery': pin(R / 'DELIVERY.json'), 'checks': len(checks), 'final_text_sources': len(final_text_bindings)}, ensure_ascii=True))
