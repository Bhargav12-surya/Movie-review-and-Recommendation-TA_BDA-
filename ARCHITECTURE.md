# Movie Review & Recommendation System

## Complete Technical Architecture, Data Strategy, Model Workflow and Implementation Blueprint

**Academic subjects:** Big Data Analytics (BDA) and Text Analytics (TA)\
**Project type:** Full-stack AI / NLP / Big Data application\
**Proposed title:** *A Big Data-Driven Movie Review Intelligence and
Personalized Recommendation System Using Apache Spark and
Transformer-Based NLP*\
**Document status:** Detailed implementation blueprint\
**Prepared:** 8 November 2026

------------------------------------------------------------------------

# 1. Executive Summary

This project is a movie discovery and review intelligence platform. It
combines a real movie catalogue, audience reviews, Big Data processing,
Transformer-based NLP, aspect-based sentiment analysis, review
summarization, fake-review risk analysis, personalized recommendations
and a conversational movie assistant.

The system is designed as a real application rather than a collection of
disconnected notebooks. The website, backend, database, NLP models and
Scala/Spark jobs must share consistent movie identifiers and data
contracts.

The application has three major user-facing capabilities:

1.  **Movie Review Intelligence**
    -   Classifies a newly submitted review as positive, negative or
        neutral.
    -   Extracts the aspects discussed in a review, such as acting,
        story, music, pacing and cinematography.
    -   Calculates a review-derived audience sentiment score for each
        movie.
    -   Produces separate aspect, theme and genre-reception insights.
    -   Generates an evidence-grounded summary of audience opinions.
    -   Assigns a suspicious-review risk score to help moderation.
2.  **Personalized Movie Recommendation**
    -   Learns a user's interests from ratings, reviews, watch history,
        watchlist and interactions.
    -   Uses collaborative filtering, content-based recommendation and a
        user-preference profile.
    -   Recommends movies based on genres, themes, story characteristics
        and similar users.
    -   Explains why a movie is recommended.
    -   Handles new users and new movies through cold-start strategies.
3.  **Conversational Movie Discovery**
    -   Accepts natural-language text queries.
    -   Supports voice-to-text input.
    -   Understands requests such as "recommend romantic science-fiction
        movies", "find movies like Interstellar" and "how is
        Interstellar?"
    -   Retrieves evidence from the movie catalogue and review
        analytics.
    -   Produces grounded answers and movie cards.

## 1.1 Core technical principle

Use each technology for the work it is best suited to:

-   **Scala + Apache Spark:** large-scale ingestion, cleaning, joins,
    aggregation, distributed feature preparation, MLlib ALS and
    streaming demonstrations.
-   **Python + PyTorch + Hugging Face:** model training, Transformer
    inference, aspect extraction, summarization, embeddings and
    evaluation.
-   **FastAPI:** backend APIs and orchestration.
-   **PostgreSQL:** transactional application data and analytical result
    storage.
-   **pgvector:** semantic movie and review retrieval.
-   **React / Next.js:** the consumer-facing website.
-   **TMDB API:** movie metadata and artwork, subject to its current
    terms and attribution requirements.

Do not force every Transformer model into Scala. The BDA implementation
is demonstrated through real Spark jobs; the TA implementation is
demonstrated through trained and evaluated NLP models.

## 1.2 What the project must not do

-   Do not present MovieLens ratings as textual reviews.
-   Do not claim that the Stanford IMDb sentiment benchmark contains
    reliable movie IDs for each review.
-   Do not invent audience scores for movies with no reviews.
-   Do not call a review fake merely because the model dislikes its
    sentiment.
-   Do not generate summaries without evidence from actual reviews.
-   Do not use scraped or redistributed copyrighted review content
    without checking the source's terms and obtaining permission where
    required.
-   Do not show a model's training accuracy as proof of real-world
    performance.
-   Do not make the frontend display hardcoded AI predictions while
    claiming that it is connected to trained models.

------------------------------------------------------------------------

# 2. Product Scope and Functional Requirements

## 2.1 Module A --- Movie Review Intelligence

### A1. Review submission

A signed-in user opens a movie page and submits a review. The system:

1.  Validates the text and movie identifier.
2.  Checks length, language and basic abuse constraints.
3.  Stores the original review.
4.  Calls the NLP inference service.
5.  Receives sentiment probabilities.
6.  Extracts aspects and aspect-level sentiment.
7.  Calculates a suspicious-review risk score.
8.  Saves the model outputs with model version information.
9.  Recalculates the movie's aggregate analytics.
10. Returns the prediction to the UI.

The user should see the review analysis shortly after submission. The
review itself should remain visible according to the product's
moderation policy; suspicious content may be held for review rather than
silently removed.

### A2. Three-class sentiment classification

The model output must contain:

-   Positive probability.
-   Negative probability.
-   Neutral probability.
-   Predicted class.
-   Model version.
-   Inference timestamp.
-   Optional calibrated confidence / uncertainty.

Example response:

``` json
{
  "label": "positive",
  "probabilities": {
    "positive": 0.78,
    "negative": 0.12,
    "neutral": 0.10
  },
  "model_version": "sentiment-distilbert-v1",
  "needs_review": false
}
```

The values above are illustrative. Actual probabilities must come from
the trained model.

### A3. Aspect-Based Sentiment Analysis

The model should identify the movie aspects discussed and the sentiment
attached to each aspect.

Initial aspect taxonomy:

  Aspect             Meaning
  ------------------ --------------------------------------------
  Acting             Performances and delivery
  Story              Plot and narrative
  Screenplay         Structure, writing and coherence
  Direction          Director's execution
  Characters         Character development and relationships
  Cinematography     Camera work and visual composition
  Visual effects     CGI and visual effects
  Editing            Cuts, transitions and pacing of scenes
  Pacing             How quickly or slowly the story moves
  Music              Songs and musical score
  Sound design       Sound effects, mixing and audio experience
  Dialogue           Dialogue quality
  Worldbuilding      Construction of fictional worlds
  Emotional impact   Emotional engagement
  Originality        Freshness of ideas
  Runtime            Perceived length and use of time

The taxonomy should be versioned. It is acceptable to add aspects after
reviewing actual training annotations.

### A4. Movie-level intelligence score

The score must be described as an **Audience Sentiment Score** or
**Audience Intelligence Score**, not an objective measurement of
artistic quality.

It should show:

-   Score from 0 to 100, only when enough valid review evidence exists.
-   Number of reviews included.
-   Positive / neutral / negative distribution.
-   Confidence or evidence-strength label.
-   Last updated time.
-   Score methodology link.

### A5. Genre, theme and category profile

Use three distinct concepts:

1.  **Genre:** movie metadata such as science fiction, drama, romance
    and thriller.
2.  **Theme:** concepts expressed in the story, such as time, sacrifice,
    family, survival and identity.
3.  **Cinematic craft / experience aspects:** soundtrack,
    cinematography, acting, pacing, visual effects and screenplay.

Do not mix metadata claims with sentiment claims. "Billion-dollar
blockbuster" is a box-office/commercial-performance fact, not a review
sentiment category. "Epic cinema" may be a curated descriptive label,
but it must be defined and supported by metadata or a clearly documented
classifier.

For themes, show both: - **Theme relevance / prevalence:** how strongly
the theme appears in the movie's synopsis, tags or review evidence. -
**Audience reception:** how positively or negatively reviewers discuss
that theme.

A theme can be highly relevant but receive mixed audience sentiment.
These two numbers must not be collapsed into one.

### A6. AI review summary

The summary must be generated from reviews associated with that movie.
The review page should display the summary above the individual reviews.

Suggested summary sections:

-   Overall audience impression.
-   Most appreciated elements.
-   Most criticized elements.
-   Commonly mentioned themes.
-   Differences between positive and negative reviewers.
-   Review count and date range.

Each summary should be tied to a review snapshot or version so that it
can be regenerated when new reviews arrive.

------------------------------------------------------------------------

## 2.2 Module B --- Personalized Recommendation

### B1. User preference profile

The system builds a profile using:

-   Explicit ratings.
-   Written reviews.
-   Watched movies.
-   Watchlist additions.
-   Likes / dislikes.
-   Search and click behaviour, if the user consents.
-   Genre interactions.
-   Theme interactions.
-   Aspect preferences.

Do not treat every click as a strong preference. Use different
interaction weights and allow users to edit or reset their preference
profile.

### B2. Recommendation types

Provide separate recommendation shelves:

-   Recommended for you.
-   Because you liked \[movie\].
-   Similar themes.
-   Similar genres.
-   Similar audience taste.
-   Hidden gems.
-   Popular in your preferred genres.
-   New releases matching your interests.

### B3. Hybrid recommendation

Combine:

1.  Collaborative filtering using Spark MLlib ALS.
2.  Content-based similarity using movie metadata and embeddings.
3.  Explicit / inferred user preference matching.

The final combination weights must be tuned on validation data. Do not
choose weights solely because they produce attractive demo results.

### B4. Cold-start support

For a new user: - Ask the user to select a few favourite genres or
movies. - Use content-based recommendations until interaction history
exists. - Update the profile as the user interacts.

For a new movie: - Use synopsis, genres, cast, keywords and other
licensed metadata to find similar movies. - Do not invent an audience
review score. - Display "Not enough audience reviews yet" when there is
insufficient review evidence. - Optionally show a clearly labelled
"Predicted match for your taste" score. This is a personalized
prediction, not an audience score.

------------------------------------------------------------------------

## 2.3 Module C --- Conversational Movie Discovery

The assistant must support:

-   Genre combinations: "romance and science fiction".
-   Similarity queries: "movies like Interstellar".
-   Preference-based requests: "something emotional but not too slow".
-   Movie questions: "how is Interstellar?"
-   Aspect questions: "what do viewers say about the soundtrack?"
-   Comparison: "compare Arrival and Interstellar".
-   Follow-up context: "show me something shorter".
-   Voice input through speech recognition.

The chatbot must use the same movie catalogue, recommendation engine and
review analytics as the normal website. It must not maintain a separate
hardcoded movie list.

------------------------------------------------------------------------

# 3. System Architecture

## 3.1 High-level architecture

``` mermaid
flowchart TB
    U[User / Browser] --> FE[React / Next.js Frontend]
    FE --> API[FastAPI Backend]
    API --> AUTH[Authentication and Authorization]
    API --> DB[(PostgreSQL)]
    API --> NLP[NLP Inference Service]
    API --> REC[Recommendation Service]
    API --> CHAT[Conversational Retrieval Service]
    API --> TMDB[TMDB Metadata Adapter]

    NLP --> SENT[Sentiment Transformer]
    NLP --> ABSA[Aspect Extraction and Sentiment]
    NLP --> FAKE[Review Risk Model]
    NLP --> SUM[Evidence-grounded Summarizer]
    NLP --> EMB[Sentence Embedding Model]

    REC --> ALS[Spark MLlib ALS Model]
    REC --> CONTENT[Content Similarity]
    REC --> PROFILE[User Preference Profile]

    CHAT --> RETR[Hybrid Retrieval]
    RETR --> DB
    RETR --> EMB

    subgraph BDA[Scala + Apache Spark Data Platform]
      ING[Data Ingestion]
      CLEAN[Bronze / Silver Cleaning]
      FEAT[Feature Engineering]
      AGG[Movie and User Aggregations]
      ALSJOB[ALS Training]
      STREAM[Structured Streaming / Micro-batches]
      ING --> CLEAN --> FEAT --> AGG
      FEAT --> ALSJOB
      CLEAN --> STREAM
    end

    ML[(Parquet / Object Storage / Model Registry)]
    ING --> ML
    AGG --> DB
    ALSJOB --> ML
    SENT --> ML
    ABSA --> ML
    FAKE --> ML
    SUM --> ML
```

## 3.2 Architecture layers

  -----------------------------------------------------------------------
  Layer                   Main responsibility     Primary technology
  ----------------------- ----------------------- -----------------------
  Presentation            Movie discovery,        React / Next.js
                          reviews, profile and    
                          chatbot                 

  API                     Authentication,         FastAPI
                          validation and          
                          orchestration           

  Application database    Users, movies, reviews, PostgreSQL
                          interactions and scores 

  Vector retrieval        Similar movies, themes  pgvector
                          and review evidence     

  NLP inference           Sentiment, aspects,     PyTorch / Transformers
                          embeddings and          
                          summaries               

  Recommendation          ALS, content similarity Spark MLlib + Python
                          and preference ranking  

  Big Data processing     Ingestion, cleaning,    Scala + Spark
                          aggregation and         
                          streaming               

  Data lake               Raw and curated         Parquet on local disk
                          datasets                or object storage

  External metadata       Movie details and       TMDB API
                          artwork                 

  Monitoring              Logs, metrics and model Python logging /
                          health                  Prometheus optional
  -----------------------------------------------------------------------

## 3.3 Batch versus real-time processing

Use two paths.

### Synchronous user request path

A single newly submitted review should not need a full Spark cluster job
to obtain a sentiment prediction.

``` text
Browser
  -> FastAPI
  -> Validate and store review
  -> NLP inference service
  -> Sentiment + aspect + risk predictions
  -> Save predictions
  -> Update or enqueue movie aggregate refresh
  -> Return analysis to browser
```

This is the user-facing low-latency path.

### Batch / micro-batch analytics path

Spark handles larger-scale processing:

``` text
Review event table / event files
  -> Spark ingestion
  -> Cleaning and deduplication
  -> Feature and sentiment aggregation
  -> Movie-level analytics
  -> Parquet / PostgreSQL analytical tables
  -> Frontend reads refreshed results
```

A student prototype can use scheduled Spark jobs or a file-streaming
demonstration. Kafka is optional and should be introduced only if there
is a clear need for a message broker.

------------------------------------------------------------------------

# 4. Dataset Strategy and Where to Get the Data

This is one of the most important design decisions. There is no single
dataset that supplies all required information.

Use multiple datasets for different tasks and document their licenses
and limitations.

