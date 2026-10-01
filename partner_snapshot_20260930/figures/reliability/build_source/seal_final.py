"""Seal new figure package after independent delivery; root adopts separately."""
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
manifest={'schema':'native-reliability-artifact-manifest.v1','files':[desc(p) for p in sorted(O.rglob('*')) if p.is_file()],'build':desc(W/'BUILD_REPORT.json'),'inputProvenance':desc(W/'INPUT_PROVENANCE.json'),'sourceManifest':desc(W/'SOURCE_MANIFEST.json'),'producerPackageReview':desc(W/'PRODUCER_PACKAGE_REVIEW.json'),'producerVisualReview':desc(W/'PRODUCER_VISUAL_REVIEW.json'),'revision':desc(W/'SOURCE_REVISION.json'),'diff':desc(W/'V1_SAMPLE_TO_FINAL_V2.patch'),'zipContents':desc(W/'ZIP_CONTENTS.json'),'independentDelivery':ind}
save(W/'ARTIFACT_MANIFEST.json',manifest)
delivery={'schema':'native-reliability-joint-delivery.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'completed_with_stated_limits':True,'root_adoption_pending':True,'scope':{'figurePages':11,'seedPanels':33,'nativeRecords':66,'binRecords':990,'occupiedBinsAndPoints':140,'emptyBinsWithoutPoint':850,'storedECEFractions':66,'widthMm':181.9,'heightMm':build['figures'][0]['heightMm'],'minPhysicalFontPt':8,'nativeShapes':producer['totalNativeShapes'],'textObjects':producer['totalTexts']},'pptx':build['pptx'],'zip':zm['zip'],'build':desc(W/'BUILD_REPORT.json'),'source':build['source'],'sourceManifest':desc(W/'SOURCE_MANIFEST.json'),'artifactManifest':desc(W/'ARTIFACT_MANIFEST.json'),'inputProvenance':desc(W/'INPUT_PROVENANCE.json'),'zipContents':desc(W/'ZIP_CONTENTS.json'),'producerReview':desc(W/'PRODUCER_PACKAGE_REVIEW.json'),'producerVisualReview':desc(W/'PRODUCER_VISUAL_REVIEW.json'),'revision':desc(W/'SOURCE_REVISION.json'),'diff':desc(W/'V1_SAMPLE_TO_FINAL_V2.patch'),'independentDelivery':ind,'README':desc(O/'README.md'),'captions':desc(O/'CAPTIONS.md'),'index':desc(O/'FIGURE_INDEX.csv'),'limits':['Fixed margin score is not posterior or fitted calibration; equality line is reference only.','Lower fixed-score ECE does not imply higher retrieval accuracy or improved calibration.','Per-variant bin membership;850 empty bins retain nulls and no points; counts do not imply uncertainty.','No pooling, ECE/gap/statistics recalculation, CI/bootstrap/significance, NPZ/model/fullranking/AP or cache/image/weight access.','Inherited saved-value/checkpoint-cache-image SHA and historical evidence-chain limits unchanged.','Native primitive objects, no embedded-image substitution or native chart grouping.','No science/GPU/PowerPoint/live state/release/lock/HANDOFF/automation operations.']}
save(W/'DELIVERY.json',delivery)
print(json.dumps({'delivery':desc(W/'DELIVERY.json'),'artifactManifest':desc(W/'ARTIFACT_MANIFEST.json'),'pptx':build['pptx'],'zip':zm['zip']}))
