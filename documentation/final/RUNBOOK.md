# Final integration and evaluation runbook

Prepared 10 November 2026, Asia/Calcutta. Scope: Phase 9–13 files for later
manual execution. This document is a procedure, not an execution report.
The user requested file generation and will install and execute later.
No training, dependency resolution, migration, server, browser test or
end-to-end inference is established by the presence of these files.

The primary specification is [ARCHITECTURE.md](../../ARCHITECTURE.md).
The fourteen-phase order in [IMPLEMENTATION_PLAN.md](../../IMPLEMENTATION_PLAN.md)
supersedes the older, shorter phase numbering in the original architecture.
Read [IMPLEMENTATION_STATUS.md](../../IMPLEMENTATION_STATUS.md) for observed
evidence and [LIMITATIONS.md](LIMITATIONS.md) for acceptance work still open.

## 1. Resume in dependency order

| Order | Work to execute after authorization | Required evidence before advancing |
|---|---|---|
| 1 | Recheck manually installed tools, disk/RAM, current CUDA and precision support | New environment report for the selected Python interpreter; actual small CUDA operation before GPU training |
| 2 | Close Phase 1 rights, canonical identities and human annotations | Source/consent records, quarantined conflicts, approved canonical registry, frozen split manifests and genuine labels |
| 3 | Recompile final Phase 2 Scala source and execute its small tests/jobs | Current-source compiler/test reports, Parquet smoke, reconciled MovieLens counts, streaming restart/replay/late/conflict/deletion checks and Spark UI evidence |
| 4 | Run Phase 3 classical baselines before the separately approved compact Transformer trial | Comparable tasks/splits, genuine held-out reports, calibration, checkpoint/reload/resume and measured resources |
| 5 | Execute Phases 4–7 in order | Trained extraction/target sentiment, reviewed themes/retrieval, risk limitations and approved evidence/score policies |
| 6 | Execute Phase 8 ALS and hybrid validation | Actual Spark factors/maps, temporal ranking protocol, validation-selected channel weights and cold-start results |
| 7 | Integrate Phase 9 with an isolated PostgreSQL test database first | Migration/constraint/auth/ownership/idempotency/revision/vector tests, then reviewed application database setup |
| 8 | Validate the Phase 10 frontend against that real backend | Type check, production build, browser states, actual API journeys, responsive and keyboard checks |
| 9 | Validate Phase 11 discovery and optional speech | Catalogue entity/constraint/evidence tests, bounded private context, offline cached speech or explicit unavailable state |
| 10 | Execute Phase 12 full integration and failure/offline rehearsal | Saved real journey results, latency/resource measurements, event replay evidence and no fabricated output |
| 11 | Freeze the Phase 13 academic evidence bundle | Report values traceable to actual artifacts, final manifests, permission review and a rehearsed demonstration |

Later source files do not waive earlier data or runtime acceptance gates.
The dependency-based exception permits independent source work; it does not
permit invented reviews, labels, model results or canonical mappings.

## 2. Manual prerequisites and configuration

Use [PREREQUISITES.md](../../PREREQUISITES.md) for official applications,
candidate versions, installation order and verification commands. Preserve a
working installation until an explicit compatibility review justifies a change.
Do not run installers, package resolvers or model/dataset download commands as
part of starting the application. Keep the selected virtual environment separate
from legacy `temp/` projects.

The backend dependency group is referenced by `backend/requirements.txt`.
The frontend manifest is `frontend/package.json`. A lockfile or installed package
directory must be checked against that manifest and the actual resolver output;
its mere presence is not a passed compatibility check. No optional cloud service,
Kafka, container platform or local generative language model is required for the
core local demonstration.

Configure a private `backend/.env` from its example once present. The source
uses individual `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`,
`DATABASE_USER` and `DATABASE_PASSWORD` fields, not the credential-bearing
`DATABASE_URL` illustration in the old architecture. Keep the password out of
shell history, logs, screenshots, Git and frontend variables. The application's
database role needs only the permissions appropriate for runtime queries; use a
separate authorized migration role when extension/schema privileges require it.

