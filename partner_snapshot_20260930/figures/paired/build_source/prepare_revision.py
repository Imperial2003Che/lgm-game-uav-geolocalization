"""Preserve first samples; add saved visible success values before the first full build."""
from pathlib import Path
import difflib,hashlib,json
W=Path(__file__).resolve().parent;p=W/'build/build_paired.mjs';before=p.read_text(encoding='utf-8')
insert='''  text(`${id}/success/heading`,x+pw/2,381,'Success% at requested coverage',8,true,'middle');
  for(const [i,r] of srows.entries()){const xx=x+(i+.5)*pw/4;text(`${id}/success/cov-${r.requested_coverage}/heading`,xx,395,String(r.requested_coverage*100),8,false,'middle');for(const variant of ['visual','full'])text(`${id}/${variant}/success-cov-${r.requested_coverage}`,xx,variant==='visual'?408:421,r[`${variant}_success_percent`].toFixed(3),8,false,'middle',COLORS[variant]);}
  text(`${id}/visual/success-prefix`,x-8,408,'V',8,true,'end',COLORS.visual);text(`${id}/full/success-prefix`,x-8,421,'F',8,true,'end',COLORS.full);
'''
replacements=[("H=467,S=4/3","H=534,S=4/3"),("const AUDIT=path.join", "if(SAMPLE)throw new Error('v2 is final-only; preserve original v1 samples');\nconst AUDIT=path.join"),("  panels.push({seed,queries:N",insert+"  panels.push({seed,queries:N"),("15,384+i*13","15,448+i*13"),("The four-row table reports requested coverage, exact k/N per variant and the saved count of shared selected members (overlap),", "The visible success-value block additionally reports all eight saved success percentages per seed to three decimals, preserving readability for very low values on the common0–100 axes; exact source precision remains in CSV and notes. The four-row table reports requested coverage, exact k/N per variant and the saved count of shared selected members (overlap),")]
after=before
for old,new in replacements:
    assert after.count(old)==1,old
    after=after.replace(old,new)
dest=W/'build/build_paired_v2.mjs'
with dest.open('x',encoding='utf-8',newline='\n') as f:f.write(after)
diff=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='build_paired.mjs',tofile='build_paired_v2.mjs'))
with (W/'V1_SAMPLE_TO_FINAL_V2.patch').open('x',encoding='utf-8',newline='\n') as f:f.write(diff)
def desc(p):
    b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
j={'schema':'native-t5-paired-preexecution-revision.v1','before':desc(p),'after':desc(dest),'diff':desc(W/'V1_SAMPLE_TO_FINAL_V2.patch'),'executedSample':desc(W/'BUILD_REPORT_SAMPLE.json'),'v1SampleExitCode':0,'v1SourceAndSampleOutputsRetained':True,'reason':'Independent reviewer requested visible V/F success values for low street results. Add saved three-decimal percentages and coverage headings below count tables, page467→534pt, footer384→448pt. No new statistics, saved values or point-coordinate changes.','beforeFirstFinalExecution':True,'scientificFailure':False}
with (W/'SOURCE_REVISION.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(j))
