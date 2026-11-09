# Phase 1 local validation runbook

Use the existing root Python 3.11 virtual environment. No installation or
dataset/model download is performed by these commands. Run from D:\BDA_TA.

## Current tests and environment

~~~powershell
.\scripts\verify_environment.ps1 -Profile Data -Json
.\.venv\Scripts\python.exe -I -B -m unittest discover -s tests -v
~~~

Current validation uses only the standard library. The optional pytest runner
is not required. A Data profile pass certifies this scope, not CUDA/Spark or the
complete application.

## Inventory, MovieLens and mapping

Each output path must be new and outside data/raw,temp,.git and environments.
Replace NEW_* names for a new run; existing files/directories are never overwritten.

~~~powershell
.\.venv\Scripts\python.exe -I -B scripts\validate_datasets.py --kind inventory --output artifacts\data_quality\NEW_INVENTORY.json
.\.venv\Scripts\python.exe -I -B scripts\audit_movielens.py --source data\raw\movielens\ml-32m --output artifacts\data_quality\NEW_MOVIELENS
.\.venv\Scripts\python.exe -I -B scripts\build_movie_id_map.py --source data\raw\movielens\ml-32m --output artifacts\data_quality\NEW_MAPPING
~~~

The provided source currently returns quality issues for six blank tags and
36 TMDB conflict groups. The mapping stays provisional; application IDs are null.
Invalid/partial data status is distinct from a failed automated test.

## IMDb text, duplicate and split audit

The complete near-duplicate scan is a substantial read-only data operation;
the recorded run took about28.5 minutes. It has a resource preflight and bounded
memory. It does not train or download a model.

~~~powershell
.\.venv\Scripts\python.exe -I -B scripts\audit_imdb.py --source data\raw\acl_imdb --near-duplicates --output artifacts\data_quality\NEW_IMDB_AUDIT
.\.venv\Scripts\python.exe -I -B scripts\prepare_imdb.py --source data\raw\acl_imdb --output artifacts\data_quality\NEW_IMDB_SPLITS
.\.venv\Scripts\python.exe -I -B scripts\validate_imdb_manifests.py --run artifacts\data_quality\NEW_IMDB_SPLITS --output artifacts\data_quality\NEW_MANIFEST_VERIFICATION
~~~

prepare_imdb runs the audit itself; do not run both full commands merely to
repeat the same scan. Use audit_imdb alone when only inspection is needed.
The independent manifest checker requires a completed static audit/split run.
It reads reference metadata, not every review again.

The original test remains intact. Train/validation reference manifests group
exact/verified-near/source-movie relationships and exclude connected training
records. Unlabelled IMDb reviews remain unlabelled. No neutral or canonical
application movie mapping is invented.

## Review, annotation and cached metadata inputs

~~~powershell
.\.venv\Scripts\python.exe -I -B scripts\preprocess_reviews.py
.\.venv\Scripts\python.exe -I -B scripts\prepare_annotations.py
.\.venv\Scripts\python.exe -I -B scripts\prepare_tmdb_snapshots.py
~~~

These currently return missing status. When inputs arrive, inspect each command's
--help and provide the approved registry/provenance and a new explicit output.
Exporting accepted original-text copies requires --write-accepted. Annotation
offsets reference the original Unicode text; mixed labels require an explicitly
approved policy. No restricted website/API is contacted.

## Exit codes and evidence

0 means the requested validation completed cleanly;2 indicates invalid data or
configuration;3 means missing input;4 means partial/blocked work. Inspect the
JSON report rather than treating any nonzero data-quality code as a test failure.
PowerShell wrappers/native process exit propagation may require inspecting
$LASTEXITCODE; the report's own exit/status field remains explicit.

Full results, class support, limits, preservation checks and current blockers
are recorded in IMPLEMENTATION_STATUS.md. Source provenance,canonical mappings,
human labels and Phase 2 prerequisites remain required gates.
