"""Download an official SDK as inert data; inspect embedded cabinet headers only.

No downloaded executable, installer, Office, COM or scientific code is executed.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import struct
import urllib.request
import urllib.parse

HERE = Path(__file__).resolve().parent
PAGE = 'https://www.microsoft.com/en-us/download/details.aspx?id=36825'
URL = 'https://download.microsoft.com/download/6/a/0/6a06bd3c-2f82-4e43-905e-2d8df5eabd81/VisioSDK64bit.exe'
MAX_BYTES = 20 * 1024 * 1024

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def new_bytes(path, data):
    with path.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def fetch(url, limit):
    start = utc()
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=45) as response:
        final = response.geturl()
        parsed = urllib.parse.urlparse(final)
        if parsed.scheme != 'https' or parsed.hostname not in ('www.microsoft.com', 'download.microsoft.com'):
            raise ValueError('Unexpected final host: ' + final)
        if response.status != 200:
            raise ValueError('HTTP status: ' + str(response.status))
        length = response.headers.get('Content-Length')
        if length is not None and (not length.isdecimal() or int(length) > limit):
            raise ValueError('Invalid or oversized Content-Length')
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Bounded download rejected')
        return data, {'requested_url': url, 'final_url': final, 'status': response.status,
                      'headers': dict(response.headers.items()), 'started_utc': start,
                      'completed_utc': utc(), 'actual_bytes': len(data)}

def main():
    new_bytes(HERE / 'DATA_DOWNLOAD_MARKER.json', (json.dumps({'utc': utc(), 'scope': 'official_sdk_inert_data_only'}, indent=2) + '\n').encode())
    page, page_http = fetch(PAGE, 2 * 1024 * 1024)
    if URL.encode() not in page:
        raise ValueError('Exact package URL not present in freshly fetched official HTML')
    page_binding = new_bytes(HERE / 'MICROSOFT_DOWNLOAD_PAGE.html.txt', page)
    data, package_http = fetch(URL, MAX_BYTES)
    if not data.startswith(b'MZ'):
        raise ValueError('Expected PE container signature absent')
    package_binding = new_bytes(HERE / 'VisioSDK64bit.exe.data', data)
    cabinets = []
    search = 0
    while True:
        offset = data.find(b'MSCF', search)
        if offset < 0:
            break
        search = offset + 4
        if offset + 36 > len(data):
            continue
        reserved1, cb_cabinet, reserved2, coff_files, reserved3 = struct.unpack_from('<IIIII', data, offset + 4)
        minor, major, folders, files, flags, set_id, cab_index = struct.unpack_from('<BBHHHHH', data, offset + 24)
        plausible = (reserved1 == reserved2 == reserved3 == 0 and major == 1 and minor == 3
                     and 36 <= cb_cabinet <= MAX_BYTES and offset + cb_cabinet <= len(data)
                     and 36 <= coff_files < cb_cabinet and folders > 0 and files > 0)
        candidate = {'offset': offset, 'cb_cabinet': cb_cabinet, 'coff_files': coff_files,
                     'version_major': major, 'version_minor': minor, 'folders': folders,
                     'files': files, 'flags': flags, 'set_id': set_id, 'cabinet_index': cab_index,
                     'header_plausible_only': plausible}
        if plausible:
            candidate['extracted_data_binding'] = new_bytes(HERE / ('embedded_cabinet_%02d.cab' % len(cabinets)), data[offset:offset+cb_cabinet])
        cabinets.append(candidate)
    report = {'schema': 'official-visio-sdk-inert-download.v1', 'utc': utc(),
              'source': {'path': str(Path(__file__).resolve()), 'bytes': Path(__file__).stat().st_size,
                         'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
              'page_http': page_http, 'page': page_binding, 'package_http': package_http,
              'package': package_binding, 'cabinet_headers': cabinets,
              'notices': ['Downloaded package treated as inert bytes only; not run or installed.',
                          'CAB magic and plausible header do not establish payload identity or complete schemas.',
                          'No Visio/Office/COM/scientific import, native training probe, release, lock or state mutation.'],
              'schema_set_obtained': False, 'full_xsd_validation_performed': False}
    report_binding = new_bytes(HERE / 'OFFICIAL_SDK_DATA_DOWNLOAD.json', (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'report': report_binding, 'package': package_binding,
                      'plausible_cabinets': [c for c in cabinets if c['header_plausible_only']]}, ensure_ascii=False))

if __name__ == '__main__':
    main()
