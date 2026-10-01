from pathlib import Path
import urllib.request,json,hashlib,datetime,concurrent.futures
D=Path(__file__).resolve().parent
sources=[
('camp.pdf','https://skyearth.org/publication/papers/2024_acvglmucampap.pdf'),
('dac.pdf','https://skyearth.org/publication/papers/2024_ecvglwdasc.pdf'),
('camp_pinned_readme.md','https://raw.githubusercontent.com/Mabel0403/CAMP/b04a9c856711770ed7a72ebf851838329c5e5b8e/README.md'),
('dac_pinned_readme.md','https://raw.githubusercontent.com/SummerpanKing/DAC/5612a79c3928d8a71939e4e761bb352f805cb51b/README.md')]
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def fetch(item):
 name,url=item;r={'name':name,'url':url,'start_utc':now(),'method':'Python urllib direct bounded request; public primary source'}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=35) as resp:
   b=resp.read(20*1024*1024+1); assert len(b)<=20*1024*1024
   r.update(status=resp.status,final_url=resp.url,content_type=resp.headers.get('Content-Type'))
  p=D/name
  with p.open('xb') as f: f.write(b)
  r.update(ok=True,path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
 except Exception as e: r.update(ok=False,error=type(e).__name__+': '+str(e))
 r['end_utc']=now(); return r
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: result=list(ex.map(fetch,sources))
p=D/'DIRECT_PRIMARY_ACCESS.json'
with p.open('x',encoding='utf-8') as f: json.dump({'accesses':result,'not_science_execution':True},f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False,indent=2))
