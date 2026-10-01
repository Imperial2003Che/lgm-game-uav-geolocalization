from pathlib import Path
import csv,io,json,hashlib,difflib,datetime,os,re
EX=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
OUT=EX.parent
HERE=EX/'camp_dac_root_literal_review_20260930_1353'
OLD=EX/'citation_camp_dac_review_20260930_0509'
PINS={}
def bind(path,cap=200000):
    path=Path(path); n=path.stat().st_size
    if n>cap: raise ValueError('bounded input size exceeded')
    raw=path.read_bytes()
    if len(raw)!=n: raise ValueError('read changed size')
    d={'path':str(path),'bytes':n,'sha256':hashlib.sha256(raw).hexdigest()}
    PINS[str(path)]=d
    return raw,d
def write_new(path,raw):
    with Path(path).open('xb') as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def js(obj):return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
if (HERE/'ROOT_CAMP_DAC_LITERAL_ADOPTION.json').exists():raise ValueError('report already exists; no replay')
old_bytes,old_desc=bind(OLD/'AUTHOR_REPORTED_ROWS.csv')
assert old_desc=={'path':str(OLD/'AUTHOR_REPORTED_ROWS.csv'),'bytes':6440,'sha256':'8982e329fdd88035a726b9276cdd2cc80523037525e0a243dc4941283e123e0a'}
rows=list(csv.DictReader(io.StringIO(old_bytes.decode('utf-8'))))
assert len(rows)==36
# Literal observations entered by root after actual original six-page image review.
# Direction order within each eight-row group is D2S150/200/250/300 then S2D150/200/250/300.
groups=[
('CAMP','I','7','University same-domain', '94.46 95.38 96.15 92.72'),
('CAMP','II','8','SUES same-domain', '95.40 96.38 97.63 98.16 98.05 98.45 99.33 99.46 96.25 93.69 97.50 96.76 98.75 98.10 100.00 98.85'),
('CAMP','III','9','University-to-SUES transfer', '78.90 82.38 86.83 89.28 91.95 93.63 95.68 96.65 87.50 78.98 95.00 87.05 95.00 91.05 96.25 93.44'),
('DAC','I','7','University same-domain', '94.67 95.50 96.43 93.79'),
('DAC','II','8','SUES same-domain', '96.80 97.54 97.48 97.97 98.20 98.62 97.58 98.14 97.50 94.06 98.75 96.66 98.75 98.09 98.75 97.87'),
('DAC','IV','9','University-to-SUES transfer', '76.65 80.56 86.45 89.00 92.95 94.18 94.53 95.45 87.50 79.87 96.25 88.98 95.00 92.81 96.25 94.00')]
visual_rows=[]
for method,table,page,scope,values in groups:
    nums=values.split();count=len(nums)//2
    assert count in (2,8)
    for i in range(count):
        direction='drone_to_satellite' if i<count//2 else 'satellite_to_drone'
        height='' if count==2 else str([150,200,250,300][i%4])
        visual_rows.append({'method':method,'table':table,'physical_pdf_page':page,'scope':scope,'retrieval_direction':direction,'height_m':height,'R_at_1_percent_as_printed':nums[i*2],'AP_percent_as_printed':nums[i*2+1]})
assert len(visual_rows)==36
mismatches=[]
for i,(r,v) in enumerate(zip(rows,visual_rows)):
    assert all(r[k]==v[k] for k in ('method','table','physical_pdf_page','scope','retrieval_direction','height_m'))
    assert r['result_origin']=='published_author_report_only' and r['project_result']=='False' and r['project_reproduction_pass']=='False'
    for k in ('R_at_1_percent_as_printed','AP_percent_as_printed'):
        if r[k]!=v[k]:mismatches.append({'csv_row_one_based_excluding_header':i+1,'key':{x:v[x] for x in ('method','table','physical_pdf_page','scope','retrieval_direction','height_m')},'field':k,'old_literal':r[k],'observed_literal':v[k]})
