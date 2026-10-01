"""Serialize the verified post-training stages; preserve a durable execution record."""
from pathlib import Path
import argparse, ctypes, datetime, hashlib, json, msvcrt, os, subprocess, time

HERE = Path(__file__).resolve().parent
ROOT = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
PYTHON = Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe')
EXP = ROOT / 'lgm_game_pytorch' / 'experiments'
U = Path(r'C:\项目\IMTMN\datasets\University-1652')
S = Path(r'C:\项目\IMTMN\datasets\SUES-200')

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
def save(p, data):
    temp = p.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, p)

def jobs():
    common = ['--delivery-root', str(ROOT)]
    data = common + ['--university-root', str(U), '--sues-root', str(S)]
    specifications = [
        ('formal_aggregate', 'aggregate_frozen_formal_results.py', common),
        ('formal_figures', 'plot_frozen_formal_results.py', ['--output-dir', str(HERE.parent / 'formal_results')]),
        ('cross_dataset_transfer', 'run_transactions_t3_transfer_matrix.py', data + ['--python', str(PYTHON), '--stage', 'evaluate']),
        ('robustness', 'run_frozen_robustness_matrix.py', data + ['--python', str(PYTHON), '--stage', 'run']),
        ('robustness_aggregate', 'aggregate_formal_robustness.py', data),
        ('query_analysis', 'run_transactions_query_analysis.py', data),
        ('formal_efficiency_component', 'run_transactions_formal_efficiency.py', data),
    ]
    return [{'id': name, 'command': [str(PYTHON), str(EXP/script)] + args,
             'entrypoint_sha256': sha(EXP/script), 'status': 'pending'}
            for name, script, args in specifications]

def pid_alive(pid):
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = ctypes.c_void_p
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if not handle: return False
    code = ctypes.c_ulong()
    try:
        return bool(kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))) and code.value == 259
    finally: kernel.CloseHandle(ctypes.c_void_p(handle))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--print-plan', action='store_true')
    args = parser.parse_args()
    if args.print_plan:
        print(json.dumps(jobs(), ensure_ascii=False, indent=2)); return
    lock = (HERE/'supervisor.lock').open('a+b')
    lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    path = HERE/'pipeline_status.json'
    if path.exists():
        state = read(path)
        if state.get('status') not in ['waiting_for_primary', 'primary_interrupted']:
            raise RuntimeError('Existing pipeline requires inspection before resumption: '+str(state.get('status')))
        expected = jobs()
        if [(j.get('id'), j.get('command'), j.get('entrypoint_sha256')) for j in state.get('jobs', [])] != [(j['id'], j['command'], j['entrypoint_sha256']) for j in expected]:
            raise RuntimeError('Stored unstarted pipeline differs from the reviewed baseline-environment commands; archive the old state before recreating it')
    else:
        state = {'schema':'lgm-evidence-pipeline.v1', 'created_utc':utc(), 'status':'waiting_for_primary',
                 'jobs':jobs(), 'remaining_preparation':[
                     'T1 actual GPU feasibility profiles and seven independent baseline fits with 70 task evaluations',
                     'T2 24 leave-one-height-out fits and a complete held-out evaluator',
                     'Newest executable literature baselines under separately documented protocols',
                     'Real descriptor and gradient-based heatmap figures; final manuscript integration and Overleaf upload']}
    state.update(supervisor_pid=os.getpid(), supervisor_started_utc=utc())
    # Temporary execution request belongs to this process; it is released on exit.
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        while True:
            primary = read(HERE/'status.json')
            state.update(heartbeat_utc=utc(), primary_status=primary.get('status'),
                         primary_progress=primary.get('active_progress'))
            if primary.get('status') == 'completed': break
            if primary.get('status') == 'failed' or not pid_alive(primary.get('controller_pid', 0)):
                state.update(status='primary_interrupted', stopped_utc=utc())
                save(path, state); return
            save(path, state); time.sleep(30)
        state['status'] = 'running_post_training'
        for job in state['jobs']:
            if job['status'] == 'completed': continue
            script = Path(job['command'][1])
            if sha(script) != job['entrypoint_sha256']:
                raise RuntimeError('Queued source changed: '+str(script))
            if pid_alive(primary.get('controller_pid', 0)):
                # Completion status is written by the original process just before it exits.
                time.sleep(5)
                if pid_alive(primary['controller_pid']):
                    raise RuntimeError('Primary controller still alive after completion; inspect before next GPU job')
            logs = HERE/'stage_logs'; logs.mkdir(exist_ok=True)
            job.update(status='running', started_utc=utc())
            state['active_stage'] = job['id']
            with (logs/(job['id']+'.stdout.log')).open('a',encoding='utf-8') as out, (logs/(job['id']+'.stderr.log')).open('a',encoding='utf-8') as err:
                child = subprocess.Popen(job['command'], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                job['pid'] = child.pid
                while child.poll() is None:
                    state['heartbeat_utc'] = utc(); save(path, state); time.sleep(30)
            job.update(exit_code=child.returncode, finished_utc=utc(), status='completed' if child.returncode==0 else 'failed')
            save(path, state)
            if child.returncode:
                raise RuntimeError('Stage failed; outputs retained for diagnosis: '+job['id'])
        state.update(status='ready_for_extension_preparation', ready_utc=utc())
        state.pop('active_stage', None)
    except BaseException as exc:
        state.update(status='failed', error=f'{type(exc).__name__}: {exc}', stopped_utc=utc())
        raise
    finally:
        save(path, state)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

if __name__ == '__main__': main()
