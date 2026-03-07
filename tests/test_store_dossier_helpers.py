#!/usr/bin/env python3

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import store
from utils.endpoints import endpoint_safe_key


class TestStoreDossierHelpers(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.pid = "test_pid"
        self.key = "GET https://example.com/api/users"
        self._store_dir_patch = patch.object(store, "STORE_DIR", self.tmpdir)
        self._store_dir_patch.start()

    def tearDown(self):
        self._store_dir_patch.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_endpoint_runs_by_key_missing_returns_empty(self):
        self.assertEqual(store.get_endpoint_runs_by_key(self.pid, self.key, limit=5), [])

    def test_update_endpoint_dossier_by_key_writes_and_deduplicates(self):
        run_v1 = {
            "run_id": "run-1700000000000",
            "started_at": "2026-01-01T00:00:00Z",
            "severity_counts": {"low": 1},
            "artifact": "/tmp/one.ndjson",
        }
        run_v2_same_id = {
            "run_id": "run-1700000000000",
            "started_at": "2026-01-02T00:00:00Z",
            "severity_counts": {"high": 3},
            "artifact": "/tmp/two.ndjson",
        }
        run_v3_new_id = {
            "run_id": "run-1700000000001",
            "started_at": "2026-01-03T00:00:00Z",
            "by_severity": {"medium": 2},
            "artifact": "/tmp/three.ndjson",
        }

        with patch("utils.schema_validation.validate_json", return_value=True) as mock_validate:
            with patch("store._bust_vulns_cache") as mock_bust:
                store.update_endpoint_dossier_by_key(self.pid, self.key, run_v1)
                store.update_endpoint_dossier_by_key(self.pid, self.key, run_v2_same_id)
                store.update_endpoint_dossier_by_key(self.pid, self.key, run_v3_new_id)

        dossier_path = store._endpoint_dossier_path_by_key(self.pid, self.key)
        self.assertEqual(Path(dossier_path).name, f"{endpoint_safe_key(self.key)}.json")
        self.assertTrue(Path(dossier_path).exists())

        with open(dossier_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        runs = data["runs"]
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["run_id"], "run-1700000000001")
        updated = next(run for run in runs if run["run_id"] == "run-1700000000000")
        self.assertEqual(updated["findings"], 3)
        self.assertEqual(updated["worst"], "high")
        self.assertEqual(updated["finished_at"], "2026-01-02T00:00:00Z")

        self.assertEqual(len(store.get_endpoint_runs_by_key(self.pid, self.key, limit=1)), 1)
        self.assertEqual(len(store.get_endpoint_runs_by_key(self.pid, self.key, limit=None)), 2)
        self.assertEqual(mock_validate.call_count, 3)
        self.assertEqual(mock_bust.call_count, 3)

    def test_update_endpoint_dossier_by_key_skips_write_when_schema_invalid(self):
        run_summary = {
            "run_id": "run-1700000000009",
            "started_at": "2026-01-05T00:00:00Z",
            "severity_counts": {"critical": 1},
        }

        with patch("utils.schema_validation.validate_json", return_value=False):
            with patch("store._bust_vulns_cache") as mock_bust:
                store.update_endpoint_dossier_by_key(self.pid, self.key, run_summary)
                mock_bust.assert_not_called()

        dossier_path = store._endpoint_dossier_path_by_key(self.pid, self.key)
        self.assertFalse(Path(dossier_path).exists())


if __name__ == "__main__":
    unittest.main()
