"""Synthetic corpus fixtures test integrity; these are not model measurements."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dataset_tools.imdb import BUCKETS, audit_imdb, prepare_imdb, resolve_layout
from dataset_tools.splits import (Groups, candidate_fingerprints, normalized_text,
                                 shingle_jaccard, validation_group)


class SplitCalculationTests(unittest.TestCase):
    def test_normalization_is_only_auditing_equivalence(self):
        self.assertEqual(normalized_text(" Good<br /> FILM&nbsp; "), "good film")

    def test_stable_bottom_k_and_jaccard(self):
        a = " ".join(f"word{i}" for i in range(80))
        b = a.replace("word40", "alternative")
        self.assertEqual(candidate_fingerprints(a), candidate_fingerprints(a))
        self.assertGreaterEqual(len(set(candidate_fingerprints(a)) & set(candidate_fingerprints(b))), 4)
        self.assertGreater(shingle_jaccard(a, b), .9)
        self.assertEqual(shingle_jaccard("", ""), 0)

    def test_group_representative_is_order_independent(self):
        a, b = Groups(), Groups()
        for left, right in [("c", "b"), ("a", "c")]:
            a.union(left, right)
        for left, right in [("a", "c"), ("c", "b")]:
            b.union(left, right)
        self.assertEqual(a.find("c"), b.find("c"))
        self.assertEqual(a.find("c"), "a")

    def test_split_is_reproducible_and_validates_fraction(self):
        self.assertEqual(validation_group("source_group", .2, 42), validation_group("source_group", .2, 42))
        with self.assertRaises(ValueError):
            validation_group("x", 0, 42)


class ImdbValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "data/raw/acl_imdb"
        self.expected = {}
        for number, (split, label) in enumerate(BUCKETS):
            folder = self.source / split / label
            folder.mkdir(parents=True)
            rating = {"neg": 1, "pos": 8, "unsup": 0}[label]
            (folder / f"0_{rating}.txt").write_text(
                f"Synthetic fixture review bucket{number} has entirely distinct wording {label} {split}.",
                encoding="utf-8")
            (self.source / split / f"urls_{label}.txt").write_text(
                f"http://www.imdb.com/title/tt{1000000 + number}/usercomments\n", encoding="utf-8")
            self.expected[f"{split}/{label}"] = 1
        (self.source / "README").write_text("Synthetic fixture source documentation.", encoding="utf-8")

    def audit(self, name="audit", **kwargs):
        return audit_imdb(self.source, self.root / "artifacts" / name,
                          workspace=self.root, expected_counts=self.expected, **kwargs)

    def test_full_counts_original_labels_and_raw_hashes_unchanged(self):
        before = {p.relative_to(self.source): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.source.rglob("*") if p.is_file()}
        report = self.audit()
        self.assertEqual(report["counts"]["accepted"], 5)
        self.assertEqual(report["counts"]["train/unsup"], 1)
        self.assertEqual(report["input_stability"]["changed_files"], 0)
        self.assertEqual(report["duplicates"]["byte_identical"]["groups"], 0)
        self.assertEqual(report["leakage"]["source_url_movie_train_test_overlap"], 0)
        self.assertEqual(report["status"], "partial")  # source permission and near checks remain pending
        after = {p.relative_to(self.source): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.source.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_direct_and_nested_layout(self):
        self.assertEqual(resolve_layout(self.source), self.source.resolve())
        nested = self.root / "container/aclImdb"
        (nested / "train").mkdir(parents=True)
        (nested / "test").mkdir()
        self.assertEqual(resolve_layout(nested.parent), nested.resolve())

    def test_missing_corpus_creates_no_output(self):
        report = audit_imdb(self.root / "missing", self.root / "absent_output", workspace=self.root)
        self.assertEqual(report["status"], "missing")
        self.assertFalse((self.root / "absent_output").exists())

    def test_low_resources_stop_api_before_any_output_is_created(self):
        with patch("dataset_tools.imdb.preflight", return_value={
                "measurements": {}, "blockers": ["Low memory fixture"]}):
            report = self.audit()
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["blockers"], ["Low memory fixture"])
        self.assertFalse((self.root / "artifacts/audit").exists())

    def test_oversized_or_invalid_url_lines_are_rejected_without_logging_contents(self):
        (self.source / "train/urls_neg.txt").write_bytes(b"x" * 20000 + b"\n")
        (self.source / "test/urls_neg.txt").write_bytes(b"SECRET_FIXTURE\xff\n")
        report = self.audit()
        self.assertEqual(report["issues"]["counters"]["oversized_movie_url"], 1)
        self.assertEqual(report["issues"]["counters"]["invalid_movie_url_utf8"], 1)
        self.assertNotIn("SECRET_FIXTURE", json.dumps(report))

    def test_rejects_protected_or_existing_output(self):
        with self.assertRaises(ValueError):
            audit_imdb(self.source, self.source / "generated", workspace=self.root)
        self.audit()
        with self.assertRaises(FileExistsError):
            self.audit()

    def test_corrupt_utf8_does_not_echo_text(self):
        marker = "SENSITIVE_FIXTURE_DO_NOT_LOG"
        (self.source / "train/neg/0_1.txt").write_bytes(marker.encode() + b"\xff")
        report = self.audit()
        self.assertEqual(report["status"], "invalid")
        self.assertEqual(report["counts"]["rejected"], 1)
        self.assertNotIn(marker, json.dumps(report))
        self.assertNotIn(marker, (Path(report["artifacts"]["rejected"])).read_text())

    def test_invalid_label_filename_and_empty_text(self):
        (self.source / "train/pos/0_8.txt").rename(self.source / "train/pos/0_1.txt")
        (self.source / "test/neg/0_1.txt").write_text(" \n", encoding="utf-8")
        report = self.audit()
        self.assertEqual(report["counts"]["rejected"], 2)
        self.assertEqual(report["status"], "invalid")

    def test_size_bound_and_sample_scope(self):
        report = self.audit(max_reviews=2)
        self.assertEqual(report["scope"], "sample")
        self.assertEqual(report["counts"]["accepted"], 2)
        report2 = self.audit("smallbound", max_review_bytes=5)
        self.assertEqual(report2["status"], "invalid")
        self.assertEqual(report2["counts"]["rejected"], 5)

    def test_duplicate_source_id_detected(self):
        (self.source / "train/pos/00_8.txt").write_text("Another synthetic fixture.", encoding="utf-8")
        report = self.audit()
        self.assertIn("duplicate_source_review_id", report["issues"]["counters"])

    def test_exact_and_normalized_cross_split_leakage(self):
        train = self.source / "train/neg/0_1.txt"
        test = self.source / "test/neg/0_1.txt"
        test.write_bytes(train.read_bytes())
        report = self.audit()
        self.assertEqual(report["duplicates"]["byte_identical"]["labelled_train_test_groups"], 1)
        self.assertEqual(report["duplicates"]["normalized"]["labelled_train_test_groups"], 1)

    def test_movie_url_overlap_is_only_source_linkage(self):
        target = self.source / "test/urls_neg.txt"
        target.write_bytes((self.source / "train/urls_neg.txt").read_bytes())
        report = self.audit()
        self.assertEqual(report["leakage"]["source_url_movie_train_test_overlap"], 1)
        self.assertTrue(report["leakage"]["source_url_mapping_is_not_a_validated_application_movie_mapping"])

    def test_near_duplicate_candidates_are_verified_but_not_claimed_exhaustive(self):
        text = " ".join(f"syntheticword{i}" for i in range(100))
        (self.source / "train/neg/0_1.txt").write_text(text, encoding="utf-8")
        (self.source / "test/neg/0_1.txt").write_text(text.replace("syntheticword50", "changedword"),
                                                   encoding="utf-8")
        report = self.audit(near_duplicates=True)
        self.assertGreaterEqual(report["near_duplicates"]["verified_cross_split_pairs"], 1)
        self.assertFalse(report["near_duplicates"]["exhaustive"])
        self.assertEqual(report["duplicates"]["normalized"]["labelled_train_test_groups"], 0)

    def test_preparation_preserves_official_test_and_excludes_connected_train(self):
        (self.source / "test/neg/0_1.txt").write_bytes((self.source / "train/neg/0_1.txt").read_bytes())
        report = prepare_imdb(self.source, self.root / "artifacts/prepared",
                              workspace=self.root, expected_counts=self.expected, near_duplicates=False)
        self.assertEqual(report["counts"]["test"], 2)
        self.assertGreaterEqual(report["counts"]["excluded"], 1)
        rows = [json.loads(line) for line in Path(report["artifacts"]["test"]["path"]).read_text().splitlines()]
        self.assertTrue(all(row["source_split"] == "test" for row in rows))
        self.assertTrue(all(row["application_movie_id"] is None for row in rows))
        self.assertEqual({row["label"] for row in rows}, {0, 1})
        self.assertFalse(report["training_authorized"])
        self.assertIn("split_integrity", report)

    def test_preparation_is_deterministic(self):
        kwargs = dict(workspace=self.root, expected_counts=self.expected, near_duplicates=False, seed=11)
        left = prepare_imdb(self.source, self.root / "artifacts/a", **kwargs)
        right = prepare_imdb(self.source, self.root / "artifacts/b", **kwargs)
        for split in ("train", "validation", "test", "excluded", "unsup"):
            self.assertEqual(left["artifacts"][split]["sha256"], right["artifacts"][split]["sha256"])

    def test_missing_cli_returns_nonzero_without_creating_data(self):
        process = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/audit_imdb.py"),
                                  "--source", str(self.root / "not_present")],
                                 capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode, 3)
        self.assertEqual(json.loads(process.stdout)["status"], "missing")


if __name__ == "__main__":
    unittest.main()
