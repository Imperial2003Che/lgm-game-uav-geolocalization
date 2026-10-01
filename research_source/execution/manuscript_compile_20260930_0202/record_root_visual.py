"""Record root's completed, actual tool-based page review; not an image test."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

here = Path(__file__).resolve().parent
def bind(p):
    b=p.read_bytes()
    return {'path':str(p), 'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}
layout=json.loads((here/'preview_2/PDF_LAYOUT.json').read_text(encoding='utf-8'))
pages=[p['png'] for d in layout['documents'] for p in d['pages']]
assert len(pages)==22
assert [Path(p['path']).name for p in pages] == ([f'main-{i:02d}.png' for i in range(1,17)]+[f'supplementary-{i:02d}.png' for i in range(1,7)])
assert all(bind(Path(p['path']))==p for p in pages)
report={
 'schema':'root-manuscript-actual-page-review.v1',
 'utc':datetime.now(timezone.utc).isoformat(),
 'reviewer':'root',
 'method':'Root actually viewed every final PNG through view_image(detail=original), forwarded as images, at 1.4x PDF rendering resolution. This file records those visual observations, not an automated visual pass.',
 'first_compilation_review':'All 17+6 first-build pages were viewed. Main p11 overfull float stack and p16/17 bibliography column imbalance led to the preserved three-file layout/caption revision.',
 'final_compilation':bind(here/'attempt_2/COMPILE.json'),
 'final_layout':bind(here/'preview_2/PDF_LAYOUT.json'),
 'pages':pages,
 'all_final_pages_actually_viewed':True,
 'accepted_pages':22,
 'findings':[
  'Main 1-8: local-working-draft label, abstract, contributions, architecture, frozen protocol and result-section beginning are readable; figures and columns are not clipped.',
  'Main 9: three new full-task tables retain all six configurations or both transfer variants, task directions/heights, mean/sample SD, units, visible low values and zero SD. No table collisions or edge clipping observed.',
  'Main 10-13: separate historical baseline narrative remains distinct; former p11 overflow is resolved without reducing font or figure scale. Discussion and conclusion preserve the observed negative Full comparisons.',
  'Main 14-15: historical figure and table panels are separated and captions are readable; qualitative panels remain their old fixed baseline example, not new model interpretation.',
  'Main 16: all 41 bibliography entries now flow in two normal full-height columns; no old large empty first column.',
  'Supplement 1-2: query/robustness scope and both complete sensitivity tables readable; seed-1 and percentage/sample-SD limitations visible.',
  'Supplement 3-6: historical tables, figure, protocol appendix and references readable. Final supplement page is sparse but contains its retained cache table and references without overlap.',
  'No visual clipping, overlapping labels or missing cross-reference markers found on the reviewed final pages. Underfull typesetting diagnostics remain in logs; this is not a claim of zero diagnostics.'
 ],
 'new_scientific_validation':False,
 'limits':'Root page-layout review only. Independent content/scalar review is separate; neither is a new model experiment, final submission acceptance, or fresh literature audit.'
}
with (here/'ROOT_VISUAL_REVIEW.json').open('x',encoding='utf-8') as f:
    json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(bind(here/'ROOT_VISUAL_REVIEW.json'),ensure_ascii=False))
