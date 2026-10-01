from pathlib import Path
import hashlib, json, difflib, os
here = Path(__file__).resolve().parent
prior = here / 'acquire_sdk_data_v2.ps1'
old = prior.read_bytes()
needle = b"    $length = $response.Headers['Content-Length']\n    if ($length -and ([int64]$length -lt 0 -or [int64]$length -gt $limit)) { throw 'Content length outside bound' }"
replacement = b"    $lengthValues = @($response.Headers['Content-Length'] | Where-Object { $null -ne $_ })\n    if ($lengthValues.Count -gt 1) { throw 'Multiple Content-Length values rejected' }\n    [int64]$declaredLength = 0\n    if ($lengthValues.Count -eq 1 -and (-not [int64]::TryParse([string]$lengthValues[0], [ref]$declaredLength) -or $declaredLength -lt 0 -or $declaredLength -gt $limit)) { throw 'Content length outside bound' }"
if old.count(needle) != 1:
    raise ValueError('Exact delta anchor not unique')
new = old.replace(needle, replacement)
for before, after in [(b'DATA_DOWNLOAD_MARKER_V2', b'DATA_DOWNLOAD_MARKER_V3'),
                      (b'MICROSOFT_DOWNLOAD_PAGE_V2', b'MICROSOFT_DOWNLOAD_PAGE_V3'),
                      (b'OFFICIAL_SDK_DATA_DOWNLOAD_V2', b'OFFICIAL_SDK_DATA_DOWNLOAD_V3'),
                      (b'DATA_DOWNLOAD_FAILURE_V2', b'DATA_DOWNLOAD_FAILURE_V3'),
                      (b'official-visio-sdk-inert-download.v2', b'official-visio-sdk-inert-download.v3'),
                      (b'source_leg=\'PowerShell read-only HTTP client after separate failed Python403 leg\'', b'source_leg=\'PowerShell read-only HTTP after Python403 and pre-body header type rejection in v2\'')]:
    if new.count(before) != 1:
        raise ValueError('Delta anchor not unique: ' + repr(before))
    new = new.replace(before, after)
diff = ''.join(difflib.unified_diff(old.decode().splitlines(keepends=True), new.decode().splitlines(keepends=True), fromfile='acquire_sdk_data_v2.ps1', tofile='acquire_sdk_data_v3.ps1')).encode()
def write(path, data):
    with path.open('xb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
bindings = [write(here / 'acquire_sdk_data_v3.ps1', new), write(here / 'DOWNLOAD_V3_DELTA.patch', diff)]
print(json.dumps({'derived': bindings}, ensure_ascii=False))
