"""Verify saved split evidence with explicitly synthetic source fixtures."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dataset_tools.imdb import BUCKETS, prepare_imdb
from dataset_tools.manifest_validation import validate_imdb_manifests


class ManifestVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "data/raw/acl_imdb"
        expected = {}
        for bucket, (split, label) in enumerate(BUCKETS):
            folder = self.source / split / label
            folder.mkdir(parents=True)
            size = 2 if label == "unsup" else 40
            expected[f"{split}/{label}"] = size
            urls = []
            for number in range(size):
                rating = {"neg": 1, "pos": 9, "unsup": 0}[label]
                (folder / f"{number}_{rating}.txt").write_text(
                    f"Synthetic source fixture distinctgroup{bucket} uniquerecord{number}.",
                    encoding="utf-8")
                urls.append(f"https://www.imdb.com/title/tt{(bucket+1)*100000+number}/\n")
            (self.source / split / f"urls_{label}.txt").write_text("".join(urls), encoding="utf-8")
        self.run = self.root / "artifacts/prepared"
        self.prepared = prepare_imdb(self.source, self.run, workspace=self.root,
                                     expected_counts=expected, near_duplicates=False)

    def verify(self, name="verified"):
        return validate_imdb_manifests(self.run, self.root / f"artifacts/{name}", workspace=self.root)

    def test_valid_saved_manifests_match_source_and_have_class_support(self):
        report = self.verify()
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["counts"]["test"], 80)
        self.assertEqual(report["cross_split_overlap_groups"], {"gid": 0, "norm": 0, "movie": 0})
        self.assertTrue(all(count > 0 for split in ("train", "validation")
                            for count in report["class_support"][split].values()))

    def test_tampered_hash_or_label_fails(self):
        path = self.run / "test.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["raw_sha256"] = "0" * 64
        rows[0]["label"] = True
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        report = self.verify()
        self.assertEqual(report["status"], "invalid")
        self.assertIn("manifest_source_contract_mismatch", report["issues"]["counters"])

    def test_missing_or_duplicate_official_test_records_fail(self):
        path = self.run / "test.jsonl"
        lines = path.read_text().splitlines(keepends=True)
        path.write_text("".join([lines[0], lines[0], *lines[2:]]), encoding="utf-8")
        report = self.verify()
        self.assertEqual(report["status"], "invalid")
        self.assertIn("duplicate_manifest_record", report["issues"]["counters"])
        self.assertIn("source_record_coverage_mismatch", report["issues"]["counters"])

    def test_unknown_or_missing_run_does_not_create_output(self):
        output = self.root / "artifacts/missing-report"
        report = validate_imdb_manifests(self.root / "not_present", output, workspace=self.root)
        self.assertEqual(report["status"], "missing")
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
