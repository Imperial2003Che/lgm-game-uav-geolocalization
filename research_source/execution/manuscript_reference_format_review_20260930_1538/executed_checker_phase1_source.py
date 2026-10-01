from pathlib import Path
from datetime import datetime, timezone
import re, json, hashlib, difflib
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914')
ex=base/'execution/manuscript_reference_format_20260930_1538'
out=base/'execution/manuscript_reference_format_review_20260930_1538'
parent=base/'manuscript_citation_revision_20260930_0520/manuscript'
newdir=base/'manuscript_reference_format_20260930_1538/manuscript'

def read(p):
 assert p.stat().st_size<=131072, str(p)
 return p.read_bytes()
def desc(p,b):
 return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
raw_before=read(parent/'refs.bib');raw_after=read(newdir/'refs.bib')
abrvp=Path(r'C:\Users\17703\AppData\Local\Programs\MiKTeX\bibtex\bib\ieeetran\IEEEabrv.bib'); abrv=read(abrvp)
specs=[('IEEE_J_GRS','IEEE Transactions on Geoscience and Remote Sensing','{IEEE} Trans. Geosci. Remote Sens.',10),('IEEE_J_CASVT','IEEE Transactions on Circuits and Systems for Video Technology','{IEEE} Trans. Circuits Syst. Video Technol.',6),('IEEE_J_IP','IEEE Transactions on Image Processing','{IEEE} Trans. Image Process.',1)]
restored=raw_after; expected=raw_before; checks=[]
for macro,full,short,count in specs:
 installed=re.search(rb'@STRING\{'+macro.encode()+rb'\s*=\s*"([^"]+)"\}',abrv).group(1)
 oldtoken=('journal = {'+full+'},').encode(); newtoken=('journal = {'+short+'},').encode()
 checks.append({'macro':macro,'abbreviation':short,'matches_installed_value':installed==short.encode(),'before_count':raw_before.count(oldtoken),'after_count':raw_after.count(newtoken),'expected_count':count})
 restored=restored.replace(newtoken,oldtoken); expected=expected.replace(oldtoken,newtoken)
assert all(c['matches_installed_value'] and c['before_count']==c['after_count']==c['expected_count'] for c in checks)
assert restored==raw_before and expected==raw_after
patch=''.join(difflib.unified_diff(raw_before.decode().splitlines(keepends=True),raw_after.decode().splitlines(keepends=True),fromfile='adopted_parent/refs.bib',tofile='new_draft/refs.bib')).encode()
assert patch==read(ex/'REFS_ONLY.patch')
keys=lambda raw: re.findall(rb'^@\w+\{([^,]+),',raw,re.M)
assert keys(raw_before)==keys(raw_after)
record=json.loads(read(ex/'REFERENCE_FORMAT_REVISION.json'))
text_checks=[]; inherited_not_read=[]
for c in record['inherited_copies']:
 p=Path(c['new_copy']['path']); op=Path(c['inherited_parent']['path'])
 if p.suffix.lower() in ('.tex','.bib','.py','.md'):
  a=read(op);b=read(p)
  text_checks.append({'relative':c['relative'],'equal_bytes':a==b,'old':desc(op,a),'new':desc(p,b)})
 else: inherited_not_read.append({'relative':c['relative'],'basis':'revision manifest records only; no content read or independent hash'})
