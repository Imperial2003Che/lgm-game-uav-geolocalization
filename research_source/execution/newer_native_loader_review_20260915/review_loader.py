"""Real source/stdlib imports and temporary control fixtures; no science."""
from contextlib import nullcontext
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'external_efficiency_preparation/newer_native_loader_v1'
sys.path.insert(0,str(PACKAGE))
import source_bindings as b
import native_load as loader
import path_aliases

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return b.FrozenJson.read(path,b.sha(path))

def seal(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    return {**value,'payload_sha256':hashlib.sha256(raw).hexdigest()}

def verify_seal(value):
    body=dict(value);expected=body.pop('payload_sha256')
    b.require(seal(body)['payload_sha256']==expected,'Fixture control seal differs')

def artifact(path):return {'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':b.sha(path)}

def verify_artifact(row):b.require(artifact(Path(row['path']))==row,'Fixture artifact differs')

def fixture(root,mutate=None):
    # Descriptor filenames hold explicit NON-NPY bytes. This only tests control
    # binding and cannot be mistaken for an actual scientific loader/run.
    root.mkdir(parents=True,exist_ok=True)
    tasks=write(root/'tasks.json',[{'name':f'fixture_task_{i}'} for i in range(10)])
    prep=write(root/'prepared.json',{'membership':{'tasks':tasks.artifact()}})
    seeds=[{'seed':seed,'checkpoints':{'weights_end.pth':{'sha256':str(seed)*64}}} for seed in (1,2,3)]
    binding=write(root/'binding.json',{'seeds':seeds})
    metrics={str(seed):{f'fixture_task_{i}':{'method':'CAMP','seed':seed,'checkpoint_sha256':str(seed)*64} for i in range(10)} for seed in (1,2,3)}
    write(root/'metrics_all_30.json',metrics)
    write(root/'three_seed_summary.json',{'fixture_only':True})
    (root/'metrics_all_30.csv').write_text('fixture-only-no-numeric-results\n',encoding='utf-8')
    for seed in (1,2,3):
        d=root/f'seed_{seed}';d.mkdir()
        write(d/'metrics.json',{'fixture_only':True});write(d/'strict_complete_final_load.json',{'fixture_only':True})
        (d/'descriptors.npy').write_bytes(b'NOT A NUMPY FILE: CONTROL FIXTURE ONLY')
    files={str(p.relative_to(root)):artifact(p) for p in root.rglob('*') if p.is_file()}
    value={'status':'completed','task_count':30,'seeds':[1,2,3],'prepared':prep.artifact(),'binding':binding.artifact(),'artifacts':files}
    if mutate:mutate(value,root)
    completion=write(root/'completion.json',seal(value))
    inputs=b.CompletedInputs('CAMP',prep,binding,completion)
    package=SimpleNamespace(protocol=SimpleNamespace(verify_seal=verify_seal,verify_artifact=verify_artifact))
    return package,inputs,{'seeds':seeds}

class BindingReview(unittest.TestCase):
    def test_actual_source_manifests_and_registered_runtime(self):
        for method,count in (('CAMP',12),('DAC',18)):
            contract=b.source_contract(method)
            self.assertEqual(contract['evaluation']['verified_file_count'],count)
            self.assertEqual(contract['prepared'].value()['python'],r'C:\项目\.venvs\lgm-camp\Scripts\python.exe')
        b.no_scientific_modules()

    def test_actual_original_package_and_prepared_reads_in_separate_processes(self):
        code="""import sys,json;from contextlib import nullcontext
sys.path.insert(0,sys.argv[1]);import source_bindings as b
method=sys.argv[2];contract=b.source_contract(method);pkg=b.open_original_package(method)
with (pkg.snapshots.snapshot_scope() if pkg.snapshots is not None else nullcontext()):
 value=pkg.evaluator.read_prepared(contract['prepared'].path)
 assert value==contract['prepared'].value()
b.no_scientific_modules()
try:b.open_original_package('DAC' if method=='CAMP' else 'CAMP')
except RuntimeError:pass
else:raise AssertionError('Cross-method reuse accepted')
print(json.dumps({'method':method,'state':value['status'],'scientific_imports':False}))
"""
        for method in ('CAMP','DAC'):
            completed=subprocess.run([sys.executable,'-X','utf8','-c',code,str(PACKAGE),method],capture_output=True,text=True,
                encoding='utf-8',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(completed.returncode,0,completed.stderr)
            result=json.loads(completed.stdout);self.assertFalse(result['scientific_imports'])
            self.assertEqual(result['state'],'prepared_waiting_for_training')

    def test_raw_BOM_CRLF_identity_and_mutation(self):
        with tempfile.TemporaryDirectory(prefix='newer_loader_json_') as temp:
            p=Path(temp)/'raw.json';p.write_bytes(b'\xef\xbb\xbf{\r\n"x":1\r\n}')
            s=b.FrozenJson.read(p,b.sha(p));self.assertEqual(s.value(),{'x':1})
            s.value()['x']=2;self.assertEqual(s.value(),{'x':1})
            p.write_bytes(b'{"x":1}')
            with self.assertRaises(RuntimeError):s.unchanged()

    def test_future_hash_or_missing_completion_rejected_before_import(self):
        with self.assertRaises(RuntimeError):b.FrozenJson.read('missing.json',None)
        with tempfile.TemporaryDirectory(prefix='newer_loader_missing_') as temp:
            with self.assertRaises(FileNotFoundError):b.bind_completed('CAMP',Path(temp)/'not-produced.json','0'*64,Path(temp)/'not-completed.json','0'*64)
        b.no_scientific_modules()

    def test_complete_windows_path_control_fixture(self):
        with tempfile.TemporaryDirectory(prefix='newer_loader_control_') as temp:
            pkg,inputs,bound=fixture(Path(temp)/'fixture')
            b.validate_completion(pkg,inputs,bound)
            self.assertEqual(inputs.seed_binding(2)['seed'],2)
            with self.assertRaises(RuntimeError):inputs.seed_binding(True)

    def reject_fixture(self,mutate):
        with tempfile.TemporaryDirectory(prefix='newer_loader_reject_') as temp:
            pkg,inputs,bound=fixture(Path(temp)/'fixture',mutate)
            with self.assertRaises(RuntimeError):b.validate_completion(pkg,inputs,bound)

    def test_partial_task_count_rejected(self):
        self.reject_fixture(lambda v,r:v.update(task_count=29))

    def test_boolean_seed_and_float_task_count_rejected(self):
        self.reject_fixture(lambda v,r:v.update(seeds=[True,2,3]))
        self.reject_fixture(lambda v,r:v.update(task_count=30.0))

    def test_missing_descriptor_artifact_rejected(self):
        def mutate(v,r):
            key=next(k for k in v['artifacts'] if k.replace('\\','/')=='seed_3/descriptors.npy')
            del v['artifacts'][key]
        self.reject_fixture(mutate)

    def test_duplicate_normalized_path_rejected(self):
        def mutate(v,r):
            key=next(k for k in v['artifacts'] if k.replace('\\','/')=='seed_1/descriptors.npy')
            alternate=key.replace('\\','/') if '\\' in key else key.replace('/','\\')
            v['artifacts'][alternate]=v['artifacts'][key]
        self.reject_fixture(mutate)

    def test_wrong_method_or_checkpoint_in_metric_rows_rejected(self):
        for field,value in (('method','DAC'),('checkpoint_sha256','0'*64)):
            def mutate(v,r,field=field,value=value):
                p=r/'metrics_all_30.json';data=json.loads(p.read_text(encoding='utf-8'))
                data['2']['fixture_task_0'][field]=value;write(p,data)
                v['artifacts']['metrics_all_30.json']=artifact(p)
            self.reject_fixture(mutate)

    def test_bad_parent_binding_identity_rejected(self):
        self.reject_fixture(lambda v,r:v['binding'].update(sha256='0'*64))

    def test_gpu_owner_any_type_rejected(self):
        loader.require_compute_idle('')
        for text in ('1234\n','not supported\n','1234, non-python-owner\n'):
            with self.assertRaises(RuntimeError):loader.require_compute_idle(text)

    def test_wrong_runtime_and_unbound_model_call_fail_without_science(self):
        prepared=b.source_contract('CAMP')['prepared'].value()
        with self.assertRaises(RuntimeError):loader.verify_native_settings(prepared)
        with self.assertRaises(RuntimeError):loader.load_native_slot(None,1)
        b.no_scientific_modules()

    def test_real_same_file_alias_preserves_all_evidence(self):
        with tempfile.TemporaryDirectory(prefix='newer_loader_alias_') as temp:
            root=Path(temp);original=root/'original.txt';alias=root/'alias.txt'
            original.write_bytes(b'fixture-source');os.link(original,alias)
            left=artifact(original);right=artifact(alias)
            rows=path_aliases.compare_evidence({'files':[left],'fixed':True},{'files':[right],'fixed':True})
            self.assertEqual(len(rows),1);self.assertTrue(rows[0]['same_file'])

    def test_equal_content_different_files_are_not_aliases(self):
        with tempfile.TemporaryDirectory(prefix='newer_loader_distinct_') as temp:
            root=Path(temp);a=root/'a.txt';c=root/'c.txt';a.write_bytes(b'same');c.write_bytes(b'same')
            with self.assertRaises(RuntimeError):path_aliases.compare_evidence(artifact(a),artifact(c))

    def test_alias_hash_or_nonartifact_change_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='newer_loader_alias_fail_') as temp:
            root=Path(temp);a=root/'a.txt';c=root/'c.txt';a.write_bytes(b'before');os.link(a,c)
            before=artifact(a);a.write_bytes(b'after!')
            with self.assertRaises(RuntimeError):path_aliases.compare_evidence(before,artifact(c))
            with self.assertRaises(RuntimeError):path_aliases.compare_evidence({'fixed':True},{'fixed':1})

if __name__=='__main__':
    path=HERE/'PATH_ALIAS_FINAL_REVIEW.json'
    if path.exists():raise RuntimeError('Preserve existing review')
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BindingReview))
    value={'status':'passed' if result.wasSuccessful() else 'failed','tests_run':result.testsRun,
           'source_files':{str(p):b.sha(p) for p in (PACKAGE/'source_bindings.py',PACKAGE/'native_load.py',PACKAGE/'path_aliases.py',Path(__file__))},
           'unittest_output':stream.getvalue(),'scientific_imports':False,'actual_model_loading':False,'GPU_execution':False,
           'scope':'Actual frozen source/prepared reads and original stdlib package isolation; temporary control fixtures only. Native load positive path remains unexecuted.'}
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(json.dumps({'status':value['status'],'tests_run':result.testsRun,'review':str(path)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
