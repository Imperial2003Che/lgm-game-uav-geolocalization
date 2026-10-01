from pathlib import Path
import difflib

here=Path(__file__).parent
old=here.parent/'robustness_audit_20260929_0946/adopt_visual1.ps1'
original=old.read_text(encoding='utf-8-sig')
s=original.replace('[string]$ObservationSHA)', '[string]$ObservationSHA,[Parameter(Mandatory=$true)][string]$DeliverySHA,[Parameter(Mandatory=$true)][string]$DiffSHA)')
s=s.replace('review_visual1.py','review_full1.py').replace("$manifest.variant -ne 'visual'", "$manifest.variant -ne 'full'")
s=s.replace('51edb3f929b337ec3c129ad502336a5f5676ef15fbd606d760526b04a2dbfbd0','c7bfc6c41ccadf0f52cf79609a76ef921bf456c5d06334b78ece284a5b4c9ce1')
s=s.replace('$null -ne $manifest.clip_clean_reproduction_audit','$null -eq $manifest.clip_clean_reproduction_audit')
s=s.replace("$liveLedger.runs.'university1652/visual/seed_1'", "$liveLedger.runs.'university1652/full/seed_1'")
start=s.index('$transition=Verify')
end=s.index('$ob=Verify',start)
s=s[:start]+r'''$transition=Verify (Join-Path $PSScriptRoot 'ROOT_FULL_TRANSITION.json') '70967e6f477d24419439c6251601300d7d77056b9682d7c6a963654b53e470f8'
$t=J $transition.path
$null=B $t.source;$null=B $t.old_identity_snapshot;$null=B $t.new_identity_snapshot;$null=B $t.ledger_snapshot
foreach($b in $t.closed_log_bindings){$null=B $b}
if(($t.completed_record|ConvertTo-Json -Depth 12 -Compress) -cne ($sealed|ConvertTo-Json -Depth 12 -Compress)){throw 'Root transition differs from independent completed record'}
$db=Verify (Join-Path $PSScriptRoot 'DELIVERY.json') $DeliverySHA
$delivery=J $db.path
foreach($b in $delivery.bindings){$null=B $b}
$diff=Verify (Join-Path $PSScriptRoot 'FULL_SOURCE_DIFF.patch') $DiffSHA
$previous=Verify (Join-Path $e 'robustness_audit_20260929_0946\ROOT_VISUAL1_ADOPTION.json') '81ec5d80b7370ae5dc79c3f12e0633b88ade73be3422ec155ea11def68713cc6'
$prev=J $previous.path
if(-not $prev.accepted_with_stated_limits -or $prev.accepted_robustness_runs -ne 1 -or $prev.accepted_corrupted_tasks -ne 90){throw 'Previous adopted scope mismatch'}
$cb=Verify (Join-Path $PSScriptRoot 'contract_review\FULL_CONTRACT_REVIEW.json') $ContractReportSHA
$c=J $cb.path
$null=B $c.review_markdown;$null=B $c.sealing_source
foreach($b in $c.source_and_small_file_bindings){$null=B $b.snapshot;if($b.label -ne 'ledger_snapshot'){$null=B $b.source}}
if($c.source_or_live_state_modified -or @($c.scientific_modules_imported).Count -ne 0 -or $c.original_validator_or_science_executed -or $c.new_test_suite_run -or -not $c.manifest_embedded_diagnostic_equals_standalone){throw 'Full contract scope mismatch'}
if(($manifest.clip_clean_reproduction_audit|ConvertTo-Json -Depth 15 -Compress) -cne ($c.diagnostic|ConvertTo-Json -Depth 15 -Compress)){throw 'Full diagnostic declaration mismatch'}
if($c.diagnostic.payload_sha256 -cne 'd8788767a0bd22ef51e0b2a81218b762c5ede896e1668991caa9626b833db10c' -or $c.diagnostic.samples -ne 64 -or $c.diagnostic.clip_provenance.precision -cne 'fp16'){throw 'Full diagnostic scope mismatch'}
if($r.inherited_authority.source_training_identifier -cne 'formal_main/university1652/full/seed_1/resnet18/dim_512' -or $manifest.checkpoint.checkpoint_sha256 -cne '581fc1b40e0dc343f3906c8e180bc843a58d37ba97e8fb5833f2c49ac39a9c99'){throw 'Specific Full authority mismatch'}
''' +s[end:]
s=s.replace('@(27888,41564)','@(40820,43872)').replace('lgm.root.robustness-visual1-adoption.v1','lgm.root.robustness-full1-adoption.v1')
s=s.replace('accepted_robustness_runs=1;accepted_corrupted_conditions=30;accepted_corrupted_tasks=90;accepted_clean_tasks=3;', 'previous_robustness_adoption=$previous;newly_accepted_runs=1;newly_accepted_corrupted_conditions=30;newly_accepted_corrupted_tasks=90;newly_accepted_clean_tasks=3;accepted_robustness_runs=2;accepted_corrupted_conditions=60;accepted_corrupted_tasks=180;accepted_clean_tasks=6;')
s=s.replace('limits=$r.limits;', 'limits=@($r.limits)+@($c.interpretation_limits);full_clean_diagnostic=$c.diagnostic;')
s=s.replace("'ROOT_VISUAL1_ADOPTION.json'", "'ROOT_FULL1_ADOPTION.json'")
# Correct the inherited previous-root path, which deliberately retains Visual1.
s=s.replace("robustness_audit_20260929_0946\\ROOT_FULL1_ADOPTION.json", "robustness_audit_20260929_0946\\ROOT_VISUAL1_ADOPTION.json")
with (here/'adopt_full1.ps1').open('x',encoding='utf-8',newline='\n') as f:f.write(s)
with (here/'ROOT_ADOPTION_DIFF.patch').open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile=str(old),tofile='adopt_full1.ps1')))
print('Prepared root source only; not executed.')
