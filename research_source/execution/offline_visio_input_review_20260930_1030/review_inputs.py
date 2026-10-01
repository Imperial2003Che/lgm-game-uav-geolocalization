"""Independent narrow input authority review; never imports/runs any builder."""
import csv
import hashlib
import io
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

OUT = Path(r"C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914")
HERE = OUT / "execution" / "offline_visio_input_review_20260930_1030"
PRODUCER = OUT / "offline_native_visio_20260930_1030"
MANIFEST = PRODUCER / "INPUT_MANIFEST_v2.json"
MANIFEST_SHA = "506aa8f9bee244714e61ec610a21345ecbdd89b91cf816d57db1c9c490b10bdd"
MAX = 512 * 1024
FAMILIES = [
    ("T3", "transfer_native_figures_20260929_1750", "output", "ROOT_TRANSFER_NATIVE_ADOPTION.json", "1ceb695ac22b09bc79c296913aeda4ea92505506afb19b996664bdf98121ca13", 2),
    ("robustness", "robustness_native_figures_20260929_1650", "output", "ROOT_NATIVE_22_ADOPTION.json", "625fc0b4b236e28476e64f3c7a38f9932ab15509a68b0e51671a0b3f03a37b33", 22),
    ("T4", "query_t4_margin_native_figures_20260929_1952", "output", "ROOT_T4_MARGIN_NATIVE_ADOPTION.json", "9ed6e8ba66e3b932a70cab25c4b992cefc0f59b2296aa74b5aabd5e826de01ce", 11),
    ("risk", "query_t5_native_figures_20260929_1856", "output_v2", "ROOT_T5_NATIVE_ADOPTION.json", "ba08d50737b82744ea1c2ce5feb5eccb82555d441384b89700667012ec80ba65", 11),
    ("reliability", "query_t5_reliability_native_figures_20260929_2054", "output", "ROOT_T5_RELIABILITY_NATIVE_ADOPTION.json", "5211b54107c520b301dda3dda565cae09fb78c2ea5846ee3b7159c09ea840b0a", 11),
    ("paired", "query_t5_paired_native_figures_20260929_2157", "output", "ROOT_T5_PAIRED_NATIVE_ADOPTION.json", "32c62c2c7c5251446ac7501fbcbe1dfe23728e9381f9a732bce95792f9b577b3", 11),
]
DESCRIPTION = {
    "T3": "Two training-to-test dataset directions, 11 target retrieval tasks/four SUES heights; 22 Visual/Full groups and 66 metric summaries. Equally weighted seed1/2/3 means and sample SD denominator2. R1 and official trapezoidal mAP times100 are percentages; MRR times100 is scaled MRR. Separate zero-start axes and complete SD/zeroSD/low street values. Full meanR1 is lower in all11 tasks, mAP/MRR only street-to-satellite SUES-to-University slight positive. No task/height/direction pooling or CI/significance.",
    "robustness": "22 distinct task-metric figures, 1320 saved rows; seed1 only, six corruption families and five severities. Retention=100*corrupt/each own clean, not absolute accuracy or pp drop. Preserve >100, nonmonotonic and low clean baselines. Clean full gallery; Full cached-clean versus online-corrupt mixes evidence path and pixel effects. Clean64 diagnostic has no equivalence threshold/bitwise parity/negligible ranking guarantee. Fixed SUES120train/80test, four heights and query/gallery member protocols inherited. No SD/CI/pool/significance or hiding primary/transfer Full negatives.",
    "T4": "132 Visual-margin quartile strata/792 saved metric values/99 metric-seed panels; other330 entropy/semantic strata outside this figure scope. Full aligns to Visual and shares Visual-defined mask, ordered categorical quartiles with linear25/50/75 cutpoints and ties lower.84 N>=100 strata only pass count gate;48 N20 strata flagged descriptive-only. Percent R1/mAP versus scaledMRR, axes0-100. Visual-anchored condition is not causal/mechanistic/calibrated posterior. No pooling/SD/CI/bootstrap/p or new stats.",
    "risk": "66 separate native records/660 saved points/33 seed panels, clean official queries. x=100*saved realized k/N with ceil(requested*N), y=100*(1-selected-subsetR1). Each variant chooses its own margin subset; same coverage is not same membership. Ten requested coverages0.1..1, no fakezero origin. Lines are guides, not all-prefix curve/integral.66 saved all-prefix AURC fractions rounded4dp, not recomputed.132 paired including75% and calibration outside plotted scope. Margin not posterior; no pool/SD/CI/bootstrap/p/significance.",
    "reliability": "990 saved bins across66 native records/33 seed panels,140 occupied and850 empty, clean official queries. Fixed clip(margin/2,0,1), min(int(15*score),14); not posterior/fitted calibration. Plot occupied stored mean-score and empiricalR1 fractions0-1 with unjittered/unconnected markers; y=x numerical equality only. All15 populations including0; empty mean/accuracy null, no fakezero point.66 stored ECE fractions4dp, notpercent/recomputed. Lower ECE does not imply higher accuracy/better probability calibration; variants bin their own members. No pooling/SD/CI/bootstrap/p/significance; primary/transfer negatives retained.",
    "paired": "132 saved paired rows/264 points/33 seed panels. x=100*saved realized k/N; y=100*(selectedANDcorrect/commonfullN), not selected-k accuracy. Four saved50/75/90/100 requests;75% actualpaired row, no interpolation/fakeorigin/jitter/AUC. Equal k can differmembers; overlap=selected intersection, not jointlycorrect. Full100% endpoint retained. Morecoverage can mechanicallyraise fullNsuccess, notimprovedranking. Original132Holm concerns fullNutility, not direct selectiveaccuracy between different subsets, not plotted/newlyverified. Margin notposterior; no pool/SD/CI/bootstrap/p/significance.",
}
REQUIRED_NOTES = {
    "T3": ["denominator n−1=2", "not a percentage accuracy", "Full mean R@1 below Visual in all 11 tasks", "No pooling", "historical evidence-chain limitations"],
    "robustness": ["seed 1", "that variant's own clean metric", "cached", "online", "no numerical equivalence threshold", "does not imply greater absolute corrupted accuracy", "historical evidence-chain limitations"],
    "T4": ["same Visual-defined membership mask", "Exactly48", "other84", "count gate only", "scaled MRR", "not a calibrated posterior", "Only132", "other330", "historical evidence-chain gaps"],
    "risk": ["realized coverage k/N", "selective risk=1−selected-query R@1", "not a calibrated posterior", "not a trapezoidal integral", "each select their own", "132 paired", "historical evidence-chain gaps"],
    "reliability": ["clip((cosine Top-1 minus Top-2 margin)/2,0,1)", "not a posterior probability", "Empty bins retain null", "not multiplied by100", "lower fixed-score ECE does not imply", "850 empty", "historical metadata-chain gaps"],
    "paired": ["common full query N", "same k is not proof", "not the number jointly correct", "mechanically increase", "No selective-accuracy difference", "all132", "historical metadata-chain gaps"],
}
checks = []
bindings = {}

