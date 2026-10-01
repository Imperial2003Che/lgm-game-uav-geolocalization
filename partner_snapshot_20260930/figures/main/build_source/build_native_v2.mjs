import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { Presentation, PresentationFile, FileBlob } from '@oai/artifact-tool';
import { xml2js } from 'xml-js';
import { createCanvas, GlobalFonts } from '@napi-rs/canvas';

const BUILD = path.dirname(fileURLToPath(import.meta.url));
const WORK = path.dirname(BUILD);
const SOURCE = path.join(path.dirname(WORK), 'formal_results_native_20260929');
const SKILL = 'C:/Users/17703/.codex/plugins/cache/openai-primary-runtime/presentations/26.927.11222/skills/presentations';
const PYTHON = 'C:/Users/17703/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL, 'container_tools/artifact_tool_utils.mjs')).href);
const hash = b => createHash('sha256').update(b).digest('hex');
const inputs = [];
async function readBound(p, expected) {
  const bytes = await fs.readFile(p);
  if (hash(bytes) !== expected) throw new Error(`Input SHA mismatch: ${p}`);
  inputs.push({path:p, sha256:expected, bytes:bytes.length});
  return bytes;
}
async function describe(p) { const bytes = await fs.readFile(p); return {path:p, sha256:hash(bytes), bytes:bytes.length}; }
function require(c, m) { if (!c) throw new Error(m); }
const root = JSON.parse(await readBound(path.join(SOURCE, 'ROOT_NATIVE_SVG_REVIEW.json'),
 'ac010cc27c27fa94a9fdd3e860af84c330a8e4cc6efa3c66b2e6a8000d6253ca'));
const independent = JSON.parse(await readBound(path.join(SOURCE, 'INDEPENDENT_NATIVE_SVG_REVIEW.json'),
 '9dbcc7f38df2057e900f8a13571b00eadb867d2e890e8948f3eea6e1f6501977'));
const captions = (await readBound(path.join(SOURCE, 'v2/CAPTIONS.md'),
 '2dd6fef4c13f2348256b68ede5e099e51ae307b65b93b0ead3afcc88cd3697a9')).toString('utf8');
