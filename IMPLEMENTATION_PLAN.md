# Implementation plan: movie review and recommendation system

Audit date: 8 November 2026, Asia/Calcutta. Workspace: D:\BDA_TA.

Original audit status: inspection was complete on 8 November 2026 and stopped for approval. Subsequent user instructions authorized implementation. On 9 November 2026 (Asia/Calcutta), the user explicitly approved dependency-based Phase 2 progress against validated local MovieLens inputs while Phase 1 provenance, canonical mappings and NLP annotations remain open. This is the accepted gate exception; the other phase dependencies remain. Software/dataset/model acquisition stays manual, build dependency resolution needs authorization, and substantial training is not approved. See IMPLEMENTATION_STATUS.md for actual evidence rather than treating this plan as completion.

Latest scope on 9 November 2026: **generate files only; the user will implement/run them later**. Phase 3 sentiment and mandatory language-extension files are now prepared without asserting Phase 2 runtime acceptance. Current verification is static source/configuration validation only. No new model fitting, evaluation, unit-test execution, Spark jobs, installations, downloads or services are part of this delivery. Follow documentation/phase3/RUNBOOK.md for later execution. This explicit source-only exception supersedes statements below that would defer all Phase 3 file creation; their execution/data acceptance criteria remain.

## 1. Specification, scope, and complete system understanding

Source expansion,10 November2026: the user requested files through Phase8 in one
pass. Phase4-8 source/configuration/notebooks/tests/docs are prepared under the
existing file-generation-only boundary. This supersedes any below wording that
would defer these file creations until earlier runtime acceptance. It does not
waive training,rights,canonical mapping,model selection,Spark execution or phase
exit criteria. The actual later execution sequence is in
documentation/phases4-8/RUNBOOK.md. No backend/frontend/chat deployment is included.

The entire root ARCHITECTURE.md was read, including its hardware-specific section 32. Its SHA-256 at inspection was 52E0E9ED68F743C3B44913D6C079F177787DA3814A0BD38C88AAE24BE37621E3. The latest user instructions override its older download commands, compressed phase numbering, and optional-feature tiers.

The goal is one integrated, locally executable academic application with three intelligent systems:

1. Review intelligence: persist a real movie-linked review; return trained positive/negative/neutral probabilities; extract aspects and classify each aspect's sentiment; assess suspicious-review signals; publish evidence-qualified movie, aspect, genre and theme reception; and generate a grounded review summary.
2. Personalized recommendations: combine Scala Spark MLlib ALS, content/semantic features, genres/themes, explicit preferences and interaction history; handle cold starts; return explanations derived from actual component inputs.
3. Conversational discovery: resolve movie entities, parse genre/theme/runtime/mood constraints and follow-up context, retrieve actual catalogue/review evidence, call the same recommendation service, and support text plus optional offline voice transcription.

Python owns NLP training/inference. Scala independently owns real Spark ingestion, cleaning, joins, aggregates, MLlib and streaming. FastAPI integrates services with PostgreSQL/pgvector. Next.js/React provides the actual product interface. Large intermediate data lives in Parquet; versioned approved models and metadata are available locally before evaluation.

The semantic contract is fundamental: movie metadata, explicit audience star ratings, review sentiment, theme relevance, theme reception, genre reception and personalized match scores are different values. Missing evidence produces a null score and the message "Not enough audience reviews yet." No prior, metadata rating, recommendation similarity, synthetic review or heuristic substitute may masquerade as an observed audience score.

The final demonstration uses frontend localhost:3000, backend localhost:8000, API docs localhost:8000/docs and PostgreSQL localhost:5432. JupyterLab8888 and Spark UI4040 are started only when needed. Core inference requires no paid service or internet connection.

### Source precedence and phase reconciliation

| Specification issue | Resolution in this plan |
|---|---|
| Architecture section 20 groups work into phases0–8 | Follow the user's more detailed phases0–13 below; retain all technical deliverables |
| Architecture includes automated dataset download commands | User manually supplies data; do not run those commands or fetch datasets |
| Earlier architecture calls aspects/chat strongly recommended | Latest user requires them; they remain acceptance requirements |
| Older architecture wants a running full stack in foundation | Current first task is audit only; runtime implementation belongs to its later phase |
| Phase 2 describes ALS training, while user's Phase 8 is recommender development | Phase 2 establishes Scala interfaces/build and data outputs; substantive ALS fitting/tuning/evaluation is Phase 8 |
| First-party reviews are needed before Phase 9/10 | Phase 1 imports consented, movie-linked reviews and human annotations through local files; full web collection follows later |
| Streaming needs trained prediction outputs | Phase 2 validates event/replay contracts with isolated labelled test fixtures; actual trained-prediction aggregation is connected in Phase 7 and rehearsed in Phase 12 |

Completing an output dependency later is part of integration, not permission to skip an earlier incomplete phase. Missing data blocks the relevant exit criterion; it does not authorize substituting a fabricated dataset.

Accepted exception: Phase 2 source implementation and available offline checks may proceed using audited MovieLens before the unrelated NLP data criteria close. Full Spark execution still requires the manually prepared toolchain and resource headroom. Phase 1 remains partial. After Phase 2 execution/evidence acceptance, integrate the mandatory multilingual/informal-language extension and annotation addendum before Phase 3. No later phase is automatically complete or authorized to bypass its own data/approval requirements.

## 2. What already exists, and what was inspected

The initial working root held ARCHITECTURE.md, .git and temp/. Git already reported 208 tracked deletions and untracked ARCHITECTURE.md/temp/. No reset, restore, move, staging or commit is part of this audit.

There were 220 project-owned files under temp/ before this audit, plus root ARCHITECTURE.md. The source/artifact view contains 208 files totaling 22,881,957 bytes and 116 unique SHA-256 contents: 92 in the primary temp tree, 88 byte-identical copies in temp/CineScope, and 28 in temp/CineScope_Midsem. Ten ignored editable-install metadata files and two existing SQLite databases account for the other 12 files. Dependency environments and generated caches were inspected separately rather than miscounted as authored source. Copies are preserved.

The review covered Python/Scala/JavaScript source, tests, configurations, scripts, Markdown documentation, notebook code and stored execution metadata, provenance/metric JSON, dataset schemas, and model artifact metadata. Binary presentations, PDF handbook, images and model weights were inventoried/hashed rather than rendered or executed. This is not a claim of visual validation or safe deserialization of joblib weights.

### Existing implementation assessment

| Component and evidence | Sound work to reuse after approval | Gap against the new project |
|---|---|---|
| temp/backend/cinescope/reviews.py:369,480,535 | Negation examples, explicit probabilities, source/evidence handling | Binary classifier is blended with heuristic Mixed/Neutral rules; lexicon fallback; positive-logit index assumes binary labels |
| reviews.py:549,620 | Aspect-conditioned classification concept | Extraction is alias/clause matching; missing aspect model falls back to sentence sentiment; no trained BIO extractor |
| reviews.py:634 | Extractive evidence, duplicate filtering, transparent counts | No calibrated minimum-evidence/shrinkage policy or persisted versioned summary/score snapshots |
| training.py:69, 94 | Separate binary and target-aspect training functions | No final three-class sentiment or span training; missing AMP/accumulation/resume/resource monitoring and mandatory per-model file structure |
| storage.py:19 | Parameterized queries and idempotent request concepts | SQLite reviews/ratings only; no full PostgreSQL schema, migrations, consent, user ownership, pgvector or prediction registry |
| api.py:127,246,290,317,410 | Validation/error handling and review API concepts | /api/docs path; on-read full aggregation; inference before durable persistence; arbitrary user IDs; import creates/seeds DB |
| temp/frontend/service.js:107,148,198 | Original dark film UI, catalogue cards and explicit sample-data notices | Static HTML/JS, shared local identity, automatic heuristic browser fallback; no required Next.js integration |
| temp/scala/src/main/scala/cinescope/ | Six genuine Scala Spark programs, not Python wrappers | Old Scala 2.12.18/Spark 3.5.7; processing responsibilities need clearer separate classes and stronger validation |
| MovieETL.scala:26, 42 | Real DataFrames/joins/Parquet outputs | Arbitrary retention with dropDuplicates(userId, movieId); potentially excessive date partitions |
| ReviewStream.scala:17, 26 | Watermark deduplication and checkpointed file ingestion | Append-only events are not current movie aggregates; missing idempotent DB publication and edit/delete/reanalysis semantics |
| ALSRecommender.scala:22, 41 | Actual MLlib fitting, chronological user splits and factor export | Multiple fitted models retained; selection by RMSE only; limited candidates before seen-item filtering |
| recommender.py; evaluation.py | Sparse content profile, factor fold-in, explicit ranking denominators | Fixed untuned weights; incomplete novelty/diversity evaluation and new-project identity mapping |
| temp/notebooks/01_Data_Engineering_and_EDA.ipynb | Teaching/EDA material | Enabling32M still reaches full pandas ratings read; enforce a hard data-size guard |
| Other notebooks, tests, Midsem work | Useful syllabus material and regression scenarios | Legacy rule-based assertions and old metrics cannot validate new models; reorganize into reproducible per-component experiments |

