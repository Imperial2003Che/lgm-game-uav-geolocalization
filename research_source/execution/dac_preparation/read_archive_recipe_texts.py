"""Extract only small author recipe/log texts using verified HTTP Range."""
from pathlib import Path
import hashlib,json,struct,zlib,sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
from read_remote_zip_directory import read_range,requests
def main():
 archive=json.loads((P/'checkpoint_zip_directory.json').read_text(encoding='utf-8'))
 destination=P/'official_archive_metadata';destination.mkdir(exist_ok=True)
 extracted=[]
 for member in archive['members']:
  if not member['name'].endswith(('/train.py','/log.txt')):continue
  assert member['uncompressed_bytes']<=64*1024 and member['compressed_bytes']<=32*1024
  offset=member['local_header_offset'];header=read_range(offset,offset+29)
  local=struct.unpack('<4s5H3I2H',header)
  assert local[0]==b'PK\x03\x04' and local[3]==member['compression_method']
  start=offset+30+local[9]+local[10];end=start+member['compressed_bytes']-1
  raw=read_range(start,end)
  text=zlib.decompress(raw,-15) if member['compression_method']==8 else raw
  assert len(text)==member['uncompressed_bytes']
  assert f'{zlib.crc32(text)&0xffffffff:08x}'==member['crc32_hex']
  name=member['name'].replace('/','__');path=destination/name
  assert path.resolve().is_relative_to(destination.resolve())
  path.write_bytes(text)
  extracted.append({**member,'local_path':str(path),'compressed_data_start':start,'compressed_data_end':end,'sha256':hashlib.sha256(text).hexdigest()})
 report={'status':'text_metadata_extracted','archive_source':archive['url'],'checkpoint_bodies_downloaded':False,'checkpoint_loaded':False,
         'members':extracted,'requests':requests,'metadata_bytes_read':sum(x['bytes_read'] for x in requests)}
 (P/'archive_recipe_texts.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 for member in extracted:
  content=Path(member['local_path']).read_text(encoding='utf-8')
  if member['name'].endswith('log.txt'):print(member['name']+'\n'+content)
  else:
   print(member['name'])
   print('\n'.join(f'{n}: {line}' for n,line in enumerate(content.splitlines(),1) if any(k in line for k in ["epochs:","epochs =","epochs =","epochs =","epochs: ","batch_size",'warmup_epochs','seed:','nclasses','weight_dsa','weight_cls'])))
 print(json.dumps({'status':report['status'],'members_count':len(extracted),'metadata_bytes_read':report['metadata_bytes_read']},ensure_ascii=False))
if __name__=='__main__':main()
