"""Read bounded ZIP directory metadata via HTTP Range, never a whole archive."""
from pathlib import Path
import hashlib,json,re,struct,urllib.request
P=Path(__file__).resolve().parent
URL='https://drive.usercontent.google.com/download?id=140xgtckQkRwqgszD1wWiDH6lV7xufa8r&export=download&authuser=0&confirm=t'
SIZE=1779419725
CAP=256*1024
requests=[]
def read_range(start,end):
 if start<0 or end>=SIZE or end<start or end-start+1>CAP:raise ValueError('Unbounded metadata request')
 req=urllib.request.Request(URL,headers={'User-Agent':'DAC-metadata-audit','Range':f'bytes={start}-{end}','Accept-Encoding':'identity'})
 with urllib.request.urlopen(req,timeout=40) as response:
  record={'requested_start':start,'requested_end':end,'status':response.status,'content_range':response.headers.get('Content-Range'),'bytes_read':0}
  requests.append(record)
  expected=f'bytes {start}-{end}/{SIZE}'
  if response.status!=206 or response.headers.get('Content-Range')!=expected:
   raise RuntimeError('Range not exactly honored; response body was not read.')
  raw=response.read(end-start+2);record['bytes_read']=len(raw)
  if len(raw)!=end-start+1:raise RuntimeError('Unexpected Range response length')
  record['sha256']=hashlib.sha256(raw).hexdigest()
  return raw
def main():
 report={'url':URL,'archive_bytes_from_head':SIZE,'status':'pending','body_scope':'ZIP end record and central directory only','checkpoint_loaded':False,'requests':requests}
 try:
  tail=read_range(SIZE-22,SIZE-1)
  if tail[:4]!=b'PK\x05\x06':tail=read_range(SIZE-65557,SIZE-1)
  at=tail.rfind(b'PK\x05\x06')
  if at<0:raise RuntimeError('ZIP end record not found')
  _,disk,cd_disk,disk_entries,total_entries,cd_bytes,cd_offset,comment_bytes=struct.unpack_from('<4s4H2IH',tail,at)
  if disk or cd_disk or total_entries!=disk_entries or total_entries==65535 or cd_offset==0xffffffff:raise RuntimeError('Multi-disk/ZIP64 archive needs separate metadata handling')
  directory=read_range(cd_offset,cd_offset+cd_bytes-1)
  (P/'checkpoint_zip_central_directory.bin').write_bytes(directory)
  offset=0;members=[]
  while offset<len(directory):
   fields=struct.unpack_from('<4s6H3I5H2I',directory,offset)
   if fields[0]!=b'PK\x01\x02':raise RuntimeError('Unexpected central-directory signature')
   name_raw=directory[offset+46:offset+46+fields[10]]
   name=name_raw.decode('utf-8' if fields[3]&0x800 else 'cp437')
   members.append({'name':name,'compression_method':fields[4],'general_flag':fields[3],'crc32_hex':f'{fields[7]:08x}','compressed_bytes':fields[8],'uncompressed_bytes':fields[9],'local_header_offset':fields[16]})
   offset+=46+fields[10]+fields[11]+fields[12]
  assert len(members)==total_entries
  report.update(status='directory_read',central_directory_bytes=cd_bytes,central_directory_offset=cd_offset,members=members,metadata_bytes_read=sum(x['bytes_read'] for x in requests),central_directory_sha256=hashlib.sha256(directory).hexdigest())
 except Exception as exc:report.update(status='range_unavailable_or_unsupported',error=str(exc),metadata_bytes_read=sum(x['bytes_read'] for x in requests))
 (P/'checkpoint_zip_directory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
