from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,difflib,re

B=Path(__file__).resolve().parent
EX=B.parent
MAN=EX.parent/'manuscript_evidence_revision_20260930_0202'/'manuscript'
NOW=datetime.now(timezone.utc).isoformat()
def bind(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(name,obj):
 with (B/name).open('x',encoding='utf8',newline='\n') as f:f.write(obj if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

cross=json.loads((B/'CROSSREF_DIRECT_ACCESS.json').read_text(encoding='utf8'))['accesses']
extra=json.loads((B/'ADDITIONAL_DIRECT_ACCESS.json').read_text(encoding='utf8'))['accesses']
pdf=json.loads((B/'PDF_DIRECT_ACCESS.json').read_text(encoding='utf8'))['accesses']
fay=json.loads((B/'FAY_CURRENT_PDF_ACCESS.json').read_text(encoding='utf8'))
assert cross[0]['selected_metadata']['page']=='1-8'
assert cross[1]['selected_metadata']['DOI']=='10.1214/aos/1176344552'
assert extra[1]['metadata']==[{'DOI':'10.2307/4615733','status':'DOI does not exist'}]
assert pdf[0]['status']=='direct_success' and fay['status']=='direct_success'

web={
 'schema':'lgm.citation-open-fields-web-evidence.v1','created_utc':NOW,
 'actual_scope':'Only the previously unresolved five field/formula targets; no repeat of the thirteen-key confirmed-field audit.',
 'access_window_utc':{'orientation_clock':'2026-09-30T04:09:03Z','first_captured_direct_access':'2026-09-30T04:10:38.077865+00:00','last_captured_direct_access':'2026-09-30T04:14:31.876593+00:00','note':'Search/open call timestamps were not captured individually. Direct-fetch scripts record their actual start/end times.'},
 'sources':[
  {'id':'aqe_deposit','url':cross[0]['url'],'mode':'direct_http200','primary_role':'IEEE publisher deposit at official DOI registration agency Crossref','new_evidence':'page=1-8; identity bound by exact title and DOI.','record':'CROSSREF_DIRECT_ACCESS.json'},
  {'id':'efron_doi_deposit','url':cross[1]['url'],'mode':'direct_http200','primary_role':'Institute of Mathematical Statistics publisher deposit at Crossref','new_evidence':'DOI10.1214/aos/1176344552 bound to exact article title. Author field remains B. Efron, not expanded.','record':'CROSSREF_DIRECT_ACCESS.json'},
  {'id':'efron_self_citation','url':pdf[0]['url'],'mode':'direct_http200_pdf_in_memory','primary_role':'author-hosted later paper containing his own bibliography','new_evidence':'PDF page7, reference3 expands the 1979 article author to Bradley Efron.','record':'PDF_DIRECT_ACCESS.json','version_note':'Later author self-citation supports expanded name; this is not a fresh reading of the original 1979 article author line.'},
  {'id':'holm_doi_ra','url':extra[1]['url'],'mode':'direct_http200_json','primary_role':'DOI.org registration-agency lookup','new_evidence':'Exact requested identifier returns status DOI does not exist.','record':'ADDITIONAL_DIRECT_ACCESS.json','version_note':'Observed current status on2026-09-30; no assertion about historical registration or temporary outages.'},
  {'id':'holm_resolution','url':'https://doi.org/10.2307/4615733','mode':'direct_http404','primary_role':'official DOI resolver','new_evidence':'Current resolver request fails404; Crossref work lookup and official handle lookup also404.','record':'ADDITIONAL_DIRECT_ACCESS.json'},
  {'id':'holm_issue','url':'https://www.jstor.org/stable/i412579','mode':'web_direct_success','primary_role':'official journal archive issue','new_evidence':'Lines6–8 identify Scandinavian Journal of Statistics6(2),1979; lines52–61 give Sture Holm, title,65–70 and stable article4615733.','tool_reference':'turn143view1','version_note':'Archive metadata; full article body was not accessed.'},
  {'id':'holm_stable_article','url':'https://www.jstor.org/stable/4615733','mode':'article_direct_client_challenge; identity established by direct official issue link','primary_role':'official archival article permalink','new_evidence':'Use the issue-linked stable URL, not an inferred DOI.','tool_reference':'exec7dda3b + turn143view1'},
  {'id':'fay_article','url':'https://journal.r-project.org/articles/RJ-2010-008/','mode':'direct_http200_html and official index text','primary_role':'original author research article, official journal publisher','new_evidence':'Fay, Michael P.;2010;The R Journal2(1):53–58; DOI10.32614/RJ-2010-008. Publisher HTML metadata supplies relative PDF URL.','record':'ADDITIONAL_DIRECT_ACCESS.json','tool_reference':'turn118search0; turn141search0; exec911fc9'},
  {'id':'fay_pdf','url':fay['url'],'mode':'direct_http200_pdf_in_memory','primary_role':'original published journal article','new_evidence':'Printed53(PDF1): capped double smaller tail;54(PDF2): equal two-sided methods under null0.5;56(PDF4): conditioning on b+c gives Binomial(b+c,theta), nulltheta0.5.','record':'FAY_CURRENT_PDF_ACCESS.json'},
  {'id':'statsmodels_official','url':'https://www.statsmodels.org/stable/_modules/statsmodels/stats/contingency_tables.html#mcnemar','mode':'direct_http200_source_document_read_only','primary_role':'official statistical software documentation/source','new_evidence':'Exact branch uses off-diagonal counts, twice Binomial CDF at their minimum with probability0.5, capped at1.','record':'ADDITIONAL_DIRECT_ACCESS.json plus DIRECT_TEXT_ADDENDUM.json','version_note':'Current stable documentation read, not pinned project dependency or executed method.'}
 ],
 'not_adopted_or_limited':[
  {'url':'https://intelligent-earth.ox.ac.uk/publication/1770575/dimensions','finding':'Indexed author-institution aggregation states pages1–8 but labels the venue2015 while date/DOI are2007. Do not use this internally inconsistent record as correction authority; the IEEE deposit resolves pages.'},
  {'url':'https://profiles.stanford.edu/bradley-efron','finding':'Direct urllib TLS certificate validation failed; verification was not disabled. Indexed profile alone was not used to connect full name to this article.'},
  {'url':'https://journal.r-project.org/archive/2010-1/RJournal_2010-1_Fay.pdf','finding':'Indexed historical URL was404 in direct access; current PDF URL was discovered from successful article metadata and read instead.'},
  {'url':'https://cran.r-project.org/web/packages/exact2x2/vignettes/exactMcNemar.pdf','finding':'Web direct access unavailable; not needed after original Fay article/PDF.'},
  {'url':'https://support.sas.com/documentation/cdl/en/statug/63347/HTML/default/statug_power_sect009.htm','finding':'Official search excerpt supported conditional binomial interpretation, but direct tool open failed; not used as sole formula authority.'}
 ],
 'scope_limits':['No new project p-values, bootstrap samples, ranks, model outputs or code execution.','No full paper copies saved; PDF text was read in memory and only metadata/digests/locators retained.','A bibliography reference supports the formula as literature, not that local implementation or scientific assumptions were verified.']}
write('WEB_EVIDENCE.json',web)
write('DIRECT_TEXT_ADDENDUM.json',{'created_utc':NOW,'statsmodels_first_marker_result':'The three false formula_markers in ADDITIONAL_DIRECT_ACCESS.json came from token-spacing/multiplication-order regex assumptions; they were not findings of absent mathematics.','subsequent_read':'A separate read-only text extraction joined HTML span contents without inserted spaces and the actual full mcnemar function was read through the tool (exec7dda3b).','semantic_result':'Its exact branch takes the minimum discordant count, doubles the Binomial(n=b+c,p=.5) CDF at that count, and caps at1. No function was executed.','captured_time_note':'The follow-up tool read was after04:11:37.843778UTC and before clock04:13:11UTC; no exact per-read timestamp or new body hash was captured. Do not attribute its byte identity to the earlier request.','minor_tool_failure':'One later ad-hoc HTML-inspection command had a Python bracket SyntaxError before network access (exec52c0e0); corrected once (exec911fc9). This did not modify any report or manuscript.'})

old_refs=(MAN/'refs.bib').read_text(encoding='utf8')
old_main=(MAN/'main.tex').read_text(encoding='utf8')
holm_old=re.search(r'@article\{holm1979,.*?\n\}',old_refs,re.S).group()
holm_new=holm_old.replace('  doi     = {10.2307/4615733}','  url     = {https://www.jstor.org/stable/4615733}')
assert holm_old!=holm_new and '10.2307' not in holm_new
fay_bib='''@article{fay2010exact,
  author  = {Michael P. Fay},
  title   = {Two-sided Exact Tests and Matching Confidence Intervals for Discrete Data},
  journal = {The R Journal},
  volume  = {2},
  number  = {1},
  pages   = {53--58},
  year    = {2010},
  doi     = {10.32614/RJ-2010-008},
  url     = {https://journal.r-project.org/articles/RJ-2010-008/}
}'''
old_cite=r'\cite{mcnemar1947}, with Holm correction'
new_cite=r'\cite{mcnemar1947,fay2010exact}, with Holm correction'
assert old_main.count(old_cite)==1 and 'fay2010exact' not in old_refs
new_refs=old_refs.replace(holm_old,holm_new)+ '\n'+fay_bib+'\n'
new_main=old_main.replace(old_cite,new_cite)
patch=''.join(difflib.unified_diff(old_refs.splitlines(True),new_refs.splitlines(True),fromfile='manuscript/refs.bib',tofile='proposed/manuscript/refs.bib'))
patch+=''.join(difflib.unified_diff(old_main.splitlines(True),new_main.splitlines(True),fromfile='manuscript/main.tex',tofile='proposed/manuscript/main.tex'))
write('PROPOSED_CITATION_ONLY.patch',patch)
write('PROPOSED_REFERENCES.bib',holm_new+'\n\n'+fay_bib+'\n')
write('PROPOSED_MAIN_EXCERPT.tex','% Proposed citation-only replacement; not applied to the sealed manuscript.\nTop-1 correctness is compared using two-sided exact McNemar tests\n\\cite{mcnemar1947,fay2010exact}, with Holm correction \\cite{holm1979} within each declared\n')

findings=[
 {'target':'aqe2007.pages','before':'unresolved_primary_evidence','after':'confirmed_unchanged','local_value':'1--8','source_ids':['aqe_deposit'],'revision':'none'},
 {'target':'efron1979.doi','before':'unresolved_primary_evidence','after':'confirmed_unchanged','local_value':'10.1214/aos/1176344552','source_ids':['efron_doi_deposit'],'revision':'none'},
 {'target':'efron1979.author_expansion','before':'unresolved_primary_evidence','after':'confirmed_by_author_self_citation','local_value':'Bradley Efron','source_ids':['efron_self_citation'],'revision':'none; original1979 first-page author line not newly checked'},
 {'target':'holm1979.doi','before':'unresolved_primary_evidence','after':'current_official_doi_lookup_says_not_exists','local_value':'10.2307/4615733','source_ids':['holm_doi_ra','holm_resolution','holm_issue','holm_stable_article'],'revision':'Recommend remove unsupported DOI field and use the official stable JSTOR URL in a new manuscript revision. Preserve title/author/year/journal/volume/issue/pages.','historical_status':'unknown; current access evidence does not prove never registered'},
 {'target':'mcnemar1947.exact_two_sided_formula_support','before':'not_established_from_original_abstract','after':'supported_by_fay2010_original_article','source_ids':['fay_article','fay_pdf','statsmodels_official'],'manuscript_location':'main.tex prose570, citation571','formula':'For discordant counts b,c, n=b+c and m=min(b,c): p=min(1,2*sum_{k=0}^{m} choose(n,k)*2^(-n)), conditional Binomial(n,0.5).','formula_kind':'Two-sided exact doubled-smaller-tail test, not chi-square approximation or mid-p. The formula is a mathematical specialization of the source; no project data evaluated.','revision':'Keep historical McNemar1947 citation and append Fay2010 to support exact conditional formulation; proposed minimal change adds only the citation key.','not_verified':'Project formula implementation, paired-data assumptions, test families, adjusted values and resulting scientific claims.'}
]
report={'schema':'lgm.citation-open-fields-review.v1','created_utc':NOW,'reviewer':'AI sub-agent /root/citation_foundations_0405; no external human reviewer','scope_count':5,'findings':findings,'inputs':[bind(p) for p in [MAN/'refs.bib',MAN/'main.tex',MAN/'supplementary.tex',EX/'citation_foundations_review_20260930_0405'/'FOUNDATION_CITATION_REVIEW.json',EX/'citation_foundations_review_20260930_0405'/'DELIVERY.json']], 'sealed_files_modified':False,'new_manuscript_created':False,'scientific_or_control_suite_executed':False,'source_code_executed':'Only these evidence-record/fetch helpers; no statistical/scientific function called. PyMuPDF was used solely to read public-paper text in memory.','suggested_revision_scope':'One wrong currently resolving DOI field replaced with valid archive URL; one literature citation added. Brightness wording is outside this five-target report and remains a separate earlier finding.','new_fields_closed':3,'new_reference_support_closed':1,'current_identifier_problem_identified':1,'claims_not_made':['All13 citations or all fields independently reverified','Full bibliography validated','Original McNemar1947 full text proved exact-binomial formula','Historical DOI absence','Implementation or science acceptance']}
write('OPEN_FIELDS_REVIEW.json',report)
md='''# Remaining citation fields: new primary evidence

AI sub-agent literature research only. No external human review, manuscript edits, or scientific execution.

| Target | New evidence | Decision |
|---|---|---|
| AQE2007 pages | IEEE deposit at Crossref says 1–8. | Keep existing pages. |
| Efron1979 DOI | IMS deposit binds 10.1214/aos/1176344552 to the article. | Keep existing DOI. |
| Efron1979 given name | Author-hosted 2017 paper, PDF page7 reference3, names Bradley Efron for the 1979 article. | Keep expanded name; original1979 author line was not newly read. |
| Holm1979 DOI | DOI.org RA says the supplied DOI does not exist; resolver/handle/Crossref return404. Direct official issue contents link the article to JSTOR stable4615733. | Replace DOI field with official stable URL in a new revision. Historical registration remains unknown. |
| Exact McNemar support | Fay2010 original PDF establishes conditional binomial null and capped doubled smaller tail. | Retain McNemar1947 and add Fay2010 beside it. No statistical implementation or result validated. |

## Ready-to-use reference support

Michael P. Fay, “Two-sided Exact Tests and Matching Confidence Intervals for Discrete Data,” *The R Journal*,2(1),53–58,2010. DOI: [10.32614/RJ-2010-008](https://doi.org/10.32614/RJ-2010-008). [Publisher article](https://journal.r-project.org/articles/RJ-2010-008/); [current original PDF](https://journal.r-project.org/articles/RJ-2010-008/RJ-2010-008.pdf).

Printed p53 defines the central two-sided probability; p54 states equivalence of the discussed two-sided rules at null probability0.5; p56 derives the binomial model after conditioning on the discordant total. Therefore, with discordant counts b,c, n=b+c and m=min(b,c), the supported probability is min(1,2 P[Binomial(n,0.5)<=m]). This is an exact conditional, doubled-smaller-tail probability. It is not mid-p and is not evidence that the project computation was correct.

The official [Holm issue record](https://www.jstor.org/stable/i412579) identifies Sture Holm, article title,65–70 in6(2),1979, and links to [the stable article](https://www.jstor.org/stable/4615733). The latter returned a client challenge during direct article access; the successful issue link establishes its identity. [DOI.org RA response](https://doi.org/ra/10.2307/4615733) supplies the current negative identifier finding. We do not infer historical registration status.

## Proposed changes, not applied

PROPOSED_REFERENCES.bib contains the Holm replacement entry and new Fay entry. PROPOSED_CITATION_ONLY.patch changes only the DOI-to-URL field, appends Fay, and adds fay2010exact to the existing main.tex citation on line571. PROPOSED_MAIN_EXCERPT.tex gives the exact minimal source replacement. Existing statistics and protocol text are unchanged. No sealed manuscript, package or Overleaf project was written.

The article DOI, author/venue identity, pages and original formula are supported by primary sources; current registrations and original publication dates are kept distinct. Failed stale URLs, a parser-marker limitation, and the direct/source access modes are retained in WEB_EVIDENCE.json and direct-access records. The scripts preserve factual metadata and response hashes, not full copyrighted paper copies.
'''
write('REVIEW.md',md)
names=['fetch_primary_metadata.py','fetch_primary_pages.py','build_open_field_report.py','CROSSREF_DIRECT_ACCESS.json','ADDITIONAL_DIRECT_ACCESS.json','PDF_DIRECT_ACCESS.json','FAY_CURRENT_PDF_ACCESS.json','WEB_EVIDENCE.json','DIRECT_TEXT_ADDENDUM.json','OPEN_FIELDS_REVIEW.json','PROPOSED_CITATION_ONLY.patch','PROPOSED_REFERENCES.bib','PROPOSED_MAIN_EXCERPT.tex','REVIEW.md']
write('DELIVERY.json',{'schema':'lgm.citation-open-fields-delivery.v1','created_utc':NOW,'files':[bind(B/n) for n in names],'scope':'Five previously open citation fields/formula-support targets; independent root adoption separate.','checks':{'five_targets_recorded':len(findings)==5,'new_reference_key_not_preexisting':True,'one_original_main_citation_replaced':True,'only_holm_doi_field_changed_in_existing_bib_entries':True,'original_manuscript_not_written':True}})
print(json.dumps({'report':bind(B/'OPEN_FIELDS_REVIEW.json'),'delivery':bind(B/'DELIVERY.json'),'proposed_patch':bind(B/'PROPOSED_CITATION_ONLY.patch')},ensure_ascii=False))
