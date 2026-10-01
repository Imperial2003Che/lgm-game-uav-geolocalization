from pathlib import Path
import fitz,json,hashlib,datetime
out=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\camp_dac_root_literal_review_20260930_1353')
source=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\citation_camp_dac_review_20260930_0509\dac.pdf')
assert not (out/'pdf_region_attempt_v1').exists()
a=out/'pdf_region_attempt_v1'; a.mkdir()
doc=fitz.open(source)
records=[]
for page_no,filename in [(8,'DAC_TABLE_II_REGION.png'),(9,'DAC_TABLE_IV_REGION.png')]:
    p=doc[page_no-1]
    clip=fitz.Rect(35,35,p.rect.width-35,310 if page_no==8 else 260)
    pix=p.get_pixmap(matrix=fitz.Matrix(4,4),clip=clip,alpha=False)
    target=a/filename
    pix.save(target)
    raw=target.read_bytes()
    text_path=a/f'DAC_PAGE_{page_no}_TEXT.txt'
    text_raw=p.get_text().encode('utf-8')
    with text_path.open('xb') as f: f.write(text_raw)
    records.append({'physical_page':page_no,'clip_pdf_points':list(clip),'png':{'path':str(target),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'text':{'path':str(text_path),'bytes':len(text_raw),'sha256':hashlib.sha256(text_raw).hexdigest()}})
doc.close()
report={'schema':'author-paper-diagnostic-region-read.v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_pdf_path':str(source),'source_pdf_sha_inherited_not_rehashed':'f3d42d52db272fa1ae931801897daa9f554b757a4ac9b7d644fa1ae79b63cc82','records':records,'scope':'Diagnostic rendering and text reading of two already saved published paper pages, no PDF whole-byte verification; regions preserve original numerals and no scientific model or statistics run.'}
raw=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
with (a/'REGION_READ_REPORT.json').open('xb') as f:f.write(raw)
print(json.dumps({'path':str(a/'REGION_READ_REPORT.json'),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},ensure_ascii=False))