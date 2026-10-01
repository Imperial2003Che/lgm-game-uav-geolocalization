"""Bounded stdlib interface tests; fixtures are not scientific data or timings."""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'ranking_bridge.py'
spec = importlib.util.spec_from_file_location('native_ranking_bridge_control_review', SOURCE)
bridge = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bridge
before = set(sys.modules)
spec.loader.exec_module(bridge)


def fixtures():
    inventory = [{'key': 'query/first', 'label': 'positive', 'bytes': 4},
                 {'key': 'gallery/a', 'label': 'negative', 'bytes': 4},
                 {'key': 'gallery/b', 'label': 'positive', 'bytes': 4},
                 {'key': 'gallery/c', 'label': 'positive', 'bytes': 4}]
    tasks = [{'name': f'task_{i}', 'query_indices': [0], 'gallery_indices': [3, 1, 2]}
             for i in range(10)]
    return inventory, tasks


class MarkerNP:
    @staticmethod
    def save(stream, value, allow_pickle):
        assert allow_pickle is False
        stream.write(('CONTROL_FIXTURE_NOT_NPY:' + repr(value)).encode())


class Labels(list):
    def __getitem__(self, key):
        if isinstance(key, list):
            return Labels([super(Labels, self).__getitem__(i) for i in key])
        return super().__getitem__(key)
    def __eq__(self, value):
        return [item == value for item in self]


class Positions(list):
    def __add__(self, number):
        return Positions([x + number for x in self])


class Rank:
    values = [1, 0, 2]
    def __getitem__(self, key):
        return self.values[key[1]] if isinstance(key, tuple) else self.values


class FlowNP:
    @staticmethod
    def array_equal(left, right):
        if isinstance(left, Rank) and isinstance(right, Rank):
            return left.values == right.values
        return list(left) == list(right)
    @staticmethod
    def asarray(values):
        return Labels(values)
    @staticmethod
    def flatnonzero(values):
        return Positions([i for i, value in enumerate(values) if value])


