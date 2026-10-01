"""Verify the two differently named bounded research binding lists."""
from pathlib import Path
import hashlib,json,datetime
HERE=Path(__file__).resolve().parent;EX=HERE.parent;OUT=EX.parent
DEST=OUT/'manuscript_citation_revision_20260930_0520'
def rec(p):
 b=p.read_bytes();return {'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
bindings=[]
for folder,key,sha in [
 ('citation_datasets_review_20260930_0509','artifact_bindings','c35fb462e6abefa439c284c2ad9a414dd9e86ff9df4014da965e4d4e9e98f4b8'),
 ('citation_camp_dac_review_20260930_0509','small_files','87a4b19f6399c67699951b416877cb5a1a26c9a19f7e5c0027810a19040af8cd')]:
 p=EX/folder/'DELIVERY.json';assert rec(p)['sha256']==sha
 d=json.loads(p.read_bytes())
 for r in d[key]:
  assert rec(Path(r['path']))==r
  bindings.append(r)
report={'schema':'root-local-draft-research-binding-addendum.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'read_with':rec(DEST/'ROOT_MANUSCRIPT_CITATION_ADOPTION.json'),'source':rec(Path(__file__)),
 'reason':'The generic package root helper only expanded delivery.files or delivery.records. These two deliveries use artifact_bindings and small_files, so their report hashes were bound in the root and their packaged members were individually verified, but the separate producer manifest edges were not expanded. This addendum checks only those new small-file edges.',
 'bindings':bindings,'verified_binding_count':len(bindings),
 'scientific_or_old_suite_rerun':False,'downloaded_pdf_and_research_preview_root_rehash':False,
 'limits':['Downloaded author-paper PDFs/previews remain the originating agent direct-access and visual evidence, not a second root page review.',
 'The root read full dataset/CAMP-DAC research reports and their scope summaries, but did not independently verify all36 author-report rows.',
 'No old manuscript/root/ZIP changed. This is an external addendum to the already sealed new package, not a new package version.']}
with (DEST/'ROOT_RESEARCH_BINDING_ADDENDUM.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(rec(DEST/'ROOT_RESEARCH_BINDING_ADDENDUM.json'),ensure_ascii=False))

