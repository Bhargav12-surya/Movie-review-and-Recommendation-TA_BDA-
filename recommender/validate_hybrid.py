"""Research-only weight selection on hash-bound, matched validation candidates.

Uses the real shared hybrid ranker/evaluator. It never fits ALS, infers app-user
consent, promotes artifacts, edits serving settings or reads final-test ratings.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
import uuid

from dataset_tools.recordio import iter_records
from ml.common.artifacts import read_json, safe_path, sha256
from recommender.evaluation import evaluate
from recommender.hybrid import recommend
from recommender.profile import build_profile

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = {'als', 'genre', 'popularity'}


def validate_plan(plan):
    trials = plan.get('trials', [])
    if (plan.get('research_only') is not True or plan.get('serving_approved') is not False
            or plan.get('k') != 10 or plan.get('selection_metric') != 'ndcg@k'
            or plan.get('diversity_penalty') != 0 or not 1 <= len(trials) <= 25):
        raise ValueError('Bounded, research-only, prespecified K=10 validation grid required.')
    if set(plan.get('channels', [])) != CHANNELS:
        raise ValueError('This study supports actual ALS, genre and training-popularity channels only.')
    identifiers, configurations = set(), set()
    for trial in trials:
        weights = trial.get('weights', {})
        if (not trial.get('id') or trial['id'] in identifiers or set(weights) != CHANNELS
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not math.isfinite(value) or value < 0 for value in weights.values())
                or not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-12)):
            raise ValueError('Unique declared trial IDs and nonnegative unit-sum weights required.')
        key = tuple(weights[name] for name in sorted(CHANNELS))
        if key in configurations:
            raise ValueError('Duplicate trial weights.')
        identifiers.add(trial['id']); configurations.add(key)
    if not any(trial['weights']['popularity'] == 1 for trial in trials):
        raise ValueError('Include the matched popularity-only control.')
    if not 10 <= plan.get('rerank_pool_size', 0) <= 2000:
        raise ValueError('Bounded reranking pool required.')
    if plan.get('selection_tie_break') != ['precision@k', 'recall@k', 'fewer_active_channels', 'declared_trial_order']:
        raise ValueError('Unsupported selection tie-break policy.')
    if any(isinstance(plan.get(name), bool) or not isinstance(plan.get(name), (int, float))
           or not math.isfinite(plan[name]) for name in ('rating_utility_center', 'rating_utility_scale')) or plan['rating_utility_scale'] <= 0:
        raise ValueError('Finite training-rating utility policy required.')


def training_profile(ratings, catalogue, center, scale):
    """MovieLens research profile; no application permission flags are invented."""
    weights = Counter()
    for identifier, value in ratings.items():
        if identifier not in catalogue or not .5 <= value <= 5 or not math.isfinite(value):
            raise ValueError('Valid source training ratings and catalogue mapping required.')
        utility = max(0.0, (value - center) / scale)
        for genre in catalogue[identifier]['genres']:
            weights[genre] += utility
    mass = sum(weights.values())
    preferences = {genre: value / mass for genre, value in weights.items() if value > 0} if mass else {}
    explicit = {'ratings': dict(ratings), 'seen_movie_ids': sorted(ratings),
                'genre_preferences': preferences, 'theme_preferences': {}}
    # Empty interaction input deliberately avoids asserting application consent.
    profile = build_profile(explicit, [], [], {'rating': 1.0})
    profile['preference_method'] = 'movielens_training_only_positive_rating_utility_research_profile'
    profile['source_scope'] = 'MovieLens research identities; no application consent inferred'
    return profile


def choose_trial(trials):
    if not trials:
        raise ValueError('Actual validation trials required.')
    def ordering(row):
        metrics = row['metrics']
        return (metrics['ndcg@k'], metrics['precision@k'], metrics['recall@k'],
                -sum(value > 0 for value in row['weights'].values()), -row['declared_order'])
    return max(trials, key=ordering)


def parquet_rows(path):
    import pyarrow.parquet as pq
    parquet = pq.ParquetFile(path)
    try:
        for batch in parquet.iter_batches(batch_size=4096, use_threads=False):
            yield from batch.to_pylist()
    finally:
        parquet.close()


def run_study(comparison_dir, grid_path, output):
    started = time.perf_counter()
    grid_hash = sha256(grid_path)
    plan = read_json(grid_path)
    validate_plan(plan)
    comparison_path = comparison_dir / 'report.json'
    comparison_hash = sha256(comparison_path)
    comparison = read_json(comparison_path)
    if (comparison.get('status') != 'passed'
            or comparison.get('kind') != 'matched_validation_popularity_comparison'
            or comparison.get('saved_spark_rankings_reproduced') is not True
            or comparison.get('final_test_evaluated') is not False):
        raise ValueError('A passing matched validation comparison is required.')
    for name, expected in comparison['files_sha256'].items():
        path = safe_path(comparison_dir / name, ROOT)
        if not path.is_relative_to(comparison_dir) or sha256(path) != expected:
            raise ValueError('Comparison snapshot fingerprint changed.')
    run_id = comparison['run_id']
    if not run_id or Path(run_id).name != run_id:
        raise ValueError('Invalid source run identifier.')
    run = safe_path(ROOT / 'models/recommendation' / run_id, ROOT)
    mapping_path = ROOT / 'data/processed/recommendation' / run_id / 'factor_mapping.json'
    mapping = read_json(mapping_path)
    if sha256(mapping_path) != comparison['mapping_sha256'] or sha256(run / 'factor_manifest.json') != comparison['factor_manifest_sha256']:
        raise ValueError('Actual factors or canonical mapping changed.')
    catalogue_dir = ROOT / 'data/processed/catalogue/approved-movielens-32m-v1'
    metadata_path = catalogue_dir / 'catalogue_metadata.jsonl'
    metadata_hash = sha256(metadata_path)
    catalogue_manifest = read_json(catalogue_dir / 'import_manifest.json')
    if metadata_hash != catalogue_manifest['metadata_sha256']:
        raise ValueError('Approved metadata input changed.')
    catalogue = {}
    for row in iter_records(metadata_path):
        identifier = str(row['movie_id'])
        if identifier in catalogue or not isinstance(row['genres'], list):
            raise ValueError('Invalid or duplicate catalogue metadata.')
        catalogue[identifier] = {'movie_id': identifier, 'genres': row['genres'], 'eligible': True}
    if len(catalogue) != catalogue_manifest['movie_count']:
        raise ValueError('Approved catalogue count differs.')
    popularity = {}
    for part in sorted((run / 'training_popularity').glob('*.parquet')):
        for row in parquet_rows(part):
            canonical = mapping['source_to_movie'][str(row['movieId'])]
            if canonical in popularity or row['training_count'] < 1:
                raise ValueError('Invalid exported training popularity.')
            popularity[canonical] = row['training_count']
    if sum(popularity.values()) != comparison['source_counts']['training_rows']:
        raise ValueError('Training popularity scope differs from the candidate study.')
    for identifier, movie in catalogue.items():
        movie['training_popularity'] = popularity.get(identifier, 0)
    histories = defaultdict(dict)
    for row in parquet_rows(comparison_dir / 'sampled_training_history.parquet'):
        user, item = row['source_user_id'], row['movie_id']
        if item in histories[user]:
            raise ValueError('Duplicate sampled training rating.')
        histories[user][item] = row['rating']
    candidate_rows = defaultdict(list)
    for row in parquet_rows(comparison_dir / 'validation_candidates.parquet'):
        candidate_rows[row['source_user_id']].append(row)
    if len(candidate_rows) != comparison['sampled_users'] or sum(map(len, candidate_rows.values())) != comparison['candidate_count']:
        raise ValueError('Matched candidate population differs.')
    if set(histories) - set(candidate_rows):
        raise ValueError('Training snapshot contains users outside the fixed validation sample.')
    movies_by_user, profiles, truth, collaborative, cohorts = {}, {}, {}, {}, {}
    for user, rows in candidate_rows.items():
        ids = [row['movie_id'] for row in rows]
        if len(ids) != len(set(ids)) or any(item not in catalogue for item in ids):
            raise ValueError('Invalid canonical candidates or duplicates.')
        if set(ids) & set(histories[user]):
            raise ValueError('Seen training items entered the candidate sample.')
        if any(row['relevant'] not in (0, 1) for row in rows):
            raise ValueError('Invalid relevance indicators.')
        truth[user] = {row['movie_id'] for row in rows if row['relevant']}
        if not truth[user]:
            raise ValueError('Every sampled ranking user needs eligible validation positives.')
        cold_count = sum(row['cold'] for row in rows)
        cohorts[user] = ('no_cold_candidates' if cold_count == 0 else
                         'all_candidates_cold' if cold_count == len(rows) else 'mixed_candidates')
        collaborative[user] = {}
        for row in rows:
            if row['cold']:
                if row['als_prediction'] is not None:
                    raise ValueError('Cold candidate unexpectedly has an ALS prediction.')
            else:
                value = row['als_prediction']
                if value is None or not math.isfinite(value):
                    raise ValueError('Nonfinite warm ALS prediction.')
                collaborative[user][row['movie_id']] = value
            if catalogue[row['movie_id']]['training_popularity'] != row['training_count']:
                raise ValueError('Candidate and training-popularity snapshots differ.')
        profiles[user] = training_profile(histories[user], catalogue,
            plan['rating_utility_center'], plan['rating_utility_scale'])
        movies_by_user[user] = [catalogue[item] for item in ids]
    print(f'Prepared {len(profiles)} training-only research profiles and {sum(map(len, candidate_rows.values()))} fixed candidates.', flush=True)
    results, rankings_by_trial = [], {}
    for order, trial in enumerate(plan['trials']):
        config = {'weights_validated': True, 'weights': trial['weights'],
                  'diversity_penalty': plan['diversity_penalty'],
                  'rerank_pool_size': plan['rerank_pool_size'], 'filters': {}, 'research_only': True}
        rankings = {}
        for user in sorted(profiles):
            result = recommend(movies_by_user[user], profiles[user], config,
                               collaborative[user], plan['k'])
            rankings[user] = [row['movie_id'] for row in result['recommendations']]
            if trial['weights']['popularity'] == 1:
                expected = [row['movie_id'] for row in sorted(candidate_rows[user],
                    key=lambda row: (-row['popularity_score'], row['movieId']))[:plan['k']]]
                if rankings[user] != expected:
                    raise ValueError('Shared-ranker popularity control did not reproduce the exact matched baseline ranking.')
        metrics = evaluate(rankings, truth, list(catalogue.values()), popularity, plan['k'])
        if trial['weights']['popularity'] == 1:
            for name, original in [('precision@k', 'precisionAt10'), ('recall@k', 'recallAt10'), ('ndcg@k', 'ndcgAt10')]:
                if not math.isclose(metrics[name], comparison['training_popularity'][original], abs_tol=1e-9):
                    raise ValueError('Popularity control metrics differ from the matched baseline.')
        results.append({'id': trial['id'], 'declared_order': order,
                        'weights': trial['weights'], 'metrics': metrics})
        rankings_by_trial[trial['id']] = rankings
        print(f"Trial {order+1}/{len(plan['trials'])}: {trial['id']}; validation NDCG@10={metrics['ndcg@k']:.6f}", flush=True)
    winner = choose_trial(results)
    selected_rankings = rankings_by_trial[winner['id']]
    selected_cohorts = {}
    for name in ('no_cold_candidates', 'all_candidates_cold', 'mixed_candidates'):
        selected_users = {user for user in profiles if cohorts[user] == name}
        measured = evaluate({u: selected_rankings[u] for u in selected_users},
            {u: truth[u] for u in selected_users}, list(catalogue.values()), popularity, plan['k']) if selected_users else {}
        selected_cohorts[name] = {'users': len(selected_users),
            **{key: measured.get(key) for key in ('precision@k', 'recall@k', 'ndcg@k', 'empty_rankings')}}
    if (sha256(grid_path) != grid_hash or sha256(comparison_path) != comparison_hash
            or sha256(metadata_path) != metadata_hash):
        raise ValueError('Study configuration or input metadata changed during evaluation.')
    research_choice = {'research_validation_complete': True, 'weights_validated': False,
        'serving_approved': False, 'selected_trial': winner['id'], 'weights': winner['weights'],
        'scope': 'Interim three-channel sampled validation research choice; not a serving configuration.'}
    with (output / 'selected_research_weights.json').open('x', encoding='utf-8') as handle:
        json.dump(research_choice, handle, indent=2, allow_nan=False)
    with (output / 'trial_metrics.json').open('x', encoding='utf-8') as handle:
        json.dump(results, handle, indent=2, allow_nan=False)
    with (output / 'selected_rankings.jsonl').open('x', encoding='utf-8') as handle:
        for user, items in sorted(selected_rankings.items()):
            handle.write(json.dumps({'source_user_id': user, 'movie_ids': items}) + '\n')
    baseline = comparison['training_popularity']
    return {'status': 'passed', 'kind': 'interim_three_channel_hybrid_validation',
        'run_id': run_id, 'sampled_users': len(profiles), 'candidate_count': comparison['candidate_count'],
        'trial_count': len(results), 'selected_trial': winner['id'], 'selected_weights': winner['weights'],
        'selected_metrics': winner['metrics'], 'selected_cohorts': selected_cohorts,
        'selection_metric': 'ndcg@k', 'selection_tie_break': plan['selection_tie_break'],
        'training_popularity_control_reproduced': True,
        'selected_minus_popularity': {name: winner['metrics'][name] - baseline[old]
            for name, old in [('precision@k', 'precisionAt10'), ('recall@k', 'recallAt10'), ('ndcg@k', 'ndcgAt10')]},
        'users_without_training_ratings': sum(not histories[user] for user in profiles),
        'profiles_with_genre_preferences': sum(bool(profile['genre_preferences']) for profile in profiles.values()),
        'profile_policy': 'Training ratings only; positive utility max(0,(rating-center)/scale), normalized genre mass.',
        'application_consent_inferred': False, 'unavailable_channels': plan['unavailable_channels'],
        'metadata_scope': plan['metadata_scope'],
        'diversity_policy': 'Shared evaluator Jaccard formula; missing-genre limitations remain explicit in the separate diversity audit.',
        'coverage_denominator': len(catalogue),
        'coverage_scope': 'Current approved canonical catalogue, distinct from the Scala train-union-validation denominator.',
        'comparison_report_sha256': comparison_hash, 'grid_sha256': grid_hash,
        'metadata_sha256': metadata_hash, 'source_sha256': sha256(Path(__file__)),
        'files_sha256': {name: sha256(output / name) for name in
            ('selected_research_weights.json', 'trial_metrics.json', 'selected_rankings.jsonl')},
        'duration_seconds': time.perf_counter() - started,
        'retraining_started': False, 'final_test_evaluated': False,
        'serving_approved': False, 'backend_configuration_changed': False,
        'limitation': 'Same 100-user validation sample used for selection; full five-channel hybrid, final test and catalogue-scale serving remain unvalidated.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comparison-directory', required=True)
    parser.add_argument('--grid', default='configs/recommendation/hybrid_validation_grid.json')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({'status': 'planned', 'research_only': True, 'evaluation_executed': False}))
        return 0
    output = ROOT / 'artifacts' / ('hybrid-validation-' + uuid.uuid4().hex)
    output.mkdir(parents=True, exist_ok=False)
    try:
        report = run_study(safe_path(args.comparison_directory, ROOT), safe_path(args.grid, ROOT), output)
    except Exception as error:
        report = {'status': 'failed', 'error_type': type(error).__name__,
            'detail': str(error)[:250] if isinstance(error, (ValueError, RuntimeError)) else
            'Preserve artifacts; inspect local inputs and prerequisites.',
            'retraining_started': False, 'final_test_evaluated': False, 'serving_approved': False}
    report['report_directory'] = str(output)
    report['recorded_at_utc'] = datetime.now(timezone.utc).isoformat()
    with (output / 'report.json').open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())