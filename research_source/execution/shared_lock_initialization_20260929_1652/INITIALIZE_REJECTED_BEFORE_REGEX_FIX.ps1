param([Parameter(Mandatory=$true)][string]$ReviewPath,[Parameter(Mandatory=$true)][string]$ReviewSha256)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$executionRoot='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$target=Join-Path $executionRoot 'latest_baseline_gpu.lock'
$prep=Join-Path $executionRoot 't6_recovery_preparation_20260929_1548'
$result=Join-Path $PSScriptRoot 'INITIALIZATION.json'
function Binding([string]$Path){$item=Get-Item -LiteralPath $Path;[ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($Expected){$actual=Binding $Expected.path;if($actual.bytes -ne $Expected.bytes -or $actual.sha256 -cne $Expected.sha256){throw "Changed input $($Expected.path)"};return $actual}
function NewJson([string]$Path,$Value){$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 14));$file=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}}
if((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath $result)){throw 'One-use initialization refuses existing lock or result'}
if([IO.Path]::GetFullPath($target) -cne 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\latest_baseline_gpu.lock'){throw 'Unexpected target'}
$parent=Get-Item -LiteralPath $executionRoot
if(-not $parent.PSIsContainer -or (($parent.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)){throw 'Unexpected target parent'}
$reviewBinding=Binding $ReviewPath
if($reviewBinding.sha256 -cne $ReviewSha256){throw 'Review changed'}
$review=Get-Content -LiteralPath $ReviewPath -Raw | ConvertFrom-Json -DateKind String
$selfBinding=Binding $PSCommandPath
if($review.schema -cne 'shared-lock-initialization-static-review.v1' -or $review.approved_for_exact_initialization -ne $true){throw 'Independent review absent'}
if($review.script.path -cne $selfBinding.path -or $review.script.sha256 -cne $selfBinding.sha256 -or $review.script.bytes -ne $selfBinding.bytes){throw 'Reviewed source changed'}
if($review.target -cne $target){throw 'Review target mismatch'}
$adoptionPath=Join-Path $prep 'ROOT_SOURCE_ADOPTION.json'
$adoptionBinding=Binding $adoptionPath
if($adoptionBinding.sha256 -cne 'fd093b974627d6ddd6700ffb40c071e2c28deceeb39713fbc8e4cede3dee3fe3'){throw 'Recovery root changed'}
$contractPath=Join-Path $prep 'RECOVERY_CONTRACT.json'
if((Binding $contractPath).sha256 -cne '01bf6d97793d0fbcda9936a85b7955b83e336d0c932531eec9f8f33b179b08a3'){throw 'Recovery contract changed'}
$contract=Get-Content -LiteralPath $contractPath -Raw | ConvertFrom-Json -DateKind String
$sourceBindings=@(
    [ordered]@{path=(Join-Path $prep 'pipeline_recovery_candidate.py');bytes=36404;sha256='b95ee9ff8c90b9323b89eb3a9228c36e40576b16830eb07dbd78e38cef1f833e'},
    [ordered]@{path=(Join-Path $executionRoot 'external_efficiency_preparation\external_t1_driver_v2\driver.py');bytes=(Get-Item -LiteralPath (Join-Path $executionRoot 'external_efficiency_preparation\external_t1_driver_v2\driver.py')).Length;sha256='98ce4defa8870e3a8a2435e78f8fbe8fabca8b34eb3304d7feef18cbc6920453'}
)
$sourceBindings=@($sourceBindings|ForEach-Object {Verify $_})
function CheckStopped {
    $stateBindings=@($contract.live_state_bindings|ForEach-Object {Verify $_})
    $boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().Ticks.ToString()
    if($boot -cne $contract.host_boot_utc_ticks){throw 'Host changed; re-audit incident'}
    $oldIds=@(33924,31992,14420,29784,30388,7584,33520,12896,7484,21652,24120,40780,37764,14260,43500,40968,23920)
    $matches=@(Get-CimInstance Win32_Process | Where-Object {($_.ProcessId -in $oldIds) -or ($_.CommandLine -match '(run_controller_with_state_retry|continue_formal_matrix|supervise_pipeline|supervise_extensions|supervise_latest_baselines|supervise_independent_comparison|run_frozen_robustness_matrix|run_image_level_robustness|run_transactions_formal_efficiency)\.py')})
    if($matches.Count -ne 0){throw 'Controller/science identity or reused old PID present; no initialization'}
    if(Test-Path -LiteralPath (Join-Path $prep 'runtime_attempt')){throw 'Actual recovery attempt already exists'}
    [ordered]@{utc=[DateTimeOffset]::UtcNow.ToString('o');host_boot_utc_ticks=$boot;states=$stateBindings;matched_processes=@()}
}
$before=CheckStopped
$final=CheckStopped
# A persistent byte carrier only. CreateNew cannot overwrite a raced/existing file.
# No byte-range lock is acquired here and no execution release is issued.
$stream=[IO.File]::Open($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.WriteByte(48);$stream.Flush($true)}finally{$stream.Dispose()}
$lockBinding=Binding $target
if($lockBinding.bytes -ne 1 -or [IO.File]::ReadAllBytes($target)[0] -ne 48){throw 'Created lock byte mismatch; preserve and review, never recreate'}
$afterStates=@($contract.live_state_bindings|ForEach-Object {Verify $_})
$record=[ordered]@{schema='persistent-shared-byte-lock-initialization.v1';utc=[DateTimeOffset]::UtcNow.ToString('o');status='created_exact_single_ascii_zero_byte';script=$selfBinding;independent_review=$reviewBinding;recovery_root=$adoptionBinding;protocol_sources=$sourceBindings;before=$before;final_before_create=$final;after_states=$afterStates;lock=$lockBinding;lock_creation_utc_ticks=(Get-Item -LiteralPath $target).CreationTimeUtc.Ticks.ToString();real_byte_lock_acquisition=$false;execution_release_created=$false;recovery_started=$false;scientific_execution=$false;limits=@('Only initializes persistent byte carrier for later Windows first-byte locking; no acquisition/exclusion/launch evidence.','GPU foreign processes unchanged and not exempted; future original GPU gate and 26GiB admission still required.','CreateNew refuses overwrite; any partial failure preserves file and requires observation, never replay or delete.','Process absence is observed twice before creation, not a claim of historical exit codes or atomic exclusion against future unrelated starts.')}
NewJson $result $record
Binding $result | ConvertTo-Json -Depth 4
