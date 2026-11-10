# Through-Phase11 generated-source index

10 November2026,Asia/Calcutta. Runtime acceptance is open; Phases12–13 are
deferred to the user. See RUNBOOK.md for concrete contracts and manual order.

| Area | Source |
|---|---|
| App factory/lifecycle | backend/app/main.py; core/config.py,errors.py,middleware.py; database/session.py |
| Persistence/migration | backend/app/models/entities.py; backend/alembic/schema_v1.sql,env.py,versions/0001_initial.py; backend/alembic.ini |
| Authentication | backend/app/auth/security.py,dependencies.py; schemas/auth.py; api/routes/auth.py |
| API routes | backend/app/api/routes/movies.py,reviews.py,profile.py,recommendations.py,admin.py,chat.py |
| Validated requests | backend/app/schemas/requests.py |
| Repository access/jobs | backend/app/repositories/catalogue.py,jobs.py |
| Review lifecycle | backend/app/services/reviews.py |
| Actual model admission/adapters | backend/app/services/artifacts.py,inference.py; backend/prepare_embedding_artifact.py |
| Scoring/evidence/summary integration | backend/app/services/analytics.py; actual shared scoring and ml/summarization modules |
| Recommendation integration | backend/app/services/recommendations.py; actual recommender modules and Scala factor artifacts |
| Discovery integration | backend/app/services/chat.py; discovery/parser.py,speech.py,README.md |
| Durable worker/outbox | backend/app/workers/main.py; backend/app/services/events.py |
| Manual admin/import/encoding | backend/manage.py |
| Local config/decision examples | backend/.env.example,serving_approval.example.json,retrieval_study.example.json; frontend/.env.example; requirements/requirements-speech.txt |
| Frontend config | frontend/package.json,tsconfig.json,next.config.ts,postcss.config.mjs,next-env.d.ts; user's manual package-lock retained |
| Frontend shared client/state | frontend/lib/api.ts,types.ts,auth.tsx |
| Frontend routes | frontend/app/page.tsx; discover,movies/[movieId],auth,watchlist,recommendations,profile,assistant,about/page.tsx |
| Frontend layouts/states | frontend/app/layout.tsx,globals.css,loading.tsx,error.tsx,not-found.tsx; components/layout/shell.tsx,ui/states.tsx |
| Movie/review/score UI | frontend/components/movie/card.tsx,discover.tsx,rating.tsx; review/composer.tsx,list.tsx,summary.tsx; score/profile.tsx |
| Recommendation/chat UI | frontend/components/recommendation/shelf.tsx; chat/voice.tsx |
| Explicit operational scripts | scripts/_local_services.ps1,start_backend.ps1,start_worker.ps1,start_frontend.ps1,setup_database.ps1,start_all.ps1,stop_all.ps1; existing check_health.ps1 retained |
| Static verifier | scripts/verify_application_sources.py; reports under artifacts/source_validation |
| Handoff | backend/README.md,frontend/README.md; documentation/phases9-11/RUNBOOK.md; root architecture/plan/status/environment/prerequisite updates |

Backend/discovery/frontend test drafts and documentation/final drafts were
prepared before the latest deferral and are preserved unexecuted. They are not
completed Phases12/13 and are not required to claim source preparation through11.
No models,datasets,posters,credentials,training metrics or browser screenshots
were manufactured. Read the latest status report before treating any file as
validated behavior.
