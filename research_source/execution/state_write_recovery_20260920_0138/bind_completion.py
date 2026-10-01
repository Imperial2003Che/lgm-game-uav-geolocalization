from pathlib import Path
E=Path(__file__).resolve().parent.parent
p=E/'restart_after_state_write_incident_20260920_v1.ps1'
t=p.read_text(encoding='utf-8-sig')
with (p.parent/'state_write_recovery_20260920_0138'/'before_completed_proof_binding.ps1').open('x',encoding='utf-8-sig') as f:f.write(t)
t=t.replace('PENDING_ROOT_COMPLETED_PROOF_SHA','93890643b3649b7b53951566ed573d494c5f78016954546853bfc416886afb5b')
t=t.replace("# Exact completed-proof schema checks are inserted after root completes its native validator.\nif ($completedProof.recovery_authorized -ne $true) { throw 'Completed-fit validation has not authorized recovery.' }",'''if ($completedProof.schema -ne 'detached-fit-completion-review.v1' -or $completedProof.passed -isnot [bool] -or -not $completedProof.passed -or $completedProof.executable -ne $pythonPath -or @($completedProof.original_training_completion_issues).Count -ne 0 -or $completedProof.original_owner_and_observer_absent -ne $true -or $completedProof.epochs_completed -ne 80 -or $completedProof.last_epoch -ne 79 -or $completedProof.completed_fit_count -ne 14 -or $completedProof.formal_evaluation_manifest_count -ne 0 -or $completedProof.ledger_unchanged -ne $true -or @($completedProof.scientific_modules).Count -ne 0) { throw 'Original completed-fit validation is not the accepted 80-epoch audit.' }
if ($completedProof.run_identifier -cne 'formal_main/university1652/visual_style/seed_2/resnet18/dim_512' -or [IO.Path]::GetFullPath($completedProof.run_dir) -ne $runRoot -or $completedProof.source_provenance.manifest_sha256 -ne $primaryManifestSha) { throw 'Completed proof does not identify this exact frozen fit.' }
foreach ($row in @($completedProof.review_script,$completedProof.observer_started,$completedProof.observed_exit,$completedProof.capture)) {
    if ((Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Completed proof provenance changed.' }
}
function Assert-CompletedArtifacts {
    $requiredNames=@('run_config.json','history.json','last.pt','best.pt','run.log')
    if (@($completedProof.artifacts_sha256_verified.PSObject.Properties).Count -ne 5) { throw 'Completed proof artifact count changed.' }
    foreach ($name in $requiredNames) {
        $row=$completedProof.artifacts_sha256_verified.$name
        if (-not $row -or [IO.Path]::GetFullPath($row.path) -ne (Join-Path $runRoot $name) -or (Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Completed-fit proof artifact changed.' }
    }
    if (@($observed.run_files_after_exit.PSObject.Properties).Count -ne 6) { throw 'Observed run file count changed.' }
    foreach ($name in @('run_manifest.json','run_config.json','history.json','run.log','process_stdout.log','process_stderr.log')) {
        $row=$observed.run_files_after_exit.$name
        if (-not $row -or [IO.Path]::GetFullPath($row.path) -ne (Join-Path $runRoot $name) -or (Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Completed run file changed since real process exit.' }
    }
    if ((Sha $completedProof.ledger.path) -ne $completedProof.ledger.sha256) { throw 'Frozen ledger changed before primary recovery.' }
}''')
start=t.index('    foreach ($entry in $observed.run_files_after_exit.PSObject.Properties)');end=t.index('    # Engineering admission threshold:',start)
t=t[:start]+'    Assert-CompletedArtifacts\n'+t[end:]
t=t.replace('$archivePath = $null\n{\n','$archivePath = $null\nif ($true) {\n')
t=t.replace("    $memoryFinal = Read-MemorySample", "    Assert-CompletedArtifacts\n    $memoryFinal = Read-MemorySample")
with p.open('w',encoding='utf-8-sig',newline='') as f:f.write(t.replace('\n','\r\n'))
print('Completion proof bound; I/O pins still pending narrow diagnostic repair.')
