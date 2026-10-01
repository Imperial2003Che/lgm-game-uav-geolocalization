"""Preserve inherited supplementary PDF and prepare its necessary bibliography-only compilation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, difflib, os

HERE=Path(__file__).resolve().parent
OUT=HERE.parent.parent
DRAFT=OUT/'manuscript_reference_format_20260930_1538/manuscript'
def binding(p,raw): return {'path':str(p), 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}
def write(p,raw):
    with p.open('xb') as f: f.write(raw);f.flush();os.fsync(f.fileno())
    return binding(p,raw)
def derive(parent,target,sha,before,after,patch):
    old=parent.read_bytes();assert hashlib.sha256(old).hexdigest()==sha
    assert old.count(before)==1
    new=old.replace(before,after)
    delta=''.join(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),fromfile=str(parent),tofile=str(target)))
    return {'parent':binding(parent,old),'source':write(target,new),'diff':write(patch,delta.encode())}
old_pdf=(DRAFT/'supplementary.pdf').read_bytes()
assert hashlib.sha256(old_pdf).hexdigest()=='8c985d3a77d425fa367418f210f7c5a66cfcb9255b9e70e18180118b7d51a8cb'
preserved=write(HERE/'supplementary.before.pdf',old_pdf)
compiler=derive(HERE/'compile_main_only.py',HERE/'compile_supplement_only.py','201e553a462b41f6db4fb801a308aa20da15be91edef0af9c316b64ae92e4983',
    b"for name in ('main',):",b"for name in ('supplementary',):",HERE/'SUPPLEMENT_COMPILE_SOURCE.patch')
renderer=derive(HERE.parent/'manuscript_compile_20260930_0202/render_and_inspect_pdf.py',HERE/'render_supplement_only.py',
    '4da093ef783da6e6f9f1ed5bfc1d05c51f76a18a9217c26b8eba9bf52cbe23a2',
    b"for name in ('main', 'supplementary'):",b"for name in ('supplementary',):",HERE/'SUPPLEMENT_RENDER_SOURCE.patch')
report={'schema':'lgm.supplement-bibliography-format-dependency-addendum.v1','utc':datetime.now(timezone.utc).isoformat(),
    'source':binding(Path(__file__).resolve(),Path(__file__).read_bytes()), 'preserved_inherited_PDF':preserved,
    'reason':'Parent supplementary.bbl contains mean2025 and cdmnet2025 journal fields changed in the shared refs.bib; its PDF must be rebuilt to match the delivered LaTeX.',
    'historical_revision_report_retained':True,'initial_inherited_supplement_compile_decision_superseded':True,
    'compiler':compiler,'renderer':renderer,'scope':'Only supplementary bibliography dependency, no source/scientific values or main recompilation.'}
print(json.dumps(write(HERE/'SUPPLEMENT_DEPENDENCY_ADDENDUM.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()),ensure_ascii=False))
