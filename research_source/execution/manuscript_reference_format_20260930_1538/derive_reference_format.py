"""Create a new local draft with only three IEEE journal-title formats changed."""
from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json, os, re

OUT=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914')
HERE=Path(__file__).resolve().parent
PARENT=OUT/'manuscript_citation_revision_20260930_0520'
BASE=PARENT/'manuscript'
NEW=OUT/'manuscript_reference_format_20260930_1538'
DRAFT=NEW/'manuscript'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def descriptor(path,raw): return dict(path=str(path.resolve()),bytes=len(raw),sha256=sha(raw))
def read(path,cap=128*1024):
    n=path.stat().st_size
    if not 0<=n<=cap: raise ValueError('Bounded selected dependency required: '+str(path))
    with path.open('rb') as f: raw=f.read(cap+1)
    if len(raw)!=n or len(raw)>cap: raise ValueError('Changed selected dependency length')
    return descriptor(path,raw),raw
def write(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    return descriptor(path,raw)
def publish(path,value): return write(path,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))

root_d,root_raw=read(PARENT/'ROOT_MANUSCRIPT_CITATION_ADOPTION.json')
if root_d['bytes']!=28808 or root_d['sha256']!='8e6f290cfa7943b1b60ac7a919beb29cf9a1669af6fad9464925ec86cf6c1c63':
    raise ValueError('Exact adopted current parent required')
add_d,add_raw=read(PARENT/'ROOT_RESEARCH_BINDING_ADDENDUM.json')
if add_d['sha256']!='a1d755bb96bd0b07260f2ee9653a626cbc0c6deee2274c9ae5642992440ae5d5':
    raise ValueError('Exact external parent addendum required')
abrv_path=Path(r'C:\Users\17703\AppData\Local\Programs\MiKTeX\bibtex\bib\ieeetran\IEEEabrv.bib')
abrv_d,abrv_raw=read(abrv_path)
specs=[
 ('IEEE_J_GRS',b'IEEE Transactions on Geoscience and Remote Sensing',b'{IEEE} Trans. Geosci. Remote Sens.',10),
 ('IEEE_J_CASVT',b'IEEE Transactions on Circuits and Systems for Video Technology',b'{IEEE} Trans. Circuits Syst. Video Technol.',6),
 ('IEEE_J_IP',b'IEEE Transactions on Image Processing',b'{IEEE} Trans. Image Process.',1)]
for macro,old,new,count in specs:
    found=re.search(rb'@STRING\{'+macro.encode('ascii')+rb'\s*=\s*"([^"]+)"\}',abrv_raw)
    if not found or found.group(1)!=new: raise ValueError('Installed IEEE abbreviation value changed')
root=json.loads(root_raw)
selected={}
for item in root['verified_bindings']:
    path=Path(item['path'])
    if path.is_relative_to(BASE):
        if str(path) in selected and selected[str(path)]!=item: raise ValueError('Conflicting parent dependency')
        selected[str(path)]=item
if len(selected)!=34: raise ValueError('Expected32 source dependencies and2 adopted PDFs')
NEW.mkdir(exist_ok=False)
DRAFT.mkdir()
copies=[]; raw_refs=None; original_refs_d=None
for expected in selected.values():
    path=Path(expected['path']); relative=path.relative_to(BASE)
    if relative==Path('main.pdf'): continue
    actual,raw=read(path,cap=6*1024*1024)
    if actual!=expected: raise ValueError('Changed selected parent dependency: '+str(relative))
    if relative==Path('refs.bib'):
        raw_refs=raw; original_refs_d=actual
        original=write(HERE/'refs.before.bib',raw)
        continue
    target=write(DRAFT/relative,raw)
    copies.append(dict(relative=str(relative),inherited_parent=actual,new_copy=target,unchanged=True))
if raw_refs is None or len(copies)!=32: raise ValueError('Expected31 unchanged sources+one adopted supplementary PDF')
revised=raw_refs; changes=[]
for macro,old,new,count in specs:
    token=b'journal = {'+old+b'},'
    replacement=b'journal = {'+new+b'},'
    if revised.count(token)!=count: raise ValueError('Unexpected journal-field occurrence count')
    revised=revised.replace(token,replacement)
    changes.append(dict(macro=macro,full_journal=old.decode('ascii'),abbreviated_journal=new.decode('ascii'),fields_changed=count))
if sum(x['fields_changed'] for x in changes)!=17: raise ValueError('Exact17 journal formatting fields')
# Reverting only the17 substitutions must recover every original byte.
restored=revised
for macro,old,new,count in specs:
    restored=restored.replace(b'journal = {'+new+b'},',b'journal = {'+old+b'},')
