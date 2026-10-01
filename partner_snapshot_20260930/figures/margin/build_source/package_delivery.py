"""Package only newly produced editable T4 figures and small adopted source tables."""
from pathlib import Path
import csv,datetime,hashlib,io,json,shutil,zipfile
W=Path(__file__).resolve().parent;O=W/'output'
def desc(p):
    p=Path(p);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def write(p,s):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
def save(p,j):write(p,json.dumps(j,ensure_ascii=False,indent=2)+'\n')
build=json.loads((W/'BUILD_REPORT.json').read_bytes());sample=json.loads((W/'BUILD_REPORT_SAMPLE.json').read_bytes());review=json.loads((W/'PRODUCER_PACKAGE_REVIEW.json').read_bytes())
assert review['passed'] and not review['independent'] and build['source']==sample['source']
assert len(build['figures'])==11 and build['numericPoints']==792
readme='''# Editable T4 shared Visual-margin quartile figures

The delivery is `t4_margin_native_editable_11figures.pptx`, 11 native SVGs and
their exact source tables. Each page is a research figure, not a presentation
title slide. Width is 181.9 mm, height 214.13611111111112 mm; Arial text is at
least 8 physical points in SVG and exported OOXML. The PPTX contains 4,851
individual native editable shapes, including 2,354 text objects. There are no
embedded image substitutes, Excel chart objects or shape groups. Select a
named text/line/marker directly to edit it. The accompanying SVG retains text,
lines and markers as native vector elements. Keep the physical size when using
the figure in a paper; reducing its width also reduces the text below 8 pt.

## What is shown

Only `visual_margin_quartile`: 132 adopted strata, 11 official tasks × three
seeds × four quartiles. Each of the 11 pages has three metric rows and three
seed columns, for 99 panels and 792 saved performance values. R@1 and official
trapezoidal mAP fractions are multiplied by 100 and labelled %. MRR is also
multiplied by 100 but explicitly labelled scaled MRR, not accuracy percent.
All panels use the same zero-to-100 scale. The 792 numerical values are also
printed below their panels to three decimals, so very low University street
values remain readable. Exact, unrounded fractions are in source tables and
notes. Seeds, tasks, directions and heights remain separate.

Q1–Q4 are ordered categories from low to high Visual margin. They are not an
equally spaced numerical margin axis. The frozen upstream method uses linear
25/50/75-percentile cutpoints for each task and seed, with values equal to a
cutpoint assigned to the lower interval. Full queries were aligned to Visual
before the same Visual-defined mask was applied to both variants. The plotted
Visual and Full values therefore use identical members within each stratum.
This differs from T5, where each variant selects its own margin-ranked subset.
Connecting segments are only categorical visual guides. N is copied exactly
from the saved stratum; equal-sized rank bins are not assumed.

There are 84 `performance_claim_eligible=true` and 48 `false` strata. All 48
false strata are the four SUES satellite-to-UAV tasks, across all three seeds,
with N=20 per quartile. Every false group is marked 20†, with a visible
`N < 100: performance_claim_eligible=false; descriptive only` explanation. The
registered threshold is 100, not 30. Eligibility is a count gate only and does
not establish significance. The strata are defined using Visual itself, so
this is a Visual-anchored conditional comparison; it is not evidence of a
causal mechanism or independent calibration. Margin is not a calibrated
posterior probability.

## Source and scope limits

The numerical source is the completed T4 JSON SHA-256
`42090c4ffdafedbfffd8ed2439e1e59756f0876e2c7ae612a87031a574b28cc8` and CSV
`bc1725e7d5a1ce298f2de579240d65ced823b57d0d2af8bcb077a9d697d66530`, bound
to sealed snapshots in CAPTURE and the root adoption SHA-256
`f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a`.
The complete 462-row original JSON/CSV are preserved byte-for-byte. The other
330 entropy/semantic strata and all inferential fields in those originals are
archived but are not plotted or newly accepted by this figure package.

`MARGIN_STRATA_132.csv` and 11 per-task CSVs flatten saved fields and multiply
fractions by 100; they do not calculate new means, quantiles, memberships or
statistics. Speaker notes include each page's 12 complete flattened strata,
cutpoints, membership SHA, N/eligibility and exact original fraction values.
No pooling, SD, confidence intervals, bootstrap intervals, p-values or
significance claims are drawn. Upstream bootstrap intervals were not
independently resampled, so they are deliberately omitted.

The original root-adopted query audit independently recounted these 132 margin
strata; that work is inherited here, not repeated. Stored AP/RR/margin values,
inherited checkpoint/cache/image SHA authority, historical metadata-chain gaps,
and the absence of model/full-ranking/all-positive-rank AP recomputation remain
unchanged. No old NPZ, weights, cache or image bytes are read by this build or
new author checks. These are official clean-query results, not corrupted-run
comparisons. This figure task adds no scientific run, inference, T6 completion
or resource/recovery permission.

## Build and review

The same unmodified builder first created two sample pages (University street
and SUES satellite-to-UAV 150 m), then created all 11 final pages. Both builds
exited 0. Samples remain under `sample/`; final delivery is only `output/`.
There was no rejected candidate or source revision in this task. All 11 final
pages were imported from the exported PPTX and rendered by artifact-tool on
CPU. The author actually inspected each final PNG with view_image(original),
including low values, nonmonotonic curves, N20† groups and text separation.
No PowerPoint application, scientific package or GPU was launched.

The bounded author package check passed 46,736 assertions over the new source
table copies, point values, notes, physical dimensions, SVG and OOXML objects,
font sizes and rendering descriptors. This is a producer check, not an
independent review. `DELIVERY.json` separately binds the independent review
when it is complete; root adoption is a separate decision. ZIP members include
PPTX, SVGs, exact small sources, derived tables, notes/captions/index/provenance
and editable builder/check source. PNG previews stay beside the package and
are omitted from the ZIP to avoid duplicate raster material.
'''
write(O/'README.md',readme)
write(O/'CAPTIONS.md','# T4 shared Visual-margin quartile captions\n\n'+'\n\n'.join(f"## Figure {f['ordinal']}: {f['title']}\n\n{f['caption']}" for f in build['figures'])+'\n')
ix=io.StringIO(newline='');writer=csv.DictWriter(ix,fieldnames=['page','task','title','svg','source_csv','preview','panels','points','eligible_strata','ineligible_strata']);writer.writeheader()
for f in build['figures']:writer.writerow({'page':f['ordinal'],'task':f['task'],'title':f['title'],'svg':Path(f['svg']['path']).relative_to(O).as_posix(),'source_csv':Path(f['sourceCSV']['path']).relative_to(O).as_posix(),'preview':Path(f['preview']['path']).relative_to(O).as_posix(),'panels':9,'points':72,'eligible_strata':f['eligibleStrata'],'ineligible_strata':f['ineligibleStrata']})
write(O/'FIGURE_INDEX.csv',ix.getvalue())
save(W/'PRODUCER_VISUAL_REVIEW.json',{'schema':'producer-t4-actual-visual-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'independent':False,'method':'Actual view_image(original) calls; final pages1-3,4-7,8-11, plus earlier2 samples separately.','finalPages':[{'page':f['ordinal'],'preview':f['preview'],'observed':'Visible title/metric units/seed/Q labels/N and low values; no clipping or text overlap. Native nonmonotonic points preserved; false N20† groups visible on pages5,7,9,11.'} for f in build['figures']],'limitations':'Visual readability review does not establish new scientific validity or inference.'})
save(W/'SOURCE_HISTORY.json',{'schema':'native-t4-source-history.v1','source':build['source'],'sameSourceSampleAndFinal':True,'sample':desc(W/'BUILD_REPORT_SAMPLE.json'),'final':desc(W/'BUILD_REPORT.json'),'sampleScope':'2pages/18panels/144points','finalScope':'11pages/99panels/792points','actualBuildExitCodes':[0,0],'revisions':[],'failures':[],'oldOutputsUnmodified':True,'noOldSuiteRerun':True})
code=O/'build_source';code.mkdir()
for p in [W/'build/build_t4.mjs',W/'verify_package.py',Path(__file__),W/'seal_final.py']:
    dst=code/p.name
    with dst.open('xb') as f:f.write(p.read_bytes())
for p in [W/'INPUT_PROVENANCE.json',W/'PRODUCER_PACKAGE_REVIEW.json',W/'PRODUCER_VISUAL_REVIEW.json',W/'SOURCE_HISTORY.json']:
    with (O/'provenance'/p.name).open('xb') as f:f.write(p.read_bytes())
save(W/'SOURCE_MANIFEST.json',{'schema':'native-t4-source-manifest.v1','files':[desc(p) for p in [W/'build/build_t4.mjs',W/'verify_package.py',Path(__file__),W/'seal_final.py']],'sourceRevision':'None; sample/final use identical source bytes.'})
with (O/'provenance/SOURCE_MANIFEST.json').open('xb') as f:f.write((W/'SOURCE_MANIFEST.json').read_bytes())
files=sorted(p for p in O.rglob('*') if p.is_file() and p.suffix not in ['.png','.zip'])
zip_path=O/'t4_margin_native_editable_and_sources.zip';members=[]
with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files:
        member=p.relative_to(O).as_posix();z.write(p,member);members.append({'member':member,**desc(p)})
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None and z.namelist()==[r['member'] for r in members]
    for d in members:
        b=z.read(d['member']);assert len(b)==d['bytes'] and hashlib.sha256(b).hexdigest()==d['sha256']
save(W/'ZIP_CONTENTS.json',{'schema':'native-t4-zip-contents.v1','zip':desc(zip_path),'members':members,'readBackByteSHAValidated':True,'PNGPreviewsOmitted':True})
print(json.dumps({'zip':desc(zip_path),'members':len(members),'docs':desc(O/'README.md'),'sourceManifest':desc(W/'SOURCE_MANIFEST.json')}))
