"""Create a separate one-cell literature transcription correction candidate only."""
from pathlib import Path
import difflib
import hashlib
import json

BASE = Path("C:/OneDrive/文档/LGM-GAME/outputs/paper_evidence_rebuild_20260914/execution")
OLD = BASE / "citation_camp_dac_review_20260930_0509" / "AUTHOR_REPORTED_ROWS.csv"
OUT = BASE / "camp_dac_reported_values_review_20260930_2032"
NEW = OUT / "AUTHOR_REPORTED_ROWS_CORRECTED_CANDIDATE.csv"
old_bytes = OLD.read_bytes()
needle = b"DAC,published_author_report_only,University-to-SUES transfer,drone_to_satellite,200,86.45,89.90,IV,9,"
replacement = b"DAC,published_author_report_only,University-to-SUES transfer,drone_to_satellite,200,86.45,89.00,IV,9,"
if old_bytes.count(needle) != 1:
    raise ValueError("Exact one confirmed saved row required")
new_bytes = old_bytes.replace(needle, replacement, 1)
with NEW.open("xb") as handle:
    handle.write(new_bytes)
patch = "".join(difflib.unified_diff(old_bytes.decode("utf-8").splitlines(keepends=True), new_bytes.decode("utf-8").splitlines(keepends=True), fromfile="saved/AUTHOR_REPORTED_ROWS.csv", tofile="candidate/AUTHOR_REPORTED_ROWS_CORRECTED_CANDIDATE.csv"))
with (OUT / "CORRECTION_CANDIDATE.patch").open("x", encoding="utf-8", newline="") as handle:
    handle.write(patch)
changes = [{"zero_based_byte_offset": i, "before_byte_decimal": a, "after_byte_decimal": b, "before_character": chr(a), "after_character": chr(b)} for i, (a, b) in enumerate(zip(old_bytes, new_bytes)) if a != b]
result = {"schema": "camp-dac-confirmed-one-cell-transcription-correction-candidate.v1",
    "source": {"path": str(OLD), "bytes": len(old_bytes), "sha256": hashlib.sha256(old_bytes).hexdigest()},
    "candidate": {"path": str(NEW), "bytes": len(new_bytes), "sha256": hashlib.sha256(new_bytes).hexdigest()},
    "length_change_bytes": len(new_bytes) - len(old_bytes), "changed_byte_count": len(changes), "exact_byte_changes": changes,
    "saved_CSV_line_one_based": 31, "saved_CSV_data_row_one_based": 30,
    "method": "DAC", "scope": "University-to-SUES transfer", "direction": "Drone→Satellite",
    "height_m": 200, "column": "AP", "source_PDF_page": 9, "source_printed_page": "13279", "source_table": "IV", "source_row": "DAC (Ours)",
    "before_display": "89.90", "actual_PDF_display_and_candidate": "89.00",
    "basis": "Independent AI visual reading of newly rendered actual original PDF page, not model execution.",
    "original_CSV_modified": False, "old_report_or_manuscript_modified": False, "scientific_results_modified": False,
    "not_project_checkpoint_reevaluation_or_training": True, "project_result_flags_preserved": True}
with (OUT / "EXACT_CORRECTION_BYTE_DELTA.json").open("x", encoding="utf-8") as handle:
    handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(result, ensure_ascii=False))

