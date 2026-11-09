from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from .test_io import fixture
except ImportError:
    from test_io import fixture


class CommandTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[2]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.source = fixture(self.workspace)

    def invoke(self, script, *args):
        process = subprocess.run([sys.executable, "-I", "-B", str(self.root / "scripts" / script),
                                  "--workspace", str(self.workspace), *map(str, args)],
                                 capture_output=True, text=True, timeout=20)
        return process.returncode, json.loads(process.stdout)

    def test_valid_real_command_uses_stdlib_and_returns_json(self):
        code, report = self.invoke("audit_movielens.py", "--source", self.source)
        self.assertEqual(code, 0)
        self.assertEqual(report["counts"]["ratings"]["rows"], 3)

    def test_missing_input_returns_explicit_nonzero(self):
        code, report = self.invoke("audit_movielens.py", "--source", self.workspace / "missing")
        self.assertEqual(code, 3)
        self.assertEqual(report["status"], "missing")

    def test_existing_output_failure_does_not_overwrite_data(self):
        output = self.workspace / "existing"
        output.mkdir()
        marker = output / "marker.txt"
        marker.write_text("keep")
        code, report = self.invoke("audit_movielens.py", "--source", self.source, "--output", output)
        self.assertEqual(code, 2)
        self.assertEqual(marker.read_text(), "keep")

    def test_mapping_cli_reports_provisional_as_partial(self):
        code, report = self.invoke("build_movie_id_map.py", "--source", self.source,
                                   "--output", self.workspace / "reports/map")
        self.assertEqual(code, 4)
        self.assertEqual(report["counts"]["canonical_ids_approved"], 0)

    def test_bad_config_is_a_structured_failure(self):
        config = self.workspace / "bad.json"
        config.write_text('{"expected_counts": []}')
        code, report = self.invoke("audit_movielens.py", "--source", self.source,
                                   "--config", config)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "invalid")

    def test_external_and_legacy_inputs_are_rejected(self):
        for source in (self.workspace.parent, self.workspace / "temp"):
            code, report = self.invoke("audit_movielens.py", "--source", source)
            self.assertEqual(code, 2)
            self.assertEqual(report["status"], "invalid")
