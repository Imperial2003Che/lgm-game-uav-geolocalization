from pathlib import Path
from datetime import datetime, timezone
import re,json,hashlib,difflib
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914')
p=base/'manuscript_citation_revision_20260930_0520/manuscript/main.bbl'; n=base/'manuscript_reference_format_20260930_1538/manuscript/main.bbl'
out=base/'execution/manuscript_reference_format_review_20260930_1538'
a=p.read_bytes();b=n.read_bytes()
assert len(a)<131072 and len(b)<131072
pat=rb'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}'
ka=re.findall(pat,a);kb=re.findall(pat,b);assert ka==kb and len(ka)==42
normalize=lambda x:re.sub(rb'\s+',b' ',x).strip()
specs=[('IEEE_J_GRS',b'IEEE Transactions on Geoscience and Remote Sensing',b'{IEEE} Trans. Geosci. Remote Sens.'),('IEEE_J_CASVT',b'IEEE Transactions on Circuits and Systems for Video Technology',b'{IEEE} Trans. Circuits Syst. Video Technol.'),('IEEE_J_IP',b'IEEE Transactions on Image Processing',b'{IEEE} Trans. Image Process.')]
na=normalize(a);nb=normalize(b);expected=na;counts=[]
for macro,full,short in specs:
 old=b'\\emph{'+full+b'}';new=b'\\emph{'+short+b'}'
 counts.append({'macro':macro,'before_cited_occurrences':na.count(old),'after_cited_occurrences':nb.count(new)})
 expected=expected.replace(old,new)
assert expected==nb
sa=re.split(pat,a);sb=re.split(pat,b)
changed=[];unchanged=[]
for i in range(1,len(sa),2):
 key=sa[i].decode()
 if sa[i+1]==sb[i+1]:unchanged.append(key)
 else:changed.append(key)
assert len(changed)==15 and len(unchanged)==27
patch=''.join(difflib.unified_diff(a.decode().splitlines(keepends=True),b.decode().splitlines(keepends=True),fromfile='parent/main.bbl',tofile='new/main.bbl')).encode()
(out/'BBL_ONLY.patch').write_bytes(patch)
def desc(p,b):return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
r=json.loads((out/'INDEPENDENT_FORMAT_REVIEW.json').read_text(encoding='utf-8'))
r['status']='source_delta_and_bbl_preservation_pass'
r['reviewed_utc']=datetime.now(timezone.utc).isoformat()
r['bbl_comparison']={'status':'pass','parent':desc(p,a),'new':desc(n,b),'old_main_bibitem_count':42,'new_main_bibitem_count':42,'identical_ordered_bibitem_keys':[x.decode() for x in kb],'abbreviation_counts_in_cited_bbl':counts,'only_expected_journal_substitutions_after_normalizing_physical_whitespace':True,'changed_entry_keys':changed,'byte_identical_entry_keys':unchanged,'changed_entry_count':15,'byte_identical_entry_count':27,'bibtex_library_entries':52,'scope_note':'Source library contains 52 entries; main BBL contains 42 cited entries. 17 changed library journal fields correspond to 15 changed cited entries; rsloc820k2025 and jointkeypoint2022 are not in main BBL.','actual_compile_executed_by':'root','root_reported_compile':'main-only pdflatex/bibtex/pdflatex/pdflatex, all exit 0, 2026-09-30 14:50:23-14:50:26 UTC','actual_compile_independently_rerun':False,'pdf_visual_review_performed':False,'bbl_diff':desc(out/'BBL_ONLY.patch',patch)}
(out/'INDEPENDENT_FORMAT_REVIEW.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md=(out/'INDEPENDENT_FORMAT_REVIEW.md').read_text(encoding='utf-8')
md=md.replace('结论：本轮源文件差异检查通过。仅 `refs.bib` 的 17 个 `journal` 字段变为本机 IEEE 标准缩写；尚待根任务完成实际主文编译后核对生成的 42 条正文参考文献。','结论：本轮源文件差异和编译后正文引用保留检查通过。仅 `refs.bib` 的 17 个 `journal` 字段变为本机 IEEE 标准缩写；实际编译后的 42 条正文参考文献全部保留、顺序一致。')
md=md.replace('待根任务明确实际编译完成后，比较父版与新版 main.bbl 的条目数、键和顺序，并确认变化只来自上述期刊缩写；PDF 视觉检查仍由根任务负责。','''根任务报告已在 2026-09-30 14:50:23–14:50:26 UTC 完成一次 main-only 四命令编译，全部 exit 0。本独立检查没有重复编译，随后直接比较了两份 main.bbl：

- 父版与新版均为 42 个 bibitem，键与顺序完全相同。
- 27 条引用的对应 BBL 内容逐字节相同；15 条仅有期刊缩写及 BibTeX 物理折行调整。对完整 BBL 统一物理空白后，仅替换上述期刊名即可得到完全相同内容。
- 15 条变化为 GRS 9 条、CASVT 6 条，IP 0 条。库中另两条格式变化对应 rsloc820k2025 与 jointkeypoint2022，二者原本就未出现在本次正文 BBL，不是本轮删引。
- 52 个引用库条目、17 个 journal 字段变化和 42 条正文引用是不同统计口径，不应混写。
- 完整 BBL 差异保存在 BBL_ONLY.patch。PDF 视觉检查及页数、版面结果仍由根任务负责，本报告不据 BBL 比较断言视觉质量。
''')
(out/'INDEPENDENT_FORMAT_REVIEW.md').write_text(md,encoding='utf-8')
print(json.dumps({'status':r['status'],'bbl_items':len(kb),'changed_bbl_entries':len(changed),'byte_identical_bbl_entries':len(unchanged),'cited_counts':counts,'parent_bbl_sha256':hashlib.sha256(a).hexdigest(),'new_bbl_sha256':hashlib.sha256(b).hexdigest()},ensure_ascii=False))
