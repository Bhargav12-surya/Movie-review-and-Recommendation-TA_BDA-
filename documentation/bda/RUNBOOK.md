# Phase 2 local Scala/Spark runbook

Updated: 9 November 2026, Asia/Calcutta.

The user approved dependency-based Phase 2 progress while Phase 1 provenance,
canonical registry, reviews and annotations remain unresolved. MovieLens-only
source processing may proceed. It does not approve guessed mappings, NLP
training, downloads, installations or changes to the mandatory stack.

## Actual state

Source implementation and offline checks are available. Spark/SBT and the
project JAR are absent. Therefore ScalaTest, actual Spark compilation, full
MovieLens Parquet outputs, streaming execution, native Windows filesystem
compatibility and Spark UI evidence have NOT passed. Phase 2 remains open.

Manual prerequisites and official links are in [PREREQUISITES.md](../../PREREQUISITES.md).
Do not invoke SBT merely to inspect its version: it can bootstrap and resolve
dependencies. No script in this phase installs or builds anything automatically.

## Manual preparation and execution order

1. User installs/prepares SBT 1.10.7 and the matching Spark 4.3.0 distribution
   with Scala 2.13.18 and the documented Hadoop baseline. Keep the existing
   JDK 21; a second standalone Scala installation is unnecessary.
2. User manually supplies approved build dependencies/cache. Reading this
   document or running preflight does not authorize SBT network resolution.
3. After manual preparation, re-run environment verification. Free enough
   measured RAM for the requested heap plus 1 GiB; retain 20 GiB disk reserve.
4. User explicitly runs the build/test commands below in the selected JDK
   session. Save actual results. Resolve incompatibilities before a 32M run.
5. Run the tiny synthetic Parquet/RDD smoke job. It is transport evidence,
   excluded from training, audience statistics and real evaluation.
6. Run batch ingestion/cleaning/analytics on the local supplied MovieLens CSVs.
   Review quarantine counts and row reconciliation against Phase 1 reports.
7. Execute the synthetic streaming tests and an atomic file-source rehearsal;
   verify replay, restart, conflicting payloads, held revisions and deletion.
8. Save Spark plans, event logs, timings and UI evidence. Mark Phase 2 complete
   only when its checklist passes; then integrate the requested multilingual NLP
   extension and its data/annotation addendum before Phase 3.

### Inspect now, without installing or starting Spark

~~~powershell
Set-Location -LiteralPath 'D:\BDA_TA'
.\scripts\verify_environment.ps1 -Profile Spark -Json
.\scripts\run_spark_jobs.ps1 -Job preflight -Json
.\.venv\Scripts\python.exe -I -B scripts/verify_scala_offline.py
.\scripts\run_spark_jobs.ps1 -Job batch -OutputPath 'data/processed/spark/reviewed-run-001' -DryRun -Json
~~~

The offline verifier uses only the existing exact Scala compiler/library/reflect
cache. It compiles/runs config/path/JSON code and parses all Scala files. It does
not type-check Spark calls or execute ScalaTest. Reports record tool/source hashes.
Preflight/dry-run reports missing prerequisites with exit 2 and executed=false;
that is an expected blocker, not a successful job.

### Build and test only after manual dependency preparation

These are instructions for the user's prepared shell; they have not run here.
JAVA_HOME below changes only that shell, not Windows global configuration.
If the dependencies are absent, stop; do not turn this into an unapproved fetch.

~~~powershell
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
$env:PATH = (Join-Path $env:JAVA_HOME 'bin') + ';' + $env:PATH
Set-Location -LiteralPath 'D:\BDA_TA\scala'
sbt -Dsbt.offline=true 'set offline := true' test package
Set-Location -LiteralPath 'D:\BDA_TA'
~~~

An offline flag cannot bootstrap a missing launcher or guarantee every plugin
avoids a network attempt. Run only after the user has prepared/approved the
toolchain. Build pins are candidate source requirements, not a tested lockfile.
The thin JAR manifest records Spark/Scala versions and contains no Spark jars.

### Actual jobs after readiness checks pass

Replace the SparkHome example with the actual manually installed directory.
Choose a fresh output name each time; do not overwrite failed or prior runs.

~~~powershell
.\scripts\run_spark_jobs.ps1 -Job smoke -SparkHome 'D:\Tools\spark-4.3.0-bin-hadoop3' -DriverMemory 1g -OutputPath 'artifacts/spark-smoke-001' -Json
.\scripts\run_spark_jobs.ps1 -Job batch -SparkHome 'D:\Tools\spark-4.3.0-bin-hadoop3' -DriverMemory 3g -OutputPath 'data/processed/spark/batch-001' -HoldUiSeconds 120 -Json
~~~

