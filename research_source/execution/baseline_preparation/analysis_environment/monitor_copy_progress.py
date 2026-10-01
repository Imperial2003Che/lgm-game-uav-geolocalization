"""Read-only file-count progress companion for the active environment copy."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,time
P=Path(__file__).resolve().parent
def counts(root):
 files=0;size=0
 for base,dirs,names in os.walk(root):
  dirs[:]=[n for n in dirs if n!='__pycache__']
  for name in names:
   if name.endswith('.pyc'):continue
   try:stat=(Path(base)/name).stat()
   except OSError:continue
   files+=1;size+=stat.st_size
 return {'files':files,'bytes':size}
def main():
 ledger=json.loads((P/'preparation_ledger.json').read_text(encoding='utf-8'))
 source=counts(ledger['source']);last=None
 while True:
  target=counts(ledger['target'])
  current=json.loads((P/'preparation_ledger.json').read_text(encoding='utf-8'))
  progress={'updated_utc':datetime.now(timezone.utc).isoformat(),'status':current['status'],
            'source_total':source,'target_observed':target,'counts_are_observed_not_final_hash_verification':True,
            'file_fraction':target['files']/source['files'],'byte_fraction':target['bytes']/source['bytes']}
  (P/'copy_progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  if target!=last:print(json.dumps(progress,ensure_ascii=False),flush=True);last=target
  if current['status']!='copying':break
  time.sleep(20)
if __name__=='__main__':main()
