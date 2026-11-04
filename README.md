# CineScope — Movie Review and Recommendation System

A complete academic codebase for **Big Data Analysis + Text Analytics**, with a responsive movie UI, a local FastAPI application, nine Jupyter notebooks and six Scala programs.

## Start in five minutes

Use **Python 3.11** (3.10–3.12 supported). Extract this folder, open a terminal inside it, and run:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux instead:
# source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[notebooks,dev]"
python -m uvicorn cinescope.api:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. The API documentation is at **http://127.0.0.1:8000/api/docs**. No API key, GPU, Node.js or paid model is needed for the default sample app. This delivery includes a **trained TF-IDF sentiment model** (90.05% binary accuracy on 24,799 deduplicated held-out IMDb reviews) and **trained MovieLens-small ALS factors**. Runtime analysis blends that binary model with contextual negation and explicit Mixed/Neutral rules; the binary benchmark must not be presented as four-class accuracy. The trained model loads automatically; ALS activates only with the real catalog. See `models/model-card.json` and the measured reports in `artifacts/`. Ratings and submitted reviews persist in SQLite. Stop with Ctrl+C.

For the containerized build:

```bash
docker compose up --build
```

The image runs as an unprivileged user, persists SQLite data in a named volume, and includes an application health check.

To open the notebooks:

```bash
python -m jupyterlab notebooks
```

The standalone frontend also works with `python -m http.server 8080 --directory frontend` at http://127.0.0.1:8080. Without the Python API, it explicitly uses the browser demonstration engine and browser-local history. Opening `index.html` directly as a `file://` URL will not work because the UI loads JSON and JavaScript modules.

## What is implemented

| Feature | Implementation | Default behavior / activation |
|---|---|---|
| Live four-label sentiment | Positive, Negative, Mixed and Neutral labels; cancellable debounced requests; identical API and browser-fallback contracts | Binary TF-IDF/DistilBERT signal blended with contextual negation, clause conflict and neutral cues |
| Six aspect scores | Story, Acting, Visuals, Music, Pacing, Ending; clause evidence; optional trained aspect transformer | No mentioned opinion → null; no invented score |
| Genre and theme scores | Named taxonomy with clause-level mention coverage | Relevance/coverage percentages, not quality or calibrated probabilities |
| All-review summary | Deduplication, flagged-review exclusion, whole-population aspect/sentiment aggregation, positive and negative evidence excerpts | Counts and synthetic-data provenance shown |
| Personalized recommendations | Signed ratings, recency weighting, TF-IDF content, optional ALS factor fold-in, seen-item exclusion, diversity penalty | Content path works immediately; ALS loads after training on real MovieLens IDs |
| Genre combinations | AND filtering, e.g. Sci-Fi + Romance; theme constraints | Both genres must be present |
| Conversation | Stateful catalog retrieval, title-linked review summaries, exclusions and runtime filters | Deterministic retrieval by default; optional semantic embeddings and local transformer wording |
| Speech-to-text | Browser SpeechRecognition plus optional local faster-whisper endpoint | Browser support/permission required; text input always available |
| Review integrity | Exact/near duplicate, repetitive/promotion signals and a training audit queue | Screening, **not proof that a review is fake** |
| New movies/users | Metadata content ranking; exploration for unrated users | No invented review summary or rating for a new title |
| Historical review processing | Idempotent JSONL ingestion and batch analyzer | The same analyzer used by live API requests |
| Big-data processing | Spark ETL, RDD/DataFrame/Dataset examples, MLlib sentiment and ALS, Structured Streaming, Hadoop MapReduce | Run with Java 17 and Spark 3.5.7 |

The review path includes bounded input, rate limiting, request IDs, safe error responses, idempotent submissions, SQLite WAL persistence, cancellation of stale live-analysis requests, security headers and non-root container execution. The user ID in the wider recommendation API is still a research identifier, not an authentication mechanism. Keep the supplied launcher on localhost or place it behind TLS and authenticated ownership checks before exposing it publicly. For multiple API replicas, replace the in-memory rate limiter with a shared store and use managed relational storage rather than a shared SQLite file.

