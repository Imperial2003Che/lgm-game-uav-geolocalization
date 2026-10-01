"""Seal this agent's two-dataset literature audit; stdlib only, no manuscript edits."""
from pathlib import Path
import hashlib, json, re
from datetime import datetime

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent
M = OUT / 'manuscript_evidence_revision_20260930_0202' / 'manuscript'
def bind(p):
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
def write(name, obj):
    data = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with (HERE / name).open('xb') as f:
        f.write(data)
    return bind(HERE / name)
expected = {
    'refs.bib': '83ce7fec93b0d41151d5afd0ba25eb36b13cd121888e302f048b109be3f7a611',
    'main.tex': '20b3eb50d7f0583c2c538f1d6c0b5e85ea39b071f2701034024c100822a65092',
    'supplementary.tex': '8886ecc95e046284356e74c4f5b7ec9a096fdf0af710ceb010cf3bf643a43a10'}
inputs = [bind(M / n) for n in expected]
assert all(x['sha256'] == expected[Path(x['path']).name] for x in inputs)
texts = {n: (M / n).read_text(encoding='utf-8') for n in expected}
assert '@inproceedings{university1652,' in texts['refs.bib']
assert '@article{sues200,' in texts['refs.bib']
now = datetime.now().astimezone().isoformat()
source = bind(Path(__file__))

