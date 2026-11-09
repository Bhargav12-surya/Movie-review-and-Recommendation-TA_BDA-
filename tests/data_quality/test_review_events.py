"""Synthetic event transport fixtures, excluded from application/model evidence."""
from importlib import util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = util.spec_from_file_location("publish_review_events", ROOT / "scripts/publish_review_events.py")
events = util.module_from_spec(spec)
spec.loader.exec_module(events)


def fixture(**changes):
    row = {"event_id": "synthetic-event-1", "review_id": "synthetic-review-1", "review_revision": 1,
           "movie_id": "synthetic-canonical-1", "operation": "upsert", "event_time": "2026-01-01T00:00:00Z",
           "positive_probability": 0.7, "neutral_probability": 0.2, "negative_probability": 0.1,
           "model_version": "synthetic-test-model", "canonical_movie_validated": True,
           "consent_eligible": True, "moderation_eligible": True, "is_synthetic": True}
    row.update(changes)
    return row


class ReviewEventTests(unittest.TestCase):
    def setUp(self):
        self.owner = tempfile.TemporaryDirectory(prefix="movieintel-events-test-")
        self.addCleanup(self.owner.cleanup)
        self.root = Path(self.owner.name).resolve()
        self.source = self.root / "input.jsonl"

    def write(self, row):
        self.source.write_text(json.dumps(row) + "\n", encoding="utf-8")

    def test_validate_only_does_not_create_destination_or_change_source(self):
        self.write(fixture())
        original = self.source.read_bytes()
        result = events.process(self.root, self.source, None, True)
        self.assertEqual(result["status"], "validated_only")
        self.assertEqual(result["synthetic_rows"], 1)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_atomic_publication_creates_unique_complete_files(self):
        self.write(fixture())
        destination = self.root / "data/events/ready"
        a = events.process(self.root, self.source, destination, True)
        b = events.process(self.root, self.source, destination, True)
        self.assertNotEqual(a["published_file"], b["published_file"])
        self.assertEqual(len(list(destination.glob("events-*.jsonl"))), 2)
        self.assertEqual(json.loads(Path(a["published_file"]).read_text()), fixture())
        self.assertEqual(list(destination.glob(".unpublished-*")), [])

    def test_synthetic_requires_explicit_permission(self):
        self.write(fixture())
        with self.assertRaises(ValueError):
            events.process(self.root, self.source, None)

    def test_failed_file_never_becomes_visible_to_spark(self):
        self.source.write_text(json.dumps(fixture()) + '\n{"secret-review-text":"private"}\n', encoding="utf-8")
        destination = self.root / "data/events/ready"
        with self.assertRaisesRegex(ValueError, "invalid_event_at_line_2"):
            events.process(self.root, self.source, destination, True)
        self.assertEqual(list(destination.glob("events-*.jsonl")), [])
        self.assertEqual(len(list(destination.glob(".unpublished-*"))), 1)

    def test_nonfinite_nonunit_boolean_probabilities_and_invalid_ids_rejected(self):
        for changes in ({"positive_probability": float("nan")}, {"positive_probability": True},
                        {"positive_probability": 0.9}, {"review_revision": True}, {"movie_id": "../other"},
                        {"event_time": "2026-01-01T00Z"}, {"event_time": "2026-13-01T00:00:00Z"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                events.validate_event(fixture(**changes), True)

    def test_deletion_and_held_revision_can_withdraw_old_evidence(self):
        for operation in ("upsert", "delete"):
            events.validate_event(fixture(operation=operation, consent_eligible=False,
                positive_probability=None, neutral_probability=None, negative_probability=None,
                model_version=None), True)

    def test_raw_output_and_overlapping_watched_source_refused(self):
        self.write(fixture())
        with self.assertRaises(ValueError):
            events.process(self.root, self.source, self.root / "data/raw/out", True)
        watched = self.root / "data/events/ready"
        watched.mkdir(parents=True)
        input_file = watched / "source.jsonl"
        input_file.write_text(json.dumps(fixture()), encoding="utf-8")
        with self.assertRaises(ValueError):
            events.process(self.root, input_file, watched, True)

    def test_unknown_private_fields_and_duplicate_json_keys_rejected(self):
        row = fixture()
        row["review_text"] = "private"
        with self.assertRaises(ValueError):
            events.validate_event(row, True)
        self.source.write_text('{"event_id":"first","event_id":"second"}\n', encoding="utf-8")
        with self.assertRaises(ValueError):
            events.process(self.root, self.source, None, True)


if __name__ == "__main__":
    unittest.main()
