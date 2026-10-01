"""Record new limited primary-source review; no manuscript/science changes."""
from pathlib import Path
import hashlib,json,re
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
MAN=HERE.parent.parent/'manuscript_evidence_revision_20260930_0202/manuscript'
def bind(p):
    p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(name,v):
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
    return bind(HERE/name)
files=['refs.bib','main.tex','supplementary.tex','tables/literature/table_literature_standard.tex','tables/literature/table_literature_transfer.tex']
inputs=[bind(MAN/x) for x in files]
standard=(MAN/files[3]).read_text(encoding='utf-8')
transfer=(MAN/files[4]).read_text(encoding='utf-8')
rows=[]
for label,source,wanted in [
 ('MGS2-Net (v2)',standard,['97.60','98.03','98.86','97.25']),
 ('InfoGeo ',transfer,['90.87','92.53','94.20','95.12','96.08','96.30','96.31','96.75']),
 ('InfoGeo (+RD)',transfer,['91.80','93.18','95.40','96.15','96.58','97.08','96.48','97.00'])]:
    line=next(x for x in source.splitlines() if x.startswith(label))
    actual=re.findall(r'(?<!\d)\d+\.\d{2}(?!\d)',line)
    assert actual==wanted,(label,actual)
    rows.append(dict(label=label,local_tex=line,primary_reported_display_values=wanted,actual_tex_values=actual,match=True))
assert sum(len(x['actual_tex_values']) for x in rows)==20
access=[
 {'url':'https://arxiv.org/html/2602.10704v2','status':'direct_read_success','scope':'version header, six-author byline, depth input and 336-pixel inference, Table 1 own row'},
 {'url':'https://arxiv.org/abs/2605.07099','status':'direct_read_success','scope':'page explicitly identifies v5, dated 14 June 2026, title and byline'},
 {'url':'https://arxiv.org/pdf/2605.07099','status':'direct_read_success_parsed_pdf','scope':'PDF text explicitly carries v5; byline, conference footer, 448-pixel input, Drone-to-Satellite setting, relational-distillation notation and Table 9 two own rows'},
 {'url':'https://github.com/HRT00/Official_InfoGeo','status':'primary_domain_search_index_only_direct_open_failed','scope':'Byline and BibTeX spelling disagree within indexed README; not used to override paper byline'},
 {'url':'https://arxiv.org/abs/2602.10704v2','status':'direct_open_failed'},
 {'url':'https://arxiv.org/abs/2602.10704','status':'direct_open_failed'},
 {'url':'https://arxiv.org/abs/2510.22582v3','status':'direct_open_failed'},
 {'url':'https://arxiv.org/abs/2510.22582','status':'direct_open_failed'},
 {'url':'https://arxiv.org/html/2510.22582v3','status':'direct_open_failed'},
 {'url':'https://arxiv.org/html/2510.22582','status':'direct_open_failed'},
 {'url':'https://arxiv.org/pdf/2510.22582v3','status':'direct_open_failed'},
 {'url':'https://arxiv.org/pdf/2510.22582','status':'direct_open_failed'},
 {'url':'https://export.arxiv.org/abs/2510.22582v3','status':'not_accessible_via_tool'},
 {'url':'https://github.com/SkyEyeLoc/MobileGeo','status':'direct_open_failed'},
 {'url':'https://arxiv.org/abs/2605.07099v5','status':'direct_open_failed'},
 {'url':'https://arxiv.org/html/2605.07099v5','status':'direct_open_failed'},
 {'url':'https://arxiv.org/html/2605.07099','status':'direct_open_failed'},
 {'url':'https://arxiv.org/pdf/2605.07099v5','status':'direct_open_failed'}]
report={
 'schema':'limited-primary-preprint-review.v1','recorded_utc':datetime.now(timezone.utc).isoformat(),
 'method':'Root AI read tool-returned primary web text and actual local TeX; no human review or external scientific replication.',
 'inputs':inputs,'access':access,'transcription_rows':rows,'checked_displayed_scalar_count':20,
 'findings':[
  {'key':'mgs2026v2','status':'selected_fields_supported','details':'The v2 header and six-author byline match the selected citation. Depth prior, 336-pixel inference and four Table 1 own-row values match the draft. DOI registration and all bibliography fields were not independently checked.'},
  {'key':'infogeo2026','status':'selected_fields_and_own_rows_supported','details':'The accessed PDF identifies v5. Its author byline uses Maonan Wang and Man On Pun, supporting the local spellings despite index/README discrepancies. Sixteen displayed Table 9 values, 448-pixel input, University-to-SUES transfer and Drone-to-Satellite direction agree. Star denotes relational distillation. The paper footer states ICML 2026/PMLR 306, but the draft deliberately cites the versioned arXiv record; no publication-reference replacement is established here.'},
  {'key':'mobilegeo2026','status':'not_newly_verified','details':'Direct primary paper/repository retrieval was unsuccessful. Third-party summaries were not adopted. Existing core/MSRM entries remain inherited and unmodified, not newly verified.'}
 ],
 'source_discrepancy_not_merged':'InfoGeo Table 5 has a different ablation AP for an intermediate configuration. This audit retains explicitly cited Table 9 and does not substitute or average across tables.',
 'correction_required_for_reviewed_values':False,'manuscript_changed':False,'science_executed':False,
 'visual_pdf_review':False,
 'limits':[
  'Only listed fields and 20 displayed source-paper values were checked. This is not a full bibliography, implementation, protocol-equivalence or statistical audit.',
  'Author-reported literature values remain distinct from local author-weight reevaluation and independent training, which are pending.',
  'Unversioned InfoGeo URL was accepted for this reading because its actual retrieved header explicitly states v5. No immutable local PDF byte hash was captured.',
  'Screenshot request for the table failed; another screenshot returned no model-visible image. No visual PDF inspection is claimed.',
  'The web retrieval interval is bounded by the saved current observation at 04:09:29Z and this record time; exact per-request clock times were not captured.',
  'No inaccessible primary source was treated as evidence of a wrong citation. No old scientific suite, checkpoint, image corpus, cache, NPZ or large archive was read.'
 ]}
records=[save('PREPRINT_REVIEW.json',report)]
note='''# 两条预印本文献及20个原报显示值的局部复核

本轮从原始来源确认 MGS2-Net v2 的六名作者、depth prior/336 输入和 Table 1 四值；InfoGeo 实际 PDF 标明 v5，两条 Table 9 自身方法行共16值、448输入、训练→测试方向和 RD 解释与现稿一致。这些仍是文献原报，不是本地模型结果。只读了相关片段，没有全文科学审查或成功 PDF 看图。

InfoGeo PDF 的作者拼写支持当前 Maonan Wang / Man On Pun；搜索索引和仓库 BibTeX 的不同拼写未被自动采用。PDF 页脚出现 ICML 2026 / PMLR 306，当前明确指定的 arXiv v5 引用保持，不据此猜测正式会议页码。

MobileGeo 原始来源直接访问失败，本轮不新增验收其数值或元数据。未采用第三方总结，也未因访问失败判错。现稿/封存包/Overleaf均未改写；无新实验。详 PREPRINT_REVIEW.json 的范围和访问实况。
'''
with (HERE/'REVIEW.md').open('x',encoding='utf-8',newline='\n') as f:f.write(note)
records+=[bind(HERE/'REVIEW.md'),bind(__file__)]
print(json.dumps(save('DELIVERY.json',{'scope':'New limited literature review only','records':records,'inputs':inputs,'manuscript_changed':False}),ensure_ascii=False))
