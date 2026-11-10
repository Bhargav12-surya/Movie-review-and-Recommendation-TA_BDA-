# Framewise backend

FastAPI, PostgreSQL/pgvector, explicit authentication/ownership, versioned
reviews, model registry and one durable inference worker. No SQLite fallback,
startup seeding, automatic migration or fabricated prediction is included.

Start from the repository root; imports use the `backend` and shared `ml`,
`scoring`, `recommender`, `discovery` packages. Manually prepare dependencies,
local DB and genuine approved data/artifacts before running.

The full source/contract/manual execution handoff is
[documentation/phases9-11/RUNBOOK.md](../documentation/phases9-11/RUNBOOK.md).
Backend private config is `backend/.env`; `.env.example` contains no password.
API localhost8000, docs `/docs`, routes `/api/v1`; worker is a separate process.

```powershell
.\scripts\setup_database.ps1
# Only after reviewing/authorizing actual migration:
.\scripts\setup_database.ps1 -ExecuteMigration
.\scripts\start_backend.ps1 -Run
# In another terminal:
.\scripts\start_worker.ps1 -Run
```

These commands were not executed. Metadata preflight never installs packages.
The source-only handoff preserves earlier data/runtime gates. Phase12 test
sources are drafts for later manual execution, not evidence of passing behavior.
