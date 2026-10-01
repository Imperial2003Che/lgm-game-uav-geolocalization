"""Only new root-review canonical-type and bounded-read regression cases."""
from pathlib import Path
import copy, hashlib, importlib.util, json, sys, tempfile
from types import SimpleNamespace
from unittest.mock import patch
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent
source=W/"reference_worker.py"
spec=importlib.util.spec_from_file_location("_b1_revision_pure",source)
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
checks=[]
def reject(fn):
    try: fn()
    except RuntimeError: return
    raise AssertionError("Expected rejection")
prepared={"settings":{"batch_size":16,"workers":1}}
prepared["payload_sha256"]=w.digest(w.canonical(prepared))
for label,value in (("int-to-bool",True),("int-to-float",1.0)):
    derived=copy.deepcopy(prepared);derived["settings"]["batch_size"]=1;derived["settings"]["workers"]=value
    declared={"json_pointer":"/settings/batch_size","original":16,"derived":1,
              "original_canonical_sha256":w.digest(w.canonical(prepared)),
              "derived_canonical_sha256":w.digest(w.canonical(derived)),
              "original_prepared_file_modified":False}
    reject(lambda:w.derivation_envelope(prepared,derived,declared))
    checks.append(label+" non-batch difference rejected despite Python equality")
with tempfile.TemporaryDirectory(prefix="revision_fixture_",dir=W) as temp:
    p=Path(temp)/"small.json";p.write_bytes(b"{}\n")
    item={"path":str(p.resolve()),"bytes":3,"sha256":w.digest(b"{}\n")}
    with patch.object(Path,"open",side_effect=AssertionError("Must not read mismatched-size control")):
        reject(lambda:w.read_control(dict(item,bytes=1)))
    checks.append("actual-vs-declared size mismatch rejected before open/hash")
    with patch.object(Path,"stat",return_value=SimpleNamespace(st_size=9*1024*1024)), patch.object(Path,"open",side_effect=AssertionError("Must not read oversized control")):
        reject(lambda:w.read_control(item))
    checks.append("synthetic oversized actual stat rejected before open/hash")
    raw,value=w.read_control(item)
    assert raw==b"{}\n" and value=={}
    checks.append("bounded valid control remains accepted")
report={"schema":"new-b1-root-revision-subset.v1","passed":True,"checks":checks,
        "source":{"path":str(source),"bytes":source.stat().st_size,"sha256":hashlib.sha256(source.read_bytes()).hexdigest()},
        "test_source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "only_affected_new_checks":True,"prior_29_checks_not_rerun":True,
        "large_asset_read":False,"science_or_old_modules_imported":False,
        "scientific_body_or_old_binder_called":False}
out=W/"ROOT_REVISION_STDLIB_CHECKS.json"
with out.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2);f.write("\n")
print(json.dumps({"passed":True,"new_checks":len(checks),"report_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"source":report["source"]},ensure_ascii=True))
