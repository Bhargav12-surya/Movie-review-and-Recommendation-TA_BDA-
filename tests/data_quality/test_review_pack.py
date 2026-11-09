"""Synthetic source relationships; these fixtures approve no real mapping."""
from importlib import util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = util.spec_from_file_location("create_phase1_review_pack", ROOT / "scripts/create_phase1_review_pack.py")
module = util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReviewPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "data/raw/movielens"
        self.source.mkdir(parents=True)
        (self.source / "movies.csv").write_text(
            "movieId,title,genres\n1,Synthetic A,Drama\n2,Synthetic B,Comedy\n")
        (self.source / "links.csv").write_text(
            "movieId,imdbId,tmdbId\n1,0000001,123\n2,0000002,123\n")
        self.quarantine = self.root / "quarantine.jsonl"
        self.quarantine.write_text("".join(json.dumps({
            "source_movie_key": f"movielens:{movie}", "source": "tmdb",
            "external_id": "123", "canonical_movie_id": None, "conflict_movie_ids": [1, 2]
        }) + "\n" for movie in (1, 2)))
        self.output = self.root / "artifacts/review"

    def test_creates_only_unapproved_forms_and_preserves_original_ids(self):
        report = module.create_review_pack(self.source, self.quarantine, self.output, self.root)
        self.assertEqual(report["relationship_rows"], 2)
        self.assertEqual(report["decisions_filled"], 0)
        self.assertEqual(report["canonical_ids_assigned"], 0)
        self.assertIn("0000001", (self.output / "mapping_decisions.csv").read_text())
        provenance = json.loads((self.output / "imdb_provenance_to_complete.json").read_text())
        self.assertIsNone(provenance["retrieved_at"])
        self.assertFalse(provenance["approved_for_training"])

    def test_rejects_existing_or_raw_output(self):
        with self.assertRaises(ValueError):
            module.create_review_pack(self.source, self.quarantine, self.source / "generated", self.root)
        module.create_review_pack(self.source, self.quarantine, self.output, self.root)
        with self.assertRaises(FileExistsError):
            module.create_review_pack(self.source, self.quarantine, self.output, self.root)

    def test_rejects_fabricated_or_outdated_external_relationship(self):
        rows = self.quarantine.read_text().replace('"123"', '"999"')
        self.quarantine.write_text(rows)
        with self.assertRaises(ValueError):
            module.create_review_pack(self.source, self.quarantine, self.output, self.root)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
