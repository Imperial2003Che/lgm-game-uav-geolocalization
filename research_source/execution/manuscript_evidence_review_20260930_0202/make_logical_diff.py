from pathlib import Path
import difflib
R=Path(__file__).resolve().parent;O=R.parent.parent
B=O.parent/'paper_label_revision_20260914/manuscript'
N=O/'manuscript_evidence_revision_20260930_0202/manuscript'
for name in ['main.tex','supplementary.tex','README_OVERLEAF.md']:
 a=(B/name).read_text(encoding='utf-8').splitlines(True)
 b=(N/name).read_text(encoding='utf-8').splitlines(True)
 diff=''.join(difflib.unified_diff(a,b,fromfile='actual_base/'+name,tofile='working/'+name))
 with (R/('LOGICAL_DIFF_'+name+'.patch')).open('x',encoding='utf-8',newline='\n') as f:f.write(diff)
 print(diff)
