from pathlib import Path
E=Path(__file__).resolve().parent.parent
I=Path(__file__).resolve().parent
p=E/'restart_after_resource_incident_20260922_v1.ps1'
t=p.read_text(encoding='utf-8-sig')
with (I/'before_root_binding.ps1').open('x',encoding='utf-8-sig') as f:f.write(t)
t=t.replace("$rootAdoptionPath = 'PENDING_ROOT_36FIT_ADOPTION_PATH'", "$rootAdoptionPath = Join-Path $executionRoot 'completion_audits_20260922/ROOT_BATCH_36_ADOPTION_20260922.json'")
t=t.replace('PENDING_ROOT_36FIT_ADOPTION_SHA','1c7bdd8e27328118789462a3db2f8283d6803e50c26a2914dd4674010ddf358f')
marker='# Exact schemas will be bound only after independent checkpoint verification and root adoption exist.'
replacement='''if ($rootAdoption.schema -ne 'root-independent-completion-adoption.v1' -or $rootAdoption.adopted -isnot [bool] -or -not $rootAdoption.adopted -or $rootAdoption.completed_fit_count -ne 36 -or $rootAdoption.formal_evaluation_count -ne 0 -or $rootAdoption.last_active_status -ne 'failed' -or $rootAdoption.last_active_complete_epochs -ne 24 -or [IO.Path]::GetFullPath($rootAdoption.last_active_run) -ne $runRoot -or $rootAdoption.no_scientific_imports_or_live_changes -ne $true) { throw 'Root adoption does not match 36 completed main fits and this incomplete 24-epoch run.' }
$acceptedIds=@($rootAdoption.completed_fit_ids)
if ($acceptedIds.Count -ne 36 -or @($acceptedIds | Select-Object -Unique).Count -ne 36 -or @($acceptedIds | Where-Object { $_ -notlike 'formal_main/*' }).Count -ne 0) { throw 'Root completion adoption includes missing, duplicate or non-main fits.' }
foreach ($row in @($rootAdoption.root_script,$rootAdoption.independent_report)+@($rootAdoption.verified_small_evidence_bindings)+@($rootAdoption.root_observational_evidence)) {
    if ((Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Root adoption provenance changed.' }
}
# Exact checkpoint schema will be bound after independent checkpoint verification exists.'''
assert marker in t
t=t.replace(marker,replacement)
with p.open('w',encoding='utf-8-sig',newline='') as f:f.write(t.replace('\n','\r\n'))
print('Root adoption bound; checkpoint proof placeholder still prohibits execution.')
