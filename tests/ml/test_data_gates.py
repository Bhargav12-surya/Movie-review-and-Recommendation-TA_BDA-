"""Generated metadata/permission fixtures; no model fitting or raw review loading."""
from pathlib import Path
import tempfile
import unittest
from ml.common.artifacts import sha256, write_json
from ml.common.config import load_config
from ml.common.gates import reserve_final_test, training_preflight
from ml.multilingual_sentiment.sarcasm_context import attach_sarcasm_context


class DataGates(unittest.TestCase):
    def test_empty_config_data_cannot_start_training_or_create_model_output(self):
        root = Path(__file__).resolve().parents[2]
        config = load_config(root / "ml/sentiment_transformer/config.yaml")
        report = training_preflight(config, component="sentiment_transformer")
        self.assertFalse(report["ready"])
        self.assertFalse(report["training_started"])
        self.assertTrue(report["blockers"])

    def test_final_test_needs_explicit_flag_and_is_reserved_once(self):
        class Bundle:
            manifest_hashes = {"test": "synthetic-hash-for-test-contract-only"}
        with tempfile.TemporaryDirectory(prefix="movieintel-final-test-contract-") as folder:
            path = Path(folder)
            with self.assertRaises(ValueError):
                reserve_final_test(path, Bundle(), "test", False)
            reserve_final_test(path, Bundle(), "test", True)
            with self.assertRaises(FileExistsError):
                reserve_final_test(path, Bundle(), "test", True)

    def test_auxiliary_sarcasm_does_not_change_actual_sentiment_fields(self):
        sentiment = {"task": "multilingual_movie", "label": "negative", "probabilities": {"negative": 0.7, "neutral": 0.2, "positive": 0.1}}
        sarcasm = {"task": "sarcasm", "label": "sarcastic", "probabilities": {"not_sarcastic": 0.1, "sarcastic": 0.9}}
        result = attach_sarcasm_context(sentiment, sarcasm)
        self.assertEqual(result["probabilities"], sentiment["probabilities"])
        self.assertEqual(result["label"], "negative")
        self.assertFalse(result["sentiment_modified"])
        self.assertNotIn("sarcasm_context", sentiment)

    def test_credentials_are_rejected_from_model_configuration(self):
        with tempfile.TemporaryDirectory(prefix="movieintel-secret-config-contract-") as folder:
            path = Path(folder) / "config.yaml"
            # JSON is a YAML subset. This is a synthetic literal,not a credential.
            write_json(path, {"schema_version": 1, "task": "binary_imdb", "data": {},
                              "output_dir": "models/fixture", "api_key": "synthetic-secret-fixture"})
            with self.assertRaises(ValueError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
