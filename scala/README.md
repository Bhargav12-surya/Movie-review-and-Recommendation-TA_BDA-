# Scala/Spark BDA pipeline

Phase 2 source targets Spark 4.3.0, Scala 2.13.18, SBT 1.10.7 and the selected
JDK 21. It independently processes local MovieLens data in Scala. Python only
checks prerequisites and launches an already built JAR. No Python ETL is hidden
inside these Scala classes.

Current validation: dependency-free configuration checks compile/run using
cached Scala jars; all source syntax can be checked offline. Spark API type
checking, ScalaTest, Parquet jobs and streaming runtime tests require manually
prepared dependencies. Source presence does not establish a working Spark job.

| File/group | Responsibility |
|---|---|
| Main.scala | Strict CLI, localhost session, job dispatch, event logs/run reports |
| config | Explicit schemas, bounded arguments, protected input/output paths |
| ingestion/MovieLensIngestion | Header validation, CSV to Bronze Parquet |
| cleaning/DataCleaning | Types/ranges, referential integrity, duplicate and external-link quarantine |
| transformations/DataFrameTransformations | Source-key joins, features, actual typed Dataset operations |
| transformations/RddExamples | Functional helpers, map/filter/flatMap/reduceByKey, bounded groupByKey, caching and DAG |
| analytics | Actual movie/user/genre/tag/star-rating aggregates and Spark SQL |
| recommendation/AlsTraining | Real MLlib estimator/input/export contract; no automatic fitting |
| ingestion/ReviewIngestion | Analysis event validation and rejection reasons |
| streaming/ReviewStreamJob | Versioned immutable snapshots, replay handling, revisions and deletion |
| io | Fresh-only Spark outputs and metadata serialization |

See [the runbook](../documentation/bda/RUNBOOK.md) for manual preparation,
commands, output contracts, acceptance tests, limitations and recovery rules.
Substantive ALS fitting/tuning/ranking evaluation remains Phase 8 and requires
an approved run; this phase has not trained a recommender.
