"""Independent control-only reproduction. Does not load or launch controllers."""
import contextlib
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
source = EXECUTION / 'state_io_retry_20260920/resilient_state.py'
fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()
assert fingerprint == '57d323af704a3d80c1cbb880cb75ac9f83462dec09d9f4e2a86a04a5976e00fe'
spec = importlib.util.spec_from_file_location('independent_resilient_state', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
calls = []
def writer(path, state):
    calls.append('writer')
    error = PermissionError('synthetic original state publication denial')
    error.winerror = 5
    raise error
class FailingStderr:
    def write(self, value):
        raise OSError('synthetic independent stderr sink failure')
    def flush(self):
        raise OSError('synthetic independent stderr sink failure')
def sleeper(seconds):
    calls.append('retry_sleep')
    raise AssertionError('This reproduction expects diagnostic failure before retry')
wrapped = module.wrap(writer, diagnostic_path=HERE, provenance={'review':'control-only'}, sleeper=sleeper)
failure = None
with contextlib.redirect_stderr(FailingStderr()):
    try:
        # Directory is not a writable JSONL file. No existing file is modified.
        wrapped(HERE / 'not_created_status.json', {})
    except OSError as error:
        failure = {'type': type(error).__name__, 'text': str(error)}
assert failure is not None and calls == ['writer']
assert not (HERE / 'not_created_status.json').exists()
report = {
    'scope':'Independent standard-library synthetic control reproduction; no science or actual controller launch',
    'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source':str(source),'source_sha256':fingerprint,
    'calls':calls,'escaped_error':failure,
    'original_windows5_retry_bypassed_by_fallback_stderr_error':True,
    'existing_reports_or_states_modified':False,
    'scientific_modules_imported':[n for n in sys.modules if n.split('.')[0] in ('torch','numpy','PIL','matplotlib')],
}
report_path = HERE / 'DIAGNOSTIC_FALLBACK_REPRODUCTION.json'
with report_path.open('x',encoding='utf-8') as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=False))
