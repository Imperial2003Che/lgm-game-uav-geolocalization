import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
import {createCanvas,GlobalFonts} from '@napi-rs/canvas';
const BUILD=path.dirname(fileURLToPath(import.meta.url)),WORK=path.dirname(BUILD),SAMPLE=process.argv.includes('--sample'),MODE=SAMPLE?'sample':'final',OUT=path.join(WORK,SAMPLE?'sample':'output');
if(SAMPLE)throw new Error('v2 is final-only; preserved v1 sample must not be overwritten');
const EX=path.join(path.dirname(WORK),'execution'),AUDIT=path.join(EX,'pipeline_post_robustness_audit_20260929_1448');
const SKILL='C:/Users/17703/.codex/plugins/cache/openai-primary-runtime/presentations/26.927.11222/skills/presentations';
const PYTHON='C:/Users/17703/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const ROOT_SHA='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a',CAP_SHA='473d5fba90c3fc0d044733ffb19e1f2955f08df96f89d4c643ad54d6ff15ca09',T5_SHA='033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc';
const W=181.9*72/25.4,H=604,S=4/3,HEIGHT_MM=H*25.4/72,COLORS={visual:'#0072B2',full:'#D55E00'};
const ALL_TASKS=['university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite',...[150,200,250,300].flatMap(h=>[`sues200_uav_${h}m_to_satellite`,`sues200_satellite_to_uav_${h}m`])];
const TASKS=SAMPLE?['university1652_drone_to_satellite','sues200_satellite_to_uav_150m']:ALL_TASKS;
let checks=0;const check=(v,m)=>{checks++;if(!v)throw new Error(m);};
const hash=b=>createHash('sha256').update(b).digest('hex'),norm=p=>path.normalize(p).toLowerCase(),inputs=[];
const describe=async p=>{const b=await fs.readFile(p);return {path:p,sha256:hash(b),bytes:b.length};},create=async(p,b)=>fs.writeFile(p,b,{flag:'wx'});
async function bind(p,d){const b=await fs.readFile(p);check(hash(b)===d.sha256&&(d.bytes===undefined||d.bytes===b.length),'SHA/size '+p);inputs.push({path:p,sha256:hash(b),bytes:b.length});return b;}
const rootPath=path.join(AUDIT,'ROOT_POST_ROBUSTNESS_ADOPTION.json'),rootBytes=await bind(rootPath,{sha256:ROOT_SHA}),root=JSON.parse(rootBytes);check(root.accepted_with_stated_limits===true,'Accepted numerical source root');
const rootMap=new Map(root.bindings.map(d=>[norm(d.path),d]));
const capturePath=path.join(AUDIT,'a1/CAPTURE.json');check(rootMap.get(norm(capturePath)).sha256===CAP_SHA,'Root binds capture');
const captureBytes=await bind(capturePath,rootMap.get(norm(capturePath))),capture=JSON.parse(captureBytes);
const sourcePath=path.join(AUDIT,'a1/query/transactions_t5_selective_calibration.json'),binding=rootMap.get(norm(sourcePath));
check(binding&&binding.sha256===T5_SHA&&binding.bytes===744943,'Exact completed T5 JSON');
const cb=capture.bindings.filter(d=>norm(d.snapshot)===norm(sourcePath));check(cb.length===1&&cb[0].sha256===T5_SHA&&cb[0].bytes===744943,'Unique sealed capture input');
const sourceBytes=await bind(sourcePath,binding),t5=JSON.parse(sourceBytes);
await create(path.join(OUT,'source_data/transactions_t5_selective_calibration.json'),sourceBytes);
await create(path.join(OUT,'provenance/ROOT_POST_ROBUSTNESS_ADOPTION.json'),rootBytes);await create(path.join(OUT,'provenance/CAPTURE.json'),captureBytes);
for(const name of ['README.md','REVIEW.json']){const p=path.join(AUDIT,name),b=await fs.readFile(p),d=rootMap.get(norm(p));if(d)check(hash(b)===d.sha256&&b.length===d.bytes,'Root-bound contextual report');inputs.push({path:p,sha256:hash(b),bytes:b.length,role:'Contextual upstream report',rootBound:!!d});await create(path.join(OUT,'provenance',`UPSTREAM_${name}`),b);}
const dep=path.join(EX,'remaining_delivery_dependency_review_20260929_1952');
for(const [name,sha256,bytes] of [['ROOT_DEPENDENCY_REVIEW_ADOPTION.json','b660eb44e4dd868782a9a98142176f2b1c09f7ff8d6e76b2e612fda6fc9953be',7605],['REVIEW.md','d63e40a71b1f17de3eafa33e346cee0726d430b9d30364a76d16886d6d04d8db',6805]]){const b=await bind(path.join(dep,name),{sha256,bytes});await create(path.join(OUT,'provenance',`DEPENDENCY_${name}`),b);}
check(t5.status==='completed'&&t5.unit==='fraction'&&t5.schema_version==='lgm-game.transactions-t5-selective-calibration.v1','Expected adopted T5 schema');
check(t5.native_rows.length===66&&t5.registered_native_row_count===66,'66 complete native records');
check(new Set(t5.native_rows.map(r=>`${r.task}/${r.seed}/${r.variant}`)).size===66,'Unique task/seed/variant');
const flat=[];
for(const task of ALL_TASKS)for(const seed of [1,2,3])for(const variant of ['visual','full']){
 const matches=t5.native_rows.filter(r=>r.task===task&&r.seed===seed&&r.variant===variant);check(matches.length===1,'Registered native record');const r=matches[0],c=r.calibration;
 check(c.bins===15&&c.reliability_bins.length===15&&c.fitted_calibration_parameter===false,'Exactly15 fixed bins; no fitted parameter');
 check(c.confidence_definition==='clip(cosine_top1_minus_top2_margin / 2, 0, 1)','Exact fixed score definition');
 check(Number.isFinite(c.ECE)&&c.ECE>=0&&c.ECE<=1,'Finite saved ECE fraction; not recomputed');
 check(Number.isInteger(r.risk_coverage.queries)&&r.risk_coverage.queries>0,'Saved full query N');
 let countSum=0;
 for(const [i,b] of c.reliability_bins.entries()){
  check(b.bin===i+1&&Number.isInteger(b.count)&&b.count>=0,'Bin order and integer population');countSum+=b.count;
  check(Number.isFinite(b.lower_inclusive)&&Number.isFinite(b.upper_inclusive_only_for_last_bin)&&b.lower_inclusive===i/15&&b.upper_inclusive_only_for_last_bin===(i+1)/15,'Stored equal-width bin boundaries');
  if(b.count===0)check(b.accuracy===null&&b.mean_fixed_normalized_margin_confidence===null&&b.weighted_absolute_gap===0,'Empty means/accuracy remain null');
  else check([b.accuracy,b.mean_fixed_normalized_margin_confidence,b.weighted_absolute_gap].every(v=>Number.isFinite(v)&&v>=0&&v<=1),'Occupied saved fractions');
  flat.push({dataset:r.dataset,task,seed,variant,queries:r.risk_coverage.queries,bin:b.bin,count:b.count,lower_inclusive:b.lower_inclusive,upper_inclusive_only_for_last_bin:b.upper_inclusive_only_for_last_bin,accuracy:b.accuracy,mean_fixed_normalized_margin_confidence:b.mean_fixed_normalized_margin_confidence,weighted_absolute_gap:b.weighted_absolute_gap,ECE:c.ECE,query_membership_sha256:r.query_membership_sha256,source_json_sha256:T5_SHA});
 }
 check(countSum===r.risk_coverage.queries,'Bin population covers saved full query N');
}
check(flat.length===990&&flat.filter(b=>b.count>0).length===140&&flat.filter(b=>b.count===0).length===850,'Observed990/140occupied/850empty');
const headers=Object.keys(flat[0]);function csv(rows){return headers.join(',')+'\n'+rows.map(r=>headers.map(k=>r[k]===null?'null':String(r[k])).join(',')).join('\n')+'\n';}
await create(path.join(OUT,'source_data/RELIABILITY_BINS_990.csv'),csv(flat));
const pageCSVs=new Map();for(const task of TASKS){const b=csv(flat.filter(r=>r.task===task));pageCSVs.set(task,b);await create(path.join(OUT,'source_data',`t5_${task}__reliability_bins.csv`),b);}
const provenance=path.join(WORK,SAMPLE?'INPUT_PROVENANCE_SAMPLE.json':'INPUT_PROVENANCE.json');
await create(provenance,JSON.stringify({schema:'native-t5-reliability-input-provenance.v1',mode:MODE,rootSha256:ROOT_SHA,inputs,allNativeRecords:66,allBinRecords:990,allOccupiedBins:140,allEmptyBins:850,plottedTasks:TASKS,plottedBinRecords:TASKS.length*90,plottedPanels:TASKS.length*3,derivedCSV:'Direct stored fields; null explicitly serialized as null. Counts checked for coverage only; no ECE, gap, accuracy, bin assignment or model statistic recomputation.',copies:await Promise.all((await fs.readdir(path.join(OUT,'source_data'))).map(n=>describe(path.join(OUT,'source_data',n))))},null,2));
check(GlobalFonts.families.some(f=>f.family==='Arial'),'Arial available');
const ctx=createCanvas(1,1).getContext('2d'),escape=v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function label(task){if(task.startsWith('university1652_'))return 'University-1652: '+({'drone_to_satellite':'Drone → satellite','satellite_to_drone':'Satellite → drone','street_to_satellite':'Street → satellite'}[task.replace('university1652_','')]);let m=task.match(/^sues200_uav_(\d+)m_to_satellite$/);if(m)return `SUES-200: UAV ${m[1]} m → satellite`;m=task.match(/^sues200_satellite_to_uav_(\d+)m$/);check(m,'Registered SUES label');return `SUES-200: Satellite → UAV ${m[1]} m`;}
const pres=Presentation.create({slideSize:{width:W*S,height:H*S}}),figures=[];
for(let ti=0;ti<TASKS.length;ti++){
 const task=TASKS[ti],rows=flat.filter(r=>r.task===task),slide=pres.slides.add();slide.background.fill='#FFFFFF';const primitives=[],panels=[];
 const add=(tag,id,a)=>primitives.push({tag,id,...a}),text=(id,x,y,content,size=8,bold=false,anchor='start',fill='#222222')=>add('text',id,{x,y,text:content,fontSize:size,bold,anchor,fill}),line=(id,x1,y1,x2,y2,stroke='#444444',width=.6)=>add('line',id,{x1,y1,x2,y2,stroke,width});
 const marker=(id,x,y,variant)=>add(variant==='visual'?'circle':'rect',id,{x,y,r:variant==='visual'?2.35:1.9,fill:variant==='visual'?'#FFFFFF':'none',stroke:COLORS[variant],width:.9});
 text('title',15,18,label(task),10,true);text('subtitle',15,34,'Fixed margin-score reliability diagnostic',9,true);
 marker('legend/visual/marker',18,48,'visual');text('legend/visual/text',27,51,'Visual (V)',8);marker('legend/full/marker',110,48,'full');text('legend/full/text',119,51,'Full (F)',8);
 line('legend/equality/line',200,48,218,48,'#ABB3BB',.6);text('legend/equality/text',224,51,'y = x: numerical equality reference',8);
 text('y-axis-label',15,69,'Empirical R@1 (fraction)',8);
 for(const seed of [1,2,3]){
  const id=`${task}/seed-${seed}`,x=42+(seed-1)*158,y=95,pw=126,ph=116,bottom=y+ph;
  text(`${id}/seed-heading`,x+pw/2,82,`Seed ${seed}`,9,true,'middle');
  for(const v of [0,.25,.5,.75,1]){const yy=bottom-v*ph;line(`${id}/y-grid-${v}`,x,yy,x+pw,yy,'#E0E6EC',.45);text(`${id}/y-label-${v}`,x-5,yy+2.7,String(v),8,false,'end');const xx=x+v*pw;line(`${id}/x-tick-${v}`,xx,bottom,xx,bottom+3);text(`${id}/x-label-${v}`,xx,bottom+14,String(v),8,false,'middle');}
  line(`${id}/reference-equality`,x,bottom,x+pw,y,'#ABB3BB',.6);line(`${id}/y-axis`,x,y,x,bottom);line(`${id}/x-axis`,x,bottom,x+pw,bottom);
  const series=[];
  for(const variant of ['visual','full']){
   const bins=rows.filter(r=>r.seed===seed&&r.variant===variant),N=bins[0].queries,ECE=bins[0].ECE;
   const points=bins.filter(b=>b.count>0).map(b=>({...b,x:x+b.mean_fixed_normalized_margin_confidence*pw,y:bottom-b.accuracy*ph}));
   for(const p of points)marker(`${id}/${variant}/bin-${p.bin}/point`,p.x,p.y,variant);
   text(`${id}/${variant}/ECE`,x+pw/2,265+(variant==='full'?13:0),`${variant==='visual'?'V':'F'} ECE = ${ECE.toFixed(4)}`,8,false,'middle',COLORS[variant]);
   series.push({variant,queries:N,ECE,allBins:bins,points});
  }
  check(series[0].queries===series[1].queries,'Same full task query count; not same bin members');
  text(`${id}/population/N`,x+pw/2,300,`N = ${series[0].queries.toLocaleString('en-US')}; bin populations`,8,true,'middle');
  text(`${id}/population/header/bin`,x+8,318,'Bin',8,true,'middle');text(`${id}/population/header/visual`,x+58,318,'V count',8,true,'middle',COLORS.visual);text(`${id}/population/header/full`,x+108,318,'F count',8,true,'middle',COLORS.full);
  line(`${id}/population/header/rule`,x-5,323,x+pw+4,323,'#CAD2DA',.5);
  for(let bi=1;bi<=15;bi++){const yy=333+(bi-1)*11,v=series[0].allBins[bi-1],f=series[1].allBins[bi-1];text(`${id}/population/bin-${bi}/label`,x+8,yy,String(bi),8,false,'middle');text(`${id}/population/bin-${bi}/visual`,x+58,yy,String(v.count),8,false,'middle',v.count?COLORS.visual:'#737B83');text(`${id}/population/bin-${bi}/full`,x+108,yy,String(f.count),8,false,'middle',f.count?COLORS.full:'#737B83');}
  panels.push({seed,plot:{x,y,width:pw,height:ph},xRange:[0,1],yRange:[0,1],series});
 }
 text('x-axis-label',W/2,243,'Mean fixed margin score (fraction)',8,false,'middle');
 const footnotes=[
  'Score = clip((cosine Top-1 − Top-2 margin) / 2, 0, 1); fixed, not a posterior.',
  'Each variant assigns queries to its own 15 equal-width bins; members can differ.',
  'Only occupied bins have markers. N = 0 retains null mean/accuracy, not zero.',
  'Gray y = x shows numerical equality only. No fitted calibration or connecting curve.',
  'Stored ECE fractions rounded to four decimals. No seed/task pooling, SD, CI or p-values.',
  'Lower fixed-score ECE does not imply higher retrieval accuracy or better calibration.'
 ];footnotes.forEach((t,i)=>text(`footnote-${i+1}`,15,517+i*13,t,8));
 for(const p of primitives){const name=`${task}/${p.id}`;
  if(p.tag==='text'){ctx.font=`${p.bold?'bold':'normal'} ${p.fontSize*S}px Arial`;const tw=ctx.measureText(p.text).width+1,left=p.x*S-(p.anchor==='middle'?tw/2:p.anchor==='end'?tw:0);check(left>=0&&left+tw<=W*S,'Text horizontal page fit');check(p.y-p.fontSize>=0&&p.y+3<=H,'Text vertical page fit');const sh=slide.shapes.add({geometry:'textbox',name,position:{left,top:(p.y-p.fontSize*.92)*S,width:tw,height:p.fontSize*S*1.25},fill:'none',line:{fill:'none',width:0}});sh.text=p.text;sh.text.style={typeface:'Arial',fontSize:p.fontSize*S,bold:p.bold,color:p.fill,alignment:p.anchor==='middle'?'center':p.anchor==='end'?'right':'left',verticalAlignment:'top',autoFit:'none',wrap:'none',insets:{top:0,bottom:0,left:0,right:0}};}
  else if(p.tag==='line')slide.shapes.add({geometry:'line',name,position:{left:Math.min(p.x1,p.x2)*S,top:Math.min(p.y1,p.y2)*S,width:Math.abs(p.x2-p.x1)*S,height:Math.abs(p.y2-p.y1)*S,verticalFlip:(p.x2-p.x1)*(p.y2-p.y1)<0},fill:'none',line:{fill:p.stroke,width:p.width*S}});
  else slide.shapes.add({geometry:p.tag==='circle'?'ellipse':'rect',name,position:{left:(p.x-p.r)*S,top:(p.y-p.r)*S,width:p.r*2*S,height:p.r*2*S},fill:p.fill,line:{fill:p.stroke,width:p.width*S}});
 }
 const svg=[`<svg xmlns="http://www.w3.org/2000/svg" width="181.9mm" height="${HEIGHT_MM}mm" viewBox="0 0 ${W} ${H}">`,`<title>${escape(label(task)+': fixed margin-score reliability diagnostic')}</title>`,`<desc>Three separate seeds with stored occupied-bin mean score and empirical R1. Full fifteen-bin population tables; empty bins retain null mean and accuracy. Saved ECE, not recomputed. Fixed margin score is not a calibrated posterior.</desc>`,`<rect id="background" x="0" y="0" width="${W}" height="${H}" fill="white"/>`];
 for(const p of primitives){const id=`id="${escape(p.id)}"`;if(p.tag==='text')svg.push(`<text ${id} x="${p.x}" y="${p.y}" font-family="Arial" font-size="${p.fontSize}" font-weight="${p.bold?'bold':'normal'}" text-anchor="${p.anchor}" fill="${p.fill}">${escape(p.text)}</text>`);else if(p.tag==='line')svg.push(`<line ${id} x1="${p.x1}" y1="${p.y1}" x2="${p.x2}" y2="${p.y2}" stroke="${p.stroke}" stroke-width="${p.width}"/>`);else if(p.tag==='circle')svg.push(`<circle ${id} cx="${p.x}" cy="${p.y}" r="${p.r}" fill="${p.fill}" stroke="${p.stroke}" stroke-width="${p.width}"/>`);else svg.push(`<rect ${id} x="${p.x-p.r}" y="${p.y-p.r}" width="${p.r*2}" height="${p.r*2}" fill="${p.fill}" stroke="${p.stroke}" stroke-width="${p.width}"/>`);}
 svg.push('</svg>');const svgPath=path.join(OUT,'native_svg',`t5_reliability_${task}.svg`);await create(svgPath,svg.join('\n')+'\n');
 const caption=`${label(task)}. Fixed margin-score reliability diagnostic for seeds1,2,3 in separate panels. The score is clip((cosine Top-1 minus Top-2 margin)/2,0,1), a fixed transformation, not a posterior probability, trained/fitted calibration model or an independently established model confidence. Each occupied bin is plotted at its stored mean fixed normalized margin score (x) and stored empirical R@1 (y), both fractions on0–1 axes. Blue outlined circles denote Visual and orange outlined squares Full; true coordinates are unchanged, without jitter. Markers are not connected. The gray y=x line is a numerical equality reference only, not a claim of ideal or demonstrated calibration. The frozen15-bin assignment is min(int(15×score),14), i.e. left-closed/right-open equal-width bins, with the final bin including1. Saved boundary floats are preserved in tables; the figure does not reassign queries from displayed bounds or claim that no clipping occurred. Visual and Full each use their own score to assign queries to bins, so equal bin numbers do not imply shared bin members, even though the full official query set is shared. All15 original bin populations for each variant are displayed, including N=0. Empty bins retain null mean score and accuracy; they have no point and are never represented as accuracy0 or filled across gaps. The sum of displayed counts equals the saved task query N, but bin assignments/accuracy/gaps/ECE are not recomputed. Stored ECE is a fraction displayed to four decimals, not multiplied by100 or interpreted as accuracy. A lower fixed-score ECE does not imply higher retrieval accuracy and cannot alone establish improved probability calibration: both empirical accuracy and the margin-score side can change with the variant. No better-calibrated-method conclusion is drawn. The original ECE, weighted_absolute_gap and full-precision occupied values are in CSV/notes. Bin populations include small counts and imply no uncertainty estimate or minimum-size guarantee. No pooled seed/task/direction/height statistics, SD, CI, bootstrap interval, p-value or significance claims are shown. This package presents990 saved bins (140 occupied and850 empty) across66 native records and33 panels; it excludes native selective-risk curves and132 paired selection comparisons from the plotted scope. These are official clean-query outputs, not corruption comparisons. Upstream query-array validation is inherited; this build reads no NPZ, weights, cache or image and performs no scientific execution, model/full-ranking/all-positive-rank AP or ECE recomputation. All inherited checkpoint/cache/image SHA authority and historical metadata-chain gaps remain unchanged.`;
 slide.speakerNotes.textFrame.setText(`${caption}\n\nRoot adoption SHA256: ${ROOT_SHA}\nExact original T5 JSON SHA256: ${T5_SHA}\n\nAll90 saved bins for this task. Literal null means undefined empty-bin mean/accuracy, not zero:\n${pageCSVs.get(task)}`);
 figures.push({ordinal:ti+1,task,title:label(task),widthMm:181.9,heightMm:HEIGHT_MM,widthPt:W,heightPt:H,minFontPt:8,nativeRecords:6,binRecords:90,occupiedBins:rows.filter(b=>b.count>0).length,emptyBins:rows.filter(b=>b.count===0).length,panels,primitives,caption,svg:await describe(svgPath),sourceCSV:await describe(path.join(OUT,'source_data',`t5_${task}__reliability_bins.csv`))});
}
const candidate=path.join(BUILD,`t5_reliability_${MODE}.candidate.pptx`),final=path.join(OUT,`t5_reliability_native_editable_${TASKS.length}figures.pptx`),receipt=path.join(BUILD,`${MODE}.validation.json`);
await(await PresentationFile.exportPptx(pres)).save(candidate);
await finalizePresentation({workspaceDir:WORK,candidatePath:candidate,finalPath:final,explicitTotalSlideCount:TASKS.length,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],pythonExecutable:PYTHON,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu',`${Math.round(181.9*36000)},${Math.round(HEIGHT_MM*36000)}`,'--cover-role','none',...TASKS.flatMap((_,i)=>['--approved-dense-slide',String(i+1)])],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:receipt});
const imported=await PresentationFile.importPptx(await FileBlob.load(final));
for(let i=0;i<TASKS.length;i++){const fig=figures[i],png=path.join(OUT,'previews',`${String(i+1).padStart(2,'0')}_t5_reliability_${fig.task}.png`);await create(png,new Uint8Array(await(await imported.export({slide:imported.slides.items[i],format:'png',scale:2})).arrayBuffer()));fig.preview=await describe(png);console.log(JSON.stringify({page:i+1,task:fig.task,preview:png}));}
await create(path.join(WORK,SAMPLE?'BUILD_REPORT_SAMPLE.json':'BUILD_REPORT.json'),JSON.stringify({schema:'native-t5-reliability-build.v1',mode:MODE,utc:new Date().toISOString(),source:await describe(fileURLToPath(import.meta.url)),inputProvenance:await describe(provenance),checks,figureCount:TASKS.length,nativeRecords:TASKS.length*6,binRecords:TASKS.length*90,occupiedBins:figures.reduce((n,f)=>n+f.occupiedBins,0),emptyBins:figures.reduce((n,f)=>n+f.emptyBins,0),savedECEValues:TASKS.length*6,panels:TASKS.length*3,pptx:await describe(final),receipt:await describe(receipt),figures,scientificExecution:false,PowerPointOpened:false,rendering:'Every finalPPTX page imported and CPU rendered using artifact-tool',limits:['Native individually editable objects, not groups or Excel chart objects.','No NPZ/cache/image/checkpoint/model/ECE recomputation or old controls.','Producer, independent and root reviews remain separate.']},null,2));
console.log(JSON.stringify({complete:true,mode:MODE,checks,figures:TASKS.length}));
