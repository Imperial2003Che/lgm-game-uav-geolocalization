"""Repeat the eight source/order checks plus four failure-persistence checks."""
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_source_initial_tests',HERE/'test_native_ops.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ops=base.ops

class SymbolicArray:
    def __init__(self,tag):self.tag=tag
    def copy(self):return SymbolicArray(self.tag)
    def __sub__(self,other):return 'symbolic difference'
    def __ne__(self,other):return 'symbolic unequal mask'

def comparison_context(equal):
    np=SimpleNamespace(array_equal=lambda a,b:equal,abs=lambda x:x,max=lambda x:0 if equal else 1,
                       count_nonzero=lambda x:0 if equal else 1)
    return SimpleNamespace(runtime=SimpleNamespace(numpy=np),components=SimpleNamespace(MeasurementError=RuntimeError))

class FailurePersistence(unittest.TestCase):
    def test_invalid_descriptor_carries_independent_arrays(self):
        a,b=SymbolicArray('actual'),SymbolicArray('reference')
        with patch.object(ops,'validate_descriptor',side_effect=RuntimeError('symbolic invalid descriptor')):
            with self.assertRaises(RuntimeError) as caught:
                ops.compare_arrays(comparison_context(False),a,b,exact=True,scope='fixture')
        a.tag='changed';b.tag='changed'
        self.assertEqual(caught.exception.actual_descriptor_array.tag,'actual')
        self.assertEqual(caught.exception.expected_descriptor_array.tag,'reference')
        json.dumps(caught.exception.evidence,allow_nan=False)

    def test_exact_failure_carries_independent_arrays(self):
        a,b=SymbolicArray('actual'),SymbolicArray('reference')
        with patch.object(ops,'validate_descriptor'):
            with self.assertRaises(RuntimeError) as caught:
                ops.compare_arrays(comparison_context(False),a,b,exact=True,scope='fixture')
        self.assertIsNot(caught.exception.actual_descriptor_array,a)
        self.assertIsNot(caught.exception.expected_descriptor_array,b)
        self.assertTrue(caught.exception.evidence['used_as_exact_gate'])
        json.dumps(caught.exception.evidence,allow_nan=False)

    def test_native_batch_difference_is_diagnostic(self):
        with patch.object(ops,'validate_descriptor'):
            result=ops.compare_arrays(comparison_context(False),SymbolicArray('actual'),SymbolicArray('reference'),exact=False,scope='batch fixture')
        self.assertFalse(result['exact_array_equal'])
        self.assertFalse(result['used_as_exact_gate'])

    def test_exact_equality_passes(self):
        with patch.object(ops,'validate_descriptor'):
            result=ops.compare_arrays(comparison_context(True),SymbolicArray('actual'),SymbolicArray('reference'),exact=True,scope='fixture')
        self.assertTrue(result['exact_array_equal'])
        self.assertTrue(result['used_as_exact_gate'])

if __name__=='__main__':
    report=HERE/'FINAL_STDLIB_REVIEW.json'
    if report.exists():raise RuntimeError('Preserve existing final review')
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(base.NativeRecipeReview),
                             unittest.defaultTestLoader.loadTestsFromTestCase(FailurePersistence)])
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    value={'status':'passed' if result.wasSuccessful() else 'failed','tests_run':result.testsRun,
           'source_sha256':ops.digest(base.SOURCE),'review_scripts':{str(p):ops.digest(p) for p in (HERE/'test_native_ops.py',Path(__file__))},
           'source_recipes':{m:ops.verify_source_recipe(m) for m in ('CAMP','DAC')},
           'unittest_output':stream.getvalue(),'scientific_imports':False,'model_or_GPU_executed':False,
           'scope':'Actual frozen-source/AST checks and symbolic order/failure checks; numerical parity, memory and timing unexecuted',
           'earlier_report':'STDLIB_REVIEW.json preserved for source before failure-array persistence amendment'}
    report.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(json.dumps({'status':value['status'],'tests_run':result.testsRun,'source_sha256':value['source_sha256']}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
