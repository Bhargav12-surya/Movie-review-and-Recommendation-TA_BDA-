"""Generated for later execution only. Synthetic numeric fixtures are not trained models."""
import math
import unittest


class TfidfContracts(unittest.TestCase):
    def test_binary_margin_order_matches_logistic_sigmoid(self):
        from ml.sentiment_tfidf.predict import logits_from_scores
        from ml.common.calibration import softmax
        values = softmax(logits_from_scores([2.0, -2.0], 2))
        self.assertAlmostEqual(values[0][1], 1.0 / (1.0 + math.exp(-2.0)))
        self.assertGreater(values[0][1], values[0][0])
        self.assertGreater(values[1][0], values[1][1])

    def test_multiclass_scores_cannot_silently_become_binary_or_nonfinite(self):
        from ml.sentiment_tfidf.predict import logits_from_scores
        for scores, classes in (([[1, 2, 3]], 2), ([[1, 2]], 3), ([float("nan")], 2)):
            with self.subTest(classes=classes), self.assertRaises(ValueError):
                logits_from_scores(scores, classes)

    def test_settings_preserve_original_signal_and_bound_work(self):
        from ml.sentiment_tfidf.train import settings
        result = settings({"language_scope": ["en"]})
        self.assertEqual(result["ngram_range"], [1, 2])
        self.assertIn("[^", result["token_pattern"])
        for change in ({"regularization_c": float("nan")}, {"max_features": 100001},
                       {"ngram_range": [1, 9]}, {"token_pattern": "()"}, {"estimator": "keyword_lookup"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                settings({"language_scope": ["en"], "tfidf": change})

    def test_portable_linear_calculation_keeps_actual_feature_indices(self):
        import numpy as np
        from scipy.sparse import csr_matrix
        from ml.sentiment_tfidf.predict import probabilities
        class NumericFixture:
            def transform(self, texts):
                return csr_matrix([[1.0, 0.0], [0.0, 1.0]])
        fixture = {"vectorizer": NumericFixture(), "coefficients": np.array([[2.0, -2.0]]),
                   "intercept": np.array([0.0]),
                   "state": {"labels": {"negative": 0, "positive": 1}, "calibration": {"temperature": 1.0}}}
        values, counts = probabilities(fixture, ["synthetic-A", "synthetic-B"])
        self.assertEqual(counts, [1, 1])
        self.assertGreater(values[0][1], values[0][0])
        self.assertGreater(values[1][0], values[1][1])
        self.assertTrue(all(abs(sum(row) - 1.0) < 1e-12 for row in values))

    def test_cohort_support_uses_only_explicit_metadata_and_aligned_outputs(self):
        from types import SimpleNamespace
        from ml.sentiment_tfidf.evaluate import cohort_metrics
        records = [SimpleNamespace(metadata={"language_code": "hi-Latn", "cohorts": ["sarcastic"]}),
                   SimpleNamespace(metadata={})]
        values = [[0.8, 0.2], [0.1, 0.9]]
        result = cohort_metrics(records, [0, 1], values, ["negative", "positive"])
        self.assertEqual(set(result), {"language:hi-Latn", "sarcastic"})
        self.assertEqual(result["sarcastic"]["count"], 1)
        self.assertEqual(result["sarcastic"]["per_class"]["positive"]["support"], 0)
        with self.assertRaises(ValueError):
            cohort_metrics(records, [0], values, ["negative", "positive"])


if __name__ == "__main__":
    unittest.main()
