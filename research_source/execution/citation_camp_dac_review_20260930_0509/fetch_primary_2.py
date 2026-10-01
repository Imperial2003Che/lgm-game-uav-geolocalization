from pathlib import Path
import urllib.request,json,datetime,hashlib
D=Path(__file__).resolve().parent
items=[('camp_train_university_pinned.py','https://raw.githubusercontent.com/Mabel0403/CAMP/b04a9c856711770ed7a72ebf851838329c5e5b8e/train_university.py'),('dac_train_university_pinned.py','https://raw.githubusercontent.com/SummerpanKing/DAC/5612a79c3928d8a71939e4e761bb352f805cb51b/train_university.py'),('author_publications.html','https://skyearth.org/publication/'),('camp_author_page.html','https://skyearth.org/team/members/wuqiong.html')]
results=[]
for name,url in items:
 r={'url':url,'name':name,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'urllib request; no execution of fetched code'}
 try:
  with urllib.request.urlopen(url,timeout=30) as x: b=x.read(4*1024*1024+1); assert len(b)<=4*1024*1024; r['status']=x.status
  with (D/name).open('xb') as f:f.write(b)
  r.update(ok=True,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
 except Exception as e:r.update(ok=False,error=repr(e))
 r['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();results.append(r)
with (D/'DIRECT_PRIMARY_ACCESS_2.json').open('x',encoding='utf-8') as f:json.dump(results,f,ensure_ascii=False,indent=2)
print(json.dumps(results,indent=2))
