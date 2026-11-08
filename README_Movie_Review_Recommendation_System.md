# Movie Review & Recommendation System

> An AI-powered movie intelligence platform combining Big Data
> Analytics, multilingual Text Analytics, explainable audience insights,
> and personalized movie discovery.

**Project status:** In active development\
**Academic focus:** Big Data Analytics (BDA) · Text Analytics (TA)\
**Deployment target:** Local-first application for academic
demonstration

------------------------------------------------------------------------

## Overview

The Movie Review & Recommendation System is designed to help users
understand films through audience reviews and discover movies that match
their interests.

Instead of relying only on star ratings or generic recommendations, the
system analyses what viewers actually say. It aims to classify review
sentiment, identify movie aspects, extract recurring themes, summarize
audience opinions, detect suspicious review patterns, and recommend
films using user preferences and interaction history.

The project combines two complementary areas:

-   **Big Data Analytics:** scalable ingestion, cleaning,
    transformation, aggregation, and collaborative filtering using Scala
    and Apache Spark.
-   **Text Analytics:** sentiment analysis, aspect-based sentiment
    analysis, multilingual language understanding, sarcasm detection,
    semantic retrieval, and review summarization using NLP and
    Transformer models.

The target is a locally executable application with a web interface, API
backend, database, and locally hosted model inference.

> **Development status:** This repository is under active development.
> Features described here are project objectives unless implementation
> and evaluation evidence has been published. Model metrics will be
> added only after experiments have been run on documented, held-out
> test sets.

## Core features

### 1. Movie review intelligence

The planned review-analysis pipeline includes:

-   **Three-class sentiment analysis:** positive, negative, and neutral
    predictions with class probabilities.
-   **Aspect-based sentiment analysis:** identify what a reviewer
    discusses---acting, story, screenplay, direction, cinematography,
    pacing, music, visual effects, and other aspects---and determine the
    sentiment toward each aspect.
-   **Theme and genre insights:** identify recurring themes and analyse
    audience reception when sufficient relevant review evidence exists.
-   **Evidence-grounded review summaries:** surface recurring praise,
    criticism, and differing opinions.
-   **Suspicious-review risk signals:** identify duplicates,
    near-duplicates, repetitive templates, and other available anomaly
    signals for moderation assistance.

### 2. Context-aware language understanding

Movie reviews are informal and often multilingual. The system is
intended to handle:

-   English reviews and internet slang.
-   Emojis, emoticons, hashtags, expressive punctuation, and repeated
    characters.
-   Sarcasm and irony, with uncertainty represented rather than assumed.
-   Hindi in Devanagari script.
-   Romanized Hindi.
-   Hinglish and Hindi-English code-switching.
-   Negation and mixed opinions within the same review.

Examples of target behaviour:

  ---------------------------------------------------------------------------
  Review                                      Intended interpretation
  ------------------------------------------- -------------------------------
  `Bhai movie ekdum mast thi 🔥`              Positive

  `Story bilkul bakwaas thi`                  Negative

  `Acting was amazing but story boring thi`   Mixed, aspect-specific
                                              sentiment

  `Wah bhai kya masterpiece hai 🙄`           Potential sarcasm; context
                                              matters

  `पिक्चर अच्छी थी लेकिन क्लाइमेक्स बेकार था`        Mixed Hindi review
  ---------------------------------------------------------------------------

These examples are illustrative, not guaranteed predictions. Language
support and model quality must be established through annotated
evaluation data.

### 3. Movie audience intelligence

For movies with sufficient eligible review evidence, the system aims to
calculate:

-   Overall audience sentiment score on a 0--100 scale.
-   Aspect-level audience reception.
-   Genre-level reception.
-   Theme-specific audience reception.
-   Review volume, evidence strength, and score freshness.

The score summarizes review sentiment; it is **not** a critic rating, a
star rating, or a direct copy of a third-party score.

