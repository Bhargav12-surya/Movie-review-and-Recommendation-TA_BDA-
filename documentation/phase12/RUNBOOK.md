# Phase12 source and later execution

Prepared10 November2026,Asia/Calcutta. Latest authorization is file generation
only. No test,model inference,benchmark,DB operation,Spark job,build,browser or
service is executed by this delivery. Static source checks are reported
separately. The user will run the following after closing the earlier gates.

## Objectives and source

Prove the integrated localhost journey,actual model loading,DB ownership/revision
safety,batch/stream/scoring consistency,failure recovery and laptop resource
limits. Use actual measured evidence and keep empty/skipped/blocked scopes open.

| Responsibility | Source |
|---|---|
| Controlled group runner | validation/runner.py,testing.py; scripts/evaluate_all.ps1 |
| Read-only latency/resources | validation/benchmark.py,resources.py |
| Actual local model load/infer/reload | validation/model_smoke.py |
| Genuine score export/shared Scala arithmetic | validation/score_export.py; scala/src/main/scala/com/movieintel/validation/ScoreParityJob.scala |
| Text-free current-state Parquet export | validation/state_export.py |
| Score and batch/stream-state comparison | validation/parity.py |
| Human grounding/query/WER study | validation/grounding.py |
| Genuine metrics/acceptance evidence register | validation/evidence.py,reporting.py |
| Read-only rehearsal,curated permitted bundle | validation/rehearsal.py,bundle.py; scripts/rehearse_demo.ps1,prepare_evaluation_bundle.ps1 |
| CLI and bounded fresh I/O | validation/cli.py,io.py |
| API/vector/worker/queue/revision/concurrency tests | backend/tests/ |
| Real browser/text/voice failure paths | frontend/tests/; existing Playwright config has no auto-start server |
| Parser and mathematical report guards | discovery/tests/; tests/integration/test_validation.py |
| Final report comparison notebook | notebooks/15_final_model_comparison.ipynb; disabled,unexecuted |

Current source fixes a queue saturation defect: dedupe is checked before
capacity,only the single leased worker may use two reserved child slots,and
event/refresh jobs drain before more analysis. External admissions retain their
configured limit. This is a prepared fix,not an executed concurrency result.

## Dependencies and execution order

1. Close Phase1 source rights/canonical mapping/annotation gates and Phase2 real
   build/runtime/Parquet/stream evidence. Run separately approved models and
   recommendation studies in Phases3–8. Source presence does not close them.
