"""Render actual newly compiled manuscript PDFs; geometry checks are not visual review."""
from pathlib import Path
import argparse, datetime, hashlib, json, re
import fitz

def binding(p):
    b = p.read_bytes()
    return {'path': str(p.resolve()), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

args = argparse.ArgumentParser()
args.add_argument('--draft', required=True)
args.add_argument('--output', required=True)
options = args.parse_args()
draft = Path(options.draft).resolve()
out = Path(options.output).resolve()
out.mkdir(parents=True, exist_ok=False)
report = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'schema': 'local-working-manuscript-pdf-layout.v1',
          'scope': 'Actual PDF text, font geometry and page rendering; visual review recorded separately.',
          'documents': []}
for name in ('main',):
    pdf = draft/(name+'.pdf')
    doc = fitz.open(pdf)
    item = {'pdf': binding(pdf), 'page_count': len(doc), 'pages': []}
    fulltext = []
    for i, page in enumerate(doc, 1):
        text = page.get_text()
        fulltext.append(text)
        png = out/f'{name}-{i:02d}.png'
        page.get_pixmap(matrix=fitz.Matrix(1.4,1.4), alpha=False).save(png)
        spans = [s for block in page.get_text('dict')['blocks'] if 'lines' in block
                 for line in block['lines'] for s in line['spans'] if s['text'].strip()]
        outside = [s for s in spans if s['bbox'][0] < -0.5 or s['bbox'][1] < -0.5
                   or s['bbox'][2] > page.rect.width+0.5 or s['bbox'][3] > page.rect.height+0.5]
        item['pages'].append({'number':i, 'png':binding(png), 'width_pt':page.rect.width,
                              'height_pt':page.rect.height, 'text_spans':len(spans),
                              'min_font_pt':min((s['size'] for s in spans), default=None),
                              'out_of_page_spans': outside,
                              'unresolved_double_question_marks': text.count('??')})
    (out/(name+'.txt')).write_text('\n\f\n'.join(fulltext), encoding='utf-8')
    item['extracted_text'] = binding(out/(name+'.txt'))
    log = (draft/(name+'.log')).read_text(encoding='utf-8', errors='replace')
    item['latex_diagnostics'] = [line for line in log.splitlines()
                                  if any(t in line for t in ('Overfull', 'Underfull', 'Warning:', 'Undefined', 'undefined'))]
    report['documents'].append(item)
(out/'PDF_LAYOUT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'documents':[{ 'name':Path(d['pdf']['path']).name, 'pages':d['page_count'],
                               'out_of_page_spans':sum(len(p['out_of_page_spans']) for p in d['pages']),
                               'question_marks':sum(p['unresolved_double_question_marks'] for p in d['pages']),
                               'diagnostics':d['latex_diagnostics']} for d in report['documents']]}, ensure_ascii=False))
