"""Bind only an actual independently completed checkpoint audit; no launch."""
from pathlib import Path
import hashlib,json,sys
E=Path(__file__).resolve().parent.parent
I=Path(__file__).resolve().parent
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
proof=E/'resource_incident_20260922_0945'/'CHECKPOINT_RECOVERY_PROOF.json'
if not proof.is_file():raise SystemExit('Proof absent; script remains guarded and unbound.')
report=json.loads(proof.read_text(encoding='utf-8-sig'))
assert report['schema']=='resource-incident-checkpoint-recovery-proof.v1' and report['passed'] is True
assert report['status']=='verified_complete_epoch_24' and report['completed_epochs']==24
if len(sys.argv)!=2 or sys.argv[1]!=sha(proof):raise SystemExit('Require independently communicated exact proof SHA before binding.')
p=E/'restart_after_resource_incident_20260922_v1.ps1'
t=p.read_text(encoding='utf-8-sig')
with (I/'before_checkpoint_binding.ps1').open('x',encoding='utf-8-sig') as f:f.write(t)
t=t.replace("$checkpointProofPath = 'PENDING_CHECKPOINT_PROOF_PATH'", "$checkpointProofPath = Join-Path $executionRoot 'resource_incident_20260922_0945/CHECKPOINT_RECOVERY_PROOF.json'")
t=t.replace('PENDING_CHECKPOINT_PROOF_SHA',sha(proof))
marker="# Exact checkpoint schema will be bound after independent checkpoint verification exists.\nthrow 'PENDING_EXACT_CHECKPOINT_AND_ROOT_ADOPTION_SCHEMA_REVIEW'"
replacement='''if ($checkpointProof.schema -ne 'resource-incident-checkpoint-recovery-proof.v1' -or $checkpointProof.passed -isnot [bool] -or -not $checkpointProof.passed -or $checkpointProof.status -ne 'verified_complete_epoch_24' -or $checkpointProof.executable -ne $pythonPath -or $checkpointProof.cuda_initialized -isnot [bool] -or $checkpointProof.cuda_initialized -ne $false -or $checkpointProof.run_id -cne 'formal_sensitivity/university1652/full/seed_1/resnet50/dim_512' -or $checkpointProof.completed_epochs -ne 24 -or $checkpointProof.epoch_zero_based -ne 23 -or $checkpointProof.resume_start_epoch -ne 24 -or $checkpointProof.target_epochs -ne 80) { throw 'Independent checkpoint proof does not verify this exact latest complete 24-epoch run.' }
if ($checkpointProof.capture.sha256 -ne $captureSha -or [IO.Path]::GetFullPath($checkpointProof.capture.path) -ne $capturePath -or $checkpointProof.resume_interface.applicable -isnot [bool] -or -not $checkpointProof.resume_interface.applicable -or $checkpointProof.resume_interface.requested -ne 'last' -or [IO.Path]::GetFullPath($checkpointProof.resume_interface.resolved_path) -ne (Join-Path $runRoot 'last.pt')) { throw 'Checkpoint proof does not bind the latest incident and original resume-last interface.' }
if ((Sha $checkpointProof.script.path) -ne $checkpointProof.script.sha256) { throw 'Independent checkpoint review script changed.' }
$checkpointNames=@()
if (@($checkpointProof.reports).Count -ne 2) { throw 'Exactly two reviewed last/best checkpoint reports are required.' }
foreach ($proof in $checkpointProof.reports) {
    $name=[IO.Path]::GetFileName($proof.file)
    if ($name -notin @('last.pt','best.pt') -or $name -in $checkpointNames) { throw 'Latest checkpoint reports must identify unique last/best files.' }
    $checkpointNames+=$name
    $captured=@($capture.files | Where-Object { $_.path -eq (Join-Path $runRoot $name) })
    if ($captured.Count -ne 1 -or [IO.Path]::GetFullPath($proof.file) -notin @($captured[0].path,$captured[0].backup) -or $proof.sha256 -ne $captured[0].sha256 -or $proof.bytes -ne $captured[0].bytes -or $proof.epoch_zero_based -ne 23 -or $proof.completed_epochs -ne 24 -or $proof.config_sha256 -ne $checkpointProof.run_config_sha256) { throw 'Latest checkpoint report does not match the captured complete epoch and configuration.' }
}
$capturedLedger=@($capture.files | Where-Object { $_.path -eq 'C:\\项目\\LGM-GAME-Partner-Delivery-20260724\\lgm_game_pytorch\\runs\\frozen_formal_matrix_ledger.json' })
if ($capturedLedger.Count -ne 1 -or $checkpointProof.ledger.sha256 -ne $capturedLedger[0].sha256) { throw 'Independent checkpoint proof does not bind the latest ledger.' }'''
assert marker in t
t=t.replace(marker,replacement)
with p.open('w',encoding='utf-8-sig',newline='') as f:f.write(t.replace('\n','\r\n'))
print(json.dumps(dict(script_sha256=sha(p),proof_sha256=sha(proof),status='bound_not_launched')))
