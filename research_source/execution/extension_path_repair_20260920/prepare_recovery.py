from pathlib import Path
import hashlib, json, shutil, difflib
E = Path(__file__).resolve().parents[1]
D = E / 'extension_recovery_20260920_0119'
OLD = E / 'path_registry_recovery_20260918_1239'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def replace(s,a,b):
    assert s.count(a) == 1, a
    return s.replace(a,b)
def main():
    assert not D.exists()
    assert not (E/'extension_status.json').exists()
    D.mkdir(); (D/'controllers').mkdir(); (D/'previous_attempt').mkdir()
    pairs=[]
    for name in ['continue_formal_matrix.py','supervise_pipeline.py','supervise_extensions.py','supervise_latest_baselines.py','supervise_independent_comparisons.py']:
        pairs.append((E/name,D/'controllers'/name))
    for name in ['latest_baseline_status.json']:
        pairs.append((E/name,D/'controllers'/name))
    for name in ['extensions_launch.json','extensions_launch_intent.json','extensions.stdout.log','extensions.stderr.log','retired_extension_status.json']:
        pairs.append((OLD/name,D/'previous_attempt'/name))
    files=[]
    for src,dst in pairs:
        shutil.copy2(src,dst)
        assert sha(src)==sha(dst)
        files.append({'path':str(src),'backup':str(dst),'bytes':dst.stat().st_size,'sha256':sha(dst)})
    preserved=D/'PRESERVED_INCIDENT.json'
    preserved.write_text(json.dumps({'scope':'Failed extension admission before state creation; primary/pipeline remain live; no scientific task executed', 'files':files},ensure_ascii=False,indent=2),encoding='utf-8')
    source=E/'restart_after_path_registry_incident_20260918_v1.ps1'
    assert sha(source)=='1e98d56dfd96cfa43a2594777a78fadc6cb1d388172f309d1636348bc09c2b14'
    old=source.read_text(encoding='utf-8-sig')
    s=replace(old,"[ValidateSet('primary','pipeline','extensions','latest','independent')]","[ValidateSet('extensions','latest','independent')]")
    s=replace(s,"$incidentRoot = Join-Path $executionRoot 'path_registry_recovery_20260918_1239'","$incidentRoot = Join-Path $executionRoot 'extension_recovery_20260920_0119'")
    s=s.replace('4b5bc25f4e82ce156901b6ed6ba00fda894d77cb15128618a3a609588b2b9ff2',sha(preserved))
    s=replace(s,"extensions=@('extension_status.json','supervise_extensions.py'","extensions=@('extension_status.json','supervise_extensions_path_compat_v1.py'")
    anchor='$definitions = @{'
    checks="""$extensionManifestPath = Join-Path $executionRoot 'extension_path_repair_20260920/SOURCE_MANIFEST.json'
$extensionManifestSha = 'b985182c80577fa1a98a7511ce5de2a6a360f908ab063d6f6a0e5a2395be3640'
if ((Sha $extensionManifestPath) -ne $extensionManifestSha) { throw 'Extension alias manifest changed.' }
$extensionManifest = Get-Content -LiteralPath $extensionManifestPath -Raw | ConvertFrom-Json
foreach ($source in $extensionManifest.files) {
    if ((Sha $source.path) -ne $source.sha256 -or (Get-Item -LiteralPath $source.path).Length -ne $source.bytes) { throw 'Extension alias source changed.' }
}
"""
    s=replace(s,anchor,checks+'\n'+anchor)
    anchor="""} else {
    $old = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json"""
    retired=OLD/'retired_extension_status.json'
    stderr=OLD/'extensions.stderr.log'
    branch="""} elseif ($Stage -eq 'extensions') {
    if (Test-Path -LiteralPath $statePath) { throw 'An extension state appeared; inspect instead of recreating.' }
    $priorRetired = Join-Path $executionRoot 'path_registry_recovery_20260918_1239/retired_extension_status.json'
    $priorStderr = Join-Path $executionRoot 'path_registry_recovery_20260918_1239/extensions.stderr.log'
    if ((Sha $priorRetired) -ne 'RETIRED_SHA' -or (Sha $priorStderr) -ne 'STDERR_SHA') { throw 'Failed extension attempt changed.' }
    $prior = Get-Content -LiteralPath $priorRetired -Raw | ConvertFrom-Json
    if ($prior.status -ne 'preceding_pipeline_interrupted' -or @($prior.jobs).Count -ne 4) { throw 'Unexpected retired extension state.' }
    foreach ($job in $prior.jobs) {
        if ($job.status -ne 'pending') { throw 'Extension job previously executed.' }
        foreach ($field in @('pid','started_utc','finished_utc','exit_code','elapsed_seconds','active_stage','active_pid','child_pid')) {
            if ($null -ne $job.$field) { throw 'Extension job has execution evidence.' }
        }
    }
    $conflicting = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*supervise_extensions.py*' -or $_.CommandLine -like '*supervise_extensions_path_compat_v1.py*' })
    if ($conflicting.Count) { throw 'An extension controller still exists.' }
} else {
    $old = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json""".replace('RETIRED_SHA',sha(retired)).replace('STDERR_SHA',sha(stderr))
    s=replace(s,anchor,branch)
    s=replace(s,"$stdout = Join-Path $incidentRoot ($Stage+'.stdout.log')","if ($Stage -eq 'extensions') { $arguments += ' --manifest-sha256 '+$extensionManifestSha }\n$stdout = Join-Path $incidentRoot ($Stage+'.stdout.log')")
    s=replace(s,'if ($ValidateOnly) {',"if ($Stage -eq 'extensions' -and (Test-Path -LiteralPath $statePath)) { throw 'Extension state appeared during preflight.' }\nif ($ValidateOnly) {")
    target=E/'restart_extension_path_incident_20260920_v1.ps1'
    with target.open('x',encoding='utf-8-sig',newline='') as stream: stream.write(s)
    (D/'recovery.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile=source.name,tofile=target.name)),encoding='utf-8')
    result={'script':str(target),'sha256':sha(target),'preserved_sha256':sha(preserved),'actual_launch':False}
    (D/'PREPARATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__': main()
