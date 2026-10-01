param([Parameter(Mandatory=$true)][string[]]$Stages)
$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$e=Split-Path -Parent $r
function Exact($v){if($v -is [DateTimeOffset]){return $v};if($v -is [DateTime]){return [DateTimeOffset]$v};return [DateTimeOffset]::Parse([string]$v)}
function Tokens([string]$s){@([regex]::Matches($s,'"([^"\r\n]*)"|([^"\s]+)')|ForEach-Object{if($_.Groups[1].Success){$_.Groups[1].Value}else{$_.Groups[2].Value}})}
function Same-Tokens($observed,$expected){if($observed.Count -ne $expected.Count){return $false};for($k=0;$k -lt $expected.Count;$k++){if($observed[$k] -cne $expected[$k]){return $false}};return $true}
function Process-Record($p){[ordered]@{pid=$p.ProcessId;parent=$p.ParentProcessId;creation=([DateTimeOffset]$p.CreationDate).ToString('o');creation_utc_ticks=([DateTimeOffset]$p.CreationDate).UtcTicks;command=$p.CommandLine}}
$defs=@{primary=@('status.json','controller_pid','running');pipeline=@('pipeline_status.json','supervisor_pid','waiting_for_primary');extensions=@('extension_status.json','supervisor_pid','waiting_for_pipeline');latest=@('latest_baseline_status.json','supervisor_pid','waiting_for_registered_extensions');independent=@('independent_comparison_status.json','supervisor_pid','waiting_for_latest_baselines')}
$rows=@()
foreach($stage in $Stages){
 if(-not $defs.ContainsKey($stage)){throw 'Unknown role'}
 $d=$defs[$stage];$launchPath=Join-Path $r ($stage+'_launch.json');$l=Get-Content -LiteralPath $launchPath -Raw|ConvertFrom-Json
 $statePath=Join-Path $e $d[0];$state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
 if($state.status -ne $d[2]){throw ('Unexpected '+$stage+' state '+$state.status)}
 $owner=@(Get-CimInstance Win32_Process -Filter ('ProcessId='+$state.($d[1])));$launcher=@(Get-CimInstance Win32_Process -Filter ('ProcessId='+$l.launcher_pid))
 if($owner.Count -ne 1 -or $launcher.Count -ne 1){throw 'Missing actual controller or launcher'}
 if($owner[0].ParentProcessId -ne $launcher[0].ProcessId){throw 'Controller parent mismatch'}
 $launchTicks=(Exact $l.launcher_creation_time).UtcTicks
 # CIM exposes microseconds; .NET StartTime additionally exposes 100 ns ticks.
 if(([DateTimeOffset]$launcher[0].CreationDate).UtcTicks -ne ($launchTicks-($launchTicks%10))){throw 'Launcher creation mismatch'}
 $expected=@($l.python)+@(Tokens $l.arguments)
 if(-not (Same-Tokens @(Tokens $launcher[0].CommandLine) $expected)){throw 'Launcher command mismatch'}
 $expected[0]='C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe'
 if(-not (Same-Tokens @(Tokens $owner[0].CommandLine) $expected)){throw 'Controller command mismatch'}
 $recorded=if($stage -eq 'primary'){$state.started_utc}else{$state.supervisor_started_utc}
 $dt=(Exact $recorded)-([DateTimeOffset]$owner[0].CreationDate)
 if($dt.TotalSeconds -lt 0 -or $dt.TotalSeconds -gt 60){throw 'Controller start mismatch'}
 $oldSnapshots=@(Get-ChildItem -LiteralPath $r -Filter 'OWNER_SNAPSHOT_*.json'|Sort-Object Name)
 foreach($f in $oldSnapshots){$old=Get-Content -LiteralPath $f.FullName -Raw|ConvertFrom-Json;$prior=@($old.states|Where-Object role -eq $stage);if($prior.Count){if($prior[0].owner.creation_utc_ticks -ne ([DateTimeOffset]$owner[0].CreationDate).UtcTicks -or $prior[0].owner.command -cne $owner[0].CommandLine -or $prior[0].launcher.creation_utc_ticks -ne ([DateTimeOffset]$launcher[0].CreationDate).UtcTicks -or $prior[0].launcher.command -cne $launcher[0].CommandLine){throw 'Current owner differs from first observed new identity'};break}}
 $stderr=Get-Item -LiteralPath $l.stderr
 $rows+=[ordered]@{role=$stage;status=$state.status;heartbeat_utc=$state.heartbeat_utc;owner=(Process-Record $owner[0]);launcher=(Process-Record $launcher[0]);pending_jobs=@($state.jobs|Where-Object status -eq 'pending').Count;total_jobs=@($state.jobs).Count;stderr_bytes=$stderr.Length;active=$state.active}
}
$primary=Get-Content -LiteralPath (Join-Path $e 'status.json') -Raw|ConvertFrom-Json
$science=@();$history=@()
if($primary.active){
 $sp=@(Get-CimInstance Win32_Process -Filter ('ProcessId='+$primary.active.pid));if($sp.Count -ne 1){throw 'Active science launcher missing'}
 if($sp[0].ParentProcessId -ne $primary.controller_pid -or -not (Same-Tokens @(Tokens $sp[0].CommandLine) @($primary.active.command))){throw 'Science active.command or parent mismatch'}
 $science+=Process-Record $sp[0]
 $ip=@(Get-CimInstance Win32_Process -Filter ('ParentProcessId='+$primary.active.pid)|Where-Object Name -eq 'python.exe')
 foreach($p in $ip){$expected=@($primary.active.command);$expected[0]='C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe';if(-not (Same-Tokens @(Tokens $p.CommandLine) $expected)){throw 'Science interpreter command mismatch'};$science+=Process-Record $p}
 $historyPath=Join-Path $primary.active.output_dir 'history.json';if(Test-Path -LiteralPath $historyPath){$history=@(Get-Content -LiteralPath $historyPath -Raw|ConvertFrom-Json)}
}
$memory=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$report=[ordered]@{schema='new-host-recovery-owner-snapshot.v1';time=(Get-Date).ToString('o');states=$rows;science=$science;history_count=$history.Count;last_history=if($history.Count){$history[-1]}else{$null};commit_headroom_GiB=($memory.CommitLimit-$memory.CommittedBytes)/1GB;runtime_memory_not_stop_threshold=$true}
$dest=Join-Path $r ('OWNER_SNAPSHOT_'+(Get-Date -Format yyyyMMdd_HHmmssfff)+'.json');$b=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 20));$s=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$s.Write($b,0,$b.Length)}finally{$s.Dispose()}
[ordered]@{path=$dest;sha256=(Get-FileHash -LiteralPath $dest).Hash.ToLower();states=@($rows|ForEach-Object{[ordered]@{role=$_.role;status=$_.status;owner=$_.owner.pid;launcher=$_.launcher.pid;stderr_bytes=$_.stderr_bytes}});science=$science;history_count=$history.Count;commit_headroom_GiB=$report.commit_headroom_GiB}|ConvertTo-Json -Depth 10
