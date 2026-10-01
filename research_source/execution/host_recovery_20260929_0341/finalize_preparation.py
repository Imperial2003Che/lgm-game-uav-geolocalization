"""Bind final comment-clarified recovery source and bounded control tests."""
import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
OUT=ROOT/'host_recovery_20260929_0341'
TARGET=ROOT/'restart_after_host_interruption_20260929_v1.ps1'
BASE=ROOT/'restart_after_host_interruption_20260927_v1.ps1'
OLD=OUT/'CANDIDATE_a2bb022ce59f_COMMENT_PRECLARIFICATION.ps1'
CONTROL=OUT/'CONTROL_REVIEW_59deea56a6df_035222064.json'

def binding(path):
    data=path.read_bytes()
    return dict(path=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())

target=binding(TARGET)
assert target['sha256']=='59deea56a6df6ee59282aa50d2612246a0b3e2cb8b9335120af8907f778fdd64'
assert binding(OLD)['sha256']=='a2bb022ce59f6966743281a5b6cfc5d825318cbe376f93faa90a94a286e4edcc'
control=json.loads(CONTROL.read_text(encoding='utf-8-sig'))
assert control['source_sha256']==target['sha256'] and control['passed'] is True and control['passed_count']==49 and control['failed_count']==0
for name,parent in [('FINAL_SOURCE_DIFF.patch',BASE),('COMMENT_CLARIFICATION_DIFF.patch',OLD)]:
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(''.join(difflib.unified_diff(parent.read_text(encoding='utf-8-sig').splitlines(keepends=True),TARGET.read_text(encoding='utf-8-sig').splitlines(keepends=True),fromfile=parent.name,tofile=TARGET.name)))
report=dict(schema='evaluation-host-recovery-final-preparation.v1',created_utc=datetime.now(timezone.utc).isoformat(),target=target,parent_source=binding(BASE),capture=binding(ROOT/'host_interruption_20260929_0341'/'CAPTURE.json'),preservation=binding(OUT/'PRESERVED_INCIDENT.json'),control_review=binding(CONTROL),control_harness=binding(OUT/'review_evaluation_host_controls.ps1'),final_diff=binding(OUT/'FINAL_SOURCE_DIFF.patch'),comment_diff=binding(OUT/'COMMENT_CLARIFICATION_DIFF.patch'),previous_candidate=binding(OLD),previous_preparation_report=binding(OUT/'PREPARATION_REPORT.json'),source_generators=[binding(OUT/name) for name in ['derive_evaluation_recovery.py','derive_control_review.py','evaluation_host_guard.fragment.ps1','finalize_preparation.py']],scope='NEW Sep29 host interruption during SUES content seed1 evaluation; all 42 accepted fits preserved. Original queue, native imports, original completion checks, sources, parameters, shared locks and predecessor checks unchanged.',changes='Replaced obsolete75epoch CPUproof with ROOT42 scope/source bindings and sealed evaluation/metadata stability; ten observed old controllers and unknown creation/interpreter for parent-recorded22496 are treated separately.',exact_original_scientific_command_preserved=True,checkpoint_bytes_read_by_preparation=False,scientific_library_imports=False,wrapper_execution_or_validateonly=False,live_state_moves_or_controller_launches=False,control_simulation_count=49,controls_are_new_bounded_cases_not_full_scientific_validation=True,independent_review_required_before_launch=True)
with (OUT/'FINAL_PREPARATION_REPORT.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps({name:binding(OUT/name)['sha256'] for name in ['FINAL_PREPARATION_REPORT.json','FINAL_SOURCE_DIFF.patch','COMMENT_CLARIFICATION_DIFF.patch','CONTROL_REVIEW_59deea56a6df_035222064.json']},ensure_ascii=False))
