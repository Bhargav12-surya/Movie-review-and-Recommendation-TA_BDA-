"""Synthetic review contracts; fixture labels are never research results."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dataset_tools.reviews import validate_reviews


class ReviewValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.raw = self.root / "data/raw/reviews"
        self.raw.mkdir(parents=True)
        self.addCleanup(self.temporary.cleanup)
        self.registry = self.root / "registry.json"
        self.registry.write_text(json.dumps({"status": "approved", "movies": [
            {"movie_id": "internal-m1", "mapping_status": "validated"}]}), encoding="utf-8")

    def row(self, **changes):
        value = {"review_id": "fixture-r1", "movie_id": "internal-m1", "revision": 1,
            "review_text": "  The acting 🎬 works.\r\n", "language_code": "en",
            "created_at": "2026-01-01T00:00:00Z", "moderation_status": "published",
            "is_deleted": False, "source": "consented-export", "source_type": "first_party",
            "consent_version": "fixture-v1", "analysis_permitted": True,
            "training_permitted": False}
        value.update(changes)
        return value

    def write(self, rows):
        path = self.raw / "reviews.jsonl"
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        return path

    def test_preserves_original_text_hash_and_raw_bytes(self):
        row = self.row()
        source = self.write([row])
        before = source.read_bytes()
        output = self.root / "reports/run"
        result = validate_reviews(source, self.registry, output, self.root, write_accepted=True)
        self.assertEqual(result["status"], "complete")
        accepted = json.loads((output / "accepted.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(accepted["review_text"], row["review_text"])
        self.assertEqual(accepted["text_sha256"], hashlib.sha256(row["review_text"].encode()).hexdigest())
        self.assertEqual(source.read_bytes(), before)
        self.assertNotIn(row["review_text"], json.dumps(result))

    def test_missing_registry_blocks_eligibility_without_inventing_ids(self):
        source = self.write([self.row()])
        result = validate_reviews(source, self.root / "not-present.json", workspace=self.root)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["counts"]["accepted"], 0)
        self.assertIn("approved_canonical_registry_missing", result["blockers"])

    def test_provisional_registry_is_rejected(self):
        self.registry.write_text(json.dumps({"status": "approved", "movies": [
            {"movie_id": "movielens:1", "mapping_status": "provisional"}]}))
        with self.assertRaises(ValueError):
            validate_reviews(self.write([self.row()]), self.registry, workspace=self.root)

    def test_consent_synthetic_unknown_movie_and_invalid_timestamp_rejected(self):
        cases = [
            self.row(consent_version=""), self.row(source="synthetic-demo"),
            self.row(movie_id="unknown"), self.row(created_at="2026-01-01"),
            self.row(revision=True), self.row(training_permitted=None)]
        result = validate_reviews(self.write(cases), self.registry, workspace=self.root)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["counts"]["rejected"], len(cases))

    def test_revisions_allowed_but_duplicate_revision_key_rejected(self):
        result = validate_reviews(self.write([self.row(), self.row(revision=2), self.row()]),
                                  self.registry, workspace=self.root)
        self.assertEqual(result["counts"]["duplicate_revision_keys"], 1)
        self.assertEqual(result["counts"]["accepted"], 2)
        self.assertEqual(result["status"], "invalid")

    def test_deleted_and_unmoderated_rows_not_exported(self):
        result = validate_reviews(self.write([self.row(is_deleted=True),
            self.row(review_id="fixture-r2", moderation_status="pending")]),
            self.registry, workspace=self.root)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["counts"]["inactive"], 2)
        self.assertEqual(result["counts"]["accepted"], 0)

    def test_deleted_tombstone_does_not_require_retaining_removed_text(self):
        result = validate_reviews(self.write([self.row(is_deleted=True, review_text=None,
            analysis_permitted=False, training_permitted=False)]),
            self.registry, workspace=self.root)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["counts"]["tombstones_without_text"], 1)
        self.assertEqual(result["counts"]["accepted"], 0)

    def test_output_cannot_overwrite_or_write_raw(self):
        source = self.write([self.row()])
        with self.assertRaises(ValueError):
            validate_reviews(source, self.registry, self.raw / "generated", self.root)
        output = self.root / "run"
        validate_reviews(source, self.registry, output, self.root)
        with self.assertRaises(FileExistsError):
            validate_reviews(source, self.registry, output, self.root)

    def test_missing_cli_reports_missing_without_dataset_creation(self):
        missing = self.root / "absent"
        run = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/preprocess_reviews.py"),
            str(missing), "--workspace", str(self.root)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 3, run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"], "missing")
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
