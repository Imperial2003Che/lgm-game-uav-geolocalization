from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote
import json, hashlib

base=Path(__file__).resolve().parent
result=[]
for doi in ['10.1109/ICCV.2007.4408891','10.1214/aos/1176344552','10.2307/4615733']:
    url='https://api.crossref.org/works/'+quote(doi,safe='')
    item={'requested_doi':doi,'url':url,'start_utc':datetime.now(timezone.utc).isoformat(),'source_role':'official DOI registration agency, publisher-deposited metadata; not a full paper'}
    try:
        req=Request(url,headers={'User-Agent':'LGM-GAME-citation-audit/1.0','Accept':'application/json'})
        with urlopen(req,timeout=20) as f:
            body=f.read(2000001)
            if len(body)>2000000: raise ValueError('response too large')
            item.update(http_status=f.status,final_url=f.url,response_bytes=len(body),response_sha256=hashlib.sha256(body).hexdigest())
        data=json.loads(body)['message']
        selected={k:data.get(k) for k in ['DOI','title','author','publisher','container-title','page','volume','issue','published','published-print','created','deposited','URL','resource','link','type','source','member','prefix']}
        item.update(status='direct_success',selected_metadata=selected)
    except Exception as e:
        item.update(status='direct_failure',error=type(e).__name__+': '+str(e))
    item['end_utc']=datetime.now(timezone.utc).isoformat()
    result.append(item)
out=base/'CROSSREF_DIRECT_ACCESS.json'
with out.open('x',encoding='utf-8',newline='\n') as f:
    json.dump({'accesses':result,'note':'Only bibliographic/registration metadata was retained; no article bodies or nonpublic endpoints.'},f,ensure_ascii=False,indent=2)
    f.write('\n')
print(json.dumps(result,ensure_ascii=False))