if restored!=raw_refs: raise ValueError('Nonformat source bytes changed')
new_refs=write(DRAFT/'refs.bib',revised)
patch=''.join(difflib.unified_diff(raw_refs.decode('utf-8').splitlines(keepends=True),revised.decode('utf-8').splitlines(keepends=True),fromfile='adopted_parent/refs.bib',tofile='new_draft/refs.bib'))
patch_d=write(HERE/'REFS_ONLY.patch',patch.encode('utf-8'))
compiler_parent=OUT/'execution/manuscript_compile_20260930_0202/compile_working_draft.py'
compiler_d,compiler_raw=read(compiler_parent)
if compiler_d['bytes']!=3645 or compiler_d['sha256']!='f833933b57e845fb25155442d3366ce4650b5b01d0d4a365a0e9a9f307e0b88a':
    raise ValueError('Original compiler source changed')
needle=b"for name in ('main', 'supplementary'):"
if compiler_raw.count(needle)!=1: raise ValueError('Exact single document-loop compiler delta')
compiler_new=compiler_raw.replace(needle,b"for name in ('main',):").replace(b'Compile the new, multi-file local manuscript; no packages or science run.',b'Compile only the newly changed main bibliography; unchanged supplement inherited.')
compiler_new_d=write(HERE/'compile_main_only.py',compiler_new)
cp=''.join(difflib.unified_diff(compiler_raw.decode().splitlines(keepends=True),compiler_new.decode().splitlines(keepends=True),fromfile='original/compile_working_draft.py',tofile='new/compile_main_only.py'))
compiler_patch=write(HERE/'COMPILE_SOURCE.patch',cp.encode())
readme=(
 '# Local reference-format working draft\n\n'
 'This continues the adopted17+6 local citation draft. Only17 journal-name display fields in refs.bib use three title abbreviations from the installed IEEEabrv.bib. Main source, scientific values, figures, citation keys, all other BibTeX fields and the31 other source dependencies are byte-identical. No font or page-size change is made.\n\n'
 'The main PDF requires actual local compilation and page review; the unchanged six-page supplementary PDF is inherited byte-for-byte. This is not a final scientific manuscript or Overleaf delivery. T6, LOHO, fresh explanatory figures, author/independent baselines, efficiency and application-level Visio acceptance remain pending. Negative results and inherited evidence limitations remain in the source.\n\n'
 'The old drafts and delivery archives are preserved. No scientific models, weights, NPZ, cache/image corpus or old ZIP were read. This folder is a new supplement to prior deliveries.\n')
readme_d=write(NEW/'README_LOCAL_DRAFT.md',readme.encode())
report={
 'schema':'lgm.reference-format-only-draft-revision.v1',
 'utc':datetime.now(timezone.utc).isoformat(),'source':read(Path(__file__).resolve())[0],
 'parent_root':root_d,'parent_external_addendum':add_d,'installed_abbreviation_source':abrv_d,
 'changes':changes,'changed_source_files':['refs.bib'],'original_refs':original_refs_d,
 'preserved_refs_before':original,'new_refs':new_refs,'full_source_diff':patch_d,
 'inherited_copies':copies,'unchanged_other_source_dependencies':31,
 'supplementary_PDF_inherited_not_recompiled':True,
 'compiler_parent':compiler_d,'compiler_main_only_source':compiler_new_d,'compiler_full_delta':compiler_patch,
 'local_readme':readme_d,'main_tex_scientific_tables_figures_all_other_BibTeX_fields_unchanged':True,
 'format_reverse_recovers_original_exact_bytes':True,
 'font_size_geometry_citation_content_changed':False,
 'original_source_line_ending_counts':dict(CRLF=raw_refs.count(b'\r\n'),LF=raw_refs.count(b'\n')),
 'new_source_line_ending_counts':dict(CRLF=revised.count(b'\r\n'),LF=revised.count(b'\n')),
 'actual_compile_or_visual_review_completed':False,
 'scientific_execution_or_new_results':False,'new_final_paper_or_Overleaf':False,
 'original_scientific_sources_recompiled_or_old_suites_replayed':False,
 'old_large_archives_or_weights_read':False,'automatic_followup_retained':True}
rd=publish(HERE/'REFERENCE_FORMAT_REVISION.json',report)
print(json.dumps(dict(revision=rd,draft=str(DRAFT),compiler=compiler_new_d,changed_fields=17,unchanged_other_sources=31),ensure_ascii=False))
