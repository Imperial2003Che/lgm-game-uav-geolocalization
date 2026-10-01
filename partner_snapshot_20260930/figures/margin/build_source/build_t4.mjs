import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
import {createCanvas,GlobalFonts} from '@napi-rs/canvas';

const BUILD=path.dirname(fileURLToPath(import.meta.url)),WORK=path.dirname(BUILD);
const SAMPLE=process.argv.includes('--sample'),MODE=SAMPLE?'sample':'final',OUT=path.join(WORK,SAMPLE?'sample':'output');
const AUDIT=path.join(path.dirname(WORK),'execution/pipeline_post_robustness_audit_20260929_1448');
const SKILL='C:/Users/17703/.codex/plugins/cache/openai-primary-runtime/presentations/26.927.11222/skills/presentations';
const PYTHON='C:/Users/17703/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const ROOT_SHA='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a';
const CAP_SHA='473d5fba90c3fc0d044733ffb19e1f2955f08df96f89d4c643ad54d6ff15ca09';
const T4_SHA='42090c4ffdafedbfffd8ed2439e1e59756f0876e2c7ae612a87031a574b28cc8';
const CSV_SHA='bc1725e7d5a1ce298f2de579240d65ced823b57d0d2af8bcb077a9d697d66530';
const W=181.9*72/25.4,H=607,S=4/3,HEIGHT_MM=H*25.4/72,COLORS={visual:'#0072B2',full:'#D55E00'};
const LEVELS=['q1_low','q2_mid_low','q3_mid_high','q4_high'];
const METRICS=[['r_at_1','R@1 (%)'],['official_trapezoid_mAP','Official trapezoidal mAP (%)'],['MRR','MRR × 100 (scaled MRR)']];
const ALL_TASKS=['university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite',...[150,200,250,300].flatMap(h=>[`sues200_uav_${h}m_to_satellite`,`sues200_satellite_to_uav_${h}m`])];
const TASKS=SAMPLE?['university1652_street_to_satellite','sues200_satellite_to_uav_150m']:ALL_TASKS;
let checks=0;const check=(v,m)=>{checks++;if(!v)throw new Error(m);};
const hash=b=>createHash('sha256').update(b).digest('hex'),norm=p=>path.normalize(p).toLowerCase(),inputs=[];
const describe=async p=>{const b=await fs.readFile(p);return {path:p,sha256:hash(b),bytes:b.length};};
const create=async(p,b)=>fs.writeFile(p,b,{flag:'wx'});
async function bind(p,expected){const b=await fs.readFile(p);check(hash(b)===expected.sha256&&(expected.bytes===undefined||expected.bytes===b.length),'SHA/size '+p);inputs.push({path:p,sha256:hash(b),bytes:b.length});return b;}
const rootPath=path.join(AUDIT,'ROOT_POST_ROBUSTNESS_ADOPTION.json'),rootBytes=await bind(rootPath,{sha256:ROOT_SHA}),root=JSON.parse(rootBytes);
check(root.accepted_with_stated_limits===true,'Accepted scientific root');
const rootMap=new Map(root.bindings.map(x=>[norm(x.path),x]));
const capturePath=path.join(AUDIT,'a1/CAPTURE.json');check(rootMap.get(norm(capturePath)).sha256===CAP_SHA,'Adopted capture');
const captureBytes=await bind(capturePath,rootMap.get(norm(capturePath))),capture=JSON.parse(captureBytes),raw={};
for(const [name,sha256,bytes] of [['transactions_t4_strata.json',T4_SHA,896696],['transactions_t4_strata.csv',CSV_SHA,143708]]){
 const snapshot=path.join(AUDIT,'a1/query',name),binding=rootMap.get(norm(snapshot));
 check(binding&&binding.sha256===sha256&&binding.bytes===bytes,'Exact adopted T4 snapshot');
 const cap=capture.bindings.filter(x=>norm(x.snapshot)===norm(snapshot));check(cap.length===1&&cap[0].sha256===sha256&&cap[0].bytes===bytes,'Unique immutable capture binding');
 raw[name]=await bind(snapshot,binding);await create(path.join(OUT,'source_data',name),raw[name]);
}
await create(path.join(OUT,'provenance/ROOT_POST_ROBUSTNESS_ADOPTION.json'),rootBytes);
await create(path.join(OUT,'provenance/CAPTURE.json'),captureBytes);
for(const name of ['README.md','REVIEW.json']){
 const p=path.join(AUDIT,name),b=await fs.readFile(p),binding=rootMap.get(norm(p));
 if(binding)check(hash(b)===binding.sha256&&b.length===binding.bytes,'Root-bound contextual report');
 inputs.push({path:p,sha256:hash(b),bytes:b.length,role:'Contextual upstream report; JSON/CSV admission uses pinned root and capture',rootBound:!!binding});
 await create(path.join(OUT,'provenance',`UPSTREAM_${name}`),b);
}
const t4=JSON.parse(raw['transactions_t4_strata.json']);
check(t4.status==='completed'&&t4.unit==='fraction'&&t4.schema_version==='lgm-game.transactions-t4-strata.v1','Completed expected T4 schema');
check(t4.rows.length===462&&t4.observed_row_count===462&&t4.registered_row_count===462&&t4.minimum_queries_for_performance_claim===100,'Frozen full T4 count and claim threshold');
const selected=t4.rows.filter(r=>r.factor==='visual_margin_quartile');
check(selected.length===132&&new Set(selected.map(r=>`${r.task}/${r.seed}/${r.level}`)).size===132,'Unique 132 selected margin strata');
check(selected.filter(r=>r.summary.performance_claim_eligible).length===84,'84 eligible strata');
const flat=[];
for(const task of ALL_TASKS)for(const seed of [1,2,3])for(const [qi,level] of LEVELS.entries()){
 const matches=selected.filter(r=>r.task===task&&r.seed===seed&&r.level===level);check(matches.length===1,'Complete registered margin stratum');const r=matches[0],s=r.summary;
 check(r.metadata.boundary_rule==='linear quantiles; values equal to a cutpoint enter the lower interval','Frozen boundary rule');
 check(r.metadata.quartile_cutpoints.length===3&&r.metadata.quartile_cutpoints.every(Number.isFinite),'Saved finite linear cutpoints');
 check(s.minimum_queries_for_claim===100&&s.performance_claim_eligible===(s.queries>=100)&&Number.isInteger(s.queries)&&s.queries>0,'Saved N and exact eligibility');
 if(!s.performance_claim_eligible)check(/^sues200_satellite_to_uav_(150|200|250|300)m$/.test(task)&&s.queries===20,'All false groups exactly N20 SUES satellite-to-UAV');
 const out={dataset:r.dataset,task,seed,factor:r.factor,level,quartile:qi+1,queries:s.queries,performance_claim_eligible:s.performance_claim_eligible,minimum_queries_for_claim:100,membership_sha256:r.membership_sha256,cutpoint_25:r.metadata.quartile_cutpoints[0],cutpoint_50:r.metadata.quartile_cutpoints[1],cutpoint_75:r.metadata.quartile_cutpoints[2]};
 for(const [metric] of METRICS){const m=s.metrics[metric];for(const v of ['visual','full']){check(Number.isFinite(m[v])&&m[v]>=0&&m[v]<=1,'Finite saved fraction');out[`${v}_${metric}`]=m[v];out[`${v}_${metric}_x100`]=m[v]*100;}check(Math.abs((m.full-m.visual)-m.full_minus_visual)<1e-12,'Saved difference consistency');out[`full_minus_visual_${metric}`]=m.full_minus_visual;}
 out.source_json_sha256=T4_SHA;flat.push(out);
}
const headers=Object.keys(flat[0]);function csv(rows){return headers.join(',')+'\n'+rows.map(r=>headers.map(k=>String(r[k])).join(',')).join('\n')+'\n';}
await create(path.join(OUT,'source_data/MARGIN_STRATA_132.csv'),csv(flat));
const pageCSVs=new Map();for(const task of TASKS){const b=csv(flat.filter(r=>r.task===task));pageCSVs.set(task,b);await create(path.join(OUT,'source_data',`t4_${task}__margin_strata.csv`),b);}
const provenance=path.join(WORK,SAMPLE?'INPUT_PROVENANCE_SAMPLE.json':'INPUT_PROVENANCE.json');
await create(provenance,JSON.stringify({schema:'native-t4-margin-input-provenance.v1',mode:MODE,rootSha256:ROOT_SHA,inputs,selectedStrata:132,selectedEligible:84,selectedIneligible:48,plottedTasks:TASKS,plottedStrata:TASKS.length*12,plottedPanels:TASKS.length*9,plottedValues:TASKS.length*72,otherStrataPreservedNotPlotted:330,derivedCSV:'Direct field flattening and multiplication by100 only. No query-array, quantile, membership, mean or inference recomputation.',copies:await Promise.all((await fs.readdir(path.join(OUT,'source_data'))).map(n=>describe(path.join(OUT,'source_data',n))))},null,2));
check(GlobalFonts.families.some(f=>f.family==='Arial'),'Arial available');
const ctx=createCanvas(1,1).getContext('2d'),escape=v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function label(task){if(task.startsWith('university1652_'))return 'University-1652: '+({'drone_to_satellite':'Drone → satellite','satellite_to_drone':'Satellite → drone','street_to_satellite':'Street → satellite'}[task.replace('university1652_','')]);let m=task.match(/^sues200_uav_(\d+)m_to_satellite$/);if(m)return `SUES-200: UAV ${m[1]} m → satellite`;m=task.match(/^sues200_satellite_to_uav_(\d+)m$/);check(m,'SUES task name');return `SUES-200: Satellite → UAV ${m[1]} m`;}
const pres=Presentation.create({slideSize:{width:W*S,height:H*S}}),figures=[];
for(let ti=0;ti<TASKS.length;ti++){
 const task=TASKS[ti],taskRows=flat.filter(r=>r.task===task),slide=pres.slides.add();slide.background.fill='#FFFFFF';const primitives=[],panels=[];
 const add=(tag,id,a)=>primitives.push({tag,id,...a});
 const text=(id,x,y,content,size=8,bold=false,anchor='start',fill='#222222')=>add('text',id,{x,y,text:content,fontSize:size,bold,anchor,fill});
 const line=(id,x1,y1,x2,y2,stroke='#444444',width=.6)=>add('line',id,{x1,y1,x2,y2,stroke,width});
 const marker=(id,x,y,variant)=>add(variant==='visual'?'circle':'rect',id,{x,y,r:1.85,fill:COLORS[variant]});
 text('title',15,18,label(task),10,true);
 text('subtitle',15,34,'Performance within shared Visual-margin quartiles',9,true);
 marker('legend/visual/marker',18,48,'visual');text('legend/visual/text',26,51,'Visual (V)',8);marker('legend/full/marker',108,48,'full');text('legend/full/text',116,51,'Full (F)',8);
 text('legend/values',197,51,'Values below plots: V then F, to three decimals',8);
 for(const seed of [1,2,3]){
  const x=42+(seed-1)*158,pw=126;
  text(`seed-${seed}/heading`,x+pw/2,70,`Seed ${seed}`,9,true,'middle');
  text(`seed-${seed}/N-label`,x-8,97,'N',8,true,'end');
  for(let qi=0;qi<4;qi++){const xx=x+(qi+.5)*pw/4,r=taskRows.find(r=>r.seed===seed&&r.quartile===qi+1);text(`seed-${seed}/quartile-${qi+1}/N-heading`,xx,84,`Q${qi+1}`,8,true,'middle');text(`seed-${seed}/quartile-${qi+1}/N-value`,xx,97,`${r.queries}${r.performance_claim_eligible?'':'†'}`,8,false,'middle');}
 }
 for(const [mi,[metric,title]] of METRICS.entries()){
  text(`${metric}/row-heading`,15,116+mi*135,title,9,true);
  for(const seed of [1,2,3]){
   const id=`${task}/seed-${seed}/${metric}`,x=42+(seed-1)*158,y=128+mi*135,pw=126,ph=77,bottom=y+ph;
   for(const v of [0,25,50,75,100]){const yy=bottom-v/100*ph;line(`${id}/y-grid-${v}`,x,yy,x+pw,yy,'#E0E6EC',.45);text(`${id}/y-label-${v}`,x-5,yy+2.7,String(v),8,false,'end');}
   line(`${id}/y-axis`,x,y,x,bottom);line(`${id}/x-axis`,x,bottom,x+pw,bottom);
   for(let qi=0;qi<4;qi++){const xx=x+(qi+.5)*pw/4;line(`${id}/x-tick-Q${qi+1}`,xx,bottom,xx,bottom+3);text(`${id}/x-label-Q${qi+1}`,xx,bottom+12,`Q${qi+1}`,8,false,'middle');}
   const series=[];
   for(const variant of ['visual','full']){
    const points=LEVELS.map((level,qi)=>{const r=taskRows.find(a=>a.seed===seed&&a.level===level),fraction=r[`${variant}_${metric}`];return {level,quartile:qi+1,queries:r.queries,performance_claim_eligible:r.performance_claim_eligible,membership_sha256:r.membership_sha256,fraction,scaledValue:fraction*100,x:x+(qi+.5)*pw/4,y:bottom-fraction*ph};});
    for(let qi=1;qi<4;qi++)line(`${id}/${variant}/segment-Q${qi}-Q${qi+1}`,points[qi-1].x,points[qi-1].y,points[qi].x,points[qi].y,COLORS[variant],.9);
    for(const p of points){marker(`${id}/${variant}/point-Q${p.quartile}`,p.x,p.y,variant);text(`${id}/${variant}/value-Q${p.quartile}`,p.x,bottom+(variant==='visual'?25:36),p.scaledValue.toFixed(3),8,false,'middle',COLORS[variant]);}
    text(`${id}/${variant}/value-prefix`,x-8,bottom+(variant==='visual'?25:36),variant==='visual'?'V':'F',8,true,'end',COLORS[variant]);series.push({variant,points});
   }
   panels.push({seed,metric,metricLabel:title,plot:{x,y,width:pw,height:ph},xCategories:LEVELS,yRange:[0,100],series});
  }
 }
 const footnotes=[
  'Q1–Q4: low to high Visual margin, defined separately for each task and seed.',
  'Linear quartile cutpoints; boundary ties enter the lower interval. Members are shared.',
  '† N < 100: performance_claim_eligible=false; descriptive only. N is per quartile.',
  'Eligible strata imply no significance. No pooling, SD, CI, bootstrap or p-values shown.',
  'Segments guide categorical groups, not continuous margins. Margin is not a posterior.'
 ];footnotes.forEach((t,i)=>text(`footnote-${i+1}`,15,538+i*13,t,8));
 for(const p of primitives){const name=`${task}/${p.id}`;
  if(p.tag==='text'){ctx.font=`${p.bold?'bold':'normal'} ${p.fontSize*S}px Arial`;const tw=ctx.measureText(p.text).width+1,left=p.x*S-(p.anchor==='middle'?tw/2:p.anchor==='end'?tw:0);check(left>=0&&left+tw<=W*S,'Text horizontal page fit');check(p.y-p.fontSize>=0&&p.y+3<=H,'Text vertical page fit');const sh=slide.shapes.add({geometry:'textbox',name,position:{left,top:(p.y-p.fontSize*.92)*S,width:tw,height:p.fontSize*S*1.25},fill:'none',line:{fill:'none',width:0}});sh.text=p.text;sh.text.style={typeface:'Arial',fontSize:p.fontSize*S,bold:p.bold,color:p.fill,alignment:p.anchor==='middle'?'center':p.anchor==='end'?'right':'left',verticalAlignment:'top',autoFit:'none',wrap:'none',insets:{top:0,bottom:0,left:0,right:0}};}
  else if(p.tag==='line')slide.shapes.add({geometry:'line',name,position:{left:Math.min(p.x1,p.x2)*S,top:Math.min(p.y1,p.y2)*S,width:Math.abs(p.x2-p.x1)*S,height:Math.abs(p.y2-p.y1)*S,verticalFlip:(p.x2-p.x1)*(p.y2-p.y1)<0},fill:'none',line:{fill:p.stroke,width:p.width*S}});
  else slide.shapes.add({geometry:p.tag==='circle'?'ellipse':'rect',name,position:{left:(p.x-p.r)*S,top:(p.y-p.r)*S,width:p.r*2*S,height:p.r*2*S},fill:p.fill,line:{fill:'none',width:0}});
 }
 const svg=[`<svg xmlns="http://www.w3.org/2000/svg" width="181.9mm" height="${HEIGHT_MM}mm" viewBox="0 0 ${W} ${H}">`,`<title>${escape(label(task)+': shared Visual-margin quartile performance')}</title>`,`<desc>Three seeds and three metrics, 72 saved values. Common query members within Visual-defined linear margin quartiles. Categorical Q1–Q4, zero-start axes. No pooling or inference. N below100 flagged ineligible.</desc>`,`<rect id="background" x="0" y="0" width="${W}" height="${H}" fill="white"/>`];
 for(const p of primitives){const id=`id="${escape(p.id)}"`;if(p.tag==='text')svg.push(`<text ${id} x="${p.x}" y="${p.y}" font-family="Arial" font-size="${p.fontSize}" font-weight="${p.bold?'bold':'normal'}" text-anchor="${p.anchor}" fill="${p.fill}">${escape(p.text)}</text>`);else if(p.tag==='line')svg.push(`<line ${id} x1="${p.x1}" y1="${p.y1}" x2="${p.x2}" y2="${p.y2}" stroke="${p.stroke}" stroke-width="${p.width}"/>`);else if(p.tag==='circle')svg.push(`<circle ${id} cx="${p.x}" cy="${p.y}" r="${p.r}" fill="${p.fill}"/>`);else svg.push(`<rect ${id} x="${p.x-p.r}" y="${p.y-p.r}" width="${p.r*2}" height="${p.r*2}" fill="${p.fill}"/>`);}
 svg.push('</svg>');const svgPath=path.join(OUT,'native_svg',`t4_${task}.svg`);await create(svgPath,svg.join('\n')+'\n');
 const caption=`${label(task)}. Three seeds are separate columns and R@1, official trapezoidal mAP, and MRR are separate rows. R@1 and mAP fractions are multiplied by100 and labelled percent; MRR×100 is scaled MRR, not accuracy percent. All axes start at0 and end at100. Each panel shows Visual and Full for the four saved Visual-margin quartiles (Q1 low, Q2 mid-low, Q3 mid-high, Q4 high). These are ordered categories, not equally spaced raw margin values; segments are categorical visual guides. Quartiles use saved linear25/50/75 percentiles within each official task and seed; a value equal to a cutpoint enters the lower interval. Full queries were aligned to Visual before the same Visual-defined membership mask was used for both variants. Counts N and eligibility are copied from the accepted summary, not reconstructed or assumed to be equal-sized rank bins. Dagger flags the saved performance_claim_eligible=false groups because N<100. Exactly48 of the132 selected strata are ineligible, all N20 satellite-to-UAV SUES groups; the other84 pass the N>=100 count gate only, not an inferential/significance criterion. Each panel also displays all eight saved metric values×100 to three decimals, preserving very small values despite the common0–100 scale. Exact fraction values, cutpoints, membership SHA and flags are in notes/CSV. The factor is defined from Visual itself, making this a Visual-anchored conditional comparison, not causal/mechanistic attribution or independent calibration evidence; raw margin is not a calibrated posterior. No new means, quantiles, memberships, model predictions or statistics are computed. No seed/task/height pooling, SD, confidence interval, bootstrap interval, p-value or significance is displayed. Upstream bootstrap intervals were not independently resampled and are deliberately excluded. Only132 visual_margin_quartile strata are plotted (792 values across99 panels); the other330 entropy/semantic strata remain in exact source copies but are not plotted. Stored AP/RR/margins, inherited checkpoint/cache/image SHA authority and historical evidence-chain gaps retain upstream limits; no NPZ, weights, cache, images, full rankings or all-positive-rank AP are read/recomputed here.`;
 slide.speakerNotes.textFrame.setText(`${caption}\n\nRoot adoption SHA256: ${ROOT_SHA}\nOriginal T4 JSON SHA256: ${T4_SHA}\nOriginal full T4 CSV SHA256: ${CSV_SHA}\n\nAll12 shared-margin strata for this task, direct saved fields and×100 only:\n${pageCSVs.get(task)}`);
 figures.push({ordinal:ti+1,task,title:label(task),widthMm:181.9,heightMm:HEIGHT_MM,widthPt:W,heightPt:H,minFontPt:8,strata:12,metricPanels:9,numericPoints:72,eligibleStrata:taskRows.filter(r=>r.performance_claim_eligible).length,ineligibleStrata:taskRows.filter(r=>!r.performance_claim_eligible).length,panels,primitives,caption,svg:await describe(svgPath),sourceCSV:await describe(path.join(OUT,'source_data',`t4_${task}__margin_strata.csv`))});
}
const candidate=path.join(BUILD,`t4_margin_${MODE}.candidate.pptx`),final=path.join(OUT,`t4_margin_native_editable_${TASKS.length}figures.pptx`),receipt=path.join(BUILD,`${MODE}.validation.json`);
await(await PresentationFile.exportPptx(pres)).save(candidate);
await finalizePresentation({workspaceDir:WORK,candidatePath:candidate,finalPath:final,explicitTotalSlideCount:TASKS.length,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],pythonExecutable:PYTHON,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu',`${Math.round(181.9*36000)},${Math.round(HEIGHT_MM*36000)}`,'--cover-role','none',...TASKS.flatMap((_,i)=>['--approved-dense-slide',String(i+1)])],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:receipt});
const imported=await PresentationFile.importPptx(await FileBlob.load(final));
for(let i=0;i<TASKS.length;i++){const fig=figures[i],png=path.join(OUT,'previews',`${String(i+1).padStart(2,'0')}_t4_${fig.task}.png`);await create(png,new Uint8Array(await(await imported.export({slide:imported.slides.items[i],format:'png',scale:2})).arrayBuffer()));fig.preview=await describe(png);console.log(JSON.stringify({page:i+1,task:fig.task,preview:png}));}
await create(path.join(WORK,SAMPLE?'BUILD_REPORT_SAMPLE.json':'BUILD_REPORT.json'),JSON.stringify({schema:'native-t4-margin-build.v1',mode:MODE,utc:new Date().toISOString(),source:await describe(fileURLToPath(import.meta.url)),inputProvenance:await describe(provenance),checks,figureCount:TASKS.length,plottedStrata:TASKS.length*12,metricPanels:TASKS.length*9,numericPoints:TASKS.length*72,allSelectedStrata:132,eligibleStrata:84,ineligibleStrata:48,otherStrataNotPlotted:330,pptx:await describe(final),receipt:await describe(receipt),figures,scientificExecution:false,PowerPointOpened:false,rendering:'Every finalPPTX page imported and CPU rendered using artifact-tool',limits:['Native individual editable shapes, not groups or Excel chart objects.','No model/cache/image/checkpoint/NPZ or original query-statistic recomputation.','Producer checks, independent review and root adoption remain separate.']},null,2));
console.log(JSON.stringify({complete:true,mode:MODE,checks,figures:TASKS.length,points:TASKS.length*72}));
