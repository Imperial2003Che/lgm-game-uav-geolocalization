from pathlib import Path
from datetime import datetime, timezone
import hashlib,json
R=Path(__file__).resolve().parent
O=R.parent.parent
def desc(p):
 p=Path(p); b=p.read_bytes(); return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
sources={
 'old_main':'manuscript/main.tex',
 'old_supplement':'manuscript/supplementary.tex',
 'old_empty_result_module':'manuscript/results/semantic_results.tex',
 'handoff':'execution/HANDOFF.md',
 'primary_claim':'formal_results_native_20260929/PRIMARY_CLAIM_REVIEW.json',
 'official_authority':'execution/evaluation_audits_20260929/ROOT_OFFICIAL42_AND_PIPELINE2_ADOPTION_20260929.json',
 'official_university':'formal_results/formal_main_university1652_variants_source.csv',
 'official_sues':'formal_results/formal_main_sues200_variants_source.csv',
 'sensitivity':'formal_results/formal_sensitivity_source.csv',
 'transfer_authority':'execution/transfer_results_20260929/ROOT_AGGREGATION_ADOPTION.json',
 'transfer_summary':'transfer_native_figures_20260929_1750/output/source_data/THREE_SEED_SUMMARY.csv',
 'transfer_contrast':'transfer_native_figures_20260929_1750/output/source_data/FULL_MINUS_VISUAL.csv',
 'post_robustness_authority':'execution/pipeline_post_robustness_audit_20260929_1448/ROOT_POST_ROBUSTNESS_ADOPTION.json',
 'robustness':'execution/pipeline_post_robustness_audit_20260929_1448/a1/aggregate/source_data/robustness_all_tasks_source.csv',
 't4':'execution/pipeline_post_robustness_audit_20260929_1448/a1/query/transactions_t4_strata.csv',
 't5_comparisons':'execution/pipeline_post_robustness_audit_20260929_1448/a1/query/transactions_t5_selective_comparisons.csv',
 't5_saved_fields':'execution/pipeline_post_robustness_audit_20260929_1448/a1/query/transactions_t5_selective_calibration.json',
 'robustness_display_scope':'robustness_native_figures_20260929_1650/output/README.md',
 't5_risk_scope':'query_t5_native_figures_20260929_1856/output_v2/README.md',
 't5_paired_scope':'query_t5_paired_native_figures_20260929_2157/output/README.md',
 't5_reliability_scope':'query_t5_reliability_native_figures_20260929_2054/output/README.md',
}
checks=[
 'Official accepted evaluation counts: 42 runs, 231 task evaluations (University 21/63; SUES 21/168). Main 36 fits use six variants, two datasets, seeds1/2/3; six sensitivity fits and sensitivity comparisons are seed1 only.',
 'Copy task-specific stored means and sample SD exactly with declared rounding. Official CSV fields already contain percentages; transfer CSV values are fractions and require x100 for R1/mAP. SD is across equally weighted seeds with n-1=2, not SE/CI. Do not turn MRR x100 into percentage accuracy.',
 'Retain official Full mean R1 and mAP lower in10/11 tasks; street exception remains below1% R1. Retain transfer Full meanR1 lower in all11 tasks and meanmAP lower in10/11; street mAP/MRR smallpositive and exactzero SD remain.',
 'Transfer has12 accepted runs,66 seed-task records,22 task-variant three-seed groups and11 within-task contrasts. Source and target direction, query/gallery counts and task names must remain correctly paired. No task/height/query-count pooling or significance inferred from mean differences.',
 'mAP is the official trapezoidal evaluator definition, not sklearn AP. The current audit transcribes saved adopted tables; it does not recompute full rankings or AP.',
 'Robustness: seed1 only; six corruptions x five severities x11 tasks x2variants x6metrics =3960 rows; R1/mAP subset1320 rows. Clean galleries, per-image query perturbation. Retention100*corrupt/own clean differs from absolute corrupted percentage and clean-minus-corrupt percentage-point drop; values>100 remain valid.',
 'Full robustness uses cached clean CLIP evidence and online corrupted-query CLIP; 64-sample diagnostic has no numerical equivalence gate. Do not attribute every change solely to pixels, imply negligible evidence-path effects, multiseed uncertainty or general robust superiority.',
 'T4:462 rows,132 independently recounted Visual-margin strata; actual eligible Holm family284. Entropy/semantic memberships and associated values not independently recomputed. T5:66 native records,132 paired comparisons from33 task-seed pairs. Bootstrap intervals are producer-retained, not independently resampled/accepted inference.',
 'T5 raw top1-minus-top2 margin is not probability. Native risk=1-correct/selected; paired coverage-constrained success=selected-and-correct/common fullN. Realizedcoverage=k/N with ceil request; Visual/Full selected membership may differ. Saved all-prefix AURC is not the trapezoid area of ten displayed points. Fixedscore=clip(margin/2,0,1); ECE is descriptive, not evidence of fitted probability calibration.',
 'Keep each task, seed, direction and height separate unless a descriptive cross-row count is explicitly identified. Negative differences and exact zero/small values must not be hidden by rhetoric or rounding.',
 'Preserve the old public-baseline exact-vs-vectorized distinction, retrospective fusion selection, conditional intervals and timing-proxy scope; do not mix those results with semantic-model evidence.',
 'Local working revision only. No claim finalOverleaf/submission, finishedT6/LOHO/external training/remaining figures or current byte verification of old checkpoint/cache/images. Original inherited provenance limitations stay documented.'
]
report={'schema':'independent-manuscript-content-review-input-checklist.v1','utc':datetime.now(timezone.utc).isoformat(),'scope':'Content and adopted-small-table consistency only; no manuscript edits, producer execution, science/NPZ/weights or old suites.','sources':{k:desc(O/v) for k,v in sources.items()},'checks':checks,'skill_scope':'anti-defensive-writing applies only concise narrative/claim-evidence matching. Explicit user requirements to preserve negative results override the skill advice to omit weaknesses or say only favorable results.','awaiting_producer_freeze':True}
with (R/'INPUT_CHECKLIST.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
for name in ['old_main','old_supplement','old_empty_result_module']:
 with (R/(name+'.tex.txt')).open('xb') as f:f.write((O/sources[name]).read_bytes())
print(json.dumps({'checklist':desc(R/'INPUT_CHECKLIST.json'),'bound_sources':len(sources)},ensure_ascii=True))