Theme relevance and audience sentiment are separate concepts. A theme
can be prominent in a movie without being positively or negatively
received.

**Evidence-first scoring:** if there are not enough eligible reviews,
the system should display **"Not enough audience reviews yet"** rather
than inventing an audience score. Any metadata-based cold-start estimate
must be labelled provisional and must never be presented as
review-derived audience sentiment.

### 4. Personalized recommendations

The planned hybrid recommendation engine combines:

-   Collaborative filtering using Spark MLlib ALS.
-   Content-based recommendations from movie metadata.
-   Semantic similarity using text embeddings.
-   User genre and theme preferences.
-   Valid user ratings and interaction history.

It aims to support similar-movie discovery, preference-based
recommendations, new users, and movies with limited interaction history.

### 5. Conversational movie discovery

A conversational interface is planned for requests such as:

-   "Recommend romance and science-fiction movies."
-   "Show me movies similar to Interstellar."
-   "What do viewers think about the soundtrack?"
-   "Recommend something emotional but not too slow."
-   "Compare these two movies."

The assistant should retrieve movie metadata, recommendation results,
and review evidence from the application rather than inventing scores or
audience opinions. Voice input is planned as an optional feature, with
text input as a fallback.

------------------------------------------------------------------------

## System architecture

The intended high-level data flow:

``` mermaid
flowchart TD
    A[Movie metadata, ratings and review datasets] --> B[Scala and Apache Spark]
    B --> C[Validated Bronze / Silver / Gold data]
    C --> D[Analytics and recommendation features]
    C --> E[NLP training and evaluation]

    E --> F[Sentiment and sarcasm models]
    E --> G[Aspect and theme models]
    E --> H[Embeddings and summarization]

    D --> I[Spark MLlib ALS]
    F --> J[Inference and scoring services]
    G --> J
    H --> J
    I --> K[Hybrid recommendation service]

    J --> L[FastAPI]
    K --> L
    M[(PostgreSQL / pgvector)] <--> L
    L <--> N[Next.js web application]
```

### Technology stack

  Layer                       Technologies
  --------------------------- --------------------------------------------------
  Programming                 Python, Scala
  Big Data                    Apache Spark, Spark SQL, RDDs, DataFrames, MLlib
  Deep learning and NLP       PyTorch, Hugging Face Transformers
  Classical ML                scikit-learn
  Semantic representations    Sentence Transformers
  Topic modelling             BERTopic / LDA, where appropriate
  Backend                     FastAPI, Pydantic, SQLAlchemy
  Database                    PostgreSQL, pgvector
  Frontend                    Next.js, React, TypeScript, Tailwind CSS
  Experiments                 Jupyter Notebook
  Build and version control   SBT, Git

Exact dependency versions are maintained in project configuration and
prerequisite documentation. Verify compatibility before installation.

## Data sources

