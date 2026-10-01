"""Run the registered extension queue after the primary experiment pipeline.

This controller never treats a prepared script or a successful launcher as an
experiment result. Individual runners validate their own evidence and outputs.
"""
from pathlib import Path
import argparse
import ctypes
import datetime
import hashlib
import json
import msvcrt
import os
import re
import subprocess
import time
import traceback

HERE = Path(__file__).resolve().parent
PRECEDING_JOBS = ('formal_aggregate', 'formal_figures', 'cross_dataset_transfer',
                  'robustness', 'robustness_aggregate', 'query_analysis', 'formal_efficiency_component')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, data):
    temporary = path.with_name(path.name + f'.tmp.{os.getpid()}')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def alive(pid, started_utc=None):
    if not pid:
        return False
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = ctypes.c_void_p
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if not handle:
        if kernel.GetLastError() == 5:
            raise RuntimeError('Process status access denied; cannot assume it has exited')
        return False
    code = ctypes.c_ulong()
    try:
        running = bool(kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))) and code.value == 259
        if running and started_utc:
            class FILETIME(ctypes.Structure):
                _fields_ = [('low', ctypes.c_uint32), ('high', ctypes.c_uint32)]
            created, ended, kern, user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
            if not kernel.GetProcessTimes(ctypes.c_void_p(handle), ctypes.byref(created), ctypes.byref(ended), ctypes.byref(kern), ctypes.byref(user)):
                raise RuntimeError('Cannot verify the preceding process identity')
            epoch = ((created.high << 32) | created.low) / 10_000_000 - 11_644_473_600
            declared = datetime.datetime.fromisoformat(started_utc).timestamp()
            # A reused Windows PID must not hold this queue forever.
            if abs(epoch - declared) > 15:
                return False
        return running
    finally:
        kernel.CloseHandle(ctypes.c_void_p(handle))


def entrypoint(job):
    command = job.get('command')
    if not isinstance(command, list) or len(command) < 2 or not all(isinstance(x, str) for x in command):
        raise RuntimeError('Job command must be a structured argument list')
    index = 1
    while index < len(command) and command[index] in ('-B', '-u', '-I'):
        index += 1
    if index >= len(command) or not Path(command[index]).is_file():
        raise RuntimeError('Missing Python entry point')
    return Path(command[index]).resolve()


def runtime_snapshot(python):
    """Read distribution metadata in the actual interpreter; import no libraries."""
    code = (
        'import importlib.metadata as m,json,sys; '
        'rows=sorted((d.metadata.get("Name",""),d.version) for d in m.distributions()); '
        'print(json.dumps({"python":sys.version,"executable":sys.executable,"distributions":rows,'
        '"scientific_modules_imported":[n for n in ("torch","torchvision","numpy","matplotlib","sklearn") if n in sys.modules]},sort_keys=True))'
    )
    completed = subprocess.run([str(python), '-I', '-c', code], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               encoding='utf-8', errors='strict', timeout=60,
                               creationflags=subprocess.CREATE_NO_WINDOW, check=True)
    result = json.loads(completed.stdout)
    if result['scientific_modules_imported']:
        raise RuntimeError('Metadata-only runtime probe unexpectedly imported scientific modules')
    result['interpreter_sha256'] = sha(python)
    return result


def preceding_ready(preceding, is_alive=alive):
    if preceding.get('status') != 'ready_for_extension_preparation':
        return False
    jobs = preceding.get('jobs', [])
    if tuple(x.get('id') for x in jobs) != PRECEDING_JOBS or any(x.get('status') != 'completed' or x.get('exit_code') != 0 for x in jobs):
        raise RuntimeError('Preceding ready status lacks seven successful stage records')
    if not preceding.get('supervisor_pid') or not preceding.get('supervisor_started_utc'):
        raise RuntimeError('Preceding process identity is missing')
    return not is_alive(preceding['supervisor_pid'], preceding['supervisor_started_utc'])


def assert_gpu_idle():
    completed = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name', '--format=csv,noheader,nounits'],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding='utf-8', errors='replace', timeout=30,
                               creationflags=subprocess.CREATE_NO_WINDOW, check=True)
    conflicts = [line for line in completed.stdout.splitlines() if 'python' in line.lower()]
    if conflicts:
        raise RuntimeError('Another Python GPU process is active: ' + '; '.join(conflicts))


def check_plan(plan):
    if plan.get('schema') != 'lgm-extension-queue.v1' or not plan.get('jobs'):
        raise RuntimeError('Invalid or empty extension plan')
    if plan.get('controller_sha256') != sha(Path(__file__)):
        raise RuntimeError('Extension controller changed after registration')
    if plan.get('preceding_status_required') != 'ready_for_extension_preparation':
        raise RuntimeError('Unexpected preceding-pipeline gate')
    identifiers = []
    runtimes = {}
    for job in plan['jobs']:
        if not isinstance(job.get('id'), str) or not re.fullmatch(r'[a-z0-9_]+', job['id']):
            raise RuntimeError('Unsafe or missing job identifier')
        identifiers.append(job['id'])
        script = entrypoint(job)
        if not Path(job['cwd']).is_dir() or not Path(job['command'][0]).is_file():
            raise RuntimeError('Missing runtime or working directory for ' + job['id'])
        if str(script) not in job.get('source_sha256', {}):
            raise RuntimeError('Entry point is not pinned: ' + job['id'])
        for source, fingerprint in job['source_sha256'].items():
            if sha(source) != fingerprint:
                raise RuntimeError('Queued source changed: ' + source)
        python = str(Path(job['command'][0]).resolve())
        if python not in runtimes:
            runtimes[python] = runtime_snapshot(python)
        if job.get('runtime_snapshot') != runtimes[python]:
            raise RuntimeError('Registered Python environment changed: ' + job['id'])
    if len(set(identifiers)) != len(identifiers):
        raise RuntimeError('Repeated job identifiers')


