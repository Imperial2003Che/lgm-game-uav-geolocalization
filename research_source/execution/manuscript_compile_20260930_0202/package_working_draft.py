"""Seal this actual local working manuscript, its small inputs and review records."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, zipfile

HERE = Path(__file__).resolve().parent
EX = HERE.parent
OUT = EX.parent
DEST = OUT/'manuscript_evidence_revision_20260930_0202'
M = DEST/'manuscript'
AUTHOR = EX/'manuscript_revision_scope_20260930_0202'
REVIEW = EX/'manuscript_evidence_review_20260930_0202'

def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def bind(p):
    b = p.read_bytes()
    return {'path':str(p), 'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}

def write(p, obj):
    with p.open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')

def verify(b):
    actual = bind(Path(b['path']))
    assert actual['bytes'] == b['bytes'] and actual['sha256'] == b['sha256'], b['path']
    return actual

revision = load(AUTHOR/'layout_revision_a1/REVISION.json')
final_sources = [verify(b) for b in revision['final_sources']]
assert len(final_sources) == 32
content = load(REVIEW/'CONTENT_REVIEW.json')
assert content['passed'] is True and not content['unresolved_content_findings']
assert all(x['passed'] is True for x in content['seal_checks'])
assert len(content['final_text_source_bindings']) == 23
for b in content['final_text_source_bindings']:
    verify(b)
method_addendum = load(REVIEW/'REVIEW_METHOD_ADDENDUM.json')
assert method_addendum['checks_rerun'] is False and method_addendum['manuscript_modified'] is False
assert 'AI agent' in method_addendum['corrected_method']
for b in method_addendum['original_bindings']:
    verify(b)
numeric = load(REVIEW/'NUMERIC_TRANSCRIPTION_REVIEW.json')
assert numeric['passed'] is True and numeric['scalar_count'] == 484
compilation = load(HERE/'attempt_2/COMPILE.json')
assert compilation['status'] == 'compiled' and compilation['input_texts_unchanged'] is True
assert len(compilation['commands']) == 8 and all(c['exit_code'] == 0 for c in compilation['commands'])
for b in compilation['input_texts'] + compilation['outputs']:
    verify(b)
layout = load(HERE/'preview_2/PDF_LAYOUT.json')
assert [x['page_count'] for x in layout['documents']] == [16,6]
for d in layout['documents']:
    verify(d['pdf'])
    assert not any('Overfull' in x or 'undefined' in x.lower() for x in d['latex_diagnostics'])
    assert all(not p['out_of_page_spans'] and p['unresolved_double_question_marks'] == 0 for p in d['pages'])
visual = load(HERE/'ROOT_VISUAL_REVIEW.json')
assert visual['all_final_pages_actually_viewed'] is True and visual['accepted_pages'] == 22
assert visual['new_scientific_validation'] is False

readme = '''# LGM-GAME 本地论文更新 — 2026-09-30

正文 16 页，补充材料 6 页。已整合采用的官方全任务结果、双向迁移、seed-1 敏感性及扰动和 clean-query 诊断说明，并同步修订摘要、贡献、讨论和结论。五张新增表的 484 个显示数值经独立逐项对照原表；主文和补充材料实际编译通过，22 页完成逐页预览。

打开 manuscript/main.pdf 与 manuscript/supplementary.pdf；可编辑 LaTeX 源在同目录。source_data/ 保存本文新增结果表和诊断说明所依据的小表，provenance/ 保存作者变更、独立内容审与实际编译/预览记录。根验收和 ZIP 校验位于压缩包旁的 ROOT_MANUSCRIPT_ADOPTION.json；包内 PACKAGE_MANIFEST.json 绑定除它自身以外的所有成员。原记录中的绝对路径及旧相对路径用于追溯本机来源，压缩包中的对应副本以本清单为准。

主文完整保留 Full 在官方 10/11 任务的三 seed 平均 R@1/mAP 较低、迁移全部 11 任务平均 R@1 较低的结果。sample SD、单 seed 扰动、Full cached-clean/online-corrupt 路径、各 query 指标分母及未独立重采样的限制均保留。此次只是已有证据的论文整合，没有新增模型实验、重算均值/SD/CI、全排名或 AP。历史 public-baseline 分析仍单列，文献表和旧图沿用原稿，未在本次重新验收其科学结果或更新文献。

这是可供合作讨论的本地工作稿。T6、LOHO 24 fit/192 task、后继基线与独立比较、真实解释图、其余 Visio、效率及最终投稿修订仍待完成。Overleaf 现有审阅项目未更新。这份论文更新形成于先前 60.47 GB 完整合作伙伴包冻结之后，可作为补充文件交付；原完整 ZIP 保持不变。

实际使用本机 MiKTeX 的 pdflatex → bibtex → pdflatex → pdflatex，禁自动安装和 shell escape，见 provenance/compile/。首次编译的排版问题及其三项修订已保留；最终没有 Overfull、未定义引用或缺失交叉引用，仍有 Underfull 排版提示。作者 README 中“另行编译”描述源冻结时分工，实际结果以本说明和最终编译记录为准。嵌套 build.py 是原稿辅助程序，本次未执行；重建需现有 TeX 环境。
'''
readme_path = DEST/'README.md'
with readme_path.open('x', encoding='utf-8') as f:
    f.write(readme)

entries = {}
def add(p, arc):
    p = Path(p)
    assert arc not in entries and not arc.startswith('/') and '..' not in Path(arc).parts
    assert p.is_file()
    entries[arc] = p

for b in final_sources:
    p = Path(b['path'])
    add(p, 'manuscript/'+p.relative_to(M).as_posix())
for name in ('main.pdf','supplementary.pdf','main.bbl','supplementary.bbl','README_LOCAL_WORKING_DRAFT.md'):
    add(M/name, 'manuscript/'+name)
add(readme_path, 'README.md')
for tree, arcroot in ((AUTHOR,'provenance/author'),(REVIEW,'provenance/independent')):
    for p in sorted(tree.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            add(p, arcroot+'/'+p.relative_to(tree).as_posix())
for name in ('compile_working_draft.py','render_and_inspect_pdf.py','record_root_visual.py','package_working_draft.py','ROOT_VISUAL_REVIEW.json'):
    add(HERE/name, 'provenance/compile/'+name)
for dirname in ('attempt_1','attempt_2'):
    for p in sorted((HERE/dirname).iterdir()):
        if p.is_file() and p.suffix != '.pdf':
            add(p, 'provenance/compile/'+dirname+'/'+p.name)
add(HERE/'preview_2/PDF_LAYOUT.json', 'provenance/compile/preview_2/PDF_LAYOUT.json')
for d in layout['documents']:
    add(Path(d['extracted_text']['path']), 'provenance/compile/preview_2/'+Path(d['extracted_text']['path']).name)
    for page in d['pages']:
        p = Path(page['png']['path'])
        verify(page['png'])
        add(p, 'previews/'+p.name)
inputs = {
    'official_university.csv': OUT/'formal_results/formal_main_university1652_variants_source.csv',
    'official_sues.csv': OUT/'formal_results/formal_main_sues200_variants_source.csv',
    'sensitivity.csv': OUT/'formal_results/formal_sensitivity_source.csv',
    'transfer_summary.csv': OUT/'transfer_native_figures_20260929_1750/output/source_data/THREE_SEED_SUMMARY.csv',
    'transfer_full_minus_visual.csv': OUT/'transfer_native_figures_20260929_1750/output/source_data/FULL_MINUS_VISUAL.csv',
    'robustness_all_tasks.csv': EX/'pipeline_post_robustness_audit_20260929_1448/a1/aggregate/source_data/robustness_all_tasks_source.csv',
    't4_strata.csv': EX/'pipeline_post_robustness_audit_20260929_1448/a1/query/transactions_t4_strata.csv',
    't5_selective_calibration.json': EX/'pipeline_post_robustness_audit_20260929_1448/a1/query/transactions_t5_selective_calibration.json',
}
for name,p in inputs.items():
    add(p,'source_data/'+name)

manifest = {'schema':'local-working-manuscript-package.v1','utc':datetime.now(timezone.utc).isoformat(),
            'scope':'Local manuscript update with existing evidence; not a complete project or final submission package.',
            'members': [{'archive_path':arc, **bind(p)} for arc,p in sorted(entries.items())],
            'manifest_self_excluded':True}
manifest_path = DEST/'PACKAGE_MANIFEST.json'
write(manifest_path,manifest)
add(manifest_path,'PACKAGE_MANIFEST.json')
archive = DEST/'LGM_GAME_Local_Evidence_Draft_20260930.zip'
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
    for arc,p in sorted(entries.items()):
        z.write(p,arc)
verified=[]
with zipfile.ZipFile(archive) as z:
    assert len(z.namelist()) == len(entries) and set(z.namelist()) == set(entries)
    for arc,p in sorted(entries.items()):
        data=z.read(arc)
        b=bind(p)
        assert len(data)==b['bytes'] and hashlib.sha256(data).hexdigest()==b['sha256'],arc
        verified.append({'archive_path':arc,'bytes':len(data),'sha256':b['sha256'],'crc32':z.getinfo(arc).CRC})
report={'schema':'local-manuscript-delivery-package-check.v1','utc':datetime.now(timezone.utc).isoformat(),
        'archive':bind(archive),'manifest':bind(manifest_path),'members':verified,'passed':True,
        'page_counts':[16,6], 'scientific_execution':False,'overleaf_updated':False,
        'prior_partner_full_archive_accessed_or_modified':False}
write(HERE/'PACKAGE_CHECK.json',report)
print(json.dumps({'archive':report['archive'],'members':len(verified),'report':str(HERE/'PACKAGE_CHECK.json')},ensure_ascii=False))
