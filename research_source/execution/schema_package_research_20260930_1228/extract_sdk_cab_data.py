"""Read the five CAB entries, then expand three inert data payloads with Windows expand.
Never executes EXE, MSI, DLL, SDK tools, Office or COM.
"""
from pathlib import Path, PureWindowsPath
import struct, hashlib, json, os, subprocess, datetime as dt
here = Path(__file__).resolve().parent
cab = here / 'embedded_cabinet_00.cab'
if cab.stat().st_size != 13893516:
    raise ValueError('Cabinet size changed')
data = cab.read_bytes()
if hashlib.sha256(data).hexdigest() != 'b1f80267f000c2ff7b8ddeea9c888381907c611640ee9497692e4df8cc1fcd3c':
    raise ValueError('Cabinet bytes changed')
if data[:4] != b'MSCF' or struct.unpack_from('<H',data,30)[0] != 0:
    raise ValueError('CAB header or unsupported flags')
file_count = struct.unpack_from('<H',data,28)[0]
offset = struct.unpack_from('<I',data,16)[0]
entries = []
for _ in range(file_count):
    if offset + 16 > len(data):
        raise ValueError('Truncated file table')
    size, folder_offset, folder_index, date, time, attribs = struct.unpack_from('<IIHHHH',data,offset)
    start = offset + 16
    end = data.find(b'\0',start,start+512)
    if end < 0:
        raise ValueError('CAB name exceeds bound')
    name = data[start:end].decode('utf8' if attribs & 0x80 else 'cp1252')
    parsed = PureWindowsPath(name)
    if parsed.name != name or parsed.is_absolute() or len(parsed.parts) != 1 or name in ('.','..') or size > 20*1024*1024:
        raise ValueError('Unsafe or oversized CAB member')
    entries.append({'name':name,'uncompressed_bytes':size,'folder_offset':folder_offset,'folder_index':folder_index,'attributes':attribs})
    offset = end + 1
if [e['name'] for e in entries] != ['EULA','readme.htm','vissdk.cab','vissdk.msi','files15.cat']:
    raise ValueError('Unexpected cabinet member list')
destination = here / 'sdk_payload_data'
if destination.exists():
    raise FileExistsError('Data extraction directory already exists; preserve it')
destination.mkdir()
def write(path,payload):
    with path.open('xb') as f:
        f.write(payload); f.flush(); os.fsync(f.fileno())
    return {'path':str(path),'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
def binding(path):
    size=path.stat().st_size
    if size>20*1024*1024:
        raise ValueError('Extracted data exceeds bound')
    body=path.read_bytes()
    return {'path':str(path),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
results=[]
for selected in ('vissdk.cab','EULA','readme.htm'):
    command=[r'C:\Windows\System32\expand.exe','-F:'+selected,str(cab),str(destination)]
    started=dt.datetime.now(dt.timezone.utc).isoformat()
    child=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=45)
    std_out=write(here/(selected.replace('.','_')+'_expand.stdout.bin'),child.stdout)
    std_err=write(here/(selected.replace('.','_')+'_expand.stderr.bin'),child.stderr)
    result={'command':command,'started_utc':started,'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'actual_subprocess_returncode':child.returncode,'stdout':std_out,'stderr':std_err,
            'exit_scope':'ordinary system expand subprocess return; not held scientific/interpreter evidence'}
    results.append(result)
    if child.returncode != 0:
        write(here/'SDK_DATA_EXPAND_FAILURE.json',(json.dumps({'entries':entries,'results':results},ensure_ascii=False,indent=2)+'\n').encode())
        raise RuntimeError('expand failed; preserve partial directory')
    output=destination/selected
    member=next(e for e in entries if e['name']==selected)
    if output.stat().st_size != member['uncompressed_bytes']:
        raise ValueError('Expanded member size differs from CAB table')
    result['data_payload']=binding(output)
if sorted(p.name for p in destination.iterdir()) != ['EULA','readme.htm','vissdk.cab']:
    raise ValueError('Unexpected files in extraction directory')
report={'schema':'official-sdk-cab-inert-payload-extraction.v1','utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'source':binding(Path(__file__).resolve()),'cabinet':binding(cab),'all_five_header_entries':entries,
        'selected_payloads':results,'downloaded_code_executed':False,'installer_run':False,'MSI_selected':False,
        'Office_COM':False,'scientific_execution':False,'schema_validation':False,
        'scope':'CAB table parsing and ordinary Windows expand of exact three data members into a new directory only.'}
out=write(here/'SDK_INERT_PAYLOAD_EXTRACTION.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
print(json.dumps({'report':out,'payloads':[r['data_payload'] for r in results]},ensure_ascii=False))
