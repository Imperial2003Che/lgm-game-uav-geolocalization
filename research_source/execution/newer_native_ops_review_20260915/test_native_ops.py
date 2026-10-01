"""Standard-library checks only. Symbolic tags are not model outputs/timings."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent/'external_efficiency_preparation/newer_native_ops_v1/native_ops.py'
spec = importlib.util.spec_from_file_location('newer_native_ops_source_review', SOURCE)
ops = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ops
before_modules = set(sys.modules)
spec.loader.exec_module(ops)


class SymbolicTensor:
    def __init__(self, owner, tag): self.owner, self.tag = owner, tag
    def to(self, *args, **kwargs):
        self.owner.trace.append(('to', args, kwargs, self.owner.amp))
        return self
    def cpu(self): self.owner.trace.append(('cpu',)); return self
    def numpy(self): self.owner.trace.append(('numpy',)); return 'symbolic CPU array'


class SymbolicTorch:
    float16, float32 = 'float16', 'float32'
    def __init__(self):
        self.trace, self.grad, self.inference, self.amp = [], True, True, None
    @contextlib.contextmanager
    def inference_mode(self, value=True):
        before = self.inference; self.inference = value
        try: yield
        finally: self.inference = before
    @contextlib.contextmanager
    def no_grad(self):
        before = self.grad; self.grad = False
        try: yield
        finally: self.grad = before
    @contextlib.contextmanager
    def autocast(self, device, *, dtype):
        assert device == 'cuda'
        before = self.amp; self.amp = dtype
        try: yield
        finally: self.amp = before
    def stack(self, values):
        self.trace.append(('stack', len(values)))
        return SymbolicTensor(self, 'batched image')


def symbolic_operations(method):
    t = SymbolicTorch()
    chosen = SymbolicTensor(t, 'original index -2')
    def model(batch):
        assert (t.grad, t.inference, t.amp) == (False, False, 'float16')
        t.trace.append(('model', batch))
        return ['unused earlier output', chosen, 'unused final output']
    def normalize(value, *, dim):
        assert value is chosen and dim == -1 and t.amp == 'float16'
        t.trace.append(('normalize',))
        return chosen
    def frombuffer(raw, *, dtype):
        assert raw == b'not-a-real-image-test-bytes' and dtype == 'uint8'
        t.trace.append(('frombuffer',))
        return 'symbolic bytes'
    def imdecode(value, color):
        assert value == 'symbolic bytes' and color == 'IMREAD_COLOR'
        t.trace.append(('imdecode',))
        return 'symbolic BGR'
    def cvtcolor(value, color):
        assert value == 'symbolic BGR' and color == 'COLOR_BGR2RGB'
        t.trace.append(('cvtColor',))
        return 'symbolic RGB'
    def transform(*, image):
        assert image == 'symbolic RGB'
        t.trace.append(('transform',))
        return {'image': SymbolicTensor(t, 'one image')}
    instance = ops.Operations(method, SimpleNamespace(torch=t, numpy=SimpleNamespace(frombuffer=frombuffer, uint8='uint8')),
        SimpleNamespace(imdecode=imdecode, cvtColor=cvtcolor, IMREAD_COLOR='IMREAD_COLOR', COLOR_BGR2RGB='COLOR_BGR2RGB'),
        SimpleNamespace(normalize=normalize), model, transform, None)
    return instance, t, chosen


class NativeRecipeReview(unittest.TestCase):
    def test_actual_both_source_pins_and_original_recipe(self):
        camp, dac = [ops.verify_source_recipe(m) for m in ('CAMP', 'DAC')]
        self.assertEqual(camp['transform_ast_sha256'], dac['transform_ast_sha256'])
        self.assertFalse(camp['numerical_parity_executed'])
        self.assertFalse(dac['numerical_parity_executed'])
        with self.assertRaises(RuntimeError): ops.verify_source_recipe('QDFL')

    def test_import_does_not_load_scientific_libraries(self):
        new = set(sys.modules)-before_modules
        self.assertFalse({x.split('.')[0] for x in new} & {'numpy','torch','cv2','PIL','albumentations'})
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        direct = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertTrue(all('torch' not in ast.unparse(n) and 'numpy' not in ast.unparse(n) for n in direct))

    def test_one_forward_without_normalization_or_flip(self):
        for method in ('CAMP', 'DAC'):
            instance, t, chosen = symbolic_operations(method)
            self.assertIs(instance.forward_gpu('GPU input'), chosen)
            self.assertEqual(t.trace, [('model', 'GPU input')])
            self.assertEqual((t.grad,t.inference,t.amp), (True,True,None))

    def test_normalization_inside_fp16_then_cast_and_cpu(self):
        for method in ('CAMP', 'DAC'):
            instance, t, _ = symbolic_operations(method)
            self.assertEqual(instance.descriptor_cpu('GPU input'), 'symbolic CPU array')
            self.assertEqual(t.trace, [('model','GPU input'),('normalize',),('to',('float32',),{},None),('cpu',),('numpy',)])
            self.assertEqual((t.grad,t.inference,t.amp), (True,True,None))

    def test_original_decode_transform_stack_blocking_transfer_order(self):
        with tempfile.TemporaryDirectory(prefix='newer_native_symbolic_') as temp:
            path=Path(temp)/'fixture.bin';path.write_bytes(b'not-a-real-image-test-bytes')
            for method in ('CAMP','DAC'):
                instance,t,_=symbolic_operations(method)
                self.assertEqual(instance.raw_descriptor_cpu(path),'symbolic CPU array')
                self.assertEqual(t.trace[:6], [('frombuffer',),('imdecode',),('cvtColor',),('transform',),('stack',1),('to',('cuda:0',),{},None)])
                self.assertEqual([row[0] for row in t.trace].count('model'),1)

    def test_bad_decode_does_not_call_transform_or_model(self):
        with tempfile.TemporaryDirectory(prefix='newer_native_decode_') as temp:
            path=Path(temp)/'fixture.bin';path.write_bytes(b'not-a-real-image-test-bytes')
            instance,t,_=symbolic_operations('CAMP')
            instance.cv2.imdecode=lambda *_:None
            with self.assertRaises(RuntimeError):instance.raw_descriptor_cpu(path)
            self.assertEqual(t.trace,[('frombuffer',)])

    def test_native_modes_replace_inapplicable_primary_labels(self):
        incoming={'runtime_flags':{'native_formal_autocast':'primary','native_clip_autocast':'clip','torch':'actual-at-runtime'},'inference_mode':True}
        outgoing=ops.measurement_metadata(incoming)
        self.assertFalse(outgoing['inference_mode'])
        self.assertTrue(outgoing['shared_timer_outer_inference_mode'])
        self.assertNotIn('native_clip_autocast',outgoing['runtime_flags'])
        self.assertNotIn('native_formal_autocast',outgoing['runtime_flags'])
        self.assertFalse(outgoing['runtime_flags']['native_flip_tta'])
        self.assertIn('native_clip_autocast',incoming['runtime_flags'])

    def test_source_mutation_is_rejected_without_scientific_import(self):
        original = ops.EXECUTION
        with tempfile.TemporaryDirectory(prefix='newer_native_source_') as temp:
            fake=Path(temp)
            for method in ('CAMP','DAC'):
                name,_,helper,_=ops.SOURCES[method]
                (fake/name).parent.mkdir(parents=True,exist_ok=True)
                (fake/name).write_bytes((original/name).read_bytes()+b'\n# mutation\n')
                (fake/helper).parent.mkdir(parents=True,exist_ok=True)
                (fake/helper).write_bytes((original/helper).read_bytes())
            try:
                ops.EXECUTION=fake
                for method in ('CAMP','DAC'):
                    with self.assertRaises(RuntimeError):ops.verify_source_recipe(method)
            finally:ops.EXECUTION=original


if __name__ == '__main__':
    report=HERE/'STDLIB_REVIEW.json'
    if report.exists():raise RuntimeError('Review report already exists; preserve the previous result')
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeRecipeReview))
    records={method:ops.verify_source_recipe(method) for method in ('CAMP','DAC')}
    payload={'status':'passed' if result.wasSuccessful() else 'failed','tests_run':result.testsRun,
        'source_sha256':ops.digest(SOURCE),'review_script_sha256':ops.digest(__file__),
        'real_source_recipe_checks':records,'unittest_output':stream.getvalue(),
        'scientific_imports':False,'model_or_GPU_executed':False,
        'symbolic_test_values_are_experiment_results':False,
        'scope':'source provenance and symbolic operation order only; no numerical parity or timing validation'}
    report.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(json.dumps({'status':payload['status'],'tests_run':result.testsRun,'report':str(report)}))
    sys.exit(0 if result.wasSuccessful() else 1)
