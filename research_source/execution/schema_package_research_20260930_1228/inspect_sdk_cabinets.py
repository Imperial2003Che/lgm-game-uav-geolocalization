from pathlib import Path
import hashlib, json, struct, datetime as dt, os
here = Path(__file__).resolve().parent
report_path = here / 'OFFICIAL_SDK_DATA_DOWNLOAD_V3.json'
report_bytes = report_path.read_bytes()
if len(report_bytes) != 4484 or hashlib.sha256(report_bytes).hexdigest() != '2bd2a0cc9e277698075adf6e68d4f766bb320ec98b43cc5c67dd9be786879b3e':
    raise ValueError('Download report binding changed')
download = json.loads(report_bytes)
package_path = Path(download['package']['path'])
if package_path.parent != here or package_path.name != 'VisioSDK64bit.exe.data':
    raise ValueError('Unexpected inert package path')
if package_path.stat().st_size != download['package']['bytes'] or package_path.stat().st_size > 20 * 1024 * 1024:
    raise ValueError('Package size rejected')
data = package_path.read_bytes()
if hashlib.sha256(data).hexdigest() != download['package']['sha256']:
    raise ValueError('Package bytes changed')
def write(name, payload):
    path = here / name
    with path.open('xb') as f:
        f.write(payload); f.flush(); os.fsync(f.fileno())
    return {'path': str(path), 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
candidates = []
search = 0
while True:
    offset = data.find(b'MSCF', search)
    if offset < 0:
        break
    search = offset + 4
    if offset + 36 > len(data):
        continue
    reserved1, size, reserved2, coff_files, reserved3 = struct.unpack_from('<IIIII', data, offset + 4)
    minor, major, folders, files, flags, set_id, cab_index = struct.unpack_from('<BBHHHHH', data, offset + 24)
    plausible = (reserved1 == reserved2 == reserved3 == 0 and (major,minor) == (1,3)
                 and 36 <= size <= 20 * 1024 * 1024 and offset + size <= len(data)
                 and 36 <= coff_files < size and folders > 0 and files > 0 and flags <= 7)
    candidate = {'offset':offset, 'bytes_header':size, 'coff_files':coff_files,
                 'folders':folders, 'files':files, 'flags':flags, 'set_id':set_id,
                 'cabinet_index':cab_index, 'header_plausible_only':plausible}
    if plausible:
        candidate['cabinet'] = write('embedded_cabinet_%02d.cab' % len(candidates), data[offset:offset+size])
    candidates.append(candidate)
pe_offset = struct.unpack_from('<I', data, 60)[0]
pe_signature = data[pe_offset:pe_offset+4].hex() if 0 <= pe_offset <= len(data)-4 else None
ole_offsets = []
cursor = 0
while True:
    cursor = data.find(bytes.fromhex('d0cf11e0a1b11ae1'), cursor)
    if cursor < 0:
        break
    ole_offsets.append(cursor); cursor += 8
result = {'schema':'official-sdk-inert-container-inspection.v1', 'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
          'source':{'path':str(Path(__file__).resolve()),'bytes':Path(__file__).stat().st_size,'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
          'download_report':{'path':str(report_path),'bytes':len(report_bytes),'sha256':hashlib.sha256(report_bytes).hexdigest()},
          'package':download['package'], 'pe_offset':pe_offset,'pe_signature_hex':pe_signature,
          'cabinet_candidates':candidates,'ole_magic_offsets_only':ole_offsets,
          'downloaded_code_executed':False,'installed':False,'COM':False,'schema_set_obtained':False,'schema_validation':False,
          'limit':'Byte carving of plausible CAB headers only; no decompression, installer execution, payload identity or complete schema claim.'}
binding = write('SDK_CABINET_HEADER_INSPECTION.json', (json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
print(json.dumps({'report':binding,'cabinet_candidates':candidates,'ole_magic_offsets':ole_offsets},ensure_ascii=False))
