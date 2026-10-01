"""Download exactly the official DAC U1652 ZIP member using verified ranges.

No torch import or model loading. Interrupted compressed/output parts are retained.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,struct,time,urllib.request,zlib
P=Path(__file__).resolve().parent
ROOT=P.parent
OUT=ROOT/'latest_author_checkpoints'
TARGET=OUT/'DAC_University_author_checkpoint.pth'
REPORT=OUT/'DAC_University_download.json'
MEMBER='pretrained_models/U1652/weights_end.pth'
RANGE_BYTES=8*1024*1024
CHUNK_BYTES=256*1024
def now():return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for data in iter(lambda:f.read(8*1024*1024),b''):h.update(data)
 return h.hexdigest()
def put(p,obj):
 temporary=p.with_suffix(p.suffix+'.writing')
 temporary.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 os.replace(temporary,p)
def main():
 directory=json.loads((P/'checkpoint_zip_directory.json').read_text(encoding='utf-8'))
 assert directory['status']=='directory_read'
 member=next(x for x in directory['members'] if x['name']==MEMBER)
 assert member['compression_method']==8 and not (member['general_flag']&1)
 if TARGET.exists() or REPORT.exists():raise RuntimeError('Existing DAC target/report preserved; inspect before starting another extraction.')
 OUT.mkdir(exist_ok=True)
 session=P/'downloads'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');session.mkdir(parents=True)
 compressed_path=session/'university_member.deflate.part';output_part=session/'DAC_University_author_checkpoint.pth.part'
 assert TARGET.resolve().parent==OUT.resolve() and output_part.resolve().is_relative_to(session.resolve())
 url=directory['url'];size=directory['archive_bytes_from_head']
 ledger={'status':'initializing','started_utc':now(),'url':url,'official_readme_url':'https://github.com/SummerpanKing/DAC/blob/5612a79c3928d8a71939e4e761bb352f805cb51b/README.md',
   'member':member,'archive_bytes':size,'central_directory_metadata_path':str(P/'checkpoint_zip_directory.json'),'central_directory_metadata_sha256':sha(P/'checkpoint_zip_directory.json'),
   'central_directory_sha256':directory['central_directory_sha256'],'extractor_path':str(Path(__file__).resolve()),'extractor_sha256':sha(__file__),
   'target_path':str(TARGET),'compressed_part_path':str(compressed_path),'output_part_path':str(output_part),'session_path':str(session),
   'range_size_bytes':RANGE_BYTES,'stream_read_bytes':CHUNK_BYTES,'ranges':[],'checkpoint_loaded':False,'gpu_executed':False,'checkpoint_bytes_transferred':0,'output_bytes':0,'metadata_bytes_transferred':0}
 put(REPORT,ledger)
 identity={}
 def save():ledger['updated_utc']=now();put(REPORT,ledger);put(session/'progress.json',ledger)
 def request_headers(response,expected_range=None):
  headers=response.headers
  if headers.get('Last-Modified')!=identity['last_modified']:raise RuntimeError('Remote archive Last-Modified changed or disappeared')
  current_etag=headers.get('ETag')
  if identity['etag'] is None and current_etag is not None:identity['etag']=current_etag
  elif identity['etag'] is not None and current_etag!=identity['etag']:raise RuntimeError('Remote archive ETag changed or disappeared')
  if expected_range:
   start,end=expected_range
   if response.status!=206 or headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':raise RuntimeError('HTTP Range was not honored exactly; body not read')
   length=headers.get('Content-Length')
   if length is not None and int(length)!=end-start+1:raise RuntimeError('Range Content-Length mismatch')
 def open_range(start,end):
  if start<0 or end>=size or end<start:raise ValueError('Invalid archive offsets')
  req=urllib.request.Request(url,headers={'User-Agent':'DAC-author-checkpoint-extraction','Accept-Encoding':'identity','Range':f'bytes={start}-{end}','If-Range':identity['etag'] or identity['last_modified']})
  response=urllib.request.urlopen(req,timeout=60)
  try:request_headers(response,(start,end))
  except BaseException:response.close();raise
  return response
 def metadata_range(start,end):
  if end-start+1>256*1024:raise ValueError('Metadata cap exceeded')
  with open_range(start,end) as response:
   raw=response.read(end-start+2)
   if len(raw)!=end-start+1:raise RuntimeError('Metadata range length mismatch')
   ledger['metadata_bytes_transferred']+=len(raw)
   return raw
 compressed_sha=hashlib.sha256();output_sha=hashlib.sha256();crc=0;decompressor=zlib.decompressobj(-15)
 try:
  req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'DAC-author-checkpoint-extraction','Accept-Encoding':'identity'})
  with urllib.request.urlopen(req,timeout=40) as response:
   if response.status!=200 or int(response.headers.get('Content-Length','-1'))!=size:raise RuntimeError('Archive size changed before extraction')
   identity.update(etag=response.headers.get('ETag'),last_modified=response.headers.get('Last-Modified'))
   if not identity['last_modified']:raise RuntimeError('No remote identity validator available')
   ledger['remote_identity']={**identity,'content_disposition':response.headers.get('Content-Disposition'),'content_type':response.headers.get('Content-Type')}
  cd=metadata_range(directory['central_directory_offset'],directory['central_directory_offset']+directory['central_directory_bytes']-1)
  if hashlib.sha256(cd).hexdigest()!=directory['central_directory_sha256']:raise RuntimeError('ZIP central directory changed')
  offset=member['local_header_offset'];header=metadata_range(offset,offset+29)
  h=struct.unpack('<4s5H3I2H',header)
  if h[0]!=b'PK\x03\x04' or h[3]!=member['compression_method']:raise RuntimeError('Local ZIP header mismatch')
  name_and_extra=metadata_range(offset+30,offset+30+h[9]+h[10]-1)
  if name_and_extra[:h[9]].decode('utf-8')!=MEMBER:raise RuntimeError('Unexpected local ZIP member name')
  start=offset+30+h[9]+h[10];end=start+member['compressed_bytes']-1
  ledger.update(status='downloading_member',compressed_data_start=start,compressed_data_end=end);save()
  with compressed_path.open('xb') as compressed,output_part.open('xb') as output:
   def write_output(data):
    nonlocal crc
    if ledger['output_bytes']+len(data)>member['uncompressed_bytes']:raise RuntimeError('Declared uncompressed member size exceeded')
    output.write(data);output_sha.update(data);crc=zlib.crc32(data,crc);ledger['output_bytes']+=len(data)
   for range_start in range(start,end+1,RANGE_BYTES):
    range_end=min(end,range_start+RANGE_BYTES-1)
    record={'start':range_start,'end':range_end,'started_utc':now(),'bytes_read':0,'status':'started'};ledger['ranges'].append(record);save()
    range_sha=hashlib.sha256()
    with open_range(range_start,range_end) as response:
     record['content_range']=response.headers.get('Content-Range');record['etag']=response.headers.get('ETag');record['last_modified']=response.headers.get('Last-Modified')
     remaining=range_end-range_start+1
     while remaining:
      data=response.read(min(CHUNK_BYTES,remaining))
      if not data:raise RuntimeError('Range stream ended prematurely')
      remaining-=len(data);record['bytes_read']+=len(data);ledger['checkpoint_bytes_transferred']+=len(data)
      compressed.write(data);compressed_sha.update(data);range_sha.update(data)
      pending=data
      while pending:
       decoded=decompressor.decompress(pending,CHUNK_BYTES*4);write_output(decoded);pending=decompressor.unconsumed_tail
     if response.read(1):raise RuntimeError('Range stream exceeded declared boundary')
    compressed.flush();output.flush();os.fsync(compressed.fileno());os.fsync(output.fileno())
    record.update(status='completed',sha256=range_sha.hexdigest(),completed_utc=now());save()
   write_output(decompressor.flush())
   output.flush();os.fsync(output.fileno())
  if not decompressor.eof or decompressor.unused_data:raise RuntimeError('Unexpected DEFLATE termination')
  if ledger['checkpoint_bytes_transferred']!=member['compressed_bytes'] or ledger['output_bytes']!=member['uncompressed_bytes']:raise RuntimeError('ZIP member byte count mismatch')
  if f'{crc&0xffffffff:08x}'!=member['crc32_hex']:raise RuntimeError('Uncompressed ZIP CRC32 mismatch')
  final_cd=metadata_range(directory['central_directory_offset'],directory['central_directory_offset']+directory['central_directory_bytes']-1)
  if hashlib.sha256(final_cd).hexdigest()!=directory['central_directory_sha256']:raise RuntimeError('ZIP directory changed during extraction')
  if sha(output_part)!=output_sha.hexdigest():raise RuntimeError('Final on-disk SHA mismatch')
  if TARGET.exists():raise RuntimeError('Target appeared during download; do not overwrite')
  os.replace(output_part,TARGET)
  ledger.update(status='completed_verified_not_loaded',finished_utc=now(),checkpoint_bytes=TARGET.stat().st_size,checkpoint_sha256=output_sha.hexdigest(),
                compressed_member_sha256=compressed_sha.hexdigest(),crc32_hex=f'{crc&0xffffffff:08x}',remote_identity_final=dict(identity))
  save();print(json.dumps({k:ledger[k] for k in ['status','target_path','checkpoint_bytes','checkpoint_sha256','checkpoint_bytes_transferred','metadata_bytes_transferred','crc32_hex']},ensure_ascii=False,indent=2))
 except BaseException as error:
  ledger.update(status='failed_partial_preserved',error_type=type(error).__name__,error=str(error));save();raise
if __name__=='__main__':main()
