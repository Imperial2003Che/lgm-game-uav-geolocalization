$ErrorActionPreference='Stop'
$capturePath=Join-Path $PSScriptRoot 'capture_20260929_144939892\CAPTURE.json'
function Bind([string]$p){$i=Get-Item -LiteralPath $p;[ordered]@{path=$i.FullName;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant();bytes=$i.Length}}
$cb=Bind $capturePath
if($cb.sha256 -ne '7cd62f16dcf7f4a1ab9f3578b7c780ecb641ec02bf0fdf55a0a802f8bec2c1e4'){throw 'Capture digest'}
$cap=Get-Content -LiteralPath $capturePath -Raw|ConvertFrom-Json -DateKind String
$checks=[Collections.Generic.List[object]]::new()
foreach($b in $cap.bindings){foreach($r in @($b.source,$b.snapshot)){$a=Bind $r.path;if($a.sha256 -ne $r.sha256 -or $a.bytes -ne $r.bytes){throw 'Capture file mismatch'};$checks.Add($a)}}
function Captured([string]$suffix){$a=@($cap.bindings|Where-Object {$_.source.path.EndsWith($suffix,[StringComparison]::OrdinalIgnoreCase)});if($a.Count -ne 1){throw "Capture unique suffix $suffix"};$a[0].snapshot.path}
$pipeline=Get-Content -LiteralPath (Captured 'execution\pipeline_status.json') -Raw|ConvertFrom-Json -DateKind String
if($pipeline.status -ne 'failed' -or $pipeline.jobs.Count -ne 7 -or @($pipeline.jobs|Where-Object status -eq completed).Count -ne 6){throw 'Pipeline contract'}
$failed=@($pipeline.jobs|Where-Object id -eq formal_efficiency_component)
if($failed.Count -ne 1 -or $failed[0].status -ne 'failed' -or $failed[0].exit_code -ne 1 -or $failed[0].pid -ne 23920){throw 'Failure contract'}
$logPath=Captured 'stage_logs\formal_efficiency_component.stderr.log'
$err=[IO.File]::ReadAllText($logPath)
if(-not $err.StartsWith('ERROR: T6 requires an exclusive GPU; active compute processes: ')){throw 'Different failure'}
$srcPath=Captured 'experiments\run_transactions_formal_efficiency.py'
$src=[IO.File]::ReadAllText($srcPath)
if((Bind $srcPath).sha256 -ne $failed[0].entrypoint_sha256){throw 'T6 source mismatch'}
$begin=$src.IndexOf('def run_benchmark(')
$gpuCheck=$src.IndexOf('    assert_exclusive_gpu()', $begin)
$cudaCheck=$src.IndexOf('    if not torch.cuda.is_available():', $begin)
$outputCreation=$src.IndexOf('    output.mkdir(', $begin)
if(-not($begin -gt 0 -and $gpuCheck -gt $begin -and $cudaCheck -gt $gpuCheck -and $outputCreation -gt $cudaCheck)){throw 'Source phase ordering'}
$output='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal'
$outputExists=Test-Path -LiteralPath $output
if($outputExists){throw 'Unexpected T6 outputs require distinct inspection'}
$all=@(Get-CimInstance Win32_Process)
$matches=@($all|Where-Object {$_.ProcessId -in $cap.searched_prior_pids -or ($_.Name -eq 'python.exe' -and $_.CommandLine -match 'LGM|lgm')}|ForEach-Object{[ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation=([DateTimeOffset]$_.CreationDate).ToString('o');creation_utc_ticks=([DateTimeOffset]$_.CreationDate).UtcTicks;command=$_.CommandLine}})
$report=[ordered]@{schema='root-efficiency-capture-review.v1';time=[DateTimeOffset]::Now.ToString('o');capture=$cb;source=(Bind $PSCommandPath);checks=$checks.ToArray();file_binding_checks=$checks.Count;completed_pipeline_job_ids=@($pipeline.jobs|Where-Object status -eq completed|ForEach-Object id);completion_scope='Original parent-recorded completions only; new robustness aggregate/query artifacts require separate scientific audits';failed_job=$failed[0];stderr=(Bind $logPath);t6_source=(Bind $srcPath);t6_output_path=$output;t6_output_exists=$outputExists;current_prior_pid_matches=$matches;cause='Original exclusive-GPU guard rejected other PIDs returned by nvidia-smi before benchmark configuration/output creation';host_reboot_incident=$false;gpu_guard_modified=$false;scientific_state_modified=$false;recovery_started=$false;limits=@('No original failed T6 interpreter creation identity or independent dual-handle exit was captured','Parent recorded launcher23920 exit1; controller own exit codes unknown','Cannot classify graphics-only or actual CUDA activity from process names/N/A/permission failures','Existing recovery scripts are consumed and remain unreplayed; natural original admission must hold before a new incident-specific recovery','No new scientific acceptance inferred from parent exit0, file existence or this capture review')}
$p=Join-Path $PSScriptRoot 'ROOT_CAPTURE_REVIEW.json'
$b=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 20))
$f=[IO.File]::Open($p,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$f.Write($b,0,$b.Length)}finally{$f.Dispose()}
Bind $p|ConvertTo-Json
