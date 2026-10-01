"""Prepare the Sep29 evaluation-interruption control wrapper, never execute it."""
import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
OUT = ROOT / 'host_recovery_20260929_0341'
CAPTURE = ROOT / 'host_interruption_20260929_0341' / 'CAPTURE.json'
CAPTURE_SHA = 'a19eeae091aafdab5791367590e2ac22752d9fc5b57f79c0ddaf090072ee06a0'
BASE = ROOT / 'restart_after_host_interruption_20260927_v1.ps1'
BASE_SHA = 'e4e7fcd529caff3a705273f3ec2c90d2a919c10358b3ac4c9788a6f8afe5c3bc'
TARGET = ROOT / 'restart_after_host_interruption_20260929_v1.ps1'
RUN = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_main\sues200\content\seed_1')
EVAL = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\evaluations\formal_main\sues200\content\seed_1')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def create_json(path, obj):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

assert sha(BASE) == BASE_SHA and sha(CAPTURE) == CAPTURE_SHA
capture = json.loads(CAPTURE.read_text(encoding='utf-8-sig'))
assert capture['schema'] == 'host-interruption-preservation.v2'
assert len(capture['files']) == 42 and capture['active']['pid'] == 22496
assert Path(capture['active']['output_dir']) == EVAL
assert not (EVAL / 'evaluation_manifest.json').exists()
(OUT / 'controllers').mkdir(exist_ok=True)
(OUT / 'training_metadata').mkdir(exist_ok=True)
names = ['status.json', 'pipeline_status.json', 'extension_status.json', 'latest_baseline_status.json', 'independent_comparison_status.json', 'supervise_pipeline.py', 'supervise_extensions.py', 'supervise_latest_baselines.py', 'supervise_independent_comparisons.py']
rows = []
for name in names:
    source = ROOT / name
    backup = OUT / 'controllers' / name
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if name.endswith('.json'):
        captured = [r for r in capture['files'] if r['path'] == str(source)]
        assert len(captured) == 1 and captured[0]['sha256'] == digest and captured[0]['bytes'] == len(data)
    with backup.open('xb') as stream:
        stream.write(data)
    assert sha(source) == sha(backup)
    rows.append(dict(source=str(source), backup=str(backup), sha256=digest, bytes=len(data)))
for name in ['run_manifest.json', 'run_config.json', 'history.json']:
    source = RUN / name
    backup = OUT / 'training_metadata' / name
    data = source.read_bytes()
    with backup.open('xb') as stream:
        stream.write(data)
    assert sha(source) == sha(backup)
    rows.append(dict(source=str(source), backup=str(backup), sha256=sha(backup), bytes=len(data)))
preservation_path = OUT / 'PRESERVED_INCIDENT.json'
create_json(preservation_path, dict(schema='host-recovery-control-preservation.v2', created_utc=datetime.now(timezone.utc).isoformat(), capture_sha256=CAPTURE_SHA, base_script=dict(path=str(BASE), sha256=BASE_SHA), files=rows, note='Byte copies of stale states/controllers and completed source training metadata. No checkpoints opened; no training/evaluation/control process launched.'))

text = BASE.read_text(encoding='utf-8-sig')
text = text.replace("'host_recovery_20260927_2145'", "'host_recovery_20260929_0341'")
text = text.replace("$runRoot = 'C:\\项目\\LGM-GAME-Partner-Delivery-20260724\\lgm_game_pytorch\\runs\\formal_sensitivity\\university1652\\backbone_resnet50\\seed_1'", f"$runRoot = '{RUN}'\n$evaluationRoot = '{EVAL}'")
text = text.replace('b6e037d17f1168025db7af97481ce5551b68573185b4cac9c67b1a04b8ede6b7', sha(preservation_path))
fragment = (OUT / 'evaluation_host_guard.fragment.ps1').read_text(encoding='utf-8-sig')
for marker, value in {'__CAPTURE_SHA__': CAPTURE_SHA, '__CAPTURE_SCHEMA__': capture['schema'], '__CAPTURE_COUNT__': '42', '__ACTIVE_COUNT__': '3'}.items():
    fragment = fragment.replace(marker, value)
fragment = fragment.replace("$rows=@($capture.files | Where-Object { $_.path -eq $expectedPath })", "$rows=@($preservation.files | Where-Object { $_.source -eq $expectedPath })")
start = text.index('# This is a later OS boot')
end = text.index('$pins = @{', start)
text = text[:start] + fragment + '\n' + text[end:]
text = text.replace('checkpoint_proof_sha256=$checkpointProofSha;', "recovery_mode='original_official_evaluation_after_42_complete_fits';")
assert '$checkpointProof' not in text
assert '__CAPTURE_' not in text and '__ACTIVE_COUNT__' not in text
assert str(RUN) in text and str(EVAL) in text
with TARGET.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
with (OUT / 'SOURCE_DIFF.patch').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(''.join(difflib.unified_diff(BASE.read_text(encoding='utf-8-sig').splitlines(keepends=True), text.splitlines(keepends=True), fromfile=BASE.name, tofile=TARGET.name)))
create_json(OUT / 'PREPARATION_REPORT.json', dict(schema='evaluation-host-recovery-preparation.v1', created_utc=datetime.now(timezone.utc).isoformat(), target=dict(path=str(TARGET), sha256=sha(TARGET)), parent_source=dict(path=str(BASE), sha256=BASE_SHA), capture=dict(path=str(CAPTURE), sha256=CAPTURE_SHA), preserved=dict(path=str(preservation_path), sha256=sha(preservation_path)), scope='NEW control wrapper for interrupted SUES content seed1 official evaluation; all 42 accepted fits preserved; original --stage all and full completion gates unchanged.', live_state_changes=False, scientific_imports=False, process_launches=False, validate_only_executed=False, review_status='pending independent static review and mocked control simulations'))
print(json.dumps(dict(target=str(TARGET), sha256=sha(TARGET), preservation_sha256=sha(preservation_path)), ensure_ascii=False))
