import unittest
from recommender.hybrid import recommend
from recommender.factors import FactorStore
from recommender.evaluation import evaluate


class RecommendationContracts(unittest.TestCase):
    def test_application_numeric_id_never_borrows_movielens_factor(self):
        factors = FactorStore({1: [1.0]}, {2: [0.5]}, {2: "canonical-fixture"}, 1, 0.1)
        self.assertEqual(factors.scores("app:1"), {})
        self.assertEqual(factors.scores("movielens:1"), {"canonical-fixture": 0.5})

    def test_filters_and_seen_exclusion_precede_top_k(self):
        movies = [{"movie_id": "a", "eligible": True, "genres": ["Drama"]},
                  {"movie_id": "b", "eligible": True, "genres": ["Drama", "Romance"]}]
        config = {"weights_validated": True, "weights": {"genre": 1}, "filters": {"required_genres": ["Drama", "Romance"]}, "rerank_pool_size": 10}
        result = recommend(movies, {"genre_preferences": {"Romance": 1}, "seen_movie_ids": ["a"]}, config, k=1)
        self.assertEqual([row["movie_id"] for row in result["recommendations"]], ["b"])
        self.assertEqual(result["recommendations"][0]["score_kind"], "personalized_match_not_audience_sentiment")

    def test_empty_cold_rankings_keep_fixed_k_denominator(self):
        catalogue = [{"movie_id": "a", "genres": ["Drama"]}]
        result = evaluate({"warm": ["a"], "cold": []}, {"warm": ["a"], "cold": ["a"]}, catalogue, {"a": 2}, k=10)
        self.assertAlmostEqual(result["precision@k"], 0.05)
        self.assertEqual(result["empty_rankings"], 1)

    def test_unvalidated_weights_do_not_become_demo_predictions(self):
        with self.assertRaises(ValueError):
            recommend([], {}, {"weights_validated": False})