## 4.1 Dataset matrix

  -------------------------------------------------------------------------
  Source            What it provides    Use in this       Important
                                        project           limitation
  ----------------- ------------------- ----------------- -----------------
  MovieLens 32M     Ratings, tags,      Recommendation,   It is not a large
                    movie metadata, ID  Spark, user       text-review
                    links               profiles          corpus

  Stanford Large    50,000 labelled     Binary sentiment  No neutral class;
  Movie Review      positive/negative   benchmark and     not a dependable
  Dataset           reviews plus 50,000 baseline          movie-ID-linked
                    unlabelled reviews                    review store

  TMDB API          Movie metadata,     Movie catalogue   Follow current
                    genres, credits,    and artwork       API terms,
                    keywords, images                      attribution and
                    and supported API                     rate limits
                    resources                             

  First-party       Reviews submitted   Movie-linked      Requires users,
  application       by users of this    analytics,        consent and
  reviews           project             summaries and     moderation
                                        scoring           

  Manually          Review text with    Domain-specific   Annotation effort
  annotated review  sentiment, aspect   evaluation and    is required
  sample            and theme labels    fine-tuning       

  Optional ABSA     Aspect and          Method            Domain and
  datasets          sentiment examples  development /     language may
                                        transfer learning differ
  -------------------------------------------------------------------------

## 4.2 MovieLens 32M --- primary BDA and recommendation dataset

Official source:

-   https://grouplens.org/datasets/movielens/
-   Dataset README:
    https://files.grouplens.org/datasets/movielens/ml-32m-README.html

The stable 32M release contains approximately: - 32,000,204 ratings. -
2,000,072 tag applications. - 87,585 movies. - 200,948 users.

Files:

  --------------------------------------------------------------------------------------
  File                    Columns / contents                     Project use
  ----------------------- -------------------------------------- -----------------------
  `ratings.csv`           `userId, movieId, rating, timestamp`   ALS training and user
                                                                 taste analysis

  `movies.csv`            `movieId, title, genres`               Movie catalogue seed
                                                                 and content features

  `tags.csv`              `userId, movieId, tag, timestamp`      Theme / keyword signals
                                                                 and user preferences

  `links.csv`             MovieLens ID, IMDb ID, TMDB ID         Cross-source movie ID
                                                                 mapping
  --------------------------------------------------------------------------------------

### Download procedure

1.  Open the official GroupLens MovieLens page.
2.  Select the stable MovieLens 32M release.
3.  Download the ZIP file.
4.  Extract it into `data/raw/movielens/ml-32m/`.
5.  Keep the original README and checksum information.
6.  Verify the extracted files and record the dataset release date.
7.  Never edit the raw CSV files directly.

### Important use limitation

Read the README and usage terms before redistribution. GroupLens
generally does not permit public redistribution of its datasets. In your
Git repository, provide download instructions and expected folder names
rather than committing the complete dataset.

## 4.3 Stanford Large Movie Review Dataset

Official source:

-   https://ai.stanford.edu/\~amaas/data/sentiment/
-   Hugging Face dataset integration:
    https://huggingface.co/datasets/stanfordnlp/imdb

It contains: - 25,000 labelled training reviews. - 25,000 labelled test
reviews. - 50,000 additional unlabelled reviews. - Positive and negative
labels.

### How to use it

1.  Download the official archive or use the official Hugging Face
    dataset integration.
2.  Preserve the official train/test split for benchmark comparison.
3.  Train a binary sentiment baseline.
4.  Fine-tune a Transformer model.
5.  Report binary results separately from the final three-class model.

### What not to do

-   Do not invent a neutral class from this dataset.
-   Do not assume that each review can be joined to a MovieLens or TMDB
    movie ID.
-   Do not use its test split for training.
-   Do not claim that this dataset alone powers the per-movie review
    summaries.

For the final three-class classifier, collect or license suitable
neutral-labelled examples and annotate a movie-review-domain validation
set. If ratings are used as weak labels, clearly document the thresholds
and label noise.

## 4.4 TMDB API --- movie catalogue and artwork

Official documentation:

-   Getting started:
    https://developer.themoviedb.org/docs/getting-started
-   API reference:
    https://developer.themoviedb.org/reference/intro/getting-started
-   FAQ / attribution information:
    https://developer.themoviedb.org/docs/faq

### What to retrieve

Where available through the current API and permitted by its terms:

-   Movie title and original title.
-   Overview / synopsis.
-   Release date.
-   Genres.
-   Runtime.
-   Poster and backdrop paths.
-   Cast and crew.
-   Keywords.
-   Language and production information.
-   Supported review or other movie resources.

### Setup procedure

1.  Create a TMDB account.
2.  Open account settings.
3.  Find the API section.
4.  Request API credentials.
5.  Read and accept the current terms.
6.  Store the credential in an environment variable such as
    `TMDB_API_KEY`.
7.  Make requests from the backend, not from frontend JavaScript.
8.  Cache permitted responses and handle rate limits.
9.  Store the external TMDB ID against the project's internal movie ID.

### Attribution

TMDB's current FAQ states that free API use is for non-commercial
purposes with attribution. The application must use the required TMDB
logo and prominently display the required notice in its About/Credits
area:

> This product uses the TMDB API but is not endorsed or certified by
> TMDB.

Check the current TMDB terms before public deployment or commercial use.
Do not assume that an academic prototype license automatically covers a
commercial launch.

### Movie review data warning

Do not assume that the metadata API provides enough audience review text
for every movie. Review availability, pagination and terms must be
verified against the current official endpoint reference. Use your own
application's submitted reviews and appropriately licensed review
datasets as the reliable foundation for review intelligence.

## 4.5 IMDb data --- caution

IMDb provides non-commercial datasets under specific restrictions. Its
current help page says limited non-commercial use is allowed under its
terms and that the data must not be republished or repurposed to create
an online/offline movie database, subject to the stated conditions.

Official information: -
https://help.imdb.com/article/imdb/general-information/can-i-use-imdb-data-in-my-software/G5JTRESSHJBBHTGX -
https://datasets.imdbws.com/

Do not scrape IMDb pages. Do not assume that downloadable IMDb data may
be incorporated into a public movie catalogue. For this project, use
TMDB as the primary metadata provider unless you have reviewed and
confirmed the rights for another source.

## 4.6 Optional aspect dataset

If multilingual or Indian-language review analysis is a future goal,
investigate MADTRAS, a Tamil movie-review ABSA dataset:

-   Mendeley Data: https://data.mendeley.com/datasets/p59cfx4vx6/3

It is an optional research dataset, not a replacement for an English
movie-review corpus. Verify the exact version, license, annotation
scheme and language before use.

## 4.7 Build your own movie-linked review dataset

This is necessary for real movie-level analytics.

Create a first-party review submission workflow in your website. Each
record must have:

-   Internal `movie_id`.
-   `user_id` or anonymous reviewer token, according to account policy.
-   Review text.
-   Optional user star rating.
-   Language.
-   Created timestamp.
-   Moderation state.
-   Consent / terms version.
-   Model predictions stored separately.

For academic model training, create an annotation set from permitted
review text. A practical starting target is 1,000--3,000 carefully
annotated examples for a small domain-specific validation/fine-tuning
set, then expand if time permits. The number is a project planning
target, not a claim that this quantity guarantees a strong model.

### Annotation guidelines

Create a written guideline before annotation:

-   Positive: the review expresses an overall favourable opinion.
-   Negative: the review expresses an overall unfavourable opinion.
-   Neutral: factual, mixed, unclear or non-evaluative review, according
    to a consistent policy.
-   Aspect labels: assign only when the review actually discusses the
    aspect.
-   Aspect sentiment: positive, negative, neutral or mixed.
-   Spam labels: use only when there is evidence or a defined annotation
    rule.

Have two annotators label an overlapping subset and calculate agreement.
Resolve disagreements before finalizing the labels.

## 4.8 Dataset folder structure

``` text
data/
├── raw/
│   ├── movielens/
│   │   └── ml-32m/
│   ├── acl_imdb/
│   ├── tmdb_snapshots/
│   ├── licensed_reviews/
│   └── manual_annotations/
├── bronze/
├── silver/
├── gold/
├── processed/
│   ├── sentiment/
│   ├── absa/
│   ├── themes/
│   └── recommendation/
├── exports/
└── dataset_cards/
```

### Data governance rules

-   Keep original files unchanged.
-   Record source URL, retrieval date, version, license and checksum.
-   Keep a data dictionary for every processed table.
-   Do not commit API secrets, private user data or restricted datasets.
-   Use synthetic demo records only when clearly labelled as synthetic.
-   Keep a deletion mechanism for user-submitted content.
-   Do not train on user reviews unless the application's consent and
    privacy policy permit it.

------------------------------------------------------------------------

# 5. Movie Identity and Cross-Dataset Mapping

The system needs one canonical internal movie identifier.

## 5.1 Canonical ID design

Use an internal `movie_id` as the primary key. Store external
identifiers separately:

-   `tmdb_id`
-   `imdb_id`
-   `movielens_id`

Do not use a TMDB ID as the only primary key because some datasets may
not have one.

## 5.2 Mapping workflow

1.  Load MovieLens `links.csv`.
2.  Create a mapping table.
3.  Fetch or import TMDB metadata using `tmdb_id`.
4.  Preserve the source ID and source name.
5.  Check duplicate mappings.
6.  Reject conflicting IDs for manual review.
7.  Use fuzzy title/year matching only as a candidate-generation aid.
8.  Never automatically merge two movies based only on a similar title.

## 5.3 Mapping table

``` sql
CREATE TABLE external_movie_ids (
    id BIGSERIAL PRIMARY KEY,
    movie_id BIGINT NOT NULL,
    source VARCHAR(40) NOT NULL,
    external_id VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, external_id)
);
```

## 5.4 Why mapping quality matters

A wrong movie join can: - Attribute one movie's reviews to another. -
Corrupt movie scores. - Train incorrect recommendations. - Generate
false summaries. - Make the chatbot answer about the wrong movie.

Create a mapping-quality report and manually inspect uncertain matches.

------------------------------------------------------------------------

# 6. Data Engineering Architecture --- Bronze, Silver and Gold

Use a simple medallion-style data architecture.

## 6.1 Bronze layer --- raw source data

Purpose: preserve source data as received.

Examples: - Raw MovieLens CSV files. - Raw TMDB JSON responses where
caching is permitted. - Raw first-party review events. - Original
annotation files.

Rules: - Do not overwrite raw files. - Add ingestion metadata. - Keep
source and retrieval timestamps. - Keep raw text only where permitted.

## 6.2 Silver layer --- cleaned and standardized data

Purpose: create consistent, validated records.

Tasks: - Normalize column names. - Convert timestamps to UTC. - Validate
movie IDs. - Remove exact duplicate events. - Standardize genres. -
Normalize language codes. - Validate rating ranges. - Detect missing or
malformed text. - Keep a rejection/quarantine table for invalid rows.

## 6.3 Gold layer --- analytical and application-ready data

Examples: - `gold_movie_features` - `gold_user_movie_interactions` -
`gold_movie_sentiment_daily` - `gold_movie_aspect_scores` -
`gold_user_preferences` - `gold_recommendation_candidates` -
`gold_theme_movie_profiles`

Gold tables are what the backend reads for fast display and
recommendation.

## 6.4 Suggested storage formats

-   Raw source files: original CSV / JSON / text.
-   Spark curated datasets: Parquet.
-   Application records and current analytics: PostgreSQL.
-   Model weights: versioned model directory or model registry.
-   Vector embeddings: pgvector initially; a separate vector database is
    optional at larger scale.

For a local academic prototype, a local `data/` directory plus
PostgreSQL is sufficient. Cloud object storage is not required.

------------------------------------------------------------------------

# 7. Database Design

Use PostgreSQL for transactional records and current analytical
summaries. Keep large training files in Parquet rather than inserting
every raw training example into transactional tables.

## 7.1 Main entities

``` mermaid
erDiagram
    USERS ||--o{ REVIEWS : writes
    USERS ||--o{ RATINGS : gives
    USERS ||--o{ USER_INTERACTIONS : performs
    MOVIES ||--o{ REVIEWS : receives
    MOVIES ||--o{ RATINGS : receives
    MOVIES ||--o{ MOVIE_GENRES : has
    GENRES ||--o{ MOVIE_GENRES : categorizes
    REVIEWS ||--o{ REVIEW_PREDICTIONS : analyzed_by
    REVIEWS ||--o{ REVIEW_ASPECTS : contains
    MOVIES ||--o{ MOVIE_SCORE_SNAPSHOTS : summarized_as
    MOVIES ||--o{ MOVIE_THEME_SCORES : has
    USERS ||--o{ USER_PREFERENCES : develops
```

## 7.2 Suggested tables

### `users`

-   `user_id`
-   `email` or authentication subject
-   `display_name`
-   `created_at`
-   `is_active`
-   privacy / consent fields where needed

Never store plaintext passwords. Prefer a trusted authentication
provider or a secure password-hashing implementation.

### `movies`

-   `movie_id`
-   `title`
-   `original_title`
-   `overview`
-   `release_date`
-   `runtime_minutes`
-   `poster_path`
-   `backdrop_path`
-   `original_language`
-   `metadata_source`
-   `metadata_updated_at`

### `external_movie_ids`

-   `movie_id`
-   `source`
-   `external_id`

### `genres`

-   `genre_id`
-   `name`

### `movie_genres`

-   `movie_id`
-   `genre_id`

### `reviews`

-   `review_id`
-   `movie_id`
-   `user_id` (nullable only if anonymous submissions are allowed)
-   `review_text`
-   `language_code`
-   `user_rating` (nullable)
-   `created_at`
-   `updated_at`
-   `moderation_status`
-   `consent_version`
-   `is_deleted`

### `review_predictions`

-   `prediction_id`
-   `review_id`
-   `model_version`
-   `positive_probability`
-   `negative_probability`
-   `neutral_probability`
-   `predicted_label`
-   `uncertainty_score`
-   `predicted_at`

Keep model predictions separate from the review so that a new model can
reprocess a review without destroying the original text.

