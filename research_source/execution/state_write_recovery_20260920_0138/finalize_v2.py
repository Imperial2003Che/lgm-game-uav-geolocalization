from pathlib import Path
import json,hashlib
E=Path(__file__).resolve().parent.parent
I=Path(__file__).resolve().parent
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
p=E/'restart_after_state_write_incident_20260920_v1.ps1'
t=p.read_text(encoding='utf-8-sig')
with (I/'before_io_v2.ps1').open('x',encoding='utf-8-sig') as f:f.write(t)
t=t.replace("if ($Value -is [DateTime])", "if ($Value -is [DateTimeOffset]) { return $Value }\n    if ($Value -is [DateTime])")
t=t.replace('run_controller_with_state_retry.py','run_controller_with_state_retry_v2.py')
t=t.replace('state_io_retry_20260920/SOURCE_MANIFEST.json','state_io_retry_20260920_v2/SOURCE_MANIFEST.json')
t=t.replace('3519d4b5ddcc6252fb6e1d2ed164d7eda0f4ef6ec8f8b7baa87c60382dacdc4f','d8e6209f5ff2c2180d053e6444cb7df6ec0846405fea7ad6dee9b76a8fcb8dfb')
out=I/'bound_provenance';out.mkdir()
rows=[]
for rel in ['run_controller_with_state_retry_v2.py','state_io_retry_20260920_v2/SOURCE_MANIFEST.json','state_io_retry_20260920_v2/resilient_state.py','state_retry_independent_review_20260920/INDEPENDENT_V2_TARGETED_REVIEW.json','status_write_incident_20260920_0138/COMPLETED_FIT_REVIEW_20260920.json']:
    src=E/rel;dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open('xb') as f:f.write(src.read_bytes())
    rows.append(dict(source=str(src),backup=str(dst),sha256=sha(dst),bytes=dst.stat().st_size))
binding=I/'BOUND_PROVENANCE.json'
with binding.open('x',encoding='utf-8') as f:json.dump(dict(schema='recovery-control-provenance.v1',files=rows),f,indent=2,ensure_ascii=False)
block="""$boundProvenancePath = Join-Path $incidentRoot 'BOUND_PROVENANCE.json'
if ((Sha $boundProvenancePath) -ne 'BINDING_SHA') { throw 'Recovery control provenance changed.' }
$boundProvenance = Get-Content -LiteralPath $boundProvenancePath -Raw | ConvertFrom-Json
foreach ($row in $boundProvenance.files) {
    if ((Sha $row.backup) -ne $row.sha256 -or (Get-Item -LiteralPath $row.backup).Length -ne $row.bytes) { throw 'Preserved recovery control source changed.' }
}

""".replace('BINDING_SHA',sha(binding))
t=t.replace('$definitions = @{',block+'$definitions = @{',1)
with p.open('w',encoding='utf-8-sig',newline='') as f:f.write(t.replace('\n','\r\n'))
h=I/'review_recovery.ps1';s=h.read_text(encoding='utf-8-sig')
with (I/'review_before_v2.ps1').open('x',encoding='utf-8-sig') as f:f.write(s)
s=s.replace('run_controller_with_state_retry.py','run_controller_with_state_retry_v2.py')
h.write_text(s,encoding='utf-8-sig')
print(json.dumps(dict(script_sha256=sha(p),binding_sha256=sha(binding))))
