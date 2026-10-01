"""Seal paired native figures after independent delivery; root adopts separately."""
from pathlib import Path
import argparse,datetime,hashlib,json
W=Path(__file__).resolve().parent;O=W/'output'
def desc(p):
    p=Path(p);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def save(p,j):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
ap=argparse.ArgumentParser();ap.add_argument('--independent-delivery',required=True);ap.add_argument('--independent-sha',required=True);a=ap.parse_args()
ind=desc(a.independent_delivery);assert ind['sha256']==a.independent_sha
r=json.loads(Path(ind['path']).read_bytes());assert r.get('accepted_with_stated_limits') is True
build=json.loads((W/'BUILD_REPORT.json').read_bytes());producer=json.loads((W/'PRODUCER_PACKAGE_REVIEW.json').read_bytes());assert producer['passed'] and not producer['independent']
for f in build['figures']:
    for k in ['svg','preview','sourceCSV']:assert desc(f[k]['path'])==f[k]
assert desc(build['source']['path'])==build['source'] and desc(build['pptx']['path'])==build['pptx']
zm=json.loads((W/'ZIP_CONTENTS.json').read_bytes());assert desc(zm['zip']['path'])==zm['zip']
for d in zm['members']:assert desc(d['path'])=={k:d[k] for k in ['path','sha256','bytes']}
for d in json.loads((W/'SOURCE_MANIFEST.json').read_bytes())['files']:assert desc(d['path'])==d
manifest={'schema':'native-paired-artifact-manifest.v1','files':[desc(p) for p in sorted(O.rglob('*')) if p.is_file()],'build':desc(W/'BUILD_REPORT.json'),'inputProvenance':desc(W/'INPUT_PROVENANCE.json'),'sourceManifest':desc(W/'SOURCE_MANIFEST.json'),'producerPackageReview':desc(W/'PRODUCER_PACKAGE_REVIEW.json'),'producerVisualReview':desc(W/'PRODUCER_VISUAL_REVIEW.json'),'revision':desc(W/'SOURCE_REVISION.json'),'diff':desc(W/'V1_SAMPLE_TO_FINAL_V2.patch'),'zipContents':desc(W/'ZIP_CONTENTS.json'),'independentDelivery':ind}
save(W/'ARTIFACT_MANIFEST.json',manifest)
delivery={'schema':'native-paired-joint-delivery.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'completed_with_stated_limits':True,'root_adoption_pending':True,'scope':{'figurePages':11,'seedPanels':33,'pairedRows':132,'points':264,'guideSegments':198,'requestedCoverages':[0.5,0.75,0.9,1.0],'countTableRows':132,'visibleSuccessValues':264,'widthMm':181.9,'heightMm':build['figures'][0]['heightMm'],'minPhysicalFontPt':8,'nativeShapes':producer['totalNativeShapes'],'textObjects':producer['totalTexts']},'pptx':build['pptx'],'zip':zm['zip'],'build':desc(W/'BUILD_REPORT.json'),'source':build['source'],'sourceManifest':desc(W/'SOURCE_MANIFEST.json'),'artifactManifest':desc(W/'ARTIFACT_MANIFEST.json'),'inputProvenance':desc(W/'INPUT_PROVENANCE.json'),'zipContents':desc(W/'ZIP_CONTENTS.json'),'producerReview':desc(W/'PRODUCER_PACKAGE_REVIEW.json'),'producerVisualReview':desc(W/'PRODUCER_VISUAL_REVIEW.json'),'revision':desc(W/'SOURCE_REVISION.json'),'diff':desc(W/'V1_SAMPLE_TO_FINAL_V2.patch'),'independentDelivery':ind,'README':desc(O/'README.md'),'captions':desc(O/'CAPTIONS.md'),'index':desc(O/'FIGURE_INDEX.csv'),'limits':['Success denominator is the full common N, not selected k; actual saved realized coverage controls x.','Equal selected k does not imply equal membership; overlap counts shared selected members, not shared correct predictions.','Four saved observations only; no origin, extrapolation, AUC or improved-ranking inference from increasing success.','Stored-field k=ceil(requested*N), realized=k/N and range consistency checks plus percentage scaling only; no query-derived selection, rate, overlap or scientific test reconstruction.','No pooling, SD, CI, bootstrap, p-value or Holm display; inferential fields retained only in original source JSON.','Inherited saved-value/checkpoint-cache-image SHA and historical evidence-chain limitations unchanged.','Native primitive objects, no embedded-image substitution or native chart grouping.','No science, GPU, PowerPoint, live state, release, lock, HANDOFF or automation operations.']}
save(W/'DELIVERY.json',delivery)
print(json.dumps({'delivery':desc(W/'DELIVERY.json'),'artifactManifest':desc(W/'ARTIFACT_MANIFEST.json'),'pptx':build['pptx'],'zip':zm['zip']}))