assert len(mismatches)==1 and mismatches[0]['csv_row_one_based_excluding_header']==30
assert mismatches[0]['old_literal']=='89.90' and mismatches[0]['observed_literal']=='89.00'
old_line=b'DAC,published_author_report_only,University-to-SUES transfer,drone_to_satellite,200,86.45,89.90,IV,9,'
new_line=old_line.replace(b'89.90',b'89.00')
assert old_bytes.count(old_line)==1
new_bytes=old_bytes.replace(old_line,new_line)
assert len(new_bytes)==len(old_bytes) and sum(a!=b for a,b in zip(new_bytes,old_bytes))==1
new_rows=list(csv.DictReader(io.StringIO(new_bytes.decode('utf-8'))))
for r,v in zip(new_rows,visual_rows):assert all(r[k]==v[k] for k in v)
assert b',300,97.58,98.14,II,8,' in new_bytes
corrected_desc=write_new(HERE/'AUTHOR_REPORTED_ROWS_ROOT_CORRECTED.csv',new_bytes)
diff=''.join(difflib.unified_diff(old_bytes.decode('utf-8').splitlines(True),new_bytes.decode('utf-8').splitlines(True),fromfile=str(OLD/'AUTHOR_REPORTED_ROWS.csv'),tofile=str(HERE/'AUTHOR_REPORTED_ROWS_ROOT_CORRECTED.csv')))
diff_desc=write_new(HERE/'ONE_FIELD_LITERAL.diff',diff.encode('utf-8'))
for name in ('CAMP_DAC_CITATION_REVIEW.json','DELIVERY.json','LOCAL_INPUTS.json'):
    bind(OLD/name)
inv_raw,_=bind(EX/'camp_dac_root_table_read_scope_20260930_1343'/'TABLE_READ_SCOPE.json')
inv=json.loads(inv_raw)
preview_bindings=[]
for p in inv['table_pages_for_root_actual_visual_review']:
    inherited=p['rendered_table_page_descriptor_inherited_not_read_or_rehashed']
    _,current=bind(inherited['path'],cap=2000000)
    assert current==inherited
    preview_bindings.append({'method':p['method'],'physical_page':p['physical_pdf_page'],'table':p['table'],'actual_root_original_image_view':True,'current_descriptor':current,'printed_header': 'article5637614' if p['method']=='CAMP' else str(13270+p['physical_pdf_page'])})
region_raw,_=bind(HERE/'pdf_region_attempt_v1'/'REGION_READ_REPORT.json')
region=json.loads(region_raw)
for r in region['records']:
    for k in ('png','text'):
        raw,current=bind(r[k]['path'],cap=500000)
        assert current==r[k]
        if k=='text':assert '98.14' not in raw.decode('utf-8') and '89.00' not in raw.decode('utf-8')
indraw,inddesc=bind(EX/'camp_dac_literal_delta_review_20260930_1349'/'DELTA_REVIEW.json')
ind=json.loads(indraw)
assert ind['correction_count']==1 and ind['findings'][0]['independent_original_PNG_pixel_literal']=='98.14' and ind['findings'][1]['independent_original_PNG_pixel_literal']=='89.00'
bind(EX/'camp_dac_literal_delta_review_20260930_1349'/'DAC_TWO_TABLE_CLIPPED_TEXT.json')
bind(HERE/'render_diagnostic_regions.py')
# Only current main/refs source binding and absence check; no repeat of484scalar/old compile suite.
ms=OUT/'manuscript_citation_revision_20260930_0520'/'manuscript'
ms_records=[]
for name in ('main.tex','refs.bib'):
    raw,d=bind(ms/name)
    hits=[m.group(0) for m in re.finditer(rb'\b(?:CAMP|DAC)\b',raw,re.I)]
    assert not hits
    ms_records.append({'descriptor':d,'literal_CAMP_or_DAC_token_count':len(hits)})
