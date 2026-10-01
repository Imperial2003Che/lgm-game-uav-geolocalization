"""Package new paired-success figures and adopted small sources only."""
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
readme='''# Coverage-constrained success: native editable figures

Final delivery is `t5_paired_native_editable_11figures.pptx` and the 11 SVGs
under `native_svg/`. Each research figure is 181.9 mm wide and
188.3833333333333 mm high, with Arial at least 8 physical points. The PPTX has
2,431 individual native editable objects, including 1,518 text objects; no
embedded SVG, raster, Excel chart or workbook substitutes. Stable named
objects can be selected individually. Objects are not grouped into charts.
SVGs retain native text, lines and markers. Reducing physical width reduces
the final font size below 8 pt.

## What is plotted

These are official clean-query diagnostics, not corruption results. Each of
11 tasks has three separate seed panels. The 132 paired source rows retain
the four registered requested coverage levels 0.5, 0.75, 0.9 and 1.0. Each
panel plots two series of four points: 264 points and 198 adjacent connecting
guides in total. The 75% record comes directly from the paired source, not
interpolation from the separate native risk-coverage series.

The x coordinate is the saved realized coverage k/N, multiplied by 100.
The y coordinate is the saved coverage_constrained_success visual_rate or
full_rate, multiplied by 100: selected AND top1-correct / the common full
query count N. This is not selective R@1, whose denominator is selected k.
Both axes run from 0 to 100. Requested coverage, actual k/N and selected-set
overlap counts appear below each seed panel. Full-precision fractions are
preserved in CSV and notes; visible success percentages are rounded to three
decimals, so very low street values remain readable.

Upstream, the variants independently select queries by stable descending raw
top1-minus-top2 cosine margin after Full is aligned to Visual's query order.
Equal k does not imply equal selected members. Overlap means members selected
by both variants, not queries correctly predicted by both. At 100% coverage,
k and overlap equal N, and success reduces to ordinary full-query R@1. That
endpoint is retained separately for every task and seed.

Connecting segments only guide the eye between the four saved observations.
No origin, extrapolated point, fitted curve, AUC or unmeasured coverage is
added. Increasing coverage admits more queries; rising success can reflect
that mechanical effect and does not establish better ranking. Visual circles
and Full squares use true coordinates without jitter; real overlaps remain.

Tasks, retrieval directions, heights and seeds stay separate. No pooling,
three-seed SD, CI, bootstrap interval, p-value, Holm decision or significance
is drawn or newly calculated. Complete original paired inferential fields
remain in the archived source JSON only. These descriptive plots do not
replace the previously adopted negative primary and transfer findings.

## Exact sources and limits

The complete T5 JSON is an exact 744943-byte copy with SHA-256
`033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc`, bound
through root adoption
`f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a` and its
sealed CAPTURE. Only these adopted small files are read. Each paired row's
full N and membership digest are tied to its task/seed's Visual and Full
native records. `PAIRED_SUCCESS_132.csv` and each task's 12-row CSV flatten
the plotted saved fields; original precision is retained. Speaker notes
include the complete caption, source SHA and exact 12-row plot table.

The builder performs small stored-field consistency calculations, including
k=ceil(requested*N), realized=k/N, endpoint/range checks and percentage
scaling. It does not reconstruct selection, rates or overlap from queries,
or recompute scientific tests. No old NPZ, model, weights, cache or image
bytes are read. Upstream query validation, stored-value scope, inherited
checkpoint/cache/image SHA authority, historical metadata-chain gaps and
the absence of a new model/full-ranking/all-positive-rank AP recomputation
remain unchanged. No scientific state, GPU, native environment, recovery,
release, lock, HANDOFF, automation or original scientific file is modified.
T6 or later experiment completion is not implied.

## Build and verification

V1 produced two samples successfully. Before the first full build, v2 added
visible three-decimal success rows for low-value readability, moved the
footer and increased page height from 467 to 534 pt; sample mode is refused
to preserve the original executed source, sample files and report. The
complete source diff and revision record are included. Source data and plot
coordinates are unchanged. This was a preparation revision, not a failed
scientific experiment. V2's first full 11-page build exited 0.

Every final PPTX page was imported and CPU-rendered with artifact-tool, and
all 11 resulting PNGs were actually viewed individually at original size.
No text clipping or overlap was seen. Low street values, N80 count tables,
real data-point overlaps and the four requested-coverage labels are readable.
No PowerPoint application or scientific package was started.

The first bounded author export check passed 22,937 assertions for source
copies, plotted values, counts, actual native XML/text, physical fonts and
dimensions, notes and coordinates. This is a producer check, not independent
acceptance. Independent display, artifact, visual and semantic review and
root adoption are bound separately. The ZIP holds the final PPTX, 11 native
SVGs, exact small JSON, plot CSVs, captions/index/provenance and producer
sources. PNG previews remain beside the ZIP and are not duplicated inside.
Root-owned adoption and automation files are deliberately excluded.
'''
write(O/'README.md',readme)
write(O/'CAPTIONS.md','# Coverage-constrained success captions\n\n'+'\n\n'.join(f"## Figure {f['ordinal']}: {f['title']}\n\n{f['caption']}" for f in build['figures'])+'\n')
ix=io.StringIO(newline='');wr=csv.DictWriter(ix,fieldnames=['page','task','title','svg','source_csv','preview','panels','paired_rows','points','guides']);wr.writeheader()
for f in build['figures']:wr.writerow({'page':f['ordinal'],'task':f['task'],'title':f['title'],'svg':Path(f['svg']['path']).relative_to(O).as_posix(),'source_csv':Path(f['sourceCSV']['path']).relative_to(O).as_posix(),'preview':Path(f['preview']['path']).relative_to(O).as_posix(),'panels':3,'paired_rows':12,'points':24,'guides':18})
write(O/'FIGURE_INDEX.csv',ix.getvalue())
save(W/'PRODUCER_VISUAL_REVIEW.json',{'schema':'producer-paired-actual-visual-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'independent':False,'method':'Actual view_image(original) of all 11 final PNGs in batches 1-3, 4-7 and 8-11; earlier two v1 samples separately.','finalPages':[{'page':f['ordinal'],'preview':f['preview'],'observed':'No visible text clipping or overlap; low street success values, full N, k/N, selected-set overlap and four requested-coverage labels legible. True point overlap retained.'} for f in build['figures']],'limitation':'Visual readability is not new scientific or inference validation.'})
sources=[W/'build/build_paired.mjs',W/'build/build_paired_v2.mjs',W/'prepare_revision.py',W/'verify_package.py',Path(__file__),W/'seal_final.py']
save(W/'SOURCE_MANIFEST.json',{'schema':'native-paired-source-manifest.v1','files':[desc(p) for p in sources],'revision':desc(W/'SOURCE_REVISION.json'),'fullDiff':desc(W/'V1_SAMPLE_TO_FINAL_V2.patch'),'rootOwnedFilesExcluded':True})
code=O/'build_source';code.mkdir()
for p in sources:
    with (code/p.name).open('xb') as f:f.write(p.read_bytes())
for p in [W/'INPUT_PROVENANCE.json',W/'PRODUCER_PACKAGE_REVIEW.json',W/'PRODUCER_VISUAL_REVIEW.json',W/'SOURCE_REVISION.json',W/'SOURCE_MANIFEST.json',W/'V1_SAMPLE_TO_FINAL_V2.patch']:
    with (O/'provenance'/p.name).open('xb') as f:f.write(p.read_bytes())
files=sorted(p for p in O.rglob('*') if p.is_file() and p.suffix not in ['.png','.zip'])
zip_path=O/'t5_paired_native_editable_and_sources.zip';members=[]
with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files:
        member=p.relative_to(O).as_posix();z.write(p,member);members.append({'member':member,**desc(p)})
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None and z.namelist()==[r['member'] for r in members]
    for d in members:
        b=z.read(d['member']);assert len(b)==d['bytes'] and hashlib.sha256(b).hexdigest()==d['sha256']
save(W/'ZIP_CONTENTS.json',{'schema':'native-paired-zip-contents.v1','zip':desc(zip_path),'members':members,'readBackByteSHAValidated':True,'PNGPreviewsOmitted':True})
print(json.dumps({'zip':desc(zip_path),'members':len(members),'docs':desc(O/'README.md'),'sourceManifest':desc(W/'SOURCE_MANIFEST.json')}))
