"""Synthetic label/span/adjudication tests; no genuine annotation data."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dataset_tools.annotations import DEFAULT_CONFIG, load_annotation_config, validate_annotations


class AnnotationValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.raw = self.root / "data/raw/annotations"
        self.raw.mkdir(parents=True)
        self.addCleanup(self.temporary.cleanup)
        self.registry = self.root / "registry.json"
        self.registry.write_text(json.dumps({"status": "approved", "movies": [
            {"movie_id": "m1", "mapping_status": "validated"}]}))

    def row(self, **changes):
        text = "🎬 The acting shines but pacing drags."
        start = text.index("acting")
        value = {"review_id": "fixture-r1", "review_revision": 1, "movie_id": "m1",
            "review_text": text, "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "sentiment": "positive", "label_schema_version": "sentiment-three-class-v1",
            "taxonomy_version": "movie-aspects-v1", "annotator_id": "fixture-a",
            "annotation_status": "annotated", "annotation_guideline_version": "fixture-v1",
            "training_permitted": True, "consent_or_license_ref": "fixture-consent",
            "aspects": [{"aspect": "acting", "start": start, "end": start + 6,
                         "text": "acting", "sentiment": "positive"}], "themes": []}
        value.update(changes)
        return value

    def validate(self, rows, **options):
        path = self.raw / "labels.jsonl"
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        return validate_annotations(path, self.registry, workspace=self.root, **options)

    def test_unicode_original_offsets_and_hash_are_validated(self):
        good = self.row()
        self.assertEqual(self.validate([good])["status"], "complete")
        bad = copy.deepcopy(good)
        bad["aspects"][0]["start"] += 1
        result = self.validate([bad])
        self.assertEqual(result["status"], "invalid")
        self.assertIn("invalid_aspect_span", result["issues"]["counters"])

    def test_wrong_label_boolean_missing_adjudicator_and_hash_rejected(self):
        rows = [self.row(sentiment="mixed"), self.row(sentiment=True),
                self.row(annotation_status="adjudicated"),
                self.row(text_sha256="0" * 64)]
        self.assertEqual(self.validate(rows)["counts"]["rejected"], 4)

    def test_mixed_aspect_requires_explicit_policy(self):
        row = self.row()
        row["aspects"][0]["sentiment"] = "mixed"
        self.assertEqual(self.validate([row])["status"], "invalid")
        self.assertEqual(self.validate([row], allow_mixed=True)["status"], "complete")

    def test_theme_reception_requires_target_specific_span(self):
        row = self.row(themes=[{"theme": "love_and_family", "relevant": True,
                               "sentiment": "positive"}])
        result = self.validate([row])
        self.assertIn("invalid_theme_reception_evidence", result["issues"]["counters"])
        row["themes"][0]["sentiment"] = None
        self.assertEqual(self.validate([row])["status"], "complete")

    def test_overlapping_bio_spans_rejected(self):
        row = self.row()
        duplicate = copy.deepcopy(row["aspects"][0])
        duplicate["aspect"] = "story"
        row["aspects"].append(duplicate)
        self.assertIn("invalid_overlapping_aspect_spans",
                      self.validate([row])["issues"]["counters"])

    def test_pairwise_agreement_calculated_only_from_observed_overlap(self):
        rows = [self.row(), self.row(annotator_id="fixture-b"),
                self.row(review_id="fixture-r2", sentiment="negative"),
                self.row(review_id="fixture-r2", annotator_id="fixture-b", sentiment="positive")]
        result = self.validate(rows)
        pair = result["agreement"]["pairs"][0]
        self.assertEqual(pair["overlapping_items"], 2)
        self.assertEqual(pair["observed_agreement"], 0.5)
        self.assertEqual(pair["cohen_kappa"], 0.0)
        self.assertNotIn("fixture-a", json.dumps(result))

    def test_single_annotator_never_produces_invented_agreement(self):
        result = self.validate([self.row()])
        self.assertEqual(result["agreement"]["pair_count"], 0)

    def test_explicit_synthetic_annotations_cannot_become_human_training_evidence(self):
        self.assertEqual(self.validate([self.row(is_synthetic=True)])["status"], "invalid")

    def test_duplicate_annotator_and_different_revision_text_rejected(self):
        self.assertEqual(self.validate([self.row(), self.row()])["counts"]["rejected"], 1)
        changed = self.row(annotator_id="fixture-b", review_text="Different text.")
        changed["text_sha256"] = hashlib.sha256(changed["review_text"].encode()).hexdigest()
        changed["aspects"] = []
        result = self.validate([self.row(), changed])
        self.assertIn("invalid_inconsistent_review_text_across_annotators", result["issues"]["counters"])

    def test_configuration_cannot_change_required_sentiment_label_mapping(self):
        config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        config["sentiment_labels"]["neutral"] = 2
        path = self.root / "bad-config.json"
        path.write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            load_annotation_config(path)


if __name__ == "__main__":
    unittest.main()