The existing source package declares2.1.0, but editable-install metadata declares1.0.0. Treat that installation as stale. Do not upgrade or repurpose it without an explicit environment decision.

Current static verification parsed32 unique Python source files and 45 notebook Python cells:77 parse units, zero Python syntax errors. One notebook %run cell was excluded as Jupyter syntax. Nine main notebooks have71 cells/44 code cells with stored execution counts; their old execution records do not establish current results. JavaScript checks were unavailable because Node was not found. Application tests were deliberately not imported because the API has import-time SQLite side effects. Historical reports of 14 passing tests, six compiled Scala programs and saved model metrics were not reproduced.

## 3. Audit conclusions that constrain execution

See ENVIRONMENT_AUDIT.md for measured commands, versions and official compatibility links, and DATASET_AUDIT.md for exact local file/schema/provenance findings.

| Finding | Consequence |
|---|---|
| Core7 240H, 10 cores/16 threads; nominal16 GB RAM; RTX5050, 8151 MiB VRAM, capability 12.0 | Compact fine-tuning remains plausible; success requires measured smoke tests and sequential workloads |
| Available visible RAM was about 1.10 GiB when sampled | Close unneeded workloads and measure again before Spark/training; nominal RAM is not available job memory |
| D: had about 55.83 GiB free, below the stated 100 GB assumption | Do not start full ingestion/model installation without a storage budget or user-approved location decision |
| Python 3.11.9 available; py defaults to3.14.6; legacy project environment uses3.12.10 | Create a distinct explicit3.11 environment; never rely on an unqualified launcher |
| Global3.14 has torch2.14.0+cpu and its import failed | It does not provide validated CUDA training; preserve it rather than repairing shared packages automatically |
| GPU driver is detected; selected3.11 environment lacks PyTorch | Driver success does not establish torch/CUDA operation |
| Spark 4.3 versioned official docs support Java17/21/25, Scala 2.13, Python 3.11+ | The architecture's JDK 21/Scala 2.13/Spark 4.3 combination is supported; port old3.5/2.12 code deliberately |
| Node/npm/SBT/Spark/PostgreSQL/pgvector and several required packages not verified as usable | Install only after approval using the staged plan; absence from PATH is not proof nothing exists anywhere |
| MovieLens 32M arrived during final verification; all four CSV checksums match and full streaming scans confirm 32,000,204 ratings, 2,000,072 tags, 87,585 catalogue movies and 200,948 rating users | Available for later BDA/ALS work after resolving mapping issues; IMDb/TMDB snapshots/human annotations remain absent |
| 3,153 catalogue movies have tags but no ratings; six tags are whitespace-only | Evaluate item cold start explicitly; quarantine blank tags in processed copies while preserving raw files |
| Genuine neutral, aspect-span, theme and reference-summary annotations are absent | Annotation/consent is a critical project dependency, not a UI detail |

During SQLite inspection, read-only connections created WAL/SHM bookkeeping files. The audit detected this, closed connections, verified both original database hashes, and removed only the four newly created sidecars after verifying empty WAL files and exclusive access. Original database files remained unchanged. Future static reads must use immutable mode only for a confirmed inactive snapshot.

## 4. Proposed architecture improvements and approval decisions

No root architectural source was edited. Compatibility-preserving implementation details below still need validation; material product/methodology choices are explicitly proposals.

| ID | Proposal and reason | Impact and decision |
|---|---|---|
| D1 | Define neutral as factual/non-evaluative/balanced according to one adjudicated guideline; annotate mixed polarity separately before mapping to three classes | The architecture groups mixed/unclear/neutral together. Approve a precise label policy before annotation/training; uncertainty must not become a substitute neutral label |
| D2 | Add an aspect-category presence head or separately trained category model for implicit aspects, alongside BIO explicit spans | BIO alone misses "it drags" when pacing is implicit. Start with explicit-span coverage; approve additional trained category support and label cost before claiming complete ABSA |
| D3 | Add explicit theme-targeted sentiment labels/classification or validated evidence-based aspect/theme linking | Whole-review polarity does not establish reception of a theme. Without adequate labels, withhold theme audience sentiment while retaining metadata/theme relevance |
| D4 | Use a durable PostgreSQL job/outbox table and one bounded local inference worker; snapshot analytics outside request handlers | Avoid lost FastAPI background work, stale overwrites and multiple GPU model copies. This adds reliability without requiring Redis/Kafka or a mandatory cloud service |
| D5 | Make minimum evidence an enforced null-score gate before shrinkage; publish effective sample size and uncertainty separately | A population prior is not a new movie's audience evidence. Approve/tune thresholds and prior only after inspecting legitimate linked reviews |
| D6 | Use Spark to train ALS, export validated factors/maps and support explicit app-user fold-in or scheduled refits | Application user IDs are not MovieLens user IDs. Approve the serving method; validate fold-in regularization/weights against the chosen ALS objective and keep cold-start content fallback |
| D7 | Freeze snapshot/version contracts across reviews, predictions, summaries, vector indexes and streaming updates | Deletions/revisions/reprocessing otherwise double-count or leave unsupported summaries. Rebuild affected indexes/snapshots and mark stale results until refreshed |
| D8 | Use compact evidence-grounded hierarchical summarization with a deterministic extractive abstention path | FLAN-T5-small is a candidate, not a proven faithful review summarizer. Evaluate local quality before promotion; a cited extractive result is preferable when generation fails evidence checks |
| D9 | Keep optional speech CPU-first until GPU runtime compatibility is proven | faster-whisper uses CTranslate2 and has its own CUDA/cuDNN requirements; a working PyTorch wheel does not validate it. Text remains available |
| D10 | Separate executable ml/ source from models/ artifacts and keep shared config/schema packages | Satisfy per-model modularity, prevent training imports at runtime, and avoid duplicated preprocessing/metric definitions |
| D11 | Choose native Windows PostgreSQL+pgvector build or another supported local deployment after checking the audited machine | pgvector on Windows may need matching PostgreSQL headers/MSVC tools. Docker/WSL is an alternative proposal, not an authorized mandatory dependency |
| D12 | Resolve storage/resource constraints before full setup | Reclaiming space, moving data/caches to another drive, or using external storage changes the local layout and needs approval. Never delete the existing environments/raw files as automatic cleanup |
| D13 | Correct the architecture's overly broad MovieLens redistribution statement using the supplied release README | This release permits redistribution, including transformations, under the same stated conditions; acknowledgement/no endorsement apply, and commercial use requires permission. Keep datasets out of Git as the user's engineering policy. Do not edit ARCHITECTURE.md without approval |
| D14 | Quarantine/resolve the actual MovieLens external-link conflicts before enforcing canonical-ID uniqueness | Among 87585 links, 124 lack TMDB IDs and 36 distinct TMDB IDs occur twice. Do not invent IDs, arbitrarily discard entries, automatically merge titles or create a multiplying join |
| D15 | Base genre/tag validation on the actual release rather than an incomplete prose enumeration | Raw genres include Children and IMAX; 7,080 records use (no genres listed), and six tags contain only a nonbreaking space. Define separate canonical features and quarantine/exclusion policies without modifying source values |

The requested stack, 14-phase order, locally trained compact NLP models and real Scala processing remain the design. No approval is requested for replacing them with shortcuts.

### Official documentation checked for these decisions

