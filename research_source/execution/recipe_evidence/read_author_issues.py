"""Read public maintainer replies relevant to the original training recipe."""
from pathlib import Path
from urllib.request import Request,urlopen
import concurrent.futures,json,re,datetime
ROOT=Path(__file__).resolve().parent
def get(url):
    with urlopen(Request(url,headers={'User-Agent':'research-recipe-audit','Accept':'application/vnd.github+json'}),timeout=30) as response:
        return json.load(response)
report=[]
for repo in ['Mabel0403/CAMP','SummerpanKing/DAC']:
    issues=get(f'https://api.github.com/repos/{repo}/issues?state=all&per_page=100')
    urls=[x['comments_url'] for x in issues if x.get('comments')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        comments=dict(zip(urls,pool.map(get,urls)))
    entries=[]
    for issue in issues:
        item={'url':issue['html_url'],'number':issue['number'],'title':issue['title'],'author':issue['user']['login'],'association':issue.get('author_association'),
              'body':issue.get('body'),'comments':[{'url':c['html_url'],'author':c['user']['login'],'association':c.get('author_association'),'body':c.get('body'),'created_at':c.get('created_at')} for c in comments.get(issue['comments_url'],[])]}
        entries.append(item)
    result={'repo':repo,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issues':entries}
    (ROOT/(repo.split('/')[-1]+'_public_issues.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    matches=[]
    for item in entries:
        for entry in [item]+item['comments']:
            body=entry.get('body') or ''
            if re.search(r'epoch|warm.?up|训练|轮|train|pretrain|learning rate',body,re.I):
                matches.append({'issue':item['number'],'url':entry['url'],'author':entry['author'],'association':entry['association'],'body':body[:7000]})
    report.append({'repo':repo,'issues_read':len(entries),'training_related':matches})
print(json.dumps(report,ensure_ascii=True,indent=2))
