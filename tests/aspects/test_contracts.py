from dataclasses import replace
import hashlib
import unittest
from ml.aspect_common.data import AspectSpan, ReviewExample
from ml.aspect_common.metrics import pipeline_metrics
from ml.aspect_extraction.windows import TokenWindow
from ml.aspect_extraction.alignment import aligned_labels
from ml.aspect_extraction.decoding import decode_window, merge_candidates


class AspectContracts(unittest.TestCase):
    def test_subword_labels_keep_exact_original_unicode_offsets(self):
        text = "x अभिनय y"
        window = TokenWindow(0, {"input_ids": [0, 1, 2, 3, 4]}, ((0, 0), (0, 1), (2, 4), (4, 7), (8, 9)), (False, True, True, True, True))
        span = AspectSpan("acting", 2, 7, text[2:7], 2)
        labels, _, _ = aligned_labels(window, [span], text, {"O": 0, "B-acting": 1, "I-acting": 2})
        self.assertEqual(labels, [-100, 0, 1, 2, 0])

    def test_span_and_polarity_must_both_match_end_to_end(self):
        gold = {"r": [{"aspect": "acting", "start": 0, "end": 6, "sentiment": "positive"}]}
        predicted = {"r": [{"aspect": "acting", "start": 0, "end": 6, "label": "negative"}]}
        result = pipeline_metrics(gold, predicted, ["acting"])
        self.assertEqual(result["f1"], 0)
        self.assertEqual(result["extraction"]["f1"], 1)

    def test_overlapping_window_duplicates_do_not_inflate_evidence(self):
        row = {"aspect": "acting", "start": 2, "end": 8, "text": "acting", "token_confidence": 0.8}
        merged, report = merge_candidates([row, {**row, "token_confidence": 0.9}])
        self.assertEqual(len(merged), 1)
        self.assertEqual(report["duplicate_window_candidates"], 1)

    def test_incomplete_target_boundaries_do_not_snap_to_nearby_tokens(self):
        window = TokenWindow(0, {"input_ids": [1]}, ((0, 6),), (True,))
        with self.assertRaises(ValueError):
            aligned_labels(window, [AspectSpan("acting", 1, 6, "cting")], "acting", {"O": 0, "B-acting": 1, "I-acting": 2})
