from pathlib import Path
import hashlib,json,difflib
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\visio_full_xsd_research_20260930_1730')
old=base/'decompile_sdk_chm_once_v2.ps1'
raw=old.read_bytes()
assert len(raw)==5475 and hashlib.sha256(raw).hexdigest()=='50642f3fff28549d560faae14c951fbbb554612c9715336dafef5cd6d686c7ff'
assert not (base/'hh_decompile_attempt_v1').exists()
needle=b'if($p -and $result.process_exit_confirmed)'
assert raw.count(needle)==1
new=raw.replace(needle,b'if($p -and ($result.process_exit_confirmed -is [bool]) -and ($result.process_exit_confirmed -eq $true))')
out=base/'decompile_sdk_chm_once_v3.ps1'
with out.open('xb') as f:f.write(new)
patch=''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True),new.decode('utf-8').splitlines(True),fromfile=old.name,tofile=out.name)).encode('utf-8')
delta=base/'decompile_sdk_chm_v2_to_v3.patch'
with delta.open('xb') as f:f.write(patch)
report={'schema':'visio-chm-decompile-strict-cleanup-source-derivation.v1','scope':'Only finally process-object disposal condition adds strict actual Boolean type and true value; no Kill/Quit or unknown-process cleanup. v1/v2 retained.','old':{'path':str(old),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'new':{'path':str(out),'bytes':len(new),'sha256':hashlib.sha256(new).hexdigest()},'patch':{'path':str(delta),'bytes':len(patch),'sha256':hashlib.sha256(patch).hexdigest()},'attempt_absent':True}
encoded=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
with (base/'DECOMPILE_V3_DERIVATION.json').open('xb') as f:f.write(encoded)
print(json.dumps(report,ensure_ascii=False))
