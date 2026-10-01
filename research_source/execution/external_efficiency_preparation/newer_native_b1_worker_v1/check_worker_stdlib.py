"""Bounded NEW worker pure-data/closed-gate checks; never enters old modules."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
path = HERE / "reference_worker.py"
spec = importlib.util.spec_from_file_location("_new_b1_worker_pure_checks", path)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
checks = []
def test(name, fn):
    fn()
    checks.append(name)
def reject(fn, error=RuntimeError):
    try:
        fn()
    except error:
        return
    raise AssertionError("Expected rejection")
def check(value):
    assert value
prepared = {"settings":{"batch_size":16,"amp":True},"method":"SYNTHETIC_NOT_SCIENCE"}
prepared["payload_sha256"] = w.digest(w.canonical(prepared))
derived = copy.deepcopy(prepared)
derived["settings"]["batch_size"] = 1
declared = {
 "json_pointer":"/settings/batch_size","original":16,"derived":1,
 "original_canonical_sha256":w.digest(w.canonical(prepared)),
 "derived_canonical_sha256":w.digest(w.canonical(derived)),
 "original_prepared_file_modified":False,
}
test("original seal valid", lambda:check(w.verify_original_seal(prepared)==prepared["payload_sha256"]))
wrong=copy.deepcopy(prepared);wrong["method"]="changed"
test("original seal mutation rejected",lambda:reject(lambda:w.verify_original_seal(wrong)))
envelope=w.derivation_envelope(prepared,derived,declared)
test("exact derivative preserves historical seal only",lambda:check(
 envelope["derived_prepared"]==derived and envelope["original_seal_not_valid_for_derived"] is True
 and envelope["derived_passed_to_read_prepared_or_verify_seal"] is False))
bad=copy.deepcopy(derived);bad["settings"]["amp"]=False
test("second config difference rejected",lambda:reject(lambda:w.derivation_envelope(prepared,bad,declared)))
bad_bool=copy.deepcopy(derived);bad_bool["settings"]["batch_size"]=True
test("boolean batch size rejected",lambda:reject(lambda:w.derivation_envelope(prepared,bad_bool,declared)))
no_seal=copy.deepcopy(derived);no_seal.pop("payload_sha256")
test("dropping historical seal rejected",lambda:reject(lambda:w.derivation_envelope(prepared,no_seal,declared)))
bad_declared=dict(declared,derived_canonical_sha256="0"*64)
test("different derivation digest rejected",lambda:reject(lambda:w.derivation_envelope(prepared,derived,bad_declared)))
request={"schema":"synthetic_request","method":"CAMP","seed":1,"source_recipe":{},"derivation":declared}
raw=w.canonical(request)+b"\n"
test("canonical request exact bytes accepted",lambda:check(w.require_request_bytes(raw,request)==w.digest(raw)))
test("same JSON different serialization rejected",lambda:reject(lambda:w.require_request_bytes(json.dumps(request,indent=2).encode(),request)))
test("changed request seed rejected",lambda:reject(lambda:w.require_request_bytes(raw,dict(request,seed=2))))
artifacts={name:{"synthetic":True} for name in w.ARTIFACT_NAMES}
candidate=w.candidate_envelope(request,artifacts)
test("candidate is consistency-only envelope",lambda:check(candidate["measurement_admitted"] is False and candidate["independent_execution_proven"] is False))
test("extra output rejected",lambda:reject(lambda:w.candidate_envelope(request,dict(artifacts,extra={}))))
test("duplicate JSON rejected",lambda:reject(lambda:w.parse(b'{"x":1,"x":2}')))
test("nonfinite JSON rejected",lambda:reject(lambda:w.parse(b'{"x":NaN}')))
with tempfile.TemporaryDirectory(prefix="pure_fixture_",dir=HERE) as temporary:
    p=Path(temporary)/"control.json"
    record=w.write_new_json(p,{"synthetic":True})
    test("closed control exact descriptor accepted",lambda:check(w.read_control(record)[1]=={"synthetic":True}))
    test("exclusive output prevents overwrite",lambda:reject(lambda:w.write_new_json(p,{"synthetic":False}),FileExistsError))
    p.write_bytes(b'{"synthetic":false}\n')
    test("changed control rejected",lambda:reject(lambda:w.read_control(record)))
    test("oversized control descriptor rejected before read",lambda:reject(lambda:w.read_control(dict(record,bytes=8*1024*1024+1))))
before=set(sys.modules)
test("public run rejects caller authorization dictionary",lambda:reject(lambda:w.run_reference({"authorized":True}),w.ClosedExecutionGate))
test("public admission rejects caller true",lambda:reject(lambda:w.admit_reference(True),w.ClosedExecutionGate))
test("private scientific body rejects before reading paths",lambda:reject(lambda:w._execute_original_reference({"authorized":True},"NEVER_CREATED","NEVER_CREATED"),w.ClosedExecutionGate))
test("private source loader rejects directly",lambda:reject(w._load_sources_after_admission,w.ClosedExecutionGate))
test("dynamic import helper rejects arbitrary caller path",lambda:reject(lambda:w._import_pinned("forged_original","NEVER_READ"),w.ClosedExecutionGate))
test("closed checks imported no old or scientific modules",lambda:check(set(sys.modules)==before))
tree=ast.parse(path.read_text(encoding="utf-8"))
functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
def first_statement(node):
    return node.body[1] if isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str) else node.body[0]
guarded=("run_reference","admit_reference","_execute_original_reference","_load_sources_after_admission","_import_pinned")
def first_calls_gate(name):
    stmt=first_statement(functions[name])
    call=stmt.value if isinstance(stmt,(ast.Expr,ast.Assign)) else None
    return isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=="_closed_execution_admission"
test("all original import/scientific entries first-call closed gate",lambda:check(all(first_calls_gate(n) for n in guarded)))
test("gate has unconditional raise and no issuer",lambda:check(len(functions["_closed_execution_admission"].body)==1 and isinstance(functions["_closed_execution_admission"].body[0],ast.Raise)))
encode_calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="encode_seed"]
test("one actual original encoder call wired",lambda:check(len(encode_calls)==1 and ast.unparse(encode_calls[0].func)=="package.evaluator.encode_seed"))
test("no native measurement loader or ranking primitive call",lambda:check(not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {"load_native_slot","measure_task_ranking","_measure_task_ranking_unreleased","measure_sample"} for n in ast.walk(tree))))
test("only original prepared seal validated",lambda:check(all(ast.unparse(n.args[0])=="prepared" for n in ast.walk(functions["_execute_original_reference"]) if isinstance(n,ast.Call) and n.args and ((isinstance(n.func,ast.Name) and n.func.id=="verify_original_seal") or (isinstance(n.func,ast.Attribute) and n.func.attr=="verify_seal")))))
report={
 "schema":"newer-native-b1-worker-new-stdlib-checks.v1","passed":True,"checks":checks,
 "source":{"path":str(path),"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()},
 "test_source":{"path":str(Path(__file__).resolve()),"sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
 "synthetic_data_only":True,"new_closed_gate_calls_only":True,"old_modules_imported":False,
 "old_binder_or_contract_functions_called":False,"scientific_body_called":False,
 "science_imported":False,"GPU_or_model_or_NPZ_read":False,
 "old_suites_rerun":False,"runtime_body_validated":False,
}
out=HERE/"NEW_STDLIB_CHECKS.json"
with out.open("x",encoding="utf-8") as f:
    json.dump(report,f,ensure_ascii=False,indent=2);f.write("\n")
print(json.dumps({"passed":True,"checks":len(checks),"sha256":hashlib.sha256(out.read_bytes()).hexdigest()}))
