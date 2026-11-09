from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dataset_tools.io import (IssueCollector, create_output_dir, fingerprint_file,
                              ensure_safe_output, write_json_new)
from dataset_tools.inventory import inventory_raw


def fixture(root: Path) -> Path:
    source = root / "data/raw/movielens/ml-32m"
    source.mkdir(parents=True)
    rows = {
        "movies.csv": [["movieId", "title", "genres"],
                       ["1", "Synthetic A", "Drama"],
                       ["2", "Synthetic B", "(no genres listed)"],
                       ["3", "Synthetic C", "Sci-Fi|IMAX"]],
        "links.csv": [["movieId", "imdbId", "tmdbId"],
                      ["1", "0000001", "101"], ["2", "0000002", "102"],
                      ["3", "0000003", ""]],
        "ratings.csv": [["userId", "movieId", "rating", "timestamp"],
                        ["1", "1", "4.0", "100"], ["1", "2", "2.5", "101"],
                        ["2", "1", "5.0", "102"]],
        "tags.csv": [["userId", "movieId", "tag", "timestamp"],
                     ["1", "3", "synthetic fixture tag", "103"]],
    }
    for filename, values in rows.items():
        with (source / filename).open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerows(values)
    checksums(source)
    return source


def checksums(source: Path) -> None:
    with (source / "checksums.txt").open("w", encoding="utf-8") as handle:
        for name in ("movies.csv", "links.csv", "ratings.csv", "tags.csv"):
            digest = hashlib.md5((source / name).read_bytes()).hexdigest()
            handle.write(f"{digest}  {name}\n")


class SafeOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_protected_paths_and_traversal_are_rejected(self):
        for candidate in ("data/raw/report", "temp/report", ".git/report", ".venv/report",
                          "../outside", "artifacts/.venv/report"):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                ensure_safe_output(candidate, self.root)

    def test_existing_outputs_are_never_overwritten(self):
        directory = create_output_dir("reports/new", self.root)
        write_json_new(directory / "report.json", {"original": True}, self.root)
        with self.assertRaises(FileExistsError):
            write_json_new(directory / "report.json", {"original": False}, self.root)
        with self.assertRaises(FileExistsError):
            create_output_dir(directory, self.root)
        self.assertTrue(json.loads((directory / "report.json").read_text())["original"])

    def test_hashes_are_streamed_and_match_known_bytes(self):
        path = self.root / "input"
        path.write_bytes(b"not research data")
        observed = fingerprint_file(path, ("sha256", "md5"))
        self.assertEqual(observed["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(observed["bytes"], 17)

    def test_issue_sample_is_bounded_but_count_is_exact(self):
        issues = IssueCollector(max_samples=2)
        for index in range(100):
            issues.add("invalid", record=index)
        self.assertEqual(issues.as_dict()["counters"]["invalid"], 100)
        self.assertEqual(len(issues.as_dict()["bounded_samples"]), 2)

    def test_inventory_counts_local_files_and_source_groups(self):
        source = fixture(self.root)
        report = inventory_raw(self.root / "data/raw")
        self.assertEqual(report["counts"]["files"], 5)
        self.assertEqual(report["counts"]["sources"]["movielens"]["files"], 5)
        self.assertEqual(report["status"], "complete")

    def test_missing_inventory_is_explicit(self):
        self.assertEqual(inventory_raw(self.root / "missing")["status"], "missing")
