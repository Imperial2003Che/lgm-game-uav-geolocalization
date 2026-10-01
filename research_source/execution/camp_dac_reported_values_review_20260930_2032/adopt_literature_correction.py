"""Adopt newly reviewed literal published values only; no scientific execution."""
from pathlib import Path
import csv, io, json, hashlib, datetime

EX = Path(r"C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution")
BASE = EX / "camp_dac_reported_values_review_20260930_2032"
bindings = {}
def read_bound(path, limit=131072, expected=None):
    path = Path(path)
    size = path.stat().st_size
    assert 0 <= size <= limit, (path, size)
    data = path.read_bytes()
    assert len(data) == size
    descriptor = {"path": str(path), "bytes": size, "sha256": hashlib.sha256(data).hexdigest()}
    if expected is not None:
        assert descriptor == expected, path
    bindings[str(path)] = descriptor
    return data

delivery_raw = read_bound(BASE / "DELIVERY.json")
delivery = json.loads(delivery_raw)
assert delivery["counts"] == {"rows": 36, "display_tokens": 72, "consistent": 71, "real_differences": 1, "unknown": 0}
assert len(delivery["artifacts"]) == 14
for descriptor in delivery["artifacts"]:
    path = Path(descriptor["path"])
    assert path.parent == BASE and path.suffix in (".json", ".csv", ".py", ".md", ".patch")
    read_bound(path, expected=descriptor)
for name in ("ROOT_ACTUAL_VISUAL_REVIEW.json", "ROOT_ACTUAL_TEXT_READS.json", "adopt_literature_correction.py"):
    read_bound(BASE / name)
visual = json.loads((BASE / "ROOT_ACTUAL_VISUAL_REVIEW.json").read_bytes())
assert visual["conclusion"]["target_tables"] == 6 and visual["conclusion"]["published_display_tokens"] == 72
for method in ("camp", "dac"):
    for page in (7, 8, 9):
        read_bound(BASE / (method + "_p" + str(page) + ".png"), limit=2097152)
old_path = EX / "citation_camp_dac_review_20260930_0509" / "AUTHOR_REPORTED_ROWS.csv"
old = read_bound(old_path, expected={"path": str(old_path), "bytes": 6440, "sha256": "8982e329fdd88035a726b9276cdd2cc80523037525e0a243dc4941283e123e0a"})
new_path = BASE / "AUTHOR_REPORTED_ROWS_CORRECTED_CANDIDATE.csv"
new = new_path.read_bytes()
assert len(old) == len(new) == 6440
changes = [(i, a, b) for i, (a, b) in enumerate(zip(old, new)) if a != b]
assert changes == [(5280, 57, 48)]
old_rows = list(csv.DictReader(io.StringIO(old.decode("utf-8-sig"))))
new_rows = list(csv.DictReader(io.StringIO(new.decode("utf-8-sig"))))
assert len(old_rows) == len(new_rows) == 36
assert old_rows[29]["method"] == new_rows[29]["method"] == "DAC"
assert new_rows[29]["scope"] == "University-to-SUES transfer" and new_rows[29]["height_m"] == "200"
assert new_rows[29]["retrieval_direction"] == "drone_to_satellite"
assert old_rows[29]["AP_percent_as_printed"] == "89.90" and new_rows[29]["AP_percent_as_printed"] == "89.00"
assert all(row["project_result"] == "False" and row["project_reproduction_pass"] == "False" for row in new_rows)
comparison = list(csv.DictReader(io.StringIO((BASE / "VALUE_COMPARISON.csv").read_text(encoding="utf-8-sig"))))
assert len(comparison) == 72
assert sum(row["status"] == "consistent" for row in comparison) == 71
assert sum(row["status"] == "real_display_difference" for row in comparison) == 1
report = {
    "schema": "root-published-literal-transcription-correction-adoption.v1",
    "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": "Only six own-method published tables, 36 rows and 72 printed point-value tokens",
    "review_methods": {
        "independent": "AI original-pixel table transcription, finite cached literal comparison; actual one PDF page-reader invocation and one separate candidate writer",
        "root": "AI actually viewed all six original-resolution rendered pages and read old CSV and complete new comparison/literal/method/sources; current script only binds new artifacts and verifies exact one-byte correction and saved metadata counts",
        "no_human_review": True,
        "no_repeat_of_independent_comparison_or_scientific_control_suite": True
    },
    "published_display_review": {"tables": 6, "rows": 36, "tokens": 72, "old_matches": 71, "old_differences": 1, "unknown": 0},
    "correction": delivery["difference"],
    "exact_byte_delta": {"offset_zero_based": 5280, "before": 57, "after": 48, "changed_bytes": 1},
    "literature_only_source_adopted": True,
    "adopted_future_literature_table": bindings[str(new_path)],
    "old_source_retained": bindings[str(old_path)],
    "local_bindings": list(bindings.values()),
    "not_adopted": {
        "scientific_execution_released": False, "B1_admitted": False, "T6_complete": False,
        "author_checkpoint_reproduction": False, "independent_training": False,
        "metric_or_protocol_equivalence": False, "new_scientific_result": False,
        "full_bibliography_or_whole_paper_review": False, "new_manuscript_or_Overleaf_delivery": False
    },
    "limits": [
        "Original published R@1/AP point numbers remain distinct from local author-checkpoint and independent-training results.",
        "Same-domain and controlled University-to-SUES transfer are distinct scopes; no street-view extrapolation or cross-task pooling.",
        "No new mean, SD, CI, significance, AP evaluator parity, gallery membership, loaded pretraining or scientific input validation.",
        "Whole original PDF hashes are historical inherited descriptors; only target pages were read by installed fitz, not whole-file rehashed.",
        "PNG hashes bind new literature page pixels; they are not scientific dataset-image hashing.",
        "Old CSV/report/roots and manuscripts/ZIPs retained. The 72 paper-reported numbers were not inserted into the latest CAMP/DAC context draft.",
        "The root read the complete small comparison/literal/method documents and new sources, but does not claim full semantic reading of the 98464-byte detail report."
    ]
}
raw = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
assert len(raw) < 131072
target = BASE / "ROOT_LITERATURE_CORRECTION_ADOPTION.json"
with target.open("xb") as handle:
    handle.write(raw)
print(json.dumps({"path": str(target), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "new_local_bindings": len(bindings), "one_byte_delta": changes, "scope": report["scope"], "scientific_execution_released": False}, ensure_ascii=False))
