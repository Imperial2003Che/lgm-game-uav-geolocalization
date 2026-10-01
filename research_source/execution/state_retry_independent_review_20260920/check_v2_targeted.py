"""Narrow independent checks for the diagnostic fix and new entry identity."""
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
EXPECTED = 'd8e6209f5ff2c2180d053e6444cb7df6ec0846405fea7ad6dee9b76a8fcb8dfb'
manifest_path = EXECUTION / 'state_io_retry_20260920_v2/SOURCE_MANIFEST.json'
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == EXPECTED
entry = EXECUTION / 'run_controller_with_state_retry_v2.py'
old_entry = EXECUTION / 'run_controller_with_state_retry.py'
assert entry.read_text() == old_entry.read_text().replace("PACKAGE=HERE/'state_io_retry_20260920'", "PACKAGE=HERE/'state_io_retry_20260920_v2'")
old = (EXECUTION / 'state_io_retry_20260920/resilient_state.py').read_text()
new = (EXECUTION / 'state_io_retry_20260920_v2/resilient_state.py').read_text()
before = "            print(line.rstrip(),file=sys.stderr,flush=True)"
after = """            try:
                print(line.rstrip(),file=sys.stderr,flush=True)
            except (OSError, ValueError):
                # A denied or closed diagnostic stream must not abandon the
                # original writer's retry or the controller's active child.
                # This diagnostic cannot be retained if both sinks fail.
                pass"""
assert new == old.replace(before, after)
checks = ['entry_only_selects_version2_package', 'retry_only_changes_diagnostic_fallback_protection']
spec = importlib.util.spec_from_file_location('independent_io_entry_v2', entry)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.verify(EXPECTED)
checks.append('manifest_and_all11_sources_verified')

class FailingStderr:
    def write(self, value): raise OSError('synthetic stderr failure')
    def flush(self): raise OSError('synthetic stderr failure')

recovered = []
for label, sink in [('oserror', FailingStderr()), ('closed_stream', io.StringIO())]:
    if label == 'closed_stream': sink.close()
    calls, sleeps = [], []
    def writer(path, state):
        calls.append('writer')
        if len(calls) == 1:
            error = PermissionError('synthetic original publication denial')
            error.winerror = 5
            raise error
        return 'published_by_original_writer'
    wrapped = module.wrap(writer, diagnostic_path=HERE, provenance={'role':'synthetic_check'}, sleeper=sleeps.append)
    with contextlib.redirect_stderr(sink):
        result = wrapped(HERE / 'not_created_status_v2.json', {})
    assert result == 'published_by_original_writer' and calls == ['writer', 'writer'] and sleeps == [0.1]
    recovered.append({'stderr_case':label,'writer_calls':len(calls),'sleeps':sleeps,'returned_original_result':True})
    checks.append('both_diagnostic_sinks_fail_and_original_writer_recovers_'+label)

plain = PermissionError('non-Windows PermissionError must propagate unchanged')
def non_windows_writer(path, state): raise plain
wrapped = module.wrap(non_windows_writer, diagnostic_path=HERE, provenance={}, sleeper=lambda n: (_ for _ in ()).throw(AssertionError('must not sleep')))
try:
    wrapped(HERE / 'not_created_plain_error.json', {})
except PermissionError as error:
    assert error is plain
else: raise AssertionError('Wrong exception was swallowed')
checks.append('non_windows_permission_propagates_unchanged')

roles = []
for role in module.TARGETS:
    controller = module.load(role, EXPECTED)
    target = EXECUTION / module.TARGETS[role]
    assert Path(controller.__file__).samefile(target)
    if role == 'extensions':
        controller = controller.load_controller('b985182c80577fa1a98a7511ce5de2a6a360f908ab063d6f6a0e5a2395be3640')
        assert Path(controller.__file__).samefile(EXECUTION / 'supervise_extensions.py')
    assert controller.main.__globals__['save'] is controller.save
    closure = dict(zip(controller.save.__code__.co_freevars, (x.cell_contents for x in controller.save.__closure__)))
    provenance = closure['provenance']
    assert provenance['role'] == role and provenance['sha256'] == EXPECTED
    assert Path(provenance['actual_controller_entry']).samefile(entry)
    assert Path(provenance['original_controller']).samefile(target)
    assert closure['writer'] is controller.save.__wrapped__
    roles.append({'role':role, 'loaded_original_file':controller.__file__, 'entry':provenance['actual_controller_entry'], 'save_lookup_and_original_writer_retained':True})
    checks.append('new_entry_'+role+'_load_save_and_provenance')
scientific = [n for n in sys.modules if n.split('.')[0] in ('torch','numpy','PIL','matplotlib','scipy','torchvision')]
assert scientific == []
checks.append('no_scientific_imports')
assert not (HERE / 'not_created_status_v2.json').exists()
assert not (HERE / 'not_created_plain_error.json').exists()
report = {
    'schema':'independent-state-io-v2-targeted-review.v1',
    'status':'passed', 'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope':'Narrow version2 diff, synthetic both-destination failures, wrong-error propagation, and changed-entry load/provenance smoke; no live controller or scientific job launch',
    'manifest_sha256':EXPECTED,'checks':checks,'count':len(checks),
    'recovery_cases':recovered,'roles':roles,'scientific_modules_imported':scientific,
    'prior17_tests_not_repeated':True,
    'limitation':'When both diagnostic destinations fail, those diagnostic messages can be lost; original state publication still blocks and retries.',
    'existing_states_and_original_sources_modified':False,
}
with (HERE / 'INDEPENDENT_V2_TARGETED_REVIEW.json').open('x',encoding='utf-8') as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=False))
