from pathlib import Path
import difflib,hashlib,json
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\visio_full_xsd_research_20260930_1730')
old=base/'derive_ascii_candidate.py'
raw=old.read_bytes();text=raw.decode('utf-8')
needle='needle="input=$inputBefore;system_executable=$system;"\nreplacement="input=$aliasBefore;original_input=$inputBefore;os_path_samefile_before=$samefileBefore;system_executable=$system;"'
replacement='needle=";input=$inputBefore;system_executable=$system;"\nreplacement=";input=$aliasBefore;original_input=$inputBefore;os_path_samefile_before=$samefileBefore;system_executable=$system;"'
assert text.count(needle)==1
newtext=text.replace(needle,replacement,1)
new=base/'derive_ascii_candidate_v2.py'
with new.open('xb') as f:f.write(newtext.encode('utf-8'))
patch=''.join(difflib.unified_diff(text.splitlines(True),newtext.splitlines(True),fromfile=old.name,tofile=new.name))
out=base/'ascii_derivation_v1_to_v2.patch'
with out.open('xb') as f:f.write(patch.encode('utf-8'))
print(json.dumps({'new_source':str(new),'new_bytes':len(newtext.encode('utf-8')),'new_sha256':hashlib.sha256(newtext.encode('utf-8')).hexdigest(),'delta':str(out),'HH_executed':False},ensure_ascii=False))

