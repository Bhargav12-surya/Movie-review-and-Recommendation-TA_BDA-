# Current source architecture and ER diagrams

Prepared 10 November 2026, Asia/Calcutta. These diagrams describe inspected
source, not a deployed system. The root [architecture](../../ARCHITECTURE.md)
and latest [status](../../IMPLEMENTATION_STATUS.md) remain authoritative. The
original architecture contains illustrative schemas; this ER diagram uses the
actual20 ORM entities in `backend/app/models/entities.py`.

## Components and trust boundaries

```mermaid
flowchart TB
    U[Browser: Next.js localhost3000] -->|HTTP API; memory bearer session| A[FastAPI localhost8000]
    A --> AUTH[Argon2 authentication / UUID ownership]
    A --> D[(PostgreSQL localhost5432 + pgvector)]
    A -->|transactional saved pending review + jobs| D
    W[One leased local worker] -->|claim / retry / revision check| D
    W --> N[Approved local sentiment / aspect extraction / aspect polarity / theme mentions]
    W --> S[Eligible snapshot / scoring / evidence summary]
    W --> C[Grounded discovery routing]
    C --> D
    A --> R[Actual hybrid channels and reviewed factor maps]
    R --> D
    W -->|durable text-free outbox| E[Atomic review JSONL files]
    E --> B[Independent Scala Structured Streaming]
    ML[User-supplied raw MovieLens] --> ETL[Scala ingestion / cleaning / RDD / DataFrame / SQL]
    ETL --> P[Versioned Parquet and quality reports]
    P --> ALS[Spark MLlib temporal ALS / evaluation / factor export]
    ALS --> R
    U -->|user microphone action; bounded audio| V[Authenticated optional offline CPU STT]
    V --> A
    H[Approved local checkpoints / hashes / language scope] --> N
    H --> S
```

No cloud AI service, external broker or automatic dataset/model downloader is a
core dependency. The API/worker do not treat reviews as instructions. Exact
metadata filters use SQL; compatible vectors use pgvector; quoted evidence and
audience scores retain current revisions. All actual data/artifacts still need
their permission and runtime acceptance gates.

## Review lifecycle

```mermaid
sequenceDiagram
    actor User
    participant UI as Next.js
    participant API as FastAPI
    participant DB as PostgreSQL
    participant W as Single worker
    participant M as Approved local models
    User->>UI: Publish review with purpose choices
    UI->>API: Authenticated POST + Idempotency-Key
    API->>DB: Lock canonical movie; verify idempotency
    API->>DB: Insert original review/revision; invalidate snapshots; enqueue jobs
    API-->>UI: Saved review UUID, revision, pending
    UI->>API: Poll own saved review
    W->>DB: Claim eligible job with durable owner/attempt
    W->>M: Load and run one component at a time
    M-->>W: Actual outputs or explicit unavailable
    W->>DB: Recheck lease/current review revision/model approval
    W->>DB: Persist current predictions and queue refresh/outbox
    W->>DB: Publish eligible score/summary at current evidence version
    API-->>UI: Current saved status and available evidence
    User->>API: Edit/delete/withdraw permission
    API->>DB: Expected-revision/ownership check; invalidate derived evidence
    Note over W,DB: Older in-flight results must not overwrite a newer revision
```

The streaming view is asynchronous and can lag behind the DB while an edited
review is pending. Its source/sink/restart/reconciliation tests must be executed
before a delivery guarantee is asserted. Missing models never create a
hardcoded sentiment or a replacement audience score.

## Actual relational entities

```mermaid
erDiagram
    USERS ||--o{ AUTH_SESSIONS : authenticates
    USERS ||--o{ REVIEWS : owns
    USERS ||--o{ RATINGS : records
    USERS ||--o{ WATCHLISTS : saves
    USERS ||--o| PREFERENCES : configures
    USERS ||--o{ INTERACTIONS : permits
    USERS ||--o{ IDEMPOTENCY : scopes
    USERS ||--o{ CONVERSATIONS : owns
    USERS ||--o{ CHAT_TURNS : requests
    MOVIES ||--o{ EXTERNAL_MOVIE_IDS : identifies
    MOVIES ||--o{ REVIEWS : receives
    MOVIES ||--o{ RATINGS : receives
    MOVIES ||--o{ WATCHLISTS : appears_in
    MOVIES ||--o{ INTERACTIONS : concerns
    MOVIES ||--o{ MOVIE_SCORES : snapshots
    MOVIES ||--o{ MOVIE_SUMMARIES : summarizes
    MOVIES ||--o{ MOVIE_EMBEDDINGS : indexes
    REVIEWS ||--o{ REVIEW_REVISIONS : versions
    REVIEWS ||--o{ PREDICTIONS : analyses
    REVIEWS ||--o{ REVIEW_EMBEDDINGS : indexes
    CONVERSATIONS ||--o{ CHAT_TURNS : contains
    USERS {
        uuid id PK
        string email UK
        string password_hash
        boolean is_admin
    }
    MOVIES {
        bigint id PK
        string title
        jsonb genres
        jsonb features
        integer content_version
        integer evidence_version
    }
    REVIEWS {
        uuid id PK
        uuid user_id FK
        bigint movie_id FK
        integer revision
        string text_sha256
        boolean evidence_permitted
        boolean training_permitted
        boolean moderation_permitted
        string analysis_status
    }
    MODEL_ARTIFACTS {
        uuid id PK
        string component
        string version UK
        string manifest_sha256
        boolean approved
    }
    JOBS {
        uuid id PK
        string dedupe_key UK
        string kind
        jsonb payload
        string status
        integer attempts
        string locked_by
    }
```

The diagram abbreviates fields rather than reproducing the migration. Registry
versions in prediction/vector payloads are logical version references, not
fabricated relational foreign keys. Jobs store typed payload identities rather
than a relational edge for every job kind. Current genres/keywords/features are
JSONB on movies; no separate `genres`/`movie_genres` ORM tables are claimed.
The frozen SQL and models are the source of truth for constraints, indexes,
cascades, nullable values and vector dimensions.

## Data and measurement lineage

`raw source hash → approved canonical registry/permissions → frozen splits or
event snapshot → exact config/model/tokenizer hashes → genuine evaluation or
prediction report → reviewed policy/snapshot → API/UI → measured acceptance
record → curated evidence bundle`.

Keep the code revision plus dirty-source hashes. A Git commit alone is
insufficient when the demonstrated workspace contains later edits. Preserve
source-namespace IDs and reject conflicts rather than inventing a canonical map.
See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the freeze record.