- Spark compatibility: https://spark.apache.org/docs/4.3.0/ — see the environment audit for the exact supported tuple and release evidence.
- Hugging Face token classification: https://huggingface.co/docs/transformers/tasks/token_classification — token/subword label alignment and trained token classification.
- Hugging Face summarization: https://huggingface.co/docs/transformers/tasks/summarization — extractive/abstractive distinction and sequence-to-sequence workflow.
- FLAN-T5-small model card: https://huggingface.co/google/flan-t5-small — Apache2.0 candidate; task performance and factuality still need local evaluation.
- faster-whisper runtime requirements: https://github.com/SYSTRAN/faster-whisper — independently validate speech dependencies.
- TMDB FAQ: https://developer.themoviedb.org/docs/faq — non-commercial API use requires attribution, approved logo and an About/Credits notice. This does not independently grant redistribution rights to all artwork.
- TMDB rate limiting: https://developer.themoviedb.org/docs/rate-limiting — limits can change; honor429 responses and bounded backoff rather than hardcoding an old quota.

External browsing was limited to compatibility, model and TMDB terms documentation. No dataset search or alternative-dataset research was performed. No TMDB API request or metadata download was made.

The local MovieLens release documentation arrived later and was read directly at data/raw/movielens/ml-32m/README.txt. Its terms and CSV measurements are recorded in DATASET_AUDIT.md; no dataset acquisition was performed by the audit. Disk figures in this plan/environment audit are earlier measurement snapshots, not a claim of final free space after the new archive and extracted files arrived.

## 5. Dependency and installation plan — proposed, not executed

Use ENVIRONMENT_AUDIT.md for exact observed versions and unresolved wheel choices. Do not install all optional groups at once. Explain size, disk/RAM effects and selected versions before a large approved installation.

1. Agree on the workspace/storage budget and material decisions. Re-measure free memory. Preserve the legacy environment. Review narrow Git ignore rules before any new environment or data is created.
2. Use the explicit Python 3.11 interpreter to create a new root .venv after approval. Record interpreter path, pip version and platform. Do not change the default Python installation or reuse temp/.venv.
3. Add a constrained base scientific/test group: NumPy, pandas, scikit-learn, pyarrow, PyYAML, pytest, httpx and plotting/JupyterLab tooling as needed. Inspect resolver output and wheel compatibility. Avoid indiscriminate latest-version upgrades.
4. Establish SBT and the Spark toolchain; keep the working JDK 21 but select one consistent JAVA_HOME/PATH. Pin the Scala 2.13 patch and Spark 4.3 patch against the actual Spark distribution/build metadata. Do not mix old PySpark 3.5 with Scala Spark 4.3. Node 24 LTS/npm is selected as a later frontend prerequisite; install it in Phase 10 rather than requiring it to finish data work.
5. Install a stable Windows Python 3.11 PyTorch CUDA wheel whose official matrix and available wheel support Blackwell capability 12.0 and the driver. The inspected selector/release pages are inconsistent; an exact torch/CUDA pin is deliberately pending. The driver-reported CUDA level is not a command to install that exact toolkit. No full CUDA Toolkit is required for ordinary compatible torch wheels.
6. Run torch import/availability/capability checks and tiny FP32/FP16/BF16 tensor tests. Log allocated/reserved/peak memory and synchronize. No model training at this step. Resolve failure before downloading model weights or starting training.
7. Add Transformers/Datasets/Accelerate/tokenizers/safetensors/evaluate/Sentence Transformers and task metrics. seqeval supports BIO spans; summary ROUGE/BERTScore are installed only when evaluation needs them. Reconcile torch/NumPy/Transformers versions and run pip check.
8. Set up local PostgreSQL with the chosen pgvector method. Add FastAPI/Uvicorn/Pydantic2/SQLAlchemy2/psycopg/pgvector/Alembic/settings/auth packages as the Phase 9 implementation needs them. Native programs can be prepared in Phase 0; application migrations remain Phase 9.
9. Add BERTopic/UMAP/HDBSCAN only in Phase 5 after checking Windows wheels, dependencies and memory. These are exploratory, not startup dependencies.
10. Add frontend dependencies in Phase 10 with exact Next/React/TypeScript/Tailwind/charting versions, package-lock and npm ci verification. Do not run scaffolding that overwrites files.
11. Add offline speech packages/model artifacts in Phase 11, separately verifying CPU/CUDA requirements. No browser speech API is promised to work offline.
12. Record a reproducible lock/constraints manifest, Python package metadata, JVM/Spark/Scala/SBT versions, Node lockfile, OS/driver and model revision hashes after the respective groups pass. Keep optional task groups separated when conflicts require it.

Model downloads are distinct from dataset acquisition. They are deferred until an approved model/license/cache budget exists. Dataset fetching remains manual even after ordinary dependency installation approval.

## 6. Shared contracts and proposed repository organization

No source restructuring occurred in the audit. After approval, add new modules deliberately and adapt audited legacy functions without moving/deleting their original copies.

    backend/app/{api, core, database, models, schemas, repositories, services, workers, auth}/
    frontend/{app, components, hooks, lib, public, styles}/
    scala/src/main/scala/com/movieintel/
      {config, ingestion, cleaning, transformations, analytics, recommendation, streaming}/
    ml/{common, sentiment_tfidf, sentiment_transformer, aspect_extraction,
        aspect_sentiment, themes, summarization, review_risk, embeddings}/
    models/{sentiment, aspect_extraction, aspect_sentiment, theme_classifier,
            summarizer, review_risk, embeddings, recommendation}/
    configs/{data, training, serving, scoring, recommendation, streaming}/
    schemas/{datasets, events, predictions, analytics}/
    notebooks/
    scripts/
    tests/{unit, data_quality, integration, end_to_end, fixtures}/
    documentation/{architecture, dataset, model_cards, evaluation, api, screenshots}/

Each ml component gets train.py, evaluate.py, predict.py, config.yaml and README/model_card.md. For pretrained-only components, train.py documents/validates an optional training path and fails clearly when labelled inputs are absent. It never pretends that downloaded weights were locally trained. Test fixtures are isolated and explicitly synthetic.

### Contracts to freeze before dependent work

| Contract | Required content |
|---|---|
| Source manifest | Source/version, local relative path, bytes/checksum, license/consent evidence, observed schema, audit scope and validation status |
| Canonical movie/external IDs | Stable internal key, source namespace/external string ID, mapping status, source hash and conflict quarantine; reversible Spark int32 map |
| User identity | Authenticated application user and source-qualified MovieLens research user are separate namespaces |
| Review revision | review_id, movie_id, user/consent provenance, raw-text hash, language, created/updated UTC, revision/deletion/moderation state |
| Prediction | Review revision, schema/model/tokenizer/label-map versions, three probabilities, uncertainty, time, status and original-text span offsets |
| Review event | Stable event ID, review/revision ID, operation, event time, model/version metadata and payload/source hash; no raw secrets |
| Score snapshot | Movie/evidence snapshot, valid/distinct/effective counts, nullable score, status, method/prior/threshold/model versions, timestamp, uncertainty |
| Summary | Evidence review/span references, review snapshot/count/date range, language, model/generation/method version, factuality status and stale flag |
| Vector index | Entity ID/revision, embedding model/revision, dimension, normalization/content hash, index version; no mixed embedding spaces |
| Recommendation | User/snapshot, eligible candidate IDs, component scores/final rank, actual reasons, model/feature versions and generated timestamp |

Schema migrations must add actual foreign keys/unique/check constraints to the architecture's illustrative SQL, immutable prediction provenance and snapshot evidence relations. Define rating/source uniqueness, watchlist and conversation/session storage, deletion propagation and model registry records before backend implementation. Probabilities must be finite, in[0, 1], sum to1 within tolerance; weights nonnegative with a defined zero-weight policy.

## 7. Actual execution order and phase gates

Run Phase 0 completion first, then phases1→2→3→4→5→6→7→8→9→10→11→12→13. Each phase has objectives, files, dependencies, implementation order, tests, metrics, expected outputs and a completion checklist below. A checkbox records evidence, not confidence or elapsed effort. No model performance target is fabricated before baselines exist.