The frontend's public configuration contains only its API base, normally
`http://localhost:8000/api/v1`. No database credentials, metadata API token or model
secret belongs in a `NEXT_PUBLIC_` variable. Start development services bound to
loopback. Review CORS if changing either browser origin or port.

Use process-scoped offline settings during serving and rehearsal:

```powershell
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
$env:NEXT_TELEMETRY_DISABLED = '1'
```

These settings do not prove offline operation. The actual rehearsal must use
cached local artifacts and show that no feature requires an external request.
Do not disable the laptop's network automatically or change global settings.

## 3. PostgreSQL, pgvector and genuine catalogue

Have the user create the dedicated database and role through the approved
PostgreSQL installation. Review the frozen initial migration in
`backend/alembic/schema_v1.sql` and back up any existing application database.
The source does not create/seed SQLite at import time and does not run migrations
at startup. A downgrade is destructive and requires its own explicit operation.

After the manual prerequisites, credentials, backup and migration review are
complete, the intended migration entry point from `D:\BDA_TA` is:

```powershell
.\.venv\Scripts\python.exe -B -m alembic -c backend/alembic.ini upgrade head
```

This connects to the configured PostgreSQL database and changes its schema.
It has not been executed for this file-generation delivery. Test clean upgrade,
existing-schema refusal, constraints and extension availability in the disposable
test database before using the demonstration database. Do not point tests at
user-owned application data.

Create a real administrator interactively; there is no default administrator,
shared password or automatic promotion:

```powershell
.\.venv\Scripts\python.exe -B -m backend.manage create-admin --execute
```

Import only user-supplied, permitted metadata linked by the approved canonical
registry. The following placeholders mean real reviewed paths that the user must
supply; they are not bundled data:

```powershell
.\.venv\Scripts\python.exe -B -m backend.manage import-catalogue --input <reviewed-metadata-path> --registry <approved-canonical-registry-path> --execute
```

Replace `<...>` before running. The importer rejects absent rights, unknown
canonical IDs, duplicate input IDs and IDs already present. It does not fetch
TMDB metadata or guess identities. Preserve external ID strings, including IMDb
leading zeros. Catalogue edits and new embeddings require deliberate content
version handling rather than silently overwriting a previously indexed record.

## 4. Approve actual serving artifacts

Use only locally supplied licensed checkpoints and genuine completed experiments.
Training and final-test reports must belong to the exact model/data/code
fingerprints. Keep binary IMDb experiments separate from final three-class
movie sentiment. A language list in configuration does not prove support.

The protected `POST /api/v1/admin/models` endpoint accepts an explicit component,
version, config path, run path, approval-reference path and validated language
scope. Its evidence contract requires:

- An actual `model_manifest.json` matching the requested component.
- A matching actual held-out evaluation, identified by path and SHA256.
- An explicit serving decision bound to the manifest/report hashes and a named
  reviewer. Example forms remain unapproved until real review.
- Genuine three-class labels for the application sentiment components. A binary
  model plus a neutral overlay is rejected as a substitute.
- Reviewed local asset permissions and actual retrieval evaluation for a
  pretrained embedding component. Describe it as pretrained inference unless
  local fine-tuning actually occurred.

Register only measured language scopes. Review the returned active version and
run one real inference through the worker before claiming integration. A
manifest hash check does not establish model accuracy, calibration or safety by
itself. Missing artifacts must produce pending/unavailable states.

Generate catalogue vectors only after the actual embedding model/config/version
is approved:

```powershell
.\.venv\Scripts\python.exe -B -m backend.manage embed-catalogue --config <approved-embedding-config> --model-version <registered-version> --execute
```

This performs actual local inference and writes vectors in bounded batches. It
is a later explicit execution step, not a static check. Validate stored dimension,
model version, content version and nearest neighbours against actual examples.
The backend uses exact pgvector search initially; an approximate index needs a
measured query-plan/recall tradeoff before adoption.

