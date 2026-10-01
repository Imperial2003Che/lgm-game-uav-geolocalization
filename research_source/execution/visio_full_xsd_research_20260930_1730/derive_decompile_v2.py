from pathlib import Path
import hashlib, json, difflib
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\visio_full_xsd_research_20260930_1730')
old=base/'decompile_sdk_chm_once.ps1'
raw=old.read_bytes()
assert len(raw)==5455 and hashlib.sha256(raw).hexdigest()=='188975b1d57b0249138558f776ab5945c3bc54520b1db0c4202988648459690c'
assert not (base/'hh_decompile_attempt_v1').exists()
new=raw.replace(b'=true',b'=$true').replace(b'=false',b'=$false')
assert new!=raw and new.replace(b'=$true',b'=true').replace(b'=$false',b'=false')==raw.replace(b'=$true',b'=true').replace(b'=$false',b'=false')
out=base/'decompile_sdk_chm_once_v2.ps1'
with out.open('xb') as f:f.write(new)
patch=''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True),new.decode('utf-8').splitlines(True),fromfile=old.name,tofile=out.name)).encode('utf-8')
delta=base/'decompile_sdk_chm_v1_to_v2.patch'
with delta.open('xb') as f:f.write(patch)
report={'schema':'visio-chm-decompile-literal-source-derivation.v1','scope':'Only unquoted PowerShell Boolean constants corrected to $true/$false. Original preentry failure retained; no HH/extraction/attempt replay or candidate execution.','old':{'path':str(old),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'new':{'path':str(out),'bytes':len(new),'sha256':hashlib.sha256(new).hexdigest()},'patch':{'path':str(delta),'bytes':len(patch),'sha256':hashlib.sha256(patch).hexdigest()},'true_replacements':raw.count(b'=true'),'false_replacements':raw.count(b'=false'),'attempt_absent':True}
encoded=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
with (base/'DECOMPILE_V2_DERIVATION.json').open('xb') as f:f.write(encoded)
print(json.dumps(report,ensure_ascii=False))