Current delivery order: preserve foundation/data validation and Phase 2 evidence; generate Phase 3 and language-extension files under the user's source-only instruction; statically validate and hand off. Later execution order: recheck the manually installed tools; recompile final Scala sources and run the Phase 2 unit/Parquet/batch/streaming/UI checks; accept the Phase 2 gate; close the relevant source/label/mapping/model requirements; then follow the Phase 3 runbook. Independent source work does not substitute for any unexecuted check.

### Phase 0 — workspace, hardware and environment audit/foundation

Objective: establish the actual machine, preserve existing work, reconcile specifications and prepare a compatible isolated development environment only after approval.

Dependencies: root architecture; user scope; read access to existing files/software/hardware and official compatibility docs. No datasets are required for the audit.

Files: the four root audit/instruction documents created now. Proposed next files: README.md, .gitignore, .env.example, LICENSES_AND_ATTRIBUTION.md, pyproject.toml/constraints, configs/environment.yaml and scripts/{audit_environment, setup_environment, check_gpu, check_health}.ps1. Inspect any existing target before adding/editing; do not restore deleted tracked files automatically.

Implementation order:

1. Read the architecture; inventory all authored files, data/artifacts, installed runtimes and Git status.
2. Record hardware/driver/storage/RAM, interpreter differences and failed/unperformed checks; compare official compatibility.
3. Present audit, decisions and exact next step; stop. This is the current hand-off.
4. After approval, implement only the foundation files and bounded diagnostic scripts; address storage/RAM blockers through an approved choice.
5. Prepare the isolated3.11 environment and approved prerequisite groups, version locks and safe Git ignore/checkpoint strategy.
6. Run real tiny CUDA/JVM/Node checks after prerequisites are installed; do not convert smoke checks into model training.

Tests/metrics: file preservation hashes; interpreter path; dependency resolution/pip check; CUDA tensor and AMP support; tiny JVM/Scala/Spark job; Node version; free disk/RAM and peak diagnostic memory. No accuracy metrics apply.

Expected outputs: approved tool tuple, reproducible setup commands, resource baseline, explicit pass/fail/deferred list and empty immutable raw-data locations.

Completion checklist:

- [x] Read architecture and existing files; record source and dataset limitations.
- [x] Gather environment/hardware evidence and create requested dataset directories.
- [x] Create the four requested audit documents without changing original project files.
- [ ] User approves the proposed next work and material decisions.
- [ ] Resolve storage/headroom and complete selected toolchain/CUDA smoke checks.

### Phase 1 — manually supplied data, validation and movie ID mapping

Objective: establish permitted, schema-checked, leakage-aware inputs and reliable identities before models/processes use them.

Dependencies: approved foundation; user-provided files under data/raw; consent/license information. Missing sources are reported, not downloaded.

