"""Extract one exact official documentation member as inert data; never open CHM UI."""
from pathlib import Path
import datetime as dt, hashlib, json, os, subprocess

here = Path(__file__).resolve().parent
cab = here / 'sdk_payload_data' / 'vissdk.cab'
dest = here / 'sdk_chm_data'

def bind(p, cap=20*1024*1024):
    size = p.stat().st_size
    if not 0 <= size <= cap:
        raise ValueError('Input size bound')
    with p.open('rb') as f:
        raw = f.read(cap+1)
    if len(raw) != size or len(raw) > cap:
        raise ValueError('Actual input length bound')
    return {'path': str(p), 'bytes': size, 'sha256': hashlib.sha256(raw).hexdigest()}

def write(name, raw):
    if len(raw) > 64*1024:
        raise ValueError('Report bound')
    p = here / name
    with p.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    return {'path': str(p), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

report = {'schema': 'official-sdk-single-inert-chm-extraction.v1',
          'source': bind(Path(__file__).resolve(), 64*1024),
          'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
          'downloaded_code_executed': False, 'CHM_UI_opened': False,
          'installer_or_COM': False, 'scientific_execution': False,
          'schema_validation': False, 'status': 'incomplete'}
primary = None
try:
    report['cabinet'] = bind(cab)
    if report['cabinet']['bytes'] != 13365839 or report['cabinet']['sha256'] != 'e2b013e7375cfe4e668af792630e07008c92615be984c34b4e767b6b2cad328b':
        raise ValueError('Exact documentation source binding')
    if dest.exists():
        raise FileExistsError('Preserve existing documentation directory; no replay')
    dest.mkdir()
    cmd = [r'C:\Windows\System32\expand.exe', '-F:VISSDK.CHM', str(cab), str(dest)]
    child = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=45, check=False)
    report['expand'] = {'command': cmd, 'actual_subprocess_returncode': child.returncode,
                        'stdout': write('chm_data_expand.stdout.bin', child.stdout),
                        'stderr': write('chm_data_expand.stderr.bin', child.stderr),
                        'exit_scope': 'ordinary system expand return; no held scientific process evidence'}
    if child.returncode != 0:
        raise RuntimeError('Data extraction failed; preserve partial directory')
    if [p.name.upper() for p in dest.iterdir()] != ['VISSDK.CHM']:
        raise ValueError('Unexpected extracted documentation member')
    member = next(dest.iterdir())
    report['documentation_data'] = bind(member)
    if report['documentation_data']['bytes'] != 6764354:
        raise ValueError('Documentation length differs from independently saved CAB and File table')
    report['status'] = 'completed'
except Exception as exc:
    primary = exc
    report['error'] = {'type': type(exc).__name__, 'message': str(exc)[:8192]}
    report['status'] = 'failed'
report['completed_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
report['scope'] = 'One documentation data member extracted; contents and complete XSD availability remain unverified.'
output = write('SDK_SINGLE_CHM_DATA_EXTRACTION.json' if primary is None else 'SDK_SINGLE_CHM_DATA_EXTRACTION_FAILURE.json',
               (json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode('utf8'))
print(json.dumps(output, ensure_ascii=False))
if primary is not None:
    raise primary