### `review_aspects`

-   `id`
-   `review_id`
-   `aspect_name`
-   `aspect_sentiment`
-   `confidence`
-   `evidence_span_start`
-   `evidence_span_end`
-   `model_version`

### `review_risk_predictions`

-   `id`
-   `review_id`
-   `risk_score`
-   `risk_band`
-   `signals_json`
-   `model_version`
-   `created_at`
-   `moderation_decision`

### `movie_score_snapshots`

-   `id`
-   `movie_id`
-   `score_type`
-   `score_value`
-   `valid_review_count`
-   `effective_sample_size`
-   `confidence_label`
-   `method_version`
-   `calculated_at`

### `movie_aspect_scores`

-   `movie_id`
-   `aspect_name`
-   `score_value`
-   `evidence_count`
-   `calculated_at`

### `movie_theme_scores`

-   `movie_id`
-   `theme_name`
-   `relevance_score`
-   `audience_sentiment_score`
-   `evidence_count`
-   `model_version`
-   `calculated_at`

### `movie_summaries`

-   `id`
-   `movie_id`
-   `summary_text`
-   `summary_type`
-   `review_snapshot_id`
-   `review_count`
-   `period_start`
-   `period_end`
-   `model_version`
-   `created_at`

### `ratings`

-   `user_id`
-   `movie_id`
-   `rating`
-   `created_at`
-   `source`

### `user_interactions`

-   `id`
-   `user_id`
-   `movie_id`
-   `interaction_type`
-   `event_timestamp`
-   `session_id` (optional)
-   `metadata_json`

### `user_preferences`

-   `user_id`
-   `preference_type`
-   `preference_value`
-   `preference_strength`
-   `updated_at`
-   `source`

### `recommendation_events`

-   `id`
-   `user_id`
-   `movie_id`
-   `rank`
-   `score`
-   `reason_code`
-   `model_version`
-   `created_at`

### `model_registry`

-   `model_name`
-   `model_version`
-   `artifact_path`
-   `training_dataset_version`
-   `metrics_json`
-   `created_at`
-   `status`

## 7.3 Database indexes

At minimum:

-   `reviews(movie_id, created_at DESC)`
-   `reviews(user_id, created_at DESC)`
-   `ratings(user_id, movie_id)`
-   `user_interactions(user_id, event_timestamp DESC)`
-   `movie_score_snapshots(movie_id, calculated_at DESC)`
-   `review_predictions(review_id, model_version)`
-   unique indexes for external IDs.

Add indexes based on actual query plans. Do not index every column.

## 7.4 Example movie score query

The backend should read the latest published score snapshot rather than
recompute all review sentiment for every page load.

``` sql
SELECT movie_id, score_value, valid_review_count,
       confidence_label, calculated_at
FROM movie_score_snapshots
WHERE movie_id = :movie_id
  AND score_type = 'audience_sentiment'
ORDER BY calculated_at DESC
LIMIT 1;
```

------------------------------------------------------------------------

# 8. Big Data Analytics Implementation --- Scala and Apache Spark

This section is the main BDA implementation.

## 8.1 What must be implemented in Scala

Create real Scala Spark jobs for:

1.  Data ingestion.
2.  RDD demonstrations.
3.  DataFrame cleaning and transformations.
4.  MovieLens joins and feature preparation.
5.  Movie-level aggregations.
6.  User preference aggregations.
7.  ALS recommendation training.
8.  Structured Streaming / micro-batch demonstration.
9.  Output writing to Parquet and, where appropriate, PostgreSQL.

Python notebooks may be used for deep-learning work, but the Scala code
must perform meaningful data processing.

## 8.2 Spark environment and version compatibility

Check the current Apache Spark documentation before installation:

-   https://spark.apache.org/docs/latest/

The documentation currently identifies supported Java, Scala and Python
versions for its release. Spark 4.x uses Scala 2.13; a Scala application
must use the same Scala binary version against which Spark was compiled.

Do not mix: - Spark 4.x with an arbitrary Scala 2.12 build. -
Incompatible Java versions. - Different Spark versions across local
notebooks and packaged Scala jobs.

Pin the versions in the README and build files. For a beginner-friendly
local setup, use a Spark release and Scala build that are officially
compatible with the installed JDK.

## 8.3 Spark execution model

Explain and demonstrate:

-   Driver.
-   Executors.
-   Cluster manager.
-   Jobs.
-   Stages.
-   Tasks.
-   Partitions.
-   Transformations.
-   Actions.
-   DAG.
-   Lazy evaluation.
-   Shuffle.
-   Cache / persist.
-   Checkpointing.

Use Spark UI to show the execution plan and stages during evaluation.

## 8.4 RDD implementation

Create a small RDD exercise using the movie review text dataset or
MovieLens tags.

Demonstrate: - `map` - `flatMap` - `filter` - `distinct` -
`reduceByKey` - `groupByKey` for teaching comparison, not as the default
production aggregation - `sortBy` - `count` - `collect` only for small
samples - `saveAsTextFile`

Example task: - Tokenize MovieLens tags. - Count tag occurrences. - Find
the most frequent tags. - Compare `reduceByKey` with `groupByKey`.

The purpose is to show the RDD concepts in the syllabus. Use DataFrames
for most production transformations because they offer higher-level
optimization.

## 8.5 DataFrame implementation

Recommended job sequence:

### Job 1 --- `01_ingest_movielens.scala`

-   Read ratings, movies, tags and links CSV files.
-   Set header and schema options.
-   Use explicit schemas where practical.
-   Validate nulls and invalid ranges.
-   Write Bronze Parquet tables.

### Job 2 --- `02_clean_and_standardize.scala`

-   Normalize column names.
-   Parse timestamps.
-   Validate IDs.
-   Standardize genre arrays.
-   Remove exact duplicate records.
-   Write Silver tables.

### Job 3 --- `03_join_movie_metadata.scala`

-   Join ratings to movies by `movieId`.
-   Join tags to movies by `movieId`.
-   Join external IDs using `links.csv`.
-   Join TMDB metadata only when the external ID mapping is validated.
-   Write curated movie and interaction tables.

### Job 4 --- `04_movie_analytics.scala`

Calculate: - Number of ratings per movie. - Mean and median rating. -
Rating distribution. - Number of unique raters. - Tag counts. -
Genre-level aggregates. - Time-based activity.

These are rating/tag analytics. Do not label them as review sentiment
unless the underlying input actually contains review sentiment
predictions.

### Job 5 --- `05_user_profiles.scala`

Calculate: - User rating count. - Average rating. - Preferred genres. -
Genre rating tendencies. - Tag-derived interests. - Recent activity.

Use a documented weighting policy. Keep explicit user ratings distinct
from implicit clicks.

### Job 6 --- `06_mllib_als.scala`

Train Spark MLlib ALS using the ratings DataFrame.

Input columns: - user integer ID. - item integer ID. - rating
float/double.

Important: - Spark ALS expects numeric user and item identifiers in its
model schema. - Keep a reversible mapping between internal IDs and
original IDs. - Use a temporal or carefully designed
train/validation/test split. - Set `coldStartStrategy` to avoid NaN
predictions during evaluation. - Tune rank, regularization, iterations
and other parameters. - Evaluate ranking quality, not just rating RMSE.

### Job 7 --- `07_review_analytics.scala`

Read review records and model prediction tables from Parquet or
PostgreSQL exports.

Calculate: - Sentiment distribution per movie. - Aspect-level counts. -
Aspect-level sentiment scores. - Theme prevalence. - Time-windowed
sentiment changes. - Evidence counts. - Score snapshots.

Do not train the Transformer inside this Spark job. Read its prediction
outputs.

### Job 8 --- `08_streaming_reviews.scala`

Demonstrate Spark Structured Streaming using a file stream or another
supported source.

-   Watch a directory for new review event files.
-   Apply schema validation.
-   Deduplicate by stable event/review ID.
-   Aggregate micro-batches.
-   Write to an idempotent sink.
-   Configure checkpoint storage.
-   Show a new review affecting a movie's aggregate.

A local file stream is enough for the course demonstration. Kafka is an
optional extension.

## 8.6 Transformations and actions to demonstrate

  Concept                    Example in project
  -------------------------- -------------------------------------------------
  `map`                      Convert source records to normalized structures
  `filter`                   Exclude invalid ratings
  `flatMap`                  Split tags into tokens
  `reduceByKey`              Aggregate tag counts
  `groupBy` / `groupByKey`   Group small demonstration data
  `select`                   Select required columns
  `withColumn`               Add derived features
  `join`                     Connect ratings and movie metadata
  `groupBy().agg()`          Movie-level metrics
  `cache`                    Reuse expensive cleaned DataFrame
  `count`, `show`, `write`   Actions that trigger execution

## 8.7 DAG and lazy evaluation demonstration

In your evaluation: 1. Build a DataFrame transformation chain. 2.
Explain that transformations are lazy. 3. Trigger an action such as
`count()` or `write`. 4. Open Spark UI. 5. Show the job, stages, tasks
and shuffle. 6. Explain why an action causes execution. 7. Show the
effect of caching a repeatedly used DataFrame.

Do not use `collect()` on the complete MovieLens dataset. It moves all
selected records to the driver and may cause memory problems.

## 8.8 Structured Streaming design

For a course prototype:

``` text
New review JSON file
  -> Spark Structured Streaming
  -> Schema validation
  -> Event ID deduplication
  -> Windowed aggregation
  -> Parquet / PostgreSQL output
```

Use checkpointing and idempotent output logic. Do not claim end-to-end
exactly-once delivery unless the source and sink semantics actually
support it.

## 8.9 Spark output contracts

Recommended curated outputs:

``` text
data/gold/
├── movies/
├── user_movie_ratings/
├── user_genre_profiles/
├── movie_rating_aggregates/
├── movie_sentiment_aggregates/
├── movie_aspect_aggregates/
├── movie_theme_aggregates/
├── als_predictions/
└── recommendation_candidates/
```

Every output should include: - schema version; - job version; - source
snapshot; - generated timestamp; - row count / quality checks.

------------------------------------------------------------------------

# 9. Text Analytics and NLP Model Architecture

Use a model pipeline with independent components. This makes training,
testing and replacing each model easier.

## 9.1 NLP pipeline overview

``` mermaid
flowchart TD
    A[Raw Review] --> B[Validation and Language Detection]
    B --> C[Minimal Text Normalization]
    C --> D[Tokenizer]
    D --> E[Sentiment Transformer]
    D --> F[Aspect Extraction Model]
    F --> G[Aspect Sentiment Classifier]
    C --> H[Review Risk Features]
    H --> I[Spam / Anomaly Model]
    C --> J[Sentence Embedding Model]
    E --> K[Prediction Store]
    G --> K
    I --> K
    J --> L[Semantic Index]
    K --> M[Movie Analytics]
    L --> N[Retrieval and Summarization]
    M --> N
```

## 9.2 Model 1 --- traditional sentiment baseline

Before Transformer fine-tuning, implement:

1.  Text cleaning.
2.  Tokenization.
3.  Bag of Words.
4.  TF-IDF.
5.  Unigrams and bigrams.
6.  Logistic Regression.
7.  Linear SVM.

Why: - Demonstrates Unit 2 concepts. - Provides a baseline for
comparison. - Helps identify whether the Transformer adds value. - Is
fast to train and easy to explain.

Evaluate with: - Accuracy. - Precision. - Recall. - Macro-F1. -
Confusion matrix.

Use macro-F1 for a class-imbalanced three-class task.

## 9.3 Model 2 --- Transformer sentiment classifier

Recommended first model: - DistilBERT or another appropriately licensed,
documented pretrained encoder.

Optional comparison: - BERT-base. - RoBERTa-base. - A domain-specific
checkpoint, only after checking its license, training data and
suitability.

### Training procedure

1.  Create a versioned labelled dataset.
2.  Preserve train, validation and test partitions.
3.  Remove exact duplicates.
4.  Check near-duplicate leakage.
5.  Keep related reviews from leaking between splits when movie-level
    generalization is being evaluated.
6.  Tokenize using the selected model tokenizer.
7.  Fine-tune a sequence-classification head.
8.  Use class weighting or sampling only if justified.
9.  Evaluate after each epoch.
10. Save the best validation checkpoint.
11. Evaluate once on the held-out test set.
12. Save the model card and metrics.

### Three-class labels

Define one consistent policy: - `0 = negative` - `1 = neutral` -
`2 = positive`

Do not derive neutral labels by simply relabelling all ambiguous
examples without inspection.

### Important distinction

The Stanford IMDb Large Movie Review Dataset is binary. Use it for
binary benchmark experiments. For the final three-class model, add
neutral-labelled data from an appropriate licensed source and/or a
manually annotated movie-review dataset.

### Model outputs

The model should return all three class probabilities. Use a validation
set to calibrate probability estimates if they will be used in score
aggregation.

## 9.4 Model 3 --- Aspect extraction

Two practical approaches:

### Approach A: Token classification

Fine-tune a Transformer token-classification model with BIO labels.

Example:

``` text
The      O
acting   B-ACTING
was      O
excellent O
but      O
the      O
pacing   B-PACING
was      O
slow     O
```

A more complete annotation scheme may include `B-ASPECT` and `I-ASPECT`
labels for each aspect type.

### Approach B: Span / multi-label extraction

Use a model that predicts aspect categories present in the review, then
extract evidence spans separately.

For a course prototype, token classification is easy to demonstrate
against the syllabus.

## 9.5 Model 4 --- Aspect sentiment classification

After extracting an aspect span, classify its sentiment.

Example:

Review: "The acting was excellent, but the screenplay felt rushed."

Expected: - Acting: positive. - Screenplay: negative.

You can: - Train a separate aspect-sentiment classifier. - Or feed the
review and aspect span together to a sequence classifier.

The second approach is useful when the same sentence contains different
sentiments for different aspects.

## 9.6 Model 5 --- Theme extraction

Themes are not identical to genres.

