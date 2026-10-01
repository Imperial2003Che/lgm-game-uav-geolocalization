"""Regression of the real failure control flow with stdlib fake arrays only."""
from __future__ import annotations
import ast
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bindings as b
import native_ops as n

class FakeArray:
    def __init__(self, values, *, shape=(1, 2), dtype='float32'):
        self.values = list(values)
        self.shape, self.dtype = tuple(shape), dtype
    def __sub__(self, other):
        return FakeArray([a - c for a, c in zip(self.values, other.values)], shape=self.shape, dtype=self.dtype)
    def __ne__(self, other):
        return [a != c for a, c in zip(self.values, other.values)]
    def max(self):
        return max(self.values)
    def copy(self):
        return FakeArray(self.values, shape=self.shape, dtype=self.dtype)

class FakeNumpy:
    @staticmethod
    def array_equal(a, c):
        return a.shape == c.shape and a.values == c.values
    @staticmethod
    def abs(value):
        return FakeArray([abs(x) for x in value.values], shape=value.shape, dtype=value.dtype)
    @staticmethod
    def count_nonzero(values):
        return sum(bool(x) for x in values)

class ParityError(RuntimeError):
    pass

checks = []
def ok(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append({'check': name, 'passed': True})

def get_failure(context, actual, expected):
    try:
        n.descriptor_parity(context, actual, expected, 'stdlib fixture only')
    except ParityError as error:
        return error
    raise AssertionError('Actual descriptor_parity did not reject fixture mismatch')

class FakeImage:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def convert(self, mode):
        return self
    def close(self):
        pass

class FakeInput:
    def unsqueeze(self, dimension):
        return self
    def pin_memory(self):
        return self
    def to(self, **kwargs):
        return self

def main():
    k = b.common()
    ctx = SimpleNamespace(runtime=SimpleNamespace(numpy=FakeNumpy()),
                          components=SimpleNamespace(MeasurementError=ParityError))
    a, e = FakeArray([1.0, 2.0]), FakeArray([1.0, 3.0])
    failure = get_failure(ctx, a, e)
    ok('real parity value failure carries actual array', failure.actual_descriptor_array.values == [1.0, 2.0])
    ok('real parity value failure carries expected array', failure.expected_descriptor_array.values == [1.0, 3.0])
    ok('actual array is independently copied', failure.actual_descriptor_array is not a and failure.actual_descriptor_array.values is not a.values)
    ok('expected array is independently copied', failure.expected_descriptor_array is not e and failure.expected_descriptor_array.values is not e.values)
    ok('failure metadata retains exact difference', failure.evidence['different_element_count'] == 1 and failure.evidence['max_abs_difference'] == 1.0)
    a.values[1] = 99.0
    e.values[1] = -99.0
    ok('mutating caller arrays does not alter failure arrays', failure.actual_descriptor_array.values == [1.0, 2.0] and failure.expected_descriptor_array.values == [1.0, 3.0])
    serialized = json.dumps(failure.evidence, allow_nan=False)
    ok('JSON evidence contains no fake/real array objects', json.loads(serialized) == failure.evidence)
    dtype_failure = get_failure(ctx, FakeArray([1, 2], dtype='float32'), FakeArray([1, 2], dtype='float64'))
    ok('dtype mismatch preserves original dtypes separately', dtype_failure.actual_descriptor_array.dtype == 'float32' and dtype_failure.expected_descriptor_array.dtype == 'float64')
    shape_failure = get_failure(ctx, FakeArray([1, 2], shape=(1, 2)), FakeArray([1, 2], shape=(2, 1)))
    ok('shape mismatch preserves original shapes separately', shape_failure.actual_descriptor_array.shape == (1, 2) and shape_failure.expected_descriptor_array.shape == (2, 1))
    ok('shape mismatch metadata remains JSON serializable', isinstance(json.dumps(shape_failure.evidence), str))
    passed = n.descriptor_parity(ctx, FakeArray([1, 2]), FakeArray([1, 2]), 'unchanged pass fixture')
    ok('successful exact comparison still returns passing metadata', passed['passed'] and passed['max_abs_difference'] == 0)

    # Execute actual measure_sample until its first parity fails. All upstream
    # image/model operations are stdlib stand-ins; no scientific module is used.
    first_actual, first_expected = FakeArray([2, 4]), FakeArray([2, 5])
    components = SimpleNamespace(MeasurementError=ParityError,
        _checked_call=lambda runtime, operation: operation())
    caller_ctx = SimpleNamespace(runtime=SimpleNamespace(numpy=FakeNumpy(), device='fixture-device'),
        components=components, model=object(), transform=lambda image: FakeInput(),
        identity={'_PIL_Image_module': SimpleNamespace(open=lambda path: FakeImage())})
    reached_return = False
    propagated = None
    with tempfile.TemporaryDirectory(prefix='parity_stdlib_', dir=HERE) as temporary:
        path = Path(temporary) / 'fixture-input.txt'
        path.write_text('stdlib mock input, not an image or scientific sample', encoding='utf-8')
        with patch.object(k, 'gpu_idle', return_value=[]), \
             patch.object(n, 'official_single_batch', return_value=first_expected), \
             patch.object(n, 'native_descriptor', return_value=first_actual):
            try:
                n.measure_sample(caller_ctx, path, 'query_drone')
                reached_return = True
            except ParityError as error:
                propagated = error
    ok('actual measure_sample propagates first failure before return', propagated is not None and not reached_return)
    ok('outer caller obtains both arrays without a successful return or traceback inspection',
       propagated.actual_descriptor_array.values == [2, 4] and propagated.expected_descriptor_array.values == [2, 5])
    ok('outer caller can serialize propagated JSON evidence', json.loads(json.dumps(propagated.evidence))['passed'] is False)

    old = HERE.parent / 'external_t1_adapter_v1'
    for name in ('bindings.py', 'native_load.py'):
        ok(name + ' byte-identical to frozen v1', (HERE / name).read_bytes() == (old / name).read_bytes())
    before = ast.parse((old / 'native_ops.py').read_text(encoding='utf-8'))
    after = ast.parse((HERE / 'native_ops.py').read_text(encoding='utf-8'))
    class RemoveOnlyFailureCopies(ast.NodeTransformer):
        removed = 0
        def visit_Assign(self, node):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute) and \
               isinstance(node.targets[0].value, ast.Name) and node.targets[0].value.id == 'error' and \
               node.targets[0].attr in {'actual_descriptor_array', 'expected_descriptor_array'}:
                self.removed += 1
                return None
            return self.generic_visit(node)
    transform = RemoveOnlyFailureCopies()
    unchanged = transform.visit(after)
    ok('only two exception-array assignments added to scientific module AST', transform.removed == 2 and ast.dump(unchanged, include_attributes=False) == ast.dump(before, include_attributes=False))
    old_snapshot = k.read(HERE / 'V1_IMMUTABLE_SOURCE_SNAPSHOT.json')
    ok('every frozen v1 file still matches initial SHA snapshot', all(k.sha(path) == expected for path, expected in old_snapshot.items()))
    forbidden = ('torch', 'numpy', 'PIL', 'torchvision', 'transformers', 'matplotlib', 'scipy')
    ok('no scientific library imported during regression', not any(name in sys.modules for name in forbidden))
    result = {'schema': 'external-t1-parity-array-regression.v1', 'created_utc': k.now(),
        'checks': checks, 'passed': len(checks), 'failed': 0, 'scientific_imports': [],
        'scientific_execution_performed': False, 'fake_arrays_are_test_fixtures_not_measurements': True,
        'reviewed_v1_source_manifest': k.record(old / 'SOURCE_MANIFEST.json'),
        'native_ops_v2': k.record(HERE / 'native_ops.py')}
    k.write_new(HERE / 'PARITY_FAILURE_REGRESSION.json', result)
    print(json.dumps({'passed': len(checks), 'failed': 0, 'scientific_execution': False}))

if __name__ == '__main__':
    main()
