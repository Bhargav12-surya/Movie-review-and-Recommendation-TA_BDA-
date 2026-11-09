import hashlib
import unittest
from scoring.aggregate import aggregate, target_records, EMPTY_MESSAGE
from scoring.policy import ScorePolicy
from scoring.eligibility import probabilities_index


def fixture(identifier, reviewer=None, **changes):
    row = {"movie_id": "canonical-fixture", "review_id": identifier, "review_revision": 1,
        "reviewer_id": reviewer or identifier, "text_sha256": hashlib.sha256(identifier.encode()).hexdigest(),
        "created_at": "2020-01-01T00:00:00Z", "is_deleted": False, "is_synthetic": False,
        "evidence_permitted": True, "moderation_status": "published", "prediction_approved": True,
        "model_version": "synthetic-contract-version", "calibrated": True,
        "probabilities": {"negative": 0.1, "neutral": 0.2, "positive": 0.7}}
    return {**row, **changes}


class ScoreContracts(unittest.TestCase):
    def setUp(self):
        self.policy = ScorePolicy("test-policy", "synthetic-contract-version", 2, 2, 2, 0, None, 0)

    def test_no_evidence_never_displays_prior(self):
        result = aggregate([], "canonical-fixture", self.policy)
        self.assertIsNone(result["score"])
        self.assertEqual(result["message"], EMPTY_MESSAGE)

    def test_genuine_formula_and_distinct_effective_support(self):
        result = aggregate([fixture("a"), fixture("b")], "canonical-fixture", self.policy)
        self.assertAlmostEqual(result["score"], 80)
        self.assertEqual(result["effective_review_count"], 2)

    def test_duplicate_reviewer_cannot_meet_evidence_gate(self):
        result = aggregate([fixture("a", "same-person"), fixture("b", "same-person")], "canonical-fixture", self.policy)
        self.assertIsNone(result["score"])
        self.assertEqual(result["distinct_reviewers"], 1)

    def test_latest_deletion_blocks_previous_revision(self):
        result = aggregate([fixture("a"), fixture("a", review_revision=2, is_deleted=True), fixture("b")], "canonical-fixture", self.policy)
        self.assertIsNone(result["score"])
        self.assertEqual(result["review_count"], 1)

    def test_target_reanalysis_without_evidence_does_not_resurrect_old_target(self):
        target = {"target_type": "aspect", "target_key": "acting", "prediction_approved": True,
            "calibrated": True, "model_version": self.policy.model_version, "probabilities": fixture("x")["probabilities"]}
        rows = target_records([fixture("a", target_predictions=[target]), fixture("a", review_revision=2, target_predictions=[])], "aspect", "acting")
        self.assertEqual(aggregate(rows, "canonical-fixture", self.policy, "aspect", "acting")["review_count"], 0)

    def test_rating_and_personalization_fields_are_not_probabilities(self):
        with self.assertRaises(ValueError):
            probabilities_index({"star_rating": 5, "match_score": 0.9})

    def test_invalid_probabilities_and_weights_fail_explicitly(self):
        with self.assertRaises(ValueError):
            aggregate([fixture("a", quality_weight=-1)], "canonical-fixture", self.policy)
        with self.assertRaises(ValueError):
            probabilities_index({"negative": 0.4, "neutral": 0.5, "positive": 0.7})