Suggested themes: - Love and family. - Time and memory. - Survival. -
Sacrifice. - Identity. - Revenge. - Justice. - Coming of age. - Human
nature. - Technology and artificial intelligence. - Social inequality. -
War and peace. - Grief and loss. - Power and corruption. - Exploration
and discovery.

Use two levels:

### Controlled theme classifier

Create a curated taxonomy and annotate a sample. Train a multi-label
classifier to predict multiple themes for a movie synopsis or review.

### Exploratory topic modelling

Use LDA or BERTopic to discover patterns in review text.

Use BERTopic as an exploratory analysis tool. Topic clusters may change
with data, parameters and model versions; do not present every
discovered topic as a stable movie fact without review and curation.

### Recommended evidence sources

-   Synopsis: primary signal for story themes.
-   Movie tags / keywords: supporting metadata.
-   Reviews: audience discussion and reception.
-   Manual curation: quality control for the final displayed theme
    taxonomy.

## 9.7 Model 6 --- Review summarization

Use a hybrid approach:

1.  Retrieve valid reviews for one movie.
2.  Split them by sentiment and aspect.
3.  Remove exact duplicates and suspicious content according to
    moderation policy.
4.  Select representative evidence.
5.  Generate a concise summary.
6.  Check generated statements against source reviews.
7.  Store summary metadata and evidence references.

### Candidate model families

-   BART.
-   T5.
-   Other suitable sequence-to-sequence models with verified licenses.

### Summarization strategy

Do not concatenate thousands of reviews into one model input. Use
hierarchical summarization:

``` text
Reviews
  -> Deduplicate / filter
  -> Group by sentiment and aspect
  -> Summarize each group
  -> Combine group summaries
  -> Verify evidence
  -> Publish movie summary
```

The summary should not claim that "most viewers" think something unless
the counts support that claim.

### Summary metadata

Store: - model version; - review snapshot ID; - review count; - date
range; - generated timestamp; - evidence review IDs or evidence
references; - language; - moderation policy version.

### Evaluation

-   ROUGE.
-   BERTScore.
-   Human factuality review.
-   Coverage of key aspects.
-   Contradiction checks.
-   Unsupported-claim rate.

ROUGE alone does not prove that a summary is factually correct.

## 9.8 Model 7 --- Fake-review / suspicious-review risk

Treat this as a review-risk and moderation-support system, not a perfect
fake-review detector.

### Signal groups

**Text signals** - Exact duplicate text. - Near-duplicate text. -
Repeated templates. - Unnatural phrase reuse. - Review text that does
not discuss the movie.

**Behaviour signals** - Unusually high submission frequency. - Burst
activity. - Repetitive rating behaviour. - Repeated patterns across
movies. - Account age / history, only if the platform has legitimately
collected it.

**Network / group signals** - Coordinated timing patterns. - Shared text
templates. - Repeated reviewer groups, if sufficient data exists and
privacy rules permit it.

### Candidate methods

-   TF-IDF / embedding similarity for duplicates.
-   Supervised text classifier if labelled examples exist.
-   Isolation Forest or another anomaly detector for behavioural
    features.
-   Rule-based checks as a transparent first layer.

### Dataset limitations

Public fake-review datasets often concern business reviews rather than
movie reviews. They can help prototype methods but may not generalize to
film reviews. Use them as external research data only after checking
their terms and label definitions.

Synthetic spam examples can test the pipeline, but must not be presented
as real-world test performance.

### Output

Return: - risk score from 0 to 100; - risk band; - contributing
signals; - model version; - moderation status.

Never use positive/negative sentiment as a fake-review feature by
itself. A strongly negative review can be genuine.

## 9.9 Model 8 --- Sentence embeddings

Use a Sentence-BERT-compatible model to create embeddings for:

-   Movie synopsis.
-   Movie keywords.
-   Theme descriptions.
-   Review snippets.
-   User preference descriptions.

Store embeddings in pgvector initially.

Use embeddings for: - Similar movie search. - Similar review
retrieval. - Theme matching. - Conversational retrieval. - Content-based
recommendation.

------------------------------------------------------------------------

# 10. Movie Scoring Methodology

This section must be documented carefully because it affects user trust.

## 10.1 Individual review sentiment score

For a review with probabilities:

-   (P\_{pos}): positive probability.
-   (P\_{neg}): negative probability.
-   (P\_{neu}): neutral probability.

Define:

\[ S_i = 100 `\times `{=tex}(P\_{pos} + 0.5P\_{neu}) \]

This produces a score from 0 to 100: - Strong negative prediction
approaches 0. - Neutral prediction approaches 50. - Strong positive
prediction approaches 100.

This is a sentiment index, not a user star rating.

## 10.2 Review inclusion and weighting

Only include reviews that: - Pass basic validation. - Are not deleted. -
Meet the moderation policy. - Have valid model outputs. - Are not
duplicates according to the defined policy.

Use a transparent review weight. For example:

\[ w_i = q_i `\times `{=tex}h_i `\times `{=tex}r_i \]

Where: - (q_i) = review quality / eligibility factor. - (h_i) =
helpfulness factor, if reliable helpfulness data exists. - (r_i) =
recency factor.

Do not assign high weight simply because a model is very confident.
Calibrate probabilities and inspect uncertainty separately.

If helpfulness is unavailable, omit that term rather than invent it.

## 10.3 Raw movie score

\[ S\_{raw} = `\frac{\sum_i w_i S_i}{\sum_i w_i}`{=tex} \]

## 10.4 Confidence adjustment / shrinkage

A movie with a small number of reviews should not appear as equally
reliable as a movie with thousands of reviews.

Use:

\[ S\_{final} = `\frac{n_{eff}}{n_{eff}+k}`{=tex}S\_{raw} +
`\frac{k}{n_{eff}+k}`{=tex}S\_{prior} \]

Where: - (n\_{eff}) = effective review sample size. - (k) = smoothing
parameter estimated or tuned on validation data. - (S\_{prior}) =
baseline sentiment score from an appropriate training/reference
population.

A weighted effective sample size can be estimated as:

\[ n\_{eff} = `\frac{(\sum_i w_i)^2}{\sum_i w_i^2}`{=tex} \]

Do not choose (k) arbitrarily and present it as scientifically
established. Tune it using historical or held-out data and document the
method.

## 10.5 Score display policy

Suggested display rules: - No valid reviews: no audience score. - Very
few reviews: "Early audience signal" with low evidence. - More reviews:
show the score with evidence strength. - Large review sample: show a
more stable score and trend.

The exact thresholds must be selected after inspecting the dataset and
should be visible in the methodology documentation.

## 10.6 Aspect scores

For each aspect, aggregate sentiment only from reviews that actually
mention that aspect.

Example:

-   Acting: score from acting-related evidence.
-   Soundtrack: score from soundtrack-related evidence.
-   Pacing: score from pacing-related evidence.

Do not apply the whole-review sentiment to every aspect. A mixed review
may praise acting and criticize pacing.

## 10.7 Genre reception

Genres come from metadata. Genre reception should be derived only when
the system has sufficient genre-relevant evidence.

Possible methods: - Multi-label genre-related review classifier. -
Genre-specific aspect and theme evidence. - Review text that explicitly
discusses genre conventions.

If there is insufficient evidence, show the genre as metadata without a
reception score.

## 10.8 Theme relevance and sentiment

For every theme, calculate two independent measures:

1.  Relevance / prevalence score.
2.  Audience sentiment score based on review evidence that discusses the
    theme.

A theme can be important to the story while audience sentiment about it
is mixed.

## 10.9 Score transparency

Every displayed score should have: - Methodology version. - Review
count. - Evidence count. - Last updated time. - Model version. -
Explanation link.

The score should be described as an audience sentiment measure, not a
definitive measure of movie quality.

------------------------------------------------------------------------

# 11. Recommendation Engine

## 11.1 Inputs

### Explicit signals

-   User ratings.
-   Review sentiment and content.
-   Favourite movies.
-   Watchlist.
-   Favourite genres.
-   User-selected interests.

### Implicit signals

-   Watched movie.
-   Search result click.
-   Movie detail page view.
-   Time spent, if collected with consent.
-   Recommendation click.
-   Watchlist addition.

Keep explicit and implicit feedback separate. A click does not mean the
user liked the movie.

## 11.2 Model A --- collaborative filtering with ALS

Use MovieLens ratings as the initial training dataset.

Workflow:

1.  Read ratings with Spark.
2.  Validate user and movie IDs.
3.  Convert IDs to the required numeric types.
4.  Split interactions using a temporal or carefully designed evaluation
    strategy.
5.  Train ALS.
6.  Tune hyperparameters.
7.  Generate top-N candidate movies.
8.  Remove movies the user has already rated or watched, where
    appropriate.
9.  Save recommendations and model metadata.

Parameters to tune: - `rank` - `maxIter` - `regParam` -
`implicitPrefs` - `alpha` when using implicit preferences -
`coldStartStrategy`

Do not rely only on RMSE. Also evaluate top-K ranking quality.

## 11.3 Model B --- content-based recommendation

Create a movie feature representation from:

-   Genres.
-   Synopsis.
-   Keywords.
-   Cast / crew, where licensed and available.
-   Theme labels.
-   Embeddings.

Possible implementation:

1.  Normalize metadata.
2.  Encode genres as multi-hot features.
3.  Generate synopsis embeddings.
4.  Encode keywords.
5.  Combine features or retrieve using multiple similarity channels.
6.  Calculate cosine similarity.
7.  Return similar movies with reason codes.

## 11.4 Model C --- user preference profile

Build a preference vector from the user's interactions.

Example dimensions: - Science fiction. - Romance. - Drama. - Mystery. -
Family. - Time travel. - Survival. - Emotional storytelling. -
Soundtrack. - Complex narratives.

Use explicit ratings and review evidence more strongly than casual
clicks.

Allow a user to correct or reset the profile.

## 11.5 Hybrid ranking

An initial design:

\[ R(u,m) = `\alpha `{=tex}`\cdot `{=tex}ALS(u,m) +
`\beta `{=tex}`\cdot `{=tex}Content(u,m) +
`\gamma `{=tex}`\cdot `{=tex}Preference(u,m) \]

Before combining: - Normalize or calibrate component scores. - Tune
weights on validation data. - Apply eligibility filters. - Add diversity
constraints. - Avoid repeatedly recommending near-identical movies.

## 11.6 Recommendation explanations

Generate explanations from actual features:

-   "Because you liked Interstellar."
-   "Matches your interest in science fiction and family drama."
-   "Similar to movies you rated highly."
-   "Frequently selected by users with similar rating patterns."

Do not invent social proof or user similarity claims.

## 11.7 Evaluation

Use: - Precision@K. - Recall@K. - NDCG@K. - MAP@K where useful. -
Coverage. - Diversity. - Novelty. - Popularity bias. - Cold-start
performance.

For temporal evaluation, train on earlier interactions and test on later
interactions. This better reflects the real recommendation scenario than
randomly mixing future interactions into training.

------------------------------------------------------------------------

# 12. Conversational AI and Retrieval Architecture

## 12.1 Core design

Use a retrieval-first assistant rather than allowing a language model to
invent movie facts.

``` mermaid
flowchart TD
    Q[Text or Voice Query] --> STT[Speech-to-Text if voice]
    STT --> INTENT[Intent and Entity Extraction]
    INTENT --> ROUTER[Query Router]
    ROUTER --> CAT[Catalogue Search]
    ROUTER --> SEM[Semantic Movie Search]
    ROUTER --> REV[Review Analytics Retrieval]
    ROUTER --> REC[Personalized Recommendation]
    CAT --> CONTEXT[Evidence Context]
    SEM --> CONTEXT
    REV --> CONTEXT
    REC --> CONTEXT
    CONTEXT --> GEN[Response Generator]
    GEN --> CHECK[Grounding / Evidence Check]
    CHECK --> UI[Answer and Movie Cards]
```

## 12.2 Query types

  -----------------------------------------------------------------------
  User query                          Backend action
  ----------------------------------- -----------------------------------
  "Romance and science fiction        Filter by genres and rank by
  movies"                             relevance

  "Movies like Interstellar"          Resolve movie, retrieve semantic
                                      neighbours

  "How is Interstellar?"              Retrieve movie summary, scores and
                                      review distribution

  "What do people say about the       Retrieve soundtrack aspect evidence
  music?"                             

  "Something emotional but under two  Parse preference filters and search
  hours"                              catalogue

  "Compare Arrival and Interstellar"  Retrieve both movie profiles and
                                      compare evidence
  -----------------------------------------------------------------------

## 12.3 Intent schema

The query parser should produce a structured object such as:

``` json
{
  "intent": "movie_search",
  "genres": ["Romance", "Science Fiction"],
  "themes": [],
  "similar_to_movie": null,
  "max_runtime": null,
  "mood": null,
  "user_personalization": true
}
```

This is an example schema. Validate model-generated JSON before using it
in SQL or search queries.

## 12.4 Retrieval

Use: - PostgreSQL filters for exact metadata. - pgvector for semantic
similarity. - Review analytics tables for sentiment and aspect
questions. - Recommendation service for personalized requests.

Retrieve evidence first, then generate a response.

## 12.5 Grounding rules

-   Cite or identify the review evidence internally.
-   Do not state an audience consensus without enough reviews.
-   If there is not enough data, say so.
-   Distinguish actual audience sentiment from a personalized
    prediction.
-   Distinguish official metadata from model-inferred themes.
-   Never let the assistant invent movie release dates, cast or review
    statistics.

## 12.6 Voice input

Start with speech-to-text: - Browser Web Speech API where supported. - A
server-side speech recognition model such as Whisper if consistent
cross-browser behaviour is required.

The Web Speech API has browser/platform-dependent behaviour. Provide a
text input fallback.

Optional later feature: - Text-to-speech for assistant responses.

Ask for microphone permission only after the user selects the microphone
control. Do not record continuously.

------------------------------------------------------------------------

# 13. Backend Architecture --- FastAPI

## 13.1 Backend responsibilities

