"""Query the exact SDK database in MSIDBOPEN_READONLY using system msi.dll.
No installation, action sequence, SDK binary, Office or COM is invoked.
V2 seals bounded failure diagnostics after independent handle-close attempts.
"""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib, json, os, subprocess, datetime as dt

here = Path(__file__).resolve().parent
cab = here / 'embedded_cabinet_00.cab'
dest = here / 'sdk_database_data_v2'
database = dest / 'vissdk.msi'
command = [r'C:\Windows\System32\expand.exe', '-F:vissdk.msi', str(cab), str(dest)]
sql = 'SELECT `File`, `FileName`, `FileSize`, `Sequence` FROM `File` ORDER BY `Sequence`'
api_specs = {
 'MsiOpenDatabaseW': ([W.LPCWSTR, C.c_void_p, C.POINTER(W.UINT)], W.UINT),
 'MsiDatabaseOpenViewW': ([W.UINT, W.LPCWSTR, C.POINTER(W.UINT)], W.UINT),
 'MsiViewExecute': ([W.UINT, W.UINT], W.UINT),
 'MsiViewFetch': ([W.UINT, C.POINTER(W.UINT)], W.UINT),
 'MsiRecordGetStringW': ([W.UINT, W.UINT, W.LPWSTR, C.POINTER(W.DWORD)], W.UINT),
 'MsiRecordGetInteger': ([W.UINT, W.UINT], C.c_int),
 'MsiCloseHandle': ([W.UINT], W.UINT)}

