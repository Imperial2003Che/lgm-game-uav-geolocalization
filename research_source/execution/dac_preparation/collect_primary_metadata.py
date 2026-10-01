"""Bounded first-source metadata requests; never downloads a checkpoint body."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,urllib.request,urllib.error,html
P=Path(__file__).resolve().parent
CAP=2*1024*1024
def put(name,obj):
 path=P/name;path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return path
def get_json(label,url):
 request=urllib.request.Request(url,headers={'User-Agent':'DAC-reproduction-audit','Accept':'application/vnd.github+json'})
 with urllib.request.urlopen(request,timeout=35) as response:
  raw=response.read(CAP+1)
  if len(raw)>CAP:raise RuntimeError('Metadata response exceeds cap')
  obj=json.loads(raw)
  record={'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'response_sha256':hashlib.sha256(raw).hexdigest(),'body':obj}
  put(label+'.json',record)
  return obj
def main():
 summary={}
 for label,url in [('issue5','https://api.github.com/repos/SummerpanKing/DAC/issues/5'),
   ('issue5_comments','https://api.github.com/repos/SummerpanKing/DAC/issues/5/comments?per_page=100'),
   ('repository','https://api.github.com/repos/SummerpanKing/DAC'),
   ('head_commit','https://api.github.com/repos/SummerpanKing/DAC/commits/main')]:
  try:
   obj=get_json(label,url)
   if label=='issue5':summary[label]={'title':obj['title'],'question':obj['body'],'url':obj['html_url']}
   elif label=='issue5_comments':summary[label]=[{'id':x['id'],'author':x['user']['login'],'association':x['author_association'],'body':x['body'],'created_at':x['created_at'],'url':x['html_url']} for x in obj if x['author_association']=='OWNER']
   elif label=='repository':summary[label]={'updated_at':obj['updated_at'],'pushed_at':obj['pushed_at'],'license':obj.get('license'),'default_branch':obj['default_branch']}
   else:summary[label]={'sha':obj['sha'],'date':obj['commit']['committer']['date']}
  except Exception as exc:summary[label]={'error':str(exc),'url':url}
 view='https://drive.google.com/file/d/140xgtckQkRwqgszD1wWiDH6lV7xufa8r/view?usp=drive_link'
 try:
  request=urllib.request.Request(view,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(request,timeout=35) as response:
   raw=response.read(CAP+1)
   if len(raw)>CAP:raise RuntimeError('Drive metadata page exceeds cap')
   text=raw.decode('utf-8','replace');(P/'official_checkpoint_view.html').write_text(text,encoding='utf-8')
   title=re.search(r'<title>(.*?)</title>',text,re.S)
   summary['checkpoint_view']={'url':view,'response_bytes':len(raw),'response_sha256':hashlib.sha256(raw).hexdigest(),'content_type':response.headers.get('Content-Type'),'title':html.unescape(title.group(1)) if title else None,'checkpoint_body_downloaded':False}
 except Exception as exc:summary['checkpoint_view']={'url':view,'error':str(exc),'checkpoint_body_downloaded':False}
 download='https://drive.usercontent.google.com/download?id=140xgtckQkRwqgszD1wWiDH6lV7xufa8r&export=download&authuser=0&confirm=t'
 try:
  request=urllib.request.Request(download,method='HEAD',headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(request,timeout=35) as response:
   headers=dict(response.headers.items())
   summary['checkpoint_head']={'url':download,'resolved_url':response.url,'status':response.status,'headers':headers,'body_bytes_read':0}
 except Exception as exc:summary['checkpoint_head']={'url':download,'error':str(exc),'body_bytes_read':0}
 put('primary_metadata_summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