## Project layout

```text
CineScope/
  frontend/              Responsive HTML/CSS/JS UI; no build needed
  backend/cinescope/     API, persistence, inference, training, ranking, chat, evaluation
  notebooks/            00–08: executable course and experiment notebooks
  scala/                sbt project with six Scala programs
  scripts/              Download, prepare, join, ingest, batch analyze, export events/factors
  data/demo/            13 sample titles and 36 explicitly synthetic reviews
  data/taxonomy.json    Aspect/genre/theme definitions and fallback lexicons
  models/               Your saved model artifacts
  artifacts/            Metrics, audit reports and experiment results
  tests/                Meaningful inference/API/data-contract checks
  docs/                 Dataset guide, architecture, syllabus mapping and validation
```

The sample title **The Last Signal** is fictional and intentionally has no reviews, to demonstrate cold start. Other sample movie metadata are brief project-authored descriptions; all bundled review texts are synthetic. Movie images are attributed to TMDB and remain the property of their respective rights holders.

## Real datasets and training

Read [docs/DATASETS.md](docs/DATASETS.md) for source terms and schema distinctions. Raw datasets and pretrained transformer weights are not redistributed in this package.

### 1. Download and prepare

```bash
python scripts/download_data.py movielens-small
python scripts/download_data.py imdb-reviews
python scripts/prepare_imdb.py
```

For the large-scale course experiment, use `movielens-32m` and the Scala ETL instead of pandas. The small dataset is for functional development; it is not evidence of big-data performance.

### 2. Train sentiment

Open **02_Text_Representations_and_Sentiment.ipynb** and set `RUN_TRAINING=True`, or run:

```bash
python scripts/train_sentiment.py
```

The pipeline saves `models/sentiment_tfidf.joblib` and a real held-out metrics JSON. Restart the API; `/api/health` should report `tfidf-logistic-regression`. To force the transparent lexicon/context engine, set `CINESCOPE_SENTIMENT=lexicon` in your shell.

For fine-tuning, install the transformer extras and use notebook 03:

```bash
python -m pip install -e ".[transformers]"
```

A GPU is recommended. Sentiment labels come from IMDb. Aspect labels must be collected separately using the generated annotation template; a whole-review positive label must not be copied to every aspect. No trained transformer or annotated aspect corpus is implied by the presence of this code.

### 3. Link real movies and reviews

MovieLens `links.csv` maps `movieId` to `imdbId` and `tmdbId`. Use the IDs, not movie-title guesses. IMDb IDs are normalized to `tt` plus at least seven digits.

Set your **TMDB API read access token** in your terminal:

```powershell
$env:TMDB_BEARER_TOKEN="your-token"
```

```bash
# macOS/Linux equivalent:
export TMDB_BEARER_TOKEN="your-token"
python scripts/ingest_tmdb.py --movielens data/raw/ml-latest-small --limit 100 --pages 3
python scripts/build_catalog.py --movielens data/raw/ml-latest-small
python scripts/ingest_reviews.py data/processed/tmdb_reviews.jsonl
```

Then set `CINESCOPE_CATALOG` to the **absolute path** of `data/processed/catalog.json` and restart the app. It will use a separate `data/real-app` database. `.env.example` documents all available settings; copying it does not automatically load it, so export values in the shell before launching.

TMDB reviews are linked but sparse. The Stanford corpus is an older binary classification benchmark. Its review file index is **not** a movie ID; `prepare_imdb.py` uses its URL files to recover title IDs. Do not assume MovieLens users and IMDb/TMDB reviewers are the same people.

### 4. Train ALS

Install **Java 17**, **sbt**, and **Spark 3.5.7 built for Scala 2.12**. Build once:

```bash
cd scala
sbt package
cd ..
spark-submit --master "local[2]" --class cinescope.MovieETL scala/target/scala-2.12/cinescope-spark_2.12-1.0.0.jar data/raw/ml-latest-small data/spark
spark-submit --master "local[2]" --class cinescope.ALSRecommender scala/target/scala-2.12/cinescope-spark_2.12-1.0.0.jar data/raw/ml-latest-small/ratings.csv artifacts/scala_als
python scripts/export_als.py artifacts/scala_als/item_factors --reg-param 0.1
```