sources = [
 {'id':'U_REPO','url':'https://github.com/layumi/University1652-Baseline',
  'kind':'author repository, current master, commit not pinned',
  'access':'direct web open success', 'tool_ref':'turn129view4',
  'locator':'README lines 211-214, 250-284, 350-364, 442-449',
  'observed':'Dataset identity, two drone/satellite directions, split table, extra Google training directory, and author citation are visible.',
  'limit':'Current documentation is not the exact historical/local source checkout; no code or data was executed.'},
 {'id':'U_PAPER','url':'https://www.zdzheng.xyz/files/ACMMM20.pdf',
  'kind':'author-hosted ACM-formatted paper',
  'access':'primary-source search index excerpts only; direct PDF open restricted',
  'tool_refs':['turn128search14','turn137search3'],
  'locator':'printed page 1395 first-page metadata; printed page 1398 section 3.2 and Table 2',
  'observed':'ACM MM 2020 identity/DOI and protocol table; 701 training plus 701 target test buildings, with 250 additional distractor buildings.',
  'limit':'No direct PDF rendering, full-file download, version hash, or final-page visual check.'},
 {'id':'U_ARCHIVE','url':'https://opus.lib.uts.edu.au/handle/10453/147990',
  'kind':'authors institutional publication record',
  'access':'indexed institutional metadata; direct open restricted',
  'tool_ref':'turn128search4', 'locator':'citation and full metadata record',
  'observed':'Proceedings of the 28th ACM International Conference on Multimedia; 2020; 1395-1403; DOI matches.',
  'limit':'Institution record lists a submitted-version PDF; mixed deposit/issue dates are not treated as conference publication dates.'},
 {'id':'U_ARXIV','url':'https://arxiv.org/abs/2002.12186',
  'kind':'author preprint record', 'access':'indexed search record; direct PDF open internal error',
  'tool_ref':'turn128academia18', 'locator':'indexed title/abstract',
  'observed':'Preprint identity matches the dataset paper.',
  'limit':'No arXiv version established; attempted html v2 URL did not yield content and is not proof of that version.'},
 {'id':'S_PAPER','url':'https://reza-zhu.github.io/files/sues-200.pdf',
  'kind':'author-hosted TCSVT-formatted paper, pagination starts at 1',
  'access':'primary-source search index excerpts only; direct PDF open restricted',
  'tool_refs':['turn128search13','turn133search3','turn139search1'],
  'locator':'page 1 title/authors/Fig. 1/introduction; page 4 Table II and Evaluation Protocol',
  'observed':'Six authors including Ling Yin; four heights; 120/80 split; per-height query/gallery table and training scenes retained as distractors.',
  'limit':'Author version is not a retrieved publisher-final PDF; final volume/issue/pages cannot be established from its 1-based header.'},
 {'id':'S_REPO','url':'https://github.com/Reza-Zhu/SUES-200-Benchmark',
  'kind':'author repository, current README; commit not pinned',
  'access':'indexed primary README; direct open internal error',
  'tool_ref':'turn128search2','locator':'Overview, Highlights, Citation',
  'observed':'Citation gives six authors, TCSVT, 2023 and DOI; maintained pipeline describes both retrieval directions.',
  'limit':'Maintained current pipeline is not a source of local executed-result evidence or a historical-code parity claim.'},
 {'id':'S_AUTHOR','url':'https://reza-zhu.github.io/publications/',
  'kind':'first author publication page','access':'indexed primary page',
  'tool_ref':'turn137search0','locator':'SUES-200 publication item',
  'observed':'Six-author order and TCSVT 2023 match the local entry.',
  'limit':'No final pagination supplied in the accessed item.'},
 {'id':'S_ARXIV','url':'https://arxiv.org/abs/2204.10704',
  'kind':'author preprint record','access':'indexed primary record; direct abs/PDF opens internal error',
  'tool_ref':'turn128academia12','locator':'indexed title/authors/date/abstract',
  'observed':'2022 preprint lists the same six authors; abstract mentions 24,120 images.',
  'limit':'2022 preprint date does not replace 2023 journal year. The attempted html v3 URL failed and does not establish an arXiv version; 24,120 must not replace complete archive inventory.'},
 {'id':'S_INSTITUTION','url':'https://pureportal.strath.ac.uk/en/publications/sues-200-a-multi-height-multi-scene-cross-view-image-benchmark-ac/',
  'kind':'institutional publication metadata, corroborative only',
  'access':'indexed record; direct open restricted',
  'tool_refs':['turn128search1','turn131search0','turn135search0'],
  'locator':'volume/issue/page/DOI/publication fields and author list',
  'observed':'33(9), 4825-4839, 2023 and DOI match; displayed author list omits Ling Yin.',
  'limit':'Author-list omission conflicts with author PDF, arXiv and author repository; not authority to remove an author. Final publication fields remain publisher-direct-unconfirmed.'}
]
failures = [
 ['https://dl.acm.org/doi/10.1145/3394171.3413896','restricted URL','turn129view2'],
 ['https://doi.org/10.1109/TCSVT.2023.3249204','not accessible via tool','turn129view3'],
 ['https://www.zdzheng.xyz/files/ACMMM20.pdf','restricted URL','turn129view0'],
 ['https://zdzheng.xyz/files/ACMMM20.pdf','not accessible via tool','turn133view2'],
 ['https://reza-zhu.github.io/files/sues-200.pdf','restricted URL','turn129view1'],
 ['https://arxiv.org/abs/2204.10704','internal error','turn129view5'],
 ['https://arxiv.org/pdf/2002.12186','internal error','turn131view0'],
 ['https://arxiv.org/pdf/2204.10704','internal error','turn131view1'],
 ['https://github.com/Reza-Zhu/SUES-200-Benchmark','internal error','turn131view2'],
 ['https://arxiv.org/html/2204.10704v3','restricted URL; requested version unconfirmed','turn133view0'],
 ['https://arxiv.org/html/2002.12186v2','restricted URL; requested version unconfirmed','turn133view1'],
 ['https://raw.githubusercontent.com/Reza-Zhu/SUES-200-Benchmark/main/README.md','restricted URL; branch not established by response','turn133view3'],
 ['https://opus.lib.uts.edu.au/handle/10453/147990','restricted URL','turn137view0'],
 ['https://pureportal.strath.ac.uk/en/publications/sues-200-a-multi-height-multi-scene-cross-view-image-benchmark-ac/','restricted URL','turn137view1']]
access = {'schema':'dataset-citation-primary-access.v1','created_local':now,
 'research_window':'2026-09-30 approximately 05:09-05:13 Europe/London; individual web-call timestamps not captured',
 'method':'AI agent read returned web text and local text; no human review or independent second-agent review claimed',
 'sources':sources,'failed_direct_accesses':[{'url':u,'result':r,'tool_ref':t} for u,r,t in failures],
 'search_scope':'Two dataset papers and authors sources only. Broad search returned later papers and third-party indexes; those are not used as decisive protocol or correction authority. Restricted domain searches sometimes produced empty or irrelevant results; these are not positive verification.',
 'raw_response_archive':False,'source_pdf_downloaded':False,'web_screenshots':False}

