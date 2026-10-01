from pathlib import Path
from datetime import datetime, timezone
import re, json, hashlib, difflib
BASE=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914')
EX=BASE/'execution/manuscript_reference_format_20260930_1538'
REVIEW=BASE/'execution/manuscript_reference_format_review_20260930_1538'
PARENT=BASE/'manuscript_citation_revision_20260930_0520/manuscript/supplementary.bbl'
NEW=BASE/'manuscript_reference_format_20260930_1538/manuscript/supplementary.bbl'
def read(p):
    assert p.stat().st_size<=32768,str(p)
    return p.read_bytes()
def desc(p,b):
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
a=read(PARENT); b=read(NEW)
pat=rb'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}'
ka=re.findall(pat,a); kb=re.findall(pat,b)
assert ka==kb==[b'mean2025',b'cdmnet2025',b'infogeo2026']
norm=lambda x:re.sub(rb'\s+',b' ',x).strip()
oldjournal=b'\\emph{IEEE Transactions on Geoscience and Remote Sensing}'
newjournal=b'\\emph{{IEEE} Trans. Geosci. Remote Sens.}'
assert norm(a).count(oldjournal)==norm(b).count(newjournal)==2
assert norm(a).replace(oldjournal,newjournal)==norm(b)
sa=re.split(pat,a);sb=re.split(pat,b)
changed=[sa[i].decode() for i in range(1,len(sa),2) if sa[i+1]!=sb[i+1]]
unchanged=[sa[i].decode() for i in range(1,len(sa),2) if sa[i+1]==sb[i+1]]
assert changed==['mean2025','cdmnet2025'] and unchanged==['infogeo2026']
cp=EX/'compile_main_only.py'; cn=EX/'compile_supplement_only.py'
ap=read(cp); an=read(cn)
assert ap.count(b"for name in ('main',):")==1
assert ap.replace(b"for name in ('main',):",b"for name in ('supplementary',):")==an
expected_patch=''.join(difflib.unified_diff(ap.decode().splitlines(keepends=True),an.decode().splitlines(keepends=True),fromfile=str(cp),tofile=str(cn))).encode()
assert expected_patch==read(EX/'SUPPLEMENT_COMPILE_SOURCE.patch')
add_path=EX/'SUPPLEMENT_DEPENDENCY_ADDENDUM.json'; add_raw=read(add_path)
add=json.loads(add_raw)
assert add['initial_inherited_supplement_compile_decision_superseded'] is True
bblpatch=''.join(difflib.unified_diff(a.decode().splitlines(keepends=True),b.decode().splitlines(keepends=True),fromfile='parent/supplementary.bbl',tofile='new/supplementary.bbl')).encode()
(REVIEW/'SUPPLEMENT_BBL_ONLY.patch').write_bytes(bblpatch)
result={'schema':'lgm.independent.supplement-bibliography-format-addendum.v1','utc':datetime.now(timezone.utc).isoformat(),'reviewer':'/root/audit_and_venues','status':'pass','scope':'Only new supplement bibliography dependency and supplement-only compiler delta; main sealed review unchanged.','parent_bbl':desc(PARENT,a),'new_bbl':desc(NEW,b),'ordered_bibitem_keys':[x.decode() for x in kb],'bibitem_count_before':3,'bibitem_count_after':3,'changed_entries':changed,'byte_identical_entries':unchanged,'journal_substitutions':2,'only_expected_journal_substitution_after_normalizing_physical_whitespace':True,'bbl_patch':desc(REVIEW/'SUPPLEMENT_BBL_ONLY.patch',bblpatch),'compiler_parent':desc(cp,ap),'compiler_new':desc(cn,an),'compiler_diff':desc(EX/'SUPPLEMENT_COMPILE_SOURCE.patch',expected_patch),'compiler_only_main_to_supplementary_loop_delta':True,'compiler_docstring_is_inherited_stale_description_not_execution_scope':True,'root_dependency_addendum':desc(add_path,add_raw),'initial_supplement_inheritance_decision_superseded_by_root_addendum':True,'root_actual_compile_reported':'supplementary-only four commands, all exit 0; root tool chunk 43a07d, wall_time_seconds 2.028','independent_actual_compile_or_producer_execution':False,'independent_pdf_or_scientific_review':False,'main_42_item_check_repeated':False,'sealed_main_review_modified':False,'main_17_field_source_check_repeated':False,'weights_npz_cache_image_zip_read':False,'root_responsibility':'actual compile/log/PDF preservation and visual acceptance; independent checker only compares bounded BBL and compiler source delta','checker_source':desc(Path(__file__),read(Path(__file__)))}
(REVIEW/'INDEPENDENT_SUPPLEMENT_FORMAT_ADDENDUM.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md='''# 补充材料参考文献格式独立追加核查

结论：本次补充材料的有限 BBL 与编译器差异检查通过。父版和新版 supplementary.bbl 均为 3 条引用，顺序为 mean2025、cdmnet2025、infogeo2026。

- mean2025、cdmnet2025 仅把期刊名改为 {IEEE} Trans. Geosci. Remote Sens.，伴随 BibTeX 的物理折行调整；统一物理空白后，两处指定期刊替换即可精确得到新版完整 BBL。
- infogeo2026 对应 BBL 内容逐字节相同；没有删除引用、修改引用顺序或更改其他引文内容。
- supplement-only compiler 相对已检查的 main-only compiler 只有循环从 ('main',) 改为 ('supplementary',) 一处；重新构造的完整 diff 与 SUPPLEMENT_COMPILE_SOURCE.patch 字节一致。文件首行沿用旧主文说明字符串，不能作为执行范围；实际代码循环明确为 supplementary。

根任务提供的 SUPPLEMENT_DEPENDENCY_ADDENDUM.json 明确取代初始“补充 PDF 仅继承”的决定，因为补充材料也依赖共享 refs.bib 中的两个 GRS 条目。该 addendum 记录旧 273,353 字节补充 PDF 的保留路径；本独立追加检查没有读取或验证 PDF 字节。根任务报告已另行完成 supplement-only 四命令编译（全部 exit 0，工具 chunk 43a07d）；真实编译、日志、PDF 保留和视觉验收由根任务负责。

本报告只追加这 3 条引用、2 个期刊显示字段及单一 compiler 循环差异。没有重复 42 条主文检查、17 字段源检查或任何数值/科学检查，没有运行 compiler 或 producer，没有读取权重、NPZ、cache、图像语料或 ZIP。已封存的 INDEPENDENT_FORMAT_REVIEW.md/json 保持不变，其中初始补充 PDF 继承边界应连同本追加报告和根的 dependency addendum 一并理解。
'''
(REVIEW/'INDEPENDENT_SUPPLEMENT_FORMAT_ADDENDUM.md').write_text(md,encoding='utf-8')
print(json.dumps({'status':result['status'],'bibitems':3,'journal_substitutions':2,'changed_entries':changed,'unchanged_entries':unchanged,'compiler_single_loop_delta':True,'sealed_main_reports_modified':False},ensure_ascii=False))
