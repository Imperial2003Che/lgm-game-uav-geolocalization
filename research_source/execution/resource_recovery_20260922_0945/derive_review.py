from pathlib import Path
I=Path(__file__).resolve().parent
E=I.parent
s=(E/'state_write_recovery_20260920_0138'/'review_recovery.ps1').read_text(encoding='utf-8-sig')
s=s.replace('state_write_recovery_20260920_0138','resource_recovery_20260922_0945').replace('restart_after_state_write_incident_20260920_v1.ps1','restart_after_resource_incident_20260922_v1.ps1')
start=s.index("    if ($LiteralPath.EndsWith('COMPLETED_FIT_REVIEW_20260920.json'))");end=s.index('    if ($script:predecessor -and $LiteralPath',start)
s=s[:start]+'''    if ($LiteralPath.EndsWith('CHECKPOINT_RECOVERY_PROOF.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.proof) {
            'not_passed' {$o.passed=$false}
            'string_passed' {$o.passed='true'}
            'wrong_epoch' {$o.completed_epochs=35}
            'wrong_resume' {$o.resume_start_epoch=23}
            'wrong_target' {$o.run_id='formal_main/university1652/visual_style/seed_2/resnet18/dim_512'}
            'no_reports' {$o.reports=@()}
            'duplicate_reports' {$o.reports=@($o.reports[0],$o.reports[0])}
            'wrong_checkpoint_sha' {$o.reports[0].sha256='f'*64}
            'cuda_initialized' {$o.cuda_initialized=$true}
            'wrong_ledger' {$o.ledger.sha256='f'*64}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath.EndsWith('ROOT_BATCH_36_ADOPTION_20260922.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.adoption) {
            'not_adopted' {$o.adopted=$false}
            'wrong_count' {$o.completed_fit_count=37}
            'includes_incomplete' {$o.completed_fit_ids[0]='formal_sensitivity/university1652/full/seed_1/resnet50/dim_512'}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath.EndsWith('resource_incident_20260922_0945\\CAPTURE.json') -or $LiteralPath.EndsWith('resource_incident_20260922_0945/CAPTURE.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.capture) {
            'wrong_exit' {$o.active.exit_code=0}
            'active_owners' {$o.old_science_and_controllers_absent=$false}
            'missing_file' {$o.files=@($o.files|Select-Object -Skip 1)}
        }
        return $o|ConvertTo-Json -Depth 100
    }
''' +s[end:]
s=s.replace('$Path.EndsWith("last.pt")', '$Path -eq "C:\\项目\\LGM-GAME-Partner-Delivery-20260724\\lgm_game_pytorch\\runs\\formal_sensitivity\\university1652\\backbone_resnet50\\seed_1\\last.pt"')
start=s.index("foreach ($stage in @('primary','pipeline','extensions','latest','independent'))");end=s.index('$failed=@(',start)
s=s[:start]+'''foreach ($stage in @('primary','pipeline','extensions','latest','independent')) {
    Run-Case ($stage+'_valid_launch') $stage @{} $true
    Run-Case ($stage+'_validate_only') $stage @{} $true -Validation
    Run-Case ($stage+'_intent_present') $stage @{existingIntent=$true} $false
}
foreach ($memory in @('low','missing_limit','bool','final_low')) {Run-Case ('memory_'+$memory) primary @{memory=$memory} $false}
foreach ($proof in @('not_passed','string_passed','wrong_epoch','wrong_resume','wrong_target','no_reports','duplicate_reports','wrong_checkpoint_sha','cuda_initialized','wrong_ledger')) {Run-Case ('proof_'+$proof) primary @{proof=$proof} $false}
foreach ($adoption in @('not_adopted','wrong_count','includes_incomplete')) {Run-Case ('adoption_'+$adoption) primary @{adoption=$adoption} $false}
foreach ($capture in @('wrong_exit','active_owners','missing_file')) {Run-Case ('capture_'+$capture) primary @{capture=$capture} $false}
foreach ($owner in @('wrong_role','role_suffix','reused','late_change')) {Run-Case ('owner_'+$owner) pipeline @{owner=$owner} $false}
foreach ($flag in @('jobStarted','jobExit','nonPending','emptyJobs','duplicateJobs','existingRetired','wrongOldStatus','oldOwnerLive','duplicateController')) {Run-Case ('independent_'+$flag) independent @{$flag=$true} $false}
foreach ($hash in @('CAPTURE.json','CHECKPOINT_RECOVERY_PROOF.json','ROOT_BATCH_36_ADOPTION_20260922.json','last.pt','resilient_state.py')) {Run-Case ('hash_'+$hash) primary @{badHash=$hash} $false}
Run-Case 'late_checkpoint_change' primary @{lateCheckpointDrift=$true} $false
Run-Case 'late_state_change' primary @{lateStateDrift=$true} $false
Run-Case 'python_present' primary @{python='always'} $false
Run-Case 'python_appears_late' primary @{python='late'} $false
''' +s[end:]
s=s.replace('state-write-recovery-control-review.v1','resource-recovery-control-review.v1')
with (I/'review_recovery.ps1').open('x',encoding='utf-8-sig') as f:f.write(s)
print('Control test harness prepared; only run against the finally bound candidate.')
