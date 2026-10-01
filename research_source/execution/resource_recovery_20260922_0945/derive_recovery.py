"""Prepare a new single-use resource-incident recovery; never launch it."""
from pathlib import Path
import hashlib,json,datetime
E=Path(__file__).resolve().parent.parent
I=Path(__file__).resolve().parent
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
capture=E/'resource_incident_20260922_0945'/'CAPTURE.json'
assert sha(capture)=='80392228a125ad6f705ba54f91172013d2c5df9b089a4e769e2496b9eae06747'
c=json.loads(capture.read_text(encoding='utf-8-sig'))
rows=[]
for name in ['status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json','independent_comparison_status.json','supervise_pipeline.py','supervise_extensions.py','supervise_latest_baselines.py','supervise_independent_comparisons.py']:
    src=E/name;dst=I/'controllers'/name
    if name.endswith('status.json'):
        old=[r for r in c['files'] if r['path']==str(src)]
        assert len(old)==1 and sha(src)==old[0]['sha256']
    with dst.open('xb') as f:f.write(src.read_bytes())
    assert sha(src)==sha(dst)
    rows.append(dict(source=str(src),backup=str(dst),sha256=sha(dst),bytes=dst.stat().st_size))
preservation=I/'PRESERVED_INCIDENT.json'
with preservation.open('x',encoding='utf-8') as f:json.dump(dict(schema='resource-recovery-control-preservation.v1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),capture_sha256=sha(capture),files=rows),f,indent=2,ensure_ascii=False)
source=E/'restart_after_state_write_incident_20260920_v1.ps1'
assert sha(source)=='24fcd4500629a61013d125eb8e6401572a55b8ab62c169bc08bdb20f0ea2c102'
t=source.read_text(encoding='utf-8-sig')
t=t.replace("'state_write_recovery_20260920_0138'","'resource_recovery_20260922_0945'")
t=t.replace('runs\\formal_main\\university1652\\visual_style\\seed_2','runs\\formal_sensitivity\\university1652\\backbone_resnet50\\seed_1')
t=t.replace('b32817173e226422c694bd3b6b20d67e96c01304aa3c584813f88b2ae7760dca',sha(preservation))
t=t.replace('Preserved state-write incident','Preserved resource incident')
start=t.index('$boundProvenancePath = ');end=t.index('$definitions = @{',start)
t=t[:start]+t[end:]
start=t.index('# This recovery follows a completed 80-epoch run');end=t.index('$pins = @{',start)
new='''# This is the Sep22 resource incident and its latest complete 24-epoch checkpoint.
# Prior completed-seed/observer/35-epoch proofs are not recovery evidence here.
$captureRoot = Join-Path $executionRoot 'resource_incident_20260922_0945'
$capturePath = Join-Path $captureRoot 'CAPTURE.json'
$captureSha = '80392228a125ad6f705ba54f91172013d2c5df9b089a4e769e2496b9eae06747'
if ((Sha $capturePath) -ne $captureSha) { throw 'Latest resource incident capture changed.' }
$capture = Get-Content -LiteralPath $capturePath -Raw | ConvertFrom-Json
if ($capture.schema -ne 'science-resource-incident-preservation.v1' -or $capture.old_science_and_controllers_absent -isnot [bool] -or -not $capture.old_science_and_controllers_absent -or @($capture.actual_python_processes).Count -ne 0 -or @($capture.files).Count -ne 35 -or $capture.active.status -ne 'failed' -or $capture.active.pid -ne 39676 -or $capture.active.exit_code -ne 1 -or [IO.Path]::GetFullPath($capture.active.output_dir) -ne $runRoot) { throw 'Resource incident does not match the failed original training.' }
foreach ($row in $capture.files) {
    if ((Sha $row.backup) -ne $row.sha256 -or (Get-Item -LiteralPath $row.backup).Length -ne $row.bytes) { throw 'Archived resource incident file changed.' }
}
$checkpointProofPath = 'PENDING_CHECKPOINT_PROOF_PATH'
$checkpointProofSha = 'PENDING_CHECKPOINT_PROOF_SHA'
$rootAdoptionPath = 'PENDING_ROOT_36FIT_ADOPTION_PATH'
$rootAdoptionSha = 'PENDING_ROOT_36FIT_ADOPTION_SHA'
if ($checkpointProofSha -notmatch '^[0-9a-f]{64}$' -or $rootAdoptionSha -notmatch '^[0-9a-f]{64}$') { throw 'Latest checkpoint verification and root completion adoption are not yet bound; no launch permitted.' }
if ((Sha $checkpointProofPath) -ne $checkpointProofSha -or (Sha $rootAdoptionPath) -ne $rootAdoptionSha) { throw 'Reviewed latest recovery evidence changed.' }
$checkpointProof = Get-Content -LiteralPath $checkpointProofPath -Raw | ConvertFrom-Json
$rootAdoption = Get-Content -LiteralPath $rootAdoptionPath -Raw | ConvertFrom-Json
# Exact schemas will be bound only after independent checkpoint verification and root adoption exist.
throw 'PENDING_EXACT_CHECKPOINT_AND_ROOT_ADOPTION_SCHEMA_REVIEW'
function Assert-RecoveryArtifacts {
    $requiredNames=@('last.pt','best.pt','history.json','run_config.json','run_manifest.json','run.log','process_stdout.log','process_stderr.log')
    $activeRows=@($capture.files | Where-Object { [IO.Path]::GetDirectoryName($_.backup) -eq (Join-Path $captureRoot 'active_run') })
    if ($activeRows.Count -ne 8) { throw 'Captured current run scope changed.' }
    foreach ($name in $requiredNames) {
        $matches=@($activeRows | Where-Object { [IO.Path]::GetFileName($_.path) -eq $name })
        if ($matches.Count -ne 1) { throw 'A required current-run artifact is missing or duplicated.' }
        $row=$matches[0]
        if ([IO.Path]::GetFullPath($row.path) -ne (Join-Path $runRoot $name) -or (Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Latest live run changed after the resource incident was captured.' }
    }
    $ledgerPath='C:\\项目\\LGM-GAME-Partner-Delivery-20260724\\lgm_game_pytorch\\runs\\frozen_formal_matrix_ledger.json'
    $ledgerRows=@($capture.files | Where-Object { $_.path -eq $ledgerPath })
    if ($ledgerRows.Count -ne 1 -or (Sha $ledgerPath) -ne $ledgerRows[0].sha256 -or (Get-Item -LiteralPath $ledgerPath).Length -ne $ledgerRows[0].bytes) { throw 'Captured latest ledger changed before recovery.' }
}
'''
t=t[:start]+new+t[end:]
t=t.replace('Assert-CompletedArtifacts','Assert-RecoveryArtifacts')
t=t.replace('completed_fit_proof_sha256=$completedProofSha;', 'checkpoint_proof_sha256=$checkpointProofSha;root_adoption_sha256=$rootAdoptionSha;incident_capture_sha256=$captureSha;')
assert 'completedProof' not in t and '$observed' not in t and '$observer' not in t and 'OBSERVED_EXIT.json' not in t and 'visual_style\\seed_2' not in t
target=E/'restart_after_resource_incident_20260922_v1.ps1'
with target.open('x',encoding='utf-8-sig',newline='') as f:f.write(t.replace('\n','\r\n'))
print(json.dumps(dict(status='prepared_placeholders_refuse_execution',script_sha256=sha(target),preservation_sha256=sha(preservation),source_template_sha256=sha(source))))
