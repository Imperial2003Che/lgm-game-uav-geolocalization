"""Produce a fixed SUES seed1 descriptive comparison from the adopted University producer."""
import ast, difflib, hashlib, json
from pathlib import Path

HERE=Path(__file__).parent
BASE=HERE.parent/'robustness_pair_results_20260929/compare_pair.py'
EXPECTED='6e63d5c3a25119089ebc49cfcc39751d71bd63dbd4bf43bd0bf3a523be20fee4'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(BASE)==EXPECTED
original=BASE.read_text(encoding='utf-8-sig')
s=original
def replace(old,new,count=None):
    global s
    n=s.count(old)
    assert n and (count is None or n==count),(old,n,count)
    s=s.replace(old,new)
replace('descriptive University visual/full','descriptive SUES visual/full',1)
replace('robustness_audit_20260929_0946/ROOT_VISUAL1_ADOPTION.json','robustness_sues_visual_audit_20260929_1351/ROOT_SUES_VISUAL1_ADOPTION.json',1)
replace('81ec5d80b7370ae5dc79c3f12e0633b88ade73be3422ec155ea11def68713cc6','a6795283cb384c77732bdb1e63af93d582d7844879f415e45ef38c8861d3af74',1)
begin=s.index('TASKS = {')
end=s.index('\nMETRICS =',begin)
newtasks="TASKS = {\n"+''.join(f"    'sues200_uav_{h}m_to_satellite': (4000, 200),\n    'sues200_satellite_to_uav_{h}m': (80, 10000),\n" for h in (150,200,250,300))+"}"
s=s[:begin]+newtasks+s[end:]
replace("'university1652'","'sues200'")
replace('University-1652, visual and full, seed1 only: 90 corrupted task/condition pairs and 3 clean task pairs.','SUES-200, visual and full, seed1 only: 240 corrupted task/condition pairs and 8 clean task pairs.',1)
replace('The historical initial12 Visual inventory whole-file SHA edge gap and all other limitations in the two adopted root reports remain.','The historical initial12/visual_style1 whole-file SHA edge gaps elsewhere in the global evidence history and all other limitations in the two adopted root reports remain; the two SUES checkpoints have their own specific accepted training authorities.',1)
replace('This two-run comparison does not complete the four-run robustness stage or the seven-stage pipeline.','The four robustness runs were adopted separately. This two-run descriptive comparison does not itself re-audit that stage or complete the seven-stage pipeline.',1)
replace("'robustness_full_audit_20260929_1247'","'robustness_sues_full_audit_20260929_1448'",1)
replace('len(rows) == len(csv_index) == 18','len(rows) == len(csv_index) == 48',1)
replace('len(paired) == 93 and len(flat) == 279','len(paired) == 248 and len(flat) == 744',1)
replace("for r in paired}) == 93","for r in paired}) == 248",1)
replace("'clean_task_pairs': 3, 'corrupted_task_pairs': 90","'clean_task_pairs': 8, 'corrupted_task_pairs': 240")
replace("'metric_rows': 279","'metric_rows': 744",1)
replace('# University-1652 Visual vs Full: seed1 only','# SUES-200 Visual vs Full: seed1 only',1)
replace('There are 3 clean task pairs\nand 90 corrupted task/condition pairs. paired_tasks.json contains 93 paired rows;\npaired_metrics.csv expands them into 279 rows (3 metrics per pair).','There are 8 clean task pairs\nand 240 corrupted task/condition pairs. paired_tasks.json contains 248 paired rows;\npaired_metrics.csv expands them into 744 rows (3 metrics per pair). Four heights\n(150, 200, 250 and 300 m) and both directions remain separate. UAV-to-satellite\ntasks use 4000 queries and 200 gallery images; satellite-to-UAV tasks use 80\nqueries and 10000 gallery images. All 200 gallery identities are retained.',1)
replace("    report = {'schema':", "    derivation_files = [descriptor(HERE / name, (HERE / name).read_bytes()) for name in\n                        ('DERIVATION.json', 'SUES_FROM_UNIVERSITY_SOURCE_DIFF.patch', 'derive_compare_sues.py')]\n    report = {'schema':",1)
replace("        'source': descriptor(__file__, source_data), 'argv': sys.argv,","        'source': descriptor(__file__, source_data), 'argv': sys.argv, 'derivation_files': derivation_files,",1)
replace("        'source': report['source'], 'root_comparison_adoption_pending': True})","        'source': report['source'], 'derivation_files': derivation_files, 'root_comparison_adoption_pending': True})",1)
ast.parse(s)
assert "'university1652'" not in s and 'robustness_full_audit_20260929_1247' not in s
assert 'len(paired) == 248 and len(flat) == 744' in s
assert 'getcontext().prec = 50' in s and "Decimal('5e-16') * scale" in s
p=HERE/'compare_sues_pair.py'
with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
d=HERE/'SUES_FROM_UNIVERSITY_SOURCE_DIFF.patch'
with d.open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile=str(BASE),tofile=str(p))))
record=dict(schema='lgm.robustness.sues-pair-source-derivation.v1',base=dict(path=str(BASE),sha256=EXPECTED),
            derived=dict(path=str(p),sha256=digest(p)),complete_diff=dict(path=str(d),sha256=digest(d)),
            scope=dict(dataset='sues200',seed=1,clean_pairs=8,corrupted_pairs=240,metric_rows=744),
            changes='Own adopted SUES Visual/Full roots, eight exact task scales, 48 drop-CSV keys, 248/744 counts, explicit retained limits. Decimal50 arithmetic, no pooling/inference, serialization tolerances and small-input bounds unchanged.',
            old_scientific_checks_repeated=False,scientific_execution=False)
with (HERE/'DERIVATION.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps(record,ensure_ascii=True))
