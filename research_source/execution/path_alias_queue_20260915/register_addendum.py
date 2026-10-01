"""Register the reviewed source-path addendum only while both queues are unstarted."""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import json
import os
import subprocess
import compatibility as c
from derive_addendum import once, save_new

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
EXPECTED = '0c4217fefb33d6550bda2300bc201f1c869da0b8d5ff02d45ae7af45b7ef6d70'
REVIEW = '156f472fa681609e0fd9a73c7729ed5acd752aa88099f498b410cc87c8ff32f3'
STATES = {'status.json': '654d4c02b8e7ba51e31b1c612f40b14617bcdb5fceff5d19feb03d32de0155a8',
          'pipeline_status.json': 'daa10a18f78516423c1769bcdf57b712cc643f43ce424828da7a37246acad8ca',
          'extension_status.json': '244eedb4d890d08914bdcf2692b5eaa19a5f60ff5ce9c92d770d89bbc210d226',
          'latest_baseline_status.json': 'c1802da7c5755903c0a7fa482de3edd55883234207d75b8c7def6dfb96ef9270'}

def unstarted(addendum):
    addendum.verify_sources()
    absent = ['independent_comparison_status.json', 'latest_baseline_logs', 'independent_comparison_logs',
              'camp_preparation/results', 'dac_preparation/results', 'camp_independent_evaluation_v3/results',
              'camp_independent_evaluation_v3/runs', 'camp_independent_runs',
              'camp_training_execution_v2/status.json', 'matched_view_execution/status.json']
    for stage in ('primary', 'pipeline', 'extensions', 'latest', 'independent'):
        absent.extend('memory_recovery_20260914_1544/' + stage + suffix
                      for suffix in ('_launch.json', '_launch_intent.json', '.stdout.log', '.stderr.log'))
    for name in absent:
        c.require(not (EXECUTION / name).exists(), 'Execution evidence exists; inspect: ' + name)
    for name, expected in STATES.items():
        c.require(c.sha(EXECUTION / name) == expected, 'Original incident state changed')
    latest = json.loads((EXECUTION / 'latest_baseline_status.json').read_bytes())
    c.require(len(latest['jobs']) == 2 and all(j['status'] == 'pending' for j in latest['jobs']), 'Author jobs were started')
    for job in latest['jobs']:
        for field in ('pid', 'started_utc', 'finished_utc', 'exit_code', 'stdout', 'stderr'):
            c.require(job.get(field) is None, 'Author job has execution evidence')
    query = "@(Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | Select-Object ProcessId,CreationDate,ExecutablePath,CommandLine) | ConvertTo-Json -Compress -Depth 4"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', query],
             capture_output=True, text=True, encoding='utf-8', errors='strict', check=True, timeout=30,
             creationflags=subprocess.CREATE_NO_WINDOW)
    rows = json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(rows, dict): rows = [rows]
    c.require(len(rows) == 1 and rows[0]['ProcessId'] == os.getpid(), 'Another Python owner exists')
    return {'observed_utc': datetime.now(timezone.utc).isoformat(), 'python_processes': rows,
            'state_sha256': STATES, 'absent_execution_evidence': absent, 'no_other_python_owner': True}

def main():
    registration = HERE / 'REGISTRATION.json'
    target = EXECUTION / 'restart_after_memory_incident_1544_path_compat_v1.ps1'
    c.require(not registration.exists() and not target.exists(), 'Existing addendum transaction; inspect without overwrite')
    addendum = c.Addendum(EXPECTED)
    c.require(c.sha(HERE / 'ADDENDUM_REVIEW.json') == REVIEW, 'Reviewed addendum evidence changed')
    original = EXECUTION / 'restart_after_memory_incident_1544.ps1'
    c.require(c.sha(original) == '3239051a4110588a4a00db8888d99cd4d112bf95f2deb1d95b4214969f1f6ff7', 'Original recovery changed')
    before = unstarted(addendum)
    after = unstarted(addendum)
    save_new(registration, {'status': 'registered_execution_addendum_not_launched', 'addendum': addendum.snapshot.artifact(),
               'review_sha256': REVIEW, 'registrar_sha256': c.sha(__file__), 'before': before, 'after': after,
               'original_plan_files_changed': False, 'original_release_files_changed': False,
               'scope': 'Only three source-path evaluation entry adapters; original plan SHA and actual execution addendum are separately recorded.'})
    source = original.read_text(encoding='utf-8-sig')
    revised = once(source, "latest=@('latest_baseline_status.json','supervise_latest_baselines.py'",
                   "latest=@('latest_baseline_status.json','supervise_latest_baselines_path_compat_v1.py'")
    revised = once(revised, "independent=@('independent_comparison_status.json','supervise_independent_comparisons.py'",
                   "independent=@('independent_comparison_status.json','supervise_independent_comparisons_path_compat_v1.py'")
    block = """
# Registered execution addendum, separate from every unchanged science plan.
$addendumPath = Join-Path $executionRoot 'path_alias_queue_20260915/EXECUTION_ADDENDUM.json'
$addendumSha = 'ADDENDUM_SHA'
$addendumRegistration = Join-Path $executionRoot 'path_alias_queue_20260915/REGISTRATION.json'
if ((Sha $addendumPath) -ne $addendumSha -or (Sha $addendumRegistration) -ne 'REGISTRATION_SHA') { throw 'Registered path compatibility addendum changed.' }
$addendum = Get-Content -LiteralPath $addendumPath -Raw | ConvertFrom-Json
foreach ($source in $addendum.files) {
    if ((Sha $source.path) -ne $source.sha256 -or (Get-Item -LiteralPath $source.path).Length -ne $source.bytes) { throw ('Compatibility source changed: '+$source.path) }
}
""".replace('ADDENDUM_SHA', EXPECTED).replace('REGISTRATION_SHA', c.sha(registration))
    revised = once(revised, '$definitions = @{', block + '\n$definitions = @{')
    revised = once(revised, "$stdout = Join-Path $incidentRoot ($Stage+'.stdout.log')",
        "if ($Stage -in @('latest','independent')) { $arguments += ' --addendum-sha256 '+$addendumSha }\n$stdout = Join-Path $incidentRoot ($Stage+'.stdout.log')")
    with target.open('x', encoding='utf-8-sig', newline='\r\n') as stream:
        stream.write(revised)
    with (HERE / 'recovery.patch').open('x', encoding='utf-8') as stream:
        stream.writelines(difflib.unified_diff(source.splitlines(True), revised.splitlines(True), fromfile=original.name, tofile=target.name))
    save_new(HERE / 'RECOVERY_DERIVATION.json', {'source': str(original), 'source_sha256': c.sha(original),
        'target': str(target), 'target_sha256': c.sha(target), 'registration_sha256': c.sha(registration),
        'status': 'derived_waiting_for_control_review', 'real_launches': 0})
    print(json.dumps({'registered_addendum': str(registration), 'registration_sha256': c.sha(registration),
                      'recovery_path': str(target), 'recovery_sha256': c.sha(target), 'real_launches': 0}))

if __name__ == '__main__':
    main()