class BridgeReview(unittest.TestCase):
    def test_01_no_scientific_import_or_cli(self):
        self.assertFalse({x.split('.')[0] for x in set(sys.modules) - before} &
                         {'torch', 'numpy', 'PIL', 'cv2', 'timm', 'albumentations'})
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        imports = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any(any(word in item for word in ('torch', 'numpy', 'PIL', 'subprocess')) for item in imports))
        self.assertNotIn("if __name__", SOURCE.read_text(encoding='utf-8'))

    def test_02_actual_pinned_dependency_sources(self):
        rows = bridge.verify_dependency_sources()
        self.assertEqual(len(rows), 6)
        self.assertEqual({Path(row['path']).name for row in rows},
                         {'SOURCE_MANIFEST.json', 'native_ops.py', 'native_load.py', 'source_bindings.py', 'path_aliases.py'})

    def test_03_exact_original_full_sort_expression(self):
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        own = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'full_stable_ranking')
        expression = next(n.value for n in own.body if isinstance(n, ast.Return))
        # Only the variable name differs from both pinned original helpers.
        class Rename(ast.NodeTransformer):
            def visit_Name(self, node):
                return ast.copy_location(ast.Name(id='descriptor' if node.id == 'query_features' else node.id,
                                                 ctx=node.ctx), node)
        root = HERE.parents[1]
        for folder in ('camp_preparation', 'dac_preparation'):
            filename = 'run_' + folder[:4] + '_author_evaluation.py' if folder.startswith('camp') else 'run_dac_author_evaluation.py'
            original = ast.parse((root / folder / filename).read_text(encoding='utf-8-sig'))
            fn = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == 'rank_with_query_evidence')
            assigned = next(n.value for n in ast.walk(fn) if isinstance(n, ast.Assign) and
                            any(isinstance(x, ast.Name) and x.id == 'ordering' for x in n.targets))
            self.assertEqual(ast.dump(expression), ast.dump(Rename().visit(assigned)))

    def test_04_fixed_first_query_and_complete_gallery_order(self):
        inventory, tasks = fixtures()
        chosen = bridge.select_first_query(inventory, tasks, 'task_3')
        self.assertEqual(chosen.query_index, 0)
        self.assertEqual(chosen.gallery_indices, (3, 1, 2))
        self.assertEqual([r['key'] for r in chosen.gallery_rows], ['gallery/c', 'gallery/a', 'gallery/b'])

    def test_05_bad_registry_and_membership_rejected(self):
        cases = ('duplicate_task', 'unknown_task', 'bool_index', 'outside_index', 'duplicate_gallery',
                 'no_positive', 'overlap', 'duplicate_key')
        for case in cases:
            with self.subTest(case=case):
                inventory, tasks = fixtures(); name = 'task_0'
                if case == 'duplicate_task': tasks[1]['name'] = tasks[0]['name']
                if case == 'unknown_task': name = 'unregistered'
                if case == 'bool_index': tasks[0]['query_indices'] = [False]
                if case == 'outside_index': tasks[0]['gallery_indices'] = [7]
                if case == 'duplicate_gallery': tasks[0]['gallery_indices'] = [1, 1]
                if case == 'no_positive': tasks[0]['gallery_indices'] = [1]
                if case == 'overlap': tasks[0]['gallery_indices'] = [0, 1]
                if case == 'duplicate_key': inventory[1]['key'] = inventory[0]['key'].upper()
                with self.assertRaises(RuntimeError): bridge.select_first_query(inventory, tasks, name)

    def test_06_completed_artifact_windows_separator_and_bytes(self):
        with tempfile.TemporaryDirectory(prefix='native_ranking_control_') as temp:
            root = Path(temp); (root / 'completion.json').write_text('{}')
            (root / 'seed_1').mkdir(); target = root / 'seed_1/descriptors.npy'
            target.write_bytes(b'CONTROL_NOT_A_SCIENTIFIC_ARRAY')
            item = bridge.artifact(target)
            completed = {'artifacts': {'seed_1\\descriptors.npy': item}}
            self.assertEqual(bridge.completion_artifact(completed, root / 'completion.json', 'seed_1/descriptors.npy'), item)
            target.write_bytes(b'CHANGED_CONTROL_BYTES')
            with self.assertRaises(RuntimeError): bridge.completion_artifact(completed, root / 'completion.json', 'seed_1/descriptors.npy')

    def test_07_artifact_duplicates_escape_and_missing_rejected(self):
        with tempfile.TemporaryDirectory(prefix='native_ranking_control_') as temp:
            root = Path(temp); completion = root / 'completion.json'; completion.write_text('{}')
            target = root / 'fixture.bin'; target.write_bytes(b'CONTROL')
            item = bridge.artifact(target)
            for rows, relative in [({'a\\b': item, 'a/b': item}, 'a/b'), ({}, 'missing'),
                                   ({'../fixture.bin': item}, '../fixture.bin')]:
                with self.subTest(relative=relative), self.assertRaises((RuntimeError, FileNotFoundError)):
                    bridge.completion_artifact({'artifacts': rows}, completion, relative)

    def test_08_failure_arrays_are_exclusive_and_outside_json(self):
        with tempfile.TemporaryDirectory(prefix='native_ranking_control_') as temp:
            output = Path(temp)
            error = RuntimeError('CONTROL PARITY FAILURE')
            error.actual_descriptor_array = ['actual control token']
            error.expected_descriptor_array = ['reference control token']
            error.evidence = {'control_fixture': True}
            bridge.preserve_failure(MarkerNP, output, error)
            value = json.loads((output / 'failure.json').read_text(encoding='utf-8'))
            self.assertEqual(len(value['actual_arrays']), 2)
            self.assertFalse(value['scientific_completion_claimed'])
            self.assertNotIn('actual control token', (output / 'failure.json').read_text(encoding='utf-8'))
            with self.assertRaises(FileExistsError): bridge.preserve_failure(MarkerNP, output, error)

    def flow(self, mismatch=False):
        inventory, tasks = fixtures(); chosen = bridge.select_first_query(inventory, tasks, 'task_0')
        selected = SimpleNamespace(**chosen.__dict__, completed_batch_descriptor='completed batch control token')
        actions = []
        gallery = SimpleNamespace(shape=(3, 1024))
        class Gallery:
            shape = (3, 1024)
            def __getitem__(self, index): return 'gallery token ' + str(index)
        gallery = Gallery()
        class Record:
            def __init__(self, relative_path, label): self.relative_path, self.label = relative_path, label
        helper = SimpleNamespace(record_path=lambda *_: Path('CONTROL_IMAGE'), Record=Record,
            Task=lambda name, query, gallery: (name, query, gallery),
            rank_with_query_evidence=lambda *_: ({'control_fixture': True}, {'top1_gallery_indices': [1], 'positive_ranks_1based': [2, 3]}),
            validate_query_arrays=lambda *_: {'control_fixture_validation': True})
        def timing(runtime, operation, **kwargs):
            actions.append(('timing', kwargs['scope'], kwargs['clock']))
            operation()
            return {'runtime_flags': {'native_clip_autocast': 'must remove', 'native_formal_autocast': 'must remove'},
                    'control_fixture_no_actual_timing': True}
        components = SimpleNamespace(_checked_call=lambda _, op: op(), measure_operation=timing)
        runtime = SimpleNamespace(numpy=FlowNP)
        ops = SimpleNamespace(runtime=runtime, components=components, model=object(),
                              raw_descriptor_cpu=lambda path: 'raw B1 control token')
        slot = SimpleNamespace(operations=ops, original_package=SimpleNamespace(protocol=SimpleNamespace(helpers=lambda: helper)),
            inputs=SimpleNamespace(prepared=SimpleNamespace(value=lambda: {'membership': {'roots': {}}, 'settings': {'ranking_chunk_size': 64}})))
        def measure(*args, **kwargs):
            self.assertEqual(kwargs['completed_batch_descriptor'], selected.completed_batch_descriptor)
            actions.append(('native_B1_gate',))
            return ({'full_t6_complete': False}, {'raw_B1': ['raw descriptor row'], 'reference_B1': ['reference row']})
        native_ops = SimpleNamespace(measure_sample=measure, measurement_metadata=lambda row: dict(row))
        ranking_calls = 0
        def rank(*_):
            nonlocal ranking_calls
            ranking_calls += 1
            value = Rank()
            if mismatch and ranking_calls == 2: value.values = [0, 1, 2]
            return value
        def save(np, path, value): actions.append(('saved', Path(path).name)); return {'control': True}
        with patch.object(bridge, 'artifact', return_value={'bytes': 4, 'sha256': 'control'}), \
             patch.object(bridge, 'save_array', side_effect=save), patch.object(bridge, 'save_arrays', side_effect=save), \
             patch.object(bridge, 'full_stable_ranking', side_effect=rank):
            result = bridge._measure_ranking_paths(slot, selected, gallery, 'original B1 control token', Path('CONTROL_OUTPUT'), native_ops)
        return result, actions

    def test_09_bridge_wires_two_scopes_and_original_one_query_validator(self):
        result, actions = self.flow()
        self.assertEqual(len([a for a in actions if a[0] == 'timing']), 2)
        self.assertTrue(all(a[2] == 'synchronized_wall' for a in actions if a[0] == 'timing'))
        self.assertEqual(actions[0], ('native_B1_gate',))
        self.assertTrue(result['ranking_measured'])
        self.assertFalse(result['full_gallery_descriptors_reencoded_here'])
        self.assertFalse(result['full_gallery_metrics_recomputed_here'])
        self.assertFalse(result['full_dataset_online_accuracy_measured'])
        self.assertNotIn('native_clip_autocast', result['descriptor_to_full_gallery_ranking']['runtime_flags'])
        self.assertIn(('saved', 'raw_full_ranking_after.npy'), actions)
        self.assertIn(('saved', 'original_online_one_query_arrays.npz'), actions)

    def test_10_ranking_mismatch_stops_before_timing(self):
        with self.assertRaisesRegex(RuntimeError, 'before timing'):
            self.flow(mismatch=True)


if __name__ == '__main__':
    output = HERE / 'CONTROL_REVIEW_FINAL.json'
    if output.exists(): raise RuntimeError('Preserve the existing control report; choose a new version')
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BridgeReview))
    scientific = sorted({name.split('.')[0] for name in sys.modules} & {'torch', 'numpy', 'PIL', 'cv2', 'timm', 'albumentations'})
    report = {'status': 'passed' if result.wasSuccessful() and not scientific else 'failed',
        'test_count': result.testsRun, 'source': bridge.artifact(SOURCE), 'script': bridge.artifact(__file__),
        'scientific_imports': scientific, 'scientific_execution': False, 'process_launches': False,
        'control_fixtures_are_experimental_results': False,
        'scope': 'New ranking bridge interfaces only; original loader/ops/driver suites not rerun',
        'unittest_output': log.getvalue()}
    bridge.write_json(output, report)
    print(log.getvalue()); print(json.dumps({'status': report['status'], 'report': str(output)}))
    sys.exit(0 if report['status'] == 'passed' else 1)
