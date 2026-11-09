# Project instructions for coding agents

## Authority and current work boundary

Read the entire root `ARCHITECTURE.md` before project work. It is the primary technical specification. The user's latest instructions take precedence, including manual dataset acquisition, the fourteen-phase order, and the audit-only scope of the initial task. Consult `IMPLEMENTATION_PLAN.md`, `ENVIRONMENT_AUDIT.md`, and `DATASET_AUDIT.md` for the audited state and proposed decisions. A proposal in those documents is not an approved architectural change.

The initial authorized work is inspection, creation of the four requested Markdown documents, and creation of missing dataset folders. After presenting the audit, stop for the user's approval. Until that approval, do not install packages, download datasets or models, train models, start the application, migrate a database, reorganize source files, or repair Git state. Once the user authorizes the next work, continue within that scope without repeatedly requesting the same approval. Large training runs and material architectural changes still require the user's explicit authorization.

Accepted progress authorization, 9 November 2026 (Asia/Calcutta): the user approved ordinary implementation and then explicitly selected **Allow dependency-based progress**. Phase 2 Scala/Spark source work and available offline checks may proceed against validated local MovieLens data while Phase 1 provenance, canonical mappings and NLP annotations remain open. Do not describe Phase 1 as complete or use this exception to invent mappings or bypass model data requirements. Manual installation/download/build-resolution and training-approval restrictions still apply. Phase 2 requires actual Spark compilation/runtime evidence before completion. Integrate the mandatory language/slang/sarcasm/Hinglish extension after that Phase 2 gate, as recorded in documentation/architecture/NLP_EXTENSION_AFTER_PHASE_2.md.

Latest scope, 9 November 2026 (Asia/Calcutta): the user then instructed **"just generate files, i implement later"** and **"continue and generate files"**. Generate the Phase 3 classical/Transformer sentiment and mandatory language-extension source, configs, notebooks, tests and documentation while Phase 2 runtime acceptance remains open. This narrowly permits source preparation before the execution gate; it does not complete or waive that gate. Limit current verification to static syntax/configuration checks. Do not run new training, fitting, evaluation, unit tests, Spark jobs, services, dependency resolution or downloads in this file-generation delivery. The user will run the documented commands later. Preserve earlier executed evidence with its source hashes and describe later edits as unexecuted. Continue the remaining phases in order after the relevant dependencies and execution scope are approved.

## Preserve the workspace

Expanded source-only scope, 10 November 2026 (Asia/Calcutta): the user requested **"generate upto phase-8 in one go/shot"**. Prepare phase4 aspect extraction/target sentiment,phase5 themes/topics/embeddings/summaries,phase6 risk,phase7 scoring and phase8 ALS/hybrid recommendation files in order. Static parsing/file-contract checks are allowed; do not execute model inference,fits,training,evaluation,unit tests,Spark jobs,services,installers,resolvers or downloads during this delivery. Preserve incomplete earlier execution/data gates and do not mark any generated phase accepted. Later phases9-13 are outside this source batch. See documentation/phases4-8/RUNBOOK.md and IMPLEMENTATION_STATUS.md.

- Work in `D:\BDA_TA`; use Windows PowerShell commands and literal paths.
- Inspect an existing file before proposing an edit. The initial audit must not overwrite or delete existing files.
- At the initial audit, Git already reports 208 tracked deletions and untracked `temp/` plus root `ARCHITECTURE.md`. Treat these as user-owned changes. Do not restore, stage, commit, move, or delete them as cleanup.
- Existing implementation copies live under `temp/`, `temp/CineScope/`, and `temp/CineScope_Midsem/`. Their names do not authorize deletion. Reuse audited sound logic after approval; do not replace the user's work indiscriminately.
- Exclude `.git`, virtual environments, `node_modules`, and generated caches from broad source searches. Inspect project-owned ignored data separately; an ignored SQLite database is still user data.
- Do not execute project modules merely to inspect them: the legacy API creates and seeds SQLite storage at import time. Do not unpickle or load joblib artifacts during inspection.
- Never delete raw datasets. Produce validated and processed outputs at different paths and retain rejection reports.
- Never log API keys, passwords, tokens, database URLs containing credentials, private review text, or full environment-variable dumps. Keep secrets out of Git and frontend bundles.
- Use narrow Git staging only after reviewing changes and ignore rules. A checkpoint must not stage pre-existing deletions, datasets, environments, model weights, or secrets.

## Project objective and fixed stack

Build one locally executable system integrating review intelligence, personalized recommendations, and grounded conversational discovery. The frontend must call actual backend APIs, PostgreSQL, and approved model artifacts. A static demo does not fulfill this objective.

