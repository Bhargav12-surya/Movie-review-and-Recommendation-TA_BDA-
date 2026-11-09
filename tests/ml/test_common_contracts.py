"""Generated tests for later execution. These do not train any model."""
import math
from pathlib import Path
import tempfile
import unittest
from ml.common.artifacts import safe_path, write_json
from ml.common.calibration import fit_temperature, softmax
from ml.common.metrics import classification_metrics
from ml.informal_language.language_detection import detect_language
from ml.informal_language.preprocess import feature_view, preserve, utf16_offset
from ml.informal_language.transliteration import transliterate


class CommonContracts(unittest.TestCase):
    def test_known_confusion_and_calibration_calculations(self):
        result = classification_metrics([0, 1], [[0.9, 0.1], [0.2, 0.8]], ["negative", "positive"], bins=2)
        self.assertEqual(result["accuracy"], 1)
        self.assertEqual(result["macro_f1"], 1)
        self.assertEqual(result["confusion_matrix"], [[1, 0], [0, 1]])
        self.assertAlmostEqual(result["multiclass_brier"], 0.05)
        self.assertAlmostEqual(result["negative_log_likelihood"], -(math.log(0.9) + math.log(0.8)) / 2)

    def test_invalid_probabilities_and_missing_data_are_rejected(self):
        for row in ([float("nan"), 0], [0.8, 0.8], [-0.1, 1.1]):
            with self.subTest(row=row), self.assertRaises(ValueError):
                classification_metrics([0], [row], ["negative", "positive"])
        with self.assertRaises(ValueError):
            classification_metrics([], [], ["negative", "positive"])

    def test_temperature_has_finite_normalized_probabilities(self):
        logits = [[3.0, -1.0], [-1.0, 3.0]]
        temperature = fit_temperature(logits, [0, 1])
        self.assertGreater(temperature, 0)
        for row in softmax(logits, temperature):
            self.assertAlmostEqual(sum(row), 1.0)

    def test_neutral_is_not_created_for_binary_task(self):
        from ml.common.config import LABELS
        self.assertEqual(LABELS["binary_imdb"], {"negative": 0, "positive": 1})
        self.assertEqual(LABELS["three_class_movie"]["neutral"], 1)

    def test_unicode_original_offsets_and_browser_conversion(self):
        text = "अच्छी फिल्म 🔥 but slow"
        view = preserve(text)
        start = text.index("🔥")
        self.assertEqual(view.original_span(start, start + 1), (start, start + 1))
        self.assertEqual(utf16_offset(text, start + 1), start + 2)

    def test_feature_views_do_not_change_original_or_assign_sentiment(self):
        original = "Bhai fire 🔥 but slow"
        view = feature_view(original, "remove_for_ablation", {"bhai": "friend"})
        self.assertEqual(view.original, original)
        self.assertNotIn("🔥", view.text)
        begin = view.text.index("friend")
        self.assertEqual(original[slice(*view.original_span(begin, begin + len("friend")))], "Bhai")

    def test_latin_script_does_not_claim_hinglish_language_prediction(self):
        self.assertIsNone(detect_language("acting mast thi")["language_code"])
        self.assertEqual(detect_language("acting mast thi")["status"], "language_model_unavailable")

    def test_missing_transliteration_adapter_abstains(self):
        with self.assertRaises(RuntimeError):
            transliterate("फिल्म अच्छी थी")

    def test_raw_outputs_and_existing_artifacts_are_protected(self):
        with tempfile.TemporaryDirectory(prefix="movieintel-ml-contract-") as folder:
            root = Path(folder)
            with self.assertRaises(ValueError):
                safe_path("data/raw/new", root, output=True)
            target = safe_path("artifacts/record.json", root, output=True)
            write_json(target, {"fixture": "synthetic metadata only"})
            with self.assertRaises(FileExistsError):
                write_json(target, {"replacement": True})


if __name__ == "__main__":
    unittest.main()