-   Authentication and authorization.
-   Request validation.
-   Movie metadata retrieval.
-   Review creation.
-   NLP inference orchestration.
-   Score and summary retrieval.
-   Recommendation retrieval.
-   Chat orchestration.
-   Database operations.
-   Rate limiting.
-   Logging and error handling.

## 13.2 Suggested API routes

### Movies

``` text
GET    /api/v1/movies
GET    /api/v1/movies/{movie_id}
GET    /api/v1/movies/{movie_id}/scores
GET    /api/v1/movies/{movie_id}/reviews
GET    /api/v1/movies/{movie_id}/summary
GET    /api/v1/movies/{movie_id}/similar
```

### Reviews

``` text
POST   /api/v1/movies/{movie_id}/reviews
GET    /api/v1/reviews/{review_id}
POST   /api/v1/reviews/{review_id}/reanalyze
POST   /api/v1/reviews/{review_id}/report
```

### User

``` text
GET    /api/v1/users/me
GET    /api/v1/users/me/preferences
PATCH  /api/v1/users/me/preferences
GET    /api/v1/users/me/history
GET    /api/v1/users/me/watchlist
POST   /api/v1/users/me/watchlist
DELETE /api/v1/users/me/watchlist/{movie_id}
```

### Recommendation

``` text
GET    /api/v1/recommendations/for-you
GET    /api/v1/recommendations/similar/{movie_id}
GET    /api/v1/recommendations/by-preference
```

### Chat

``` text
POST   /api/v1/chat/query
POST   /api/v1/chat/voice-transcript
```

### Admin / model operations

``` text
GET    /api/v1/admin/model-health
GET    /api/v1/admin/pipeline-status
POST   /api/v1/admin/recompute-movie/{movie_id}
```

Protect admin routes with authorization. Do not expose model-management
endpoints publicly.

## 13.3 Review submission sequence

``` mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as FastAPI
    participant D as PostgreSQL
    participant N as NLP Service
    participant J as Analytics Job

    U->>F: Submit review
    F->>A: POST review
    A->>A: Validate input and permissions
    A->>D: Save review as pending analysis
    A->>N: Analyze text
    N-->>A: Sentiment, aspects, risk
    A->>D: Save predictions
    A->>J: Enqueue aggregate refresh
    A-->>F: Review analysis response
    F-->>U: Show sentiment and aspects
    J->>D: Publish updated score / summary snapshot
```

For a simple prototype, the aggregate refresh may be a background task.
For a larger system, use a durable job queue or event broker.

## 13.4 API response contract

Use stable response schemas. Example:

``` json
{
  "review_id": "review_123",
  "sentiment": {
    "label": "positive",
    "positive": 0.78,
    "negative": 0.12,
    "neutral": 0.10
  },
  "aspects": [
    {
      "aspect": "cinematography",
      "sentiment": "positive",
      "confidence": 0.91
    },
    {
      "aspect": "pacing",
      "sentiment": "negative",
      "confidence": 0.83
    }
  ],
  "risk": {
    "score": 12,
    "band": "low"
  },
  "model_version": "review-pipeline-v1"
}
```

Illustrative output only.

## 13.5 Error handling

Define clear errors for: - Invalid movie ID. - Review too short / too
long. - Unsupported language. - Model unavailable. - Rate limit
reached. - Database unavailable. - External metadata provider
unavailable. - Authentication required.

If NLP inference is unavailable, save the review safely and mark it as
awaiting analysis if the product policy permits. Do not fabricate a
prediction.

------------------------------------------------------------------------

# 14. Frontend Architecture and User Experience

The website should feel like a real film community product, not a
generic AI dashboard.

## 14.1 Visual direction

Take product-design inspiration from film discovery and review
platforms, but create original branding and components.

Recommended style: - Dark charcoal / near-black background. - Film
posters as primary visual objects. - Strong typography. - Consistent
spacing. - Restrained accent colour. - Clear rating hierarchy. -
Responsive layout. - No excessive neon gradients, glowing AI effects or
unnecessary glassmorphism.

## 14.2 Pages

### Page 1 --- Home / Discover

Sections: - Featured movies. - Trending. - Popular. - Recommended for
you. - New releases. - Genre shelves. - Theme discovery. - Search bar.

### Page 2 --- Search results

Filters: - Genre. - Release year. - Runtime. - Language. - Theme. -
Audience sentiment score where available.

### Page 3 --- Movie details

This is the most important page.

Recommended order:

1.  Backdrop and poster.
2.  Title, release year, runtime and genres.
3.  Audience sentiment score and review count.
4.  Genre reception / theme / cinematic aspect profile.
5.  AI-generated review summary.
6.  Positive / neutral / negative review distribution.
7.  Aspect sentiment charts.
8.  Individual reviews.
9.  Write a review.
10. Similar movies.

The AI summary must appear above the individual reviews, as requested.

### Page 4 --- Review composer

-   Text editor.
-   Optional star rating.
-   Spoiler checkbox.
-   Submit button.
-   Real-time or immediate post-submit analysis.
-   Sentiment label.
-   Aspect analysis.
-   Moderation notice if needed.

### Page 5 --- User profile

-   Watched movies.
-   Ratings.
-   Reviews.
-   Watchlist.
-   Taste profile.
-   Preferred genres and themes.
-   Recommendation history.

### Page 6 --- Recommendations

-   Personalized shelf.
-   Similar movies.
-   Theme-based discovery.
-   Explainable recommendation cards.
-   Filters.

### Page 7 --- Conversational discovery

-   Chat transcript.
-   Text input.
-   Microphone control.
-   Suggested prompts.
-   Movie result cards.
-   Follow-up query support.

### Page 8 --- About / Methodology

Explain: - What the score means. - What data sources are used. - How
sentiment is calculated. - How reviews are moderated. - TMDB
attribution. - Model limitations. - Dataset and privacy notes.

## 14.3 Frontend component structure

``` text
frontend/
├── app/
│   ├── page.tsx
│   ├── discover/
│   ├── movies/[movieId]/
│   ├── search/
│   ├── recommendations/
│   ├── profile/
│   ├── assistant/
│   └── about/
├── components/
│   ├── layout/
│   ├── movie/
│   ├── review/
│   ├── score/
│   ├── charts/
│   ├── recommendation/
│   ├── chatbot/
│   └── common/
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   └── types.ts
└── styles/
```

## 14.4 Important UI states

Every page must support: - Loading. - Empty results. - Error. - No
review data. - Insufficient evidence. - Model processing. - Model
unavailable. - User not signed in. - Mobile layout.

A movie with zero reviews should not show a fake score. Show an honest
empty state.

------------------------------------------------------------------------

# 15. Model Serving and Model Versioning

## 15.1 Separate training from inference

Training notebooks should not be imported into the website at runtime.

Training workflow:

``` text
Notebook / Training Script
  -> Dataset version
  -> Train model
  -> Evaluate
  -> Save checkpoint
  -> Create model card
  -> Register approved version
```

Inference workflow:

``` text
FastAPI
  -> Load approved model at startup
  -> Validate input
  -> Tokenize
  -> Run inference
  -> Return structured output
```

## 15.2 Model directory

``` text
models/
├── sentiment/
│   ├── v1/
│   │   ├── config.json
│   │   ├── tokenizer files
│   │   ├── model weights
│   │   └── model_card.md
├── aspect_extraction/
├── aspect_sentiment/
├── theme_classifier/
├── summarizer/
├── fake_review/
├── embeddings/
└── recommendation/
```

Do not commit large model weights to Git if the repository or platform
has file-size limitations. Use Git LFS or an appropriate artifact store.

## 15.3 Model registry metadata

For every model version record: - Model name. - Version. -
Architecture. - Base checkpoint. - Training dataset version. - Training
code commit. - Hyperparameters. - Metrics. - Known limitations. -
License. - Artifact location. - Approval status.

## 15.4 Reproducibility

Set random seeds where supported. Save: - Environment file. - Dataset
version. - Train / validation / test IDs. - Tokenizer version. - Model
checkpoint. - Training logs. - Evaluation output.

------------------------------------------------------------------------

# 16. Jupyter Notebook Plan

The notebook sequence should be modular and reproducible.

  ---------------------------------------------------------------------------------------
  Notebook                                Purpose                 Main output
  --------------------------------------- ----------------------- -----------------------
  `01_dataset_audit.ipynb`                Inspect all sources,    Dataset report
                                          schema and licenses     

  `02_movielens_eda.ipynb`                Ratings, users, movies  EDA charts
                                          and tags analysis       

  `03_review_preprocessing.ipynb`         Clean and validate      Clean review dataset
                                          review text             

  `04_tfidf_baseline.ipynb`               BoW, n-grams, TF-IDF    Baseline metrics
                                          and traditional models  

  `05_transformer_sentiment.ipynb`        Fine-tune three-class   Sentiment checkpoint
                                          sentiment model         

  `06_sentiment_evaluation.ipynb`         Confusion matrix, class Evaluation report
                                          metrics and calibration 

  `07_aspect_extraction.ipynb`            Train aspect extraction Aspect model

  `08_aspect_sentiment.ipynb`             Train aspect sentiment  Aspect sentiment model
                                          model                   

  `09_theme_extraction.ipynb`             Theme classifier and    Theme model / topics
                                          topic modelling         

  `10_review_summarization.ipynb`         Evidence-grounded       Summary examples
                                          summarization           

  `11_fake_review_detection.ipynb`        Duplicate and anomaly   Risk model
                                          analysis                

  `12_embeddings_semantic_search.ipynb`   Generate embeddings and Embedding index
                                          evaluate retrieval      

  `13_hybrid_recommender.ipynb`           ALS, content and hybrid Recommendation model
                                          ranking                 

  `14_recommendation_evaluation.ipynb`    Top-K ranking metrics   Evaluation report
                                          and cold-start tests    

  `15_final_model_comparison.ipynb`       Consolidate all model   Final comparison
                                          results                 
  ---------------------------------------------------------------------------------------

### Notebook rules

-   Every notebook should start with its objective.
-   State the input dataset and its version.
-   Keep preprocessing reproducible.
-   Avoid hidden dependencies on variables from another notebook.
-   Save outputs in known paths.
-   Include model evaluation.
-   Include a short conclusion.
-   Do not report metrics from the training set as final performance.
-   Do not use the held-out test set repeatedly for tuning.

------------------------------------------------------------------------

# 17. Scala Project Structure

``` text
scala/
├── build.sbt
├── project/
├── src/
│   ├── main/
│   │   └── scala/
│   │       └── com/movieintel/
│   │           ├── config/
│   │           ├── ingestion/
│   │           │   ├── MovieLensIngestion.scala
│   │           │   └── ReviewIngestion.scala
│   │           ├── cleaning/
│   │           │   └── DataCleaning.scala
│   │           ├── transformations/
│   │           │   ├── RddExamples.scala
│   │           │   └── DataFrameTransformations.scala
│   │           ├── analytics/
│   │           │   ├── MovieAnalytics.scala
│   │           │   └── UserAnalytics.scala
│   │           ├── recommendation/
│   │           │   └── AlsTraining.scala
│   │           ├── streaming/
│   │           │   └── ReviewStreamJob.scala
│   │           └── Main.scala
│   └── test/
└── README.md
```

## 17.1 Scala functional programming concepts

Demonstrate: - Immutable `val`. - Immutable collections. - `map`,
`flatMap`, `filter`, `fold`, `reduce`. - Higher-order functions. -
Pattern matching. - Case classes. - Pure functions. - Tail recursion in
a small independent exercise. - Error handling with `Option` / `Either`
where appropriate.

Do not write every Spark operation as a custom low-level function. Use
Spark DataFrame APIs where appropriate.

## 17.2 Example case classes

``` scala
case class Movie(
  movieId: Long,
  title: String,
  genres: Seq[String]
)

case class Rating(
  userId: Long,
  movieId: Long,
  rating: Double,
  timestamp: Long
)
```

These are illustrative domain structures. The actual Spark schema should
be validated against source data.

------------------------------------------------------------------------

# 18. Repository Structure --- Complete Project

``` text
movie-review-recommendation-system/
│
├── README.md
├── ARCHITECTURE.md
├── LICENSES_AND_ATTRIBUTION.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   └── workers/
│   ├── requirements.txt
│   └── tests/
│
├── notebooks/
│   └── 01_...ipynb
│
├── scala/
│   ├── build.sbt
│   └── src/
│
├── models/
│   ├── sentiment/
│   ├── aspect_extraction/
│   ├── aspect_sentiment/
│   ├── theme/
│   ├── summarization/
│   ├── fake_review/
│   ├── embeddings/
│   └── recommendation/
│
├── data/
│   ├── README.md
│   ├── raw/
│   ├── bronze/
│   ├── silver/
│   ├── gold/
│   └── dataset_cards/
│
├── scripts/
│   ├── download_instructions.md
│   ├── validate_datasets.py
│   ├── run_spark_jobs.ps1
│   └── run_spark_jobs.sh
│
├── documentation/
│   ├── architecture/
│   ├── dataset/
│   ├── model_cards/
│   ├── evaluation/
│   ├── api/
│   └── screenshots/
│
└── tests/
    ├── integration/
    ├── data_quality/
    └── end_to_end/
```

Keep data and model artifacts out of Git unless they are small, legally
distributable and intentionally included. Add appropriate ignore rules.

------------------------------------------------------------------------

# 19. Local Development Setup

This is a practical setup path for a Windows development machine. The
same architecture can be adapted to Linux.

## 19.1 Install prerequisites

Install and verify:

1.  Git.
2.  Python version supported by the selected PyTorch / Transformers
    environment.
3.  Java version supported by the chosen Spark release.
4.  Scala version matching Spark.
5.  SBT.
6.  Node.js LTS.
7.  PostgreSQL.
8.  A code editor such as VS Code or IntelliJ IDEA.
9.  JupyterLab or Jupyter Notebook.

Do not install random versions independently. Pin compatible versions in
the project documentation.

## 19.2 Python environment

Create a virtual environment:

``` powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

Install packages in groups and record the final tested versions.

Suggested package families:

``` text
fastapi
uvicorn
pydantic
sqlalchemy
psycopg
pandas
numpy
scikit-learn
matplotlib
seaborn
jupyter
torch
transformers
datasets
evaluate
accelerate
sentence-transformers
bertopic
pgvector
```

Install a PyTorch build compatible with the machine's GPU and CUDA setup
by following the official PyTorch installation selector. Do not assume
that a CUDA version is installed merely because the computer has an
NVIDIA GPU.

## 19.3 Node environment

Create the frontend using a supported React / Next.js setup.

Install: - Tailwind CSS. - A component library only if it helps. - A
charting library. - An API client. - Form validation. - Authentication
integration.

Pin dependencies and commit the lockfile.

## 19.4 PostgreSQL setup

1.  Install PostgreSQL.
2.  Create a database such as `movie_intelligence`.
3.  Create a dedicated application user.
4.  Enable pgvector if available in the selected PostgreSQL
    installation.
5.  Run schema migrations.
6.  Add indexes.
7.  Insert a small seed dataset.
8.  Verify the backend connection.

Example environment variables:

``` env
DATABASE_URL=postgresql://app_user:change_me@localhost:5432/movie_intelligence
TMDB_API_KEY=replace_me
MODEL_DIR=../models
ENVIRONMENT=development
```

This is an example only. Never commit a real `.env` file.

## 19.5 Spark setup

1.  Install a compatible JDK.
2.  Install the chosen Spark distribution.
3.  Configure `JAVA_HOME`.
4.  Configure Spark environment variables if needed.
5.  Confirm `spark-shell` starts.
6.  Run a sample Scala application.
7.  Configure the Scala/SBT build to match the Spark and Scala versions.
8.  Run a small local job before using the full MovieLens dataset.

Start with local mode, such as `local[*]`, and reduce parallelism if the
laptop runs out of memory.

## 19.6 GPU verification

Before training: - Check that PyTorch detects the GPU. - Check GPU
memory. - Run a tiny training batch. - Record training speed and
memory. - Use a smaller batch size or gradient accumulation if
necessary.

The project must remain runnable in CPU mode for inference/testing, even
if model training uses a GPU.

------------------------------------------------------------------------

# 20. End-to-End Implementation Workflow

Follow this order. Do not start every component at once.

## Phase 0 --- Project foundation

### Step 1

Create the Git repository and folder structure.

### Step 2

Create `README.md`, `ARCHITECTURE.md`, `.gitignore` and `.env.example`.

### Step 3

Pin compatible tool versions.

### Step 4

Create a project issue board with tasks and acceptance criteria.

**Exit criteria:** The repository runs a minimal frontend, backend and
database connection.

## Phase 1 --- Data acquisition and audit

### Step 1

Download MovieLens 32M from GroupLens.

### Step 2

Download the Stanford IMDb sentiment dataset.

### Step 3

Create TMDB API credentials and read its current terms.

### Step 4

Fetch a small set of movie metadata records for a proof of concept.

### Step 5

Create a first-party review submission form.

### Step 6

Prepare a manually annotated review dataset.

### Step 7

Create dataset cards and source/license records.

### Step 8

Validate all IDs and build the external ID mapping table.

**Exit criteria:** A validated movie catalogue, ratings dataset, review
benchmark and documented movie-linked review collection strategy exist.

## Phase 2 --- Spark and Scala BDA pipeline

### Step 1

Set up the compatible Spark / Scala environment.

### Step 2

Implement RDD examples.

### Step 3

Read MovieLens files using DataFrames.

### Step 4

Create Bronze and Silver outputs.

### Step 5

Join movies, ratings, tags and external IDs.

### Step 6

Create movie and user aggregates.

### Step 7

Train and evaluate ALS.

### Step 8

Implement a small Structured Streaming demonstration.

### Step 9

Capture Spark UI screenshots and performance metrics.

**Exit criteria:** Scala jobs execute successfully and produce
documented Parquet outputs.

## Phase 3 --- NLP baseline and Transformer

### Step 1

Audit the review dataset.

### Step 2

Define label guidelines.

### Step 3

Build TF-IDF and Logistic Regression baseline.

### Step 4

Build a Linear SVM comparison.

### Step 5

Create a valid three-class training set.

### Step 6

Fine-tune DistilBERT or a suitable Transformer.

### Step 7

Evaluate on held-out data.

### Step 8

Calibrate probabilities if required by the score engine.

### Step 9

Save model artifacts and model cards.

**Exit criteria:** A working sentiment inference function returns three
probabilities and a class label.

## Phase 4 --- Aspect, theme and review intelligence

### Step 1

Define aspect taxonomy.

### Step 2

Annotate aspect spans / labels.

### Step 3

Train aspect extraction model.

### Step 4

Train aspect sentiment classifier.

### Step 5

Create theme taxonomy.

### Step 6

Train or validate theme classification.

### Step 7

Run exploratory topic modelling.

### Step 8

Implement evidence-grounded review summarization.

### Step 9

Implement suspicious-review risk scoring.

### Step 10

Implement score aggregation and confidence policy.

**Exit criteria:** For a movie with real linked reviews, the system can
show sentiment, aspect insights, theme insights and an evidence-grounded
summary.

## Phase 5 --- Recommendation engine

### Step 1

Train ALS using MovieLens.

### Step 2

Create content-based movie features.

### Step 3

Generate movie embeddings.

### Step 4

Build user preference profiles.

### Step 5

Combine candidate sources.

### Step 6

Tune ranking weights.

### Step 7

Evaluate ranking quality.

### Step 8

Implement new-user and new-movie cold start.

### Step 9

Generate explanation reason codes.

**Exit criteria:** The backend can return personalized and similar-movie
recommendations with a reason.

## Phase 6 --- Backend

### Step 1

Create FastAPI project.

### Step 2

Implement database models and migrations.

### Step 3

Implement movie APIs.

### Step 4

Implement review submission.

### Step 5

Load NLP models in a dedicated service.

### Step 6

Save prediction outputs.

### Step 7

Implement movie score and summary APIs.

### Step 8

Implement recommendation APIs.

### Step 9

Implement chatbot retrieval endpoints.

### Step 10

Add authentication, validation, logging and rate limits.

**Exit criteria:** APIs work independently and return real
database/model results.

## Phase 7 --- Frontend

### Step 1

Create the design system.

### Step 2

Build home / discover.

### Step 3

Build movie detail page.

### Step 4

Build review composer and analysis display.

### Step 5

Build review summary and aspect scorecards.

### Step 6

Build user profile and watchlist.

### Step 7

Build recommendation page.

### Step 8

Build conversational discovery.

### Step 9

Add microphone input and text fallback.

### Step 10

Test responsive behaviour and empty states.

**Exit criteria:** A user can discover movies, open a movie, read its
summary, submit a review, see model analysis and receive
recommendations.

## Phase 8 --- Integration and evaluation

### Step 1

Run the complete application locally.

### Step 2

Create integration tests for API and database.

### Step 3

Test review submission and prediction persistence.

### Step 4

Test movie score refresh.

### Step 5

Test recommendation generation.

### Step 6

Test chatbot retrieval grounding.

### Step 7

Test new movie and new user cold-start states.

### Step 8

Run model evaluation scripts.

### Step 9

Capture screenshots and demo videos.

### Step 10

Prepare the academic report and presentation.

**Exit criteria:** All core user journeys work end-to-end and the
evaluation evidence is reproducible.

------------------------------------------------------------------------

# 21. Testing Strategy

## 21.1 Data quality tests

Check: - Null movie IDs. - Duplicate IDs. - Invalid ratings. - Invalid
timestamps. - Missing review text. - Wrong external ID mapping. -
Unexpected genre labels. - Duplicate reviews. - Unexpected language. -
Broken poster paths.

## 21.2 NLP tests

Check: - Empty review. - Very short review. - Long review. - Mixed
sentiment. - Sarcasm. - Negation. - Aspect with different sentiment from
the overall review. - Unsupported language. - Emoji and punctuation. -
Text with spam patterns.

Use a fixed regression test set. When a model changes, compare outputs
against the previous version.

## 21.3 Scoring tests

Check: - No reviews. - One review. - Few reviews. - Many reviews. -
All-positive reviews. - All-negative reviews. - Mixed reviews. -
Duplicate review attempt. - Suspicious review excluded /
down-weighted. - Model reprocessing. - Score snapshot version.

## 21.4 Recommendation tests

Check: - New user. - New movie. - User with one rating. - User with many
ratings. - No unseen movies. - Genre filter. - Similar-movie query. -
Diversity. - Repeated recommendations. - Model unavailable fallback.

## 21.5 Chatbot tests

Check: - Exact title lookup. - Ambiguous title. - Genre combination. -
Similar movie. - Aspect-specific review question. - No review
evidence. - Follow-up context. - Voice transcription failure. - Prompt
injection / requests to ignore evidence.

The chatbot should treat retrieved reviews and metadata as data, not
instructions.

## 21.6 Full end-to-end test

A final demonstration should execute this journey:

1.  User opens the website.
2.  Searches for a movie.
3.  Opens its detail page.
4.  Sees real metadata and current audience analytics.
5.  Reads the AI review summary.
6.  Submits a review.
7.  Receives sentiment and aspect predictions.
8.  Sees the review saved.
9.  The movie analytics refreshes.
10. User receives a recommendation.
11. User asks the chatbot a follow-up question.
12. Chatbot answers using movie/review evidence.

------------------------------------------------------------------------

# 22. Evaluation Metrics and Reporting

## 22.1 Sentiment

Report: - Accuracy. - Per-class precision. - Per-class recall. -
Macro-F1. - Weighted-F1. - Confusion matrix. - Calibration / confidence
analysis.

Do not report only accuracy, especially if the neutral class is
imbalanced.

## 22.2 Aspect extraction

Report: - Span-level precision. - Span-level recall. - Span-level F1. -
Per-aspect performance. - Error examples.

## 22.3 Aspect sentiment

Report: - Per-class precision / recall / F1. - Macro-F1. - Aspect-wise
confusion matrix.

## 22.4 Summarization

Report: - ROUGE. - BERTScore. - Human factuality assessment. - Aspect
coverage. - Unsupported claim count. - Contradiction examples.

## 22.5 Fake-review risk

Report: - Precision. - Recall. - F1. - PR-AUC. - False-positive rate. -
Performance by review source / domain.

A high false-positive rate can unfairly suppress genuine reviews.
Include human moderation and an appeal/review process.

## 22.6 Recommendation

Report: - Precision@K. - Recall@K. - NDCG@K. - MAP@K where useful. -
Coverage. - Diversity. - Novelty. - Cold-start evaluation.

## 22.7 Big Data

Report: - Dataset size. - Processing time. - Number of partitions. -
Input and output row counts. - Throughput. - Shuffle size where
relevant. - Memory usage. - Spark job / stage screenshots. - Batch
versus micro-batch behaviour.

Compare a small local baseline with Spark processing where possible. Do
not claim distributed speedup if you only ran one local process.

## 22.8 Inference and application

Report: - Average latency. - p95 latency. - Requests per second under a
small test. - Model loading time. - Memory usage. - API error rate. -
Database query latency.

------------------------------------------------------------------------

# 23. Mapping to the BDA and TA Syllabus

## 23.1 BDA mapping

  --------------------------------------------------------------------------
  Unit                    Syllabus concepts          Evidence in project
  ----------------------- -------------------------- -----------------------
  Unit 1                  Big Data characteristics,  MovieLens 32M,
                          tools, Hadoop ecosystem,   ingestion,
                          Mapper / Reducer           partitioning, tag word
                                                     count, MapReduce-style
                                                     aggregation

  Unit 2                  Scala FP,                  Scala examples,
                          mutable/immutable          immutable
                          structures, collections,   transformations, case
                          higher-order functions,    classes, functional
                          closures, recursion, OOP,  helpers, safe parallel
                          concurrency                Spark execution

  Unit 3                  Spark architecture, RDDs,  Scala Spark jobs, Spark
                          DataFrames, Datasets,      UI, RDD exercises,
                          transformations/actions,   DataFrame pipeline and
                          lazy evaluation, DAG       optimization

  Unit 4                  MLlib, ML pipelines and    ALS recommendation,
                          algorithms                 model tuning, ranking
                                                     evaluation and pipeline
                                                     documentation
  --------------------------------------------------------------------------

## 23.2 TA mapping

  -----------------------------------------------------------------------
  Unit                    Syllabus concepts       Evidence in project
  ----------------------- ----------------------- -----------------------
  Unit 1                  Linguistics, syntax,    Review preprocessing,
                          semantics, morphology,  tokenization, POS
                          collocation             tagging / linguistic
                                                  exploration

  Unit 2                  One-hot, BoW, TF-IDF,   Baseline notebook,
                          n-grams, embeddings     TF-IDF, Sentence-BERT

  Unit 3                  Deep learning,          Transformer
                          sequences, BERT, GPT,   fine-tuning, token
                          graph NLP, HMM, CRF,    classification,
                          topic modelling         theme/topic modelling,
                                                  optional CRF comparison

  Unit 4                  POS, NER, sentiment,    Sentiment, aspect
                          translation, QA,        extraction, summary,
                          summarization,          chatbot QA, metrics and
                          evaluation and          charts
                          visualization           
  -----------------------------------------------------------------------

### Course coverage strategy

Prioritize the core project tasks: - TF-IDF baseline. - Transformer
sentiment. - Aspect extraction. - Topic/theme analysis. -
Summarization. - ALS. - RDD and DataFrame operations. - Scala functional
programming.

Demonstrate POS tagging and NER as supporting exercises. Do not add
machine translation, HMM, CRF and Graph NLP to the product unless they
have a clear use. A small notebook demonstration can cover a syllabus
concept without making the production architecture unnecessarily
complicated.

------------------------------------------------------------------------

# 24. Project Timeline and Priorities

A realistic student implementation can be organized into 8--10 work
blocks. Adjust the calendar based on the course deadline and team size.

  -----------------------------------------------------------------------
  Block                   Main work               Deliverable
  ----------------------- ----------------------- -----------------------
  1                       Requirements,           Frozen design and data
                          architecture, dataset   plan
                          audit                   

  2                       MovieLens ingestion,    Working BDA pipeline
                          Spark, Scala            

  3                       TF-IDF and Transformer  Evaluated sentiment
                          sentiment               model

  4                       Aspect extraction and   Aspect/theme outputs
                          theme analysis          

  5                       Summarization and       Review intelligence
                          review risk             

  6                       ALS and content         Hybrid recommender
                          recommendation          

  7                       Backend and database    Working APIs
                          integration             

  8                       Frontend and chatbot    Working website

  9                       Testing and performance Evaluation evidence

  10                      Report, slides and demo Final academic
                          rehearsal               submission
  -----------------------------------------------------------------------

## 24.1 Priority tiers

### Must-have

-   Movie catalogue.
-   MovieLens Spark pipeline.
-   Scala RDD and DataFrame demonstrations.
-   TF-IDF baseline.
-   Trained three-class sentiment model.
-   Review submission.
-   Movie-level sentiment score with evidence count.
-   AI review summary.
-   ALS recommendation.
-   Basic frontend.
-   Backend integration.

### Strongly recommended

-   Aspect extraction and aspect sentiment.
-   Theme profile.
-   Content-based recommendation.
-   New-movie cold start.
-   Suspicious-review risk analysis.
-   Conversational movie discovery.

### Advanced extensions

-   Voice responses.
-   Kafka.
-   Multilingual review support.
-   Graph-based recommendations.
-   Fine-grained temporal sentiment trends.
-   Advanced coordinated-review detection.
-   Online learning / periodic retraining.

Do not sacrifice the quality of the must-have features to add every
advanced extension.

------------------------------------------------------------------------

# 25. Security, Privacy, Ethics and Data Licensing

## 25.1 API security

-   Keep TMDB API credentials on the backend.
-   Use environment variables.
-   Do not expose database credentials.
-   Validate every request.
-   Rate-limit review submission and chat endpoints.
-   Protect admin routes.
-   Use secure authentication.
-   Use HTTPS in public deployments.

## 25.2 User privacy

-   Collect only required user data.
-   Explain how reviews and interactions are used.
-   Obtain appropriate consent before using user-submitted content for
    training.
-   Provide account and data deletion paths.
-   Avoid collecting sensitive personal information.
-   Do not expose reviewer private details.
-   Keep audit logs without unnecessarily storing sensitive text.

## 25.3 Review moderation fairness

-   Do not equate negative sentiment with fake content.
-   Do not automatically penalize users for unpopular opinions.
-   Use suspicious-review scores as moderation signals.
-   Keep human review for high-impact moderation decisions.
-   Monitor false positives and subgroup performance.

## 25.4 Licensing

Create `LICENSES_AND_ATTRIBUTION.md` documenting: - Dataset source. -
License / terms. - Allowed usage. - Attribution. - Redistribution
restrictions. - Model checkpoint license. - Poster/image attribution. -
Third-party code licenses.

Check every pretrained model's license and use restrictions before
distribution.

------------------------------------------------------------------------

# 26. Deployment Architecture

For the academic prototype, begin locally.

## 26.1 Local development deployment

``` text
Browser
  -> Next.js development server
  -> FastAPI server
  -> PostgreSQL + pgvector
  -> Local model artifacts
  -> Local Spark jobs
  -> Local Parquet data lake