require(root.status === 'passed_root_data_geometry_and_visual_review' && independent.status === 'passed_with_caption_recommendation', 'Accepted SVG review statuses');
const datasets = [
 {id:'university1652', widthMm:181.9, heightMm:137.9, svgSha:'a103659da037e8edffd1c0ffd3f19bb1b3f431c04de323361164d4209e997a6a', texts:73, cells:18},
 {id:'sues200', widthMm:181.9, heightMm:240.3, svgSha:'b35c007fe48dc4508411fc4f1ad795a1c3fd13b9ac618167559c4ba4cf5294b1', texts:143, cells:48},
];
require(GlobalFonts.families.some(x => x.family === 'Arial'), 'Arial is installed in CPU canvas runtime');
const ctx = createCanvas(1, 1).getContext('2d');
const outputs = [];
for (const spec of datasets) {
  const evidence = root.figures.find(x => x.dataset === spec.id);
  require(evidence.svg.sha256 === spec.svgSha, 'Root SVG binding');
  const svgPath = path.join(SOURCE, `v2/formal_main_${spec.id}_variants_native.svg`);
  const svg = (await readBound(svgPath, spec.svgSha)).toString('utf8');
  const csvPath = path.join(SOURCE, `v2/formal_main_${spec.id}_variants_source.csv`);
  const csv = (await readBound(csvPath, evidence.source.sha256)).toString('utf8');
  const tree = xml2js(svg, {compact:false, alwaysChildren:true});
  const svgRoot = tree.elements.find(x => x.type === 'element' && x.name === 'svg');
  require(svgRoot.attributes.width === `${spec.widthMm}mm` && svgRoot.attributes.height === `${spec.heightMm}mm`, 'Exact physical dimensions');
  const view = svgRoot.attributes.viewBox.split(/\s+/).map(Number);
  const width = spec.widthMm * 96 / 25.4, height = spec.heightMm * 96 / 25.4;
  const sx = width / view[2], sy = height / view[3];
  const pres = Presentation.create({slideSize:{width, height}});
  const slide = pres.slides.add();
  slide.background.fill = '#FFFFFF';
  const map = [];
  const dataGroups = [];
  const counts = {};
  function visit(node, groups = []) {
    if (node.type !== 'element') return;
    const a = node.attributes ?? {};
    require(!a.transform && !a.style, 'No unimplemented SVG transforms or inherited styles');
    const ids = a.id ? [...groups, a.id] : groups;
    if (node.name === 'g') {
      if (a['data-task']) dataGroups.push({group:a.id, ...a});
      for (const child of node.elements ?? []) visit(child, ids);
      return;
    }
    if (['svg','title','desc'].includes(node.name)) {
      if (node.name === 'svg') for (const child of node.elements ?? []) visit(child, ids);
      return;
    }
    require(['rect','line','circle','polygon','text'].includes(node.name), `Unsupported visible SVG element ${node.name}`);
    const num = n => { const v=Number(a[n]); require(Number.isFinite(v), `Finite SVG ${n}`); return v; };
    const name = `${String(map.length+1).padStart(4,'0')}:${ids.join('/')}:${node.name}`;
    const config = {name, fill:a.fill ?? 'none', line:{fill:a.stroke ?? 'none', width:Number(a['stroke-width'] ?? 0) * sx}};
    let content;
    if (node.name === 'rect') {
      config.geometry='rect';
      config.position={left:num('x')*sx, top:num('y')*sy, width:num('width')*sx, height:num('height')*sy};
    } else if (node.name === 'circle') {
      config.geometry='ellipse';
      config.position={left:(num('cx')-num('r'))*sx, top:(num('cy')-num('r'))*sy, width:2*num('r')*sx, height:2*num('r')*sy};
    } else if (node.name === 'line') {
      const x1=num('x1')*sx, x2=num('x2')*sx, y1=num('y1')*sy, y2=num('y2')*sy;
      require(x1===x2 || y1===y2, 'Reference chart lines are horizontal or vertical');
      config.geometry='line'; config.fill='none';
      config.position={left:Math.min(x1,x2), top:Math.min(y1,y2), width:Math.abs(x2-x1), height:Math.abs(y2-y1)};
    } else if (node.name === 'polygon') {
      const points=a.points.trim().split(/\s+/).map(p=>p.split(',').map(Number));
      require(points.every(p=>p.length===2 && p.every(Number.isFinite)), 'Finite polygon points');
      const xs=points.map(p=>p[0]*sx), ys=points.map(p=>p[1]*sy);
      const x=Math.min(...xs), y=Math.min(...ys), w=Math.max(...xs)-x, h=Math.max(...ys)-y;
      config.geometry='custom'; config.position={left:x,top:y,width:w,height:h};
      config.customPaths=[{width:w,height:h, commands:[{moveTo:{x:xs[0]-x,y:ys[0]-y}},
        ...points.slice(1).map((_,i)=>({lineTo:{x:xs[i+1]-x,y:ys[i+1]-y}})), {close:{}}]}];
    } else {
      content=(node.elements??[]).filter(x=>x.type==='text').map(x=>x.text).join('');
      require((node.elements??[]).every(x=>x.type==='text'), 'Simple editable SVG text');
      const fontPt=num('font-size');
      require(fontPt>=8, 'Minimum original text size is 8 points');
      const fontPx=fontPt * 96 / 72;
      ctx.font=`${a['font-weight']==='bold'?'bold':'normal'} ${fontPx}px Arial`;
      const measured=ctx.measureText(content);
      const textWidth=measured.width+1.0;
      const x=num('x')*sx, baseline=num('y')*sy;
      const anchor=a['text-anchor'] ?? 'start';
      const align={start:'left',middle:'center',end:'right'}[anchor];
      require(align, 'Known text anchor');
      config.geometry='textbox'; config.fill='none'; config.line={fill:'none',width:0};
      config.position={left:x-(anchor==='middle'?textWidth/2:anchor==='end'?textWidth:0),
        top:baseline-fontPx*0.92, width:textWidth,height:fontPx*1.25};
      const shape=slide.shapes.add(config);
      shape.text=content;
      shape.text.style={typeface:'Arial',fontSize:fontPx,bold:a['font-weight']==='bold',color:a.fill??'#222222',
        alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'none',insets:{top:0,bottom:0,left:0,right:0}};
      map.push({name, svgTag:node.name, svgAttributes:a, nativeGeometry:config.position, text:content,
                fontSizePt:fontPt, svgBaseline:baseline, measuredWidth:measured.width});
      counts[node.name]=(counts[node.name]??0)+1;
      return;
    }
    slide.shapes.add(config);
    map.push({name, svgTag:node.name, svgAttributes:a,nativeGeometry:config.position, nativeCustomPaths:config.customPaths});
    counts[node.name]=(counts[node.name]??0)+1;
  }
  visit(svgRoot);
  require(counts.text===spec.texts && dataGroups.length===2*spec.cells, 'Complete native text/data object counts');
  const normalizedCaptions=captions.replaceAll('\r\n','\n');
  const selectedCaption=spec.id==='university1652' ? normalizedCaptions.split('# University-1652\n')[1].split('# SUES-200\n')[0].trim() : normalizedCaptions.split('# SUES-200\n')[1].split('# Scope and interpretation\n')[0].trim();
  const limitations='The markers, error bars, cell values and colors are descriptive and do not establish statistical significance. These figures inherit the accepted results documented evidence limitations, including inherited checkpoint SHA verification. They do not constitute a new scientific evaluation.';
  slide.speakerNotes.textFrame.setText(`${selectedCaption}\n\n${limitations}\n\nAccepted source SVG: ${svgPath}\nSHA256 ${spec.svgSha}\nSource CSV: ${csvPath}\nSHA256 ${evidence.source.sha256}\n\nExact original source CSV follows.\n${csv}`);
  const candidate=path.join(BUILD,`${spec.id}.candidate_v2.pptx`);
  await (await PresentationFile.exportPptx(pres)).save(candidate);
  const draftPng=path.join(BUILD,`${spec.id}.draft_v2.png`);
  await fs.writeFile(draftPng,new Uint8Array(await (await pres.export({slide,format:'png',scale:2})).arrayBuffer()));
  await fs.writeFile(path.join(BUILD,`${spec.id}.layout.json`),await (await slide.export({format:'layout'})).text());
  await fs.writeFile(path.join(BUILD,`${spec.id}.native_map.json`),JSON.stringify({spec,slideSizePx:{width,height},sx,sy,counts,dataGroups,elements:map},null,2));
  const finalPath=path.join(WORK,'output',`formal_main_${spec.id}_native_editable_v2.pptx`);
  const finalization=await finalizePresentation({workspaceDir:WORK,candidatePath:candidate,finalPath,
    explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
    pythonExecutable:PYTHON, integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
    layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
    layoutArgs:['--expected-slide-size-emu',`${Math.round(spec.widthMm*36000)},${Math.round(spec.heightMm*36000)}`,
                '--approved-dense-slide','1','--cover-role','none'],
    fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,
    receiptPath:path.join(BUILD,`${spec.id}.validation_v2.json`)});
  const imported=await PresentationFile.importPptx(await FileBlob.load(finalPath));
  const importedSlide=imported.slides.items[0];
  const previewPath=path.join(WORK,'output',`formal_main_${spec.id}_native_editable_v2.png`);
  await fs.writeFile(previewPath,new Uint8Array(await (await imported.export({slide:importedSlide,format:'png',scale:2})).arrayBuffer()));
  outputs.push({dataset:spec.id,pptx:await describe(finalPath),preview:await describe(previewPath),
    nativeMap:await describe(path.join(BUILD,`${spec.id}.native_map.json`)),counts,finalization});
  console.log(JSON.stringify({dataset:spec.id,counts,pptx:finalPath,preview:previewPath}));
}
await fs.writeFile(path.join(WORK,'BUILD_REPORT_V2.json'),JSON.stringify({utc:new Date().toISOString(),
  source:await describe(fileURLToPath(import.meta.url)),inputs,outputs,
  method:'Each visible SVG primitive is authored as one native editable PPTX shape, text box or custom polygon. No SVG/image embedding; no model/scientific data recalculation.',
  physicalSize:'181.9 mm width; 137.9 / 240.3 mm height', font:'Arial, preserved 8/9/10 pt; no auto-fit shrinking',
  limits:['CPU artifact-tool final PPTX import/render; no PowerPoint GUI process opened.',
    'Data plots are native grouped-by-name shapes, not embedded raster/SVG or Excel chart objects.',
    'Accepted upstream data and inherited evidence limits remain.']},null,2));
