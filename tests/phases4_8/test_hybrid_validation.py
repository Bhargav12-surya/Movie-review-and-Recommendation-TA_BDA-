"""Research-weight selection contracts; all records here are synthetic fixtures."""
import copy
import unittest

from ml.common.artifacts import read_json
from recommender.hybrid import recommend
from recommender.validate_hybrid import ROOT, choose_trial, training_profile, validate_plan


class HybridValidationContracts(unittest.TestCase):
    def plan(self):
        return read_json(ROOT / 'configs/recommendation/hybrid_validation_grid.json')

    def test_prespecified_grid_has_fifteen_unique_trials_and_controls(self):
        plan = self.plan()
        validate_plan(plan)
        self.assertEqual(len(plan['trials']), 15)
        for channel in ('als', 'genre', 'popularity'):
            self.assertTrue(any(row['weights'][channel] == 1 for row in plan['trials']))

    def test_zero_sum_and_duplicate_trials_are_rejected(self):
        plan = self.plan()
        plan['trials'][0]['weights'] = {'als': 0, 'genre': 0, 'popularity': 0}
        with self.assertRaises(ValueError):validate_plan(plan)
        plan = self.plan()
        plan['trials'].append(copy.deepcopy(plan['trials'][0]))
        with self.assertRaises(ValueError):validate_plan(plan)

    def test_grid_cannot_claim_serving_approval_or_unavailable_channels(self):
        plan = self.plan(); plan['serving_approved'] = True
        with self.assertRaises(ValueError):validate_plan(plan)
        plan = self.plan(); plan['channels'].append('semantic')
        with self.assertRaises(ValueError):validate_plan(plan)

    def test_research_profile_uses_supplied_training_ratings_without_invented_consent(self):
        movies = {'a': {'genres': ['Drama']}, 'b': {'genres': ['Horror']},
                  'heldout': {'genres': ['Romance']}}
        profile = training_profile({'a': 4, 'b': 1}, movies, 2.75, 2.25)
        self.assertEqual(profile['genre_preferences'], {'Drama': 1.0})
        self.assertEqual(profile['ratings'], {'a': 4, 'b': 1})
        self.assertEqual(profile['seen_movie_ids'], ['a', 'b'])
        self.assertNotIn('personalization_permitted', profile)
        self.assertNotIn('Romance', profile['genre_preferences'])

    def test_infinite_rating_utility_and_changed_tie_break_are_rejected(self):
        plan = self.plan(); plan['rating_utility_scale'] = float('inf')
        with self.assertRaises(ValueError):validate_plan(plan)
        plan = self.plan(); plan['selection_tie_break'] = ['force_als']
        with self.assertRaises(ValueError):validate_plan(plan)

    def test_user_without_training_history_keeps_empty_preferences(self):
        profile = training_profile({}, {}, 2.75, 2.25)
        self.assertEqual(profile['genre_preferences'], {})
        self.assertEqual(profile['ratings'], {})

    def test_selection_follows_ndcg_then_simplicity_and_declared_order(self):
        def trial(name, ndcg, weights, order):
            return {'id': name, 'weights': weights, 'declared_order': order,
                'metrics': {'ndcg@k': ndcg, 'precision@k': .5, 'recall@k': .5}}
        popular = trial('pop', .8, {'als': 0, 'genre': 0, 'popularity': 1}, 0)
        blend = trial('blend', .8, {'als': .5, 'genre': 0, 'popularity': .5}, 1)
        self.assertEqual(choose_trial([blend, popular])['id'], 'pop')
        blend['metrics']['ndcg@k'] = .81
        self.assertEqual(choose_trial([popular, blend])['id'], 'blend')

    def test_cold_candidates_do_not_receive_fabricated_als_scores(self):
        movies = [{'movie_id': 'a', 'genres': ['Drama'], 'eligible': True, 'training_popularity': 50},
                  {'movie_id': 'b', 'genres': ['Comedy'], 'eligible': True, 'training_popularity': 5}]
        profile = {'ratings': {}, 'seen_movie_ids': [], 'genre_preferences': {}}
        config = {'weights_validated': True, 'weights': {'als': 1, 'genre': 0, 'popularity': 0}}
        self.assertEqual(recommend(movies, profile, config, {}, k=1)['recommendations'], [])
        config['weights'] = {'als': 0, 'genre': 0, 'popularity': 1}
        rows = recommend(movies, profile, config, {}, k=1)['recommendations']
        self.assertEqual(rows[0]['movie_id'], 'a')
        self.assertNotIn('als', rows[0]['channels'])


if __name__ == '__main__':
    unittest.main()