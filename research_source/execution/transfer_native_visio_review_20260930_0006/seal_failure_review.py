"""Seal only the new failure evidence; do not rerun prior successful review suites."""
from pathlib import Path
import json,hashlib,datetime as dt
B=Path(__file__).resolve().parent;OUT=B.parent.parent;W=OUT/'transfer_native_visio_20260930_0006'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def desc(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
fail=read(W/'BUILD_FAILURE.json');launch=read(W/'BUILD_ACTUAL_EXIT.json');source=desc(W/'build_visio.ps1')
assert source==fail['source']
assert source['sha256']==launch['sourceSHA256']=='21b292f980dbb62e208f492ef731bfce7d0541bdabce709eaa54a19d8a01a5a6'
assert launch['actualExitCode']==1 and launch['singleAttempt'] is True
assert fail['stage']=='create' and fail['results']==[] and fail['cleanupFailures']==[] and fail['recordedAfterFinally'] is True
assert [e['event'] for e in fail['events']]==['unconfirmed_reference_released_without_Quit']
assert ': line 52' in fail['scriptStack'] and 'not parented by this exact builder' in fail['message']
artifacts=list((W/'output').glob('*.vsdx'))+list((W/'output/previews').glob('*.png'))+list((W/'output/previews').glob('*.pdf'))
assert not artifacts
assert not (W/'BUILD_REPORT.json').exists()
paths=[W/n for n in ['BUILD_ACTUAL_EXIT.json','BUILD_ACTUAL.stdout.txt','BUILD_ACTUAL.stderr.txt','BUILD_FAILURE.json','POST_FAILURE_VISIO_OBSERVATION.json','build_visio.ps1','SOURCE_HISTORY_ADDENDUM.json','SOURCE_DERIVATION.json']]
paths+=[OUT/'execution/host_boot_change_20260930_0008/ROOT_AFTER_T3_COM.json']
paths+=sorted(p for p in B.iterdir() if p.is_file() and p.name not in ['FAILURE_REVIEW.json','DELIVERY.json'])
bindings=[desc(p) for p in dict.fromkeys(paths)]
result=dict(schema='independent-t3-visio-failure-review-final.v1',utc=dt.datetime.now(dt.timezone.utc).isoformat(),source=desc(Path(__file__)),review=desc(B/'FAILURE_ANALYSIS.md'),decision='NO_ARTIFACT_ADOPTION; ACTUAL_COM_ATTEMPT_FAILED; EXISTING_PROCESS_OWNERSHIP_UNRESOLVED',producerActualExit=1,failedStage='create: direct-builder parent gate',firstExecutionFailureReviewed=True,priorInputContract=dict(path=str(B/'DATA_CONTRACT.json'),checks=800,scope='successful v2 input/display contract only; not rerun'),priorSourceReview=dict(path=str(B/'PREEXEC_SOURCE_REVIEW.json'),checks=1247,scope='successful v2 static review only; Windows launch-parent assumption failed in actual first attempt; not rerun'),newArtifacts=[],artifactXMLReviewed=False,originalPNGViewsPerformed=0,COMExecutedByReviewer=False,producerCheckersInvoked=False,scientificExecution=False,processControlPerformed=False,HANDOFFChanged=False,automationChanged=False,limits=['Current Visio CIM/service observation does not prove ownership of the missing original COM candidate.','No Quit, Kill, process absence-as-exit or reconstructed candidate evidence is endorsed.','Any future broker-aware source and execution require a separate review and root decision; no retry permission follows from this report.'],bindings=bindings)
with (B/'FAILURE_REVIEW.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
with (B/'DELIVERY.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(dict(schema='independent-t3-visio-review-delivery.v1',utc=dt.datetime.now(dt.timezone.utc).isoformat(),kind='input/static review followed by actual execution-failure review; no figure deliverable',report=desc(B/'FAILURE_REVIEW.json'),review=desc(B/'FAILURE_ANALYSIS.md'),source=desc(Path(__file__))),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(report=desc(B/'FAILURE_REVIEW.json'),delivery=desc(B/'DELIVERY.json')),ensure_ascii=False))