Configure the reviewed overall scoring policy/approval and separate target
policies. Keep `discovery_minimum_aspect_score` unset until its meaning and
threshold are validated. The sample scoring forms and hybrid weights do not
authorize publication. Actual ALS serving requires verified factor parts and
canonical maps; application user UUIDs never become MovieLens user IDs.

## 5. Start the services only after execution is authorized

Stop training and substantial Spark jobs before the full application stack.
Check that the intended ports are free. The persistent services are PostgreSQL,
one API process, one leased inference worker and one Next.js process.

The underlying commands, run in separate terminals from `D:\BDA_TA`, are:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --no-access-log --no-proxy-headers
.\.venv\Scripts\python.exe -B -m backend.app.workers.main
```

The first line is the API command; the second belongs in a separate terminal.
The generated PowerShell launchers are the preferred way to preserve consistent
local configuration. Use installed frontend dependencies through the launcher;
avoid an `npx` command that could fetch an absent package. The API must not be
started with several workers that each duplicate GPU models.

| Local service | Address | Readiness meaning |
|---|---|---|
| Frontend | http://localhost:3000 | Actual pages render and reach the API |
| Backend | http://localhost:8000 | Liveness only does not prove DB/model readiness |
| API docs | http://localhost:8000/docs | Routes available for inspection; protected routes still need auth |
| PostgreSQL | localhost:5432 | Correct database, schema and pgvector verified |
| JupyterLab, optional | http://localhost:8888 | Start only for a specific authorized experiment |
| Spark UI, while a job is active | http://localhost:4040 | Actual Scala jobs/stages/partitions, not a screenshot presented as a live run |

Check `/api/v1/health` and `/api/v1/ready` separately. Inspect authenticated admin
pipeline status for failed/unavailable jobs and active models. A healthy database
does not imply that sentiment, aspects, speech or hybrid ranking is ready.

## 6. Required integration behavior

A review submission is persisted as pending with a request idempotency key.
The durable worker loads actual local models, publishes only the current review
revision and queues snapshot refresh. The frontend polls actual persisted states.
Editing, deleting or withdrawing evidence permission invalidates current derived
content rather than continuing to display stale scores or summaries.

The PostgreSQL snapshot is the live application view. Text-free event files feed
the separate Spark demonstration. That asynchronous stream can lag while a new
review revision is awaiting analysis. Reconcile the final evidence snapshot,
event IDs and revisions before comparing batch/stream/application values.
Do not claim end-to-end exactly-once semantics without executing the complete
restart/replay/source/sink protocol.

All of the following must be verified later with actual approved artifacts:

- Saved review ownership, idempotency and expected-revision conflicts.
- Genuine sentiment and target-specific aspect results, with model versions.
- Null audience score and exact message, "Not enough audience reviews yet.",
  when reviewed evidence thresholds are unmet.
- Valid score/summary publication only at the current movie evidence version.
- Rating averages, theme relevance, audience reception and personal match scores
  remain distinct.
- Real recommendation input contributions, cold users/items and seen exclusion.
- Grounded title/genre/similarity/comparison/aspect/follow-up discovery.
- Worker/database/model failure recovery without fabricated predictions.
- Review deletion/permission withdrawal reflected in all derived evidence and
  the event replay protocol.

## 7. Tests, measurements and evidence freeze

Follow the Phase 12 test instructions after the manual environment is verified.
Do not execute authored tests merely to turn a documentation checkbox green.
Use an explicitly designated disposable PostgreSQL database. Keep synthetic test
fixtures isolated from audience evidence, training and academic evaluation.
The browser suite must target a user-started real local application; intercepted
mock API responses do not establish full integration.

Record actual results using [EVALUATION_REGISTER.md](EVALUATION_REGISTER.md).
Complete [DEMO_SCRIPT.md](DEMO_SCRIPT.md), including no-data/error cases and a
separate small Spark run. Keep a fresh uniquely named evidence directory for
each run; do not overwrite historical reports. Freeze code hashes, dependency
locks, model/tokenizer hashes, policies, data manifests and candidate sets.
The full report remains a methods-and-results template until those genuine
measurements are attached.