For a separate RDD demonstration use Job rdd with a new output. It performs the
same source validation before its tag-word analysis. Default local[2], four
input partitions and eight shuffle partitions are conservative trials. The
launcher refuses unbounded local[*], remote masters, protected/overlapping
paths, incompatible manifests, existing outputs and insufficient resources.
It launches one hidden owned process, logs under artifacts/spark-launcher,
sets JAVA_HOME/SPARK_HOME/PATH/SPARK_LOCAL_IP/SPARK_CONF_DIR only in the child,
and blocks unreviewed injected JVM/resolver options without printing values.
The Spark UI is localhost:4040 while active; port conflicts fail rather than
silently choosing another port. Event logs remain under artifacts/spark-events.

## Batch output contract

Each fresh run directory contains Bronze, Silver, Gold, quarantine and reports.
All writes use error-if-exists. Raw CSVs are never edited, moved or deleted.
Large tables remain distributed DataFrames/Parquet; no full collect or pandas.

Phase1's strict CSV field-count/checksum audit remains required. Spark CSV
PERMISSIVE corrupt-record capture alone does not classify every extra/missing
token as a corrupt row. Re-audit changed/new sources with the Phase1 validator
before this pipeline; header and typed-field checks are additional safeguards.

| Layer | Actual content |
|---|---|
| bronze/{ratings,movies,tags,links} | Raw string fields, corrupt record capture, source/ingestion metadata |
| silver/{ratings,movies,tags,links} | Validated typed source rows; ratings/tags partitioned by UTC event_year |
| quarantine | All invalid/orphan/duplicate source rows and ambiguous external relationships |
| gold/movie_features,rating_features,tag_features | Source movieId joins with cardinality checks |
| gold/movie_rating_profiles | Nullable mean star rating, observed counts, tag-only ALS item cold starts |
| gold/genre_* | Genre star-rating aggregates and catalogue coverage; IMAX kept as a format flag |
| gold/source_user_* | Source-qualified observed rating/genre/tag profiles, never app accounts |
| gold/tag_word_counts | Scala RDD word frequencies; bounded teaching groupByKey sample separate |
| reports | Reconciliation, counts, actual cache timings, plans, RDD DAG and execution metadata |

Every duplicate user/movie rating key is wholly quarantined; no arbitrary
retention. Empty/NBSP-only tags are rejected in processed copies. Missing genres
remain explicit. IMDb IDs retain leading zeros. Duplicated external relationships
are quarantined without deleting the underlying movies/ratings. Canonical IDs
stay null until approved mapping; title matching never supplies an identity.
Multi-genre rating fractions can sum above one and genre totals overlap.
Ratings are not textual reviews, calibrated sentiment or recommendation scores.

Compare real outputs with Phase 1's measured inputs: 32,000,204 ratings,
2,000,072 tags,87,585 movies, six blank tags,124 missing TMDB references and
36 duplicated TMDB groups/72 affected relationships. These are prior raw-audit
observations, not claims that this Scala run reproduced them. Source changes
or a different quality policy require reconciliation, not adjusted constants.

## Streaming contract and limitations

The event contract is [schemas/events/review_event.schema.json](../../schemas/events/review_event.schema.json).
The watched directory contains immutable UTF-8 JSONL analysis events only.
No raw review text or invented predictions are generated. Producer-supplied
canonical/consent/moderation flags are mandatory attestations; real authenticated
DB ownership/provenance enforcement must be connected in Phase 9.

Validate a supplied file without publication; add publish-to only to explicitly
publish the validated copy. This does not perform inference:

~~~powershell
.\.venv\Scripts\python.exe -I -B scripts/publish_review_events.py --input 'data/processed/approved-review-events.jsonl'
.\.venv\Scripts\python.exe -I -B scripts/publish_review_events.py --input 'data/processed/approved-review-events.jsonl' --publish-to 'data/events/review-ready'
.\scripts\run_spark_jobs.ps1 -Job stream -SparkHome 'D:\Tools\spark-4.3.0-bin-hadoop3' -EventInput 'data/events/review-ready' -OutputPath 'data/processed/spark/stream-001' -CheckpointPath 'data/checkpoints/stream-001' -Json
~~~

