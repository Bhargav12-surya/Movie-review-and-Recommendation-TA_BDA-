"""Synthetic local snapshot/provenance checks; never contact TMDB."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dataset_tools.tmdb import validate_tmdb_snapshots


class TmdbValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.raw = self.root / "data/raw/tmdb"
        self.raw.mkdir(parents=True)
        self.addCleanup(self.temporary.cleanup)
        self.provenance = self.root / "provenance.json"
        self.provenance.write_text(json.dumps({"source": "tmdb", "snapshot_version": "fixture-v1",
            "terms_version": "fixture-terms", "retrieved_at": "2026-01-01T00:00:00Z",
            "usage_approved": True, "attribution_acknowledged": True}))

    def row(self, **changes):
        value = {"id": 101, "title": "Fixture film", "overview": None, "runtime": None,
                 "release_date": "", "genres": [], "original_language": "en",
                 "poster_path": None}
        value.update(changes)
        return value

    def write(self, records):
        path = self.raw / "snapshot.json"
        path.write_text(json.dumps({"results": records}))
        return path

    def test_nullable_metadata_is_measured_not_invented(self):
        result = validate_tmdb_snapshots(self.write([self.row()]), self.provenance,
                                         workspace=self.root)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["nullable_field_counts"]["overview"], 1)
        self.assertEqual(result["counts"]["valid"], 1)

    def test_missing_or_unapproved_provenance_blocks_export(self):
        result = validate_tmdb_snapshots(self.write([self.row()]), workspace=self.root)
        self.assertEqual(result["status"], "partial")
        self.assertIn("tmdb_provenance_manifest_missing", result["blockers"])

    def test_invalid_date_runtime_boolean_duplicate_id_and_overflow_rejected(self):
        rows = [self.row(runtime=True), self.row(id=102, release_date="2026-02-31"),
                self.row(id=10**30), self.row(id=103), self.row(id=103)]
        result = validate_tmdb_snapshots(self.write(rows), self.provenance, workspace=self.root)
        self.assertEqual(result["counts"]["rejected"], 4)
        self.assertEqual(result["counts"]["duplicates"], 1)
        self.assertEqual(result["status"], "invalid")

    def test_accepted_records_keep_source_namespace_and_raw_bytes(self):
        source = self.write([self.row()])
        before = source.read_bytes()
        output = self.root / "reports/snapshot"
        result = validate_tmdb_snapshots(source, self.provenance, output, self.root, True)
        accepted = json.loads((output / "accepted.jsonl").read_text())
        self.assertIsNone(accepted["canonical_movie_id"])
        self.assertEqual(accepted["tmdb_id"], 101)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(result["status"], "complete")

    def test_malformed_source_is_reported_without_private_content(self):
        source = self.raw / "bad.json"
        source.write_text('{"title":"private-secret",invalid}')
        result = validate_tmdb_snapshots(source, self.provenance, workspace=self.root)
        self.assertEqual(result["status"], "invalid")
        self.assertNotIn("private-secret", json.dumps(result))

    def test_missing_cli_is_explicit_and_offline(self):
        run = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/prepare_tmdb_snapshots.py"),
            str(self.root / "missing"), "--workspace", str(self.root)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 3, run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"], "missing")


if __name__ == "__main__":
    unittest.main()
