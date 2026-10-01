$ErrorActionPreference='Stop'
$out=Join-Path $PSScriptRoot 'BROKER_QUERY_IMAGE_OBSERVATION.json'
if(Test-Path -LiteralPath $out){throw 'Observation already exists'}
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class BrokerReadOnly {
 [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern bool QueryFullProcessImageName(IntPtr h, uint flags, StringBuilder name, ref uint size);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern bool GetProcessTimes(IntPtr h, out long created, out long exited, out long kernel, out long user);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern bool CloseHandle(IntPtr h);
}
'@
function Snapshot {
 $s=@(Get-CimInstance Win32_Service -Filter "Name = 'DcomLaunch'")
 if($s.Count -ne 1 -or $s[0].State -ne 'Running' -or $s[0].StartName -ne 'LocalSystem'){throw 'Unexpected exact service mapping'}
 $p=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$s[0].ProcessId)
 if(!$p -or $p.Name -ne 'svchost.exe' -or !$p.CreationDate){throw 'Missing parent identity'}
 [ordered]@{utc=[DateTime]::UtcNow.ToString('o');service=[ordered]@{name=$s[0].Name;state=$s[0].State;startName=$s[0].StartName;processId=$s[0].ProcessId;configuredPathName=$s[0].PathName};parent=[ordered]@{pid=$p.ProcessId;name=$p.Name;ticks=$p.CreationDate.ToUniversalTime().Ticks.ToString();actualExecutable=$p.ExecutablePath;actualCommandLine=$p.CommandLine}}
}
$first=Snapshot
$record=[ordered]@{schema='dcom-broker-readonly-image-observation.v1';source=[ordered]@{path=$PSCommandPath;bytes=(Get-Item -LiteralPath $PSCommandPath).Length;sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()};first=$first;accessRequested='PROCESS_QUERY_LIMITED_INFORMATION 0x1000 only';openSucceeded=$false;openError=$null;querySucceeded=$false;queryError=$null;actualImagePath=$null;getTimesSucceeded=$false;getTimesError=$null;heldCreationUtcTicks=$null;closeSucceeded=$null;second=$null;identityMatched=$false;COMExecuted=$false;processControl=$false;limits='Only the currently mapped DcomLaunch service host is queried. No Visio handle, COM reference, ownership, closure or launch authorization.'}
$handle=[BrokerReadOnly]::OpenProcess(0x1000,$false,[uint32]$first.parent.pid)
$openError=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
if($handle -eq [IntPtr]::Zero){$record.openError=$openError}else{
 $record.openSucceeded=$true
 try {
  [uint32]$size=32768;$name=[Text.StringBuilder]::new([int]$size)
  $record.querySucceeded=[BrokerReadOnly]::QueryFullProcessImageName($handle,0,$name,[ref]$size)
  $qerror=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
  if($record.querySucceeded){$record.actualImagePath=$name.ToString()}else{$record.queryError=$qerror}
  [long]$created=0;[long]$exited=0;[long]$kernel=0;[long]$user=0
  $record.getTimesSucceeded=[BrokerReadOnly]::GetProcessTimes($handle,[ref]$created,[ref]$exited,[ref]$kernel,[ref]$user)
  $terror=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
  if($record.getTimesSucceeded){$record.heldCreationUtcTicks=[DateTime]::FromFileTimeUtc($created).Ticks.ToString()}else{$record.getTimesError=$terror}
  $record.second=Snapshot
  if($record.getTimesSucceeded){$ticks=[long]$record.heldCreationUtcTicks;$record.identityMatched=($first.parent.pid -eq $record.second.parent.pid -and $first.parent.ticks -eq $record.second.parent.ticks -and ($ticks-($ticks%10)) -eq [long]$first.parent.ticks)}
 }finally{$record.closeSucceeded=[BrokerReadOnly]::CloseHandle($handle)}
}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($record|ConvertTo-Json -Depth 10)+"`n")
$stream=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
[ordered]@{path=$out;sha256=(Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash.ToLowerInvariant();bytes=$bytes.Length;observation=$record}|ConvertTo-Json -Depth 12
