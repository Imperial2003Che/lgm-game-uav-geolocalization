"""Real Windows PID/handle check using only standard-library child processes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'dac_training_control_v2'
sys.path.insert(0, str(SOURCE))
import dac2_gates as gates

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        parent_pid, parent_start, expected_exit = int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
        identity = {'schema': 'dac-actual-worker-identity.v2', 'pid': os.getpid(),
            'started_utc': gates.process_started(os.getpid()),
            'plan_sha256': sha(__file__), 'release_sha256': sha(__file__),
            'lineage': gates.worker_lineage(os.getpid(), parent_pid, parent_start),
            'stdlib_fixture_only_not_a_training_launch': True}
        print(json.dumps(identity), flush=True)
        input()
        return expected_exit
    out = HERE / 'REAL_PROCESS_API_SMOKE_1822.json'
    if out.exists():
        raise RuntimeError('Preserve existing probe output')
    before = {name: sha(SOURCE / name) for name in ('dac2_gates.py', 'dac2_contracts.py', 'run_dac_stage.py')}
    parent = {'pid': os.getpid(), 'started_utc': gates.process_started(os.getpid())}
    results = []
    for expected_exit in (0, 7):
        p = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), 'child',
            str(parent['pid']), parent['started_utc'], str(expected_exit)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
        launcher = worker = None
        try:
            launcher = gates.ProcessObservation(p.pid, existing_handle=p._handle)
            line = p.stdout.readline()
            identity = json.loads(line)
            gates.validate_worker_identity(identity, sha(__file__), sha(__file__), parent,
                {'pid': p.pid, 'started_utc': launcher.started_utc})
            worker = gates.ProcessObservation(identity['pid'])
            assert worker.started_utc == identity['started_utc']
            assert worker.exit_code() == launcher.exit_code() == 259
            assert gates.direct_parent_pid(identity['pid']) == identity['lineage'][0]['parent_process_id']
            stdout, stderr = p.communicate('\n', timeout=30)
            actual_worker_exit = worker.exit_code()
            assert p.returncode == launcher.exit_code() == actual_worker_exit == expected_exit
            results.append({'expected_exit_code': expected_exit, 'popen_pid': p.pid,
                'launcher_started_utc': launcher.started_utc, 'actual_worker_identity': identity,
                'launcher_exit_code': p.returncode, 'actual_worker_exit_code': actual_worker_exit,
                'distinct_launcher_and_worker': p.pid != identity['pid'],
                'stdout_after_handshake': stdout, 'stderr': stderr,
                'retained_handle_verified_running_then_actual_exit': True})
        finally:
            if p.poll() is None:
                p.communicate('\n', timeout=30)
            if worker is not None:
                worker.close()
            if launcher is not None:
                launcher.close()
    assert before == {name: sha(SOURCE / name) for name in before}
    forbidden = [name for name in ('torch', 'numpy', 'PIL', 'scipy', 'cv2', 'transformers') if name in sys.modules]
    assert not forbidden
    report = {'schema': 'actual-dac-windows-process-api-smoke.v1', 'status': 'passed',
        'observed_utc': datetime.now(timezone.utc).isoformat(), 'interpreter': sys.executable,
        'parent': parent, 'source_files_sha256': before, 'script_sha256': sha(__file__),
        'cases': results, 'scientific_imports': forbidden, 'scientific_execution_performed': False,
        'gpu_api_called': False, 'training_plan_or_release_created': False,
        'scope': 'Real ProcessObservation/direct_parent_pid/worker_lineage/validate_worker_identity and controlled exits; no scientific stage.'}
    with out.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'status': 'passed', 'path': str(out), 'sha256': sha(out),
        'cases': len(results), 'exit_codes': [row['actual_worker_exit_code'] for row in results]}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
