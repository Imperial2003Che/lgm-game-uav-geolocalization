from pathlib import Path
import json,csv,re,hashlib,datetime
D=Path(__file__).resolve().parent
EX=D.parent
M=EX.parent/'manuscript_evidence_revision_20260930_0202'/'manuscript'
def bind(p):
 p=Path(p); b=p.read_bytes(); return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def out(name,obj):
 p=D/name
 with p.open('x',encoding='utf-8',newline='\n') as f: json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
 return bind(p)
def txt(name,value):
 with (D/name).open('x',encoding='utf-8',newline='\n') as f:f.write(value)
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
texts=sorted([*M.rglob('*.tex'),*M.rglob('*.bib')])
assert all(p.stat().st_size<1024*1024 for p in texts)
match=[]
for p in texts:
 for n,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
  if re.search(r'\b(?:CAMP|DAC)\b',line,re.I):match.append({'path':str(p),'line':n,'text':line})
assert not match
localextra=[EX/'camp_preparation'/'README.md',EX/'dac_preparation'/'EVALUATION_README.md']
out('LOCAL_INPUTS.json',{'generated_utc':now,'input_scope':'all local manuscript .tex/.bib text only, plus two adapter explanatory README files; no weight/cache/NPZ/large archive access','manuscript_inputs':[bind(p) for p in texts],'adapter_inputs':[bind(p) for p in localextra],'case_insensitive_word_boundary_CAMP_DAC_matches':match,'search_tool_exit1_means_no_matches':True})
methods={
'CAMP':{'authors':['Qiong Wu','Yi Wan','Zhi Zheng','Yongjun Zhang','Guangshuai Wang','Zhenyang Zhao'],'title':'CAMP: A Cross-View Geo-Localization Method Using Contrastive Attributes Mining and Position-Aware Partitioning','journal':'IEEE Transactions on Geoscience and Remote Sensing','year':2024,'volume':'62','number':None,'article_number':'5637614','physical_pages':14,'bibliographic_page_range':'1--14','doi':'10.1109/TGRS.2024.3448499','published_online':'2024-08-23','current_version_date':'2024-09-03','metadata_location':'PDF page 1 header, title, author list, DOI and first-page publication footnote; physical page count via pdfinfo','pdf':'camp.pdf','pdf_url':'https://skyearth.org/publication/papers/2024_acvglmucampap.pdf','publisher_url':'https://ieeexplore.ieee.org/document/10644040/','repository':'https://github.com/Mabel0403/CAMP','project_pinned_commit':'b04a9c856711770ed7a72ebf851838329c5e5b8e','published_version':'author-hosted IEEE typeset version of record; not labelled arXiv/preprint','arxiv_version':'not established; exact-title arXiv searches did not identify an applicable preprint, which does not prove nonexistence','protocol_paper':['Two image views: drone and satellite. ConvNeXt-B shared backbone.','Section IV-B: 384-square inputs, training batch 24, AdamW, initial learning rate 0.001, cosine schedule, one-epoch warmup as printed.','Section IV-D: University-1652 training to SUES-200 testing; controlled comparison explicitly says batch 48.','AP is the paper label; Eq.(7) displays recall-increment weighted precision. Section IV-B testing says Euclidean distance. Do not infer equality to every local trapezoidal-AP/cosine implementation.'],'protocol_locations':['PDF p7, sections IV-A/B/C and Table I','PDF p8, Table II and IV-D','PDF p9, Table III'],'pretraining_scope':'Paper IV-B identifies ConvNeXt-B but does not identify its pretraining dataset. Pinned train_university.py names convnext_base.fb_in22k_ft_in1k_384 at line41 but defaults handcraft_model=True at42; this string alone does not validate actual loaded pretrained weights.'},
'DAC':{'authors':['Panwang Xia','Yi Wan','Zhi Zheng','Yongjun Zhang','Jiwei Deng'],'title':'Enhancing Cross-View Geo-Localization With Domain Alignment and Scene Consistency','journal':'IEEE Transactions on Circuits and Systems for Video Technology','year':2024,'volume':'34','number':'12','article_number':None,'physical_pages':11,'bibliographic_page_range':'13271--13281','doi':'10.1109/TCSVT.2024.3443510','published_online':'2024-08-14','current_version_date':'2024-12-23','metadata_location':'PDF page 1 header, title, author list, DOI and publication footnote; last page header 13281; physical page count via pdfinfo','pdf':'dac.pdf','pdf_url':'https://skyearth.org/publication/papers/2024_ecvglwdasc.pdf','publisher_url':'https://ieeexplore.ieee.org/document/10636268/','repository':'https://github.com/SummerpanKing/DAC','project_pinned_commit':'5612a79c3928d8a71939e4e761bb352f805cb51b','published_version':'author-hosted final IEEE issue version, volume34 issue12 December2024; not just early access','arxiv_version':'not established; exact-title arXiv search gave no applicable record, not proof of nonexistence','protocol_paper':['Drone/satellite retrieval uses a ConvNeXt-Base backbone pretrained on ImageNet-22k.','Section IV-B: 384-square inputs; batch24 means 24 drone plus24 satellite images (48 total); AdamW with initial learning rate0.001, cosine scheduler and first10% warmup.','Section IV-D: University-1652 training to SUES-200 test, with ConvNeXt-B/384/batch equivalent48. SUES-trained-to-University transfer is not this experiment.','Table III Multi-weather University-1652 is separate from same-domain Table I and cross-region Table IV; its normal row is not interchangeable with Table I.'],'protocol_locations':['PDF p7, printed13277, sections IV-B/C/D and Table I','PDF p8, printed13278, Table II and III','PDF p9, printed13279, Table IV'],'pretraining_scope':'ImageNet-22k is explicitly printed in IV-B. This paper claim is not proof that any local checkpoint is the authors\' exact training run.'}}
for method,x in methods.items():
 x['pdf_binding']=bind(D/x['pdf'])
 x['field_status']={k:'confirmed_from_author_hosted_published_pdf' for k in ['authors','title','journal','year','volume','doi','published_online','current_version_date']}
 x['field_status']['number']='not_applicable_no_issue_given' if method=='CAMP' else 'confirmed_header'
 x['field_status']['article_number']='confirmed_header' if method=='CAMP' else 'not_applicable_continuous_pages'
 x['field_status']['bibliographic_page_range']='physical pagination 1--14 with article number5637614; retain article number separately' if method=='CAMP' else 'confirmed_first_and_last_headers'
