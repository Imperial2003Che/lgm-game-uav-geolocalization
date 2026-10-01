"""Create the bounded literature review record; stdlib only; no manuscript edits."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re

OUT = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914')
HERE = Path(__file__).resolve().parent
MAN = OUT / 'manuscript_evidence_revision_20260930_0202' / 'manuscript'
KEYS = ['clip2021','csls2018','rerank2017','aqe2007','resnet2016','dropout2014','adamw2019','sgdr2017','mixedprecision2018','efron1979','mcnemar1947','holm1979','commoncorruptions2019']
NOW = datetime.now(timezone.utc).isoformat()

def binding(p):
    b = p.read_bytes()
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def save(name, value):
    p = HERE/name
    with p.open('x',encoding='utf-8',newline='\n') as f:
        f.write(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n')

text = (MAN/'refs.bib').read_text(encoding='utf-8')
entries = {}
for key in KEYS:
    m = re.search(r'@\w+\{'+re.escape(key)+r',',text)
    assert m, key
    depth=1; n=m.end()
    while depth:
        if text[n]=='{' and text[n-1]!='\\': depth+=1
        if text[n]=='}' and text[n-1]!='\\': depth-=1
        n+=1
    body=text[m.end():n-1]
    fields={}
    for fm in re.finditer(r'^\s*(\w+)\s*=\s*\{',body,re.M):
        d=1; j=fm.end()
        while d:
            if body[j]=='{' and body[j-1]!='\\': d+=1
            if body[j]=='}' and body[j-1]!='\\': d-=1
            j+=1
        fields[fm[1]]=' '.join(body[fm.end():j-1].split())
    entries[key]=fields

# These are bibliographic facts and short paraphrases, not downloaded paper copies.
SOURCES = [
 {'id':'clip_pmlr','url':'https://proceedings.mlr.press/v139/radford21a.html','access':'direct_success','kind':'official proceedings record','facts':'Twelve authors in the local order; ICML 38; PMLR 139; 8748–8763; 2021. Publisher BibTeX supplies no DOI.','locator':'publisher title/authors and BibTeX','tool_ref':'turn97view0'},
 {'id':'clip_pdf','url':'https://proceedings.mlr.press/v139/radford21a/radford21a.pdf','access':'direct_success','kind':'official proceedings paper','facts':'Multimodal embedding projection and ViT-B/32 are described.','locator':'PDF p.4, text near lines 271–299','tool_ref':'turn111view2 / turn112view3'},
 {'id':'csls_conference','url':'https://openreview.net/references/pdf?id=S1-xnaqDf','access':'official_index_only_direct_restricted','kind':'official conference-paper PDF indexed text','facts':'Published as an ICLR 2018 conference paper; Guillaume Lample precedes Alexis Conneau, with shared-contribution stars, followed by Ranzato, Denoyer, Jégou.','locator':'first-page title and author block','tool_ref':'turn107search12 / turn108view0'},
 {'id':'csls_method','url':'https://openreview.net/pdf?id=H196sainb','access':'official_index_only_direct_restricted','kind':'official conference-paper PDF indexed text','facts':'Section 2.2 describes CSLS and neighborhood-size K.','locator':'indexed PDF text, section 2.2 and p.7','tool_ref':'turn109search13'},
 {'id':'csls_arxiv','url':'https://arxiv.org/abs/1710.04087','access':'direct_success','kind':'author preprint record','facts':'ArXiv lists Alexis Conneau before Guillaume Lample. v1 2017-10-11, v3 2018-01-30; record says ICLR 2018. This differs from the conference first-page order.','locator':'authors, comments, submission history','tool_ref':'turn101view0'},
 {'id':'rerank_cvf','url':'https://openaccess.thecvf.com/content_cvpr_2017/html/Zhong_Re-Ranking_Person_Re-Identification_CVPR_2017_paper.html','access':'official_index_only_direct_403','kind':'official CVF accepted-version record','facts':'Zhong, Zheng, Cao, Li; matching title; CVPR 2017; CVF pagination 1318–1327. Reciprocal encoding combines k-reciprocal feature distances with original distances.','locator':'CVF citation/abstract; accepted-version first page','tool_ref':'turn100search0 / turn100search14 / turn97view2'},
 {'id':'rerank_anu','url':'https://researchportalplus.anu.edu.au/en/publications/re-ranking-person-re-identification-with-k-reciprocal-encoding/','access':'author_institution_index_only','kind':'author institution publication record','facts':'Same four authors and title; IEEE CVPR 2017 proceedings pagination 3652–3661; DOI 10.1109/CVPR.2017.389. Publisher IEEE; record publication date 2017-11-06.','locator':'publication metadata','tool_ref':'turn107search5'},
 {'id':'rerank_ieee','url':'https://ieeexplore.ieee.org/document/8099872','access':'direct_restricted','kind':'publisher endpoint','facts':'No accessible publisher metadata obtained through direct open.','locator':None,'tool_ref':'turn108view4'},
 {'id':'aqe_vgg','url':'https://www.robots.ox.ac.uk/~vgg/publications/2007/Chum07b/','access':'author_institution_index_only_direct_restricted','kind':'author group publication record','facts':'Chum, Philbin, Sivic, Isard, Zisserman in the local order; matching title; ICCV 2007. Query expansion is based on verified matches and a generative feature model.','locator':'author-provided bibliography/abstract','tool_ref':'turn103search2 / turn104view1'},
 {'id':'aqe_ora','url':'https://ora.ox.ac.uk/objects/uuid%3Abf5d687d-9f38-4d77-86b4-9d4d0dd818e1','access':'author_institution_index_only','kind':'author institutional accepted-manuscript record','facts':'IEEE 11th ICCV, 2007; DOI 10.1109/ICCV.2007.4408891. The obtained primary excerpt did not establish the 1–8 page range.','locator':'repository publication metadata','tool_ref':'turn107search0'},
 {'id':'aqe_ieee','url':'https://ieeexplore.ieee.org/document/4408891','access':'direct_restricted','kind':'publisher endpoint','facts':'Direct article metadata inaccessible.','locator':None,'tool_ref':'turn108view5'},
 {'id':'resnet_cvf','url':'https://openaccess.thecvf.com/content_cvpr_2016/html/He_Deep_Residual_Learning_CVPR_2016_paper.html?_hsmi=2','access':'official_index_only_direct_restricted','kind':'official CVF accepted-version record','facts':'He, Zhang, Ren, Sun; matching title; CVPR 2016; 770–778. CVF distinguishes accepted and final IEEE versions.','locator':'CVF citation/abstract','tool_ref':'turn103search1 / turn98view0'},
 {'id':'resnet_ieee','url':'https://doi.org/10.1109/CVPR.2016.90','access':'official_index_only_direct_restricted','kind':'indexed publisher metadata via DOI URL','facts':'IEEE conference publication; CVPR 2016; DOI 10.1109/CVPR.2016.90. Conference June 2016, added to IEEE in December 2016.','locator':'IEEE metadata displayed in search result','tool_ref':'turn113search1 / turn106view3'},
 {'id':'dropout_jmlr','url':'https://www.jmlr.org/beta/papers/v15/srivastava14a.html','access':'direct_success','kind':'official journal record','facts':'Five authors in the local order; matching title; JMLR 15(56), 1929–1958, 2014. Random unit dropping is the method; no DOI in the obtained record.','locator':'author/title/citation/abstract','tool_ref':'turn101view2'},
 {'id':'adamw_arxiv','url':'https://arxiv.org/abs/1711.05101','access':'direct_success','kind':'author preprint record with conference comment','facts':'Loshchilov and Hutter; matching title; explicitly published at ICLR 2019. v1 2017-11-14; v3 2019-01-04. Decoupled weight decay is distinguished from L2 in adaptive optimization.','locator':'authors, abstract, comments, version history','tool_ref':'turn101view3'},
 {'id':'adamw_openreview','url':'https://openreview.net/forum?id=Bkg6RiCqY7','access':'direct_challenge','kind':'official conference endpoint','facts':'Direct record not obtained.','locator':None,'tool_ref':'turn98view2'},
 {'id':'sgdr_arxiv','url':'https://arxiv.org/abs/1608.03983','access':'direct_success','kind':'author preprint record with conference comment','facts':'Loshchilov and Hutter; matching title; ICLR 2017. v1 2016-08-13; v5 2017-05-03.','locator':'authors, comments, version history','tool_ref':'turn101view4'},
 {'id':'sgdr_pdf','url':'https://arxiv.org/pdf/1608.03983','access':'direct_success','kind':'author paper','facts':'Section 3 equation (5) is a cosine learning-rate schedule within a restart cycle.','locator':'PDF p.3, section 3, equation (5)','tool_ref':'turn110view0'},
 {'id':'mixed_arxiv','url':'https://arxiv.org/abs/1710.03740','access':'official_index_only_direct_restricted','kind':'author preprint metadata','facts':'Eleven authors in the local linear order, beginning Paulius Micikevicius then Sharan Narang; matching title. Submission in October 2017 is not conference year.','locator':'arXiv metadata in index','tool_ref':'turn103academia12 / turn101view5'},
 {'id':'mixed_conference','url':'https://openreview.net/pdf?id=r1gs9JgRZ','access':'official_index_only_direct_restricted','kind':'official conference paper indexed text','facts':'Published at ICLR 2018. The first-page author layout groups Baidu and NVIDIA affiliations; it is not a reason to replace linear arXiv citation order. Method discusses low-precision computation with FP32 master values and loss scaling.','locator':'first-page author block and indexed abstract','tool_ref':'turn103search17 / turn108view2'},
 {'id':'efron_issue','url':'https://www.jstor.org/stable/i348796','access':'official_index_only','kind':'official journal issue archive','facts':'Annals of Statistics 7(1), January 1979; B. Efron; matching title; pages 1–26. Original 1977 Rietz Lecture context does not change 1979 publication year.','locator':'issue table of contents','tool_ref':'turn109search0'},
 {'id':'efron_doi','url':'https://doi.org/10.1214/aos/1176344552','access':'direct_restricted','kind':'publisher DOI endpoint','facts':'No primary direct metadata obtained; DOI and expanded given name remain unresolved in this review.','locator':None,'tool_ref':'turn106view0'},
 {'id':'mcnemar_cambridge','url':'https://www.cambridge.org/core/journals/psychometrika/article/abs/note-on-the-sampling-error-of-the-difference-between-correlated-proportions-or-percentages/698C2461BE63F5848763502D54E534FD','access':'official_index_only_direct_restricted','kind':'current official publisher article record','facts':'Quinn McNemar; matching title; Psychometrika 12(2), June 1947, 153–157; DOI 10.1007/BF02295996. Online date 2025 is not the original publication year. Abstract discusses correlated proportions and chi-square equivalence, without establishing the exact binomial implementation.','locator':'article metadata and abstract','tool_ref':'turn102search0 / turn104view4'},
 {'id':'holm_issue','url':'https://www.jstor.org/stable/i412579','access':'direct_success','kind':'official journal issue archive','facts':'Scandinavian Journal of Statistics 6(2), 1979; Sture Holm; matching title; 65–70. DOI not supplied by the accessed issue table.','locator':'table of contents','tool_ref':'turn104view3'},
 {'id':'holm_article','url':'https://www.jstor.org/stable/4615733','access':'direct_restricted','kind':'official journal article archive','facts':'Article content and DOI metadata inaccessible directly. Stable identifier alone is not treated as independent DOI confirmation.','locator':None,'tool_ref':'turn99view3'},
 {'id':'corruptions_conference','url':'https://openreview.net/pdf?id=HJz6tiCqYm','access':'official_index_only_direct_restricted','kind':'official conference paper indexed text','facts':'Dan Hendrycks then Thomas Dietterich; matching title; published as ICLR 2019 conference paper. ImageNet-C corruptions and ImageNet-P perturbations are distinguished.','locator':'first-page title/authors and abstract','tool_ref':'turn105search2 / turn108view3'},
 {'id':'corruptions_code','url':'https://github.com/hendrycks/robustness/blob/master/ImageNet-C/create_c/make_imagenet_c.py','access':'direct_success','kind':'paper author-maintained implementation','facts':'The brightness function adds positive offsets to HSV value, increasing brightness; the file also defines Gaussian noise, Gaussian blur and contrast changes. Current master was read, not a pinned 2019 commit.','locator':'brightness function near displayed lines 2131–2142; gaussian_blur near 1836–1842','tool_ref':'turn111view0 / turn112view0 / turn112view1'},
]

def rec(key, matched, sources, note, claims, unresolved=None):
    f={}
    mapping={'author':'author_order','booktitle':'venue','journal':'venue','year':'year','volume':'volume','number':'issue_or_article_number','pages':'pages','doi':'doi','publisher':'publisher','series':'series','title':'title'}
    for k,v in entries[key].items():
        status='match_in_obtained_primary_evidence' if k in matched else 'unresolved_primary_evidence'
        f[k]={'local_value':v,'status':status}
    if 'doi' not in f:
        f['doi']={'local_value':None,'status':'not_in_local_entry_no_addition_proposed','note':'Preprint DOI is not automatically a conference-publication DOI.'}
    for missing in ['volume','number','pages']:
        if missing not in f: f[missing]={'local_value':None,'status':'not_in_local_entry_no_contradiction_established'}
    return {'key':key,'fields':f,'sources':sources,'version_note':note,'bounded_claim_review':claims,'explicit_unresolved':unresolved or [],'confirmed_correction_required':False}

R=[]
R.append(rec('clip2021',list(entries['clip2021']),['clip_pmlr','clip_pdf'],'Conference version and 2021 PMLR publication match.',{'main_lines':[210,316,317],'finding':'Supports common image/text representation space and named ViT-B/32 model. Project freezing, encoder precision, preprocessing and scientific outcomes were not verified.'}))
R.append(rec('csls2018',list(entries['csls2018']),['csls_conference','csls_arxiv','csls_method'],'Keep conference author order Lample then Conneau. ArXiv lists Conneau then Lample; this is a version distinction, not a proven local error.',{'main_lines':[652,653],'finding':'CSLS is a local-neighborhood similarity adjustment. The manuscript describes its own adapted ranking procedure; code and neighbor membership were not reviewed.'}))
R.append(rec('rerank2017',list(entries['rerank2017']),['rerank_cvf','rerank_anu','rerank_ieee'],'Keep IEEE proceedings pages 3652–3661, corroborated by the author institution. CVF accepted-version pages 1318–1327 are a separate pagination. Direct IEEE page access failed.',{'main_lines':[654,655],'finding':'Reciprocal-neighbor inspiration is supported. Manuscript explicitly says its bonus is distinct from full k-reciprocal encoding, so attribution does not imply algorithm equivalence.'},['IEEE pagination and DOI confirmed at author-institution record, not a successful fresh direct IEEE read.']))
R.append(rec('aqe2007',[k for k in entries['aqe2007'] if k!='pages'],['aqe_vgg','aqe_ora','aqe_ieee'],'ICCV conference year 2007 agrees; repository publication date in December is distinct from October event dates.',{'main_lines':[656,657],'finding':'Classical automatic query expansion is supported as conceptual antecedent. The manuscript already distinguishes its rank-weighted heuristic; no equivalence to the original generative model is claimed.'},['Pages 1–8 were not freshly established from obtained primary evidence; unchanged.']))
R.append(rec('resnet2016',list(entries['resnet2016']),['resnet_cvf','resnet_ieee'],'CVF accepted version and indexed IEEE publication agree on 2016; later IEEE online addition does not alter conference year.',{'main_lines':[357,358,359,360,531],'finding':'Residual-network attribution supported. Exact 512/2048 feature widths, classifier removal and project ImageNet initialization were not traced in an accessible original full-text architecture table in this review.'},['Architecture-dimensional statements were not independently verified here.']))
R.append(rec('dropout2014',list(entries['dropout2014']),['dropout_jmlr'],'JMLR record explicitly gives 15(56):1929–1958 (2014); retain 56 as publisher citation number.',{'main_lines':[532],'finding':'Dropout method attribution supported; project probability 0.20 is a local setting, not a value validated by this citation.'}))
R.append(rec('adamw2019',list(entries['adamw2019']),['adamw_arxiv','adamw_openreview'],'Use ICLR 2019, not arXiv first-posting year 2017. No conference DOI invented.',{'main_lines':[534],'finding':'Decoupled weight decay / AdamW attribution supported; local learning rate, weight decay, optimizer state and outcomes not reviewed.'}))
R.append(rec('sgdr2017',list(entries['sgdr2017']),['sgdr_arxiv','sgdr_pdf'],'Use ICLR 2017; arXiv begins in 2016. Original equation (5) supplies the cosine form.',{'main_lines':[536,537],'finding':'Manuscript expressly uses cosine annealing without restarts and cites only the cosine form. This is compatible with the original schedule formula and does not assert using full SGDR; local five-epoch warm-up is not citation-validated.'}))
R.append(rec('mixedprecision2018',list(entries['mixedprecision2018']),['mixed_arxiv','mixed_conference'],'Conference 2018 vs preprint 2017. Retain arXiv metadata linear author order; conference PDF affiliation blocks are not a replacement order.',{'main_lines':[536],'finding':'Mixed-precision training is supported as a method attribution. Actual AMP mode, loss scaler, dtype transitions and project numeric equivalence were not reviewed.'}))
R.append(rec('efron1979',[k for k in entries['efron1979'] if k not in ['author','doi']],['efron_issue','efron_doi'],'Journal publication 1979 is correct relative to issue metadata; earlier lecture context is not publication year.',{'main_lines':[568,569],'finding':'Foundational bootstrap attribution is bibliographically identified. Original full text was inaccessible, so query-paired resampling, 10,000 replicates, interval construction and actual reported intervals are not verified.'},['Primary issue archive gives B. Efron, not expanded Bradley; full given name not freshly established.','DOI 10.1214/aos/1176344552 not freshly established from accessible primary record.']))
R.append(rec('mcnemar1947',list(entries['mcnemar1947']),['mcnemar_cambridge'],'Keep original June 1947 publication; publisher online display date 2025 is a migration/display date and not a correction to 1947.',{'main_lines':[569,570],'finding':'Supports correlated-proportions test attribution. Accessed abstract does not establish the manuscript exact two-sided binomial form. This is a bounded source-support gap, not evidence that the implementation or scientific result is wrong; a specific formula source may be added in a later open revision.'},['Exact-binomial implementation/formula support was not established from accessible abstract.']))
R.append(rec('holm1979',[k for k in entries['holm1979'] if k!='doi'],['holm_issue','holm_article'],'Journal issue, year and pages agree. Stable article identifier is not used to infer a DOI confirmation.',{'main_lines':[570,571],'finding':'Sequentially rejective multiple-testing method attribution identified. Full proof and project adjustment implementation or the 12/32 hypothesis families were not independently reviewed.'},['DOI 10.2307/4615733 not freshly established from an accessible primary DOI field.']))
R.append(rec('commoncorruptions2019',list(entries['commoncorruptions2019']),['corruptions_conference','corruptions_code'],'ICLR 2019 conference attribution matches. Code observation is current author master, not a pinned historical revision.',{'main_lines':[583,584,585,586],'finding':'ImageNet-C-style inspiration is appropriate; equivalence to original transforms or severity values is not established. The original author brightness function increases brightness, while local prose says reduced brightness. Preserve the project transform; optionally clarify that brightness direction/severities are adapted. Occlusion/rotation are already labeled author-defined.'},['No fresh project corruption execution or code validation; no ImageNet-C-equivalence conclusion.']))

# Avoid treating every conference publishing-detail field as independently shown when
# only a paper header/author record was obtained.
for r in R:
    if r['key'] in ['csls2018','adamw2019','sgdr2017','mixedprecision2018','commoncorruptions2019']:
        r['fields']['booktitle']['status']='conference_name_year_match_ordinal_not_separately_checked'
        r['fields']['publisher']['status']='hosting_platform_consistent_publisher_role_not_separately_established'
R[9]['fields']['author']['note']='B. Efron matches surname/initial; expanded given name unresolved.'
assert [r['key'] for r in R]==KEYS
assert len(set(s['id'] for s in SOURCES))==len(SOURCES)
assert all(s in {x['id'] for x in SOURCES} for r in R for s in r['sources'])

access={'schema':'lgm.foundation-citation-access.v1','recorded_utc':NOW,'timing_note':'Accesses occurred in this AI-agent review session on 2026-09-30. Exact per-call UTC timestamps were not captured; this is record-generation time, not an invented fetch timestamp.','evidence_note':'Short bibliographic facts and paraphrases from actual tool results; indexed official/author sources are distinguished from successful direct page reads. No full paper copies saved. Secondary search hits were not adopted as authorities.','sources':SOURCES,'additional_failed_attempts':['OpenReview forum/API direct requests for several IDs returned challenge/restricted/403; no content inferred from failure.','Project Euclid direct article and DOI attempts for Efron were restricted.','Springer direct McNemar article was restricted; obtained official Cambridge index metadata instead.']}
report={'schema':'lgm.foundation-citation-review.v1','created_utc':NOW,'reviewer':'independent AI sub-agent /root/citation_foundations_0405; no external human reviewer','scope_keys':KEYS,'scope_count':13,'local_inputs':[binding(MAN/p) for p in ['refs.bib','main.tex','supplementary.tex']],'method':'Read the latest HANDOFF tail and relevant actual citation occurrences; compare scoped local BibTeX fields against primary official or author-held records. Bounded claim support only. Supplemental TeX had no direct occurrences of these keys in the scoped search. No original scientific outputs, code execution, models or large assets were revalidated.','result':'partial_primary_citation_audit_no_proven_metadata_correction','all_bibliography_verified':False,'all_fields_verified':False,'scientific_validation':False,'manuscript_modified':False,'sealed_zip_modified':False,'entries':R,'notes':['No automatic rewriting of author order across preprint/conference versions.','No automatic conversion between CVF accepted-version and IEEE proceedings pagination.','An inaccessible primary endpoint is an unresolved field, not proof of a wrong citation.','Foundational citation support does not independently validate project numeric results, bootstrap confidence intervals, paired test implementation or frozen protocol.']}
save('PRIMARY_ACCESS.json',access)
save('FOUNDATION_CITATION_REVIEW.json',report)
save('CORRECTION_DECISION.json',{'created_utc':NOW,'confirmed_bibtex_corrections':[],'corrected_snippets_or_diff_created':False,'reason':'No proven metadata error in these 13 local entries. Preserve version-specific order and pagination; unresolved fields stay unresolved.','optional_text_clarification':{'scope':'future unsealed revision only','location':'main.tex lines 583–586','finding':'The author ImageNet-C implementation brightens images, whereas the local project description darkens images. Existing ImageNet-C-style wording denotes inspiration, not strict benchmark equivalence.','suggested_direction':'State explicitly that illumination direction and severities are project adaptations, preserving the frozen transform. This is not a proposed scientific change.'},'source_support_followup':{'location':'main.tex lines 569–570','finding':'Accessible McNemar abstract does not establish the exact binomial formula; a dedicated formula reference can be checked later. No claim of implementation failure.'}})

lines=['# Foundation citation review — 13 keys','',f'Record generated: {NOW}. Reviewer: independent AI sub-agent; no external human reviewer.','',
'This is a partial primary-source metadata and bounded claim-support audit. No proven bibliography correction was found. It does not certify every field, the remaining bibliography, project implementation, or scientific results. The adopted manuscript, full package and evidence remain unchanged.','',
'## Findings','',
'| Key | Evidence and decision |','|---|---|',
'| clip2021 | PMLR direct record matches the twelve-author order, ICML/PMLR 139, 8748–8763, 2021. Common embedding space and ViT-B/32 are supported by the official paper. |',
'| csls2018 | Keep Lample before Conneau for the conference paper. ArXiv reverses these two authors; do not silently apply preprint order to the conference entry. |',
'| rerank2017 | IEEE proceedings 3652–3661 is corroborated by the author institution. CVF accepted version uses 1318–1327. Keep the selected IEEE pagination; direct IEEE read was restricted. |',
'| aqe2007 | Author order, ICCV 2007 and DOI match obtained author-held records. Pages 1–8 remain unverified from primary evidence in this review. |',
'| resnet2016 | CVF and indexed IEEE metadata support the entry, including DOI. Exact feature widths and local implementation choices were not independently traced. |',
'| dropout2014 | Direct JMLR record matches 15(56):1929–1958 and author order. A project dropout probability is not established by the citation. |',
'| adamw2019 | The author record states ICLR 2019; 2017 is first preprint year. Local optimizer settings were not reviewed. |',
'| sgdr2017 | Original equation (5) supports the cosine form. The manuscript explicitly excludes restarts, so its wording does not misrepresent full SGDR. |',
'| mixedprecision2018 | ICLR 2018 header and arXiv metadata support title/year and linear author order; affiliation-grouped PDF layout is not a correction rule. |',
'| efron1979 | Issue record supports B. Efron, title, 7(1):1–26 and 1979. Expanded given name and DOI remain unresolved from obtained primary evidence. |',
'| mcnemar1947 | Official publisher index supports original 1947 metadata and DOI. Displayed 2025 online date is not the publication year. Exact-binomial formulation is not established by the accessed abstract. |',
'| holm1979 | Direct issue contents match Sture Holm, title, 6(2):65–70 (1979). DOI remains unresolved from the accessed primary field. |',
'| commoncorruptions2019 | Conference metadata matches. Original author code increases brightness; manuscript reduced-brightness condition is an adaptation. Existing “style” wording must not imply exact ImageNet-C implementation or severity equivalence. |','',
'ICLR conference names and years were supported; their ordinal numbers and the BibTeX publisher-role designation OpenReview.net were not separately established by every accessed paper header. Missing conference page/DOI fields were not filled with invented values or preprint identifiers.','',
'## Bounded support','',
'CSLS, reciprocal reranking and query expansion are cited as adapted or conceptually related procedures in the actual manuscript; their local algorithms are not certified by the source review. Frozen CLIP FP16 use, ResNet feature dimensions, training hyperparameters, paired-resampling settings, significance families and actual scientific outcomes remain outside this audit.','',
'Two future text checks are recorded without editing the manuscript: explicitly call brightness direction/severity a project adaptation; verify a precise source for the exact McNemar binomial formula. Neither observation changes the frozen protocol or establishes a scientific implementation error.','',
'## Primary sources and access','']
for s in SOURCES:
    lines.append(f"- [{s['id']}]({s['url']}): {s['access']}. {s['facts']}")
lines += ['', 'Direct access failures and indexed evidence are kept distinct in PRIMARY_ACCESS.json. Exact per-call access timestamps were not captured. The record stores short facts/paraphrases and locators, not full copyrighted papers.', '', 'CORRECTION_DECISION.json records why no corrected BibTeX or patch was produced. FOUNDATION_CITATION_REVIEW.json contains each local field, its status, actual manuscript line locations, limitations and input hashes.', '']
save('REVIEW.md','\n'.join(lines))
manifest={'schema':'lgm.foundation-citation-review-delivery.v1','created_utc':NOW,'producer':'independent AI sub-agent; not human review','files':[binding(HERE/p) for p in ['build_review_record.py','PRIMARY_ACCESS.json','FOUNDATION_CITATION_REVIEW.json','CORRECTION_DECISION.json','REVIEW.md']],'checks':{'exactly_13_requested_unique_keys':len(R)==13 and len(set(KEYS))==13,'all_source_references_resolve':True,'no_confirmed_metadata_correction':True,'no_manuscript_or_zip_writes':True},'scope':'Literature metadata/claim-attribution research only; parent adoption still separate.'}
save('DELIVERY.json',manifest)
print(json.dumps({'review':binding(HERE/'FOUNDATION_CITATION_REVIEW.json'),'delivery':binding(HERE/'DELIVERY.json'),'scope_keys':13,'mandatory_corrections':0},ensure_ascii=False))