def field(key, name, local, status, ids, note=''):
 return {'key':key,'field':name,'local':local,'assessment':status,'sources':ids,'note':note}
fields = [
 field('university1652','entry_type','inproceedings','supported',['U_PAPER','U_ARCHIVE'],'Author README uses @article shorthand; do not replace the correct conference type with that shorthand.'),
 field('university1652','author','Zhedong Zheng and Yunchao Wei and Yi Yang','supported',['U_REPO']),
 field('university1652','title','University-1652: A Multi-view Multi-source Benchmark for Drone-based Geo-localization','supported',['U_REPO','U_PAPER']),
 field('university1652','booktitle','Proceedings of the 28th ACM International Conference on Multimedia','supported by indexed institutional record',['U_ARCHIVE']),
 field('university1652','pages','1395--1403','retained; indexed institutional corroboration',['U_ARCHIVE','U_PAPER'],'1395 visible in author PDF index; final page 1403 was not directly rendered.'),
 field('university1652','year','2020','supported',['U_REPO','U_PAPER']),
 field('university1652','doi','10.1145/3394171.3413896','supported by author sources; publisher direct unavailable',['U_REPO','U_PAPER']),
 field('sues200','entry_type','article','supported',['S_PAPER','S_REPO']),
 field('sues200','author','Runzhe Zhu and Ling Yin and Mingze Yang and Fei Wu and Yuncheng Yang and Wenbo Hu','supported',['S_AUTHOR','S_ARXIV'],'Do not delete Ling Yin based on the incomplete institutional list.'),
 field('sues200','title','SUES-200: A Multi-Height Multi-Scene Cross-View Image Benchmark Across Drone and Satellite','supported; capitalization is editorial',['S_AUTHOR']),
 field('sues200','journal','IEEE Transactions on Circuits and Systems for Video Technology','supported',['S_AUTHOR','S_REPO']),
 field('sues200','volume','33','retained; publisher-direct-unconfirmed',['S_INSTITUTION']),
 field('sues200','number','9','retained; publisher-direct-unconfirmed',['S_INSTITUTION']),
 field('sues200','pages','4825--4839','retained; publisher-direct-unconfirmed',['S_INSTITUTION'],'Author PDF pagination starts at 1; not a reason to replace journal pagination.'),
 field('sues200','year','2023','supported journal year',['S_AUTHOR','S_REPO'],'Do not replace with 2022 preprint date.'),
 field('sues200','doi','10.1109/TCSVT.2023.3249204','supported by author citation; publisher direct unavailable',['S_REPO'])]

