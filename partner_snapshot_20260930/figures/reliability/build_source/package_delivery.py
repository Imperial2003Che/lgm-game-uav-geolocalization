"""Package only new fixed-score diagnostic figures and adopted small source data."""
from pathlib import Path
import csv,datetime,hashlib,io,json,zipfile
W=Path(__file__).resolve().parent;O=W/'output'
def desc(p):
    p=Path(p);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def write(p,s):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
def save(p,j):write(p,json.dumps(j,ensure_ascii=False,indent=2)+'\n')
build=json.loads((W/'BUILD_REPORT.json').read_bytes());review=json.loads((W/'PRODUCER_PACKAGE_REVIEW.json').read_bytes())
assert review['passed'] and not review['independent'] and len(build['figures'])==11
readme='''# Fixed margin-score reliability diagnostic: editable figures

Final delivery is `t5_reliability_native_editable_11figures.pptx` and the 11 SVGs
under `native_svg/`. Every page is a research figure at 181.9 mm width and
213.07777777777778 mm height, with Arial at least 8 physical points. The PPTX
contains 2,824 individual native editable objects, including 2,189 text
objects. It embeds no SVG, raster image, Excel chart or workbook substitutes.
There are no grouped chart objects: select each stable named text, line or
marker directly. SVGs also retain native text, lines and outlined markers.
Reducing the physical width would reduce the final font below 8 pt.

## Data and interpretation

The 11 official tasks each have three separate seed panels. Across the 66
native task/seed/variant records, all 15 original bins are preserved: 990 bin
records, 140 occupied and 850 empty. Only the 140 occupied bins receive plotted
markers, at the exact stored mean fixed score (x) and empirical R@1 (y), both
fractions on axes from 0 to 1. The markers use their true coordinates without
jitter. Visual is an outlined blue circle and Full an outlined orange square;
overlap is possible and not displaced. No bins are connected by line segments.

The score is `clip((cosine_top1_minus_top2_margin)/2, 0, 1)`. It is a fixed
transformation, not a posterior probability or a trained/fitted calibration
model. The gray y=x line is only a numerical equality reference. It is not
labelled ideal/perfect calibration and does not establish calibration. The
source's field name `mean_fixed_normalized_margin_confidence` is preserved in
CSV, but is labelled fixed margin score on the figures to avoid a probability
claim.

Upstream assignment is `min(int(15*score),14)`: equal-width left-closed and
right-open bins, with the final bin including 1. Exact stored boundary floats
are archived; queries are not re-assigned from displayed boundaries here.
No assertion is made that clipping never occurred. Visual and Full assign
their queries according to their own scores: the same bin number does not
mean the same members, even with a shared full official query set. This is
different from the T4 shared Visual-margin strata.

Each panel includes the saved ECE fraction rounded to four decimals, without
multiplication by 100. ECE is not accuracy or an unweighted mean bin gap. The
saved ECE and each saved weighted_absolute_gap are preserved exactly, not
recomputed. A lower fixed-score ECE does not imply higher retrieval accuracy
and cannot alone establish improved probability calibration: both empirical
accuracy and margin score can change across variants. No better-calibrated
or better-method conclusion is drawn from these figures. Existing primary and
transfer negative results are unaffected.

Every page visibly lists all 15 Visual/Full bin populations, including zeros.
An empty bin has count=0 and mean/accuracy=null, with no plotted point. Zero
count never becomes zero accuracy, and gaps are not filled or interpolated.
Small occupied populations are shown without claiming precision or confidence
intervals. Seeds, datasets, tasks, heights and retrieval directions remain
separate; there is no pooling, SD, CI, bootstrap, p-value or significance claim.

## Exact inputs and inherited limits

The numerical source is the root-adopted T5 JSON SHA-256
`033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc`, 744943
bytes, pinned through root report
`f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a` and its
sealed CAPTURE binding. The complete source JSON is byte-identical to that
snapshot. `RELIABILITY_BINS_990.csv` and each task's 90-row CSV directly flatten
the saved fields, with literal `null` for empty mean/accuracy. Speaker notes
contain the full caption, input SHA and exact 90-row source table for each page.
Original selective-risk curves, AURC and paired-comparison fields remain in the
exact JSON but are outside this plotting scope.

These are official clean-query diagnostics, not corrupted-image comparisons.
Upstream independent bin/query validation is inherited and not rerun. No NPZ,
weights, cache or image bytes are read. No model, full-ranking, all-positive-rank
AP, score, bin assignment, accuracy, weighted gap or ECE is recomputed. The
stored-value scope, inherited checkpoint/cache/image SHA authority and historical
metadata-chain gaps remain. No native-environment, GPU, recovery, lock, release,
scientific state, HANDOFF, automation or original scientific file is modified.
T6 and later experiment completion are not implied.

## Build and review history

V1 first produced two samples successfully. After that run, a requested
interpretation clarification was added before the first full build: v2 adds
the visible lower-ECE warning and the complete caption limitation, increases
page height from 585 to 604 pt, and refuses sample mode to protect the preserved
v1 sample. All source data and point coordinates are unchanged. The v1 source,
sample PPTX/SVG/PNG/report and complete v1-to-v2 diff remain at their original
paths. This was a preparation revision, not a failed scientific result.

V2's first full 11-page build exited 0. Every page was imported from the final
PPTX and CPU-rendered using artifact-tool, then actually viewed individually
with view_image(original). No clipping or text overlap was seen, including
small-score points, y=0/y=1 occupied markers, sparse N80 series and all empty
population rows. No PowerPoint application or scientific package was launched.

The first bounded author package check passed 33,862 assertions: new source
copies, nulls/populations/ECE transcription, actual XML/native objects, physical
fonts and dimensions, exact notes and point positions, and v1/v2 unchanged data.
It is a producer export check, not independent scientific acceptance. Independent
display/geometry/visual/semantic reviews and root adoption are separately bound
in DELIVERY and the root's later adoption. The ZIP contains PPTX, native SVGs,
exact small JSON, flattened CSVs, captions/index/provenance and producer sources;
PNG previews remain beside the archive and are not duplicated in the ZIP.
'''
write(O/'README.md',readme)
write(O/'CAPTIONS.md','# Fixed margin-score reliability diagnostic captions\n\n'+'\n\n'.join(f"## Figure {f['ordinal']}: {f['title']}\n\n{f['caption']}" for f in build['figures'])+'\n')
ix=io.StringIO(newline='');wr=csv.DictWriter(ix,fieldnames=['page','task','title','svg','source_csv','preview','panels','bin_records','occupied_bins','empty_bins']);wr.writeheader()
for f in build['figures']:wr.writerow({'page':f['ordinal'],'task':f['task'],'title':f['title'],'svg':Path(f['svg']['path']).relative_to(O).as_posix(),'source_csv':Path(f['sourceCSV']['path']).relative_to(O).as_posix(),'preview':Path(f['preview']['path']).relative_to(O).as_posix(),'panels':3,'bin_records':90,'occupied_bins':f['occupiedBins'],'empty_bins':f['emptyBins']})
write(O/'FIGURE_INDEX.csv',ix.getvalue())
save(W/'PRODUCER_VISUAL_REVIEW.json',{'schema':'producer-reliability-actual-visual-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'independent':False,'method':'Actual view_image(original) of all11 final PNGs in batches1-3,4-7,8-11; earlier2 v1 samples separately.','finalPages':[{'page':f['ordinal'],'preview':f['preview'],'observed':'No visible text clipping/overlap; exact point locations, boundary y=0/y=1 markers, outline differences, ECE values and all15 population rows legible.'} for f in build['figures']],'limitation':'Visual readability is not new scientific or inference validation.'})
sources=[W/'build/build_reliability.mjs',W/'build/build_reliability_v2.mjs',W/'prepare_revision.py',W/'verify_package.py',Path(__file__),W/'seal_final.py']
save(W/'SOURCE_MANIFEST.json',{'schema':'native-reliability-source-manifest.v1','files':[desc(p) for p in sources],'revision':desc(W/'SOURCE_REVISION.json'),'fullDiff':desc(W/'V1_SAMPLE_TO_FINAL_V2.patch'),'rootOwnedFilesExcluded':True})
code=O/'build_source';code.mkdir()
for p in sources:
    with (code/p.name).open('xb') as f:f.write(p.read_bytes())
for p in [W/'INPUT_PROVENANCE.json',W/'PRODUCER_PACKAGE_REVIEW.json',W/'PRODUCER_VISUAL_REVIEW.json',W/'SOURCE_REVISION.json',W/'SOURCE_MANIFEST.json',W/'V1_SAMPLE_TO_FINAL_V2.patch']:
    with (O/'provenance'/p.name).open('xb') as f:f.write(p.read_bytes())
files=sorted(p for p in O.rglob('*') if p.is_file() and p.suffix not in ['.png','.zip'])
zip_path=O/'t5_reliability_native_editable_and_sources.zip';members=[]
with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files:
        member=p.relative_to(O).as_posix();z.write(p,member);members.append({'member':member,**desc(p)})
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None and z.namelist()==[r['member'] for r in members]
    for d in members:
        b=z.read(d['member']);assert len(b)==d['bytes'] and hashlib.sha256(b).hexdigest()==d['sha256']
save(W/'ZIP_CONTENTS.json',{'schema':'native-reliability-zip-contents.v1','zip':desc(zip_path),'members':members,'readBackByteSHAValidated':True,'PNGPreviewsOmitted':True})
print(json.dumps({'zip':desc(zip_path),'members':len(members),'docs':desc(O/'README.md'),'sourceManifest':desc(W/'SOURCE_MANIFEST.json')}))
