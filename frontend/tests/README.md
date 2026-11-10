# Local browser acceptance sources

Prepared 10 November 2026, Asia/Calcutta. Not executed. Playwright never starts
the application. These tests never mock model predictions; some deliberately
abort transport requests or block external origins to exercise error/offline
paths against the real local application.

Manually install the pinned frontend dependencies and an approved Playwright
Chromium browser first. Start PostgreSQL, API, worker and frontend independently
using the runbook. `RUN_LOCAL_E2E=1` enables checks against `localhost:3000` and
`localhost:8000`. Set `E2E_MOVIE_ID` to an actual validated internal movie ID.
From `frontend`, run the already-installed local Playwright runner:

```powershell
.\node_modules\.bin\playwright.cmd test
```

Without explicit opt-in, tests are skipped rather than silently starting services.
Use a disposable evaluation account and a licensed, genuine review only if
enabling the optional write journey with `RUN_REVIEW_E2E=1`. Privately set
`E2E_EMAIL`, `E2E_PASSWORD`, `E2E_REVIEW_TEXT`. Neither account credentials nor
review text belong in source, command history, reports or traces. Browser traces,
video and screenshots are off because they can capture private content. Keep
console output private as test failures can contain page text. Delete the
created review through the account profile after the run; its ID is recorded as
an annotation. No database reset is performed.

`E2E_REQUIRE_MODELS=1` additionally requires actual worker analysis to complete;
it must fail when approved artifacts are absent. Leaving that flag unset tests
submission/persistence only, and cannot establish integrated NLP acceptance.

The journey covers both desktop and mobile viewports. It does not establish
speech accuracy, no-network operation, cross-browser accessibility, calibrated
scores, recommendation quality, full evidence-grounding or concurrent ownership
behavior. Record those as separate measured acceptance results.

Phase12 adds journeys.spec.ts and reporter.ts. Use the curated reporter through
scripts/evaluate_all.ps1 -Groups browser -Execute -AllowBrowser after explicit
RUN_LOCAL_E2E=1 and any additional test-specific opt-ins. Inspect each scenario:
disabled auth/write/chat/speech cohorts remain skipped,so complete browser
acceptance is incomplete. No server/browser download/installer is auto-started.
