"""Sampler/numeric parity checks; synthetic fixtures are not audience evidence."""
import copy
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

from ml.common.artifacts import read_json
from recommender.compare_popularity import (
    ROOT, negative_items, ranking_metrics, sequential_float32,
    verify_installed_hashes, verify_reproduction,
)


class PopularityComparisonContracts(unittest.TestCase):
    def test_sampling_excludes_seen_items_and_every_heldout_positive(self):
        first = negative_items(7, range(1, 20), {1, 3, 5}, {2, 4, 6}, limit=5)
        second = negative_items(7, reversed(range(1, 20)), {1, 3, 5}, {2, 4, 6}, limit=5)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)
        self.assertFalse(set(first) & {1, 2, 3, 4, 5, 6})

    def test_float32_accumulation_matches_ordered_java_fmul_fadd(self):
        matrix = np.array([[1e8, 1, -1e8, 5]], dtype=np.float32)
        result = sequential_float32(matrix, [1, 1, 1, 1])
        self.assertEqual(result.dtype, np.float32)
        self.assertEqual(float(result[0]), 5.0)
        self.assertEqual(sum(float(x) for x in matrix[0]), 6.0)

    def test_ranking_uses_fixed_k_and_all_positive_support(self):
        result = ranking_metrics([{'relevant': 1}, {'relevant': 0}], positive_count=4, k=10)
        self.assertAlmostEqual(result['precisionAt10'], .1)
        self.assertAlmostEqual(result['recallAt10'], .25)
        ideal = sum(1 / math.log2(index + 2) for index in range(4))
        self.assertAlmostEqual(result['ndcgAt10'], 1 / ideal)

    def fixture(self):
        candidates = [{'movieId': 1, 'relevant': 1, 'cold': False},
                      {'movieId': 2, 'relevant': 0, 'cold': True}]
        saved = {'candidateCount': 2, 'positiveCount': 1, 'coldCandidates': 1, 'k': 10,
                 'precisionAtK': .1, 'recallAtK': 1.0, 'ndcgAtK': 1.0,
                 'topK': [dict(row, position=index + 1) for index, row in enumerate(candidates)]}
        return saved, candidates

    def test_different_saved_ranking_is_not_accepted_as_comparable(self):
        saved, candidates = self.fixture()
        verify_reproduction(saved, candidates, candidates)
        with self.assertRaises(ValueError):
            verify_reproduction(saved, candidates, list(reversed(candidates)))

    def test_changed_candidate_universe_or_support_is_rejected(self):
        saved, candidates = self.fixture()
        with self.assertRaises(ValueError):
            verify_reproduction(saved, candidates + [{'movieId': 3, 'relevant': 0, 'cold': False}], candidates)
        changed = copy.deepcopy(saved)
        changed['positiveCount'] = 2
        with self.assertRaises(ValueError):
            verify_reproduction(changed, candidates, candidates)

    def test_python_xxhash_matches_installed_spark_primitive_kernels(self):
        environment = read_json(ROOT / 'configs/environment.json')
        temporary_root = Path(tempfile.gettempdir()).resolve()
        with tempfile.TemporaryDirectory(prefix='movieintel-xxhash-test-') as directory:
            target = Path(directory).resolve()
            self.assertTrue(target.is_relative_to(temporary_root))
            self.assertTrue(target.name.startswith('movieintel-xxhash-test-'))
            result = verify_installed_hashes(environment, target)
            self.assertTrue(result['passed'])
            self.assertEqual(result['cases'], 8)


if __name__ == '__main__':
    unittest.main()