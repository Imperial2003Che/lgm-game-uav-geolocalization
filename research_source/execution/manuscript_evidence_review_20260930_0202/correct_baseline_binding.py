from pathlib import Path
import hashlib,json,difflib
R=Path(__file__).resolve().parent
O=R.parent.parent
A=O/'manuscript'
B=O.parent/'paper_label_revision_20260914'/'manuscript'
def d(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
entries=[]
for n in ['main.tex','supplementary.tex','results/semantic_results.tex']:
 a=A/n;b=B/n
 diff=''.join(difflib.unified_diff(a.read_text(encoding='utf-8').splitlines(True),b.read_text(encoding='utf-8').splitlines(True),fromfile=str(a),tofile=str(b)))
 patch=R/('EARLIER_TO_ACTUAL_BASE_'+Path(n).name+'.patch')
 with patch.open('x',encoding='utf-8',newline='\n') as f:f.write(diff)
 copy=R/('actual_base_'+Path(n).name+'.txt')
 with copy.open('xb') as f:f.write(b.read_bytes())
 entries.append({'earlier_read':d(a),'actual_producer_base':d(b),'same_bytes':a.read_bytes()==b.read_bytes(),'complete_difference':d(patch),'snapshot':d(copy)})
 print(diff)
record={'schema':'independent-manuscript-baseline-correction.v1','reason':'Root clarified actual producer baseline is outputs/paper_label_revision_20260914/manuscript. Earlier INPUT_CHECKLIST old_main/old_supplement/old_empty_result_module refer to a different historical draft. Keep that checklist and snapshots unchanged; this addendum is the actual base authority for final old/new review.','files':entries,'final_diff_must_use':str(B),'manuscript_modified':False}
out=R/'BASELINE_BINDING_ADDENDUM.json'
with out.open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(d(out),ensure_ascii=True))