def check(name, condition):
    checks.append({"name": name, "passed": bool(condition)})
    if not condition:
        raise RuntimeError(name)

def key(path):
    return str(Path(path).resolve()).casefold()

def read(path, expected=None):
    path = Path(path).resolve(strict=True)
    limit = 2 * 1024 * 1024 if path == MANIFEST else MAX
    check("bounded-approved-input:" + path.name, path.is_relative_to(OUT) and path.stat().st_size <= limit
          and path.suffix.lower() in {".json", ".csv", ".md", ".svg", ".py"})
    before = path.stat()
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    after = path.stat()
    check("stable-input:" + path.name, (before.st_size, before.st_mtime_ns, before.st_ino) ==
          (after.st_size, after.st_mtime_ns, after.st_ino) and len(raw) == before.st_size)
    item = {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    if expected is not None:
        check("accepted-root-byte-edge:" + path.name, key(item["path"]) == key(expected["path"])
              and item["bytes"] == expected["bytes"] and item["sha256"] == expected["sha256"])
    check("same-input-repeat-consistency:" + path.name, key(path) not in bindings or bindings[key(path)] == item)
    bindings[key(path)] = item
    return raw, item

def write(name, raw):
    if len(raw) > 1024 * 1024:
        raise RuntimeError("Output exceeds the pre-CreateNew serialization bound: " + name)
    path = HERE / name
    with path.open("xb") as handle:
        handle.write(raw); handle.flush(); os.fsync(handle.fileno())
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")

def csv_rows(raw):
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))

def approved_read(path, table):
    check("path-listed-in-family-root:" + Path(path).name, key(path) in table)
    return read(path, table[key(path)])

