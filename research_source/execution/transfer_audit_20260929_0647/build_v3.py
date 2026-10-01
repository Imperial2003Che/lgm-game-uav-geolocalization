from pathlib import Path
import hashlib,difflib
here=Path(__file__).parent
old=here/'review_transfer_v2.py';base=old.read_text(encoding='utf-8')
assert hashlib.sha256(old.read_bytes()).hexdigest()=='51493d8e86df998581668e8485f7e8c23bfca7c17d469757a0dc4cf385310130'
s=base.replace('EXTRACTED=[]','EXTRACTED=[]\nSOURCE_BYTES={}')
s=s.replace("text=Path(path).read_text(encoding='utf-8');tree=ast.parse(text)","check(str(path) in SOURCE_BYTES,'Original AST source must come from SHA-verified immutable snapshot bytes')\n    text=SOURCE_BYTES[str(path)].decode('utf-8');tree=ast.parse(text)")
oldline="for p,h in [(matrix_path,'50e681a17bd21188ec059112a77653e04f0cd716a95f4e1c0dfbb486375cc84c'),(adapter_path,'29cccd4ff3e975571b578288f7a691ceccaf4a8ed7ab9483812b68edbc4f5ed8'),(core_path,'081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862')]:snap(p,expected=h)"
assert oldline in s
s=s.replace(oldline,oldline.replace(':snap(p,expected=h)',":SOURCE_BYTES[str(p)]=snap(p,expected=h)[0]"))
s=s.replace("'canonical_json_bytes','canonical_sha256','slugify'", "'canonical_json_bytes','canonical_sha256','normalized_relative_path','slugify'")
s=s.replace("check(len(paths)==len(set(paths)),'Unique evidence paths')", "check(paths==[core.normalized_relative_path(p) for p in paths],'Evidence paths must already equal original normalized form')\n        check(len(paths)==len(set(p.casefold() for p in paths)),'Casefold-unique evidence paths')")
s=s.replace("start,end=lr['events'];check(start['status']=='running'", "start,end=lr['events']\n        check(all(lr[k]==end[k] for k in ('status','attempt','return_code','finished_utc','elapsed_seconds','manifest_sha256','checkpoint_sha256','stdout_sha256','stderr_sha256')),'Ledger terminal row differs from original completion event')\n        check(start['status']=='running'")
s=s.replace("fn,kind=converters[dtype];return Vec([fn(v) for v in value],kind)", "fn,kind=converters[dtype];converted=[fn(v) for v in value]\n        if dtype==NP.int64:check(all(-(2**63)<=v<2**63 for v in converted),'Compatibility int64 overflow rejected')\n        return Vec(converted,kind)")
s=s.replace("'source_definitions_extracted_unchanged']=EXTRACTED", "'source_definitions_extracted_unchanged']=EXTRACTED\n    report['AST_definitions_loaded_from_SHA_verified_snapshot_bytes']=True")
s=s.replace("snap(HERE/'V1_TO_V2.patch')", "snap(HERE/'V1_TO_V2.patch')\n    snap(HERE/'V2_TO_V3.patch')\n    snap(HERE/'review_transfer_v2.py',expected='51493d8e86df998581668e8485f7e8c23bfca7c17d469757a0dc4cf385310130')\n    report['unexecuted_v2_candidate_retained']=True\n    report['v3_static_review_changes']=['Extract only SHA-verified source bytes','Apply original path normalizer and casefold uniqueness','Bind ledger terminal fields to completed event','Fail closed on compatibility int64 overflow']")
compile(s,'v3','exec')
new=here/'review_transfer_v3.py'
with new.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
with (here/'V2_TO_V3.patch').open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(difflib.unified_diff(base.splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(new))))
first=(here/'review_transfer.py').read_text(encoding='utf-8')
with (here/'V1_TO_V3_FULL.patch').open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(difflib.unified_diff(first.splitlines(True),s.splitlines(True),fromfile=str(here/'review_transfer.py'),tofile=str(new))))
print(hashlib.sha256(new.read_bytes()).hexdigest())
