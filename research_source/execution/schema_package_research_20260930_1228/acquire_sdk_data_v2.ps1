$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$pageUrl = 'https://www.microsoft.com/en-us/download/details.aspx?id=36825'
$packageUrl = 'https://download.microsoft.com/download/6/a/0/6a06bd3c-2f82-4e43-905e-2d8df5eabd81/VisioSDK64bit.exe'
function Write-NewBytes([string]$path, [byte[]]$data) {
    $stream = [System.IO.File]::Open($path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
    try { $stream.Write($data, 0, $data.Length); $stream.Flush($true) } finally { $stream.Dispose() }
    [ordered]@{ path=$path; bytes=$data.Length; sha256=[Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($data)).ToLowerInvariant() }
}
function Fetch-Bounded([string]$url, [int64]$limit) {
    $started = [DateTime]::UtcNow.ToString('o')
    $response = Invoke-WebRequest -Uri $url -TimeoutSec 45 -MaximumRedirection 2
    $final = $response.BaseResponse.RequestMessage.RequestUri
    if ($response.StatusCode -ne 200 -or $final.Scheme -ne 'https' -or $final.Host -notin @('www.microsoft.com','download.microsoft.com')) { throw 'Unexpected HTTP status or final host' }
    $length = $response.Headers['Content-Length']
    if ($length -and ([int64]$length -lt 0 -or [int64]$length -gt $limit)) { throw 'Content length outside bound' }
    if ($response.RawContentStream.Length -gt $limit) { throw 'Actual body outside bound' }
    $data = $response.RawContentStream.ToArray()
    [ordered]@{ data=$data; access=[ordered]@{ requested_url=$url; final_url=$final.AbsoluteUri; status=[int]$response.StatusCode; headers=$response.Headers; started_utc=$started; completed_utc=[DateTime]::UtcNow.ToString('o'); actual_bytes=$data.Length } }
}
$utf8 = [System.Text.UTF8Encoding]::new($false)
Write-NewBytes (Join-Path $here 'DATA_DOWNLOAD_MARKER_V2.json') ($utf8.GetBytes((@{ utc=[DateTime]::UtcNow.ToString('o'); scope='sdk_inert_bytes_only'; prior_python_leg='HTTP403 before page/package write; preserved; no retry of prior source' } | ConvertTo-Json))) | Out-Null
try {
    $page = Fetch-Bounded $pageUrl (2MB)
    if (-not $utf8.GetString($page.data).Contains($packageUrl)) { throw 'Exact package URL absent from freshly read official HTML' }
    $pageBinding = Write-NewBytes (Join-Path $here 'MICROSOFT_DOWNLOAD_PAGE_V2.html.txt') $page.data
    $package = Fetch-Bounded $packageUrl (20MB)
    if ($package.data.Length -lt 2 -or $package.data[0] -ne 77 -or $package.data[1] -ne 90) { throw 'Expected PE MZ data signature absent' }
    $packageBinding = Write-NewBytes (Join-Path $here 'VisioSDK64bit.exe.data') $package.data
    $sourceBytes = [System.IO.File]::ReadAllBytes($PSCommandPath)
    $report = [ordered]@{ schema='official-visio-sdk-inert-download.v2'; utc=[DateTime]::UtcNow.ToString('o'); page_http=$page.access; page=$pageBinding; package_http=$package.access; package=$packageBinding; source=@{path=$PSCommandPath;bytes=$sourceBytes.Length;sha256=[Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($sourceBytes)).ToLowerInvariant()}; source_leg='PowerShell read-only HTTP client after separate failed Python403 leg'; executed_downloaded_code=$false; installed=$false; COM=$false; scientific_execution=$false; schema_set_obtained=$false; full_xsd_validation_performed=$false }
    $binding = Write-NewBytes (Join-Path $here 'OFFICIAL_SDK_DATA_DOWNLOAD_V2.json') ($utf8.GetBytes(($report | ConvertTo-Json -Depth 12)))
    $binding | ConvertTo-Json -Compress
} catch {
    $failure = [ordered]@{ schema='official-sdk-data-access-failure.v1'; utc=[DateTime]::UtcNow.ToString('o'); error=$_.ToString(); position=$_.InvocationInfo.PositionMessage; package_executed=$false; installed=$false; schema_validation=$false }
    Write-NewBytes (Join-Path $here 'DATA_DOWNLOAD_FAILURE_V2.json') ($utf8.GetBytes(($failure | ConvertTo-Json -Depth 8))) | ConvertTo-Json -Compress
    throw
}