def main():
    family_reports = []
    figure_map = []
    root_descriptor_tables = {}
    for family, directory, subdir, root_name, root_sha, expected_count in FAMILIES:
        base = OUT / directory
        output = base / subdir
        root_raw, root_item = read(base / root_name)
        check("exact-adopted-graphical-root:" + family, root_item["sha256"] == root_sha)
        root = json.loads(root_raw)
        check("family-root-accepted:" + family, root.get("accepted", root.get("accepted_with_stated_limits")) is True)
        table = {key(item["path"]): item for item in root["bindings"]}
        root_descriptor_tables[key(root_item["path"])] = table
        index_path = output / ("FIGURE_INDEX.json" if family in {"T3", "robustness", "risk"} else "FIGURE_INDEX.csv")
        index_raw, index_item = approved_read(index_path, table)
        index = json.loads(index_raw) if index_path.suffix == ".json" else csv_rows(index_raw)
        figures = index["figures"] if isinstance(index, dict) else index
        check("exact-index-coverage:" + family, len(figures) == expected_count)
        captions_raw, captions_item = approved_read(output / "CAPTIONS.md", table)
        captions = captions_raw.decode("utf-8-sig")
        sections = re.split(r"(?m)^## Figure \d+: ", captions)[1:]
        check("full-caption-per-index-figure:" + family, len(sections) == expected_count)
        _, readme_item = approved_read(output / "README.md", table)
        extra_data = []
        if family == "T3":
            for filename, count in [("THREE_SEED_SUMMARY.csv", 22), ("SEED_RESULTS.csv", 66), ("FULL_MINUS_VISUAL.csv", 11)]:
                raw, item = approved_read(output / "source_data" / filename, table)
                rows = csv_rows(raw)
                check("stored-T3-small-row-count:" + filename, len(rows) == count)
                extra_data.append({"binding": item, "stored_rows": len(rows), "columns": list(rows[0])})
        total_rows = 0
        for offset, figure in enumerate(figures):
            svg_path = output / figure["svg"]
            svg_raw, svg_item = approved_read(svg_path, table)
            svg = ET.fromstring(svg_raw)
            width = float(svg.attrib["width"].removesuffix("mm"))
            height = float(svg.attrib["height"].removesuffix("mm"))
            box = [float(v) for v in svg.attrib["viewBox"].split()]
            texts = [n for n in svg.iter() if n.tag.rsplit("}", 1)[-1] == "text"]
            check("fixed-fullsize-width:" + svg_path.name, abs(width - 181.9) <= 1e-8)
            check("positive-page-height:" + svg_path.name, height > 0 and box[2] > 0 and box[3] > 0)
            check("actual-texts-exist:" + svg_path.name, bool(texts))
            physical_fonts = [float(n.attrib["font-size"]) * width * 72 / 25.4 / box[2] for n in texts]
            check("all-Arial-physical-at-least8pt:" + svg_path.name,
                  all(n.attrib.get("font-family") == "Arial" for n in texts) and min(physical_fonts) >= 8 - 1e-8)
            check("no-raster-foreign-object-input:" + svg_path.name,
                  all(n.tag.rsplit("}", 1)[-1] not in {"image", "foreignObject"} for n in svg.iter()))
            csv_bindings = []
            stored_rows = None
            if family == "T3":
                csv_bindings = [v["binding"] for v in extra_data]
            else:
                csv_path = output / figure.get("source_csv", figure.get("sourceCSV"))
                raw, item = approved_read(csv_path, table)
                rows = csv_rows(raw)
                stored_rows = len(rows)
                expected_rows = {"robustness": 60, "T4": 12, "risk": 60, "reliability": 90, "paired": 12}[family]
                check("stored-CSV-record-count:" + csv_path.name, stored_rows == expected_rows)
                total_rows += stored_rows
                csv_bindings = [item]
            full_notes_section = "## Figure " + str(offset + 1) + ": " + sections[offset]
            check("notes-body-not-empty:" + svg_path.name, len(full_notes_section.strip()) > 1000)
            check("complete-common-unit-and-limit-clauses:" + svg_path.name,
                  all(marker in full_notes_section for marker in REQUIRED_NOTES[family]))
            figure_map.append({"family": family, "ordinal_in_family": offset + 1,
                "id": figure.get("id", figure.get("task")), "title": figure["title"],
                "svg": svg_item, "accepted_graphical_root": root_item,
                "accepted_index": index_item, "accepted_captions": captions_item,
                "csv_bindings": csv_bindings, "stored_csv_record_count": stored_rows,
                "physical_size_mm": [width, height], "text_count": len(texts),
                "minimum_actual_physical_font_pt": min(physical_fonts),
                "full_accepted_notes_section": full_notes_section,
                "scientific_scope_and_limits": DESCRIPTION[family]})
        family_reports.append({"family": family, "figure_count": expected_count, "root": root_item,
            "index": index_item, "captions": captions_item, "readme": readme_item,
            "stored_per_figure_csv_records": total_rows if family != "T3" else None,
            "T3_small_tables": extra_data, "scientific_description": DESCRIPTION[family],
            "complete_inherited_root_limits": root.get("limits", root.get("limitations"))})
    check("exact-six-family68-SVG-coverage", len(family_reports) == 6 and len(figure_map) == 68)
    check("distinct68-accepted-SVG-paths", len({key(v["svg"]["path"]) for v in figure_map}) == 68)
    manifest_raw, manifest_item = read(MANIFEST)
    check("exact-fixed-producer-manifest", manifest_item["sha256"] == MANIFEST_SHA and manifest_item["bytes"] == 1052344)
    manifest = json.loads(manifest_raw)
    check("manifest-source-only-scope", manifest["schema"] == "offline-native-visio-inputs.v1"
          and manifest["figure_count"] == 68 and manifest["VSDX_files_created"] is False
          and manifest["COM_or_Office_invoked"] is False and manifest["scientific_execution"] is False
          and manifest["visio_open_validated"] is False and manifest["visio_roundtrip_pending"] is True)
    manifest_family_names = {"T3": "transfer", "robustness": "robustness", "T4": "margin",
                             "risk": "risk", "reliability": "reliability", "paired": "paired"}
    expected_family_counts = {manifest_family_names[v["family"]]: v["figure_count"] for v in family_reports}
    check("producer-manifest-exact-six-family-counts", len(manifest["families"]) == 6 and
          {v["name"]: v["count"] for v in manifest["families"]} == expected_family_counts)
    manifest_families = {v["name"]: v for v in manifest["families"]}
    for accepted in family_reports:
        source = manifest_families[manifest_family_names[accepted["family"]]]
        check("manifest-family-root-caption-index:" + accepted["family"],
              source["accepted_root"] == accepted["root"] and source["captions"] == accepted["captions"]
              and accepted["index"] in source["metadata"] and accepted["readme"] in source["metadata"])
        table = root_descriptor_tables[key(accepted["root"]["path"])]
        # Compare other declared source descriptor VALUES against the accepted
        # root only. Their large JSON file contents are deliberately not read.
        check("manifest-extra-source-descriptors-in-accepted-root:" + accepted["family"],
              all(key(v["path"]) in table and table[key(v["path"])] == v for v in source["data"] + source["metadata"]))
    # Producer manifest shape is checked here explicitly after it is fixed;
    # it is not used to discover or choose the accepted family authority above.
    manifest_figures = manifest["figures"]
    check("producer-manifest-exact68", len(manifest_figures) == 68)
    manifest_svgs = [v["svg"] for v in manifest_figures]
    check("producer-manifest-exact-authorized-SVG-set", {key(v["path"]) for v in manifest_svgs} ==
          {key(v["svg"]["path"]) for v in figure_map} and len({key(v["path"]) for v in manifest_svgs}) == 68)
    mapped = {key(v["svg"]["path"]): v for v in figure_map}
    for record in manifest_figures:
        expected = mapped[key(record["svg"]["path"])]
        check("producer-manifest-family-identity:" + Path(record["svg"]["path"]).name,
              record["family"] == manifest_family_names[expected["family"]] and
              key(record["source_directory"]) == key(Path(expected["accepted_index"]["path"]).parent))
        check("producer-manifest-byte-SVG:" + Path(record["svg"]["path"]).name, record["svg"] == expected["svg"])
        check("producer-manifest-root-authority:" + Path(record["svg"]["path"]).name,
              record["root"] == expected["accepted_graphical_root"])
        check("producer-manifest-full-captions-source:" + Path(record["svg"]["path"]).name,
              record["captions"] == expected["accepted_captions"])
        data_table = {key(v["path"]): v for v in record["data"]}
        check("producer-manifest-all-selected-CSV-edges:" + Path(record["svg"]["path"]).name,
              all(key(v["path"]) in data_table and data_table[key(v["path"])] == v for v in expected["csv_bindings"]))
        source_table = {key(v["path"]): v for v in record["source_files"]}
        check("producer-manifest-notes-index-source-file-edges:" + Path(record["svg"]["path"]).name,
              all(key(v["path"]) in source_table and source_table[key(v["path"])] == v
                  for v in [expected["accepted_captions"], expected["accepted_index"]] + expected["csv_bindings"]))
        inventory = record["inventory"]
        check("producer-manifest-physical-font-size:" + Path(record["svg"]["path"]).name,
              abs(inventory["width_mm"] - expected["physical_size_mm"][0]) <= 1e-8
              and abs(inventory["height_mm"] - expected["physical_size_mm"][1]) <= 1e-8
              and inventory["minimum_font_pt"] >= 8 - 1e-8)
    read(Path(__file__))
    input_index = write("INPUT_BINDINGS.json", encoded({"schema": "offline-native-visio-input-review-bindings.v1",
        "inputs": list(bindings.values())}))
    mapping = write("SVG_AUTHORITY_NOTES_MAP.json", encoded({"schema": "accepted68-svg-authority-notes-map.v1", "figures": figure_map}))
    report = {"schema": "offline-native-visio-accepted-input-review.v1",
        "reviewed_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Independent AI read the accepted family root summaries/limits and common caption contracts plus initial per-figure sections; this own stdlib checker binds complete selected caption files/per-figure sections, checks repeated unit/limit clauses and bounded selected file bytes, indices, per-page CSV row counts and SVG XML font/size declarations. No human review, builder import/execution, original scientific recomputation or prior suite rerun.",
        "scope": "68 accepted chart inputs in six families for new CPU-only direct OPC XML VSDX serialization; original two main VSDX and original template ZIP not read by this reviewer.",
        "accepted_input_scope": True, "scientific_revalidation": False, "new_scientific_execution": False,
        "native_visio_application_open_verified": False, "native_visio_repair_free_verified": False,
        "native_visio_render_verified": False, "native_visio_GUI_edit_verified": False,
        "all_final_visio_delivered": False,
        "figure_count": 68, "family_count": 6, "families": family_reports,
        "producer_input_manifest": manifest_item, "mapping": mapping, "input_bindings": input_index,
        "check_count": len(checks), "checks": list(checks), "unique_input_bindings": len(bindings),
        "limits": [
            "This validates exact selected derivative input authority/notes/counts only; root inherited upstream limits remain. Metadata/accepted root does not prove current checkpoint/cache/image bytes, fullranking/all-positive-rank AP or independent bootstrap resampling.",
            "No figure numbers/means/SD/quantiles/selection/reliability/retention ratios were recomputed. CSV record counts and SVG physical font unit conversion are presentation/input consistency checks only.",
            "Producer's other declared source-data JSON/metadata descriptors are compared against accepted root descriptor values only, not reread/current-byte validation. Font TTF image bytes, original template package and producer inventory object counts are not independently reopened or validated by this reviewer.",
            "Full official main10of11 R1/mAP negative and transfer all11meanR1 negative remain; local conditional/retention/ECE/coverage patterns cannot become universal improvement claims.",
            "Direct OPC native XML objects are actual serialization artifacts; opening without repair, Visio rendering/layout and GUI editability remain separate pending application checks, not claimed by this input review.",
            "No COM/app interaction, images, old ZIP, weights, NPZ, caches, scientific modules/GPU, state/release/intent/lock or HANDOFF mutation.",
        ]}
    report_item = write("INPUT_AUTHORITY_REVIEW.json", encoded(report))
    delivery = write("DELIVERY.json", encoded({"schema": "offline-native-visio-input-review-delivery.v1",
        "issued_utc": datetime.now(timezone.utc).isoformat(), "scope": report["scope"],
        "input_scope_accepted": True, "scientific_revalidation": False,
        "application_open_render_GUI_validated": False, "checks": report["check_count"],
        "unique_inputs": len(bindings), "inputs": list(bindings.values()),
        "outputs": [input_index, mapping, report_item]}))
    print(json.dumps({"scope": "68 accepted input authority only", "checks": report["check_count"],
        "inputs": len(bindings), "report": report_item, "delivery": delivery}, ensure_ascii=False))

if __name__ == "__main__":
    main()