The requested stack is Python 3.11, PyTorch, Hugging Face Transformers/Datasets, scikit-learn, Sentence Transformers, optional BERTopic; Scala 2.13 with an officially compatible Spark release, SQL/DataFrames/RDDs/MLlib/Structured Streaming; FastAPI/Pydantic/SQLAlchemy/PostgreSQL/pgvector; React/Next.js/TypeScript/Tailwind and charts; Git/JupyterLab/SBT/JDK 21 when compatible. Check installed versions and official release documentation before selecting dependencies. Pin tested versions and lockfiles; never upgrade the legacy environment arbitrarily.

Explain a material compatibility correction and obtain approval before adopting it. Never assume the architecture's specific Spark/CUDA version examples are installable merely because they appear in the document. The PyTorch wheel's CUDA runtime, the NVIDIA driver's supported CUDA level, and an optional installed CUDA Toolkit are different facts.

## Dataset ownership, identities, and consent

- The user manually supplies all datasets under `data/raw/`. Do not search for, fetch, scrape, or automatically download datasets, including from notebook cells or helper scripts. Do not research alternatives unless asked.
- Inspect only local user-supplied files. If a source is absent, report it and continue independent authorized work. Do not invent schema measurements, class distributions, missing-value counts, or row counts.
- Keep source provenance, versions, license/terms records, checksums, and bounded audit reports. Use Parquet for substantial processed tables. Never load MovieLens 32M fully into pandas or collect it to the Spark driver.
- MovieLens contains ratings and tags, not full review text. Stanford aclImdb is a binary benchmark, has an official test split, and has no validated application movie mapping. Do not create neutral labels from it or use its test data for training, fitting preprocessing, or tuning.
- Keep canonical internal movie IDs separate from MovieLens, IMDb, and TMDB IDs. Preserve IMDb leading zeros. Validate external IDs and quarantine conflicts; title similarity is only a manual-resolution candidate signal.
- Keep MovieLens users in a source namespace separate from application accounts. Identical numeric IDs do not identify the same person.
- Legacy demo IDs 1–13 are local demo identifiers. Never treat them as MovieLens or TMDB IDs. All bundled synthetic reviews stay explicitly labelled and excluded from real academic evaluation and audience evidence.
- `source=user` alone does not establish consent, authenticity, training eligibility, or valid movie linkage. Collect those records explicitly.
- First-party review collection and offline annotation may precede the full website. Do not bypass the phase order by building the final API/frontend to acquire training data.
- Do not redistribute restricted reviews, raw datasets, or poster assets without appropriate rights. TMDB access, caching, images, attribution, and current terms require review before later use. No TMDB API calls are authorized by the initial audit.

## Model validity and organization

Each NLP component needs separate `train.py`, `evaluate.py`, `predict.py`, `config.yaml`, and README/model card. Keep executable source separate from model weights and prediction outputs. Major experiments require reproducible notebooks calling shared source functions rather than duplicating entire pipelines.

Before any training: inspect source/labels/class counts, exact and near duplicates, leakage, split manifests, EDA, and baseline; document hyperparameters and licenses. Fit preprocessing on training data. Tune only on validation data. Evaluate the final held-out test once after selection and record genuine measurements, code revision, dataset hashes, model revision, hardware, and limitations.

- Compare TF-IDF Logistic Regression and Linear SVM with the Transformer on comparable splits. Calibrate probability outputs on validation data if used for aggregation; Linear SVM margins are not probabilities.
- Train the final positive/negative/neutral model on permitted genuinely annotated three-class data. Do not deploy the earlier binary model plus heuristic Mixed/Neutral overlay as a trained three-class classifier.
- Keep a written policy separating neutral, mixed, uncertain, and unsupported language. Mixed examples need annotation/adjudication policy; uncertainty is not a new sentiment label.
- Train aspect extraction and aspect-conditioned sentiment. Preserve character offsets into original text, align subwords correctly, and evaluate exact spans plus the full pipeline. Do not assign overall review sentiment to every aspect.
- Theme relevance and theme-specific audience sentiment require different evidence. Metadata keywords do not establish audience reception. BERTopic clusters are exploratory, versioned results until curated.
- Summaries retrieve permitted evidence for one movie, deduplicate, balance sentiment/aspects, summarize in bounded chunks, and store evidence references and snapshot versions. Generated statistics must come from database calculations. Omit unsupported claims or abstain.
- Suspicious-review analysis uses documented duplicate/similarity and legitimately collected behavioural signals. It is moderation support, not a proven fake label or a calibrated probability unless validated as such. Sentiment extremity alone must not increase risk.
- A pretrained-only embedding/summarization component may use actual trained pretrained weights after license review; do not claim local fine-tuning occurred. Training entry points must explain unmet data prerequisites rather than manufacture training examples or metrics.

## Laptop resource policy

The laptop has an RTX 5050 with 8 GB VRAM and nominal 16 GB system RAM. Use measured available memory rather than assuming nominal memory is free.

