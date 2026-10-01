from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

import numpy as np
import torch

from external_baselines.fetch_and_verify_sources import IntegrityError
from external_baselines.qdfl_adapter import (
    CONFIG_SPECS,
    EPOCH_AUDIT_STATE_KEY,
    RNG_STATE_SCHEMA,
    audit_full_checkpoint,
    assert_fit_environment_has_no_test_roots,
    load_weight_registry,
    training_class_inventory,
    training_content_inventory,
    validate_resource_adaptation,
    write_immutable_json,
)


class QDFLAdapterTests(unittest.TestCase):
    def test_resource_adaptation_preserves_nominal_batch(self) -> None:
        spec = CONFIG_SPECS["qdfl_dinov2_b14"]
        self.assertEqual(validate_resource_adaptation(spec, 4), 6)
        with self.assertRaises(IntegrityError):
            validate_resource_adaptation(spec, 5)

    def test_training_inventory_requires_identical_views(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for view in ("satellite", "street", "drone"):
                for class_name in ("0001", "0002"):
                    class_root = root / view / class_name
                    class_root.mkdir(parents=True)
                    (class_root / "image.jpg").write_bytes(b"fixture")
            inventory = training_class_inventory(root, expected_classes=2)
            self.assertEqual(inventory["class_count"], 2)
            (root / "drone" / "0002").rename(root / "drone" / "0003")
            with self.assertRaises(IntegrityError):
                training_class_inventory(root, expected_classes=2)

    def test_training_content_inventory_is_content_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            image = root / "satellite" / "0001" / "image.jpg"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"first")
            inventory = training_content_inventory(root, expected=None)
            self.assertEqual(inventory["file_count"], 1)
            self.assertEqual(inventory["total_bytes"], 5)
            self.assertEqual(inventory["relative_path_prefix"], "train")
            image.write_bytes(b"other")
            changed = training_content_inventory(root, expected=None)
            self.assertNotEqual(inventory["sha256"], changed["sha256"])
            with self.assertRaises(IntegrityError):
                training_content_inventory(root, expected=inventory)

    def test_test_root_environment_is_rejected(self) -> None:
        with mock.patch.dict(os.environ, {"LGM_QDFL_U1652_TEST_ROOT": "forbidden"}):
            with self.assertRaises(IntegrityError):
                assert_fit_environment_has_no_test_roots()

    def test_immutable_json_rejects_change(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "config.json"
            first_hash = write_immutable_json(path, {"value": 1})
            self.assertEqual(first_hash, write_immutable_json(path, {"value": 1}))
            with self.assertRaises(IntegrityError):
                write_immutable_json(path, {"value": 2})

    def test_weight_registry_matches_all_config_initializations(self) -> None:
        registry_path = (
            Path(__file__).resolve().parents[1]
            / "transactions_weight_registry.json"
        )
        registry, digest = load_weight_registry(registry_path)
        self.assertTrue(
            {spec.initialization for spec in CONFIG_SPECS.values()}.issubset(
                set(registry)
            )
        )
        self.assertEqual(len(digest), 64)

    def _full_checkpoint_payload(self) -> dict:
        rng_state = {
            "schema_version": RNG_STATE_SCHEMA,
            "python": random.getstate(),
            "numpy": np.random.get_state(),
            "torch_cpu": torch.get_rng_state(),
            "torch_cuda": [torch.arange(16, dtype=torch.uint8)],
        }
        return {
            "epoch": 0,
            "global_step": 7,
            "pytorch-lightning_version": "2.3.3",
            "state_dict": {"weight": torch.ones(1)},
            "loops": {"fit_loop": {}},
            "callbacks": {
                EPOCH_AUDIT_STATE_KEY: {
                    "schema_version": EPOCH_AUDIT_STATE_KEY,
                    "records": [
                        {
                            "epoch_index": 0,
                            "completed_epochs": 1,
                            "global_step": 7,
                            "metrics": {},
                        }
                    ],
                    "rng_state": rng_state,
                }
            },
            "optimizer_states": [{"state": {}, "param_groups": [{}]}],
            "lr_schedulers": [{"last_epoch": 0}],
            "MixedPrecision": {"scale": 65536.0},
        }

    def test_full_checkpoint_audit_accepts_all_required_state(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "last.ckpt"
            torch.save(self._full_checkpoint_payload(), path)
            audit = audit_full_checkpoint(path)
            self.assertEqual(audit["epoch"], 0)
            self.assertEqual(audit["global_step"], 7)
            self.assertEqual(audit["optimizer_state_count"], 1)
            self.assertEqual(audit["rng_state_schema"], RNG_STATE_SCHEMA)

    def test_full_checkpoint_audit_rejects_model_only_state(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "last.ckpt"
            payload = self._full_checkpoint_payload()
            payload.pop("optimizer_states")
            torch.save(payload, path)
            with self.assertRaises(IntegrityError):
                audit_full_checkpoint(path)


if __name__ == "__main__":
    unittest.main()
