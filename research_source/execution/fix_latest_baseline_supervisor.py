"""Apply independently identified lifecycle fixes to the new successor only."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
target=HERE/'supervise_latest_baselines.py'
before=target.read_text(encoding='utf-8')
before_sha=hashlib.sha256(target.read_bytes()).hexdigest()
assert before_sha=='da050479e7d8c3566aec01cdad15ec370c78ea49bce9777e39fa853f457d8b31'
old="        running = bool(kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))) and code.value == 259"
new="        if not kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code)):\n            raise RuntimeError('Cannot query preceding process exit state')\n        running = code.value == 259"
assert before.count(old)==1
result=before.replace(old,new)
start=result.index('def preceding_ready(')
end=result.index('\ndef assert_gpu_idle()',start)
result=result[:start]+'''def preceding_ready(preceding, is_alive=alive, *, expected_plan_sha256):
    if preceding.get('status') != 'registered_extensions_finished_review_pending':
        return False
    if preceding.get('plan_sha256') != expected_plan_sha256:
        raise RuntimeError('The completed predecessor state belongs to another plan')
    jobs = preceding.get('jobs', [])
    if tuple(x.get('id') for x in jobs) != PRECEDING_JOBS or any(x.get('status') != 'completed' or x.get('exit_code') != 0 for x in jobs):
        raise RuntimeError('Preceding ready status lacks four successful extension records')
    if not preceding.get('supervisor_pid') or not preceding.get('supervisor_started_utc'):
        raise RuntimeError('Preceding process identity is missing')
    if is_alive(preceding['supervisor_pid'], preceding['supervisor_started_utc']):
        return False
    execution_pid_keys = {'pid', 'child_pid', 'surviving_child_pid', 'launcher_pid', 'worker_pid', 'training_pid', 'process_id'}
    def any_live_owner(value, inherited_started=None):
        if isinstance(value, list):
            return any(any_live_owner(item, inherited_started) for item in value)
        if not isinstance(value, dict):
            return False
        started = value.get('started_utc', inherited_started)
        for key in execution_pid_keys:
            pid = value.get(key)
            if pid:
                if not started:
                    raise RuntimeError('Preceding child PID has no recorded start time')
                if is_alive(pid, started):
                    return True
        return any(any_live_owner(item, started) for item in value.values() if isinstance(item, (dict, list)))
    if any_live_owner(jobs):
        return False
    if preceding.get('surviving_child_pid'):
        if is_alive(preceding['surviving_child_pid']):
            return False
    return True

''' +result[end:]
old='if preceding_ready(preceding):'
new="if preceding_ready(preceding, expected_plan_sha256=plan['preceding_extension_plan_sha256']):"
assert result.count(old)==1;result=result.replace(old,new)
compile(result,str(target),'exec')
target.write_text(result,encoding='utf-8',newline='\n')
(HERE/'latest_supervisor_lifecycle_fixes.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),result.splitlines(True),fromfile='initial_successor',tofile='reviewed_successor')),encoding='utf-8')
report=dict(before_sha256=before_sha,after_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    fixed=['unknown Windows process exit status raises','predecessor completion bound to the exact registered plan','check predecessor jobs and nested owner PIDs before dispatch'])
(HERE/'latest_supervisor_lifecycle_fixes.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