def check_state_jobs(state, plan):
    if len(state.get('jobs', [])) != len(plan['jobs']):
        raise RuntimeError('Persisted job count differs from the registered plan')
    for retained, registered in zip(state['jobs'], plan['jobs']):
        for key, expected in registered.items():
            if key == 'status':
                continue  # A supplied job may describe preparation, while execution tracks pending/running.
            if retained.get(key) != expected:
                raise RuntimeError('Persisted job specification differs from plan: ' + key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=HERE / 'extension_plan.json')
    parser.add_argument('--check-plan', action='store_true')
    args = parser.parse_args()
    plan = read(args.plan)
    check_plan(plan)
    if args.check_plan:
        print(json.dumps({'status': 'valid_cpu_only', 'jobs': [x['id'] for x in plan['jobs']],
                          'plan_sha256': sha(args.plan)}, ensure_ascii=False))
        return
    lock = (HERE / 'extension_supervisor.lock').open('a+b')
    lock.seek(0)
    lock.write(b'0')
    lock.flush()
    lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    path = HERE / 'extension_status.json'
    if path.exists():
        state = read(path)
        if state.get('status') != 'waiting_for_pipeline':
            raise RuntimeError('Inspect existing extension evidence before resuming: ' + str(state.get('status')))
        if state['plan_sha256'] != sha(args.plan):
            raise RuntimeError('Plan changed after queue registration')
    else:
        state = {'schema': 'lgm-extension-execution.v1', 'status': 'waiting_for_pipeline',
                 'created_utc': utc(), 'plan_path': str(args.plan.resolve()), 'plan_sha256': sha(args.plan),
                 'jobs': [{**job, 'status': 'pending'} for job in plan['jobs']],
                 'remaining_work': plan.get('remaining_work', [])}
    check_state_jobs(state, plan)
    state.update(supervisor_pid=os.getpid(), supervisor_started_utc=utc())
    child = None
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        while True:
            preceding = read(HERE / 'pipeline_status.json')
            state.update(heartbeat_utc=utc(), preceding_status=preceding.get('status'))
            save(path, state)
            if preceding.get('status') == 'ready_for_extension_preparation':
                if preceding_ready(preceding):
                    state['preceding_completion_sha256'] = sha(HERE / 'pipeline_status.json')
                    break
            elif preceding.get('status') in ('failed', 'primary_interrupted'):
                state.update(status='preceding_pipeline_interrupted', stopped_utc=utc())
                return
            elif not alive(preceding.get('supervisor_pid'), preceding.get('supervisor_started_utc')):
                state.update(status='preceding_controller_missing', stopped_utc=utc())
                return
            time.sleep(30)
        if sha(args.plan) != state['plan_sha256']:
            raise RuntimeError('Plan changed while waiting')
        check_plan(plan)
        state['status'] = 'running_extensions'
        logs = HERE / 'extension_logs'
        logs.mkdir(exist_ok=True)
        for job in state['jobs']:
            if sha(args.plan) != state['plan_sha256']:
                raise RuntimeError('Plan changed during execution')
            check_plan(plan)
            assert_gpu_idle()
            child = None
            job.update(status='running', started_utc=utc())
            state['active_stage'] = job['id']
            stdout_path = logs / (job['id'] + '.stdout.log')
            stderr_path = logs / (job['id'] + '.stderr.log')
            environment = dict(os.environ)
            environment['PYTHONDONTWRITEBYTECODE'] = '1'
            # Persist launch intent before spawning, so a crashed supervisor cannot
            # restart from a stale waiting state and launch a second experiment.
            save(path, state)
            with stdout_path.open('x', encoding='utf-8') as stdout, stderr_path.open('x', encoding='utf-8') as stderr:
                child = subprocess.Popen(job['command'], cwd=job['cwd'], env=environment,
                                         stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                job.update(pid=child.pid, stdout=str(stdout_path), stderr=str(stderr_path))
                save(path, state)
                while child.poll() is None:
                    state['heartbeat_utc'] = utc()
                    save(path, state)
                    time.sleep(30)
            job.update(exit_code=child.returncode, finished_utc=utc(),
                       status='completed' if child.returncode == 0 else 'failed',
                       stdout_sha256=sha(stdout_path), stderr_sha256=sha(stderr_path))
            save(path, state)
            if child.returncode:
                raise RuntimeError('Extension failed; inspect retained outputs: ' + job['id'])
            check_plan(plan)
        state.update(status='registered_extensions_finished_review_pending', finished_utc=utc())
        state.pop('active_stage', None)
    except BaseException as error:
        state.update(status='failed', error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc(), stopped_utc=utc())
        if child is not None and child.poll() is None:
            state['surviving_child_pid'] = child.pid
            state['recovery_note'] = 'The child is still running. Do not relaunch; inspect this PID and its retained logs first.'
        raise
    finally:
        save(path, state)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == '__main__':
    main()
