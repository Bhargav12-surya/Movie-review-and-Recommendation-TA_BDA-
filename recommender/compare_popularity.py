"""Validation-only matched-candidate ALS/popularity comparison; never fit a model.

Reconstructs the original Spark XXH64 sample, verifies installed-JAR hash parity
and float32 accumulation, and requires exact reproduction of stored top-K lists.
No model selection, final-test evaluation, dependency resolution or DB calls.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import heapq
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import uuid

from ml.common.artifacts import read_json, safe_path, sha256
from recommender.factors import FactorStore

ROOT = Path(__file__).resolve().parents[1]
MASK64 = (1 << 64) - 1
SEED = 42


def hash_int(value: int, seed: int) -> int:
    import xxhash
    return xxhash.xxh64(struct.pack('<i', value), seed=seed & MASK64).intdigest()


def hash_long(value: int, seed: int) -> int:
    import xxhash
    return xxhash.xxh64(struct.pack('<q', value), seed=seed & MASK64).intdigest()


def signed(value: int) -> int:
    return value if value < (1 << 63) else value - (1 << 64)


def negative_items(user: int, universe, seen, truth, limit: int = 100):
    prefix = hash_int(user, SEED)
    def key(movie):
        return signed(hash_long(SEED, hash_int(movie, prefix))), movie
    eligible = (movie for movie in universe if movie not in seen and movie not in truth)
    return heapq.nsmallest(limit, eligible, key=key)


def sequential_float32(matrix, vector):
    """Match ALSModel.$anonfun$predict$1 fmul/fadd bytecode, without FMA."""
    import numpy as np
    matrix = np.asarray(matrix, dtype=np.float32)
    vector = np.asarray(vector, dtype=np.float32)
    if matrix.ndim != 2 or vector.shape != (matrix.shape[1],):
        raise ValueError('Incompatible factor shapes.')
    result = np.zeros(matrix.shape[0], dtype=np.float32)
    for column in range(matrix.shape[1]):
        product = np.multiply(matrix[:, column], vector[column], dtype=np.float32)
        np.add(result, product, out=result)
    return result


def ranking_metrics(top, positive_count: int, k: int):
    if positive_count < 1 or k < 1:
        raise ValueError('Positive evaluation support and K are required.')
    hits = sum(int(row['relevant']) for row in top)
    dcg = sum(int(row['relevant']) / math.log2(index + 2)
              for index, row in enumerate(top))
    ideal = sum(1 / math.log2(index + 2) for index in range(min(k, positive_count)))
    return {'precisionAt10': hits / k, 'recallAt10': hits / positive_count,
            'ndcgAt10': dcg / ideal}


def verify_reproduction(saved, candidates, top):
    actual = [(item['movieId'], int(item['relevant']), bool(item['cold'])) for item in top]
    expected = [(item['movieId'], int(item['relevant']), bool(item['cold']))
                for item in sorted(saved['topK'], key=lambda item: item['position'])]
    if (len(candidates) != saved['candidateCount']
            or sum(int(row['relevant']) for row in candidates) != saved['positiveCount']
            or sum(bool(row['cold']) for row in candidates) != saved['coldCandidates']
            or actual != expected):
        raise ValueError('Saved Spark candidate counts or top-K ranking did not reproduce.')
    measured = ranking_metrics(top, saved['positiveCount'], saved['k'])
    for name, original in [('precisionAt10', 'precisionAtK'),
                           ('recallAt10', 'recallAtK'), ('ndcgAt10', 'ndcgAtK')]:
        if not math.isclose(measured[name], saved[original], abs_tol=1e-10, rel_tol=1e-10):
            raise ValueError('Stored per-user metrics did not reproduce.')
    return measured


def verify_installed_hashes(environment, folder: Path):
    """Tiny Java hash probe; no SparkContext, job, resolver or model load."""
    injected = [key for key in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS')
                if os.environ.get(key)]
    if injected:
        raise ValueError('Unreviewed JVM options are present; inspect their names privately.')
    java = Path(environment['java']['home']) / 'bin/java.exe'
    jars = Path(environment['spark']['home']) / 'jars'
    if not java.is_file() or not jars.is_dir():
        raise ValueError('Installed project Java/Spark paths are unavailable.')
    source = folder / 'SparkHashParity.java'
    source.write_text('''import org.apache.spark.sql.catalyst.expressions.XXH64;
public class SparkHashParity {
  public static void main(String[] args) {
    int[][] cases={{1,1},{1,73483},{200948,292757},{2147483647,2147483647},
                   {42,1},{42,100000},{99999,17},{123456,654321}};
    for (int[] pair : cases) {
      long prefix=XXH64.hashInt(pair[0],42L);
      long userHash=XXH64.hashLong(42L,prefix);
      long candidateHash=XXH64.hashLong(42L,XXH64.hashInt(pair[1],prefix));
      System.out.println(pair[0]+","+pair[1]+","+userHash+","+candidateHash);
    }
  }
}
''', encoding='utf-8')
    result = subprocess.run([str(java), '-Xms32m', '-Xmx192m', '--class-path',
                             str(jars / '*'), str(source)], cwd=folder,
                            capture_output=True, text=True, timeout=45,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode != 0:
        raise RuntimeError('Installed-JAR hash parity probe failed; no comparison accepted.')
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 8:
        raise RuntimeError('Unexpected installed-JAR hash probe output.')
    for line in lines:
        user, movie, user_hash, candidate_hash = map(int, line.split(','))
        prefix = hash_int(user, SEED)
        if (signed(hash_long(SEED, prefix)) != user_hash
                or signed(hash_long(SEED, hash_int(movie, prefix))) != candidate_hash):
            raise ValueError('Python hashing differs from the actual Spark XXH64 class.')
    return {'passed': True, 'cases': len(lines), 'seed': SEED,
            'spark_version': environment['spark']['version'],
            'probe_source_sha256': sha256(source)}


def parquet_rows(directory: Path, columns=None):
    import pyarrow.parquet as pq
    for path in sorted(directory.glob('*.parquet')):
        parquet = pq.ParquetFile(path)
        try:
            for batch in parquet.iter_batches(batch_size=65536, columns=columns,
                                               use_threads=False):
                yield from batch.to_pylist()
        finally:
            parquet.close()


def collect_histories(source: Path, manifest, users, train_end: int, validation_end: int):
    """Bounded projection; no test-period row group is decoded."""
    import numpy as np
    import pyarrow.parquet as pq
    parts = sorted(source.rglob('*.parquet'))
    expected = manifest['input_files_sha256']
    if {path.relative_to(source).as_posix() for path in parts} != set(expected):
        raise ValueError('Cleaned rating file inventory changed.')
    histories = {user: {} for user in users}
    positives = {user: set() for user in users}
    wanted = np.asarray(sorted(users), dtype=np.int32)
    counts = Counter()
    for index, path in enumerate(parts, 1):
        before = (path.stat().st_size, path.stat().st_mtime_ns)
        if sha256(path) != expected[path.relative_to(source).as_posix()]:
            raise ValueError('Cleaned rating fingerprint changed.')
        parquet = pq.ParquetFile(path)
        try:
            timestamp_index = parquet.schema.names.index('timestamp')
            selected = []
            for group_index in range(parquet.metadata.num_row_groups):
                group = parquet.metadata.row_group(group_index)
                if group.num_rows == 0:
                    continue
                stats = group.column(timestamp_index).statistics
                if stats is None or not stats.has_min_max:
                    raise ValueError('Timestamp statistics required to exclude test row groups.')
                if int(stats.min) > validation_end:
                    counts['test_period_rows_not_decoded'] += group.num_rows
                elif int(stats.max) > validation_end:
                    raise ValueError('Row group crosses validation/test boundary; use an explicit Spark export.')
                else:
                    selected.append(group_index)
            if not selected:
                if before != (path.stat().st_size, path.stat().st_mtime_ns):
                    raise ValueError('Excluded input changed during fingerprint inspection.')
                continue
            for batch in parquet.iter_batches(batch_size=65536, row_groups=selected,
                    columns=['userId', 'movieId', 'rating', 'timestamp'], use_threads=False):
                if any(column.null_count for column in batch.columns):
                    raise ValueError('Null cleaned rating field.')
                arrays = [column.to_numpy(zero_copy_only=False) for column in batch.columns]
                identifiers, items, ratings, timestamps = arrays
                counts['training_rows'] += int(np.count_nonzero(timestamps <= train_end))
                counts['validation_rows'] += int(np.count_nonzero(timestamps > train_end))
                for offset in np.flatnonzero(np.isin(identifiers, wanted)):
                    user, item = int(identifiers[offset]), int(items[offset])
                    value = float(ratings[offset])
                    if int(timestamps[offset]) <= train_end:
                        if item in histories[user]:
                            raise ValueError('Repeated sampled training user/item.')
                        histories[user][item] = value
                    elif value >= 4.0:
                        positives[user].add(item)
        finally:
            parquet.close()
        if before != (path.stat().st_size, path.stat().st_mtime_ns):
            raise ValueError('Cleaned rating input changed during comparison.')
        if index % 40 == 0:
            print(f'Inspected {index}/{len(parts)} cleaned rating parts.', flush=True)
    for user in users:
        positives[user].difference_update(histories[user])
        if not positives[user]:
            raise ValueError('A saved evaluation user has no reconstructed eligible positives.')
    return histories, positives, dict(counts)


def mean_metrics(rows):
    return {name: sum(row[name] for row in rows) / len(rows) if rows else None
            for name in ('precisionAt10', 'recallAt10', 'ndcgAt10')}


def compare(config_path, run_path, mapping_path, output: Path):
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    started = time.perf_counter()
    config = read_json(config_path)
    manifest = read_json(run_path / 'factor_manifest.json')
    if (config.get('mode') != 'validation' or manifest.get('evaluation_split') != 'validation'
            or sha256(config_path) != manifest['config_sha256']):
        raise ValueError('Exact completed validation configuration is required; final test is excluded.')
    plan = read_json(config_path.parent / 'run-plan.json')
    build = read_json(ROOT / 'artifacts/scala-build/manual-final-002/build_report.json')
    if sha256(safe_path(plan['jar_path'], ROOT)) != plan['jar_sha256'] or build['jar_sha256'] != plan['jar_sha256']:
        raise ValueError('Original compiled JAR differs from the recorded run.')
    for name, digest in build['source_hashes'].items():
        if sha256(safe_path(name, ROOT)) != digest:
            raise ValueError('Original Scala source hashes differ; review candidate semantics first.')
    for name in ('train_end', 'validation_end', 'rank', 'iterations', 'regularization', 'input_files_sha256'):
        if config[name] != manifest[name]:
            raise ValueError('Completed run and requested configuration differ.')
    factor_manifest_hash = sha256(run_path / 'factor_manifest.json')
    mapping = read_json(mapping_path)
    mapping_hash = sha256(mapping_path)
    mapping_report = read_json(mapping_path.parent / 'mapping_report.json')
    if mapping_report.get('status') != 'factor_mapping_verified' or mapping_report.get('mapping_sha256') != mapping_hash:
        raise ValueError('Verified canonical mapping report does not match this mapping.')
    if mapping.get('factor_manifest_sha256') != factor_manifest_hash:
        raise ValueError('Mapping is bound to a different factor manifest.')
    hash_check = verify_installed_hashes(read_json(ROOT / 'configs/environment.json'), output)
    print('PASS: Python sampler matches installed Spark XXH64 primitives.', flush=True)
    store = FactorStore.load(run_path, mapping_path, ROOT)
    saved = list(parquet_rows(run_path / 'ranking_per_user'))
    if not saved or len(saved) > 100 or len({row['userId'] for row in saved}) != len(saved):
        raise ValueError('Expected 1..100 unique saved validation users.')
    saved_by_user = {row['userId']: row for row in saved}
    if any(row['k'] != 10 or row['negativesPerUser'] != 100 or row['candidateProtocol'] !=
           'all_eligible_positives_plus_hash_sampled_train_items_after_seen_exclusion' for row in saved):
        raise ValueError('Unsupported original ranking protocol.')
    histories, positives, source_counts = collect_histories(
        safe_path(config['input_path'], ROOT), manifest, set(saved_by_user),
        config['train_end'], config['validation_end'])
    popularity = {}
    for row in parquet_rows(run_path / 'training_popularity'):
        identifier, count = row['movieId'], row['training_count']
        if identifier in popularity or count < 1:
            raise ValueError('Invalid exported training popularity.')
        popularity[identifier] = count
    if set(popularity) != set(store.items) or sum(popularity.values()) != source_counts['training_rows']:
        raise ValueError('Training popularity and reconstructed training scope differ.')
    if set(saved_by_user) - set(histories):
        raise ValueError('Missing sampled user histories.')
    all_candidates, per_user, all_histories = [], [], []
    universe = sorted(popularity)
    for number, user in enumerate(sorted(saved_by_user), 1):
        original = saved_by_user[user]
        truth = positives[user]
        negatives = negative_items(user, universe, histories[user], truth)
        candidate_ids = sorted(truth | set(negatives))
        warm_items = [item for item in candidate_ids if user in store.users and item in store.items]
        predictions = {}
        if warm_items:
            matrix = np.asarray([store.items[item] for item in warm_items], dtype=np.float32)
            scores = sequential_float32(matrix, store.users[user])
            predictions = dict(zip(warm_items, (float(value) for value in scores)))
        candidates = []
        for item in candidate_ids:
            if item not in store.source_to_movie:
                raise ValueError('Validation candidate lacks an approved canonical movie ID.')
            cold = item not in predictions
            count = popularity.get(item, 0)
            score = math.log1p(count) if cold else predictions[item]
            candidates.append({'source_user_id': user, 'movieId': item,
                'movie_id': store.source_to_movie[item], 'relevant': int(item in truth),
                'cold': cold, 'training_count': count, 'als_prediction': predictions.get(item),
                'als_with_fallback_score': score, 'popularity_score': math.log1p(count)})
        als_top = sorted(candidates, key=lambda row: (-row['als_with_fallback_score'], row['movieId']))[:10]
        als = verify_reproduction(original, candidates, als_top)
        popular_top = sorted(candidates, key=lambda row: (-row['popularity_score'], row['movieId']))[:10]
        baseline = ranking_metrics(popular_top, len(truth), 10)
        cohort = ('no_cold_candidates' if original['coldCandidates'] == 0 else
                  'all_candidates_cold' if original['coldCandidates'] == original['candidateCount'] else
                  'mixed_candidates')
        per_user.append({'source_user_id': user, 'cohort': cohort,
                         'candidate_count': len(candidates), 'als': als, 'popularity': baseline})
        all_candidates.extend(candidates)
        for item, rating in sorted(histories[user].items()):
            all_histories.append({'source_user_id': user, 'source_movie_id': item,
                'movie_id': store.source_to_movie[item], 'rating': rating})
        if number % 10 == 0:
            print(f'Reproduced Spark sample and compared {number}/{len(saved)} users.', flush=True)
    parts = sorted((run_path / 'ranking_metrics').glob('part-*.json'))
    if len(parts) != 1:
        raise ValueError('Expected one saved aggregate validation metric file.')
    original_metrics = read_json(parts[0])
    als_mean = mean_metrics([row['als'] for row in per_user])
    for name, value in als_mean.items():
        if not math.isclose(value, original_metrics[name], rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError('Stored aggregate ALS metrics failed independent reproduction.')
    schema = pa.schema([('source_user_id', pa.int32()), ('movieId', pa.int32()),
        ('movie_id', pa.string()), ('relevant', pa.int8()), ('cold', pa.bool_()),
        ('training_count', pa.int64()), ('als_prediction', pa.float32()),
        ('als_with_fallback_score', pa.float64()), ('popularity_score', pa.float64())])
    pq.write_table(pa.Table.from_pylist(all_candidates, schema=schema), output / 'validation_candidates.parquet')
    history_schema = pa.schema([('source_user_id', pa.int32()), ('source_movie_id', pa.int32()),
                               ('movie_id', pa.string()), ('rating', pa.float64())])
    pq.write_table(pa.Table.from_pylist(all_histories, schema=history_schema), output / 'sampled_training_history.parquet')
    with (output / 'per_user_comparison.jsonl').open('x', encoding='utf-8') as handle:
        for row in per_user:
            handle.write(json.dumps(row, allow_nan=False) + '\n')
    cohorts = {}
    for name in ('no_cold_candidates', 'all_candidates_cold', 'mixed_candidates'):
        group = [row for row in per_user if row['cohort'] == name]
        cohorts[name] = {'users': len(group), 'als_with_fallback': mean_metrics([row['als'] for row in group]),
                         'training_popularity': mean_metrics([row['popularity'] for row in group])}
    if sha256(run_path / 'factor_manifest.json') != factor_manifest_hash or sha256(mapping_path) != mapping_hash:
        raise ValueError('Factor manifest or mapping changed during comparison.')
    baseline_mean = mean_metrics([row['popularity'] for row in per_user])
    return {'status': 'passed', 'kind': 'matched_validation_popularity_comparison',
        'run_id': manifest['approved_run_id'], 'sampled_users': len(per_user),
        'candidate_count': len(all_candidates), 'source_counts': source_counts,
        'installed_spark_hash_parity': hash_check, 'saved_spark_rankings_reproduced': True,
        'als_with_fallback': als_mean, 'training_popularity': baseline_mean, 'cohorts': cohorts,
        'als_minus_popularity': {name: als_mean[name] - baseline_mean[name] for name in als_mean},
        'candidate_protocol': 'identical_saved_users_all_eligible_positives_plus_100_signed_xxhash64_sampled_unseen_train_items',
        'popularity_policy': 'training rating count; descending score, ascending numeric source movie ID ties',
        'factor_manifest_sha256': factor_manifest_hash, 'mapping_sha256': mapping_hash,
        'config_sha256': sha256(config_path), 'comparison_source_sha256': sha256(Path(__file__)),
        'source_namespace': 'movielens; application accounts do not borrow these identities',
        'files_sha256': {name: sha256(output / name) for name in ('validation_candidates.parquet',
            'sampled_training_history.parquet', 'per_user_comparison.jsonl')},
        'duration_seconds': time.perf_counter() - started,
        'retraining_started': False, 'final_test_evaluated': False,
        'model_selected_or_frozen': False, 'backend_configuration_changed': False,
        'limitation': 'Sampled retrospective validation only; not a full-catalogue or final-test performance claim.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--run-directory', required=True)
    parser.add_argument('--mapping', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({'status': 'planned', 'training_started': False, 'evaluation_executed': False}))
        return 0
    output = ROOT / 'artifacts' / ('als-popularity-comparison-' + uuid.uuid4().hex)
    output.mkdir(parents=True, exist_ok=False)
    try:
        report = compare(safe_path(args.config, ROOT), safe_path(args.run_directory, ROOT),
                         safe_path(args.mapping, ROOT), output)
    except Exception as error:
        report = {'status': 'failed', 'error_type': type(error).__name__,
                  'detail': str(error)[:250] if isinstance(error, (ValueError, RuntimeError)) else
                  'Retain comparison artifacts; inspect local prerequisites and inputs.',
                  'retraining_started': False, 'final_test_evaluated': False}
    report['report_directory'] = str(output)
    report['recorded_at_utc'] = datetime.now(timezone.utc).isoformat()
    with (output / 'report.json').open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())