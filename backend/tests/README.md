# Backend test sources

Prepared 10 November 2026, Asia/Calcutta. These tests have not been executed.
Static parsing is separate from behavioral validation.

From the repository root, after manually installing the reviewed backend packages:

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_contracts -v
.\.venv\Scripts\python.exe -m unittest discovery.tests.test_parser -v
```

The contract suite skips when backend packages are missing. A skipped suite is
not a pass. The parser suite uses only the Python standard library. Password
tests call the actual Argon2 implementation. They load no model or dataset.

The PostgreSQL suite additionally needs a manually installed compatible `httpx`
for FastAPI's TestClient. It uses real PostgreSQL and pgvector, not SQLite. Prepare
an **existing disposable local database** named with an `_test` or `_tests`
suffix. Its owner must have already installed pgvector into `public` and granted
the test role schema-creation rights. Do not use the application database.

Set `RUN_POSTGRES_TESTS=1` and privately supply `MOVIE_TEST_DATABASE_URL` using
the `postgresql+psycopg` driver, a loopback host and that disposable database.
Do not put its value in a checked-in script or a test report. Then run:

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_postgres_api -v
```

Each test starts an outer transaction, creates a unique `movie_test_<uuid>`
schema and applies the frozen SQL there, excluding `CREATE EXTENSION`.
Application sessions use savepoints, so their commits never commit the outer
transaction. Cleanup rolls back the outer transaction, including the new schema.
No existing schema is migrated, cleared or dropped. These tests must run
sequentially and never start the inference worker against the test database.
Invented account/movie/review fixtures remain inside the test transaction.

Coverage includes genuine opaque-session authorization, cross-owner rejection,
idempotent replay and conflicts, missing predictions, revision conflicts,
snapshot invalidation, durable jobs, text scrubbing/deletion events, PostgreSQL
constraints and private chat ownership. Scores and model outputs are not
fabricated. Authenticated request tests use actual token hashes; password
verification is covered independently.

Further acceptance still requires two-connection contention tests, worker crash
recovery, lost advisory-lock behavior, concurrent review changes during actual
inference, approved model promotion/revocation, genuine score-refresh parity,
Spark replay/reordering and a real browser journey with approved artifacts.
An authored test file or an opt-in skip does not establish those results.

## Phase12 generated additions

The latest source batch adds fixtures.py,test_runtime_guards.py and
test_postgres_concurrency.py. The runtime-guard suite uses the actual
ModelRuntime with an empty registry,so unavailable outputs are genuine and no
sentiment prediction is mocked. It covers current vector/snapshot gates,
auth/session expiry,summary withholding,consent/revision/deletion,lease/cancel,
bounded context,attempt limits,queue dedupe/reserved child capacity and drain
ordering. These tests were authored,not run.

The two-connection suite additionally requires RUN_POSTGRES_CONCURRENCY=1.
Its separate CommittedPostgresSandbox commits only its new random owned schema
and drops only that schema on exit. Existing application schemas are never
cleared. Review the harness before enabling this explicit database-write mode.
Both isolated fixtures and private settings remain separate from application
data; the fixtures patch settings across all accessed routes.

Use scripts/evaluate_all.ps1 -Groups postgres -Execute for the full selected DB
suite after setting both opt-ins and privately supplying the disposable URL.
Without the concurrency opt-in,the suite is incomplete rather than passing all
DB acceptance. The curated runner suppresses exception messages/private inputs.
httpx0.28.1 is the manual test-only candidate in requirements/requirements-integration.txt.
