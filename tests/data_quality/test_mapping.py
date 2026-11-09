from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dataset_tools.mapping import build_provisional_movie_map, validate_movie_ids
try:
    from .test_io import fixture
except ImportError:
    from test_io import fixture


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = fixture(self.root)

    def test_provisional_keys_preserve_leading_zeros_without_canonical_ids(self):
        result = build_provisional_movie_map(self.source, self.root / "reports/map", self.root)
        values = [json.loads(line) for line in Path(result["artifacts"]["provisional_movies"]).read_text().splitlines()]
        self.assertEqual(values[0]["imdb_id_raw"], "0000001")
        self.assertEqual(values[0]["imdb_id_normalized"], "tt0000001")
        self.assertTrue(all(value["canonical_movie_id"] is None for value in values))
        self.assertTrue(all(not value["externally_verified"] for value in values))
        self.assertEqual(result["status"], "partial")

    def test_tmdb_collision_is_quarantined_without_merging_movies(self):
        text = (self.source / "links.csv").read_text()
        (self.source / "links.csv").write_text(text.replace("0000002,102", "0000002,101"))
        result = build_provisional_movie_map(self.source, self.root / "reports/map", self.root)
        self.assertEqual(result["counts"]["source_movies"], 3)
        self.assertEqual(result["counts"]["tmdb_conflict_groups"], 1)
        quarantined = Path(result["artifacts"]["quarantined_external_ids"]).read_text().splitlines()
        self.assertEqual(len(quarantined), 2)
        candidates = [json.loads(line) for line in Path(result["artifacts"]["external_id_candidates"]).read_text().splitlines()]
        self.assertFalse(any(row["source"] == "tmdb" and row["external_id"] == "101" for row in candidates))

    def test_orphan_and_duplicate_source_links_are_not_silently_accepted(self):
        with (self.source / "links.csv").open("a", newline="") as handle:
            csv.writer(handle).writerows([["999", "999", "999"], ["1", "0000001", "101"]])
        result = validate_movie_ids(self.source)
        self.assertIn("mapping.orphan_source_movie", result["issues"]["counters"])
        self.assertIn("mapping.duplicate_movie_link", result["issues"]["counters"])

    def test_export_refuses_existing_directory(self):
        target = self.root / "reports/exists"
        target.mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            build_provisional_movie_map(self.source, target, self.root)