claims = [
 {'id':'U01','local':'main.tex:77-79','claim':'Both datasets support the two drone/satellite retrieval directions.','verdict':'supported literature background','sources':['U_REPO','S_PAPER']},
 {'id':'U02','local':'main.tex:476 and 493-500','claim':'University split: 701 training, 701 target test, 250 extra gallery identities.','verdict':'agrees with original section 3.2; 951 gallery identities include distractors','sources':['U_PAPER']},
 {'id':'U03','local':'main.tex:497-500','claim':'D2S 37,855→951; S2D 701→51,355; Street2S 2,579→951.','verdict':'agrees with original Table 2 and current author README for these selected directions','sources':['U_REPO','U_PAPER'], 'limit':'Every gallery here refers to the three evaluated tasks. Original ground gallery is 2,921 images/793 identities; no claim that every possible view-gallery has 951 identities.'},
 {'id':'U04','local':'main.tex:493-495','claim':'40,513 drone/street training queries and 701 satellite positives.','verdict':'project-specific input count; not freshly validated by this literature review','sources':['U_PAPER'], 'limit':'Original training total is 50,218 including extra data; the two scopes differ.'},
 {'id':'U05','local':'main.tex:616-621','claim':'Four locally completed public-baseline runs and exact local re-evaluation.','verdict':'execution evidence is out of scope','sources':['U_REPO'],'limit':'Author source supports an extra-Google training option, not the local runs, CUDA order or numerical outcomes.'},
 {'id':'S01','local':'main.tex:503-510','claim':'120/80 identities; heights 150/200/250/300 m; per-height 4,000→200 and 80→10,000; training identities retained as distractors.','verdict':'agrees with original Table II/protocol and Fig. 1','sources':['S_PAPER'],'limit':'Agreement of counts does not prove the exact identities, file members, split seed, image bytes or local model execution.'},
 {'id':'S02','local':'main.tex:504-505','claim':'24,000 UAV training images and 120 training satellite images.','verdict':'agrees with original Table II','sources':['S_PAPER']},
 {'id':'S03','local':'main.tex:510-512','claim':'Report results separately by height and direction.','verdict':'project reporting choice preserved','sources':['S_PAPER'],'limit':'Original paper also defines cross-height summary coefficients; it does not require this project to pool tasks or use those coefficients.'},
 {'id':'I01','local':'supplementary.tex:131-132 and 159-163','claim':'University local inventory 146,520; supported rows137,576; excluded Google-view8,944; SUES40,200.','verdict':'local inventory and coverage remain dependent on adopted project evidence','sources':['U_PAPER','S_PAPER','S_ARXIV'],'limit':'No image/cache/manifest enumeration performed. SUES abstract24,120 is not a complete-gallery inventory authority; original Table II separately identifies training/query/gallery scopes.'},
 {'id':'I02','local':'supplementary.tex:165-169','claim':'652/375 optimizer steps, each training query scheduled, final-checkpoint evaluation.','verdict':'local implementation/execution claims; not validated by citing either dataset paper','sources':[]}
]
issues = [
 {'id':'D01','classification':'optional clarity change, not required numerical correction','local':'main.tex:493-510',
  'proposal':'Keep all frozen counts and tasks. In a future reviewed revision add: Dataset papers define the benchmark structure; the frozen local manifests determine the exact image membership used here.',
  'reason':'Explicitly separates literature agreement from executed local membership evidence.'},
 {'id':'D02','classification':'unresolved source-scope reconciliation; not a scientific failure','local':'main.tex:494-495; supplementary.tex:159-161',
  'calculation':'50,218 - (40,513 + 701) = 9,004; 9,004 - 8,944 = 60.',
  'proposal':'Do not replace 8,944 or alter frozen training. A later provenance note may explain why the local excluded-row inventory is not identical to the original paper total.',
  'reason':'This difference arises only if one assumes the entire local excluded Google inventory fills the original training-total gap. That assumption is unverified; local inventory rows and historical paper counts can represent different archive versions/counting scopes.',
  'required_before_any_numeric_change':'Read relevant already-adopted small inventory authority/definitions in a separately scoped review; do not infer missing images, bad training or false results from subtraction.'},
 {'id':'D03','classification':'optional wording precision','local':'main.tex:500',
  'proposal':'Replace Every gallery with Each gallery used in these three tasks only if editing this paragraph for clarity.',
  'reason':'Current context already specifies D2S/S2D/Street2S; prevent the sentence being detached and misapplied to the original ground-view gallery.'},
 {'id':'D04','classification':'remaining bibliographic verification','local':'refs.bib:19-21',
  'proposal':'Keep SUES33(9):4825--4839; obtain publisher-final metadata/PDF on a later successful access before claiming direct publisher verification.',
  'reason':'Current author sources identify the article but accessed first-party items do not expose final volume/issue/pages; institutional record corroborates them. No contradictory evidence justifies correction.'}]
report = {'schema':'two-dataset-citation-and-protocol-review.v1','created_local':now,
 'reviewer':'independent task AI agent /root/boot_contract_0405; not a human reviewer',
 'scope':'Only university1652 and sues200. A first review of these two dataset citations and local dataset-protocol prose in this round. No rerun of the earlier 13-key foundations suite.',
 'source':source,'local_inputs':inputs,'bibliographic_fields':fields,'local_claim_assessments':claims,'decisions':issues,
 'required_bibtex_corrections':0,'required_frozen_numeric_changes':0,'manuscript_modified':False,
 'scientific_validation':False,'exact_dataset_membership_validated':False,'full_primary_pdf_read':False,
 'limits':['Direct University author README and indexed primary paper excerpts are different access scopes.',
 'No data, cache, checkpoints, weights, NPZ, large ZIP, scientific source execution, COM, state or locks accessed or modified.',
 'No final Overleaf or submission-readiness claim; negative experimental results and original evidence limitations remain unchanged.',
 'Search output initially included unrelated/secondary sources; they do not support correction decisions.'],
 'result':'No proven citation or protocol-number error. Preserve frozen protocol; record four limited clarification/follow-up items.'}

