import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
import {createCanvas,GlobalFonts} from '@napi-rs/canvas';

const BUILD=path.dirname(fileURLToPath(import.meta.url)),WORK=path.dirname(BUILD),OUT=path.join(WORK,'output_v2');
const AUDIT=path.join(path.dirname(WORK),'execution/pipeline_post_robustness_audit_20260929_1448');
const SKILL='C:/Users/17703/.codex/plugins/cache/openai-primary-runtime/presentations/26.927.11222/skills/presentations';
const PYTHON='C:/Users/17703/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const ROOT_SHA='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a';
const CAP_SHA='473d5fba90c3fc0d044733ffb19e1f2955f08df96f89d4c643ad54d6ff15ca09';
const T5_SHA='033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc';
const CSV_SHA='2dc5b6bf9fba1edbde657427f516e0b539b310fb93f49511444a2061e598b40e';
const W=181.9*72/25.4,H=383,S=4/3,HEIGHT_MM=H*25.4/72,COLORS={visual:'#0072B2',full:'#D55E00'};
let checks=0;const check=(v,m)=>{checks++;if(!v)throw new Error(m);};
const hash=b=>createHash('sha256').update(b).digest('hex'),norm=p=>path.normalize(p).toLowerCase();
const inputs=[];
const describe=async p=>{const b=await fs.readFile(p);return {path:p,sha256:hash(b),bytes:b.length};};
const create=async(p,b)=>fs.writeFile(p,b,{flag:'wx'});
async function bind(p,expected){const b=await fs.readFile(p);check(hash(b)===expected.sha256&&(expected.bytes===undefined||expected.bytes===b.length),'SHA/size '+p);inputs.push({path:p,sha256:hash(b),bytes:b.length});return b;}
const rootPath=path.join(AUDIT,'ROOT_POST_ROBUSTNESS_ADOPTION.json'),rootBytes=await bind(rootPath,{sha256:ROOT_SHA}),root=JSON.parse(rootBytes);
check(root.accepted_with_stated_limits===true,'Accepted root');
const rootMap=new Map(root.bindings.map(x=>[norm(x.path),x]));
const capturePath=path.join(AUDIT,'a1/CAPTURE.json');check(rootMap.get(norm(capturePath)).sha256===CAP_SHA,'Exact adopted capture');
const captureBytes=await bind(capturePath,rootMap.get(norm(capturePath))),capture=JSON.parse(captureBytes);
const raw={};
for(const [name,sha256,bytes] of [['transactions_t5_selective_calibration.json',T5_SHA,744943],['transactions_t5_selective_comparisons.csv',CSV_SHA,20814]]){
 const snapshot=path.join(AUDIT,'a1/query',name),binding=rootMap.get(norm(snapshot));
 check(binding&&binding.sha256===sha256&&binding.bytes===bytes,'Exact adopted T5 snapshot');
 const cap=capture.bindings.filter(x=>norm(x.snapshot)===norm(snapshot));check(cap.length===1&&cap[0].sha256===sha256&&cap[0].bytes===bytes,'One immutable capture snapshot binding');
 raw[name]=await bind(snapshot,binding);await create(path.join(OUT,'source_data',name),raw[name]);
}
await create(path.join(OUT,'provenance/ROOT_POST_ROBUSTNESS_ADOPTION.json'),rootBytes);
await create(path.join(OUT,'provenance/CAPTURE.json'),captureBytes);
const t5=JSON.parse(raw['transactions_t5_selective_calibration.json']);
check(t5.status==='completed'&&t5.unit==='fraction'&&t5.schema_version==='lgm-game.transactions-t5-selective-calibration.v1','Completed expected T5 schema');
check(t5.native_rows.length===66&&t5.registered_native_row_count===66&&t5.paired_comparisons.length===132&&t5.registered_comparison_count===132,'66 native/132 paired accepted rows');
const TASKS=['university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite',...[150,200,250,300].flatMap(h=>[`sues200_uav_${h}m_to_satellite`,`sues200_satellite_to_uav_${h}m`])];
check(new Set(t5.native_rows.map(r=>`${r.task}/${r.seed}/${r.variant}`)).size===66,'Unique native task/seed/variant keys');
check([...new Set(t5.paired_comparisons.map(r=>r.requested_coverage))].sort((a,b)=>a-b).join(',')==='0.5,0.75,0.9,1','Paired comparison coverages preserved and excluded from plot');
const flat=[];
for(const task of TASKS)for(const seed of [1,2,3])for(const variant of ['visual','full']){
 const rows=t5.native_rows.filter(r=>r.task===task&&r.seed===seed&&r.variant===variant);check(rows.length===1,'Complete exact plotted native keys');const r=rows[0],rc=r.risk_coverage;
 check(rc.rows.length===10&&Number.isInteger(rc.queries)&&rc.queries>0,'Ten native points and N');
 check(rc.ranking==='descending raw cosine Top-1 margin with stable query-order ties','Frozen margin selection statement');
 check(Number.isFinite(rc.AURC_discrete_all_prefixes)&&rc.AURC_discrete_all_prefixes>=0&&rc.AURC_discrete_all_prefixes<=1,'Finite saved all-prefix AURC');
 for(let i=0;i<10;i++){const p=rc.rows[i];check(p.requested_coverage===(i+1)/10,'Exact ten requested coverage levels');check(p.selected_queries===Math.ceil(p.requested_coverage*rc.queries),'Saved ceil-selected count');check(Math.abs(p.realized_coverage-p.selected_queries/rc.queries)<1e-14,'Saved realized count/N');check(p.selective_risk>=0&&p.selective_risk<=1&&Math.abs(p.selective_risk-(1-p.selective_r_at_1))<1e-14,'Saved risk complement/range');flat.push({dataset:r.dataset,task,seed,variant,queries:rc.queries,point_index:i+1,requested_coverage:p.requested_coverage,selected_queries:p.selected_queries,realized_coverage:p.realized_coverage,selective_r_at_1:p.selective_r_at_1,selective_risk:p.selective_risk,AURC_discrete_all_prefixes:rc.AURC_discrete_all_prefixes,query_membership_sha256:r.query_membership_sha256,selection_index_membership_sha256:p.selection_index_membership_sha256,source_json_sha256:T5_SHA});}
}
check(flat.length===660,'All 660 native points');
const headers=Object.keys(flat[0]);
function csv(rows){return headers.join(',')+'\n'+rows.map(r=>headers.map(k=>String(r[k])).join(',')).join('\n')+'\n';}
await create(path.join(OUT,'source_data/NATIVE_POINTS_660.csv'),csv(flat));
const pageCSVs=new Map();
for(const task of TASKS){const text=csv(flat.filter(r=>r.task===task));pageCSVs.set(task,text);await create(path.join(OUT,'source_data',`t5_${task}__native_points.csv`),text);}
await create(path.join(WORK,'INPUT_PROVENANCE_V2.json'),JSON.stringify({schema:'native-t5-input-provenance.v1',rootSha256:ROOT_SHA,inputs,plottedNativeRows:66,plottedNativePoints:660,pairedRowsPreservedNotPlotted:132,derivedCSV:'Direct field flattening from the bound T5 JSON; no query-array or AURC recomputation.',copies:await Promise.all((await fs.readdir(path.join(OUT,'source_data'))).map(n=>describe(path.join(OUT,'source_data',n)))),limits:'Reads only adopted small JSON/CSV and adoption/capture metadata; no old metrics/NPZ/cache/image/checkpoint/scientific execution.'},null,2));
check(GlobalFonts.families.some(f=>f.family==='Arial'),'Arial available');
const ctx=createCanvas(1,1).getContext('2d'),escape=v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function label(task){if(task.startsWith('university1652_'))return 'University-1652: '+({'drone_to_satellite':'Drone → satellite','satellite_to_drone':'Satellite → drone','street_to_satellite':'Street → satellite'}[task.replace('university1652_','')]);let m=task.match(/^sues200_uav_(\d+)m_to_satellite$/);if(m)return `SUES-200: UAV ${m[1]} m → satellite`;m=task.match(/^sues200_satellite_to_uav_(\d+)m$/);check(m,'SUES task name');return `SUES-200: Satellite → UAV ${m[1]} m`;}
const pres=Presentation.create({slideSize:{width:W*S,height:H*S}}),figures=[];
for(let ti=0;ti<TASKS.length;ti++){
 const task=TASKS[ti],taskRows=t5.native_rows.filter(r=>r.task===task),N=taskRows[0].risk_coverage.queries;
 check(taskRows.every(r=>r.risk_coverage.queries===N),'Same official query N per task');
 const slide=pres.slides.add();slide.background.fill='#FFFFFF';const primitives=[],panels=[];
 const add=(tag,id,a)=>primitives.push({tag,id,...a});
 const text=(id,x,y,content,size=8,bold=false,anchor='start',fill='#222222')=>add('text',id,{x,y,text:content,fontSize:size,bold,anchor,fill});
 const line=(id,x1,y1,x2,y2,stroke='#444444',width=.6)=>add('line',id,{x1,y1,x2,y2,stroke,width});
 const marker=(id,x,y,variant)=>add(variant==='visual'?'circle':'rect',id,{x,y,r:1.85,fill:COLORS[variant]});
 text('title',15,18,label(task),10,true);
 text('subtitle',15,34,`Selective risk by margin-ranked coverage; N = ${N.toLocaleString('en-US')} queries`,9,true);
 marker('legend/visual/marker',18,48,'visual');text('legend/visual/text',26,51,'Visual',8);
 marker('legend/full/marker',89,48,'full');text('legend/full/text',97,51,'Full',8);
 text('risk-axis-label',15,70,'Selective risk = 1 − R@1 among selected queries (%)',8);
 for(const seed of [1,2,3]){
  const x=42+(seed-1)*158,y=99,pw=126,ph=136,bottom=y+ph;
  text(`seed-${seed}/heading`,x+pw/2,86,`Seed ${seed}`,9,true,'middle');
  for(const v of [0,25,50,75,100]){
   const yy=bottom-v/100*ph;line(`seed-${seed}/y-grid-${v}`,x,yy,x+pw,yy,'#E0E6EC',.45);text(`seed-${seed}/y-label-${v}`,x-5,yy+2.7,String(v),8,false,'end');
   const xx=x+v/100*pw;line(`seed-${seed}/x-tick-${v}`,xx,bottom,xx,bottom+3,'#444444',.6);text(`seed-${seed}/x-label-${v}`,xx,bottom+14,String(v),8,false,'middle');
  }
  line(`seed-${seed}/y-axis`,x,y,x,bottom);line(`seed-${seed}/x-axis`,x,bottom,x+pw,bottom);
  const series=[];
  for(const variant of ['visual','full']){
   const r=taskRows.find(r=>r.seed===seed&&r.variant===variant),points=r.risk_coverage.rows.map((p,i)=>({index:i+1,...p,x:x+p.realized_coverage*pw,y:bottom-p.selective_risk*ph}));
   for(let i=1;i<points.length;i++)line(`${task}/seed-${seed}/${variant}/segment-${i}-${i+1}`,points[i-1].x,points[i-1].y,points[i].x,points[i].y,COLORS[variant],1.0);
   for(const p of points)marker(`${task}/seed-${seed}/${variant}/point-${p.index}`,p.x,p.y,variant);
   const saved=r.risk_coverage.AURC_discrete_all_prefixes;
   text(`seed-${seed}/${variant}/AURC`,x+pw/2,294+(variant==='full'?12:0),`${variant==='visual'?'Visual':'Full'} ${saved.toFixed(4)}`,8,false,'middle',COLORS[variant]);
   series.push({variant,AURC_discrete_all_prefixes:saved,points});
  }
  text(`seed-${seed}/AURC-label`,x+pw/2,282,'All-prefix AURC (fraction)',8,false,'middle');
  panels.push({seed,plot:{x,y,width:pw,height:ph},xRange:[0,100],yRange:[0,100],series});
 }
 text('coverage-axis-label',W/2,266,'Realized coverage = selected queries / N (%)',8,false,'middle');
 const footnotes=[
  'Selection: top k = ceil(requested coverage × N), ranked by raw cosine Top-1 margin.',
  'Margin is not a calibrated probability. Ties retain the source query order.',
  'Points: ten registered coverage levels; connecting segments are visual guides only.',
  'Seeds and tasks stay separate. No CI or significance shown; AURC uses all prefixes.'
 ];footnotes.forEach((t,i)=>text(`footnote-${i+1}`,15,330+i*13,t,8));
 for(const p of primitives){const name=`${task}/${p.id}`;
  if(p.tag==='text'){ctx.font=`${p.bold?'bold':'normal'} ${p.fontSize*S}px Arial`;const tw=ctx.measureText(p.text).width+1,left=p.x*S-(p.anchor==='middle'?tw/2:p.anchor==='end'?tw:0);check(left>=0&&left+tw<=W*S,'Text horizontal page fit');check(p.y-p.fontSize>=0&&p.y+3<=H,'Text vertical page fit');const sh=slide.shapes.add({geometry:'textbox',name,position:{left,top:(p.y-p.fontSize*.92)*S,width:tw,height:p.fontSize*S*1.25},fill:'none',line:{fill:'none',width:0}});sh.text=p.text;sh.text.style={typeface:'Arial',fontSize:p.fontSize*S,bold:p.bold,color:p.fill,alignment:p.anchor==='middle'?'center':p.anchor==='end'?'right':'left',verticalAlignment:'top',autoFit:'none',wrap:'none',insets:{top:0,bottom:0,left:0,right:0}};}
  else if(p.tag==='line')slide.shapes.add({geometry:'line',name,position:{left:Math.min(p.x1,p.x2)*S,top:Math.min(p.y1,p.y2)*S,width:Math.abs(p.x2-p.x1)*S,height:Math.abs(p.y2-p.y1)*S,verticalFlip:(p.x2-p.x1)*(p.y2-p.y1)<0},fill:'none',line:{fill:p.stroke,width:p.width*S}});
  else slide.shapes.add({geometry:p.tag==='circle'?'ellipse':'rect',name,position:{left:(p.x-p.r)*S,top:(p.y-p.r)*S,width:p.r*2*S,height:p.r*2*S},fill:p.fill,line:{fill:'none',width:0}});
 }
 const svg=[`<svg xmlns="http://www.w3.org/2000/svg" width="181.9mm" height="${HEIGHT_MM}mm" viewBox="0 0 ${W} ${H}">`,`<title>${escape(label(task)+': selective risk and coverage')}</title>`,`<desc>Three seeds shown separately. Sixty native observed points at actual selected-count coverage. Connecting lines are visual guides, not complete all-prefix curves. Saved AURC uses all prefixes. No CI or significance. Margin is not a calibrated posterior.</desc>`,`<rect id="background" x="0" y="0" width="${W}" height="${H}" fill="white"/>`];
 for(const p of primitives){const id=`id="${escape(p.id)}"`;if(p.tag==='text')svg.push(`<text ${id} x="${p.x}" y="${p.y}" font-family="Arial" font-size="${p.fontSize}" font-weight="${p.bold?'bold':'normal'}" text-anchor="${p.anchor}" fill="${p.fill}">${escape(p.text)}</text>`);else if(p.tag==='line')svg.push(`<line ${id} x1="${p.x1}" y1="${p.y1}" x2="${p.x2}" y2="${p.y2}" stroke="${p.stroke}" stroke-width="${p.width}"/>`);else if(p.tag==='circle')svg.push(`<circle ${id} cx="${p.x}" cy="${p.y}" r="${p.r}" fill="${p.fill}"/>`);else svg.push(`<rect ${id} x="${p.x-p.r}" y="${p.y-p.r}" width="${p.r*2}" height="${p.r*2}" fill="${p.fill}"/>`);}
 svg.push('</svg>');const svgPath=path.join(OUT,'native_svg',`t5_${task}.svg`);await create(svgPath,svg.join('\n')+'\n');
 const caption=`${label(task)}. Native selective-risk results for seeds 1, 2 and 3 shown separately, with Visual and Full distinct in each panel. Each series contains the ten saved native requested coverage levels 0.1, 0.2, ..., 1.0. Its horizontal coordinate is the saved realized coverage k/N multiplied by 100, where k=ceil(requested coverage×N); it is not the nominal request when ceiling changes the fraction. N=${N}. The vertical coordinate is saved selective risk=1−selected-query R@1, multiplied by 100. Queries are selected in descending raw cosine Top-1 minus Top-2 margin, using stable original query-order ties. Margin ranking is not a calibrated posterior probability or a fitted calibration model. Markers denote only the ten registered observations; straight connecting segments are visual guides and do not represent every selection prefix or justify interpolated performance claims. The displayed AURC values are saved upstream discrete all-prefix AURC fractions, rounded to four decimal places; they are not a trapezoidal integral of these ten plotted points and are not recomputed in this conversion. The original exact AURC and point values are in the per-task CSV and source JSON. No seed/task/direction/height pooling, SD/CI/error bars, bootstrap intervals, p-values or significance claims are displayed. The 132 paired comparisons, including their 75% requests and inferential fields, are preserved in the exact input JSON/CSV but are outside the plotted native66/660point scope. Calibration/ECE/reliability bins are also not plotted. Upstream query recomputation authority, saved-value limitations, inherited checkpoint/cache/image SHA and historical evidence-chain gaps remain unchanged; no query NPZ, model, full ranking or AP computation is repeated here.`;
 slide.speakerNotes.textFrame.setText(`${caption}\n\nRoot adoption SHA256: ${ROOT_SHA}\nExact original T5 JSON SHA256: ${T5_SHA}\nExact original comparison CSV SHA256: ${CSV_SHA}; preserved, not plotted.\n\nAll 60 native point rows for this task, directly flattened from the adopted JSON (fractions and counts unchanged):\n${pageCSVs.get(task)}`);
 figures.push({ordinal:ti+1,task,title:label(task),queries:N,widthMm:181.9,heightMm:HEIGHT_MM,widthPt:W,heightPt:H,minFontPt:8,nativeRows:6,nativePoints:60,panels,primitives,caption,svg:await describe(svgPath),sourceCSV:await describe(path.join(OUT,'source_data',`t5_${task}__native_points.csv`))});
}
const candidate=path.join(BUILD,'t5_selective_native_v2.candidate.pptx'),final=path.join(OUT,'t5_selective_native_editable_11figures_v2.pptx'),receipt=path.join(BUILD,'final_v2.validation.json');
await(await PresentationFile.exportPptx(pres)).save(candidate);
await finalizePresentation({workspaceDir:WORK,candidatePath:candidate,finalPath:final,explicitTotalSlideCount:11,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],pythonExecutable:PYTHON,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu',`${Math.round(181.9*36000)},${Math.round(HEIGHT_MM*36000)}`,'--cover-role','none',...Array.from({length:11},(_,i)=>['--approved-dense-slide',String(i+1)]).flat()],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:receipt});
const imported=await PresentationFile.importPptx(await FileBlob.load(final));
for(let i=0;i<11;i++){const fig=figures[i],png=path.join(OUT,'previews',`${String(i+1).padStart(2,'0')}_t5_${fig.task}.png`);await create(png,new Uint8Array(await(await imported.export({slide:imported.slides.items[i],format:'png',scale:2})).arrayBuffer()));fig.preview=await describe(png);console.log(JSON.stringify({page:i+1,task:fig.task,preview:png}));}
await create(path.join(WORK,'BUILD_REPORT_V2.json'),JSON.stringify({schema:'native-t5-build.v1',utc:new Date().toISOString(),source:await describe(fileURLToPath(import.meta.url)),inputProvenance:await describe(path.join(WORK,'INPUT_PROVENANCE_V2.json')),checks,figureCount:11,nativeRows:66,nativePoints:660,savedAllPrefixAURCValues:66,pairedComparisonsNotPlotted:132,pptx:await describe(final),receipt:await describe(receipt),figures,scientificExecution:false,PowerPointOpened:false,rendering:'All11 finalPPTX pages imported and CPU rendered using artifact-tool',limits:['Individual native shapes, not groups/Excel chart objects.','No model/cache/image/checkpoint/NPZ or original query-statistic recomputation.','Producer figure checking and independent review/root adoption are separate.']},null,2));
console.log(JSON.stringify({complete:true,checks,figures:11,nativePoints:660}));
