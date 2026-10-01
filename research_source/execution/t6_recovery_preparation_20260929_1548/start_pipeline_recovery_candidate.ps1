# PREPARATION ONLY. No release is produced by this package. No ValidateOnly mode.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Release,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ReleaseSha256,
    [Parameter(Mandatory=$true)][string]$RootAdoption,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$RootAdoptionSha256
)
$ErrorActionPreference='Stop'
$Candidate=Join-Path $PSScriptRoot 'pipeline_recovery_candidate.py'
$Python='C:\项目\.venvs\lgm-baselines\Scripts\python.exe'
foreach($Item in @($Candidate,$Release,$RootAdoption,$Python)) {
    if(!(Test-Path -LiteralPath $Item -PathType Leaf)){throw "Missing required file: $Item"}
    if($Item.Contains('"')){throw 'A quoted path is unsupported'}
}
if((Get-FileHash -LiteralPath $Release -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ReleaseSha256){throw 'Release SHA mismatch'}
if((Get-FileHash -LiteralPath $RootAdoption -Algorithm SHA256).Hash.ToLowerInvariant() -ne $RootAdoptionSha256){throw 'Root adoption SHA mismatch'}
$ReleaseRecord=Get-Content -LiteralPath $Release -Raw -Encoding UTF8 | ConvertFrom-Json
$AdoptionRecord=Get-Content -LiteralPath $RootAdoption -Raw -Encoding UTF8 | ConvertFrom-Json
$Manifest=Join-Path $PSScriptRoot 'SOURCE_MANIFEST.json'
function Assert-Binding($Row,[string]$ExactPath) {
    if($Row.path -cne $ExactPath){throw "Binding path mismatch: $ExactPath"}
    $Info=Get-Item -LiteralPath $ExactPath
    if($Info.Length -ne $Row.bytes -or (Get-FileHash -LiteralPath $ExactPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Row.sha256){throw "Binding bytes mismatch: $ExactPath"}
}
Assert-Binding $ReleaseRecord.root_adoption $RootAdoption
Assert-Binding $ReleaseRecord.source_manifest $Manifest
Assert-Binding $AdoptionRecord.source_manifest $Manifest
if($ReleaseRecord.schema -cne 't6-pipeline-recovery-release.v1' -or $ReleaseRecord.scope -cne 'pipeline_only_original_stage7' -or $ReleaseRecord.execute -ne $true){throw 'No pipeline-only execution release'}
if($AdoptionRecord.schema -cne 't6-pipeline-recovery-source-adoption.v1' -or $AdoptionRecord.approved_for_future_gated_execution -ne $true){throw 'No adopted source'}
$ManifestRecord=Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$CandidateMatched=$false
$EntryMatched=$false
foreach($Row in $ManifestRecord.candidate_files){
    Assert-Binding $Row $Row.path
    if($Row.path -ceq $Candidate){$CandidateMatched=$true}
    if($Row.path -ceq $PSCommandPath){$EntryMatched=$true}
}
if(!$CandidateMatched -or !$EntryMatched){throw 'Candidate or PowerShell entry not manifest-bound'}
# These are guardian-launch observations only, inside the preparation directory.
# They are NOT the one-use pipeline intent and do not mutate any scientific state.
$Observation=Join-Path (Join-Path $PSScriptRoot 'launcher_observations') ((Get-Date -Format 'yyyyMMdd_HHmmssfff')+'_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Observation | Out-Null
$Arguments=@('-B',('"'+$Candidate+'"'),'--release',('"'+$Release+'"'),'--release-sha256',$ReleaseSha256,'--root-adoption',('"'+$RootAdoption+'"'),'--root-adoption-sha256',$RootAdoptionSha256)
$Child=Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Observation 'guardian.stdout.log') -RedirectStandardError (Join-Path $Observation 'guardian.stderr.log')
$Row=[ordered]@{schema='t6-guardian-launch-observation.v1';observed_utc=[DateTime]::UtcNow.ToString('o');launcher_pid=$Child.Id;launcher_creation_utc=$Child.StartTime.ToUniversalTime().ToString('o');launcher_creation_utc_ticks=$Child.StartTime.ToUniversalTime().Ticks.ToString();candidate=$Candidate;release=$Release;release_sha256=$ReleaseSha256;root_adoption=$RootAdoption;root_adoption_sha256=$RootAdoptionSha256;scientific_launch_confirmed=$false;limits='Only the guardian launcher was started. Read its actual gated pipeline intent/launch/exit before claiming recovery.'}
[IO.File]::WriteAllText((Join-Path $Observation 'GUARDIAN_LAUNCH.json'),($Row|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
$Row|ConvertTo-Json -Depth 8
