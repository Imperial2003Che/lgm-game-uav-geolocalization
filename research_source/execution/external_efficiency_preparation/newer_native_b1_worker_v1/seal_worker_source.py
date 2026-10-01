"""Read small source/control files only, preserve exact call blocks, seal source."""
import ast, difflib, hashlib, json
from pathlib import Path
W=Path(__file__).resolve().parent
EX=W.parents[1]
def desc(p):
    raw=p.read_bytes()
    return {"path":str(p.resolve()),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
def write_new(p,v):
    with p.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")
source=W/"reference_worker.py"
old=W/"PRE_ROOT_REVIEW_reference_worker.py.txt"
before=old.read_text(encoding="utf-8")
after=source.read_text(encoding="utf-8")
with (W/"ROOT_REVIEW_REVISION.patch").open("x",encoding="utf-8",newline="\n") as f:
    f.write("".join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=old.name,tofile=source.name)))
with (W/"FULL_NEW_SOURCE.patch").open("x",encoding="utf-8",newline="\n") as f:
    f.write("".join(difflib.unified_diff([],after.splitlines(True),fromfile="/dev/null",tofile=source.name)))
blocks=[];old_sources=[];prepared_metadata=[]
for method,directory,loader,prepared in (
 ("CAMP","camp_independent_evaluation_v3","camp_independent_model.py","preparations/frozen_three_seed_final_v3/manifest.json"),
 ("DAC","dac_independent_evaluation_v2","dac_independent_model.py","preparations/fixed_three_seed/manifest.json"),
):
    root=EX/directory
    for filename,names in (("run_evaluation.py",("read_prepared","encode_seed")),(loader,("load_complete_final_model",))):
        path=root/filename;raw=path.read_bytes();text=raw.decode("utf-8-sig");lines=text.splitlines(True)
        old_sources.append(desc(path));tree=ast.parse(text)
        for name in names:
            node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
            snippet="".join(lines[node.lineno-1:node.end_lineno])
            blocks.append({"method":method,"source":desc(path),"function":name,"start_line":node.lineno,"end_line":node.end_lineno,
                           "exact_source_block":snippet,"block_utf8_sha256":hashlib.sha256(snippet.encode()).hexdigest()})
    path=root/prepared;value=json.loads(path.read_text(encoding="utf-8"))
    prepared_metadata.append({"method":method,"prepared":desc(path),"runtime_prefix":value["runtime"]["prefix"],"python":value["python"],
                              "read_for_metadata_only":True,"no_bind_completed_or_read_prepared_called":True})
write_new(W/"ORIGINAL_CALL_BLOCKS.json",{"schema":"b1-original-source-correspondence.v1","blocks":blocks,
                                     "runtime_prefix_metadata":prepared_metadata,"original_modules_imported":False})
tree=ast.parse(after)
positions={n.name:{"start_line":n.lineno,"end_line":n.end_lineno} for n in tree.body if isinstance(n,ast.FunctionDef)}
write_new(W/"IMPLEMENTATION_MAP.json",{
 "schema":"new-b1-worker-interface-map.v1","source":desc(source),"functions":positions,
 "implemented_dormant_body":[
  "Exact source pins, original CompletedInputs binder and byte-matched rebuilt request",
  "Original seal verification then exact adopted batch16-to1 derivation envelope",
  "Actual native runtime/environment and unmodified original encode_seed invocation",
  "Original native-root four artifacts, DAC snapshot scope and explicit unchanged",
  "Consistency-only candidate, closed control output and return intent",
  "Failure phase and preserved partial native bytes without closed-data claims"],
 "closed_interfaces":["run_reference","admit_reference","_execute_original_reference","_load_sources_after_admission","_import_pinned"],
 "missing_controller":["actual prior exits","fresh process identities and handles","current plan/release/resources","shared GPU byte lock",
                       "launcher/interpreter parent acknowledgement","both actual exits then closed stream evidence"],
 "old_public_gates_unchanged":True,"old_source_not_modified":True,"scientific_execution":False,"full_t6_complete":False,
 "duplicate_implementation_search":"Read-only rg of execution Python sources found only existing B1 contract rejection functions and ranking's unreleased primitive before this module; no later actual reference worker.",
})
paths=[p for p in W.iterdir() if p.is_file() and p.name!="SOURCE_MANIFEST.json"]
write_new(W/"SOURCE_MANIFEST.json",{
 "schema":"newer-native-b1-worker-source.v1","status":"source_prepared_execution_closed",
 "files":[desc(p) for p in sorted(paths)],
 "original_source_references":old_sources,
 "prior_B1_root_adoption":desc(W.parent/"newer_native_b1_contract_v1"/"ROOT_SOURCE_ADOPTION.json"),
 "current_source":desc(source),
 "original_sources_read_not_imported":True,"scientific_execution":False,"execution_admission":False,
 "prior_29_checks_repeated":False,"full_t6_complete":False,"manuscript_result":False,
})
print(json.dumps({"source":desc(source),"manifest":desc(W/"SOURCE_MANIFEST.json"),
                  "map":desc(W/"IMPLEMENTATION_MAP.json"),"blocks":desc(W/"ORIGINAL_CALL_BLOCKS.json")},ensure_ascii=True))