Files: scripts/{validate_datasets, audit_movielens, audit_imdb, prepare_imdb, prepare_annotations, validate_movie_ids, build_movie_id_map, prepare_tmdb_snapshots, preprocess_reviews}.py; configs/data/*.yaml; schemas/datasets/*; data/dataset_cards/*; documentation/dataset/{ANNOTATION_GUIDELINES, ID_MAPPING, DATA_DICTIONARY}.md; notebooks/01_dataset_audit.ipynb; tests/data_quality/*. Split preparation belongs to prepare_annotations and prepare_imdb; shared functions avoid redundant implementations.

Implementation order:

1. Implement streaming/bounded local inventory and validator commands with explicit input/output paths and size guards; absent input exits clearly. Unit tests use isolated tiny synthetic fixtures.
2. Validate MovieLens CSV headers/types/ranges and source documentation; exact row/null/duplicate/reference checks use streaming or later Spark passes, never a full pandas read.
3. Audit aclImdb directories, labels, train/test IDs, encodings/text lengths and duplicate/near-duplicate overlap. Preserve the original split. Version any evaluation exclusions separately.
4. Inspect user-supplied TMDB snapshots without API fetching; validate external IDs/fields/license records and metadata coverage.
5. Create canonical movie/external-source mapping with uniqueness/coverage/conflict reports. Preserve IMDb IDs as strings. Quarantine unresolved IDs; do not guess from title matches.
6. Import consented first-party reviews by local CSV/JSONL with validated internal IDs; create human annotation guidelines for three-class sentiment, aspect spans/sentiment, themes and target-specific reception.
7. Annotate/adjudicate an overlapping subset with two annotators and measure agreement. Version labelled files separately from raw text. A 1,000–3,000-example target is a planning starting point, not a quality guarantee.
8. Freeze train/validation/test manifests using duplicate clusters and appropriate movie/reviewer groups. Keep the official IMDb test isolated. Record retrospective vs future-time evaluation semantics.
9. Save EDA, leakage reports, dataset cards and processed copies; no raw file mutation.

Tests: malformed CSV/JSON, missing columns, null/overflow IDs, invalid ratings/timestamps, unsafe output paths, missing consent, UTF-8/leading-zero IDs, conflicts, orphans, duplicate leakage, reproducible splits and raw hash preservation.

Metrics: observed row/file/byte counts; null/type/range failures; duplicate rates; mapping coverage/conflicts; class/aspect/theme distributions; annotation agreement; train/test overlap and rejection counts. Report sampled checks as sampled.

Expected outputs: versioned manifests and clean copied inputs; accepted/quarantine mapping tables; genuine labelled data and locked splits. No audience statistics are produced from synthetic samples.

Completion checklist:

- [ ] User supplies required raw sources and terms/consent provenance.
- [ ] Validators, preprocessing scripts and meaningful tests pass.
- [ ] Movie mappings and review linkage are validated.
- [ ] Labels, agreement, leakage and split manifests are reviewed.
- [ ] Missing datasets/labels remain explicit blockers; no fabricated completion.

### Phase 2 — independent Scala/Spark BDA pipeline

Objective: produce real, reproducible Parquet data engineering and demonstrable BDA syllabus evidence.

Dependencies: compatible JDK 21/Scala 2.13/SBT/Spark build; validated MovieLens inputs/manifests; review event schemas. Full ALS experimentation waits for Phase 8.

Files: scala/build.sbt, project/build.properties; separate config/ingestion/{MovieLensIngestion, ReviewIngestion}.scala; cleaning/DataCleaning.scala; transformations/{RddExamples, DataFrameTransformations}.scala; analytics/{MovieAnalytics, UserAnalytics}.scala; recommendation/AlsTraining.scala; streaming/ReviewStreamJob.scala; Main.scala; Scala tests; scripts/run_spark_jobs.ps1; notebooks/02_movielens_eda.ipynb.

Implementation order:

1. Pin one Spark/Scala/JDK tuple. Source work and cached-compiler config/syntax checks may proceed under the approved exception. After manual toolchain preparation, compile a tiny local application and verify real filesystem/Parquet operation on Windows before the full run.
2. Read source CSV using explicit schemas, capture malformed rows and ingestion provenance; keep raw files untouched.
3. Produce Bronze/Silver Parquet with source timestamps, normalized IDs/genres, UTC conversions and documented duplicate-event policy.
4. Join ratings, movies, tags, links and approved metadata; track row counts/orphans before and after joins.
5. Produce rating distributions, raters, genre/time aggregates and user genre/tag profiles with explicit source semantics.
6. Demonstrate RDD map/flatMap/filter/reduceByKey vs small groupByKey, immutable Scala functions, Option/Either/case classes, DataFrames/Datasets, joins and aggregation.
7. Demonstrate partitioning, lazy evaluation, explain plans, DAG, shuffle, cache/unpersist and Spark UI with measured input/output/time/memory. Avoid full collect/toPandas and excessive date partitions.
8. Define ALS input/export interfaces and compile the class; reserve substantive fitting for Phase 8.
9. Implement file-stream validation, stable IDs, watermark/late-event policy, checkpoints and an idempotent demonstrable sink; use explicitly synthetic test events only until real review predictions exist.

Tests: Scala compile/unit tests; known fixture transformations/row conservation; invalid/orphan quarantine; UTC and duplicate policy; Parquet round-trip; restart/replay/duplicate/late-event scenarios and immutable raw files.

Metrics: rows/bytes/time/throughput; partitions/tasks/shuffle/cache effects; peak process/RAM usage; input/output/rejection counts; streaming batch lag/checkpoint restart. Local mode is not evidence of multi-machine speedup.

Expected outputs: independently executed Scala jobs, documented Bronze/Silver/Gold schemas, movie/user analytics, BDA screenshots and streaming contract.

Completion checklist:

- [ ] All separate Scala components compile and execute actual processing.
- [ ] MovieLens outputs reconcile with validation counts.
- [ ] RDD/DataFrame/DAG/cache/Spark UI evidence is saved.
- [ ] Checkpoint/replay behaviour is tested and accurately described.
- [ ] No pandas32M/full-driver collection or Python wrapper substitute.

### Phase 3 — TF-IDF and Transformer sentiment

Objective: compare defensible binary benchmarks and train the genuine final three-class movie-domain classifier.

Source status: modular classical, English Transformer, multilingual and independent sarcasm implementations are generated; no Phase 3 model has been trained/evaluated. Original-text alignment utilities and optional adapter contracts do not establish Hindi/Hinglish capability. See documentation/phase3/GENERATED_FILES.md and RUNBOOK.md. Learned sarcasm/sentiment fusion, a trained language detector and a transliterator are not supplied or claimed; independently trained diagnostics must not reverse sentiment.

Dependencies: approved source licenses/model checkpoint, valid neutral labels, frozen splits and functioning GPU environment. No approved data means no training.

Files: ml/sentiment_tfidf, ml/sentiment_transformer, ml/multilingual_sentiment and ml/sarcasm component bundles; ml/informal_language; shared ml/common utilities; configs/training/*; scripts/prepare_sentiment_splits.py and train_models.ps1; schemas/datasets/phase3_review_manifest.schema.json; tests/ml; notebooks03-06 and five language/ablation notebooks; model cards and the language annotation addendum. Each trainable component has train.py,evaluate.py,predict.py,config.yaml,README.md,model_card.md.

Implementation order:

1. Reconfirm labels/distributions/duplicate clusters and EDA; define negative 0, neutral 1, positive 2 in the artifact, not implicit logit indices.
2. Fit train-only BoW/TF-IDF unigrams/bigrams and Logistic Regression/Linear SVM. Keep IMDb binary results separate from three-class domain results; preserve comparable task splits.
3. Review compact DistilBERT model license/revision and authorize any weight download/cache use.
4. Run an approved tiny forward/backward/checkpoint smoke only after data/GPU checks; then approve the bounded training configuration.
5. Fine-tune one model using sequence 128, micro-batch 4 initially, dynamic padding, gradient accumulation, validated mixed precision and low worker counts. Checkpoint supported models when needed.
6. Save/reload/resume optimizer, scheduler, scaler and RNG state; early-stop using validation metrics. Use fixed seeds while documenting GPU nondeterminism.
7. Select truncation/representation/hyperparameters on tuning data, then fit temperature on a separate calibration subset of the original validation partition. Keep train,tuning,calibration,test groups disjoint. The generated model uses documented truncation; chunk aggregation remains a later controlled experiment. Freeze tokenizer, slang/emoji views and model-source hashes for checkpoint resume and inference.
8. Freeze the selected model, evaluate held-out data once, save metrics/error examples/model card and register approved artifacts.

Tests: raw-text preservation, train-only vocabulary, split isolation, label mapping, probability normalization, empty/long/negated/mixed/language cases, train-serving tokenization parity, CPU fallback, CUDA memory and resume/reload equivalence.

Metrics: accuracy, per-class precision/recall/F1, macro/weighted-F1, confusion matrix; calibration NLL/Brier/ECE with binning protocol; latency/VRAM/throughput. No inferred neutral benchmark from IMDb.

Expected outputs: baseline artifacts plus evaluated binary/three-class checkpoints with separate model cards and reproducible prediction contract.

Completion checklist:

- [ ] Actual neutral-labelled data and calibration splits exist.
- [ ] Comparable baselines and trained Transformer are evaluated honestly.
- [ ] GPU/AMP/checkpoint/resume and CPU inference pass.
- [ ] No heuristic production neutral/mixed overlay or hardcoded predictions.

### Phase 4 — trained aspect extraction and aspect sentiment

Source status: generated,not trained/accepted. Shared local supervised engine,
complete-annotation loader,original-offset BIO/window adapter,target-context
classifier and sequential full pipeline are present. Read documentation/phase4
and documentation/phases4-8 before execution. Implicit/mixed/overlapping target
schemes remain unsupported until separately reviewed; no source capability claim.

Objective: identify movie aspects/evidence and classify target-specific sentiment, including mixed sentences.

Dependencies: Phase 3 shared utilities; adjudicated aspect spans/categories/sentiments and label policy. The architecture's16-aspect taxonomy is the starting point; support per aspect depends on observed annotation counts.

Files: ml/aspect_extraction and ml/aspect_sentiment component bundles; schemas/predictions/aspects*; annotation validators; notebooks/07_aspect_extraction, 08_aspect_sentiment.ipynb; per-component tests/cards.

Implementation order:

1. Freeze taxonomy/BIO conventions, original-text offsets, annotation rules and split groups; audit rare classes and agreement.
2. Train a compact BIO extractor with correct subword alignment and padding masks. Record unsupported/implicit-aspect coverage.
3. Train the target/span-conditioned sentiment classifier using review+aspect context, not review-wide labels copied to aspects.
4. Handle positive/negative/neutral and separately annotated mixed aspect opinions according to approved policy; do not silently collapse incompatible labels.
5. Evaluate extraction and sentiment separately and end-to-end using predicted spans. For long text, merge overlapping-window spans deterministically and deduplicate evidence.
6. Calibrate/tune thresholds on validation data, inspect errors, register artifacts and expose a common predict contract.

Tests: multiword spans, subword alignment, negation, contrasting aspects, overlap/window boundaries, Unicode offsets, missing aspect, evidence substrings, CPU/GPU parity and absent checkpoint states.

Metrics: exact span precision/recall/F1; token/per-aspect F1 as secondary; gold-aspect sentiment macro-F1; full-pipeline target+polarity F1; class support, latency/VRAM.

Expected outputs: actual trained extraction and aspect-sentiment checkpoints with evidence spans; insufficiently supported aspects explicitly limited.

Completion checklist:

- [ ] Human aspect annotation and trained BIO extraction validated.
- [ ] Target-conditioned sentiments differ correctly when evidence differs.
- [ ] Full-pipeline held-out evaluation and model cards saved.
- [ ] No keyword-only extraction claimed as a trained final model.

### Phase 5 — themes, topics, embeddings and grounded summaries

Source status: generated,not evaluated. Multi-label Transformer relevance,
train-only LDA and numeric inference,reviewed local Sentence Transformer inference,
movie-isolated evidence snapshots and hierarchical summary candidates are present.
Pretrained embedding/summary operation is explicitly distinct from local fitting.
BERTopic,reference overlap metrics and curated cluster mapping are unclaimed
until their actual inputs/experiments exist. Generation needs factuality approval
before publication; default evidence extraction uses actual source quotes.

Objective: derive separately documented themes and audience reception, build reusable semantic representations, and summarize actual linked reviews faithfully.

Dependencies: permitted metadata/review snapshots; trained sentiment/aspects; theme labels; local embedding/summarization checkpoints and evaluation references/annotation rubric.

Files: ml/{themes, embeddings, summarization} bundles; topic modelling module/config; ml/common/evidence.py; summary/vector schemas; notebooks/09_theme_extraction, 10_review_summarization, 12_embeddings_semantic_search.ipynb; evaluation/cards/tests.

Implementation order:

1. Freeze theme taxonomy and distinguish synopsis relevance, tags, review mentions and theme-targeted reception.
2. Train a compact multi-label classifier on actual human labels; tune per-theme thresholds on validation data and evaluate rare themes.
3. Run bounded LDA/BERTopic explorations separately; record seeds, versions, sample scope and curator mappings. Topics are not automatically stable movie facts.
4. Generate compact sentence embeddings in batches from licensed metadata/review snippets. Save content hashes, dimensions and model revision; evaluate retrieval before indexing in Phase 9.
5. Implement representative review retrieval per movie with deduplication, sentiment/aspect balance and evidence IDs. No use of IMDb reviews without validated movie linkage.
6. Build hierarchical chunk→group→movie summarization with compact pretrained candidate weights. Fine-tuning is optional only with permitted targets and separate approval.
7. Calculate all counts/ratios outside generation; verify sentence evidence, contrast/negation and scope qualifiers. Abstain or return cited extractive output on unsupported generation.
8. Persist summary/evidence snapshot contracts, refresh/stale/deletion behaviour and evaluation references. Keep summaries above individual reviews in the later page contract.

Tests: no reviews, single/insufficient reviews, contradictory sentiment, duplicate-heavy inputs, token limits, movie isolation, evidence citations, wrong IDs, deletion/revision invalidation and vector-version mismatch.

Metrics: theme micro/macro/per-theme F1 and PR-AUC where appropriate; topic coherence/stability plus human relevance; retrieval Recall/MRR/NDCG on annotated queries; ROUGE/BERTScore only with legitimate references, plus factuality/aspect coverage/unsupported-claim rate and latency/memory.

Expected outputs: trained theme model, curated exploratory topics, batch semantic embeddings and grounded summary artifacts with factuality evidence. Missing theme-reception labels or summary references are reported rather than simulated.

Completion checklist:

- [ ] Theme relevance and audience sentiment remain separate.
- [ ] Embeddings/model revisions and retrieval evaluation are saved.
- [ ] Hierarchical summary evidence and unsupported-claim checks pass.
- [ ] Human review supplements overlap metrics; no invented consensus.

### Phase 6 — suspicious-review risk analysis

Source status: generated,not validated. Exact/TF-IDF similarity,legitimate
behaviour vectors,actual Isolation Forest fitting and numeric-tree inference
are separate. Sentiment is excluded; no fake verdict or calibrated fraud
probability is returned. Missing history/labels remain missing evidence.

Objective: provide transparent moderation support from legitimate text/behaviour signals.

Dependencies: real permitted review records; stable account/event provenance where available; human label definitions for any supervised claims.

Files: ml/review_risk/{train, evaluate, predict}.py, config.yaml, model_card.md; duplicate/similarity/behaviour feature modules; notebooks/11_fake_review_detection.ipynb; tests and moderation policy documentation.

Implementation order:

1. Audit which signals exist and consent permits; do not invent account age, helpfulness, network links or coordinated groups.
2. Establish exact/near-duplicate, template and burst-frequency analytical features; keep counts/source windows explainable.
3. Train supervised/Isolation Forest components only if appropriate labels/features/sample support exist. Describe unlabeled anomaly outputs as relative risk rather than proof or calibrated fraud probability.
4. Define moderation thresholds through validation/human review, store signals/method version and allow correction/appeal.
5. Test false positives on legitimate repetitive or passionate opinions; preserve strong positive/negative reviews as valid unless independent evidence indicates risk.

Tests: empty history, duplicate paraphrases, legitimate short/negative reviews, missing signals, rate bursts and source/domain shift. Synthetic abuse fixtures test mechanics only.

Metrics: precision/recall/F1, PR-AUC, false-positive rate and source breakdown only with ground truth; otherwise duplicate retrieval validation, human audits and analytical coverage. Record unavailable metrics as unavailable.

Expected outputs: versioned risk signals and justified moderation bands; no claim of a proven fake-review detector.

Completion checklist:

- [ ] Signal provenance/availability documented.
- [ ] Risk does not depend on sentiment extremity.
- [ ] False positives/human moderation and metric limitations documented.
- [ ] No synthetic fixture result presented as real detection performance.

### Phase 7 — movie scoring and audience intelligence

Source status: generated,not accepted. Python latest-revision/eligibility and
reviewer/text deduplication,reviewed evidence gates,weighted/shrunk index,
bootstrap sensitivity,target-only records and Scala aggregate source are present.
Thresholds/prior remain null until reviewed. Actual Python/Scala parity,
transactional publishing and streaming/event integration remain open.

Objective: turn trained eligible review predictions into transparent evidence-qualified snapshots.

Dependencies: calibrated sentiment, aspects, theme-targeted evidence and moderation policy; valid linked review revisions; approved minimum-evidence/shrinkage methodology.

Files: scoring common module/config/methodology; separate Scala ReviewAnalytics.scala; aggregate/score schemas; unit/data-quality tests; score evaluation notebook/documentation.

Implementation order:

1. Define eligible review revisions and duplicate/moderation/deletion handling. Keep per-movie and per-aspect/theme evidence counts separate.
2. Compute individual index 100*(p_positive+0.5*p_neutral), then nonnegative documented weighting. Omit unavailable helpfulness signals; model confidence is not a quality weight.
3. Compute weighted mean and effective sample size (sum w)^2/sum(w^2); handle zero weights and duplicate reviewer dependence.
4. Enforce minimum distinct/effective evidence before display. Tune prior/shrinkage strength on appropriate held-out historical data; do not publish a prior as evidence or invent thresholds as established science.
5. Estimate uncertainty using a documented interval/bootstrap sensitivity procedure appropriate to weighted data and correlated reviews; separate model uncertainty from sampling uncertainty.
6. Calculate aspect scores only from aspect-specific evidence; theme/genre reception only from target-relevant review evidence. Missing labels/evidence yields null.
7. Implement both local analytical service and Scala aggregate processing against the same fixtures/contracts; reconcile numeric outputs.
8. Publish versioned immutable score/summary snapshots with timestamps, model/method/evidence versions and stale states. Connect actual prediction events to the earlier streaming pipeline.

Tests: zero/one/few reviews, all classes, mixed aspects, zero/invalid weights, invalid probabilities, duplicates, outlier weights, deletion/reanalysis, stale model results, idempotent replay and Python/Scala agreement.

Metrics: eligible/distinct/effective counts; stability/sensitivity to new evidence; interval coverage when estimable; calibration and score parity; snapshot refresh lag. No objective artistic-quality metric.

Expected outputs: real nullable audience/aspect/theme/genre reception snapshots and a public methodology ready for APIs/UI.

Completion checklist:

- [ ] Minimum-evidence gate and exact empty message enforced.
- [ ] Weighting, shrinkage, confidence and provenance reviewed.
- [ ] Scala/service calculations agree and replay does not double-count.
- [ ] Ratings, personalization and metadata are never substituted for sentiment.

### Phase 8 — Spark ALS and personalized hybrid recommendations

Source status: generated,not trained. Real Scala global-time split/MLlib ALS,
sampled ranking/factor export,Python verified factor import/content profile,
channel normalization/diversity reranking and ranking metrics are present.
Validation selection functions use actual reports. App identities never borrow
MovieLens factors; optional fold-in remains disabled without method approval.
The sampled Scala protocol and cold fallback need measured validation and are
not full-catalogue performance claims. Actual genre diversity needs catalogue
metadata and Python evaluation. No automatic large ALS run is authorized.

Objective: fit/evaluate real collaborative filtering and combine it with content/preferences under one honest ranking contract.

Dependencies: validated MovieLens interactions/maps; content embeddings/features; Phase 2 Scala pipeline; profile consent and temporal split design. Large fitting/tuning needs explicit run-size approval.

Files: scala recommendation/{AlsTraining, RankingEvaluation}.scala; recommender training/evaluation/prediction modules; factor export/import validators; configs/recommendation/*; notebooks/13_hybrid_recommender, 14_recommendation_evaluation.ipynb; model card/tests.

Implementation order:

1. Freeze relevance threshold, K values, user/item eligibility, chronological cutoffs, candidate universe and unseen-item exclusions. Distinguish per-user chronology from stricter global-time holdout.
2. Establish popularity/content baselines; compute popularity and novelty only from training-period data. Prevent future metadata/features from leaking into claims of deployment-time evaluation.
3. Train explicit-feedback Scala Spark MLlib ALS with reversible int32 IDs; tune rank/regParam/maxIter on validation data. Implicit feedback is a separately justified experiment, not an arbitrary switch on star ratings.
4. Fit one bounded trial at a time, release unneeded factors/caches and retain selected artifacts/metrics rather than all models in memory.
5. Export versioned factors, predictions, candidate sets and maps. Validate factor dimensions, ID namespace and selected Spark prediction parity.
6. Implement approved app-user fold-in or refit strategy without conflating users. Until enough valid ratings exist, use genre/theme/content preferences and disclose cold start.
7. Build semantic/content/genre/theme/profile channels, normalize component scores, tune hybrid weights and apply eligibility/seen filters before choosing final topK. Avoid a small candidate cap that starves results after filtering.
8. Add calibrated diversity/novelty controls and reasons traceable to actual input history/features/contributing channels.
9. Lock the ranking configuration and evaluate held-out warm-user, new-user, new-item cohorts with denominators, exclusions, confidence intervals and ablations.

Tests: ALS map round-trip, int32 bounds, factor parity, user namespace isolation, coldStartStrategy NaN accounting, all-seen/no-history/incomplete channels, genre AND/theme/runtime filters, deterministic ties, seen exclusion, actual explanation evidence and K denominators.

Metrics: Precision@K, Recall@K, NDCG@K, coverage, intra-list diversity, novelty, popularity bias and cold-start performance; optional MAP@K; RMSE/MAE secondary. State sampled vs full-catalogue ranking and dropped cold rows, not just successful ALS predictions.

Expected outputs: real Spark-trained factors, validated local serving, hybrid ranker with tuned configuration, explanations and reproducible model/evaluation cards.

Completion checklist:

- [ ] Spark ALS training/tuning and factor mappings validated.
- [ ] Genuine app-user personalization and cold-start paths work.
- [ ] Required ranking metrics, diversity/novelty and ablations recorded.
- [ ] Explanations use actual features and metrics exclude no cohorts silently.

### Phase 9 — FastAPI, PostgreSQL and pgvector integration

Objective: expose actual versioned catalogue/review/model/recommendation services with secure persistence.

Dependencies: preceding validated modules/artifacts/contracts; chosen PostgreSQL+pgvector deployment and auth policy; no fabricated seed evidence.

Files: backend/app with separate routes/services/schemas/ORM/repositories/core/auth/workers; Alembic migrations; backend tests; API documentation; scripts/{setup_database, start_backend, check_health}.ps1.

Implementation order:

1. Create schema migrations for architecture entities plus constraints, review revisions, consent, snapshots/evidence, watchlists, job/outbox and sessions. Verify pgvector extension and embedding dimension/model compatibility.
2. Implement authenticated users/ownership/password hashing or approved local auth, admin protection, bounded inputs, CORS/rate limits and secret-safe structured logs.
3. Implement catalogue/search/details/metadata, ratings/watchlists/preferences/history and pagination using actual imported data.
4. Persist review as pending with idempotent request key, then run bounded analysis/store versioned predictions/enqueue snapshot refresh. Preserve retry/error states when models are unavailable.
5. Implement lazy model registry/loading with one bounded GPU worker, CPU fallback and no heuristic substitute; offline artifact paths and health/readiness differ.
6. Implement score/summary/similarity/recommendation endpoints from published snapshots and actual engine components.
7. Implement pgvector retrieval and source/version filters; use exact search initially if catalogue size permits, benchmark before an approximate index.
8. Add transaction/outbox retries and idempotent publication; handle review edits/deletion, summary/vector invalidation and auth ownership.
9. Expose /docs and stable /api/v1 routes; implement health/model/pipeline endpoints with appropriate authorization.

Tests: migrations on clean/disposable DB, FK/unique/check constraints, transactions, owner/admin access, API validation, idempotency, model absent/DB down states, pending/retry handling, vector dimensions, review→prediction→snapshot flow and deletion.

Metrics: API/query/model load latency, p50/p95/error rates, worker queue depth, resource use and stale-snapshot lag under a bounded local load.

Expected outputs: working backend localhost:8000/docs and real PostgreSQL/pgvector persistence; no startup training or network downloads.

Completion checklist:

- [ ] API/DB/model integration and ownership tests pass.
- [ ] Actual predictions and evidence snapshots persist correctly.
- [ ] Failure/retry/deletion scenarios remain truthful and durable.
- [ ] Offline local serving works with approved artifacts.

### Phase 10 — Next.js/React product frontend

Objective: deliver a genuine original film discovery/review product on localhost3000.

Dependencies: stable backend/auth contracts and permitted local metadata/artwork; Node/npm lockfile; API integration tests.

Files: Next app pages for home/discover/search/movies/[movieId]/reviews/profile/recommendations/assistant/about; components/{movie, review, score, recommendation, chat, charts, shared}; lib/api/types/auth; styles/hooks; UI tests; scripts/start_frontend.ps1.

Implementation order:

1. Build original dark visual language, typography, navigation, poster cards and responsive shared components. Reuse audited design ideas without copying protected branding or calling a mock working AI.
2. Add typed API/auth/error handling and loading/empty/error/mobile patterns shared by every page.
3. Implement search/filters/detail metadata and clearly separated audience-rating/sentiment/match displays.
4. Place grounded review summary above individual reviews; show counts, timestamps, methodology, evidence and absent/processing/model-unavailable states.
5. Implement authenticated review composer and persisted sentiment/aspect results; ratings/watchlists/user taste profile.
6. Add real recommendation shelves and explanations; label cold starts and missing model channels honestly.
7. Implement About/methodology/privacy/attribution pages, cache-approved artwork fallbacks and accessibility.
8. Reserve assistant page for Phase 11 integration; do not implement disconnected hardcoded catalogue/chat responses.

Tests: component/API contract tests, auth/pagination/form validation, keyboard/focus/contrast, image fallback, responsive viewports and loading/empty/error/insufficient-evidence states for every page.

Metrics: measured local page/interaction latency, accessibility issues, bundle/image sizes and successful real API journeys.

Expected outputs: professional connected website localhost3000 with real movie details/reviews/profiles/recommendations.

Completion checklist:

- [ ] All pages integrate actual APIs and have required states.
- [ ] Summary appears above individual reviews.
- [ ] Score distinctions, confidence and null evidence are clear.
- [ ] Responsive/accessibility and auth journeys pass.

### Phase 11 — conversational discovery and offline voice

Objective: answer required discovery/comparison/aspect queries through the same catalogue/review/recommendation services.

Dependencies: backend retrieval, semantic vectors, entity catalogue, ranking and frontend; approved local speech artifacts for voice.

Files: backend conversational modules for intent/entity/parser/context/retrieval/grounding/response/STT; schemas/chat*; assistant/chat components; speech/query evaluation scripts/tests; model/inference documentation.

Implementation order:

1. Define validated intent/entities/constraints schema and supported phrase semantics, including genre AND, negation, max runtime, similarity and comparison.
2. Resolve catalogue titles/aliases/year with ambiguity clarification; no invented movie entity. Parse themes/moods with documented rules and/or validated model inputs.
3. Route exact filters to SQL, semantic requests to embeddings, opinion/aspect questions to review snapshots and personal queries to the actual hybrid recommender.
4. Preserve bounded context and explicit filters across follow-ups; enforce user/session ownership and context expiry.
5. Compose cited/template-grounded answers and movie cards. An optional local language model may rephrase evidence after factual checks, never manufacture counts/details.
6. Evaluate the six required query examples plus ambiguous titles, no evidence, negation, unknown movie, comparison and follow-up requests against human-labelled expectations.
7. Add user-initiated microphone recording, format/duration limits and cached offline STT using CPU initially; test local-only operation. Text input remains the permanent fallback.

Tests: entity ambiguity, genre intersection, mood/runtime tradeoffs, personalization, aspect evidence isolation, no-data abstention, comparison/context reset, malicious retrieved text, prompt injection, microphone denied and STT failure.

Metrics: intent/entity/constraint accuracy; retrieval Recall/MRR/NDCG; grounded-answer/evidence correctness; unsupported-claim rate; latency; voice WER on permitted recordings plus practical transcription success.

Expected outputs: grounded text/voice movie discovery that uses actual catalogue/model evidence and remembers context.

Completion checklist:

- [ ] Required example queries and follow-up contexts pass.
- [ ] No invented movie facts/audience statistics.
- [ ] Offline STT works with cached weights or explicitly reports unavailability.
- [ ] Text fallback, privacy and microphone control work.

### Phase 12 — integration, correctness and optimization

Objective: prove the complete system works within laptop limits, including offline and failure paths.

Dependencies: all preceding exit criteria; approved artifacts/data; isolated test DB; repeatable launch commands.

Files: tests/integration and end_to_end; scripts/{start_all, stop_services, check_health, evaluate_all}.ps1; resource/load benchmarks; notebooks/15_final_model_comparison.ipynb; documented runbook.

Implementation order:

1. Implement launchers with explicit ports, consistent environment, hidden background helpers where appropriate, health polling, log paths and safe shutdown of only project-owned processes.
2. Run full user journey:search→movie→summary→submit review→persist model outputs→refresh scores→recommend→chat follow-up→voice.
3. Verify import/restart/stream replay, deletion/reanalysis, duplicate requests and concurrent updates do not corrupt current snapshots.
4. Reconcile batch vs streaming and Python vs Scala scores on the same real prediction snapshot.
5. Test DB/model/provider/worker failure and stale snapshot recovery without invented outputs.
6. Rehearse offline with cached catalogue/artwork/model/tokenizer/STT files; disable accidental network loading.
7. Measure memory/VRAM/latency and tune lazy loading, batches, thread limits, SQL indexes and vector search using evidence. Stop training during the full demo.
8. Repeat only tests justified by changed code/failures; freeze versions/artifacts and record genuine final metrics.

Tests: end-to-end browser/API/DB; localhost health; schema migrations; cold users/movies; no evidence; auth; failed model; streaming restart; concurrency/idempotence; offline rehearsal.

Metrics: complete journey pass rate, p50/p95 latency, error/timeout rate, peak RAM/VRAM, model load time, snapshot lag, throughput under a small bounded load and resource headroom.

Expected outputs: tested integrated localhost system, reproducible launch/health scripts and measured optimization report.

Completion checklist:

- [ ] Core journeys and failure/offline cases pass.
- [ ] No mock predictions or synthetic reviews contaminate final evidence.
- [ ] Laptop resource budget and reproducible startup validated.
- [ ] Final model/data/code/lock versions frozen.

### Phase 13 — academic evaluation and demonstration preparation

Objective: deliver a defensible report, repeatable demonstration and honest limitations.

Dependencies: frozen tested system and real saved results; reviewed licenses/consent.

Files: final README, LICENSES_AND_ATTRIBUTION, academic report/slides, architecture/ER diagrams, syllabus mapping, model/dataset cards, evaluation results/screenshots, demo checklist and recovery runbook.

Implementation order:

1. Map BDA units to actual Scala FP/RDD/DataFrame/Dataset/lazy-DAG/cache/partition/MLlib/streaming outputs and screenshots; describe local-mode limits.
2. Map TA units to preprocessing/linguistic exploration, BoW/TF-IDF/embeddings, Transformer fine-tuning, aspects, themes/topics, summarization, QA and evaluations. Supporting POS/NER/CRF/HMM/Graph examples are labelled coursework demonstrations, not claimed product features.
3. Present comparable baselines, ablation/calibration/ranking/grounding results with supports, splits, confidence and limitations. Keep binary IMDb vs final three-class metrics separate.
4. Explain score methodology, minimum evidence, model versions, consent, mapping quality and suspicious-review limits.
5. Prepare a coherent movie journey and a separate short real Spark run/UI inspection. Never retrain large models during evaluation; show saved checkpoints and genuine logs.
6. Freeze/cache assets, back up permitted artifacts, practice clean startup and recovery, and verify the demo offline on the laptop.

Tests: new-terminal setup from the documented environment, health checks, all local addresses, offline rehearsal, checkpoint load, report-to-artifact metric consistency and secret/restricted-data review before sharing.

Metrics: reproducible result consistency, demo completion/recovery time and checklist coverage. No inflated syllabus/full-distributed-performance claim.

Expected outputs: academically defensible local demonstration, report, presentation, source and artifact manifests.

Completion checklist:

- [ ] Evidence for every required BDA/TA capability is traceable.
- [ ] Actual measured results and limitations match saved artifacts.
- [ ] Attribution/privacy/consent and distribution boundaries reviewed.
- [ ] Demo rehearsed with no training or paid inference dependency.

## 8. Resource, storage and experiment policies

Use separate operating modes. Training: one compact GPU model, no heavy Spark jobs. Spark: bounded local threads and memory, no Transformer training. Demo: PostgreSQL+backend+frontend and only necessary inference models; Spark/Jupyter started for a specific demonstration only.

| Resource | Initial proposal | Validation required |
|---|---|---|
| GPU training | Sequence128; sentiment micro-batch 4; aspect extraction2–4; configurable accumulation | Forward/backward/AMP test and measured peak memory, including Windows display allocation |
| Data loading | Dynamic padding, num_workers0 initially, memory-mapped/batched datasets | Observe RAM, worker spawning and throughput before increasing |
| GPU inference | One bounded worker, CPU-capable embeddings/STT where sensible, lazy models | Measure cold/warm latency and concurrent memory; no multiple Uvicorn workers duplicating GPU models |
| Spark | local[4] as a trial;3–4 GB driver and 8–16 shuffle partitions only with available headroom | Smaller local[2] first if needed; monitor Spark UI/shuffle/memory and unpersist intermediates |
| Storage | Retain source once, curated Parquet, limited approved checkpoints, known cache paths | Exact inventory after user supplies files; no speculative claim55.8 GiB is sufficient |
| Reserve | Preserve at least20 GB system/project working reserve where practical | Allocate downloads/extraction/venv/cache/checkpoints/scratch separately; user decides location changes |

Training run requests must identify task, data/split hashes, model/license/revision, epochs/max steps, batches, sequence length, expected artifacts, available memory/disk, checkpoint/resume and stop conditions. Runtime estimates are made from a measured short run, not invented in advance.

Git checkpoints are created after a coherent phase output passes relevant checks and the user authorizes working-tree integration. Stage only reviewed paths. Existing208 deletions and duplicate legacy copies remain untouched until a separate explicit source-integration decision.

## 9. Exact next implementation work after approval

The first approved implementation work is Phase 0 foundation completion, followed immediately by Phase 1 validator/mapping work; it is not a frontend build or a training run.

Concrete first sequence:

1. Confirm the approved architecture decisions and a storage/headroom solution without deleting anything.
2. Create safe ignore/configuration files and environment/health diagnostic scripts; preserve the old temp projects and Git changes.
3. Select and record explicit Python 3.11/JDK 21/Scala 2.13/Spark versions, resolve the official Windows Blackwell torch wheel ambiguity, and prepare a concrete installation batch for approval where required. No blanket upgrade.
4. After authorized installations, run tiny CUDA/precision/JVM/Node checks; save actual results. No model training.
5. Create local-only dataset validators and preprocessing/mapping scripts with tiny isolated tests and clear missing-input failures.
6. The real MovieLens/IMDb audits and independent manifest checks have run. Under the explicit 9 November gate exception, continue Phase 2 MovieLens source work while human review/metadata/annotation inputs remain pending. Keep provisional movie IDs and do not claim full Phase 1 acceptance. Runtime Phase 2 processing still requires manual Spark/SBT preparation and measured headroom.

If NLP data remains missing, continue the authorized MovieLens Phase 2 work and report Phase 1 as partial. Do not download replacements, train on the bundled synthetic demo, restore deleted sources or claim an integrated application. Phase 3 training still needs its genuine labels, provenance, approved artifacts and functioning environment.

## 10. Audit hand-off checklist

- [x] Architecture read completely and fingerprinted.
- [x] Existing project/duplicate/archive/config/source/notebook/artifact files inspected at the appropriate safe level.
- [x] Available local data inventoried without large-memory loading; missing sources documented.
- [x] Hardware/software/GPU/storage/RAM checked; failed/unperformed checks distinguished.
- [x] Official compatibility and relevant metadata/model documentation checked.
- [x] Required missing data folders created; raw inputs preserved.
- [x] IMPLEMENTATION_PLAN.md, ENVIRONMENT_AUDIT.md, DATASET_AUDIT.md, AGENTS.md created.
- [x] No packages/datasets/models installed or downloaded; no model trained; no original project file overwritten.
- [x] User approval received for implementation and the narrow dependency-based Phase 2 exception; installation and training are separate.

Current next step: review the generated Phase 3 files and documentation/phase3/RUNBOOK.md. Spark/SBT were subsequently found at configured manual-install paths, and an earlier snapshot of all 15 Scala main sources compiled offline; final-source recompilation and Phase 2 runtime checks remain pending. After the current source-only handoff, the next execution step is the environment/Phase 2 preflight in documentation/bda/RUNBOOK.md. No retraining or installation was performed for file generation.
