"""Adopt bounded literature research and independent local scope review only."""
from pathlib import Path
import datetime, hashlib, json

HERE=Path(__file__).parent
EX=HERE.parent
PEER=EX/'citation_foundations_scope_review_20260930_0405'
bindings={}

def bind(path,expected=None,sha=None):
    path=Path(path)
    assert path.stat().st_size<150000
    data=path.read_bytes()
    b=dict(path=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    if expected: assert b==expected,str(path)
    if sha: assert b['sha256']==sha,str(path)
    bindings[str(path)]=b
    return b

def load(path,sha=None):
    bind(path,sha=sha)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

delivery=load(HERE/'DELIVERY.json','15317cd56357905614f3497895890b710b2a98ed7f57a500e9788e227403eb96')
report=load(HERE/'FOUNDATION_CITATION_REVIEW.json','1fc0add81a24d08395cfe99ba8aa653e5b1fdd0842c55b086ecc63d89be4a1ca')
peer=load(PEER/'SCOPE_REVIEW.json','ec08b761d59c1e76b4755eea743c9f1a3e32074ac70b1d40c317f53324223258')
access=load(HERE/'PRIMARY_ACCESS.json')
decision=load(HERE/'CORRECTION_DECISION.json')
for record in delivery['files']+report['local_inputs']+peer['bindings']: bind(record['path'],record)
bind(PEER/'REVIEW.md')
bind(HERE/'ROOT_PRIMARY_ACCESS_ADDENDUM.md')
assert peer['accepted_for_bounded_scope_only'] is True
assert peer['scope_keys']==report['scope_keys'] and len(set(report['scope_keys']))==13
assert len(report['entries'])==13 and peer['saved_local_field_count_checked']==110
assert decision['confirmed_bibtex_corrections']==peer['confirmed_bibtex_corrections']==[]
assert all(not report[k] for k in ('all_bibliography_verified','all_fields_verified','scientific_validation','manuscript_modified','sealed_zip_modified'))
assert all(not e['confirmed_correction_required'] for e in report['entries'])
assert len({s['id'] for s in access['sources']})==len(access['sources'])
assert all(set(e['sources']) <= {s['id'] for s in access['sources']} for e in report['entries'])
src=bind(__file__)
out={
 'schema':'root-bounded-foundation-citation-research-adoption.v1',
 'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'accepted_research_scope_only':True,
 'scope_keys':report['scope_keys'],
 'confirmed_bibtex_corrections':[],
 'manuscript_modified':False,
 'all_bibliography_verified':False,
 'all_fields_verified':False,
 'scientific_validation':False,
 'method':'Root AI read producer report and decisions, complete independent scope source/findings and targeted actual manuscript text. Root separately opened the conference CSLS first-page record and current author brightness code; ANU direct read failed. It did not independently browse all thirteen references or rerun the 168 local assertions.',
 'source':src,
 'bindings':list(bindings.values()),
 'limits':[
 'Thirteen foundational references only. Remaining bibliography and inaccessible fields are not accepted as verified.',
 'Keep selected conference author order and publisher-version pagination. Producer indexed versus direct source access remains as originally recorded; root spot checks are a separate addendum.',
 'AQE pages, Efron DOI/expanded given name, Holm DOI and some ICLR ordinal/publisher-role fields remain unresolved. No correction is inferred from a failed endpoint.',
 'McNemar exact-binomial formula needs a specific source check; actual manuscript test prose is line570 and citation571. This does not establish a wrong test or new scientific failure.',
 'The brightness comparison concerns currently read author master, not a pinned2019 revision. A future revision may clarify project-adapted direction/severities while preserving frozen transformations.',
 'No experiment, model, cache, image, scientific statistics, compilation, PDF/ZIP, or Overleaf execution. No externally verified human review is claimed.'
 ]
}
target=HERE/'ROOT_CITATION_RESEARCH_ADOPTION.json'
with target.open('x',encoding='utf-8',newline='\n') as f: f.write(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'root':bind(target),'bindings':len(out['bindings']),'keys':13},ensure_ascii=False))