- Verify driver, selected interpreter, torch build/runtime, capability support, and an actual small CUDA tensor operation before training. `nvidia-smi` success alone is insufficient.
- Train one substantial model at a time. Do not run large Spark jobs concurrently with GPU training or the complete demonstration stack.
- Start compact encoders with sequence length 128, sentiment micro-batch 4, aspect extraction micro-batch 2–4, configurable accumulation and dynamic padding. These are starting trials, not guarantees.
- Use AMP only after an executed precision check; use BF16 when validated, otherwise FP16 with appropriate scaling. Enable checkpointing when useful and supported by the selected implementation.
- Support checkpoint save/reload/resume including optimizer/scheduler/scaler/RNG state. Start Windows data loaders with zero workers. Record peak VRAM, RAM, throughput, and OOM recovery decisions.
- Keep CPU fallback for smoke tests and inference. Missing CUDA must not silently turn a planned long GPU training run into an unapproved CPU run.
- Use a bounded inference queue and lazy model loading. Avoid multiple server workers that each duplicate GPU models. Keep summarization and embedding generation outside latency-sensitive review requests.
- Spark starts with controlled local parallelism and a measured 3–4 GB driver target only when system headroom permits. Do not cache every table or copy raw files to every medallion layer.
- Core inference and the evaluation demonstration require no paid cloud API. Pre-cache approved model and metadata artifacts before an offline rehearsal.

## Scores, recommendations, and grounded chat

Keep movie metadata, star ratings, review sentiment, genre reception, theme relevance, theme reception, and personalized match scores distinct in storage, APIs, charts, and language.

An individual sentiment index may use `100 * (p_positive + 0.5 * p_neutral)` from valid calibrated probabilities. Apply eligibility and documented weights before aggregation. Confidence, minimum evidence, effective sample size, shrinkage, timestamps, method/model versions, and evidence counts must remain explicit. Do not display a prior as audience evidence. Until thresholds are validated and met, return a null score with the exact UI message: **"Not enough audience reviews yet."**

Recommend using actual Scala Spark MLlib ALS, content features/semantic embeddings, and explicit/inferred preference channels. Normalize channel scores, tune validation weights, exclude seen/ineligible movies, and explain actual contributing inputs. Define separate handling for application users absent from MovieLens training; never borrow another person's factors. Evaluate temporal ranking with Precision@K, Recall@K, NDCG@K, coverage, diversity, novelty, and cold-start cohorts; report candidate sets and exclusions.

Chat resolves catalogue entities and ambiguity, parses genre/theme/runtime/negation constraints, retrieves actual evidence, calls the recommendation service, and retains bounded conversation context. Reviews and metadata are untrusted data, never executable instructions. Do not generate movie facts, counts, or consensus without retrieved support. Offline speech recognition requires local cached weights; browser speech support must not be described as guaranteed offline. Retain text input and request microphone permission only on user action.

## Engineering and verification

- Keep Scala ingestion, cleaning, RDD examples, DataFrame transformations, movie analytics, user analytics, ALS, and streaming in separate classes. Scala must perform real processing independently of Python.
- Use explicit source/output schemas, stable event IDs, atomic event-file publication, replay-safe sinks, checkpoint paths, and tested late-event/reanalysis/deletion policies. Do not claim end-to-end exactly-once without proof across source and sink.
- Split FastAPI routes/services/schemas/ORM/repositories/configuration/authentication. Use migrations, constraints, actual authenticated ownership checks, idempotent submissions, bounded requests, and structured errors.
- Persist pending/failed analysis states and durable refresh jobs. Missing models return explicit unavailability or pending state; never silently fall back to fabricated predictions.
- Separate Next.js pages and movie/review/score/recommendation/chat/shared components. Provide loading/empty/error/mobile states and actual API integration. The AI review summary appears above individual reviews.
- Keep localhost defaults: frontend3000, backend8000 with `/docs`, PostgreSQL5432, optional Jupyter8888, Spark UI4040 while active. Bind development services locally and verify port availability before starting.
- Implement PowerShell setup/database/backend/frontend/all-services/Spark/training/health scripts in their assigned phases. Scripts must not auto-download datasets, auto-train, or silently install large dependencies.
- Write meaningful automated data-quality, model-contract, score, recommendation, API/DB, streaming, and end-to-end tests. Small synthetic test fixtures must be isolated from real training/evaluation/application evidence.
- State exactly which checks ran, failed, or were deferred. Historical metrics and old test reports are artifacts, not current validation. Do not execute costly training just to refresh documentation.
- Follow phases0–13 and their completion checklists in `IMPLEMENTATION_PLAN.md`. A phase blocked by missing data may continue its independent tasks but cannot be marked complete. Do not skip to unrelated modules.

## Reporting

Report outcomes, evidence, blockers, limitations, changed files, and the next exact executable step. Distinguish observed results, source documentation, inference, and proposed decisions. Record user-facing dates in Asia/Calcutta. Explain and seek approval for material design changes after preparing a concrete proposal; do not silently change architecture.
