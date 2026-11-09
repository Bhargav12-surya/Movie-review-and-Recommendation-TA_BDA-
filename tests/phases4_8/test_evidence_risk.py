import hashlib
import unittest
from ml.common.evidence import snapshot, snapshot_stale
from ml.review_risk.predict import predict
from ml.themes.task import multilabel_metrics


def evidence(identifier, movie="m", **changes):
    text = "Synthetic contract fixture " + identifier
    return {"movie_id": movie, "review_id": identifier, "review_revision": 1, "review_text": text,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(), "language_code": "en", "is_deleted": False,
        "is_synthetic": False, "evidence_permitted": True, "moderation_status": "published",
        "consent_or_license_ref": "synthetic-fixture-only", **changes}


class EvidenceRiskContracts(unittest.TestCase):
    def test_movie_isolation_and_deletion_invalidate_snapshot(self):
        rows = [evidence("a"), evidence("b", movie="other")]
        retained, old = snapshot(rows, "m")
        self.assertEqual(len(retained), 1)
        _, new = snapshot([*rows, evidence("a", review_revision=2, is_deleted=True)], "m")
        self.assertTrue(snapshot_stale(old, new))

    def test_no_behaviour_or_history_does_not_invent_fake_risk(self):
        for text in ("I strongly love this film", "I strongly hate this film"):
            result = predict(text, [])
            self.assertIsNone(result["risk_index"])
            self.assertIsNone(result["automated_fake_verdict"])
            self.assertFalse(result["signals"]["sentiment_used"])

    def test_multilabel_theme_metrics_are_separate_from_sentiment(self):
        result = multilabel_metrics([[1, 0], [0, 1]], [[0.9, 0.1], [0.2, 0.8]], ["time", "family"], [0.5, 0.5])
        self.assertEqual(result["micro_f1"], 1)
        self.assertNotIn("audience_sentiment", result)