```

Use separate terminals or a process manager.

## 26.2 Optional container deployment

Docker Compose can run: - Frontend. - Backend. - PostgreSQL. - Optional
worker.

Spark jobs can run locally or in a separate container after version
compatibility is confirmed.

Do not put huge model weights inside a container image if that makes
builds unnecessarily large. Mount model artifacts or download approved
artifacts through a controlled process.

## 26.3 Public demo deployment

Before deploying publicly: - Review TMDB terms and attribution. - Remove
development credentials. - Use a secure database. - Set upload / request
limits. - Protect user data. - Ensure model artifacts are licensed for
deployment. - Provide a clear privacy notice. - Avoid publishing
restricted datasets.

------------------------------------------------------------------------

# 27. Common Failure Modes and How to Avoid Them

  -----------------------------------------------------------------------
  Failure                 Why it happens          Prevention
  ----------------------- ----------------------- -----------------------
  Movie score is          Very few reviews or     Shrinkage, evidence
  misleading              uncalibrated            counts and uncertainty
                          predictions             labels

  Movie summaries are     Free-form generation    Evidence-grounded
  invented                without retrieved       summarization
                          reviews                 

  MovieLens has no review It is a ratings/tag     Use separate review
  text                    dataset                 sources

  Neutral classifier      Binary training data    Build a valid
  performs poorly         used as three-class     neutral-labelled
                          data                    dataset

  Wrong movie review      Fuzzy title joins or    Canonical IDs and
  mapping                 incorrect IDs           mapping audit

  ALS recommendations are Leakage, bad split or   Temporal evaluation and
  poor                    sparse data             parameter tuning

  Fake-review detector    Sentiment or weak       Risk score plus human
  blocks genuine users    heuristics treated as   moderation
                          truth                   

  New movie gets a        Cold start not designed Show no score until
  fabricated score                                evidence exists

  Chatbot hallucinates    Model answers without   Retrieval-first
                          retrieval               architecture and
                                                  evidence checks

  Spark job runs out of   Collecting large data   DataFrames, partitions
  memory                  or bad partitioning     and bounded samples

  Scala dependency        Incompatible Spark /    Pin compatible versions
  conflicts               Scala versions          

  Frontend shows stale    No refresh / snapshot   Background aggregation
  analytics               versioning              and timestamps

  Model metrics look      Data leakage or         Deduplicate and use
  unrealistically high    duplicate overlap       leakage-aware splits

  Project becomes too     Too many features built Follow priority tiers
  large                   simultaneously          and exit criteria
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 28. Final Acceptance Checklist

## Data

-   [ ] MovieLens 32M downloaded and documented.
-   [ ] Stanford IMDb dataset documented as binary benchmark.
-   [ ] TMDB API credentials configured securely.
-   [ ] Dataset licenses reviewed.
-   [ ] Canonical movie IDs created.
-   [ ] External ID mappings validated.
-   [ ] First-party review collection implemented.
-   [ ] Dataset cards prepared.

## BDA / Scala

-   [ ] Scala build works with selected Spark version.
-   [ ] RDD operations demonstrated.
-   [ ] DataFrame ingestion works.
-   [ ] Cleaning and joins work.
-   [ ] Movie aggregations work.
-   [ ] User aggregates work.
-   [ ] ALS model trains.
-   [ ] Structured Streaming demo works.
-   [ ] Spark UI evidence captured.

## TA / NLP

-   [ ] TF-IDF baseline trained.
-   [ ] Transformer sentiment model trained.
-   [ ] Three-class labels validated.
-   [ ] Held-out evaluation completed.
-   [ ] Aspect extraction evaluated.
-   [ ] Aspect sentiment evaluated.
-   [ ] Theme extraction evaluated.
-   [ ] Summary evidence checks implemented.
-   [ ] Suspicious-review risk approach documented.
-   [ ] Model cards saved.

## Recommendation

-   [ ] ALS evaluation completed.
-   [ ] Content-based similarity implemented.
-   [ ] User profile implemented.
-   [ ] Hybrid ranker implemented.
-   [ ] Cold-start logic implemented.
-   [ ] Recommendation explanations implemented.

## Backend and frontend

-   [ ] FastAPI starts.
-   [ ] PostgreSQL schema is migrated.
-   [ ] Movie APIs work.
-   [ ] Review submission works.
-   [ ] NLP predictions are persisted.
-   [ ] Movie score API works.
-   [ ] Summary API works.
-   [ ] Recommendation API works.
-   [ ] Chat API works.
-   [ ] Home / discover page works.
-   [ ] Movie detail page works.
-   [ ] Review summary appears above reviews.
-   [ ] User profile works.
-   [ ] Voice input has a text fallback.
-   [ ] Empty and error states work.

## Evaluation and submission

-   [ ] Model metrics documented.
-   [ ] Data pipeline metrics documented.
-   [ ] Screenshots captured.
-   [ ] Architecture diagram included.
-   [ ] Database ER diagram included.
-   [ ] API documentation included.
-   [ ] README setup instructions tested.
-   [ ] Demo script rehearsed.
-   [ ] Academic report prepared.
-   [ ] Limitations and future work documented.

------------------------------------------------------------------------

# 29. Recommended Final Demonstration Script

Use one coherent story rather than randomly opening notebooks.

1.  Start the website and backend.
2.  Show the home page and search for a movie.
3.  Open the movie detail page.
4.  Explain the movie metadata and source attribution.
5.  Show the audience sentiment score and review count.
6.  Show genre, theme and cinematic aspect insights.
7.  Explain that theme relevance and audience sentiment are separate.
8.  Show the AI review summary above individual reviews.
9.  Submit a new review.
10. Show positive / negative / neutral probabilities.
11. Show aspect-level sentiment.
12. Show the review-risk signal and explain that it is not an automatic
    fake label.
13. Open personalized recommendations.
14. Show a recommendation explanation.
15. Ask the conversational assistant for romance + science-fiction
    movies.
16. Ask for movies similar to Interstellar.
17. Ask how a movie is and show the retrieved review evidence.
18. Demonstrate voice input if it is stable.
19. Switch to the Scala Spark project.
20. Show RDD operations, DataFrame processing and Spark UI.
21. Run or show ALS model training and evaluation.
22. Open the Jupyter notebooks and show Transformer metrics.
23. End with limitations, methodology and future improvements.

------------------------------------------------------------------------

# 30. Official Documentation and Reference Links

Use official documentation as the first source when implementing and
resolving version-specific issues.

## Datasets and metadata

-   GroupLens MovieLens: https://grouplens.org/datasets/movielens/
-   MovieLens 32M README:
    https://files.grouplens.org/datasets/movielens/ml-32m-README.html
-   Stanford Large Movie Review Dataset:
    https://ai.stanford.edu/\~amaas/data/sentiment/
-   TMDB API getting started:
    https://developer.themoviedb.org/docs/getting-started
-   TMDB API reference:
    https://developer.themoviedb.org/reference/intro/getting-started
-   TMDB FAQ and attribution: https://developer.themoviedb.org/docs/faq
-   IMDb non-commercial data policy:
    https://help.imdb.com/article/imdb/general-information/can-i-use-imdb-data-in-my-software/G5JTRESSHJBBHTGX
-   Optional MADTRAS dataset:
    https://data.mendeley.com/datasets/p59cfx4vx6/3

## Big Data and Scala

-   Apache Spark documentation: https://spark.apache.org/docs/latest/
-   Spark RDD programming guide:
    https://spark.apache.org/docs/latest/rdd-programming-guide.html
-   Spark SQL / DataFrames:
    https://spark.apache.org/docs/latest/sql-programming-guide.html
-   Spark Structured Streaming:
    https://spark.apache.org/docs/latest/streaming/index.html
-   Spark MLlib: https://spark.apache.org/docs/latest/ml-guide.html
-   Scala documentation: https://docs.scala-lang.org/

## NLP and model training

-   Hugging Face Transformers: https://huggingface.co/docs/transformers/
-   Text classification:
    https://huggingface.co/docs/transformers/main/tasks/sequence_classification
-   Token classification:
    https://huggingface.co/docs/transformers/tasks/token_classification
-   Summarization:
    https://huggingface.co/docs/transformers/main/tasks/summarization
-   Hugging Face Datasets: https://huggingface.co/docs/datasets/
-   Sentence Transformers: https://www.sbert.net/
-   BERTopic: https://bertopic.readthedocs.io/

## Backend, database and voice

-   FastAPI: https://fastapi.tiangolo.com/
-   PostgreSQL: https://www.postgresql.org/docs/
-   pgvector: https://github.com/pgvector/pgvector
-   MDN Web Speech API:
    https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API
-   Next.js: https://nextjs.org/docs
-   React: https://react.dev/

------------------------------------------------------------------------

# 31. Final Architectural Recommendation

The project should be built as one integrated system with three clear
intelligence modules:

1.  **Review Intelligence Engine:** Transformer sentiment, aspect-based
    sentiment, theme analysis, evidence-grounded summarization,
    suspicious-review risk and transparent score aggregation.
2.  **Recommendation Engine:** Spark MLlib ALS, content-based retrieval
    and a user preference model.
3.  **Conversational Discovery Engine:** natural-language query
    understanding, semantic retrieval, recommendation integration and
    grounded response generation.

The data platform underneath these modules should use Scala and Spark
for reproducible, distributed processing. Python should own
deep-learning experimentation and inference. FastAPI should connect the
models to the database and frontend. The frontend should behave like a
real movie discovery and review community.

The most important implementation rule is to preserve the difference
between **metadata, user ratings, review sentiment, theme relevance and
personalized prediction**. These are related signals, but they are not
interchangeable.

Build the smallest complete end-to-end version first. Then improve model
quality, coverage, speed and sophistication without breaking the shared
data contracts.

**Definition of success:** A user can open a real movie page, see
evidence-backed audience insights, submit a review and receive actual
model predictions, get personalized movie recommendations, and discover
movies through a grounded text/voice assistant --- while the project
also contains reproducible Scala/Spark jobs and evaluated NLP notebooks
that clearly demonstrate the BDA and TA syllabus.

---

# 32. Hardware-Specific Implementation Plan for the Development Laptop

This section adapts the architecture to the development machine that will be used for model training and the live localhost demonstration.

## 32.1 Confirmed hardware profile

| Component | Available hardware | Design implication |
|---|---|---|
| CPU | Intel Core 7 240H, 2.50 GHz base-reported frequency | Suitable for local development, Spark local jobs and CPU preprocessing |
| System RAM | 16 GB | Run heavy Spark jobs and GPU training sequentially; avoid loading every model at once |
| GPU | NVIDIA GeForce RTX 5050 Laptop GPU | Use CUDA-enabled PyTorch for Transformer fine-tuning and embedding generation |
| GPU memory | 8 GB GDDR7 | Prefer compact encoders, small micro-batches, mixed precision and gradient accumulation |
| Free SSD space | At least 100 GB | Sufficient for a controlled local project; monitor model, dataset and package caches |
| Development environment | Windows laptop, VS Code and Codex | Keep the main workspace and datasets local |

The RTX 5050 Laptop GPU is part of NVIDIA's Blackwell laptop generation. NVIDIA lists 8 GB GDDR7 memory for the RTX 5050 Laptop GPU. Laptop GPU power limits vary by system manufacturer and configuration, so actual sustained training speed also depends on the laptop's configured GPU power and cooling. See https://www.nvidia.com/en-us/geforce/laptops/50-series/.

## 32.2 Overall feasibility

The machine is suitable for:

- Fine-tuning compact Transformer encoders such as DistilBERT.
- Training three-class sentiment classification models.
- Training compact token-classification models for aspect extraction.
- Training compact multi-label theme classifiers.
- Generating Sentence Transformer embeddings in batches.
- Running small local summarization models for inference and experimentation.
- Running the complete frontend, backend and PostgreSQL application locally.
- Running Scala / Spark in local mode for the BDA coursework.

The machine is not intended for:

- Training large language models from scratch.
- Fine-tuning large encoder-decoder models with large batches.
- Keeping several large Transformer models resident on the GPU at the same time.
- Running long GPU training, a large Spark job, the full application and multiple notebooks concurrently without resource limits.

## 32.3 Recommended software baseline

Use a version-controlled environment and verify compatibility at installation time.

| Component | Recommended baseline | Notes |
|---|---|---|
| Python | 3.11 | Common compatible baseline for current PyTorch and Spark 4.3 |
| PyTorch | Current stable Windows build supporting Blackwell | Select the stable CUDA build from the official installation selector; verify actual GPU execution |
| CUDA runtime | CUDA 13.2 PyTorch wheel where available for the selected stable release | The PyTorch wheel supplies its CUDA runtime dependencies; a separate CUDA Toolkit is not normally needed for ordinary PyTorch training |
| NVIDIA driver | Current compatible NVIDIA laptop driver | Update through the laptop/OEM or NVIDIA driver channel, then verify with `nvidia-smi` |
| Java | JDK 21 | Supported by Spark 4.3 |
| Scala | 2.13 | Spark 4.x Scala API uses Scala 2.13 |
| Apache Spark | 4.3.0 | Use local mode for the student laptop |
| SBT | Version compatible with the chosen Scala/Spark dependencies | Pin the version in the repository |
| Node.js | 24 LTS, if available as the current supported LTS at setup time | Use for Next.js frontend development |
| PostgreSQL | Current supported stable version | Local database; enable pgvector if supported by the selected installation |

Official compatibility references:

- PyTorch installation selector: https://pytorch.org/get-started/locally/
- PyTorch release and CUDA architecture matrix: https://github.com/pytorch/pytorch/blob/main/RELEASE.md
- Apache Spark 4.3.0 documentation: https://spark.apache.org/docs/latest/

Do not blindly copy an old CUDA installation command from a tutorial. Select Windows, Pip, Python and the stable CUDA option on the official PyTorch installation page. If the selector and release matrix do not yet show the same release, use the latest stable combination explicitly listed for Windows and Blackwell, not a nightly build unless a specific compatibility issue requires it.

A separate full CUDA Toolkit installation is not required for normal PyTorch wheel usage. Install it only if a selected dependency explicitly requires compiling CUDA extensions or building custom CUDA code. The NVIDIA driver must still be sufficiently recent for the selected CUDA runtime.

## 32.4 Environment setup commands

Run these from PowerShell after installing Python 3.11 and Git.

Create the project environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
```