# Only these two papers' own named rows, with headings retained; no other method copied.
vals={
'CAMP':{'University same-domain':[[94.46,95.38],[96.15,92.72]],'SUES same-domain':[[95.40,96.38],[97.63,98.16],[98.05,98.45],[99.33,99.46],[96.25,93.69],[97.50,96.76],[98.75,98.10],[100.00,98.85]],'University-to-SUES transfer':[[78.90,82.38],[86.83,89.28],[91.95,93.63],[95.68,96.65],[87.50,78.98],[95.00,87.05],[95.00,91.05],[96.25,93.44]]},
'DAC':{'University same-domain':[[94.67,95.50],[96.43,93.79]],'SUES same-domain':[[96.80,97.54],[97.48,97.97],[98.20,98.62],[97.58,98.14],[97.50,94.06],[98.75,96.66],[98.75,98.09],[98.75,97.87]],'University-to-SUES transfer':[[76.65,80.56],[86.45,89.90],[92.95,94.18],[94.53,95.45],[87.50,79.87],[96.25,88.98],[95.00,92.81],[96.25,94.00]]}}
rows=[]
for method,scopes in vals.items():
 for scope,numbers in scopes.items():
  for i,(r1,ap) in enumerate(numbers):
   uni=scope=='University same-domain'
   direction=['drone_to_satellite','satellite_to_drone'][i if uni else i//4]
   table='I' if uni else ('II' if scope=='SUES same-domain' else ('III' if method=='CAMP' else 'IV'))
   rows.append({'method':method,'result_origin':'published_author_report_only','scope':scope,'retrieval_direction':direction,'height_m':'' if uni else [150,200,250,300][i%4],'R_at_1_percent_as_printed':f'{r1:.2f}','AP_percent_as_printed':f'{ap:.2f}','table':table,'physical_pdf_page':7 if uni else(8 if scope=='SUES same-domain' else 9),'pdf_sha256':methods[method]['pdf_binding']['sha256'],'project_result':False,'project_reproduction_pass':False})
assert len(rows)==36
with (D/'AUTHOR_REPORTED_ROWS.csv').open('x',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
source_differences=[
{'id':'CAMP-warmup','paper':'PDF p7 IV-B says one-epoch warmup','pinned_code':'train_university.py lines103/125/453-455: epochs=1, warmup_epochs=0.1; warmup_steps=train_steps*warmup_epochs','disposition':'Record paper and pinned-code settings separately; do not silently normalize to one recipe or infer author checkpoint training history. No manuscript claim currently requires correction.'},
{'id':'CAMP-batch','paper':'IV-B says24; IV-D spanning PDFp8 says48','pinned_code':'line104 default24 with two-branches help text','disposition':'Label paired-batch count versus total images when future protocol is independently established; do not infer that paper48 necessarily means48 pairs.'},
{'id':'default-code-vs-history','paper':'Journal result rows identify published experiments, not project checkpoint provenance','pinned_code':'Both pinned University CLIs default seed1/epochs1/batch24/eval128; fetched files were never imported or executed','disposition':'Defaults and checkpoint filenames do not establish original training seed, checkpoint selection or achieved score.'},
{'id':'AP-and-gallery','paper':'CAMP Eq7 discrete AP and Euclidean wording; DAC prose area under PR','project_adapter':'Local CAMP README describes retaining distractors rather than author junk filtering, stable ties, cosine and frozen trapezoidal AP; DAC README likewise defines controlled full-gallery evaluation','disposition':'Keep paper AP label and paper-reported rows separate from local official-trapezoidal-mAP values. No identity of all evaluator operations is claimed.'},
{'id':'DAC-multiweather','paper':'TableIII has ten named conditions including normal, with normal D2S92.81/94.06 andS2D97.43/92.90 unlike TableI','repository':'Pinned README states the multi-weather part is not well presented and suggests manual augmentation insertion','disposition':'No equivalence to project six-family/five-severity seed1 corruption protocol; do not substitute TableIII normal for TableI or assert reproduction.'}]
claims=[
{'id':'local-absence','location':'All manuscript .tex/.bib in LOCAL_INPUTS.json','result':'No word-boundary CAMP or DAC and no corresponding refs.bib entry. No existing named numeric attribution error found in this scope.'},
{'id':'local-status','location':'main.tex lines485-489; supplementary.tex lines18-19','result':'Later external comparison and efficiency explicitly remain unfinished; consistent with project queue. No completed author re-evaluation or independent CAMP/DAC training may be inferred.'},
{'id':'future-three-origins','location':'future manuscript comparison tables','result':'Separate literature author reports, controlled author-checkpoint re-evaluation, and independent training; use the latter two only after real completion and acceptance.'},
{'id':'project-SUES-meaning','location':'camp_preparation/README.md and dac_preparation/EVALUATION_README.md','result':'Current prepared author jobs use University checkpoints on University and SUES. SUES would be University-trained checkpoint transfer, neither SUES-trained paper TableII nor proof of replication of separate paper controlled transfer training.'},
{'id':'no-street-extrapolation','location':'Both author tables I/II/transfer','result':'These rows cover drone/satellite directions only; do not infer street-to-satellite results.'},
{'id':'no-uncertainty-pooling','location':'AUTHOR_REPORTED_ROWS.csv','result':'Numbers are literal published point results, not project three-seed means/SD, confidence intervals, statistical significance, or pooling across heights/directions.'}]
report={'schema':'camp-dac-primary-citation-and-attribution-review.v1','created_utc':now,'reviewer':'independent AI subagent reading tool text and rendered source PDF pages; no human review','scope':'Two references not yet present in current local manuscript. Future integration research only. No other bibliography re-audit.','status':'research_complete_no_sealed_manuscript_changes','local_inputs':bind(D/'LOCAL_INPUTS.json'),'methods':methods,'claims':claims,'paper_code_and_project_distinctions':source_differences,'author_reported_rows':bind(D/'AUTHOR_REPORTED_ROWS.csv'),'author_reported_rows_count':36,'author_reported_numeric_values_count':72,'visual_check':{'pages_actual_viewed':['camp p5','camp p6','camp p7','camp p8','camp p9','dac p7','dac p8','dac p9'],'tables_transcribed':'only CAMP/DAC own rows from TableI/II/transfer with headings/directions/heights; six relevant table pages actually viewed','renderer':'Poppler pdftoppm CPU; tool commands returned0, individual command held-exit handles not recorded','diagnostics':['No display font for Symbol','No display font for ArialUnicode'],'claim':'Table numerals and headers were readable. Not whole-paper visual/layout validation; no redrawing or project scientific figure generation.'},'required_future_actions':['Add two verified journal entries and cite them when CAMP/DAC are introduced in a future unsealed revision. No edit needed to an existing CAMP/DAC entry because none exists.','Label paper-reported numbers with source table/version, retain AP wording, and keep away from project completed-result counts.','Document actual accepted local backbone/pretraining/view/source/protocol for future reproduced rows; current published/code defaults do not establish that execution.','Keep source-code warmup/batch discrepancies and protocol differences visible without altering frozen experiments.'],'prohibited_inferences':['No universal SOTA claim imported from either abstract.','No project Full improvement or transfer improvement inferred from these methods.','No paper number used as acceptance threshold, test tuning target or replacement for pending evaluations.','No running/exit status independently audited by this citation task.'],'execution':{'scientific_execution':False,'model_import_or_weight_read':False,'COM':False,'sealed_manuscript_modified':False,'Overleaf_updated':False,'zip_modified':False,'source_code_imported':False,'paper_figures_created':False}}
out('CAMP_DAC_CITATION_REVIEW.json',report)
# Complete journal fields proposed, never inserted into sealed refs.bib.
txt('PROPOSED_REFERENCES.bib','''% Proposed future additions only; not inserted into any manuscript.
@article{camp2024,
  author = {Qiong Wu and Yi Wan and Zhi Zheng and Yongjun Zhang and Guangshuai Wang and Zhenyang Zhao},
  title = {{CAMP}: A Cross-View Geo-Localization Method Using Contrastive Attributes Mining and Position-Aware Partitioning},
  journal = {IEEE Transactions on Geoscience and Remote Sensing},
  year = {2024},
  volume = {62},
  pages = {1--14},
  note = {Art. no. 5637614},
  doi = {10.1109/TGRS.2024.3448499}
}
@article{dac2024,
  author = {Panwang Xia and Yi Wan and Zhi Zheng and Yongjun Zhang and Jiwei Deng},
  title = {Enhancing Cross-View Geo-Localization With Domain Alignment and Scene Consistency},
  journal = {IEEE Transactions on Circuits and Systems for Video Technology},
  year = {2024},
  volume = {34},
  number = {12},
  pages = {13271--13281},
  doi = {10.1109/TCSVT.2024.3443510}
}
''')
out('WEB_TOOL_ACCESS_LEDGER.json',{'time_window_utc':{'lower_bound':'2026-09-30T04:10:31Z','upper_bound':'2026-09-30T04:16:51Z','precision':'Clock bounds for web-tool sequence; exact per-web-request timestamps were not returned and are not invented.'},'initial_searches':['CAMP cross view geolocalization author GitHub paper','DAC cross view geolocalization author GitHub paper'],'primary_successes':[{'url':'https://github.com/Mabel0403/CAMP','mode':'web open current main, 247 lines','use':'official project identification only; pinned raw README fetched separately'},{'url':'https://github.com/SummerpanKing/DAC','mode':'initial indexed search result with official README','use':'source locator, then exact pinned raw README fetched directly'},{'url':'https://ieeexplore.ieee.org/document/10644040/','mode':'initial indexed search metadata','use':'locator; later direct web open Internal Error, published PDF supplies metadata'},{'url':'https://skyearth.org/publication/','mode':'search primary lab publication listing and web open 3277 lines','use':'CAMP author list and author-lab PDF locator; later web find returned no match, not proof of absence'},{'url':'https://skyearth.org/team/members/wuqiong.html','mode':'indexed primary author profile','use':'author affiliation/publication association; direct open failed'}],'web_direct_failures':[{'url':'https://github.com/SummerpanKing/DAC','error':'restricted URL on subsequent direct open'},{'url':'https://skyearth.org/publication/papers/2024_acvglmucampap.pdf','error':'restricted URL via web open; direct urllib later200'},{'url':'https://skyearth.org/publication/papers/2024_ecvglwdasc.pdf','error':'restricted URL via web open; direct urllib later200'},{'url':'https://www.skyearth.org/publication/papers/2024_acvglmucampap.pdf','error':'restricted URL'},{'url':'https://www.skyearth.org/publication/papers/2024_ecvglwdasc.pdf','error':'not accessible via this tool'},{'url':'https://skyearth.org/team/members/wuqiong.html','error':'restricted URL; subsequent urllib406'},{'url':'https://ieeexplore.ieee.org/document/10644040/','error':'Internal Error on direct open'},{'url':'https://ieeexplore.ieee.org/document/10636268/','error':'returned3lines without usable article fields; no successful complete metadata read claimed'},{'url':'https://skyearth.org/publication/','error':'web find CAMP and Enhancing Cross-View returned no matching text, despite earlier indexed listing; subsequent urllib406'}],'secondary_search_hits':'DBLP and assorted aggregators appeared but were not used as final metadata authority. ArXiv searches did not establish an applicable version.','exact_direct_request_times':[bind(D/'DIRECT_PRIMARY_ACCESS.json'),bind(D/'DIRECT_PRIMARY_ACCESS_2.json')],'local_locator_errors':[{'path':str(EX/'dac_independent_science_v1'/'README.md'),'error':'rg path does not exist, exit1; no scientific execution'},{'path':str(EX/'dac_preparation'/'README.md'),'error':'Get-Content path does not exist; corrected to EVALUATION_README.md'}]})
txt('REVIEW.md','''# CAMP / DAC 引用与结果归属核查

本地 20260930 工作稿的全部 .tex/.bib 未出现单词边界 CAMP 或 DAC，refs.bib 也无这两条。因此本轮提供未来补录材料，没有把缺席条目说成已有错误，也未改稿、ZIP 或 Overleaf。

已核两篇作者课题组托管的 IEEE 正式排版 PDF，下载字节和真实访问时间见 DIRECT_PRIMARY_ACCESS.json。CAMP 是 TGRS 62 (2024), Art.5637614, 14页；DAC 是 TCSVT 34(12),13271–13281 (2024)。作者顺序、标题、DOI、在线日期与当前版本日期逐字段记录在 CAMP_DAC_CITATION_REVIEW.json。PROPOSED_REFERENCES.bib 仅为建议追加，未编译或插入。PDF首页和末页/页数元数据提供版本依据；没有建立适用 arXiv 版本。

AUTHOR_REPORTED_ROWS.csv 只转录这两篇论文 Table I、Table II 和各自迁移表的本方法行，共36行/72数值；实际查看了对应六张整页渲染，包含列头、方向、高度。原表 AP 保持 AP，不自动更名为项目梯形 mAP。论文数值均属文献原报，不是本项目复评、独立训练或科学验收。

必须区分论文同域 SUES 表、论文 University→SUES 受控训练迁移表，以及本项目待执行的 University 作者权重完整图库复评。当前任务没有检查或改变这些科学作业状态。CAMP 作者配套代码/项目README说明的 gallery junk、稳定tie和AP口径差异也不能抹平。两论文没有这些表的 street→sat 结果；没有从原报点值推算训练三seed不确定性或显著性。

CAMP 正式论文写 one-epoch warmup，固定作者 University CLI 却是 epochs=1、warmup_epochs=0.1，以总steps相乘；纸面批量24与迁移段48也分源保留，不擅改冻结协议或补造作者训练历史。DAC纸面明确24对/48图与10%warmup。CLI默认或checkpoint文件名不是实际训练记录。CAMP论文没有明确预训练数据集；CLI模型字符串也不足证明默认handcraft分支加载了哪一权重。

DAC多天气表的normal行不同于其TableI，且作者README提示多天气部分展示不完整。本项目6family×5severity不能宣称等于该原报10条件协议。本轮没有复制多天气完整数表或重新检查基础13篇文献。

web直开IEEE/部分作者页面和PDF存在失败，随后标准公开HTTP请求取得两篇PDF和固定commit的README/University脚本。完整失败及时间精度见 WEB_TOOL_ACCESS_LEDGER.json；没有把搜索索引冒充直读。下载的作者脚本仅作为文本，未import/执行。渲染器提示缺少Symbol/ArialUnicode显示字体；表格数字可读，不宣称无诊断或全论文视觉审查。核查由AI代理执行，未声称人工审稿。
''')
artifacts=[p for p in D.iterdir() if p.is_file() and p.name!='DELIVERY.json']
small=[bind(p) for p in sorted(artifacts) if p.suffix.lower() not in {'.pdf','.png'}]
assets=[bind(p) for p in sorted(artifacts) if p.suffix.lower() in {'.pdf','.png'}]
# Recheck only manuscript input bytes just read; no scientific files.
for b in json.loads((D/'LOCAL_INPUTS.json').read_text(encoding='utf-8'))['manuscript_inputs']:assert bind(b['path'])==b
out('DELIVERY.json',{'schema':'camp-dac-citation-research-delivery.v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'primary-literature research only; sealed manuscript untouched; no scientific result acceptance','small_files':small,'downloaded_paper_and_render_assets':assets,'local_inputs_manifest':bind(D/'LOCAL_INPUTS.json'),'review':bind(D/'CAMP_DAC_CITATION_REVIEW.json'),'source':bind(__file__),'checks':{'all_manuscript_tex_bib_no_named_references':True,'manuscript_input_bytes_unchanged':True,'author_rows':36,'author_values':72,'paper_table_pages_actually_viewed':6},'execution_released':False,'scientific_results_adopted':False})
print(json.dumps({'review':bind(D/'CAMP_DAC_CITATION_REVIEW.json'),'delivery':bind(D/'DELIVERY.json'),'manuscript_files_checked':len(texts),'small_artifacts':len(small),'paper_render_assets':len(assets)},ensure_ascii=False,indent=2))