ranges = {'refs.bib':[(1,24)],'main.tex':[(72,80),(476,476),(491,512),(614,625)],'supplementary.tex':[(27,33),(121,142),(157,169)]}
excerpts = {'schema':'local-dataset-citation-excerpts.v1','local_inputs':inputs,'scope':'Exact selected local text excerpts, not a full manuscript audit','excerpts':[]}
for name, spans in ranges.items():
 lines=texts[name].splitlines()
 for first,last in spans:
  excerpts['excerpts'].append({'file':name,'first_line':first,'last_line':last,'text':'\n'.join(lines[first-1:last])})
write('PRIMARY_ACCESS.json', access)
write('LOCAL_EXCERPTS.json', excerpts)
write('DATASET_CITATION_REVIEW.json', report)
write('CORRECTION_DECISION.json', {'schema':'two-dataset-correction-decision.v1','created_local':now,
 'required_bibtex_corrections':0,'required_frozen_numeric_changes':0,'patch_produced':False,
 'decisions':issues,'sealed_manuscript_edited':False,'permission_to_change_scientific_protocol':False})
md = '''# Two dataset citations and protocol scope

No proven BibTeX or frozen protocol-number correction was found. This is a partial AI-agent literature review, not human review, new experimental validation, or final manuscript adoption.

University-1652: the directly accessed [author README](https://github.com/layumi/University1652-Baseline) and indexed [original ACM author PDF](https://www.zdzheng.xyz/files/ACMMM20.pdf) agree with the draft's selected query/gallery counts and split. The current README is not a pinned historical checkout.

SUES-200: indexed [author PDF](https://reza-zhu.github.io/files/sues-200.pdf), Table II, supports the 120/80 split and the full-gallery per-height counts. Literature agreement does not validate the local split members, images, checkpoints, or execution. The journal year remains 2023; the preprint's 2022 date is separate. Keep Ling Yin: the author sources include this author despite an incomplete institutional listing. Final volume/issue/pages are retained with institutional corroboration, without claiming successful publisher-direct verification.

The 60-row arithmetic comparison is unresolved, not an identified missing-data incident: original University training total50,218 minus local semantic inputs41,214 gives9,004; local excluded Google-view inventory is8,944. Different inventory scope/version has not been reconciled here. Do not change either count based on this audit.

Possible future wording refinements: say that frozen local manifests determine exact membership; restrict 'Every gallery' to the three evaluated University tasks. Neither requires protocol changes. All proposed items and access failures are itemized in the JSON reports; no manuscript patch was made.

Only the three small local manuscript texts were read and bound. No weights, image/cache bytes, scientific/COM run, live state/lock change, old-suite rerun, large package read, or Overleaf update occurred. Direct PDF/publisher opens failed; indexed excerpts are labeled explicitly. Neither full primary-PDF reading nor independent second-reviewer acceptance is claimed.
'''
with (HERE/'REVIEW.md').open('x',encoding='utf-8',newline='\n') as f: f.write(md)
assert len(fields)==16 and len(claims)==10 and len(issues)==4
assert [bind(M/n) for n in expected] == inputs
artifacts=[bind(HERE/n) for n in ['seal_dataset_review.py','PRIMARY_ACCESS.json','LOCAL_EXCERPTS.json','DATASET_CITATION_REVIEW.json','CORRECTION_DECISION.json','REVIEW.md']]
delivery=write('DELIVERY.json',{'schema':'two-dataset-citation-review-delivery.v1','created_local':datetime.now().astimezone().isoformat(),
 'artifact_bindings':artifacts,'local_inputs':inputs,'two_keys':['university1652','sues200'],
 'bibliographic_field_rows':16,'local_claim_rows':10,'limited_decision_items':4,
 'required_bibtex_corrections':0,'scientific_execution':False,'manuscript_mutation':False,
 'producer_checks':'Three small local SHA bindings checked before/after; report counts asserted. These are not independent scientific tests or a re-run of any old suite.'})
print(json.dumps({'delivery':delivery,'report':bind(HERE/'DATASET_CITATION_REVIEW.json'),'status':'written; manuscript unchanged'},ensure_ascii=False))
