# Matched ALS and popularity validation

Added 12 November 2026 (Asia/Calcutta). Run manually from the project root:

```powershell
.\.venv\Scripts\python.exe -B -m recommender.compare_popularity `
  --config 'configs/local/als-validation-c8378830710a4feeb97d5671a9542ba1/als-validation.json' `
  --run-directory 'models/recommendation/als-validation-c8378830710a4feeb97d5671a9542ba1' `
  --mapping 'data/processed/recommendation/als-validation-c8378830710a4feeb97d5671a9542ba1/factor_mapping.json' `
  --execute
```

Without `--execute`, the command is a plan only. It never fits a model, installs,
downloads, writes to PostgreSQL, edits backend settings or evaluates final test.
Each execution creates a fresh `artifacts/als-popularity-comparison-*` directory.
A failure preserves partial evidence and must not be interpreted as a comparison.

The sampler is tied to the original compiled Scala source and actual installed
Spark XXH64 Java primitives. It reuses the exact saved evaluation users, includes
all their eligible validation positives (rating >=4), excludes training-seen
pairs, and samples up to100 unseen training movies per user using Spark's signed
hash ordering. Sampling is not replaced by Python random or unsigned ordering.

Training histories are reconstructed with bounded Parquet projections. SHA256
fingerprints are checked, and row groups wholly beyond the validation cutoff are
not decoded. A row group straddling the cutoff is rejected rather than silently
reading test labels. The supplied year-partitioned input supports this policy.

Exported factors are verified through the real FactorStore. ALS predictions use
ordered float32 multiply/add to reproduce the installed ALSModel transform. Cold
predictions retain the original disclosed `log1p(training_count)` fallback. The
baseline ranks *every* identical candidate by training popularity, with numeric
MovieLens movie ID tie-breaking. It uses no held-out popularity or future ratings.

Acceptance requires identical candidate/positive/cold counts, exact saved top-K
movie/relevance/cold sequences and matching per-user and aggregate metrics.
Otherwise the command reports failure and publishes no passing comparison.

A passing run saves `report.json`, `per_user_comparison.jsonl`,
`validation_candidates.parquet` and `sampled_training_history.parquet`, with file
hashes, cold-cohort results and model/config/mapping provenance. Source user IDs
remain anonymous MovieLens identities, separate from application account UUIDs.
The snapshots are local derived data under the original dataset restrictions.

These are sampled validation results, not full-catalogue or final-test metrics.
No winner is automatically promoted, no weights are approved, and no model is
frozen. A popularity win must be reported honestly and should motivate examination
of candidate difficulty, cold-start composition and the mixed fallback scales.

Six focused tests passed during source preparation, including actual installed
Spark hash-kernel parity. The full real-data comparison is pending user execution.
Run the focused tests with:

```powershell
.\.venv\Scripts\python.exe -B -m unittest tests.phases4_8.test_popularity_comparison -v
```