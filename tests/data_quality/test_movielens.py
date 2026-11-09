from __future__ import annotations

from pathlib import Path
import csv
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dataset_tools.movielens import audit_movielens
try:
    from .test_io import fixture, checksums
except ImportError:
    from test_io import fixture, checksums


class MovieLensTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = fixture(self.root)

    def append(self, filename, row):
        with (self.source / filename).open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerow(row)
        checksums(self.source)

    def run_audit(self, **kwargs):
        return audit_movielens(self.source, workspace=self.root, **kwargs)

    def test_valid_fixture_counts_missing_semantics_and_cold_start(self):
        report = self.run_audit()
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["counts"]["ratings"]["rows"], 3)
        self.assertEqual(report["counts"]["ratings"]["rating_distribution"], {"2.5": 1, "4.0": 1, "5.0": 1})
        self.assertEqual(report["counts"]["coverage"]["tag_only_movies"], 1)
        self.assertEqual(report["counts"]["movies"]["no_genres_listed"], 1)
        self.assertEqual(report["counts"]["links"]["missing_tmdb_ids"], 1)
        self.assertTrue(all(x == "match" for x in report["checksum_comparison"].values()))
        self.assertIn("checksums.txt", report["input_fingerprints"])

    def test_raw_hashes_are_unchanged_and_rejected_metadata_has_no_text(self):
        self.append("tags.csv", ["1", "3", "\u00a0", "104"])
        before = {p.name: p.read_bytes() for p in self.source.iterdir()}
        report = self.run_audit(output=self.root / "reports/run")
        self.assertEqual(report["counts"]["tags"]["rejected"], 1)
        self.assertEqual(report["status"], "invalid")
        rejected = (self.root / "reports/run/rejected_rows.jsonl").read_text()
        self.assertNotIn("\u00a0", rejected)
        self.assertNotIn("tag text", rejected)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.source.iterdir()})

    def test_nan_and_non_half_star_ratings_are_rejected(self):
        self.append("ratings.csv", ["2", "2", "NaN", "104"])
        self.append("ratings.csv", ["2", "3", "3.3", "105"])
        self.assertEqual(self.run_audit()["counts"]["ratings"]["rejected"], 2)

    def test_orphan_movie_is_not_an_accepted_rating(self):
        self.append("ratings.csv", ["2", "999", "4.0", "103"])
        report = self.run_audit()
        self.assertEqual(report["counts"]["ratings"]["accepted"], 3)
        self.assertEqual(report["counts"]["ratings"]["rejected"], 1)
        self.assertIn("ratings.csv.orphan_movie_id", report["issues"]["counters"])

    def test_unsorted_input_does_not_claim_complete_duplicate_check(self):
        self.append("ratings.csv", ["1", "1", "4.0", "100"])
        result = self.run_audit()["counts"]["ratings"]
        self.assertFalse(result["exact_duplicate_check_complete"])
        self.assertIsNone(result["exact_duplicates_in_sorted_groups"])

    def test_same_user_movie_repeated_rating_is_detected(self):
        self.append("ratings.csv", ["2", "1", "5.0", "102"])
        result = self.run_audit()["counts"]["ratings"]
        self.assertEqual(result["repeated_user_movie_pairs"], 1)
        self.assertEqual(result["exact_duplicates_in_sorted_groups"], 1)

    def test_nonadjacent_tag_duplicates_within_sorted_group_are_detected(self):
        self.append("tags.csv", ["1", "3", "other synthetic tag", "104"])
        self.append("tags.csv", ["1", "3", "synthetic fixture tag", "103"])
        result = self.run_audit()["counts"]["tags"]
        self.assertEqual(result["adjacent_exact_duplicates"], 0)
        self.assertEqual(result["exact_duplicates_in_sorted_groups"], 1)

    def test_changed_checksum_is_an_error(self):
        with (self.source / "ratings.csv").open("a", encoding="utf-8") as handle:
            handle.write("2,2,3.0,103\n")
        report = self.run_audit()
        self.assertEqual(report["checksum_comparison"]["ratings.csv"], "mismatch")
        self.assertEqual(report["status"], "invalid")

    def test_sample_mode_is_explicitly_partial(self):
        report = self.run_audit(max_rows=1)
        self.assertEqual(report["scope"], "sample")
        self.assertEqual(report["status"], "partial")
        self.assertTrue(report["blockers"])

    def test_missing_sources_do_not_create_report(self):
        report = audit_movielens(self.root / "missing", self.root / "reports/missing", workspace=self.root)
        self.assertEqual(report["status"], "missing")
        self.assertFalse((self.root / "reports").exists())

    def test_wrong_header_fails_and_expected_counts_are_checked(self):
        (self.source / "movies.csv").write_text("not,the,schema\n", encoding="utf-8")
        checksums(self.source)
        report = self.run_audit(expected_counts={"movies": 3})
        self.assertIn("movies.csv.invalid_header", report["issues"]["counters"])
        self.assertIn("expected_count.movies", report["issues"]["counters"])

    def test_report_inside_raw_is_rejected(self):
        with self.assertRaises(ValueError):
            self.run_audit(output=self.source / "new")

    def test_low_resource_full_scan_returns_partial_without_output(self):
        with (self.source / "ratings.csv").open("r+b") as handle:
            handle.truncate(64 * 1024**2)
        resources = {"disk": {"free_bytes": 19 * 1024**3},
                     "memory": {"available_bytes": 128 * 1024**2}}
        with patch("scripts._verification_common.resource_snapshot", return_value=resources):
            report = self.run_audit(output=self.root / "reports/no-run")
        self.assertEqual(report["status"], "partial")
        self.assertFalse((self.root / "reports").exists())
        self.assertEqual(report["checks_complete"], [])

    def test_missing_manifest_is_not_a_checksum_success(self):
        (self.source / "checksums.txt").unlink()
        report = self.run_audit()
        self.assertEqual(report["status"], "partial")
        self.assertTrue(all(value == "missing" for value in report["checksum_comparison"].values()))