These paths are instructions, not files populated with mock predictions.
The publisher validates bounded files/lines, flushes a hidden incomplete file,
then atomically renames on the same volume. Failed partials remain dot-prefixed
and must never be renamed manually into the watched set. Synthetic permission
must be explicit at both publisher and stream; synthetic rows never enter real
movie analysis inputs. Already published files are immutable, never edited/reused.

The stream defaults to AvailableNow; Continuous keeps micro-batches running
every five seconds until interrupted. Input, output and checkpoint paths must
be distinct/nonoverlapping. A fresh run requires fresh output/checkpoint paths.
Resume uses the same paths plus Resume and matching retained stream.properties;
committed runs require the original Spark offsets/metadata. Never delete a
checkpoint to restart the same sink. A new source/sink gets a new pair of paths.

Each batch writes a cumulative ledger/current state/eligible state/analysis-input
snapshot and rejection tables under staging, then atomically renames the complete
directory into committed/batch-<id>. One file lock prevents concurrent writers.
An already committed checkpoint batch is replayed without rewriting or recounting.
Sequential batch IDs are enforced. This assumes immutable input files and the
same retained checkpoint: it does not verify a repurposed batch ID's new payload.
No end-to-end exactly-once guarantee is claimed.

Event ID/payload collisions, conflicting immutable review revisions and changed
movie/source identities withhold the entire affected review until explicitly
resolved in a new reviewed run. The highest valid revision controls current
state; a deletion tombstone defeats stale lower revisions. A held/withdrawn
consent or moderation revision removes eligibility. A deliberately higher
approved upsert may reinstate a previously deleted record; authorization belongs
to the future producer. Malformed events are rejected with reasons.

Late valid files/revisions are accepted irrespective of event-time age; revisions
resolve order. The Watermark argument currently records a reporting allowance,
not a bounded-state eviction/drop rule. It does not silently discard late
deletions. Future bounded-state optimization needs its own correctness evidence.

Real analysis inputs are grouped by movie AND model version. They contain counts
and an unadjusted probability-derived review index, without a calibration or
confidence claim. Final audience_sentiment_score stays null with the exact
"Not enough audience reviews yet." message. Phase 7 owns calibrated weighting,
minimum evidence, effective sample size and final score methodology.

This demonstration sink reads/writes cumulative history per batch, bounded to
100,000 unique event payloads and10,000 snapshots. It is not the final scalable
transactional sink. Disk grows with snapshots; after a failure retain staging and
inspect it. Atomic rename is required; no copy/delete fallback exists. Review
rights withdrawal also needs the Phase 9 retention/purge policy; a tombstone
removes active evidence, not historical audit files. Do not claim full privacy
deletion from this local demonstration ledger.

## Acceptance and recovery checklist

- [ ] Exact JDK/Spark/Scala versions and manually prepared dependencies verified.
- [ ] SBT compilation and all ScalaTest contracts actually pass.
- [ ] Synthetic local Parquet/RDD smoke passes on Windows.
- [ ] Full MovieLens batch reconciles raw/accepted/quarantined rows and joins.
- [ ] UTC partitions, original identifiers and missing/ambiguous mappings verified.
- [ ] SQL/DataFrame/Dataset/RDD outputs, caching/unpersist and plans saved.
- [ ] Streaming malformed/synthetic/replay/restart/edit/delete/late/conflict cases pass.
- [ ] Interrupted staging, missing checkpoint and concurrent writer failures tested.
- [ ] Actual Spark UI/event logs/resource metrics captured and interpreted.
- [ ] No raw mutation, fabricated prediction or audience score; source/license gate recorded.
- [ ] Phase 2 evidence reviewed before the mandatory NLP extension and Phase 3.

If a job fails, keep its output/logs and use a fresh run directory for batch.
For stream, retain checkpoint/output together and resume only a compatible run.
Native Hadoop errors need an actual reproduced diagnosis; do not download
unverified winutils binaries. RAM/resource blocks require closing workloads or
an explicitly smaller heap trial, never bypassing the checks silently.

Official references: [Spark quick start](https://spark.apache.org/docs/4.3.0/quick-start.html),
[CSV schema/corrupt-record behavior](https://spark.apache.org/docs/4.3.0/sql-data-sources-csv.html),
[Structured Streaming file/foreachBatch semantics](https://spark.apache.org/docs/4.3.0/streaming/apis-on-dataframes-and-datasets.html),
[Spark UI/event logs](https://spark.apache.org/docs/4.3.0/monitoring.html).
