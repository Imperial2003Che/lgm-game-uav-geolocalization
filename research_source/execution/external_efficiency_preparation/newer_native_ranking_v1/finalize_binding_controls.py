"""Derive only changed-interface tests; preserve previous fixtures/reports."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
source = (HERE / 'review_bridge_final.py').read_text(encoding='utf-8')
source = source.replace('def flow(self, mismatch=False):', 'def flow(self, mismatch=False, bad_content=False):')
source = source.replace("selected = SimpleNamespace(**chosen.__dict__, completed_batch_descriptor='completed batch control token')",
    "selected = SimpleNamespace(**chosen.__dict__, completed_batch_descriptor='completed batch control token',\n            expected_image_content={'bytes': 4, 'sha256': 'wrong' if bad_content else 'control'})")
source = source.replace("        def measure(*args, **kwargs):\n", "        def measure(*args, **kwargs):\n            self.assertFalse(bad_content, 'Content mismatch must fail before native B1 gate')\n")
source = source.replace("        self.assertTrue(result['ranking_measured'])", "        self.assertTrue(result['ranking_measured'])\n        self.assertFalse(result['scientific_acceptance'])\n        self.assertFalse(result['original_B1_provenance_verified_here'])")
addition = '''
    def test_11_completed_image_content_binding(self):
        inventory, _ = fixtures()
        original = [{'key': row['key'], 'bytes': row['bytes'], 'sha256': 'a' * 64} for row in inventory]
        with tempfile.TemporaryDirectory(prefix='native_ranking_content_control_') as temp:
            root = Path(temp); completion = root / 'completion.json'; completion.write_text('{}')
            (root / 'seed_1').mkdir(); target = root / 'seed_1/image_content_sha256.jsonl'
            def bind(rows):
                target.write_text(''.join(json.dumps(row) + '\\n' for row in rows), encoding='utf-8')
                return {'artifacts': {'seed_1\\\\image_content_sha256.jsonl': bridge.artifact(target)}}
            completed = bind(original)
            row, artifact = bridge.completed_query_content(completed, completion, 1, inventory, 0)
            self.assertEqual(row, original[0]); self.assertEqual(artifact, bridge.artifact(target))
            cases = ('wrong_order', 'missing', 'extra', 'bad_size', 'bool_size', 'bad_digest', 'uppercase_digest')
            for case in cases:
                with self.subTest(case=case):
                    rows = [dict(row) for row in original]
                    if case == 'wrong_order': rows[0], rows[1] = rows[1], rows[0]
                    if case == 'missing': rows.pop()
                    if case == 'extra': rows.append(dict(rows[-1]))
                    if case == 'bad_size': rows[0]['bytes'] = 5
                    if case == 'bool_size': rows[0]['bytes'] = True
                    if case == 'bad_digest': rows[0]['sha256'] = 'g' * 64
                    if case == 'uppercase_digest': rows[0]['sha256'] = 'A' * 64
                    with self.assertRaises(RuntimeError):
                        bridge.completed_query_content(bind(rows), completion, 1, inventory, 0)
            completed = bind(original)
            target.write_text('changed after binding', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'bytes changed'):
                bridge.completed_query_content(completed, completion, 1, inventory, 0)

    def test_12_changed_query_bytes_fail_before_native_gate(self):
        with self.assertRaisesRegex(RuntimeError, 'bytes differ from completed'):
            self.flow(bad_content=True)

    def test_13_public_gate_rejects_unbound_reference_without_side_effects(self):
        with patch.object(bridge, 'verify_dependency_sources', side_effect=AssertionError('No input reads')):
            with self.assertRaisesRegex(NotImplementedError, 'Independent original B=1 execution evidence'):
                bridge.measure_task_ranking(None, 'task_0', 'a caller array is not evidence', 'UNUSED_OUTPUT')

'''
source = source.replace("\n\nif __name__ == '__main__':", addition + "\nif __name__ == '__main__':")
source = source.replace("output = HERE / 'CONTROL_REVIEW_FINAL.json'", "output = HERE / 'CONTROL_REVIEW_BINDING_FINAL.json'")
source = source.replace('unittest.defaultTestLoader.loadTestsFromTestCase(BridgeReview)',
    "unittest.TestSuite(BridgeReview(name) for name in unittest.defaultTestLoader.getTestCaseNames(BridgeReview) if int(name.split('_')[1]) >= 9)")
source = source.replace("'scope': 'New ranking bridge interfaces only; original loader/ops/driver suites not rerun'",
    "'scope': 'Five changed-interface controls only: two ranking-flow regression checks, completed content binding, changed query rejection and public B1 gate; previous passed source tests are not repeated',\n        'previous_report': bridge.artifact(HERE / 'CONTROL_REVIEW_FINAL.json')")
with (HERE / 'review_bridge_binding_final.py').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(source)
