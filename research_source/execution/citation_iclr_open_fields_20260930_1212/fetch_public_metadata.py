"""Read three public official metadata endpoints only; never science or manuscript edits."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import urllib.request,urllib.error,json,hashlib,os
HERE=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\citation_iclr_open_fields_20260930_1212')
URLS=[('adamw2019','https://api.openreview.net/notes?id=Bkg6RiCqY7'),('sgdr2017','https://api.openreview.net/notes?id=Skq89Scxx'),('mixedprecision2018','https://api.openreview.net/notes?id=r1gs9JgRZ')]
def one(pair):
 key,url=pair;r={'key':key,'requested_url':url,'started_utc':datetime.now(timezone.utc).isoformat(),'public_primary_metadata_only':True}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'LGM-citation-primary-metadata-review/1.0'})
  with urllib.request.urlopen(req,timeout=25) as h:
   raw=h.read(256*1024+1);r.update({'http_status':h.status,'final_url':h.geturl(),'content_type':h.headers.get('Content-Type')})
  if len(raw)>256*1024:raise RuntimeError('official metadata256KiB bound')
  r['received_bytes']=len(raw);r['received_sha256']=hashlib.sha256(raw).hexdigest()
  parsed=json.loads(raw)
  selected=[]
  for note in parsed.get('notes',[]):
   c=note.get('content',{})
   fields={k:c[k] for k in ('authors','venue','venueid','bibtex','_bibtex') if k in c}
   selected.append({'id':note.get('id'),'forum':note.get('forum'),'invitation':note.get('invitation'),'selected_fields':fields})
  r.update({'access_status':'direct_public_official_JSON_success','note_count':len(selected),'selected_notes':selected})
 except urllib.error.HTTPError as e:r.update({'access_status':'http_access_failed','http_status':e.code,'error':str(e)})
 except BaseException as e:r.update({'access_status':'metadata_access_failed','error':repr(e)})
 r['completed_utc']=datetime.now(timezone.utc).isoformat();return r
with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(one,URLS))
report={'schema':'iclr-three-public-primary-metadata-access.v1','scope':'Only three official OpenReview metadata public HTTP requests; author/venue/bibtex fields, no abstracts/formulas/science or manuscript changes','results':results,'method':'Installed ordinary Python standard-library urllib, no credentials or challenge interaction; direct statuses separate from web indexed snippets.'}
raw=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
if len(raw)>128*1024:raise RuntimeError('source access report cap beforeCreateNew')
p=HERE/'DIRECT_PUBLIC_METADATA_ACCESS.json'
with p.open('xb') as h:h.write(raw);h.flush();os.fsync(h.fileno())
print(json.dumps({'report':{'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'results':results},ensure_ascii=False))