Different datasets serve different tasks and must not be treated as
interchangeable.

  --------------------------------------------------------------------------------------------------
  Source                                                         Intended use        Important
                                                                                     limitation
  -------------------------------------------------------------- ------------------- ---------------
  [MovieLens 32M](https://grouplens.org/datasets/movielens/)     Ratings analytics,  Ratings and
                                                                 user-item           tags are not
                                                                 interactions, genre full textual
                                                                 analysis, Spark     movie reviews
                                                                 processing, ALS     

  [IMDb Large Movie Review Dataset                               English             Binary labels;
  mirror](https://huggingface.co/datasets/stanfordnlp/imdb)      positive/negative   not a
                                                                 sentiment benchmark three-class
                                                                                     dataset and not
                                                                                     automatically
                                                                                     linked to
                                                                                     MovieLens movie
                                                                                     IDs

  [TMDB API](https://developer.themoviedb.org/)                  Movie metadata,     Requires API
                                                                 genres, overviews,  access and
                                                                 posters, and        compliance with
                                                                 catalogue           current terms
                                                                 information         and attribution
                                                                                     requirements

  [TweetEval](https://github.com/cardiffnlp/tweeteval)           Research            Social-media
                                                                 experiments for     performance may
                                                                 social-media        not transfer
                                                                 sentiment, irony,   directly to
                                                                 and emoji-related   movie reviews
                                                                 tasks               

  [iSarcasmEval](https://aclanthology.org/2022.semeval-1.111/)   Sarcasm and irony   Check access,
                                                                 research            licensing,
                                                                 experiments         annotation
                                                                                     format, and
                                                                                     domain
                                                                                     suitability
  --------------------------------------------------------------------------------------------------

Human-annotated movie-domain data will also be needed to train and
evaluate three-class sentiment, aspect extraction, aspect sentiment, and
Hinglish-specific behaviour.

### Data integrity principles

-   Preserve raw datasets; write preprocessing outputs separately.
-   Keep source identifiers and application identifiers distinct.
-   Validate movie ID joins; quarantine ambiguous mappings rather than
    guessing.
-   Preserve IMDb identifiers as strings where leading zeros matter.
-   Respect dataset licenses, provenance, attribution, and usage
    restrictions.
-   Label synthetic examples and exclude them from real audience
    analytics and reported model performance.
-   Prevent duplicate and near-duplicate leakage across train,
    validation, and test splits.
-   Do not assume a dataset contains movie-linked review text unless its
    schema and identifiers confirm that relationship.

------------------------------------------------------------------------

## Repository structure

The repository is organized by responsibility. The exact tree may evolve
during implementation.

``` text
movie-review-recommendation-system/
├── ARCHITECTURE.md
├── AGENTS.md
├── IMPLEMENTATION_PLAN.md
├── IMPLEMENTATION_STATUS.md
├── README.md
├── data/
│   ├── raw/                 # Original datasets; do not modify
│   ├── bronze/              # Ingested source data
│   ├── silver/              # Validated and cleaned data
│   ├── gold/                # Analytics-ready data
│   ├── processed/
│   └── samples/             # Clearly labelled test samples only
├── notebooks/               # Reproducible academic experiments
├── ml/
│   ├── common/
│   ├── sentiment_tfidf/
│   ├── sentiment_transformer/
│   ├── multilingual_sentiment/
│   ├── informal_language/
│   ├── sarcasm/
│   ├── aspect_extraction/
│   ├── aspect_sentiment/
│   ├── themes/
│   ├── embeddings/
│   ├── summarization/
│   └── fake_review_risk/
├── scala/
│   └── src/
│       ├── main/scala/
│       └── test/scala/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── database/
│   └── tests/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   └── lib/
├── database/migrations/
├── models/                  # Local model artifacts; not necessarily committed
├── configs/
├── scripts/
└── tests/
```

Large datasets, model checkpoints, secrets, virtual environments,
caches, and generated build outputs should not be committed to GitHub.

## Local development environment

The target is a local-first application suitable for an academic
demonstration.

  ---------------------------------------------------------------------
  Service                            Local address
  ---------------------------------- ----------------------------------
  Web application                    http://localhost:3000

  FastAPI backend                    http://localhost:8000

  API documentation                  http://localhost:8000/docs

  PostgreSQL                         localhost:5432

  JupyterLab                         http://localhost:8888

  Spark UI                           http://localhost:4040 (while a
                                     Spark application is running)
  ---------------------------------------------------------------------

### Development hardware

The development environment is designed around:

-   CPU: Intel Core 7 240H
-   GPU: NVIDIA GeForce RTX 5050 Laptop GPU
-   GPU memory: 8 GB
-   System RAM: 16 GB
-   Operating system: Windows

Training configurations must be selected based on actual available
memory and validated CUDA support. Train one substantial Transformer at
a time, use appropriate mixed precision and gradient accumulation where
supported, and save checkpoints so interrupted experiments can resume.

The core application should not require paid cloud GPU services or paid
inference APIs.

### Setup

The exact installation sequence and compatible versions are documented
in `PREREQUISITES.md`.

From the repository root, after Python 3.11 is installed:

``` powershell
# Verify the intended Python version
py -3.11 --version

# Create a project virtual environment if it does not exist
py -3.11 -m venv .venv

# Activate in PowerShell
.\.venv\Scripts\Activate.ps1

# Verify Python and pip
python --version
python -m pip --version
```

Install dependencies only after the project dependency manifest has been
created and validated:

``` powershell
python -m pip install -r requirements.txt
```

### GPU verification

After installing a compatible PyTorch build:

``` powershell
nvidia-smi
```

``` python
import torch

print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print("VRAM (GB):", round(
        torch.cuda.get_device_properties(0).total_memory / 1024**3, 2
    ))
```

A working NVIDIA driver alone does not guarantee that the installed
PyTorch build supports the GPU. Verify CUDA availability from PyTorch
itself.

### Running the application

Startup commands will be maintained in project scripts as services are
implemented. The intended workflow is:

1.  Start PostgreSQL.
2.  Apply database migrations.
3.  Start the FastAPI backend.
4.  Start the Next.js frontend.
5.  Load previously trained local model checkpoints.
6.  Run Spark jobs separately when required.

Model training should not run automatically when the website starts.
Evaluation should use saved, versioned model artifacts.

------------------------------------------------------------------------

## Model evaluation

Model quality must be demonstrated using held-out data and
task-appropriate metrics. No performance numbers are published here
until actual experiments have produced them.

  ---------------------------------------------------------------------
  Component                          Evaluation
  ---------------------------------- ----------------------------------
  Sentiment classification           Accuracy, macro-F1, per-class
                                     precision/recall, confusion
                                     matrix, calibration

  Sarcasm / irony                    Precision, recall, F1,
                                     false-positive analysis

  Aspect extraction                  Span precision, recall, F1

  Aspect sentiment                   Per-class F1 and aspect-level
                                     confusion analysis

  Theme classification               Micro/macro-F1 and per-theme
                                     performance

  Summarization                      Human evaluation and
                                     reference-based metrics where
                                     valid references exist

  Suspicious-review risk             Precision/recall on labelled data,
                                     false-positive analysis

  Recommendation                     Precision@K, Recall@K, NDCG@K,
                                     coverage, diversity, novelty

  Big Data pipeline                  Runtime, throughput, data
                                     reconciliation, resource usage
  ---------------------------------------------------------------------

Report results separately for English, Hindi, Romanized Hindi, and
Hinglish when sufficient labelled evaluation data exists. Social-media
benchmark results must not be presented as proof of movie-review-domain
performance.

## Academic syllabus alignment

### Big Data Analytics

  ---------------------------------------------------------------------
  Syllabus area                      Project implementation
  ---------------------------------- ----------------------------------
  Big Data characteristics and       MovieLens-scale data ingestion and
  ecosystem                          processing

  Hadoop and MapReduce concepts      Relevant data-processing
                                     demonstrations

  Scala functional programming       Collections, higher-order
                                     functions, immutability,
                                     functional transformations

  Scala OOP and concurrency          Modular Scala jobs and concurrency
                                     demonstrations

  Spark architecture                 Spark execution, jobs, stages, and
                                     local cluster concepts

  RDDs and DataFrames                Transformations, actions, joins,
                                     and aggregations

  Lazy evaluation and DAG            Execution-plan and DAG
                                     demonstrations

  Spark MLlib                        ALS collaborative filtering

  ML pipelines                       Reproducible processing and
                                     recommendation workflows
  ---------------------------------------------------------------------

### Text Analytics

  ---------------------------------------------------------------------
  Syllabus area                      Project implementation
  ---------------------------------- ----------------------------------
  Computational linguistics          Text normalization, language
                                     variation, morphology and context

  Word representation                Bag-of-Words, TF-IDF and
                                     embeddings

  N-grams and language models        Classical text features and
                                     Transformer representations

  Deep learning for NLP              Transformer fine-tuning

  BERT-based models                  Contextual sentiment and
                                     multilingual language
                                     understanding

  Topic modelling                    LDA / BERTopic experiments

  POS and NER                        Supporting NLP experiments where
                                     relevant

  Sentiment analysis                 Three-class review classification

  Summarization                      Evidence-grounded review summaries

  Evaluation and visualization       Metrics, error analysis, and model
                                     visualizations
  ---------------------------------------------------------------------

------------------------------------------------------------------------

## Responsible AI, privacy, and limitations

-   Models can misunderstand sarcasm, cultural expressions, slang, and
    code-mixed language. Predictions should expose uncertainty.
-   Sarcasm detection must not automatically reverse sentiment.
-   A suspicious-review score is a moderation signal, not proof that a
    person posted a fake review.
-   Audience scores require sufficient eligible review evidence.
-   Metadata-based estimates must be distinguished from review-derived
    scores.
-   Review text and user activity must be handled with appropriate
    privacy, consent, retention, and deletion controls.
-   Third-party datasets, APIs, posters, and metadata remain subject to
    their own licenses and terms.
-   The application is an informational movie-discovery tool, not an
    authoritative measure of artistic quality.

## Development roadmap

The implementation is organized into these phases:

-   [ ] Phase 0 --- Environment and project foundation
-   [ ] Phase 1 --- Dataset validation and movie ID mapping
-   [ ] Phase 2 --- Scala and Apache Spark BDA pipeline
-   [ ] Phase 3 --- TF-IDF and Transformer sentiment analysis
-   [ ] \[ \] Phase 4 --- Aspect-based sentiment analysis
-   [ ] Phase 5 --- Themes, embeddings, and review summarization
-   [ ] Phase 6 --- Suspicious-review risk analysis
-   [ ] Phase 7 --- Movie scoring and audience intelligence
-   [ ] Phase 8 --- ALS and hybrid recommendations
-   [ ] Phase 9 --- FastAPI, PostgreSQL, and pgvector
-   [ ] Phase 10 --- Next.js frontend
-   [ ] Phase 11 --- Conversational discovery and voice input
-   [ ] Phase 12 --- Full integration, testing, and optimization
-   [ ] Phase 13 --- Academic evaluation and final demonstration

Update this checklist only when the corresponding phase has met its
documented exit criteria.

## Project documentation

-   `ARCHITECTURE.md` --- system architecture and design decisions.
-   `AGENTS.md` --- development and coding-agent instructions.
-   `IMPLEMENTATION_PLAN.md` --- phase-by-phase implementation plan.
-   `DATASET_AUDIT.md` --- dataset schemas, availability, and quality
    findings.
-   `ENVIRONMENT_AUDIT.md` --- development environment findings.
-   `PREREQUISITES.md` --- installation and compatibility guide.
-   `IMPLEMENTATION_STATUS.md` / `PROGRESS.md` --- current
    implementation status and handover notes.

## Contributing

This is an academic project under active development. Contributions
should preserve data integrity and reproducibility.

Before submitting changes:

1.  Explain the problem or feature.
2.  Keep changes modular and focused.
3.  Add or update tests.
4.  Document dataset and model assumptions.
5.  Do not commit raw datasets, private data, credentials, or large
    model checkpoints.
6.  Report actual test results and known limitations.

## License and attribution

A repository license has not yet been specified. Until a `LICENSE` file
is added, do not assume that the project code is available for
unrestricted reuse.

Third-party datasets, models, APIs, metadata, and images retain their
respective licenses, attribution requirements, and terms of use. Check
those terms before redistribution or commercial use.

------------------------------------------------------------------------

**Built as an academic Big Data Analytics + Text Analytics project.**\
The goal is to make movie discovery more useful by combining scalable
data engineering with contextual, explainable, and evidence-grounded
language intelligence.