2. Manually verify/install reviewed prerequisites. Backend TestClient needs the
   additional candidate `httpx==0.28.1` in `requirements/requirements-integration.txt`.
   The [official release](https://pypi.org/project/httpx/0.28.1/) supports Python3.11;
   a full resolved/installed stack still needs actual compatibility checks.
   No new psutil,cloud service,monitoring server or Docker is required by these
   tools. PyArrow is needed only for actual Parquet projection. Optional plotting
   in notebook15 uses already-installed Matplotlib; it never installs it.
3. Run source verification first. Default evaluation runner prints a plan only:

   ```powershell
   .\.venv\Scripts\python.exe -I -B scripts/verify_all_sources.py
   .\scripts\evaluate_all.ps1 -Groups unit
   # Only later,when executing tests is intended:
   .\scripts\evaluate_all.ps1 -Groups unit -Execute
   ```

4. Set up an existing disposable local database ending `_test` or `_tests`,with
   pgvector already installed by its owner. Privately provide
   `MOVIE_TEST_DATABASE_URL`; do not write its value into a report,command argument
   or Git. Enable `RUN_POSTGRES_TESTS=1`. The rollback-only harness creates its
   own transactionally isolated schema. True two-connection tests additionally
   require `RUN_POSTGRES_CONCURRENCY=1`; their separate committed-schema harness
   owns and drops only its random `movie_test_...` schema. Read
   `backend/tests/README.md` and the harness before authorizing those DB writes.
5. Execute PostgreSQL tests before application setup on genuine data:

   ```powershell
   .\scripts\evaluate_all.ps1 -Groups postgres -Execute
   ```

   Missing packages,zero tests,skips,expected failures or disabled concurrency
   do not pass complete acceptance. The custom unittest reporter emits static
   case IDs,status,duration and error type only. It suppresses private messages,
   request bodies,tracebacks and credentials. To debug,inspect source and run an
   individual isolated test manually; never publish unreviewed console output.
6. Follow the through11 runbook for actual DB migration,canonical import,admin,
   model admission,policy setup,API/worker/frontend start. No evaluation tool
   starts services,installs browsers,resolves SBT or trains an NLP/ALS model.
7. Manually prepare an installed Playwright browser. Enable `RUN_LOCAL_E2E=1`,
   select genuine `E2E_MOVIE_ID` and a disposable evaluation account with private
   `E2E_EMAIL`/`E2E_PASSWORD`. Set opt-ins required by each scenario. Review write
   tests use a genuine permitted `E2E_REVIEW_TEXT`,never a fabricated audience
   opinion. Keep synthetic fixtures confined to the disposable DB test schema.
   Actual model checks require `E2E_REQUIRE_MODELS=1`; without it submission
   persistence alone does not establish NLP integration. Then:

   ```powershell
   .\scripts\evaluate_all.ps1 -Groups browser -Execute -AllowBrowser
   ```

   The browser reporter excludes failure snippets,annotations,console text,
   screenshots and traces. Tests may deliberately abort a network request to
   verify error/fallback behavior; they never manufacture model predictions.
8. Prepare reviewed local copies of the example configs below. All scientific/
   benchmark configs require `execution_approved:true` and a reviewer. Empty
   examples deliberately block rather than report fake measurements. Optional
   groups are selected explicitly; default suite paths are null.
9. Run model reload checks only with actual trained,permission-backed artifacts
   and1–4 real permitted inference samples. This check loads twice and compares
   actual outputs; it does not train,retune or reopen final-test selection:

   ```powershell
   .\.venv\Scripts\python.exe -m validation.cli models --config configs/validation/local-model-smoke.json --execute
   ```

   Samples are JSONL with original `text`,`text_sha256`,`language_code`,
   `inference_permitted:true`,`is_synthetic:false`,`is_deleted:false`,and
   `consent_or_license_ref`. No samples are generated here. Use explicit CPU or
   verified CUDA; there is no silent GPU-to-CPU fallback. Separate actual training
   checkpoint/resume-equivalence evidence remains mandatory; matching inference
   reloads does not prove optimizer/scheduler/scaler/RNG resume correctness.
10. Measure a small real GET workload using a reviewed benchmark config:

    ```powershell
    .\.venv\Scripts\python.exe -m validation.cli benchmark --config configs/validation/local-benchmark.json --execute
    ```

    At most100 requests,1–4 concurrent requests,a5–300second scheduling budget,
    per-request timeout and RAM headroom guard. Default concurrency is1. Only
    loopback HTTP ports3000/8000 are permitted,no redirects/proxies/query-string
    credentials. Authenticated GETs can refer only to private
    `MOVIE_EVALUATION_TOKEN`; tokens/bodies never enter reports. Metrics include
    first observed vs subsequent successful p50/p95,error/blocked counts,elapsed
    throughput and real available RAM/process working-set/device GPU samples.
    Headers-only timing is not total body-transfer time; first observed is not a
    proven cold model cache. Sampling may miss peaks and GPU memory is device-wide.

## Scoring and streaming parity

These are distinct studies. Current stream analytics expose unadjusted model
inputs and a null final score. They must not be compared as if they were the
reviewed,weighted/shrunk application score.

For genuine Python/Scala score arithmetic:

1. Prepare an approved current prediction JSONL snapshot under processed data,
   retaining actual revision,identity,permission,calibration,model and probability
   fields consumed by `scoring.eligibility`. Review source rights and policy.
2. Fill `score_export.example.json` in a new local file: exact source hash,
   reviewed policy/approval paths and1–1000 actual canonical movie IDs. Run:

   ```powershell
   .\.venv\Scripts\python.exe -m validation.cli score-export --config configs/validation/local-score-export.json --execute
   ```

   A fresh artifacts/phase12 directory contains actual eligible probability rows,
   declared movie scope,Python scores and a hashed export manifest. It writes no
   original review text. Empty-evidence movies retain null scores and zero counts.
3. Compile the final Scala JAR with the manually installed exact toolchain after
   approving actual build execution. Run the new
   `com.movieintel.validation.ScoreParityJob` through installed spark-submit with
   arguments: absolute workspace,actual export directory,new artifacts output.
   Use controlled `--master local[2] --driver-memory 3g` only after resource
   preflight. The Scala job performs real `ReviewAnalytics` arithmetic and writes
   a bounded single-part JSON export,with explicit null fields. No Python is called.
4. Point a reviewed parity config at `python_scores.jsonl` and the actual Spark
   `part-*.json` file. Freeze both hashes,copy the exact exported scope and use
   `kind:"score"`. Run `validation.cli parity --config <local-config> --execute`.
   Model,method,policy,eligible-evidence hashes,counts,raw/final scores and null
   evidence messages must match. Scala does not implement Python bootstrap
   uncertainty; that gap is explicitly reported rather than claimed comparable.

For batch versus stream final current state:

1. Execute existing Scala stream/replay/restart/late/deletion/conflict tests and
   the genuine event pipeline later; preserve checkpoints and immutable commits.
   Never delete/reuse checkpoints to make a replay look clean.
2. Independently prepare the reference batch and final stream `current_reviews`
   Parquet snapshots. Retain quarantine history and commit/event manifests.
3. Project each with a reviewed `state_export.example.json` copy using
   `validation.cli state-export --config <local-config> --execute`. The projection
   checks input file hashes and exports existing text-free state fields only.
4. Set `kind:"state"` in a new parity config,freeze both projected file hashes
   and run parity. Late tombstones must not revive older upserts. Declared
   pending review IDs keep the result incomplete; they are not ignored as passes.
   A final state match alone does not prove restart/replay/atomicity behavior.

## Grounding,query and voice measurements

Create genuine permitted human-reviewed cases under the supplied JSON schema
`schemas/validation/grounding_case.schema.json`. There is no synthetic academic
evaluation dataset bundled here. Normalize actual service outputs into frozen
JSON records retaining `model_version`,`evidence_snapshot_sha256`,`evidence_ids`
and actual intent. Keep source output/provenance,not an invented label wrapper.
Voice outputs use the actual `text` and `model_revision` returned by speech.

Each case binds its actual output path/hash,model or parser version,held-out split,
human reviewer,permission reference and complete human support judgments.
Supported claims must cite actual frozen evidence IDs. Record contradictions,
unsupported claims,abstentions,expected intent and constraint correctness. Voice
cases contain privately permitted human reference transcripts. Run:

```powershell
.\.venv\Scripts\python.exe -m validation.cli grounding --config configs/validation/local-grounding.json --execute
```

The report calculates actual supported/unsupported/contradicted claim fractions,
intent/constraint accuracy and corpus WER where ground truth exists. WER uses
NFC+casefold whitespace tokenization,preserves punctuation,has the reference-word
denominator and may exceed1. Missing task support produces null metrics. Human
annotation quality,inter-annotator agreement and representative coverage require
their own evidence. No private query,claim text or transcript is written to results.

## Evidence freeze and optimization

Fill a new evidence config with genuine report path/hash,task,protocol ID,
reviewer and provenance bindings. `metric_pointers` are JSON pointers to numeric
measured values; `check_pointers` name actual executed status/count checks.
Declare `evaluation_role` as held_out_test,validation,calibration_diagnostic,
runtime_acceptance or exploratory. A held-out study must reference a real
`split:test` report; tuning/calibration values cannot become test results.
Requirements map concrete acceptance IDs to needed study IDs. Empty registers
remain incomplete. Build the register and Markdown result table with:

```powershell
.\.venv\Scripts\python.exe -m validation.cli evidence --config configs/validation/local-evidence.json --execute
```

Only compare studies with the same task and frozen split/candidate protocol.
Use notebook15 to read real records and optionally export actual plots. It is
disabled by default and never retrains or chooses a model on test values.

Tune only after actual baseline measurements: inference micro-batches,sequence
length/lazy-loading strategy,CPU thread limits,queue capacity,SQL indexes and
vector/candidate strategy. Preserve each reviewed config/code/input hash and
report before/after with actual denominators. No optimization gain is claimed
here. See the final academic report for scientific limitations and unimplemented
theme/genre reception or optional coursework gaps.

Completion requires actual user journey,DB/model/Spark/stream/failure/offline
evidence and reviewed laptop headroom. Phase13 then uses the real register,
rehearsal and a distribution-reviewed allowlist. Generated tests,skips,planned
commands,prepared bundles and recorded numbers alone do not close every gate.