assert (OLD/'AUTHOR_REPORTED_ROWS.csv').read_bytes()==old_bytes
report={
'schema':'camp-dac-root-literal-transcription-adoption.v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
'scope':'First root actual visual review of six saved paper table pages,36 own-method rows72 literal R@1/AP values; new corrected literature CSV only. No scientific experiment, fresh full-paper validator, existing manuscript revision, figure or Overleaf delivery.',
'method':'Root AI actual tools.view_image detail original for six existing pages and two new high-resolution unmodified PDF diagnostic regions; not human review. Manual numeric strings above independently entered from visible rows, then exact string comparison and one-byte correction. Independent AI reviewed only the two initially suspected DAC AP fields.',
'root_visual_page_count':6,'root_diagnostic_region_count':2,'own_method_row_count':36,'literal_values_checked':72,'old_literal_matches':71,'confirmed_transcription_error_count':1,'corrected_literal_matches':72,
'findings':mismatches,
'initial_suspicion_not_a_source_error':{'field':'DAC TableII300m D2S AP','root_initial_small_preview_candidate':'94.14','independent_saved_pixel_observation':'98.14','root_actual_high_resolution_pdf_region_observation':'98.14','final':'98.14 kept; initial94.14 reading was unsupported and not published or written into corrected CSV'},
'visual_source_pages':preview_bindings,'observed_numeric_rows':visual_rows,
'source_PDF_byte_authority':'Both PDF descriptors are inherited from prior source research; neither PDF rehashed. DAC was opened only to read physical p8/p9 regions and text. Current selected PNG byte checks do not prove current full PDF bytes or original render provenance independently.',
'pdf_text_limitation':'Both root full-page text reads and independent clipped text omit the target table numerals. Text is not numeric corroboration. Confirmation comes from actual saved PNG and newly rendered unmodified PDF-region pixels.',
'paper_heading_correction':'CAMP physical page ordinals7/8/9 are distinct from visible repeated article header5637614; inventory printed_page7/8/9 is not asserted as printed pagination by this root.',
'outputs':[corrected_desc,diff_desc],
'independent_two_field_review':inddesc,'current_main_and_refs_only':ms_records,
'old_CSV_and_reports_preserved':True,'old_CSV_bytes_checked_unchanged_after_new_write':True,
'input_bindings':list(PINS.values()),
'adoption':{'literature_literal_table_only':True,'source_research_report_all_claims_adopted':False,'full_bibliography_validated':False,'scientific_result_adopted':False,'original_scientific_environment_validated':False,'scientific_execution_released':False,'B1_admitted':False,'T6_completed':False,'manuscript_revised':False,'Overleaf_updated':False},
'limitations':[
'Published own-method point reports remain distinct from project author-weight re-evaluation and independent training; no street rows, three-seed mean/SD, pooling, CI or significance are inferred.',
'TableII is same-domain SUES, CAMPTableIII/DACTableIV is University-trained to SUES controlled-transfer literature. Current authorUniversity checkpoints onSUES cannot establish TableII reproduction or matched papertransfer protocol.',
'AuthorAP label retained; equality to project cosine/stable-tie/full-gallery/trapezoidal mAP is not established. No frozen scientific parameter/checkpoint/data/source command changed.',
'CAMP batch24 inIV-B and48 incontrolledtransfer, one-epoch paperwarmup versus pinned0.1totalsteps remain separate. DAC paper24drone+24sat=48images,10%warmup/ImageNet22k remains a paperclaim, not localweights provenance.',
'DAC weatherTableIII and CAMP parameter/inferenceTableIV were not adopted in this72value scope.',
'No existing manuscript CAMP/DAC literal attribution was present in current selectedmain/refs; this correction affects a future literature research table. PDFs/ZIP/Overleaf not changed. All projectFull negative results and historical source-chain/model/fullranking/AP/resampling limitations continue.',
'Counts are transcription/association checks, not scientific suite checks or model accuracy acceptance.']}
report_desc=write_new(HERE/'ROOT_CAMP_DAC_LITERAL_ADOPTION.json',js(report))
print(json.dumps({'report':report_desc,'corrected_CSV':corrected_desc,'diff':diff_desc,'literal_values':72,'errors_corrected':1,'selected_input_bindings':len(PINS)},ensure_ascii=False))