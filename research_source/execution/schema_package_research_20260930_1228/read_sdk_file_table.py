"""Query the exact SDK database in MSIDBOPEN_READONLY using system msi.dll.
No installation, action sequence, SDK binary, Office or COM is invoked.
"""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib, json, os, subprocess, datetime as dt
here=Path(__file__).resolve().parent
cab=here/'embedded_cabinet_00.cab'
if cab.stat().st_size != 13893516 or hashlib.sha256(cab.read_bytes()).hexdigest() != 'b1f80267f000c2ff7b8ddeea9c888381907c611640ee9497692e4df8cc1fcd3c':
    raise ValueError('Exact cabinet binding changed')
dest=here/'sdk_database_data'
if dest.exists():
    raise FileExistsError('Database data directory already exists; preserve it')
dest.mkdir()
def write(name,raw):
    if len(raw)>256*1024:
        raise ValueError('Report bound before CreateNew')
    p=here/name
    with p.open('xb') as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
    return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def bind(p,cap=20*1024*1024):
    if p.stat().st_size>cap:
        raise ValueError('Input bound')
    raw=p.read_bytes()
    return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
command=[r'C:\Windows\System32\expand.exe','-F:vissdk.msi',str(cab),str(dest)]
child=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45,check=False)
expand_log={'command':command,'actual_returncode':child.returncode,
            'stdout':write('msi_data_expand.stdout.bin',child.stdout),
            'stderr':write('msi_data_expand.stderr.bin',child.stderr)}
if child.returncode!=0:
    raise RuntimeError('Data extraction failed; preserve partial directory')
database=dest/'vissdk.msi'
if database.stat().st_size != 3063808 or [p.name for p in dest.iterdir()]!=['vissdk.msi']:
    raise ValueError('Unexpected database data extraction')
before=bind(database)
msi=C.WinDLL(r'C:\Windows\System32\msi.dll')
api_specs={
 'MsiOpenDatabaseW':([W.LPCWSTR,C.c_void_p,C.POINTER(W.UINT)],W.UINT),
 'MsiDatabaseOpenViewW':([W.UINT,W.LPCWSTR,C.POINTER(W.UINT)],W.UINT),
 'MsiViewExecute':([W.UINT,W.UINT],W.UINT),
 'MsiViewFetch':([W.UINT,C.POINTER(W.UINT)],W.UINT),
 'MsiRecordGetStringW':([W.UINT,W.UINT,W.LPWSTR,C.POINTER(W.DWORD)],W.UINT),
 'MsiRecordGetInteger':([W.UINT,W.UINT],C.c_int),
 'MsiCloseHandle':([W.UINT],W.UINT)}
for name,(args,result) in api_specs.items():
    fn=getattr(msi,name);fn.argtypes=args;fn.restype=result
def require(code,where):
    if code!=0:
        raise RuntimeError(where+' returned '+str(code))
def text(record,field):
    buf=C.create_unicode_buffer(4096);length=W.DWORD(4095)
    require(msi.MsiRecordGetStringW(record,field,buf,C.byref(length)),'MsiRecordGetStringW')
    if length.value>4095:
        raise ValueError('String bound exceeded')
    return buf.value
db=W.UINT(0);view=W.UINT(0)
rows=[];closed=[]
sql='SELECT `File`, `FileName`, `FileSize`, `Sequence` FROM `File` ORDER BY `Sequence`'
try:
    # MSIDBOPEN_READONLY is the predefined null persistence-mode pointer.
    require(msi.MsiOpenDatabaseW(str(database),None,C.byref(db)),'MsiOpenDatabaseW READONLY')
    require(msi.MsiDatabaseOpenViewW(db,sql,C.byref(view)),'MsiDatabaseOpenViewW SELECT')
    require(msi.MsiViewExecute(view,0),'MsiViewExecute SELECT')
    while True:
        record=W.UINT(0)
        code=msi.MsiViewFetch(view,C.byref(record))
        if code==259:
            break
        require(code,'MsiViewFetch')
        try:
            row={'file_key':text(record,1),'file_name_field':text(record,2),
                 'uncompressed_bytes':msi.MsiRecordGetInteger(record,3),
                 'sequence':msi.MsiRecordGetInteger(record,4)}
            row['installed_long_filename']=row['file_name_field'].split('|')[-1]
            if row['uncompressed_bytes']<0 or row['sequence']<=0 or len(rows)>=1000:
                raise ValueError('File table row/size/count bound')
            rows.append(row)
        finally:
            code=msi.MsiCloseHandle(record);closed.append({'kind':'record','actual_returncode':code})
            require(code,'MsiCloseHandle record')
finally:
    if view.value:
        closed.append({'kind':'view','actual_returncode':msi.MsiCloseHandle(view)})
    if db.value:
        closed.append({'kind':'database','actual_returncode':msi.MsiCloseHandle(db)})
after=bind(database)
if before!=after or any(x['actual_returncode']!=0 for x in closed):
    raise ValueError('Read-only database changed or close failed')
schema_rows=[r for r in rows if r['installed_long_filename'].lower().endswith('.xsd') or 'schema' in r['installed_long_filename'].lower()]
doc_rows=[r for r in rows if r['installed_long_filename'].lower().endswith(('.chm','.htm','.html'))]
report={'schema':'official-sdk-readonly-file-table.v1','utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'source':bind(Path(__file__).resolve()),'database_before':before,'database_after':after,'expand':expand_log,
        'native_system_dll':r'C:\Windows\System32\msi.dll','database_mode':'MSIDBOPEN_READONLY (null)',
        'sql_only':sql,'all_file_rows':rows,'file_row_count':len(rows),'schema_named_rows':schema_rows,
        'documentation_rows':doc_rows,'closed_native_database_handles':closed,
        'installer_run':False,'action_sequence_or_custom_action_run':False,'Office_COM':False,
        'downloaded_code_executed':False,'schema_validation':False,
        'scope_limit':'File table names and sizes only; absence of named XSD does not inspect compressed documentation contents or prove schemas never distributed.'}
out=write('SDK_READONLY_FILE_TABLE.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
print(json.dumps({'report':out,'file_row_count':len(rows),'schema_named_rows':schema_rows,'documentation_rows':doc_rows},ensure_ascii=False))
