# BDA_TA Project Handout for GPT Assistants

**Workspace:** `D:\BDA_TA`  
**User-facing date:** 12 November 2026 (Asia/Calcutta)  
**Purpose:** Give a future assistant enough context to continue the project without confusing generated source with executed or accepted work.

## Project in one paragraph

BDA_TA is an academic Big Data Analytics and Text Analytics project: a locally runnable movie review intelligence, personalized recommendation, and grounded movie discovery application. Scala and Apache Spark process MovieLens data and demonstrate RDDs, DataFrames, MLlib ALS, and Structured Streaming. Python provides trained/evaluated NLP components. FastAPI and PostgreSQL/pgvector connect the services, and Next.js/TypeScript provides the user interface. The final product must use real data and model outputs, show evidence-qualified audience insights, recommend with measured inputs, and ground chat answers in catalogue/review evidence.

## Read these before changing project files

1. Read the full root `ARCHITECTURE.md`; it is the main technical specification.
2. Read `AGENTS.md` for the user's current work boundary and preservation rules.
3. Read `IMPLEMENTATION_STATUS.md` for observed progress and evidence.
4. Use the phase runbook for the task at hand:
   - `documentation/bda/RUNBOOK.md` — Phase 2 Spark
   - `documentation/phase3/RUNBOOK.md` — Phase 3 sentiment and language extension
   - `documentation/phases4-8/RUNBOOK.md` — Phases 4–8 NLP, scoring, and recommendations
   - `documentation/phases9-11/RUNBOOK.md` — application, UI, discovery, and voice
   - `documentation/phase12/RUNBOOK.md` and `documentation/final/` — validation and academic/demo evidence

The implementation plan is `IMPLEMENTATION_PLAN.md`. Audited dataset and environment facts are recorded in `DATASET_AUDIT.md` and `ENVIRONMENT_AUDIT.md`. Do not treat a proposed choice in those documents as an approved architectural change.

## Current state

The latest status ledger is dated 11 November 2026. Phase 0's available foundation checks are largely complete. Phase 1 remains partial; Phase 2 has meaningful but incomplete Spark execution evidence. Phases 3–13 have source prepared, while their runtime, scientific, integration, and acceptance work remains open. In particular, later generated tests have not been run, and source generation does not complete any phase gate.

Recorded work includes:

- Audits and validators for the locally supplied MovieLens and IMDb files; no raw dataset was edited.
- Phase 2 Scala source and a real standalone Spark analytics run with **30/30 assertions**. A JAR was built for a recorded earlier source snapshot. Later Scala edits need a fresh final-source compile. Full MovieLens Parquet/batch reconciliation, the final SparkTest/runtime gate, and streaming lifecycle acceptance remain open.
- Python test runs recorded at earlier project checkpoints (including 180 passed), plus current static source/config checks. These results apply to their fingerprinted snapshots and must not be reused to claim that later generated code passed runtime tests.
- Next.js TypeScript `--noEmit` checking passed for its recorded snapshot. No application build or browser acceptance was established.
- Final static source checks cover Python, JSON/YAML, notebooks, Scala syntax, TypeScript, PowerShell, and backend schema-column correspondence. Static checks do not establish runtime behavior, database validity, model quality, or system integration.

See `IMPLEMENTATION_STATUS.md` and its linked evidence reports for exact hashes and dates. Report only the evidence applicable to the current source snapshot.

## Data and model constraints

- The user manually supplies datasets under `data/raw/`. Do not fetch, scrape, or automatically download datasets, models, or metadata.
- MovieLens 32M provides ratings, tags, catalogue rows, and external links. Ratings are not textual reviews.
- IMDb/aclImdb is a binary English benchmark with official splits. It has no reliable application movie mapping; do not invent neutral labels or use its test split for training or tuning.
- The latest audit found 124 missing TMDB references and 36 duplicated TMDB-ID groups affecting 72 relationships. Keep unresolved mappings quarantined; title similarity is only a manual review signal. Do not invent canonical IDs.
- The latest inventory found no permitted first-party/licensed review corpus, human sentiment/aspect/theme annotations, or TMDB snapshots. Genuine review permissions, canonical mappings, adjudicated labels, and split approvals are still required for the relevant NLP/application claims.
- Keep MovieLens research-user IDs separate from application accounts. Keep legacy demo IDs and synthetic fixtures out of real evidence.
- Preserve original Unicode review text and source provenance. Do not claim consent, authenticity, training eligibility, or movie linkage from `source=user` alone.
- Never invent metrics, predictions, summaries, audience scores, mapping decisions, or evaluation examples. Empty evidence must remain explicitly empty; unsupported claims abstain.

## Phase-by-phase execution still needed

