"""One finite stdlib text/byte comparison. Never import or execute the derivation source."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import re

BASE = Path("C:/OneDrive/文档/LGM-GAME/outputs/paper_evidence_rebuild_20260914")
NEW = BASE / "manuscript_ieee_reference_display_20260930_2145/manuscript"
OLD = BASE / "manuscript_camp_dac_context_20260930_1948/manuscript"
META = BASE / "execution/manuscript_ieee_reference_display_20260930_2145"
OUT = BASE / "execution/manuscript_ieee_author_display_delta_review_20260930_2150"
paths = {"derive": META/"derive_author_display.py", "revision": META/"AUTHOR_DISPLAY_REVISION.json",
         "patch": META/"main.tex.patch", "control": NEW/"ieee_controls.bib",
         "new_main": NEW/"main.tex", "new_refs": NEW/"refs.bib", "new_bbl": NEW/"main.bbl", "new_aux": NEW/"main.aux",
         "old_main": OLD/"main.tex", "old_refs": OLD/"refs.bib", "old_bbl": OLD/"main.bbl", "old_aux": OLD/"main.aux"}
raw = {}
bindings = []
for name, path in paths.items():
    data = path.read_bytes()
    if len(data) > 131072:
        raise ValueError("Bounded text scope exceeded")
    raw[name] = data
    bindings.append({"name": name, "path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
text = {name: data.decode("utf-8-sig") for name, data in raw.items()}
ast.parse(text["derive"], filename=str(paths["derive"]))
revision = json.loads(text["revision"])
checks = []
def check(name, okay):
    checks.append({"name": name, "candidate_relation_satisfied": bool(okay)})
control_id = "IEEEAuthorDisplayControl"
insert = b"\\bstctlcite{IEEEAuthorDisplayControl}\n"
expected_main = raw["old_main"].replace(b"\\begin{document}\n", b"\\begin{document}\n"+insert, 1).replace(b"\\bibliography{refs}", b"\\bibliography{ieee_controls,refs}", 1)
check("main_has_only_the_two_exact_author_display_changes", expected_main == raw["new_main"] and raw["old_main"].count(b"\\begin{document}\n")==1 and raw["old_main"].count(b"\\bibliography{refs}")==1)
check("parent_FloatBarrier_clearpage_retained", b"\\FloatBarrier\n\\clearpage\n" in raw["new_main"])
check("complete_main_patch_matches_actual_text_difference", "".join(difflib.unified_diff(text["old_main"].splitlines(keepends=True), text["new_main"].splitlines(keepends=True), fromfile="adopted-parent/main.tex", tofile="new/main.tex")).encode() == raw["patch"])
check("refs_full_bytes_metadata_unchanged", raw["old_refs"] == raw["new_refs"])
expected_control = "@IEEEtranBSTCTL{IEEEAuthorDisplayControl,\n  CTLuse_forced_etal = {yes},\n  CTLmax_names_forced_etal = {6},\n  CTLnames_show_etal = {1}\n}\n"
check("only_explicit_yes_6_1_control_record", text["control"] == expected_control)
check("new_source_descriptors_match_saved_revision", all(len(raw[name])==revision[field]["bytes"] and hashlib.sha256(raw[name]).hexdigest()==revision[field]["sha256"] for name,field in [("derive","source"),("new_main","changed_main"),("patch","complete_delta"),("control","new_control"),("old_main","old_main")]))
def braced(source, start):
    depth = 0
    escaped = False
    for i in range(start, len(source)):
        char = source[i]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start+1:i], i+1
    raise ValueError("Unclosed braced local Bib field")
def bib_records(source):
    records = {}
    for match in re.finditer(r"(?m)^@\w+\s*\{\s*([^,\s]+)\s*,", source):
        start = source.index("{", match.start())
        body, stop = braced(source, start)
        key = match.group(1)
        if key in records:
            raise ValueError("Duplicate local Bib key")
        fields = {}
        for field in ("author","editor"):
            field_match = re.search(r"(?m)^\s*"+field+r"\s*=\s*\{", source[match.end():stop])
            if field_match:
                opening = match.end()+field_match.end()-1
                value, end = braced(source, opening)
                fields[field] = value
        records[key] = fields
    return records
def name_count(value):
    if not value:
        return 0
    depth = 0
    escaped = False
    count = 1
    for i, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif depth == 0 and value[i:i+5] == " and ":
            count += 1
    return count
records = bib_records(text["new_refs"])
def bbl_entries(source):
    markers = list(re.finditer(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", source))
    blocks = []
    for i, match in enumerate(markers):
        stop = markers[i+1].start() if i+1<len(markers) else source.index("\\end{thebibliography}", match.end())
        blocks.append((match.group(1), source[match.end():stop]))
    return source[:markers[0].start()], blocks
old_header, old_blocks = bbl_entries(text["old_bbl"])
new_header, new_blocks = bbl_entries(text["new_bbl"])
old_keys = [k for k,b in old_blocks]
new_keys = [k for k,b in new_blocks]
check("44_visible_keys_same_unique_order", len(old_keys)==len(new_keys)==len(set(new_keys))==44 and old_keys==new_keys)
check("control_record_not_a_visible_bibitem", control_id not in new_keys)
check("BBL_preamble_unchanged", old_header==new_header)
normalize = lambda value: " ".join(value.split())
details = []
quote_prefix = chr(96)*2
for (key, old_block),(new_key,new_block) in zip(old_blocks,new_blocks):
    if new_key != key or quote_prefix not in old_block or quote_prefix not in new_block:
        raise ValueError("Unsupported target BBL structure")
    old_prefix, old_suffix = old_block.split(quote_prefix,1)
    new_prefix, new_suffix = new_block.split(quote_prefix,1)
    authors = name_count(records[key].get("author",""))
    editors = name_count(records[key].get("editor",""))
    old_prefix = normalize(old_prefix)
    new_prefix = normalize(new_prefix)
    macro = "\\BIBentryALTinterwordspacing "
    prefix_prologue = macro if old_prefix.startswith(macro) else ""
    author_text = old_prefix[len(prefix_prologue):]
    first_name = author_text.split(",",1)[0]
    expected_prefix = prefix_prologue+first_name+" \\emph{et~al.},"
    forced = authors > 6
    prefix_okay = new_prefix == expected_prefix if forced else new_prefix == old_prefix
    suffix_okay = normalize(old_suffix)==normalize(new_suffix)
    unchanged_block_okay = old_block == new_block if not forced else True
    details.append({"key":key, "author_count":authors, "editor_count":editors, "forced_global_author_truncation_expected":forced,
        "old_display_prefix":old_prefix, "new_display_prefix":new_prefix,
        "prefix_relation_satisfied":prefix_okay, "suffix_equal_after_whitespace_normalization":suffix_okay,
        "unaffected_BBL_block_exact_bytes_equal":unchanged_block_okay if not forced else None})
check("all_44_BBL_suffixes_unchanged_except_line_wrapping", all(d["suffix_equal_after_whitespace_normalization"] for d in details))
check("all_display_prefixes_follow_candidate_global_6_1_rule", all(d["prefix_relation_satisfied"] for d in details))
check("all_unaffected_BBL_blocks_exactly_unchanged", all(d["unaffected_BBL_block_exact_bytes_equal"] is not False for d in details))
def citations(source):
    return re.findall(r"\\citation\{([^}]+)\}",source)
def labels(source):
    return re.findall(r"\\bibcite\{([^}]+)\}\{([^}]+)\}",source)
check("AUX_44_labels_numbers_order_preserved", labels(text["old_aux"])==labels(text["new_aux"])==list(zip(new_keys,[str(i) for i in range(1,45)])))
new_cites = citations(text["new_aux"])
check("AUX_only_extra_control_citation_first", new_cites.count(control_id)==1 and new_cites[0]==control_id and [c for c in new_cites if c!=control_id]==citations(text["old_aux"]))
check("AUX_control_has_no_visible_label", not any(k==control_id for k,v in labels(text["new_aux"])))
check("AUX_control_library_explicit", "\\bibdata{ieee_controls,refs}" in text["new_aux"])
result = {"schema":"finite-IEEE-author-display-candidate-consistency-check.v1",
    "scope":"Candidate byte/text/BBL/AUX relations only; no IEEE policy applicability, complete bibliography or scientific acceptance.",
    "input_files":len(bindings),"max_input_bytes":131072,"bindings":bindings,"AST_parses":1,
    "candidate_deriver_imports_or_executions":0,"checker_invocations":1,"aggregate_relation_checks":len(checks),"checks":checks,
    "candidate_relations_all_satisfied":all(c["candidate_relation_satisfied"] for c in checks),
    "refs_library_entry_count":len(records),"visible_BBL_entries":len(new_keys),"per_visible_entry_comparisons":len(details),
    "globally_truncated_author_keys":[d["key"] for d in details if d["forced_global_author_truncation_expected"]],
    "unaffected_visible_entries":sum(not d["forced_global_author_truncation_expected"] for d in details),
    "selected_entries_with_editors":[d["key"] for d in details if d["editor_count"]],
    "details":details,"official_rule_scope_or_working_draft_adopted":False,
    "policy_boundary":"Parent reports non-IEEE names-provided exceptions unresolved; global truncation affects MobileGeo, CLIP and MixedPrecision. Internal consistency is not format-policy acceptance.",
    "root_compile_or_visual_claimed_as_own":False,"scientific_execution_or_adoption":False}
(OUT/"CHECK_RESULT.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(0 if result["candidate_relations_all_satisfied"] else 1)