**Use the selected `reg_param` from `artifacts/scala_als/metrics`, not the example value blindly.** This value is required for consistent user-vector fold-in. Alternatively notebook 05 automatically exports the chosen value with the factors. That notebook also works through PySpark (`python -m pip install -e ".[spark]"`).

ALS factors are used only with the real catalog. Demo IDs are a separate namespace, so the backend deliberately refuses to blend a real MovieLens model with demo movie IDs. Evaluate cold-start coverage and ranking quality as well as RMSE.

### 5. Batch and streaming reviews

```bash
python scripts/batch_analyze.py data/processed/tmdb_reviews.jsonl
python scripts/export_events.py --db data/real-app/cinescope.sqlite3 --out data/events --watch
# In another terminal:
spark-submit --master "local[2]" --class cinescope.ReviewStream scala/target/scala-2.12/cinescope-spark_2.12-1.0.0.jar data/events data/stream-output data/checkpoints/reviews
```

The exporter commits complete JSON event files atomically; Spark commits output with a durable checkpoint. Review IDs are the deduplication key. Its 24-hour watermark intentionally bounds state: events older than that window can be dropped and duplicates outside the window can recur. Historical/backfill processing should use the batch path with source-ID deduplication, not pretend the live stream is a full historical store.

The Scala sentiment job consumes notebook 01's JSONL:

```bash
spark-submit --master "local[2]" --class cinescope.SentimentPipeline scala/target/scala-2.12/cinescope-spark_2.12-1.0.0.jar data/processed/imdb_reviews.jsonl models/spark_sentiment
# Supply models/spark_sentiment/model as the optional fourth ReviewStream argument.
```

Hadoop: `hadoop jar <compiled-jar> cinescope.HadoopWordCount <review-text-input> <new-output-directory>`.

### 6. Semantic conversation and speech

Use notebook 06 to download optional model files, then set:

```text
CINESCOPE_EMBEDDING_MODEL=/absolute/path/models/movie_embeddings
CINESCOPE_CHAT_MODEL=/absolute/path/models/movie_chat
CINESCOPE_WHISPER_MODEL=/absolute/path/models/whisper-small.en
```

Install `.[transformers,speech]` first. The browser microphone fills the text box; you choose when to send the message. When browser speech is unavailable and the local speech model is enabled, the UI records up to 30 seconds and calls `/api/transcribe`. Browser speech may depend on the browser vendor's online service. Transformer wording is experimental; factual movie cards and review summaries remain grounded in the stored data.

## Main API routes

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Active model and feature status |
| `GET /api/movies?q=...` | Search canonical titles/themes, with pagination |
| `GET /api/movies/{id}` | Metadata, all-review aggregate and evidence |
| `POST /api/analyze` | Analyze `{text,movie_id}` without saving |
| `POST /api/reviews` | Analyze and save a review; optional UUID `request_id` makes retries idempotent |
| `PUT /api/users/{user}/ratings` | Save `{movie_id,rating}` in half-star steps |
| `GET /api/users/{user}/history` | User ratings/history |
| `GET /api/users/{user}/recommendations` | `q`, comma-separated `genres`/`themes`, `limit` |
| `POST /api/users/{user}/chat` | `{message,context}`; return context with next request |
| `POST /api/transcribe` | Raw audio bytes; optional downloaded Whisper |

## Validation and reporting

```bash
python -m pytest -q
python scripts/check_notebooks.py
```

See [docs/VALIDATION.md](docs/VALIDATION.md) for what was actually run for this delivery and what still needs your data/GPU/credentials. See [docs/SYLLABUS_MAP.md](docs/SYLLABUS_MAP.md) for the course-to-code mapping and [docs/EVALUATION.md](docs/EVALUATION.md) for the experiment plan.

Never present the synthetic sample reviews, heuristic aspect indices or screening signals as validated model results. Report actual saved metrics, data split, candidate-set policy, hardware and limitations in your course submission.