Install PyTorch using the exact command generated by the official PyTorch selector for the chosen stable Windows CUDA build. Do not install the CPU-only wheel for the main training environment.

After PyTorch installation, verify the environment:

```powershell
nvidia-smi
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('CUDA runtime:', torch.version.cuda); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Not detected'); print('Capability:', torch.cuda.get_device_capability(0) if torch.cuda.is_available() else 'N/A'); print('VRAM GB:', round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2) if torch.cuda.is_available() else 'N/A'); print('BF16 supported:', torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False)"
```

A successful import alone is not enough. `torch.cuda.is_available()` must be true and a small tensor operation must execute on `cuda:0` before any model training begins.

Example GPU smoke test:

```python
import torch

assert torch.cuda.is_available(), "CUDA is not available. Check the NVIDIA driver and PyTorch build."

device = torch.device("cuda:0")
x = torch.randn((2048, 2048), device=device)
y = x @ x
print(torch.cuda.get_device_name(0))
print(y.mean().item())
print(torch.cuda.memory_allocated() / 1024**3, "GB allocated")
```

## 32.5 GPU training settings

Use conservative starting settings and increase only after a successful memory test. Actual batch capacity depends on sequence length, model implementation, optimizer, activation memory, Windows display usage and other GPU processes.

| Model task | Suggested first micro-batch | Starting maximum sequence length | Precision / memory strategy |
|---|---:|---:|---|
| DistilBERT sentiment | 4 | 128 | FP16 initially; BF16 only after runtime support test |
| DistilBERT aspect token classification | 2–4 | 128 | FP16; gradient accumulation |
| Aspect sentiment | 4 | 128 | FP16; gradient accumulation |
| Theme multi-label classifier | 4 | 128–192 | FP16; gradient accumulation |
| Sentence embeddings | 8–16 | Model-dependent | Batch inference and monitor VRAM |
| T5-small / FLAN-T5-small summarization inference | 1–2 sequences | Chunked inputs | Small model, short input chunks, inference mode |
| Lightweight summarization fine-tuning, if needed | 1 | 256–512 input tokens | Gradient accumulation, checkpointing and FP16; only after a memory test |

These are starting values, not guaranteed maximums. The training configuration must expose batch size, sequence length, gradient accumulation, learning rate, epochs and precision through YAML or command-line settings.

Recommended training controls:

- Use a small per-device micro-batch first.
- Use gradient accumulation to achieve a larger effective batch size without increasing the GPU micro-batch.
- Use mixed precision when supported by the installed GPU/runtime combination.
- Test BF16 support with `torch.cuda.is_bf16_supported()`; otherwise use FP16 with a GradScaler where appropriate.
- Use gradient checkpointing only when necessary because it reduces activation memory at the cost of additional computation.
- Use dynamic padding and a suitable maximum sequence length.
- Use early stopping and save the best validation checkpoint.
- Save checkpoints at safe intervals and test resume-from-checkpoint.
- Use `torch.cuda.empty_cache()` only as a memory allocator aid between workloads; it does not free live tensors.
- Avoid unnecessarily large dataloader worker counts on a 16 GB RAM machine. Start with `num_workers=0` on Windows, then test a small increase if useful.
- Monitor GPU memory, system RAM, GPU temperature and laptop power mode during training.

## 32.6 Model choices adapted to 8 GB VRAM

### Sentiment classification

Primary model: DistilBERT sequence classifier.

- Train the three-class model on the project's labelled review dataset.
- Keep the TF-IDF + Logistic Regression baseline for comparison.
- Use a maximum sequence length of 128 initially; test 192 or 256 only if the data and memory budget justify it.
- Start with a micro-batch of 4 and gradient accumulation.
- Use macro-F1, per-class precision/recall and a confusion matrix for evaluation.

### Aspect extraction

Primary model: DistilBERT token classifier.

- Use BIO or a documented span-labeling scheme.
- Start with sequence length 128 and micro-batch 2–4.
- Keep aspect labels consistent across training, evaluation and inference.
- Evaluate exact span and token-level F1; do not report only token accuracy.

### Aspect sentiment

Primary model: compact Transformer classifier conditioned on the target aspect.

- Provide the review and aspect as model input.
- Start with micro-batch 4 and sequence length 128.
- Evaluate per-aspect and per-class macro-F1.

### Theme classification

Primary model: DistilBERT or MiniLM multi-label classifier.

- Use a controlled theme taxonomy.
- Train with multi-label targets.
- Tune thresholds on the validation set.
- Report per-theme precision, recall and F1.

### Embeddings

Primary model: `all-MiniLM-L6-v2` or another compact Sentence Transformers checkpoint after license and model-card review.

- Generate embeddings in batches.
- Persist embeddings rather than recomputing them for every page request.
- Store vectors in pgvector for local semantic retrieval.

### Summarization

Primary strategy: hierarchical summarization with a compact model such as T5-small or FLAN-T5-small, after checking its license and actual local memory usage.

- First group and summarize reviews by sentiment and aspect.
- Use short chunks rather than concatenating all reviews into one prompt.
- Run inference in small batches.
- Fine-tune only if a suitable permitted summary dataset exists and the memory test succeeds.
- Do not attempt BART-large fine-tuning on this 8 GB GPU as the default project plan.
- Keep evidence references and factuality checks around generated summaries.

### Fake-review detection

Start with duplicate detection, TF-IDF similarity, Logistic Regression where labels exist, and CPU anomaly detection. This component does not need to consume GPU memory by default.

### Recommendation

Train Spark MLlib ALS in local CPU mode. Generate content embeddings on the GPU in a separate Python stage. Keep ALS training separate from Transformer training.

## 32.7 System RAM and Spark constraints

With 16 GB system RAM, do not run all heavy workloads simultaneously.

Recommended operating modes:

**Mode A — Model training**
- Run one training notebook or script.
- Close unused browser tabs and heavy IDE windows.
- Do not run a large Spark job at the same time.
- Keep PostgreSQL stopped unless required for the experiment.

**Mode B — Spark processing**
- Run Spark local mode with a controlled number of threads, initially `local[4]`.
- Start with a driver memory target around 3–4 GB and adjust based on observed system memory.
- Start with a modest shuffle partition count such as 8–16 for a laptop-scale local job, then tune from Spark UI evidence.
- Avoid caching every DataFrame.
- Write intermediate outputs to Parquet and process incrementally.
- Never collect the full MovieLens dataset to the driver.
- Run Spark jobs separately from GPU training.

**Mode C — Evaluation / localhost demo**
- Stop training jobs.
- Start PostgreSQL, FastAPI and the frontend.
- Load only the models needed for the demo.
- Prefer lazy model loading and controlled inference batches.
- Do not start Spark unless the evaluator specifically needs to see a Spark job or Spark UI.

Spark's local mode is explicitly supported by the Spark documentation. The selected Spark 4.3 release supports Java 17/21/25, Scala 2.13 and Python 3.11+. See https://spark.apache.org/docs/latest/.

## 32.8 Local application resource policy

The evaluation application must run locally without depending on an external AI inference API.

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- JupyterLab: `http://localhost:8888` when explicitly started
- Spark UI: `http://localhost:4040` while a Spark application is active

Before evaluation:

1. Train and evaluate models in advance.
2. Save approved model checkpoints locally.
3. Preload permitted movie metadata and artwork into the local database/cache.
4. Stop all training processes.
5. Start PostgreSQL, backend and frontend.
6. Load only the inference models required for the current application session.
7. Test the full user journey without internet access, except where an explicitly optional external resource is being demonstrated.

A local movie catalogue and cached artwork should be sufficient for the core demonstration. The website must not fail if TMDB or another external metadata service is unreachable during evaluation.

## 32.9 Storage management

At least 100 GB free SSD space is a workable starting point, but maintain a reserve of at least 20 GB for Windows, temporary files, package caches and model checkpoints.

Recommended storage rules:

- Keep original datasets under `data/raw/` and never overwrite them.
- Keep processed Parquet datasets under `data/processed/` or the medallion directories.
- Keep model checkpoints under `models/`.
- Use one project virtual environment unless dependency conflicts require a separate environment.
- Set a known Hugging Face cache directory under the project drive or a dedicated cache directory.
- Avoid duplicate copies of the same large dataset.
- Do not commit datasets, model weights, `.venv`, `node_modules`, cache directories or `.env` files to Git.
- Record dataset versions and checksums in dataset cards.

## 32.10 Laptop operating practices

- Connect the laptop to its AC adapter during training.
- Use the manufacturer's performance mode only if temperatures remain safe.
- Keep air intakes and exhaust vents unobstructed.
- Monitor CPU/GPU temperatures and throttling.
- Do not disable Windows pagefile; allow Windows to manage it or configure it deliberately.
- Avoid long-duration GPU training while simultaneously running the local web application.
- Save checkpoints to SSD and verify that checkpoint resume works.

## 32.11 Hardware-specific acceptance tests

Before beginning model development, complete these tests:

- [ ] `nvidia-smi` detects the RTX 5050 Laptop GPU.
- [ ] PyTorch imports successfully in the project virtual environment.
- [ ] `torch.cuda.is_available()` returns `True`.
- [ ] PyTorch reports the expected GPU device name.
- [ ] A CUDA tensor operation completes successfully.
- [ ] GPU memory reporting is plausible for the installed 8 GB GPU.
- [ ] A small DistilBERT forward pass completes on CUDA.
- [ ] A short training smoke test completes and saves a checkpoint.
- [ ] A checkpoint can be reloaded for inference.
- [ ] A small Spark Scala job runs using the pinned JDK and Scala versions.
- [ ] PostgreSQL, FastAPI and frontend can run locally after training processes are stopped.
- [ ] The complete movie demo works using locally cached model and metadata artifacts.

## 32.12 Final hardware-specific decision

The project remains fully feasible on this laptop if the implementation follows a resource-aware workflow:

1. Train compact Transformer models one at a time on the RTX 5050.
2. Use mixed precision and gradient accumulation where supported.
3. Keep Spark MLlib and data engineering as separate CPU-oriented jobs.
4. Persist model checkpoints, embeddings and Spark outputs.
5. Stop training before starting the full localhost evaluation stack.
6. Load only the inference models needed for each application session.

The project does not require a paid cloud GPU for its core academic implementation. A cloud GPU may be an optional acceleration path, but the primary training and demonstration workflow must remain reproducible on the local laptop.
