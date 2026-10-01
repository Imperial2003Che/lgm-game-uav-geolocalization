"""Preserve executed v1 sample; prepare final-only v2 for requested interpretation note."""
from pathlib import Path
import difflib,hashlib,json
W=Path(__file__).resolve().parent
p=W/'build/build_reliability.mjs';before=p.read_text(encoding='utf-8')
replacements=[
    ("H=585,S=4/3","H=604,S=4/3"),
    ("const EX=path.join(path.dirname(WORK),'execution')", "if(SAMPLE)throw new Error('v2 is final-only; preserved v1 sample must not be overwritten');\nconst EX=path.join(path.dirname(WORK),'execution')"),
    ("  'Stored ECE fractions rounded to four decimals. No seed/task pooling, SD, CI or p-values.'", "  'Stored ECE fractions rounded to four decimals. No seed/task pooling, SD, CI or p-values.',\n  'Lower fixed-score ECE does not imply higher retrieval accuracy or better calibration.'"),
    ("Stored ECE is a fraction displayed to four decimals, not multiplied by100 or interpreted as accuracy.","Stored ECE is a fraction displayed to four decimals, not multiplied by100 or interpreted as accuracy. A lower fixed-score ECE does not imply higher retrieval accuracy and cannot alone establish improved probability calibration: both empirical accuracy and the margin-score side can change with the variant. No better-calibrated-method conclusion is drawn.")
]
after=before
for old,new in replacements:
    assert after.count(old)==1,old
    after=after.replace(old,new)
dest=W/'build/build_reliability_v2.mjs'
with dest.open('x',encoding='utf-8',newline='\n') as f:f.write(after)
diff=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='build_reliability.mjs',tofile='build_reliability_v2.mjs'))
with (W/'V1_SAMPLE_TO_FINAL_V2.patch').open('x',encoding='utf-8',newline='\n') as f:f.write(diff)
def desc(p):
    b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
record={'schema':'native-t5-reliability-preexecution-revision.v1','before':desc(p),'after':desc(dest),'diff':desc(W/'V1_SAMPLE_TO_FINAL_V2.patch'),'executedSample':desc(W/'BUILD_REPORT_SAMPLE.json'),'v1SampleExitCode':0,'v1SourceAndAllSampleOutputsRetained':True,'reason':'Root/independent clarification received after successful sample: smaller fixed-score ECE is not evidence of higher accuracy or improved probability calibration. Add visible footer and caption, extend page height19pt. No data/plot coordinate/ECE/count edits.','v2BeforeFirstFinalExecution':True,'rejectedScientificResult':False}
with (W/'SOURCE_REVISION.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(record))
