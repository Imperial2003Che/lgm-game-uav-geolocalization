"""Read-only adopted small-table counts and manuscript fragment semantic review."""
from pathlib import Path
import json, hashlib, math, csv
W=Path(__file__).resolve().parent
EX=W.parents[1]
ADOPT=EX/"pipeline_post_robustness_audit_20260929_1448"
Q=ADOPT/"a1"/"query"
P=EX/"manuscript_revision_scope_20260930_0202"
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def desc(p):
    b=p.read_bytes()
    return {"path":str(p),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
t4=load(Q/"transactions_t4_strata.json")
t5=load(Q/"transactions_t5_selective_calibration.json")
root=load(ADOPT/"ROOT_POST_ROBUSTNESS_ADOPTION.json")
margin=[r for r in t4["rows"] if r["factor"]=="visual_margin_quartile"]
low=[r for r in margin if not r["summary"]["performance_claim_eligible"]]
eligible=[r for r in margin if r["summary"]["performance_claim_eligible"]]
bins=[b for r in t5["native_rows"] for b in r["calibration"]["reliability_bins"]]
points=[p for r in t5["native_rows"] for p in r["risk_coverage"]["rows"]]
checks={
 "T4_margin_rows_132":len(margin)==132,
 "T4_eligible_margin_84":len(eligible)==84,
 "T4_ineligible_margin_48":len(low)==48,
 "all_ineligible_margin_SUES_satellite_to_UAV_20":all(r["dataset"]=="sues200" and "_satellite_to_uav_" in r["task"] and r["summary"]["queries"]==20 for r in low),
 "T4_total_eligible_Holm_284":sum(r["summary"]["performance_claim_eligible"] for r in t4["rows"])==284,
 "T5_native_66_paired_132":len(t5["native_rows"])==66 and len(t5["paired_comparisons"])==132,
 "native_display_660":len(points)==660,
 "native_display_coverages":all([p["requested_coverage"] for p in r["risk_coverage"]["rows"]]==[i/10 for i in range(1,11)] for r in t5["native_rows"]),
 "native_display_ceil_selected_counts":all(p["selected_queries"]==math.ceil(p["requested_coverage"]*r["risk_coverage"]["queries"]) for r in t5["native_rows"] for p in r["risk_coverage"]["rows"]),
 "paired_coverage_four":{r["requested_coverage"] for r in t5["paired_comparisons"]}=={.5,.75,.9,1.0},
 "paired_common_N_success_definition":all(r["coverage_constrained_success"]["definition"]=="selected AND top1-correct over the common full query set" for r in t5["paired_comparisons"]),
 "bins_990_140_occupied_850_empty":len(bins)==990 and sum(b["count"]>0 for b in bins)==140 and sum(b["count"]==0 for b in bins)==850,
 "empty_bins_null_score_accuracy":all(b["accuracy"] is None and b["mean_fixed_normalized_margin_confidence"] is None for b in bins if b["count"]==0),
 "root_CI_not_recomputed":root["query"]["bootstrap_CI_recomputed"] is False,
 "root_nonmargin_membership_not_recomputed":root["query"]["T4_other_strata_membership_and_values_recomputed"] is False,
 "root_T5_native_and_paired_recount":root["query"]["T5_native_query_recomputed"]==66 and root["query"]["T5_paired_query_recomputed"]==132,
}
fragments=[P/"semantic_results.tex",P/"supplementary_evidence.tex"]
assert all(p.is_file() for p in fragments)
report={
 "schema":"manuscript-t4-t5-fragment-review.v1",
 "scope":"Only T4/T5 query sentences and numbers in the two exact fragments. Main/transfer/robustness/official-33 inference family and final assembled manuscript are outside this narrow review.",
 "passed":all(checks.values()),
 "checks":checks,
 "manualSemanticReview":{
   "T4_visual_anchored_shared_masks_and_noncausal_scope":"PASS",
   "T4_quartile_boundary_and_unequal_size_interpretation":"PASS",
   "T5_independent_variant_selections":"PASS",
   "T5_selected_k_vs_common_N_denominators":"PASS",
   "selected_overlap_is_membership_not_shared_correctness":"PASS",
   "all_prefix_AURC_not_ten_point_integral":"PASS",
   "fixed_margin_score_not_posterior_or_fitted_calibration":"PASS",
   "empty_bin_undefined_values_not_zero":"PASS",
   "bootstrap_and_nonmargin_audit_limits_retained":"PASS",
   "no_unwarranted_semantic_significance_claim":"PASS",
 },
 "findings":[],
 "bindings":[desc(p) for p in [ADOPT/"ROOT_POST_ROBUSTNESS_ADOPTION.json",Q/"transactions_query_analysis_config.json",Q/"transactions_t4_strata.csv",Q/"transactions_t4_strata.json",Q/"transactions_t5_selective_comparisons.csv",Q/"transactions_t5_selective_calibration.json",*fragments,Path(__file__)]],
 "notDone":["No NPZ/model/cache/image read","No bootstrap/statistics/model rerun","No producer execution","No manuscript edits","No final assembled manuscript checked"],
 "handoff":"Lead independent reviewer must confirm these exact fragment contents are retained in the final assembled manuscript.",
}
out=W/"QUERY_FRAGMENT_REVIEW.json"
with out.open("x",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2);f.write("\n")
print(json.dumps({"report":desc(out),"passed":report["passed"],"checks":len(checks),"findings":report["findings"]},ensure_ascii=True))
