"""Prepare pending delivery wording only, using independently reviewed small metadata."""
from pathlib import Path
import json, hashlib, os
from datetime import datetime, timezone
OUT = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914')
HERE = OUT / 'execution' / 'offline_visio_delivery_scope_20260930_1030'
REVIEW = OUT / 'execution' / 'offline_visio_input_review_20260930_1030'
MAX = 1024 * 1024
bindings = []
def read(path, expected=None):
    if path.stat().st_size > MAX:
        raise RuntimeError('Draft source exceeds declared bounded input')
    before = path.stat()
    with path.open('rb') as stream:
        raw = stream.read(MAX+1)
    after = path.stat()
    if len(raw) != before.st_size or (before.st_size,before.st_mtime_ns) != (after.st_size,after.st_mtime_ns):
        raise RuntimeError('Unstable draft source')
    desc = {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    if expected is not None and desc['sha256'] != expected:
        raise RuntimeError('Draft prior adoption digest mismatch')
    bindings.append(desc)
    return json.loads(raw),desc

def write(name, value):
    raw = (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8') if not isinstance(value,str) else value.encode('utf-8')
    if len(raw) > MAX:
        raise RuntimeError('Draft output too large before CreateNew')
    path = HERE / name
    with path.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

review,review_desc = read(REVIEW/'INPUT_AUTHORITY_REVIEW.json','557bbd1480f57d543628b3da3a1288ada07ae44277c9b363991e72603d42ae2c')
delivery,delivery_desc = read(REVIEW/'DELIVERY.json','af8df41e69edbf68f9b439d58acbdcb4952a6bb337362f5348e6171fa9c4d416')
mapping,map_desc = read(REVIEW/'SVG_AUTHORITY_NOTES_MAP.json')
figures = mapping['figures']
if len(figures) != 68:
    raise RuntimeError('Draft source map must contain 68 independently accepted inputs')
if not delivery['input_scope_accepted'] or delivery['scientific_revalidation']:
    raise RuntimeError('Unexpected input review scope')

readme = '''# 68 图原生 VSDX 补充交付说明——待实物报告后定稿

当前这是交付说明草稿。68 个最终 VSDX 的真实生成、逐文件字节、原生对象总数、输出验收及打包尚未写入本草稿；不能据此称文件已经完成。输入来源审查已通过，实际生成采用意见另行封存。

拟交付范围为 68 个单页 VSDX：T3 双向迁移 2 图、seed 1 扰动 22 图、T4 Visual-margin 分层 11 图、T5 risk–coverage 11 图、T5 fixed-margin reliability 11 图、T5 paired full-N success 11 图。每页沿用已采用 SVG 的 181.9 mm 宽度与各自原高度；输入文字为 Arial、至少 8 pt。计划映射 19945 个原生几何/文字 primitive，此数当前仅为准备声明，须用实际 full 输出报告和独立包内 XML 核查更新。

这些新文件拟由 CPU 程序直接写入 OPC/VSDX 的原生 ShapeSheet 文字和几何对象。生成后若包内对象核查通过，可称“已实际生成原生对象文件”，编辑范围是单独对象；不得据文件结构核查称已在 Visio GUI 中编辑、Excel 联动或应用内往返成功。其采用层级与此前两张主结果 VSDX 分开：旧 University/SUES 主结果两图已通过实际 Visio 创建、保存、关闭、重开和 PNG/PDF 导出；本批 68 图仍待实际 Visio 打开无修复、应用导出、GUI 编辑和往返验证。

拟随附的 CPU 原生 XML 预览应依据新文件中的 ShapeSheet 对象绘制，用于检查文字、坐标、标签、重叠及裁剪。这类预览不是 Visio 实际导出，也不证明 Visio 不请求修复。每页实际 preview 与包内 XML 验收须分别列明；字号和页面宽度仅在原尺寸下有效，后续缩图会缩小文字。

本批只转换已采用图件的表示形式，不重跑训练、模型、ranking、query 统计、均值、SD、AP、ECE、AURC、bootstrap 或其他科学实验。完整原 CAPTIONS、源 CSV/JSON 和 notes 的原字节应随包保留；包内 User.Notes 应带入相应完整原图注。各图来源、单位和局限按六个图件采用根继承，并在最终 INDEX 中逐文件绑定。

## 数据口径必须完整保留

- T3：三 seed 等权均值 ± sample SD（分母 2），不是 SE/CI；R@1/mAP ×100 是百分数，MRR ×100 是 scaled MRR。Full 的 mean R@1 在全部 11 项任务低于 Visual，mAP/MRR 仅 SUES→University street→sat 略正；不跨任务、高度、方向 pool 或暗示显著性。
- 扰动：仅 seed 1；曲线为 100×corrupt/该 variant 自己的 clean metric，非绝对准确率或 pp drop；保留 >100、非单调和低 clean 基线。Full 的 cached-clean 与 online-corrupt 混合了证据路径和像素扰动；64 样本诊断没有等价阈值、bitwise 或排名差可忽略结论。
- T4：只绘 132 个 Visual-margin strata；其余 330 个 entropy/semantic strata 不在本图验收范围。Full 对齐 Visual 后共享 Visual 定义的 mask；48 个 N=20 strata 仅描述，84 个计数门通过不证明显著性；margin 非 posterior，条件不证明因果机制。
- T5 risk：x 为保存 realized k/N，y 为所选 query 内 1−R@1；Visual/Full 分别筛选自己的成员，同 coverage 不等于共同成员。十点线仅引导，不是全前缀曲线积分；保存 all-prefix AURC 是 fraction，不从十点重算。
- T5 reliability：固定 clip(margin/2,0,1) 非 posterior；占用 bin 的 mean score 与 empirical R@1 为 0–1 fraction，空 bin 的 mean/accuracy 保持 null，不补零点；15-bin 人数完整保留。保存 ECE 为 fraction，较低 ECE 不证明较高准确率或更好概率校准；两 variant 的 bin 成员可不同。
- T5 paired：y 为 selected AND correct /共同全 N，非所选 k 内准确率；同 k 可不同成员，overlap 计共同 selected 而非共同 correct。覆盖率增加可机械增加 success，不证明 ranking 改善；四保存 coverage 含真实 75% 行。原 Holm 关系针对 full-N utility，不是不同子集的 selective accuracy 直接检验。

本批继承历史 SHA 链边缺口、当前 metadata 不证明模型/cache/image 当前字节、未重新运行模型/full ranking/全部正样本 AP、未独立 resampling 验收及各图根的所有原限制。query 成对推理不能当作三 seed 训练不确定性，局部正值不能遮盖主结果与迁移负结果。完整任务的 T6、后继比较与效率、LOHO、真实解释图、最终论文/Overleaf及投稿建议仍未由本批补充交付完成。

## 最终包建议内容

68 个实际 VSDX、逐文件 bytes/SHA 和原生对象计数 INDEX、实际 CPU native-XML previews、逐文件完整 notes、原字节 CAPTIONS/源 CSV/JSON/SVG、冻结 input manifest、builder/source diff、实际 BUILD_REPORT、独立输入/包内对象/视觉审查及根采用报告。仅加入已经真实生成且采用的附件；尚无实际 Visio 导出的 PNG/PDF 就不列为 Visio 导出。最终包应另新建并封存，不回写历史两 main VSDX、PPT/SVG、论文或 60.47 GB 合作伙伴包。

## 待实物记录

actual build report: pending
actual generated VSDX count and bytes: pending
actual native primitive count: pending (prepared expectation 19945)
independent output XML/CPU preview review and root adoption: pending
Visio application open without repair / actual export / GUI edit / round-trip: pending
package path/bytes/SHA/member audit: pending
'''

rows = []
for item in figures:
    rows.append({
        'family':item['family'],'id':item['id'],'title':item['title'],
        'accepted_svg':item['svg'],'accepted_graphical_root':item['accepted_graphical_root'],
        'accepted_captions':item['accepted_captions'],'accepted_csv':item['csv_bindings'],
        'actual_vsdx':None,'actual_native_shapes':None,'actual_native_texts':None,
        'actual_cpu_native_xml_preview':None,'actual_visio_export':None,
        'application_open_without_repair':False,'gui_edit_validated':False,'roundtrip_validated':False,
    })
index = {
    'schema':'offline-native-visio-delivery-index-draft.v1',
    'issued_utc':datetime.now(timezone.utc).isoformat(),
    'draft_only':True,'actual_vsdx_delivery_adopted':False,
    'scope':'68 accepted chart inputs; final actual output descriptors pending',
    'planned_figure_count':68,'prepared_primitive_expectation_not_actual':19945,
    'page_width_mm':181.9,'input_font':'Arial','input_minimum_font_pt':8,
    'build_report':None,'root_output_adoption':None,'package':None,
    'figures':rows,
    'description_scope':'README_DRAFT.md; complete full per-figure original notes remain bound in source map',
    'source_inputs':list(bindings),
    'science_recomputed':False,'application_open_render_GUI_validated':False,
    'old_two_main_application_accepted_separate':True,
}
outputs = [write('README_DRAFT.md',readme),write('INDEX_DRAFT.json',index)]
source_path = HERE/'prepare_scope_draft.py'
with source_path.open('rb') as stream:
    source_raw = stream.read(MAX+1)
if len(source_raw) > MAX:
    raise RuntimeError('Draft source over bound')
source_desc = {'path':str(source_path),'bytes':len(source_raw),'sha256':hashlib.sha256(source_raw).hexdigest()}
outputs.append(write('DRAFT_SOURCE_BINDINGS.json',{'schema':'offline-native-visio-delivery-draft-bindings.v1','issued_utc':datetime.now(timezone.utc).isoformat(),'scope':'wording/index draft, not output native artifact adoption','inputs':bindings,'draft_source':source_desc,'draft_outputs':outputs,'science_or_builder_or_API_executed':False,'actual_vsdx_claimed':False,'method':'AI drafting from its already completed independent narrow input authority review; no new input suite or model/scientific recomputation'}))
print(json.dumps({'draft_only':True,'inputs':len(bindings),'outputs':outputs},ensure_ascii=False))