assert len(text_checks)==21 and all(c['equal_bytes'] for c in text_checks)
cp=base/'execution/manuscript_compile_20260930_0202/compile_working_draft.py';cn=ex/'compile_main_only.py'
cpraw=read(cp);cnraw=read(cn)
ce=cpraw.replace(b"for name in ('main', 'supplementary'):",b"for name in ('main',):").replace(b'Compile the new, multi-file local manuscript; no packages or science run.',b'Compile only the newly changed main bibliography; unchanged supplement inherited.')
assert ce==cnraw
compile_patch=''.join(difflib.unified_diff(cpraw.decode().splitlines(keepends=True),cnraw.decode().splitlines(keepends=True),fromfile='original/compile_working_draft.py',tofile='new/compile_main_only.py')).encode()
assert compile_patch==read(ex/'COMPILE_SOURCE.patch')
report={'schema':'lgm.independent.reference-format-delta-review.v1','reviewed_utc':datetime.now(timezone.utc).isoformat(),'scope':'Only current journal-title formatting delta. No scientific revalidation or source graph adoption.','reviewer':'/root/audit_and_venues','status':'source_delta_pass_bbl_comparison_pending_root_compile','source_artifacts':[desc(parent/'refs.bib',raw_before),desc(newdir/'refs.bib',raw_after),desc(abrvp,abrv),desc(ex/'REFS_ONLY.patch',patch),desc(cp,cpraw),desc(cn,cnraw),desc(ex/'COMPILE_SOURCE.patch',compile_patch),desc(ex/'derive_reference_format.py',read(ex/'derive_reference_format.py'))],'abbreviation_checks':checks,'changed_journal_fields':17,'bibtex_entries_before':len(keys(raw_before)),'bibtex_entries_after':len(keys(raw_after)),'bibtex_entry_order_and_keys_identical':True,'forward_exact_bytes':expected==raw_after,'reverse_exact_bytes':restored==raw_before,'preserved_refs_before_exact_bytes':read(ex/'refs.before.bib')==raw_before,'refs_diff_recomputed_exact':patch==read(ex/'REFS_ONLY.patch'),'line_endings_before':{'CRLF':raw_before.count(b'\r\n'),'LF_total':raw_before.count(b'\n')},'line_endings_after':{'CRLF':raw_after.count(b'\r\n'),'LF_total':raw_after.count(b'\n')},'independent_text_dependency_byte_checks':text_checks,'manifest_only_inherited_files_not_read':inherited_not_read,'compiler_source_only_two_expected_changes':ce==cnraw,'compiler_patch_recomputed_exact':compile_patch==read(ex/'COMPILE_SOURCE.patch'),'executed_producer':False,'executed_compiler':False,'adopted_upstream_complete_source_graph':False,'checked_scientific_values':False,'read_weights_npz_cache_images_archives':False,'pdf_visual_review_performed':False,'root_responsibilities':['actual main-only compile and logs','10 scientific figure PDF byte inheritance and supplementary PDF inheritance','PDF page/layout review','final adoption and any scientific readiness assessment'],'bbl_comparison':{'status':'pending_root_compile','expected_main_bibitems':42}}
(out/'INDEPENDENT_FORMAT_REVIEW.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md='''# 本轮参考文献格式差异独立核查

结论：本轮源文件差异检查通过。仅 `refs.bib` 的 17 个 `journal` 字段变为本机 IEEE 标准缩写；尚待根任务完成实际主文编译后核对生成的 42 条正文参考文献。本报告不证明实验结果、论文整体质量或投稿就绪。

## 独立完成的检查

| 项目 | 独立结果 |
|---|---|
| IEEE_J_GRS | `{IEEE} Trans. Geosci. Remote Sens.`，10 项；等于安装的 IEEEabrv.bib 第 262 行 |
| IEEE_J_CASVT | `{IEEE} Trans. Circuits Syst. Video Technol.`，6 项；等于第 128 行 |
| IEEE_J_IP | `{IEEE} Trans. Image Process.`，1 项；等于第 220 行 |
| refs 全差异 | 全部 17 组变化均为 journal 字段；独立重建 diff 与 REFS_ONLY.patch 字节相同 |
| 精确逆变换 | 撤回三个缩写的 17 次替换后，与旧 refs.bib 全部 21,188 字节相同；保存的 refs.before.bib 也相同 |
| 引用库 | 52 个 BibTeX 条目、键和顺序保留；未删引用、改作者、题名、年份、DOI、页码等其他字段 |
| 主文及文本依赖 | main.tex 和本轮 manifest 所列 21 个文本依赖逐字节相同；表格数值仅做字节比较，未重算或解释 |
| 字号与科学协议 | main.tex 及相关文本依赖未改，因此本轮未引入字号、版心、引用内容或科学协议变化 |
| 换行 | 前后均为 571 个 CRLF、583 个总 LF，换行字节保留 |
| 编译器差异 | 只有说明字符串和文档循环由 main+supplementary 改为 main 两处；独立 diff 与 COMPILE_SOURCE.patch 相同 |

旧 refs.bib SHA-256：`5aa4d85644e26e04f5d2895389d72c2e2cd8d63eeffc59613115f8b527e526e7`。新 refs.bib SHA-256：`d868d592aa6510d7b7ecdce5aaa8f1beda6ed0cae380b9acc20e6e970390702e`。主文前后共同 SHA-256：`fe0dc1a9c03995ea1ad35d5660ccfd3f28749c06d306c0b82d0f2bbc7dd7b07e`。

已完整阅读 REFS_ONLY.patch、refs.bib、derive_reference_format.py、两份 compiler 源及编译差异。derive 脚本只把安装缩写的值写入 journal 字段，未新增宏依赖；编译器保留禁用自动安装和 shell escape 的参数，仍为 pdflatex→bibtex→pdflatex→pdflatex，但仅作用于 main。阅读和比较源代码不等于执行编译。本独立核查没有运行 producer 或 compiler。

## 根任务职责与本报告边界

本轮 manifest 的“其他 31 个源依赖”包含 21 个文本依赖和 10 个科学图 PDF。本独立检查直接比对了前者；后者及沿用的 supplementary.pdf 仅读取本轮 manifest 的继承记录，没有读取图像内容或独立验证其 PDF 字节。根任务负责这些文件的继承证明、一次真实主文编译、编译日志、最终 PDF 页面检查和本轮采用决定。

没有采用上游完整 source graph，没有重验 484 个数值或旧 suite，没有读取权重、NPZ、cache、图像语料或 ZIP，没有重新做科学审稿。上述“未改”仅是相对于指定父版本的差异结论，不构成原有内容正确性的证明。

## 编译产物有限检查

待根任务明确实际编译完成后，比较父版与新版 main.bbl 的条目数、键和顺序，并确认变化只来自上述期刊缩写；PDF 视觉检查仍由根任务负责。
'''
(out/'INDEPENDENT_FORMAT_REVIEW.md').write_text(md,encoding='utf-8')
print(json.dumps({'report':str(out/'INDEPENDENT_FORMAT_REVIEW.md'),'json':str(out/'INDEPENDENT_FORMAT_REVIEW.json'),'status':report['status']},ensure_ascii=False))
