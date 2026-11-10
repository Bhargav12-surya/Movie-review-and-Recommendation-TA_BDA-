# Framewise frontend

Next.js/React/TypeScript/Tailwind and Recharts. Pages call the real backend for
catalogue, reviews, audience scores, profile, watchlist, recommendations and
grounded text/voice discovery. Missing data/models are shown explicitly.

See [the through-11 runbook](../documentation/phases9-11/RUNBOOK.md) before
starting. `frontend/.env.example` documents the public API base; keep passwords,
private model paths and admin tokens out of frontend configuration. Auth sessions
are held in React memory; refreshing requires sign-in again. Cached posters are
served by the backend; artwork is never automatically downloaded.

Node24.22.2 and an operator-installed package-lock/node_modules were observed.
The installed TypeScript compiler may be run directly without network resolution:

```powershell
# From D:\BDA_TA:
node frontend/node_modules/typescript/bin/tsc --project frontend/tsconfig.json --noEmit --incremental false
.\scripts\start_frontend.ps1 -Run
```

Startup is a later operator action. A production build must be manually produced
before `start_frontend.ps1 -Production -Run`; the script never builds or installs.
The API/DB/worker must separately be ready for intelligent features. The AI/evidence
summary is above individual reviews. Browser/visual/accessibility/offline tests
and Phase12/13 acceptance are deferred; source type checking is a narrower check.
