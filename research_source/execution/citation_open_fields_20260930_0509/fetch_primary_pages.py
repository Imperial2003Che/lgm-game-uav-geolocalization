from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from html.parser import HTMLParser
import json, re, hashlib

class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.links=[]
    def handle_data(self,data): self.parts.append(data)
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            d=dict(attrs)
            if d.get('href'): self.links.append(d['href'])

sources=[
('holm_handle','https://doi.org/api/handles/10.2307/4615733','json'),
('holm_ra','https://doi.org/ra/10.2307/4615733','json'),
('holm_resolver','https://doi.org/10.2307/4615733','html'),
('efron_home','https://efron.ckirby.su.domains','html'),
('efron_profile','https://profiles.stanford.edu/bradley-efron','html'),
('fay_rjournal','https://journal.r-project.org/articles/RJ-2010-008/','html'),
('statsmodels_mcnemar','https://www.statsmodels.org/stable/_modules/statsmodels/stats/contingency_tables.html#mcnemar','html')]
out=[]
for ident,url,kind in sources:
    r={'id':ident,'url':url,'started_utc':datetime.now(timezone.utc).isoformat()}
    try:
        with urlopen(Request(url,headers={'User-Agent':'LGM-GAME-citation-audit/1.0'}),timeout=20) as f:
            data=f.read(2000001)
            if len(data)>2000000: raise ValueError('response too large')
            r.update(http_status=f.status,final_url=f.url,response_bytes=len(data),response_sha256=hashlib.sha256(data).hexdigest())
        r['status']='direct_success'
        if kind=='json': r['metadata']=json.loads(data)
        else:
            txt=data.decode('utf-8',errors='replace'); h=Text(); h.feed(txt); content=' '.join(' '.join(h.parts).split())
            patterns={'holm_resolver':[r'10\.2307/4615733',r'A Simple Sequentially Rejective Multiple Test Procedure'],
            'efron_home':[r'Bradley Efron',r'Bootstrap Methods.{0,25}Jackknife'],
            'efron_profile':[r'Bradley Efron',r'BOOTSTRAP METHODS.{0,40}JACKKNIFE'],
            'fay_rjournal':[r'\bMichael P\. Fay\b',r'10\.32614/RJ-2010-008'],
            'statsmodels_mcnemar':[r'def mcnemar',r'pvalue = stats\.binom\.cdf.{0,80}',r'pvalue = np\.minimum.{0,30}']}[ident]
            r['fact_markers']=[m.group(0) for p in patterns for m in re.finditer(p,content,re.I)][:10]
            if ident=='efron_home':
                r['publication_links']=[v for v in h.links if any(s in v.lower() for s in ['1979','bootstrap','jackknife','publication','paper','vita','pdf'])][:30]
            if ident=='efron_profile':
                r['cv_links']=[v for v in h.links if any(s in v.lower() for s in ['cv','vita','efron.ckirby'])][:10]
            if ident=='fay_rjournal':
                r['target_section_present']='Analysis of' in content and 'paired' in content
                r['metadata_bibtex_present']='RJ-2010-008' in content and '53-58' in content
            if ident=='statsmodels_mcnemar':
                r['formula_markers']={
                 'binomial_cdf_half':bool(re.search(r'binom\.cdf\s*\(\s*statistic\s*,\s*int_sum\s*,\s*0\.5\s*\)',content)),
                 'double_tail':bool(re.search(r'2\s*\*\s*stats\.binom\.cdf',content)),
                 'minimum_one':bool(re.search(r'np\.minimum\s*\(\s*pvalue\s*,\s*1\s*\)',content))}
    except Exception as e: r.update(status='direct_failure',error=type(e).__name__+': '+str(e))
    r['ended_utc']=datetime.now(timezone.utc).isoformat(); out.append(r)
with (Path(__file__).resolve().parent/'ADDITIONAL_DIRECT_ACCESS.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump({'accesses':out,'retention':'Only metadata, short fact markers and response digests retained; no full article/source text saved.'},f,ensure_ascii=False,indent=2); f.write('\n')
print(json.dumps(out,ensure_ascii=False))