def write(name, raw):
    if not isinstance(raw, bytes) or len(raw) > 256 * 1024:
        raise ValueError('Report bound before CreateNew')
    p = here / name
    with p.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    return {'path': str(p), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def bounded_bytes(p, cap=20 * 1024 * 1024):
    size = p.stat().st_size
    if not 0 <= size <= cap:
        raise ValueError('Input size bound before read')
    with p.open('rb') as f:
        raw = f.read(cap + 1)
    if len(raw) != size or len(raw) > cap:
        raise ValueError('Actual input length changed or exceeds bound')
    return raw

def bind(p, cap=20 * 1024 * 1024):
    raw = bounded_bytes(p, cap)
    return {'path': str(p), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def error_data(exc):
    message = str(exc)
    return {'type': type(exc).__name__, 'message': message[:8192],
            'message_truncated': len(message) > 8192}

def require(code, where):
    if code != 0:
        raise RuntimeError(where + ' returned ' + str(code))

def text(record, field):
    buf = C.create_unicode_buffer(4096)
    length = W.DWORD(4095)
    require(msi.MsiRecordGetStringW(record, field, buf, C.byref(length)), 'MsiRecordGetStringW')
    if length.value > 4095:
        raise ValueError('String bound exceeded')
    return buf.value

def close_independently(handle, kind):
    if not handle.value:
        return
    result = {'kind': kind, 'handle': int(handle.value)}
    try:
        code = int(msi.MsiCloseHandle(handle))
        result['actual_returncode'] = code
        if code != 0:
            secondary_close_errors.append({'kind': kind, 'handle': int(handle.value),
                                           'actual_returncode': code})
    except Exception as exc:
        result['api_call_error'] = error_data(exc)
        secondary_close_errors.append({'kind': kind, 'handle': int(handle.value),
                                       'api_call_error': error_data(exc)})
    finally:
        closed.append(result)

db = W.UINT(0)
view = W.UINT(0)
msi = None
rows = []
closed = []
secondary_close_errors = []
post_read_errors = []
primary_error = None
primary_traceback = None
before = None
after = None
cab_binding = None
source_binding = None
expand_log = None
query_completed = False
rows_json_bytes = 0

try:
    source_binding = bind(Path(__file__).resolve(), 64 * 1024)
    cab_binding = bind(cab)
    if cab_binding['bytes'] != 13893516 or cab_binding['sha256'] != 'b1f80267f000c2ff7b8ddeea9c888381907c611640ee9497692e4df8cc1fcd3c':
        raise ValueError('Exact cabinet binding changed')
    if dest.exists():
        raise FileExistsError('Database data directory already exists; preserve it')
    dest.mkdir()
    child = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=45, check=False)
    expand_log = {'command': command, 'actual_returncode': child.returncode,
                  'stdout': write('msi_data_expand_v2.stdout.bin', child.stdout),
                  'stderr': write('msi_data_expand_v2.stderr.bin', child.stderr)}
    if child.returncode != 0:
        raise RuntimeError('Data extraction failed; preserve partial directory')
    if database.stat().st_size != 3063808 or [p.name for p in dest.iterdir()] != ['vissdk.msi']:
        raise ValueError('Unexpected database data extraction')
    before = bind(database)
    msi = C.WinDLL(r'C:\Windows\System32\msi.dll')
    for name, (args, result) in api_specs.items():
        fn = getattr(msi, name)
        fn.argtypes = args
        fn.restype = result
    try:
        # MSIDBOPEN_READONLY is the predefined null persistence-mode pointer.
        require(msi.MsiOpenDatabaseW(str(database), None, C.byref(db)), 'MsiOpenDatabaseW READONLY')
        require(msi.MsiDatabaseOpenViewW(db, sql, C.byref(view)), 'MsiDatabaseOpenViewW SELECT')
        require(msi.MsiViewExecute(view, 0), 'MsiViewExecute SELECT')
        while True:
            record = W.UINT(0)
            close_errors_before = len(secondary_close_errors)
            finished = False
            try:
                code = msi.MsiViewFetch(view, C.byref(record))
                if code == 259:
                    finished = True
                else:
                    require(code, 'MsiViewFetch')
                    row = {'file_key': text(record, 1), 'file_name_field': text(record, 2),
                           'uncompressed_bytes': msi.MsiRecordGetInteger(record, 3),
                           'sequence': msi.MsiRecordGetInteger(record, 4)}
                    row['installed_long_filename'] = row['file_name_field'].split('|')[-1]
                    if row['uncompressed_bytes'] < 0 or row['sequence'] <= 0 or len(rows) >= 1000:
                        raise ValueError('File table row/size/count bound')
                    row_bytes = len(json.dumps(row, ensure_ascii=False, indent=2).encode('utf8')) + 8
                    if rows_json_bytes + row_bytes > 96 * 1024:
                        raise ValueError('Cumulative row output bound before append')
                    rows_json_bytes += row_bytes
                    rows.append(row)
            finally:
                # Includes a nonzero partial record even if fetch or parsing failed.
                close_independently(record, 'record')
            if len(secondary_close_errors) != close_errors_before:
                raise RuntimeError('Record close failed; preserve actual secondary close evidence')
            if finished:
                break
        query_completed = True
    finally:
        # A view close result/error never prevents the database close attempt.
        try:
            close_independently(view, 'view')
        finally:
            close_independently(db, 'database')
except Exception as exc:
    primary_error = exc
    primary_traceback = exc.__traceback__
finally:
    # Preserve partial data, and independently attempt an after hash on ordinary failure.
    try:
        if database.exists():
            after = bind(database)
        if before is not None and before != after:
            post_read_errors.append({'type': 'DatabaseByteDifference',
                                     'message': 'Read-only database before/after descriptor differs'})
    except Exception as exc:
        post_read_errors.append(error_data(exc))

success = (primary_error is None and not secondary_close_errors and not post_read_errors
           and query_completed and before is not None and before == after)
schema_rows = [r for r in rows if r['installed_long_filename'].lower().endswith('.xsd')
               or 'schema' in r['installed_long_filename'].lower()]
doc_rows = [r for r in rows if r['installed_long_filename'].lower().endswith(('.chm', '.htm', '.html'))]
report = {
 'schema': 'official-sdk-readonly-file-table.v2',
 'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'completed' if success else 'failed',
 'source': source_binding, 'cabinet': cab_binding, 'database_before': before, 'database_after': after,
 'database_after_hash_scope': 'Attempted after ordinary success/failure if extracted file exists; null is not byte-equality evidence.',
 'expand': expand_log, 'native_system_dll': r'C:\Windows\System32\msi.dll',
 'database_mode': 'MSIDBOPEN_READONLY (null)', 'sql_only': sql,
 'query_completed': query_completed, 'all_file_rows' if success else 'partial_file_rows': rows,
 'file_row_count': len(rows), 'schema_named_rows': schema_rows, 'documentation_rows': doc_rows,
 'closed_native_database_handles': closed,
 'primary_error': error_data(primary_error) if primary_error is not None else None,
 'secondary_close_errors': secondary_close_errors, 'post_read_errors': post_read_errors,
 'installer_run': False, 'action_sequence_or_custom_action_run': False, 'Office_COM': False,
 'downloaded_code_executed': False, 'schema_validation': False,
 'scope_limit': 'File table names and sizes only. Partial rows are not a completed query. Absence of named XSD does not inspect compressed documentation contents or prove schemas never distributed. Hard host interruption cannot guarantee this diagnostic finally executes.'}
raw_report = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf8')
out = write('SDK_READONLY_FILE_TABLE_v2.json' if success else 'SDK_READONLY_FILE_TABLE_FAILURE_v2.json', raw_report)
print(json.dumps({'report': out, 'status': report['status'], 'file_row_count': len(rows),
                  'schema_named_rows': schema_rows, 'documentation_rows': doc_rows}, ensure_ascii=False))
if primary_error is not None:
    raise primary_error.with_traceback(primary_traceback)
if not success:
    raise RuntimeError('Read-only data query failed; preserved failure report: ' + out['path'])