1. **Phase 1 — data acceptance:** review provenance/rights; resolve and approve real canonical mappings; supply permitted movie-linked reviews and human annotations; review language, neutral/mixed, sarcasm, aspect, theme, and split policies. This is partly manual data/annotation work, not just running scripts.
2. **Phase 2 — Spark acceptance:** recheck the current environment and resources; compile final Scala sources; run the authored Scala tests and small Parquet smoke; process the actual MovieLens inputs; verify reconciliation/quarantine; exercise streaming publication, replay, restart, late data, revisions, conflicts, and deletions; capture Spark plans/UI and measured results.
3. **Phase 3 — sentiment/language:** prepare and review disjoint task splits, run comparable TF-IDF Logistic Regression and Linear SVM baselines, verify the selected CUDA/precision path, run an approved small checkpoint/resume smoke, then train/tune/calibrate/evaluate actual English and supported multilingual/sarcasm tasks. Reserve final test evaluation until selection is frozen.
4. **Phases 4–8 — review intelligence and recommendations:** train/evaluate aspect extraction and target sentiment; theme relevance and exploratory topics; approved embeddings and evidence-grounded summaries; legitimate review-risk signals; score policy and Python/Scala parity; then ALS, content/hybrid ranking, cold-start behavior, and temporal ranking evaluation.
5. **Phases 9–11 — integrated application:** after actual artifacts and data exist, manually prepare reviewed dependencies and a local PostgreSQL/pgvector instance; review and run migrations; import approved catalogue data; register models; run API/worker/frontend; check real authentication, review lifecycle, recommendations, grounded discovery, responsive UI, and optional offline speech.
6. **Phases 12–13 — acceptance/submission:** run the authored unit, disposable-database, browser, model-reload, benchmark, parity, grounding, and resource checks as applicable; fix and rerun failures; populate academic reports only from genuine evidence; rehearse the local demo and review the distribution bundle.

The sequence is dependency-driven. The user's Phase 2 exception allowed Scala source/check progress while Phase 1 NLP requirements remained open. It did not waive Phase 1 or permit invented mappings/data. Keep heavy Spark and GPU-training workloads sequential on the laptop.

## Active work boundary

The latest recorded user scope is **generate files; the user will implement/run later**. Phase 12–13 source generation was authorized, and the complete source preparation through Phase 13 is recorded. Under that scope, do not install or resolve packages, download data/models, train, fit, evaluate, run inference or tests, migrate/connect a database, run Spark jobs, build/start services, or publish. Static parsing/configuration checks were allowed for that file-generation delivery. A future explicit user instruction can change this boundary; do not infer broader authorization from source-generation requests or old phase approvals.

Do not ask the user to approve work they already authorized. Do ask only when a genuinely new material architectural/methodology decision or restricted action requires it. Complete authorized preparation first and make any needed approval request specific and reviewable.

## Workspace preservation and reporting rules

- Work only in `D:\BDA_TA` unless the user authorizes another location. Inspect existing files before editing; create a new path instead of overwriting user-owned content when possible.
- Preserve `temp/`, legacy sources, raw/processed datasets, SQLite databases, model artifacts, and user edits. Do not clean up, restore, reset, stage, commit, move, or delete as routine housekeeping.
- Exclude `.git`, environments, `node_modules`, and generated caches from broad searches. Inspect ignored user data separately. Do not import side-effectful legacy modules or deserialize pickle/joblib artifacts to inspect them.
- Keep secrets out of reports, shell output, Git, and browser bundles. Do not print full environment dumps or credential-bearing database URLs.
- Do not run tests unless the user asks or a current explicit task authorizes them. State exactly which checks were run, failed, or deferred.
- Distinguish observed execution, static inspection, documentation, inference, and proposed decisions. Historical results apply only to their recorded source/input hashes.

## Immediate next step when execution is authorized

Follow `documentation/bda/RUNBOOK.md` and `PREREQUISITES.md`. First recheck the manually installed environment and Spark preflight, then prepare the final-source Phase 2 build/test/smoke/batch/stream evidence while resolving Phase 1 data decisions. Do not jump to model runs before the genuine input, rights, split, and run-approval records are ready. The runbooks contain the exact commands and output safeguards.

## Product invariants

- Metadata, user ratings, review sentiment, aspect/theme reception, theme relevance, and personalized match are distinct concepts.
- The displayed audience score remains null until approved evidence thresholds are met, with the exact empty-state text **“Not enough audience reviews yet.”**
- Aspect sentiment comes from evidence about that aspect; whole-review polarity cannot be copied onto every aspect.
- Theme relevance and audience reception are separate. Metadata keywords do not establish audience reception.
- Review-risk analysis is moderation support, not a proven fake label; sentiment extremity alone is not a risk signal.
- Chat uses the shared catalogue/recommendation/evidence services. Reviews and metadata are untrusted content, never instructions. No unsupported movie facts, counts, or consensus claims.
- Local core inference and demonstration must not depend on paid cloud inference. Browser speech support is not guaranteed offline; keep text input.

