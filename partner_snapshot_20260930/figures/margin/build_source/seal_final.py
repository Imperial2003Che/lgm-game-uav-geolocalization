"""Final joint packaging seal; independent review and root adoption are distinct."""
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
build=json.loads((W/'BUILD_REPORT.json').read_bytes());producer=json.loads((W/'PRODUCER_PACKAGE_REVIEW.json').read_bytes())
assert producer['passed'] and producer['independent'] is False
for f in build['figures']:
    for k in ['svg','preview','sourceCSV']:assert desc(f[k]['path'])==f[k]
assert desc(build['source']['path'])==build['source'] and desc(build['pptx']['path'])==build['pptx']
zm=json.loads((W/'ZIP_CONTENTS.json').read_bytes());assert desc(zm['zip']['path'])==zm['zip']
for d in zm['members']:assert desc(d['path'])=={k:d[k] for k in ['path','sha256','bytes']}
for d in json.loads((W/'SOURCE_MANIFEST.json').read_bytes())['files']:assert desc(d['path'])==d
manifest={'schema':'native-t4-artifact-manifest.v1','files':[desc(p) for p in sorted(O.rglob('*')) if p.is_file()],'build':desc(W/'BUILD_REPORT.json'),'inputProvenance':desc(W/'INPUT_PROVENANCE.json'),'sourceManifest':desc(W/'SOURCE_MANIFEST.json'),'producerPackageReview':desc(W/'PRODUCER_PACKAGE_REVIEW.json'),'producerVisualReview':desc(W/'PRODUCER_VISUAL_REVIEW.json'),'history':desc(W/'SOURCE_HISTORY.json'),'zipContents':desc(W/'ZIP_CONTENTS.json'),'independentDelivery':ind}
save(W/'ARTIFACT_MANIFEST.json',manifest)
delivery={'schema':'native-t4-margin-joint-delivery.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'completed_with_stated_limits':True,'root_adoption_pending':True,'scope':{'figurePages':11,'sharedMarginStrata':132,'metricPanels':99,'numericPoints':792,'eligibleStrata':84,'ineligibleStrata':48,'otherT4RowsPreservedNotPlotted':330,'widthMm':181.9,'heightMm':build['figures'][0]['heightMm'],'minPhysicalFontPt':8,'nativeShapes':producer['totalNativeShapes'],'textObjects':producer['totalTexts']},'pptx':build['pptx'],'zip':zm['zip'],'build':desc(W/'BUILD_REPORT.json'),'source':build['source'],'sourceManifest':desc(W/'SOURCE_MANIFEST.json'),'artifactManifest':desc(W/'ARTIFACT_MANIFEST.json'),'inputProvenance':desc(W/'INPUT_PROVENANCE.json'),'zipContents':desc(W/'ZIP_CONTENTS.json'),'producerReview':desc(W/'PRODUCER_PACKAGE_REVIEW.json'),'producerVisualReview':desc(W/'PRODUCER_VISUAL_REVIEW.json'),'sourceHistory':desc(W/'SOURCE_HISTORY.json'),'independentDelivery':ind,'README':desc(O/'README.md'),'captions':desc(O/'CAPTIONS.md'),'index':desc(O/'FIGURE_INDEX.csv'),'limits':['Only Visual-defined shared-margin strata; no330 entropy/semantic strata plotted.','84 N>=100 gate-passing strata do not imply inference;48 N20 ineligible groups visibly flagged.','No pooling, newmeans/quantiles/memberships, SD/CI/bootstrap/pvalue or causal/calibration claims.','Inherited saved-value and checkpoint/cache/image authority/metadata gaps; no NPZ/model/fullranking/AP recomputation.','Native primitive objects; no grouped native charts or embedded image substitutes.','No science/GPU/PowerPoint app/live state/release/HANDOFF/automation changes.']}
save(W/'DELIVERY.json',delivery)
print(json.dumps({'delivery':desc(W/'DELIVERY.json'),'artifactManifest':desc(W/'ARTIFACT_MANIFEST.json'),'pptx':build['pptx'],'zip':zm['zip']}))
