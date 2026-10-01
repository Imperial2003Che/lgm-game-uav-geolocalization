import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { Presentation, PresentationFile, FileBlob } from '@oai/artifact-tool';
import { createCanvas, GlobalFonts } from '@napi-rs/canvas';

const BUILD=path.dirname(fileURLToPath(import.meta.url)), WORK=path.dirname(BUILD), OUT=path.join(WORK,'output');
const EX=path.join(path.dirname(WORK),'execution');
const AUDIT=path.join(EX,'pipeline_post_robustness_audit_20260929_1448');
const RAW=path.join(AUDIT,'a1/aggregate');
const SKILL='C:/Users/17703/.codex/plugins/cache/openai-primary-runtime/presentations/26.927.11222/skills/presentations';
const PYTHON='C:/Users/17703/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const SAMPLE=process.argv.includes('--sample');
const W=181.9*72/25.4, H=165*72/25.4, S=96/72;
const COLORS={visual:'#0072B2',full:'#D55E00'};
const FAMILIES=['gaussian_noise','gaussian_blur','brightness','contrast','center_occlusion','rotation'];
const LABELS=['Gaussian noise','Gaussian blur','Brightness','Contrast','Center occlusion','Rotation'];
const SOURCE_SHA='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a';
let checks=0;
const require=(v,m)=>{checks++;if(!v)throw new Error(m);};
const hash=b=>createHash('sha256').update(b).digest('hex');
const normalize=p=>path.normalize(p).toLowerCase();
const inputs=[];
const describe=async p=>{const b=await fs.readFile(p);return {path:p,sha256:hash(b),bytes:b.length};};
async function bind(p,expected){const b=await fs.readFile(p);require(hash(b)===expected.sha256 && (expected.bytes===undefined||b.length===expected.bytes),`SHA/size ${p}`);inputs.push({path:p,sha256:hash(b),bytes:b.length});return b;}
async function createOrVerify(p,b){try{await fs.writeFile(p,b,{flag:'wx'});}catch(e){if(e.code!=='EEXIST')throw e;require(hash(await fs.readFile(p))===hash(b),`Existing preparation changed ${p}`);}}
const root=JSON.parse(await bind(path.join(AUDIT,'ROOT_POST_ROBUSTNESS_ADOPTION.json'),{sha256:SOURCE_SHA}));
require(root.accepted_with_stated_limits===true,'Root adoption accepted');
const rootBindings=new Map(root.bindings.map(x=>[normalize(x.path),x]));
const bindAdopted=async p=>{require(rootBindings.has(normalize(p)),'Exact adopted path');return bind(p,rootBindings.get(normalize(p)));};
const index=JSON.parse(await bindAdopted(path.join(RAW,'figure_index.json')));
const aggConfig=JSON.parse(await bindAdopted(path.join(RAW,'aggregation_run_config.json')));
require(index.figures.length===22,'Exactly 22 accepted task/metric figures');
function parseCsv(text){const rows=[];let row=[],field='',quoted=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){field+='"';i++;}else quoted=!quoted;}else if(!quoted&&(c===','||c==='\n')){row.push(field.replace(/\r$/,''));field='';if(c==='\n'){if(row.length>1)rows.push(row);row=[];}}else field+=c;}if(field||row.length){row.push(field.replace(/\r$/,''));rows.push(row);}require(!quoted,'Balanced CSV quotes');const headers=rows.shift();require(new Set(headers).size===headers.length,'Unique columns');return rows.map(r=>{require(r.length===headers.length,'CSV shape');return Object.fromEntries(headers.map((h,i)=>[h,r[i]]));});}
function taskLabel(task){if(task.startsWith('university1652_'))return {'drone_to_satellite':'Drone → satellite','satellite_to_drone':'Satellite → drone','street_to_satellite':'Street → satellite'}[task.replace('university1652_','')];let m=task.match(/^sues200_uav_(150|200|250|300)m_to_satellite$/);if(m)return `UAV ${m[1]} m → satellite`;m=task.match(/^sues200_satellite_to_uav_(150|200|250|300)m$/);require(m,'Exact SUES height/task');return `Satellite → UAV ${m[1]} m`;}
const escape=v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
require(GlobalFonts.families.some(f=>f.family==='Arial'),'Arial installed');
const ctx=createCanvas(1,1).getContext('2d');
const prepped=[];
for(let n=0;n<index.figures.length;n++){
 const fig=index.figures[n], sourcePath=path.join(RAW,fig.source_csv), raw=await bindAdopted(sourcePath), rows=parseCsv(raw.toString('utf8'));
 require(rows.length===60,'Exactly 60 source rows');
 const keys=new Set();
 for(const row of rows){require(row.dataset===fig.dataset&&row.task===fig.task&&row.metric===fig.metric&&row.seed==='1','Exact task metric seed');const k=`${row.variant}/${row.corruption}/${row.severity_index}`;require(!keys.has(k),'Unique source key');keys.add(k);require(['visual','full'].includes(row.variant)&&FAMILIES.includes(row.corruption)&&[1,2,3,4,5].includes(Number(row.severity_index)),'Frozen condition key');for(const f of ['clean_fraction','corrupted_fraction','value'])require(Number.isFinite(Number(row[f])),'Finite actual metric');const clean=Number(row.clean_fraction), corrupt=Number(row.corrupted_fraction);require(clean>=0&&clean<=1&&corrupt>=0&&corrupt<=1,'Fraction range');if(clean===0){require(row.retained_percent_of_clean==='','Undefined zero baseline retained field');}else{require(Number.isFinite(Number(row.retained_percent_of_clean))&&Math.abs(Number(row.retained_percent_of_clean)-100*corrupt/clean)<1e-9,'Retained percent exact formula');}}
 const stem=`${fig.task}__${fig.metric.toLowerCase()}`, copyPath=path.join(OUT,'source_data',`${stem}.csv`);
 await createOrVerify(copyPath,raw);
 const clean={};
 for(const variant of ['visual','full']){const vals=new Set(rows.filter(r=>r.variant===variant).map(r=>r.clean_fraction));require(vals.size===1,'Single own-clean baseline per variant');clean[variant]=Number([...vals][0]);}
 const conditions=FAMILIES.map((family,i)=>{const r=rows.filter(r=>r.variant==='visual'&&r.corruption===family).sort((a,b)=>Number(a.severity_index)-Number(b.severity_index));const q=rows.filter(r=>r.variant==='full'&&r.corruption===family).sort((a,b)=>Number(a.severity_index)-Number(b.severity_index));require(r.length===5&&q.length===5,'Complete two variant family');for(let k=0;k<5;k++)for(const f of ['parameter','value','units','corruption_display'])require(r[k][f]===q[k][f],'Frozen same condition pair');return {name:family,display:LABELS[i],parameter:r[0].parameter,values:r.map(x=>Number(x.value)),units:r[0].units};});
 prepped.push({ordinal:n+1,...fig,stem,sourcePath,source:await describe(sourcePath),sourceCopy:await describe(copyPath),rows,clean,conditions});
}
await createOrVerify(path.join(WORK,'INPUT_PROVENANCE.json'),Buffer.from(JSON.stringify({schema:'robustness-native-inputs.v1',root_adoption_sha256:SOURCE_SHA,inputs,figures:prepped.map(({rows,...f})=>f),scope:'22 figures, 1320 source rows only; remaining four metrics in 3960-row aggregate are not plotted.'},null,2)));
const selected=SAMPLE?[prepped[0],prepped.find(f=>f.dataset==='sues200')]:prepped;
const pres=Presentation.create({slideSize:{width:W*S,height:H*S}});
const figureReports=[];
for(const fig of selected){
 const slide=pres.slides.add();slide.background.fill='#FFFFFF';
 const primitives=[];
 const metricLabel=fig.metric==='r_at_1'?'R@1':'Official mAP';
 const datasetLabel=fig.dataset==='university1652'?'University-1652':'SUES-200';
 const title=`${datasetLabel}: ${taskLabel(fig.task)}`;
 function add(tag,id,a,text,data={}){primitives.push({tag,id,...a,...(text===undefined?{}:{text}),data});}
 const txt=(id,x,y,text,size=8,bold=false,anchor='start',fill='#222222')=>add('text',id,{x,y,fontSize:size,bold,anchor,fill},text);
 const line=(id,x1,y1,x2,y2,stroke,width=0.65,data={})=>add('line',id,{x1,y1,x2,y2,stroke,width},undefined,data);
 const marker=(id,x,y,variant,data={})=>add(variant==='visual'?'circle':'rect',id,{x,y,r:2,fill:COLORS[variant]},undefined,data);
 txt('title',15,17,title,10,true);
 txt('metric-title',15,33,`${metricLabel} retention under image corruption`,9,true);
 marker('legend-visual',18,47,'visual');txt('legend-visual-label',26,50,'Visual',8);
 marker('legend-full',100,47,'full');txt('legend-full-label',108,50,'Full',8);
 txt('clean-baselines',15,68,`Clean ${metricLabel} (%): Visual ${(100*fig.clean.visual).toFixed(4)}; Full ${(100*fig.clean.full).toFixed(4)}`,8);
 txt('y-axis-label',15,86,'Retained performance (% of each variant’s own clean baseline)',8);
 const finite=fig.rows.filter(r=>r.retained_percent_of_clean!=='').map(r=>Number(r.retained_percent_of_clean));
 const maxValue=Math.max(100,...finite), yMax=Math.ceil(Math.max(110,maxValue*1.05)/20)*20;
 const panelWidth=(W-30-24)/3, plotW=panelWidth-33, plotH=94;
 const panels=[];
 for(let i=0;i<6;i++){
  const left=15+(i%3)*(panelWidth+12), top=116+Math.floor(i/3)*155, x0=left+26, y0=top, bottom=y0+plotH;
  const family=FAMILIES[i];
  txt(`panel-${family}-title`,left,top-10,`(${String.fromCharCode(97+i)}) ${LABELS[i]}`,8.5,true);
  for(let tick=0;tick<=yMax;tick+=20){const y=bottom-tick/yMax*plotH;line(`panel-${family}-grid-${tick}`,x0,y,x0+plotW,y,tick===100?'#9EABB3':'#DEE4E8',tick===100?.65:.4);txt(`panel-${family}-ytick-${tick}`,x0-4,y+2.8,String(tick),8,false,'end');}
  line(`panel-${family}-axis-y`,x0,y0,x0,bottom,'#333333',.65);line(`panel-${family}-axis-x`,x0,bottom,x0+plotW,bottom,'#333333',.65);
  for(let sev=0;sev<=5;sev++){const x=x0+sev/5*plotW;line(`panel-${family}-tick-${sev}`,x,bottom,x,bottom+3,'#333333',.65);txt(`panel-${family}-xlabel-${sev}`,x,bottom+13,String(sev),8,false,'middle');}
  const series=[];
  for(const variant of ['visual','full']){
   const actual=fig.rows.filter(r=>r.variant===variant&&r.corruption===family).sort((a,b)=>Number(a.severity_index)-Number(b.severity_index));
   const points=[{severity:0,retention:fig.clean[variant]>0?100:null,kind:'defined-clean-reference',cleanFraction:fig.clean[variant]},...actual.map(r=>({severity:Number(r.severity_index),retention:r.retained_percent_of_clean===''?null:Number(r.retained_percent_of_clean),kind:'source-row',cleanFraction:Number(r.clean_fraction),corruptFraction:Number(r.corrupted_fraction),parameter:r.parameter,parameterValue:Number(r.value),units:r.units}))];
   const located=points.map(p=>({...p,x:x0+p.severity/5*plotW,y:p.retention===null?null:bottom-p.retention/yMax*plotH}));
   for(let j=1;j<located.length;j++){const a=located[j-1],b=located[j];if(a.y!==null&&b.y!==null)line(`${family}-${variant}-segment-${j-1}-${j}`,a.x,a.y,b.x,b.y,COLORS[variant],1.05,{family,variant,fromSeverity:j-1,toSeverity:j});}
   for(const p of located)if(p.y!==null)marker(`${family}-${variant}-severity-${p.severity}`,p.x,p.y,variant,{family,variant,...p});
   if(fig.clean[variant]===0)txt(`${family}-${variant}-undefined`,x0+plotW/2,y0+35+(variant==='full'?12:0),`${variant==='visual'?'Visual':'Full'}: undefined (clean = 0)`,8,false,'middle',COLORS[variant]);
   series.push({variant,points:located});
  }
  panels.push({family,plot:{x:x0,y:y0,width:plotW,height:plotH},yMin:0,yMax,series});
 }
 txt('x-axis-label',W/2,393,'Severity (0 = clean; 1–5 = frozen corruption levels)',8,false,'middle');
 const visibleNotes=[
  'Seed 1 only. Full official queries and clean full gallery; tasks remain separate.',
  'Higher retention does not imply higher absolute corrupted accuracy.',
  'Full uses cached CLIP for clean queries and online CLIP for corrupted queries.',
  'Full curves include evidence-path differences as well as image corruption.'
 ];
 visibleNotes.forEach((text,i)=>txt(`caveat-${i+1}`,15,411+i*13,text,8));
 for(const p of primitives){
  const name=`${fig.task}/${fig.metric}/${p.id}`;
  if(p.tag==='text'){
   ctx.font=`${p.bold?'bold':'normal'} ${p.fontSize*S}px Arial`;const tw=ctx.measureText(p.text).width+1;
   const left=p.x*S-(p.anchor==='middle'?tw/2:p.anchor==='end'?tw:0);
   require(left>=-.1&&left+tw<=W*S+.1,`Text horizontal fit ${name}`);
   const sh=slide.shapes.add({geometry:'textbox',name,position:{left,top:(p.y-p.fontSize*.92)*S,width:tw,height:p.fontSize*S*1.25},fill:'none',line:{fill:'none',width:0}});
   sh.text=p.text;sh.text.style={typeface:'Arial',fontSize:p.fontSize*S,bold:p.bold,color:p.fill,alignment:{start:'left',middle:'center',end:'right'}[p.anchor],verticalAlignment:'top',autoFit:'none',wrap:'none',insets:{top:0,bottom:0,left:0,right:0}};
  }else if(p.tag==='line'){
   slide.shapes.add({geometry:'line',name,position:{left:Math.min(p.x1,p.x2)*S,top:Math.min(p.y1,p.y2)*S,width:Math.abs(p.x2-p.x1)*S,height:Math.abs(p.y2-p.y1)*S,verticalFlip:(p.x2-p.x1)*(p.y2-p.y1)<0},fill:'none',line:{fill:p.stroke,width:p.width*S}});
  }else slide.shapes.add({geometry:p.tag==='circle'?'ellipse':'rect',name,position:{left:(p.x-p.r)*S,top:(p.y-p.r)*S,width:2*p.r*S,height:2*p.r*S},fill:p.fill,line:{fill:'none',width:0}});
 }
 const header=`<svg xmlns="http://www.w3.org/2000/svg" width="181.9mm" height="165mm" viewBox="0 0 ${W} ${H}" role="img">`;
 const svg=[header,`<title>${escape(title+': '+metricLabel+' retention')}</title>`,`<desc>Seed 1 only. Native editable text and geometric primitives. ${escape(visibleNotes.join(' '))}</desc>`,`<rect id="background" x="0" y="0" width="${W}" height="${H}" fill="white"/>`];
 for(const p of primitives){const attrs=`id="${escape(p.id)}" data-source-task="${escape(fig.task)}" data-source-metric="${escape(fig.metric)}"`+Object.entries(p.data).filter(([k,v])=>v!==null&&typeof v!=='object').map(([k,v])=>` data-${k.replace(/[A-Z]/g,m=>'-'+m.toLowerCase())}="${escape(v)}"`).join('');if(p.tag==='text')svg.push(`<text ${attrs} x="${p.x}" y="${p.y}" font-family="Arial" font-size="${p.fontSize}" font-weight="${p.bold?'bold':'normal'}" text-anchor="${p.anchor}" fill="${p.fill}">${escape(p.text)}</text>`);else if(p.tag==='line')svg.push(`<line ${attrs} x1="${p.x1}" y1="${p.y1}" x2="${p.x2}" y2="${p.y2}" stroke="${p.stroke}" stroke-width="${p.width}"/>`);else if(p.tag==='circle')svg.push(`<circle ${attrs} cx="${p.x}" cy="${p.y}" r="${p.r}" fill="${p.fill}"/>`);else svg.push(`<rect ${attrs} x="${p.x-p.r}" y="${p.y-p.r}" width="${2*p.r}" height="${2*p.r}" fill="${p.fill}"/>`);}
 svg.push('</svg>');const svgPath=path.join(OUT,'native_svg',`${fig.stem}.svg`);await createOrVerify(svgPath,Buffer.from(svg.join('\n')+'\n'));
 const caption=`${title}. ${metricLabel} retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean ${metricLabel} is Visual ${(fig.clean.visual*100).toFixed(4)}% and Full ${(fig.clean.full*100).toFixed(4)}%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.`;
 const parameters=fig.conditions.map(c=>`${c.display}: ${c.parameter}=[${c.values.join(', ')}]; ${c.units}.`).join('\n');
 slide.speakerNotes.textFrame.setText(`${caption}\n\nFrozen severity 1–5 parameters:\n${parameters}\n\nRoot adoption SHA256: ${SOURCE_SHA}\nSource CSV: ${fig.sourcePath}\nSource SHA256: ${fig.source.sha256}\n\nExact accepted source CSV:\n${await fs.readFile(fig.sourcePath,'utf8')}`);
 figureReports.push({ordinal:fig.ordinal,task:fig.task,dataset:fig.dataset,metric:fig.metric,title,caption,parameters:fig.conditions,source:fig.source,sourceCopy:fig.sourceCopy,svg:await describe(svgPath),widthMm:181.9,heightMm:165,minimumFontPt:8,yMin:0,yMax,clean:fig.clean,panels,primitives,nativeShapeCount:primitives.length});
}
const variant=SAMPLE?'sample':'final';
const candidate=path.join(BUILD,`${variant}.candidate.pptx`);await(await PresentationFile.exportPptx(pres)).save(candidate);
let target=candidate;
if(!SAMPLE){target=path.join(OUT,'robustness_native_editable_22figures.pptx');await finalizePresentation({workspaceDir:WORK,candidatePath:candidate,finalPath:target,explicitTotalSlideCount:22,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],pythonExecutable:PYTHON,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu',`${Math.round(181.9*36000)},${Math.round(165*36000)}`,'--cover-role','none',...Array.from({length:22},(_,i)=>['--approved-dense-slide',String(i+1)]).flat()],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(BUILD,'final.validation.json')});}
const imported=await PresentationFile.importPptx(await FileBlob.load(target));
for(let i=0;i<figureReports.length;i++){const fig=figureReports[i],png=path.join(SAMPLE?BUILD:path.join(OUT,'previews'),`${String(fig.ordinal).padStart(2,'0')}_${fig.stem}${SAMPLE?'_sample':''}.png`);await fs.writeFile(png,new Uint8Array(await(await imported.export({slide:imported.slides.items[i],format:'png',scale:2})).arrayBuffer()));fig.preview=await describe(png);console.log(JSON.stringify({page:i+1,ordinal:fig.ordinal,task:fig.task,metric:fig.metric,preview:png}));}
await fs.writeFile(path.join(WORK,SAMPLE?'SAMPLE_REPORT.json':'BUILD_REPORT.json'),JSON.stringify({schema:'native-robustness-figures-build.v1',utc:new Date().toISOString(),sample:SAMPLE,source:await describe(fileURLToPath(import.meta.url)),rootSha256:SOURCE_SHA,inputProvenance:await describe(path.join(WORK,'INPUT_PROVENANCE.json')),checks,pptx:await describe(target),figureCount:figureReports.length,sourceRows:figureReports.length*60,figures:figureReports,scientificExecution:false,PowerPointOpened:false,renderer:'artifact-tool imported final/candidate PPTX, CPU rendering',limits:['Native individual shapes with stable hierarchical selection names; no embedded images or Excel chart objects.','No model inference, ranking, checkpoint, cache or NPZ read.','Inherited root adoption/evidence limitations apply; only a presentation conversion.']},null,2));
console.log(JSON.stringify({completed:variant,figures:figureReports.length,checks,target}));
