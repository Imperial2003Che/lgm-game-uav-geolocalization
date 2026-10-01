import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
import {createCanvas,GlobalFonts} from '@napi-rs/canvas';

const BUILD=path.dirname(fileURLToPath(import.meta.url)),WORK=path.dirname(BUILD),OUT=path.join(WORK,'output');
const SRC=path.join(path.dirname(WORK),'execution/transfer_results_20260929');
const RESULTS=path.join(SRC,'result_20260929_061052_519928');
const SKILL='C:/Users/17703/.codex/plugins/cache/openai-primary-runtime/presentations/26.927.11222/skills/presentations';
const PYTHON='C:/Users/17703/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const ROOT_SHA='a8867a9ebdf01061a55d143b79eff91196571c2275f4379902131a69dd4ce80c';
const W=181.9*72/25.4,S=4/3,COLORS={visual:'#0072B2',full:'#D55E00'};
const METRICS=['r_at_1','official_trapezoid_mAP','MRR'];
const inputs=[];let assertions=0;
function check(v,m){assertions++;if(!v)throw new Error(m);}
const hash=b=>createHash('sha256').update(b).digest('hex');
const norm=p=>path.normalize(p).toLowerCase();
async function describe(p){const b=await fs.readFile(p);return {path:p,sha256:hash(b),bytes:b.length};}
async function writeNew(p,b){await fs.writeFile(p,b,{flag:'wx'});}
async function bind(p,expected){const b=await fs.readFile(p);check(hash(b)===expected.sha256 && (expected.bytes===undefined||expected.bytes===b.length),`SHA/size ${p}`);const descriptor={path:p,sha256:hash(b),bytes:b.length};inputs.push(descriptor);return b;}
const rootPath=path.join(SRC,'ROOT_AGGREGATION_ADOPTION.json'),rootBytes=await bind(rootPath,{sha256:ROOT_SHA}),root=JSON.parse(rootBytes);
check(root.status==='root_adopted_descriptive_transfer_statistics','Accepted root status');
const rootMap=new Map(root.bindings.map(x=>[norm(x.path),x]));
const raw={};
for(const name of ['README.md','DELIVERY.json','THREE_SEED_SUMMARY.csv','THREE_SEED_SUMMARY.json','SEED_RESULTS.csv','SEED_RESULTS.json','FULL_MINUS_VISUAL.csv','FULL_MINUS_VISUAL.json','ANALYSIS.md']){
 const p=path.join(name==='README.md'?SRC:RESULTS,name);check(rootMap.has(norm(p)),`Root exact binding ${name}`);
 const bytes=await bind(p,rootMap.get(norm(p)));raw[name]=bytes;
 const destination=path.join(OUT,name.endsWith('.csv')||name.endsWith('.json')&&!['DELIVERY.json'].includes(name)?'source_data':'provenance',name==='README.md'?'SOURCE_README.md':name);
 await writeNew(destination,bytes);
}
await writeNew(path.join(OUT,'provenance/ROOT_AGGREGATION_ADOPTION.json'),rootBytes);
const delivery=JSON.parse(raw['DELIVERY.json']);
for(const name of ['THREE_SEED_SUMMARY.csv','THREE_SEED_SUMMARY.json','SEED_RESULTS.csv','SEED_RESULTS.json','FULL_MINUS_VISUAL.csv','FULL_MINUS_VISUAL.json']){
 const a=delivery.artifacts.find(x=>norm(x.path)===norm(path.join(RESULTS,name)));check(a&&a.sha256===hash(raw[name])&&a.bytes===raw[name].length,`Delivery adopted artifact ${name}`);
}
function csv(text){const rows=[];let row=[],field='',q=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(q&&text[i+1]==='"'){field+='"';i++;}else q=!q;}else if(!q&&(c===','||c==='\n')){row.push(field.replace(/\r$/,''));field='';if(c==='\n'){if(row.length>1)rows.push(row);row=[];}}else field+=c;}if(field||row.length){row.push(field.replace(/\r$/,''));rows.push(row);}check(!q,'CSV quote balance');const headers=rows.shift();check(new Set(headers).size===headers.length,'Unique CSV headers');return rows.map(r=>{check(r.length===headers.length,'CSV column count');return Object.fromEntries(headers.map((h,i)=>[h,r[i]]));});}
const summaries=JSON.parse(raw['THREE_SEED_SUMMARY.json']),seeds=JSON.parse(raw['SEED_RESULTS.json']);
const summaryCSV=csv(raw['THREE_SEED_SUMMARY.csv'].toString('utf8')),seedCSV=csv(raw['SEED_RESULTS.csv'].toString('utf8'));
const rowKey=r=>[r.source_dataset,r.target_dataset,r.task,r.variant].join('/');
function compareTables(j,c,seed){check(j.length===c.length,'CSV/JSON row count');for(let i=0;i<j.length;i++){for(const [k,v] of Object.entries(j[i]))check(typeof v==='number'?Number(c[i][k])===v:c[i][k]===v,`Exact CSV/JSON field ${i}/${k}`);}const keys=j.map(r=>rowKey(r)+(seed?'/'+r.seed:''));check(new Set(keys).size===keys.length,'Unique table keys');}
compareTables(summaries,summaryCSV,false);compareTables(seeds,seedCSV,true);
check(summaries.length===22&&seeds.length===66,'22 groups, 66 seed-task rows');
for(const r of summaries){check(r.n_seeds===3&&r.unit==='fraction','Three equal-weight seeds and fraction unit');const members=seeds.filter(s=>rowKey(s)===rowKey(r));check(members.length===3&&members.map(x=>x.seed).sort().join(',')==='1,2,3','Exact seeds 1/2/3');for(const metric of METRICS){check(Number.isFinite(r[metric+'_mean'])&&r[metric+'_mean']>=0&&r[metric+'_mean']<=1,'Mean fraction');check(Number.isFinite(r[metric+'_sample_sd'])&&r[metric+'_sample_sd']>=0,'Sample SD nonnegative');}}
const directions=[
 {id:'university_to_sues',source:'university1652',target:'sues200',title:'Trained on University-1652 → evaluated on SUES-200',tasks:[150,200,250,300].flatMap(h=>[`sues200_uav_${h}m_to_satellite`,`sues200_satellite_to_uav_${h}m`])},
 {id:'sues_to_university',source:'sues200',target:'university1652',title:'Trained on SUES-200 → evaluated on University-1652',tasks:['university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite']},
];
for(const d of directions){d.rows=summaries.filter(r=>r.source_dataset===d.source&&r.target_dataset===d.target);check(d.rows.length===d.tasks.length*2,'Exact groups per training/evaluation direction');for(const task of d.tasks)for(const variant of ['visual','full'])check(d.rows.filter(r=>r.task===task&&r.variant===variant).length===1,'Complete task/variant key');}
check(directions.flatMap(x=>x.rows).length===22,'All accepted groups plotted');
await writeNew(path.join(WORK,'INPUT_PROVENANCE.json'),JSON.stringify({schema:'native-transfer-inputs.v1',root_sha256:ROOT_SHA,inputs,copies:await Promise.all((await fs.readdir(path.join(OUT,'source_data'))).map(n=>describe(path.join(OUT,'source_data',n)))),scope:'Only adopted small aggregate tables; no original metrics/checkpoint/cache/image/NPZ read.'},null,2));
check(GlobalFonts.families.some(f=>f.family==='Arial'),'Arial available');
const ctx=createCanvas(1,1).getContext('2d');
const escape=v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function label(task){if(task.startsWith('university1652_'))return [[{'drone_to_satellite':'Drone → satellite','satellite_to_drone':'Satellite → drone','street_to_satellite':'Street → satellite'}[task.replace('university1652_','')]]];let m=task.match(/^sues200_uav_(\d+)m_to_satellite$/);if(m)return [['UAV → satellite'],[`${m[1]} m`]];m=task.match(/^sues200_satellite_to_uav_(\d+)m$/);check(m,'SUES direction parsing');return [['Satellite → UAV'],[`${m[1]} m`]];}
const reports=[];
for(let ordinal=1;ordinal<=directions.length;ordinal++){
 const d=directions[ordinal-1],H=185+46*d.tasks.length,heightMm=H*25.4/72;
 const pres=Presentation.create({slideSize:{width:W*S,height:H*S}}),slide=pres.slides.add();slide.background.fill='#FFFFFF';
 const primitives=[],cells=[],axes=[];
 const add=(tag,id,values)=>primitives.push({tag,id,...values});
 const text=(id,x,y,content,size=8,bold=false,anchor='start',fill='#222222')=>add('text',id,{x,y,text:content,fontSize:size,bold,anchor,fill});
 const line=(id,x1,y1,x2,y2,stroke='#444444',width=.55)=>add('line',id,{x1,y1,x2,y2,stroke,width});
 const marker=(id,x,y,variant)=>add(variant==='visual'?'circle':'rect',id,{x,y,r:1.8,fill:COLORS[variant]});
 text('training-evaluation-direction',15,18,d.title,10,true);
 text('study-title',15,34,'Zero-shot cross-dataset retrieval',9,true);
 marker('legend/visual/marker',18,48,'visual');text('legend/visual/text',25,51,'Visual',8);
 marker('legend/full/marker',86,48,'full');text('legend/full/text',93,51,'Full',8);
 text('statistical-summary',153,51,'Mean ± sample SD; seeds 1, 2, 3',8);
 text('task-header',15,79,'Target retrieval',8,true);text('task-header-second',15,90,'task / height',8,true);
 const axisY=104,firstY=116,rowH=46;
 for(let mi=0;mi<3;mi++){
  const metric=METRICS[mi],x=118+mi*130,pw=116;
  const high=Math.max(...d.rows.map(r=>100*(r[metric+'_mean']+r[metric+'_sample_sd']))),axisMax=Math.ceil(high/10)*10;
  check(axisMax>0,'Positive axis maximum');
  text(`${metric}/heading`,x+pw/2,79,['R@1 (%)','Official mAP (%)','MRR × 100'][mi],9,true,'middle');
  if(mi===1)text(`${metric}/semantics`,x+pw/2,90,'Trapezoidal AP',8,false,'middle');
  const bottom=firstY+d.tasks.length*rowH-3;
  for(let v=0;v<=axisMax;v+=10){const tx=x+v/axisMax*pw;line(`${metric}/grid/${v}`,tx,axisY,tx,bottom,'#E4E8ED',.4);line(`${metric}/tick/${v}`,tx,axisY-2,tx,axisY,'#444444',.6);text(`${metric}/tick-label/${v}`,tx,101,String(v),8,false,'middle');}
  line(`${metric}/axis`,x,axisY,x+pw,axisY,'#444444',.6);
  axes.push({metric,x,y:axisY,width:pw,min:0,max:axisMax,tickStep:10});
  for(let ti=0;ti<d.tasks.length;ti++)for(let vi=0;vi<2;vi++){
   const task=d.tasks[ti],variant=['visual','full'][vi],r=d.rows.find(r=>r.task===task&&r.variant===variant),mean=r[metric+'_mean']*100,sd=r[metric+'_sample_sd']*100;
   check(mean-sd>=0&&mean+sd<=axisMax,'Actual SD interval fully fits zero-based axis; no clipping');
   const y=firstY+ti*rowH+vi*20,px=x+mean/axisMax*pw,l=x+(mean-sd)/axisMax*pw,h=x+(mean+sd)/axisMax*pw,id=`${task}/${variant}/${metric}`;
   line(`${id}/sd-line`,l,y,h,y,COLORS[variant],.9);line(`${id}/sd-cap-left`,l,y-2.1,l,y+2.1,COLORS[variant],.8);line(`${id}/sd-cap-right`,h,y-2.1,h,y+2.1,COLORS[variant],.8);marker(`${id}/mean`,px,y,variant);
   const valueText=`${mean.toFixed(3)} ± ${sd.toFixed(3)}`;
   text(`${id}/value`,x+pw/2,y+11,valueText,8,false,'middle',COLORS[variant]);
   cells.push({task,variant,metric,sourceDataset:d.source,targetDataset:d.target,meanFraction:r[metric+'_mean'],sampleSdFraction:r[metric+'_sample_sd'],meanDisplayed:mean,sdDisplayed:sd,n:3,sdDenominator:2,valueText,point:{x:px,y},interval:{left:l,right:h,y},axis:axes.at(-1),seedValues:seeds.filter(s=>rowKey(s)===rowKey(r)).sort((a,b)=>a.seed-b.seed).map(s=>({seed:s.seed,value:s[metric]}))});
  }
 }
 for(let ti=0;ti<d.tasks.length;ti++){
  const y=firstY+ti*rowH,parts=label(d.tasks[ti]);parts.forEach((part,j)=>text(`${d.tasks[ti]}/label/${j}`,15,y+9+j*12,part[0],8));
  if(ti<d.tasks.length-1)line(`${d.tasks[ti]}/separator`,15,y+38,W-15,y+38,'#CAD2DA',.5);
 }
 const foot=firstY+d.tasks.length*rowH+14;
 text('footnote/sd',15,foot,'Bars are sample SD (n − 1 = 2), not confidence intervals or significance tests.',8);
 text('footnote/tasks',15,foot+13,'Each retrieval task is separate; no pooling across heights, directions or datasets.',8);
 text('footnote/units',15,foot+26,'R@1 and mAP are percentages; MRR × 100 is scaled MRR, not an accuracy percentage.',8);
 text('footnote/numerics',15,foot+39,'Labels show mean ± sample SD; exact fractions and all seed values are in the source tables.',8);
 for(const p of primitives){const name=`${d.id}/${p.id}`;
  if(p.tag==='text'){
   ctx.font=`${p.bold?'bold':'normal'} ${p.fontSize*S}px Arial`;const tw=ctx.measureText(p.text).width+1,left=p.x*S-(p.anchor==='middle'?tw/2:p.anchor==='end'?tw:0);
   check(left>=0&&left+tw<=W*S,'Text horizontal bounds');check(p.y-p.fontSize>=0&&p.y+3<=H,'Text vertical bounds');
   const sh=slide.shapes.add({geometry:'textbox',name,position:{left,top:(p.y-p.fontSize*.92)*S,width:tw,height:p.fontSize*S*1.25},fill:'none',line:{fill:'none',width:0}});sh.text=p.text;sh.text.style={typeface:'Arial',fontSize:p.fontSize*S,bold:p.bold,color:p.fill,alignment:p.anchor==='middle'?'center':'left',verticalAlignment:'top',autoFit:'none',wrap:'none',insets:{top:0,bottom:0,left:0,right:0}};
  }else if(p.tag==='line')slide.shapes.add({geometry:'line',name,position:{left:Math.min(p.x1,p.x2)*S,top:Math.min(p.y1,p.y2)*S,width:Math.abs(p.x2-p.x1)*S,height:Math.abs(p.y2-p.y1)*S,verticalFlip:(p.x2-p.x1)*(p.y2-p.y1)<0},fill:'none',line:{fill:p.stroke,width:p.width*S}});
  else slide.shapes.add({geometry:p.tag==='circle'?'ellipse':'rect',name,position:{left:(p.x-p.r)*S,top:(p.y-p.r)*S,width:p.r*2*S,height:p.r*2*S},fill:p.fill,line:{fill:'none',width:0}});
 }
 const svg=[`<svg xmlns="http://www.w3.org/2000/svg" width="181.9mm" height="${heightMm}mm" viewBox="0 0 ${W} ${H}">`,`<title>${escape(d.title)}</title>`,`<desc>Three-seed mean and sample SD. SD uses denominator 2, not confidence intervals. Native editable text and shapes. R@1 and official trapezoidal mAP percentages; MRR multiplied by 100. Tasks remain separate.</desc>`,`<rect id="background" x="0" y="0" width="${W}" height="${H}" fill="white"/>`];
 for(const p of primitives){const id=`id="${escape(p.id)}"`;if(p.tag==='text')svg.push(`<text ${id} x="${p.x}" y="${p.y}" font-family="Arial" font-size="${p.fontSize}" font-weight="${p.bold?'bold':'normal'}" text-anchor="${p.anchor}" fill="${p.fill}">${escape(p.text)}</text>`);else if(p.tag==='line')svg.push(`<line ${id} x1="${p.x1}" y1="${p.y1}" x2="${p.x2}" y2="${p.y2}" stroke="${p.stroke}" stroke-width="${p.width}"/>`);else if(p.tag==='circle')svg.push(`<circle ${id} cx="${p.x}" cy="${p.y}" r="${p.r}" fill="${p.fill}"/>`);else svg.push(`<rect ${id} x="${p.x-p.r}" y="${p.y-p.r}" width="${p.r*2}" height="${p.r*2}" fill="${p.fill}"/>`);}
 svg.push('</svg>');const svgPath=path.join(OUT,'native_svg',`transfer_${d.id}.svg`);await writeNew(svgPath,svg.join('\n')+'\n');
 const caption=`${d.title}. Zero-shot retrieval for each target task. All three metrics are shown for Visual and Full using equally weighted seeds 1, 2 and 3; points and labels denote mean and bars denote sample SD with denominator n−1=2. SD is neither a confidence interval nor a significance test. The source fraction mean and SD are both multiplied by 100: R@1 and official trapezoidal mAP are percentages, while MRR ×100 is a scaled MRR value, not a percentage accuracy. Official mAP uses the frozen official trapezoidal AP semantics. All axes start at zero; each metric axis is separately scaled and the complete mean±SD interval is retained. Numeric labels use three decimal places; full-precision fractions and all individual seeds are preserved in source CSV/JSON and notes. Training/evaluation dataset direction in the title is distinct from the retrieval directions and heights within the target dataset. No pooling across tasks, heights, directions, datasets or query counts is performed. These are descriptive results and do not establish statistical significance or general superiority. The adopted results show Full mean R@1 below Visual in all 11 tasks; mAP/MRR are also below Visual except the small positive SUES→University street→satellite differences. No checkpoint bytes, caches, images, NPZs, model or full-ranking/AP computation is repeated here. All inherited checkpoint/cache/image SHA and historical evidence-chain limitations remain in force.`;
 slide.speakerNotes.textFrame.setText(`${caption}\n\nRoot adoption SHA256: ${ROOT_SHA}\n\nExact adopted THREE_SEED_SUMMARY.csv:\n${raw['THREE_SEED_SUMMARY.csv'].toString('utf8')}\nExact adopted SEED_RESULTS.csv:\n${raw['SEED_RESULTS.csv'].toString('utf8')}`);
 const candidate=path.join(BUILD,`transfer_${d.id}.candidate.pptx`),final=path.join(OUT,`transfer_${d.id}_native_editable.pptx`),receipt=path.join(BUILD,`transfer_${d.id}.validation.json`);
 await(await PresentationFile.exportPptx(pres)).save(candidate);
 await finalizePresentation({workspaceDir:WORK,candidatePath:candidate,finalPath:final,explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],pythonExecutable:PYTHON,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu',`${Math.round(181.9*36000)},${Math.round(heightMm*36000)}`,'--cover-role','none','--approved-dense-slide','1'],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:receipt});
 const imported=await PresentationFile.importPptx(await FileBlob.load(final)),png=path.join(OUT,'previews',`transfer_${d.id}.png`);await writeNew(png,new Uint8Array(await(await imported.export({slide:imported.slides.items[0],format:'png',scale:2})).arrayBuffer()));
 reports.push({ordinal,id:d.id,sourceDataset:d.source,targetDataset:d.target,title:d.title,tasks:d.tasks,summaryGroups:d.rows.length,metricSummaries:cells.length,widthMm:181.9,heightMm,widthPt:W,heightPt:H,minFontPt:8,axes,cells,primitives,caption,svg:await describe(svgPath),pptx:await describe(final),preview:await describe(png),receipt:await describe(receipt)});
 console.log(JSON.stringify({figure:d.id,preview:png,pptx:final,groups:d.rows.length,metricSummaries:cells.length}));
}
await writeNew(path.join(WORK,'BUILD_REPORT.json'),JSON.stringify({schema:'native-transfer-build.v1',utc:new Date().toISOString(),source:await describe(fileURLToPath(import.meta.url)),inputProvenance:await describe(path.join(WORK,'INPUT_PROVENANCE.json')),assertions,figureCount:2,summaryGroups:22,metricSummaries:66,seedTaskRows:66,figures:reports,scientificExecution:false,PowerPointOpened:false,rendering:'Artifact-tool CPU, actual import of each finalized one-page PPTX',limits:['Flat native shapes, not grouped or Excel chart objects.','Only adopted small summary tables were read. No raw metrics/checkpoint/NPZ/cache/image scientific inputs.','Producer and independent reviews remain separate; root artifact adoption is pending.']},null,2));
console.log(JSON.stringify({completed:true,assertions,figures:2,metricSummaries:66}));
