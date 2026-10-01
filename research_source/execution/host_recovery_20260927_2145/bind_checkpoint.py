from pathlib import Path
import difflib
import hashlib

root=Path(r"C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution")
out=root/'host_recovery_20260927_2145'
target=root/'restart_after_host_interruption_20260927_v1.ps1'
proof=root/'host_interruption_20260927_2145'/'CHECKPOINT_RECOVERY_PROOF.json'
digest='62da440dccee5b3cea2a2de753a791e8792e91cd12e045358c0b2406d4a71e9c'
assert hashlib.sha256(proof.read_bytes()).hexdigest()==digest
original=target.read_bytes()
assert hashlib.sha256(original).hexdigest()=='b4d0649d135d5abd0861e04c1973d1b7ce63b76640b69033954251fee348921d'
with (out/'UNBOUND_SOURCE_PRESERVED.ps1').open('xb') as f: f.write(original)
text=original.decode('utf-8')
assert text.count('UNBOUND_75_EPOCH_PROOF_DO_NOT_LAUNCH')==1
text=text.replace('UNBOUND_75_EPOCH_PROOF_DO_NOT_LAUNCH',digest)
target.write_text(text,encoding='utf-8',newline='\n')
base=root/'restart_after_resource_incident_20260922_v1.ps1'
with (out/'BOUND_SOURCE_DIFF.patch').open('x',encoding='utf-8',newline='\n') as f:
    f.write(''.join(difflib.unified_diff(base.read_text(encoding='utf-8-sig').splitlines(keepends=True),text.splitlines(keepends=True),fromfile=base.name,tofile=target.name)))
print(hashlib.sha256(target.read_bytes()).hexdigest())
