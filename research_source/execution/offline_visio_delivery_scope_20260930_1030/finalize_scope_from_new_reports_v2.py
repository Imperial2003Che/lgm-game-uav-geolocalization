"""Load only bound new reports and own drafts; never opens native/preview/scientific files."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os
from collections import Counter
HERE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\offline_visio_delivery_scope_20260930_1030')
OUT = HERE.parent.parent
BUILD = OUT/'offline_native_visio_20260930_1030'/'output68'/'BUILD_REPORT.json'
ARTIFACT = OUT/'execution'/'offline_native_visio_independent_review_20260930_1030'/'full68_review_v4'/'ARTIFACT_REVIEW.json'
BINDINGS=[]
def require(condition,label):
    if not condition: raise RuntimeError(label)
def read(path, expected):
    limit=8*1024*1024 if path==ARTIFACT else 512*1024
    before=path.stat()
    require(0<before.st_size<=limit,'Exact new report/draft bounded before read')
    with path.open('rb') as h: raw=h.read(limit+1)
    after=path.stat()
    require(len(raw)==before.st_size and (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),'Stable new report/draft bytes')
    desc={'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    require(desc['sha256']==expected,'Exact new report/draft digest')
    BINDINGS.append(desc)
    return raw,desc

def write(name,value):
    raw=(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode('utf-8') if not isinstance(value,str) else value.encode('utf-8')
    require(len(raw)<=512*1024,'Final scope output cap before CreateNew')
    path=HERE/name
    with path.open('xb') as h: h.write(raw);h.flush();os.fsync(h.fileno())
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def key(path):return str(Path(path).resolve()).casefold()

buildraw,build_desc=read(BUILD,'9a25ed045d253652ebfa6363ad274b745fff74f80ef2b8665aeda0d0bd826475')
artifactsraw,artifact_desc=read(ARTIFACT,'366a42231df3e23890e813e1bfbe2ae853660a3787f4f218a15708b7a5e6f17a')
draftraw,draft_desc=read(HERE/'README_DRAFT.md','ca5405fb0bb163f6410b3f9a4dc77f50d12ae04d7c322bb519bf1872f13858c8')
indexraw,index_desc=read(HERE/'INDEX_DRAFT.json','41f77f07e240d4fb7fe8f180fab7ff3443d39abdcca0ed0c2c325b427834ac23')
build=json.loads(buildraw);artifact=json.loads(artifactsraw);draft_index=json.loads(indexraw)
require(build['schema']=='offline-native-visio-build.v1' and build['mode']=='full68' and build['figure_count']==68,'Actual full68 producer report')
require(build['native_shape_files_created'] is True and build['visio_open_validated'] is False and build['scientific_execution'] is False,'Producer actual file-only scope')
require(artifact['schema']=='offline-native-visio-independent-artifact-review.v1' and artifact['passed'] is True and artifact['mode']=='full68' and artifact['figure_count']==68,'Actual independent full68 artifact report')
require(artifact['producer_report']==build_desc,'New independent report binds actual producer bytes')
require(artifact['CPU_XML_derived_previews_written'] is True and artifact['native_opc_shape_text_files_reviewed'] is True,'Actual new native XML and CPU previews')
require(artifact['Visio_renderer_used'] is False and artifact['visio_open_repair_render_GUI_edit_roundtrip_validated'] is False and artifact['complete_XSD_validation'] is False and artifact['scientific_recomputation'] is False and artifact['old_accepted_suite_replayed'] is False,'Accurate report limits')
require(len(build['figures'])==len(artifact['figures'])==len(draft_index['figures'])==68,'68 report/draft records')
by_svg={key(x['source_svg']['path']):x for x in build['figures']}
by_vsdx={key(x['vsdx']['path']):x for x in artifact['figures']}
require(len(by_svg)==len(by_vsdx)==68,'Unique actual report records')
rows=[];totals=Counter();family_totals={};native_bytes=0;native_texts=0
for old in draft_index['figures']:
    b=by_svg[key(old['accepted_svg']['path'])]
    a=by_vsdx[key(b['output']['path'])]
    require(b['source_svg']==old['accepted_svg'] and a['parity']['source_svg']==old['accepted_svg'],'Actual source descriptor maps to previously reviewed input')
    require(a['vsdx']==b['output'] and a['parity']['accepted_figure_root']==old['accepted_graphical_root'],'Actual output and accepted graphical authority descriptors match')
    family={'T3':'transfer','T4':'margin'}.get(old['family'],old['family'])
    require(a['family']==b['family']==family,'Actual family naming relation')
    counts=a['parity']['native_counts']
    require(all(type(v) is int and v>=0 for v in counts.values()),'Native count integer metadata')
    require(sum(counts.values())==b['native_objects'] and counts['text']==b['native_texts'],'Producer and independent native count metadata agree')
    require(all(abs(x-y)<=1e-8 for x,y in zip(a['page_mm'],[b['inventory']['width_mm'],b['inventory']['height_mm']])) and abs(a['page_mm'][0]-181.9)<1e-8,'Actual page size metadata agree within declared1e-8mm serialization tolerance')
    fc=a['parity']['native_font_pt_counts']
    require(all(float(k)>=8-1e-8 and type(v) is int and v>=0 for k,v in fc.items()) and sum(fc.values())==counts['text'],'Native min8 font and text count metadata agree')
    pr=a['preview']
    require(pr['native_input_only'] is True and pr['source_svg_rendered'] is False and pr['visio_renderer'] is False and pr['clipped_text_count']==0,'Actual native XML CPU preview scope and saved glyph bound result')
    preview=dict(pr['preview']);preview['dimensions_px']=pr['dimensions']
    row=dict(old)
    row.update({'actual_vsdx':b['output'],'actual_native_shapes':b['native_objects'],'actual_native_texts':b['native_texts'],'actual_native_primitive_counts':counts,'actual_native_font_pt_counts':fc,'page_dimensions_mm':a['page_mm'],'VSDX_member_count':a['member_count'],'CPU_XML_preview':preview,'actual_cpu_native_xml_preview':preview,'CPU_XML_preview_native_input_only':True,'source_svg_rendered_for_preview':False,'Visio_export':False,'actual_visio_export':None,'Visio_renderer_used':False,'application_open_without_repair':False,'gui_edit_validated':False,'roundtrip_validated':False,'root_output_adoption':'pending','root_all68_visual_review':'pending','saved_cpu_glyph_clipped_text_count':0})
    rows.append(row);totals.update(counts);native_bytes+=b['output']['bytes'];native_texts+=b['native_texts']
    ft=family_totals.setdefault(family,{'VSDX_count':0,'VSDX_bytes':0,'native_objects':0,'native_texts':0,'CPU_XML_preview_count':0})
    ft['VSDX_count']+=1;ft['VSDX_bytes']+=b['output']['bytes'];ft['native_objects']+=b['native_objects'];ft['native_texts']+=b['native_texts'];ft['CPU_XML_preview_count']+=1
require(dict(totals)=={'rect':1892,'text':8879,'circle':1818,'line':7356} and sum(totals.values())==19945 and native_texts==8879 and native_bytes==2582980,'Reported actual new metadata totals')
require({k:v['VSDX_count'] for k,v in family_totals.items()}=={'transfer':2,'robustness':22,'margin':11,'risk':11,'reliability':11,'paired':11},'Actual six-family coverage metadata')

scope = '''# 68 图原生 VSDX 文件交付范围

本批已实际生成 68 个单页原生 VSDX，共 2582980 B、19945 个原生文字/几何对象，其中 8879 个文字对象。六组为 T3 双向迁移 2 图、seed 1 扰动 22 图、T4 Visual-margin 分层 11 图、T5 risk–coverage 11 图、T5 fixed-margin reliability 11 图、T5 paired full-N success 11 图。页面宽度全部 181.9 mm、高度沿用各自已采用图件；已保存原生文字为 Arial 8/9/10 pt，最小 8 pt。逐文件实际路径、bytes/SHA、对象/文字/字号计数及 CPU 预览尺寸和 SHA 见 INDEX_FINAL.json。

这次交付说明根据真实 full68 BUILD_REPORT 和独立 full68 ARTIFACT_REVIEW 的保存实值编写。独立审查实际读取新 OPC/VSDX 原生对象，并进行了保存几何、文字、字体、样式、颜色、notes 的比较；完整 XSD 验证未完成。本说明的 finalizer 只读取已绑定新报告和自己的已封草稿，没有重新读取 68 个 VSDX、预览或科学数据，也没有重跑独立对象审查。

文件已生成与本批根最终采用、打包、全 68 页根视觉审查是不同状态：后者在本说明封存时仍 pending。68 个 VSDX 是 CPU 程序直接写入 OPC/ShapeSheet 的原生文字与几何对象，属于 file-only 交付。尚未在 Visio 应用中打开、验证不请求修复、实际导出、GUI 编辑或完成往返。单对象原生结构不能代称 GUI 编辑实测、Excel 联动或应用兼容性验证。

此前 University/SUES 两张主结果 VSDX 已实际通过 Visio 创建、保存、关闭、重开和 PNG/PDF 导出，属于另外已采用的应用验收范围。本批 68 图沿用各自原科学数据和图件根，不能借用旧两主图的应用证据来补本批的 Visio 待项，也不覆盖或回写旧产物。

独立审查实际生成 68 张 CPU native-XML PNG 预览。预览使用本批保存的 ShapeSheet 几何、文字和格式，经 Pillow/FreeType Arial 绘制；没有渲染 source SVG，亦没有调用 Visio renderer。保存的 CPU glyph bounds 全 68 页 clipped_text_count=0，但 Pillow 字形布局只是对原生保存布局的近似；Visio 实际 baseline、kerning、wrapping、line caps/joins 和修复行为仍未验证。CPU PNG 不是 Visio 实际导出；本批 Visio_export=false。实际视觉审查意见与数值 glyph bounds 检查须分别引用，不能相互替代。原尺寸最小 8 pt；后续缩图会缩小字号。

本批只转换已采用图件的表示形式，不重跑训练、模型、ranking、query 统计、均值、SD、AP、ECE、AURC、bootstrap 或其他科学实验。完整原 CAPTIONS、源 CSV/JSON、SVG 和 notes 应随包保留原字节；各图源根和来源 descriptor 已在 INDEX 绑定，包内完整 notes/copy bytes 还应联合实际根文件与打包审查采用。科研结果与所有局限均继承原采用范围。

'''
old_text=draftraw.decode('utf-8')
scientific=old_text.split('## 数据口径必须完整保留\n',1)[1].split('## 最终包建议内容\n',1)[0]
readme=scope+'## 数据口径必须完整保留\n'+scientific+'''## 最终包内容及待项

建议包内包括 68 个已实际生成的 VSDX、逐文件 INDEX、68 张实际 CPU native-XML previews、完整 notes、原字节 CAPTIONS/源 CSV/JSON/SVG、冻结 input manifest、builder/source diff、实际 BUILD_REPORT、独立输入/包内对象审查及后到根实际采用和视觉记录。仅加入真实生成且明确范围的附件；没有实际 Visio 导出的 PNG/PDF 就不列为 Visio 导出。最终包应另新建并封存，不回写历史两 main VSDX、PPT/SVG、论文或 60.47 GB 合作伙伴包。

本说明封存时：root output adoption、全 68 页 root actual visual、包路径/bytes/SHA/member audit 仍 pending，另封后到报告，不回写本说明中的时间范围。Visio application open without repair / actual export / GUI edit / round-trip 仍 pending；完整 XSD 验证仍 false。其他实际科学实验、最终论文/Overleaf与投稿建议不由本批文件交付完成。

实际 producer BUILD_REPORT：output68/BUILD_REPORT.json，92748 B，SHA 9a25ed045d253652ebfa6363ad274b745fff74f80ef2b8665aeda0d0bd826475。
实际独立 ARTIFACT_REVIEW：execution/offline_native_visio_independent_review_20260930_1030/full68_review_v4/ARTIFACT_REVIEW.json，5630497 B，SHA 366a42231df3e23890e813e1bfbe2ae853660a3787f4f218a15708b7a5e6f17a。
'''
index={'schema':'offline-native-visio-delivery-file-index.v1','issued_utc':datetime.now(timezone.utc).isoformat(),'actual_native_files_created':True,'actual_native_figure_count':68,'VSDX_total_bytes':native_bytes,'native_primitive_counts':dict(totals),'native_objects':sum(totals.values()),'native_texts':native_texts,'family_totals':family_totals,'figures':rows,'source_inputs':BINDINGS,'actual_output_file_descriptors_inherited_from_exact_bound_reports':True,'actual_output_files_reread_by_this_finalizer':False,'scientific_recomputation':False,'old_input_or_scientific_suite_replayed':False,'CPU_XML_preview_count':68,'CPU_XML_preview_renderer':'Independent ShapeSheet reader + Pillow/FreeType Arial; not Visio export','Visio_export':False,'Visio_open_without_repair_validated':False,'Visio_actual_export_validated':False,'GUI_edit_roundtrip_validated':False,'complete_XSD_validation':False,'root_output_adoption':'pending at scope sealing','root_all68_visual_review':'pending at scope sealing','package':'pending at scope sealing','old_two_main_application_accepted_separate':True,'method':'AI final metadata transcription and wording only from exact new full producer/independent report bytes and own prior draft; no independent object/preview reread or visual review by this finalizer','independent_new_native_artifact_review':artifact_desc,'actual_full_build_report':build_desc}
outputs=[write('README_FINAL.md',readme),write('INDEX_FINAL.json',index)]
source=HERE/'finalize_scope_from_new_reports.py'
require(source.stat().st_size<=512*1024,'Final scope source bounded')
with source.open('rb') as h:sr=h.read(512*1024+1)
source_desc={'path':str(source),'bytes':len(sr),'sha256':hashlib.sha256(sr).hexdigest()}
outputs.append(write('FINAL_SCOPE_BINDINGS.json',{'schema':'offline-native-visio-final-file-scope-bindings.v1','utc':datetime.now(timezone.utc).isoformat(),'input_bindings':BINDINGS,'source':source_desc,'outputs':outputs,'actual_reports_loaded':True,'actual_new_file_descriptor_rows':68,'actual_native_objects_reported':19945,'root_adoption_or_package_claimed':False,'Visio_export':False,'scientific_recomputation':False,'scope':'Final README/INDEX explanation, not execution/builder/nativefile reread or root output adoption'}))
print(json.dumps({'scope':'file-only README/INDEX','actual_figures':68,'native_objects':19945,'native_texts':8879,'VSDX_bytes':native_bytes,'bound_reports_and_drafts':len(BINDINGS),'outputs':outputs},ensure_ascii=False))