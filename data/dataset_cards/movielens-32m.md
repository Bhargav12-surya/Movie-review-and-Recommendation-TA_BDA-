# MovieLens 32M dataset card

Local release: ml-32m, source README generation date 13 October2023.
Publisher source recorded in the specification: https://grouplens.org/datasets/movielens/.
Actual acquisition URL/date remains owner-supplied provenance, not inferred
from this audit. Original CSV/README/checksum/archive files are preserved.

## Observed data

The executed full validator measured32,000,204 ratings,2,000,072 tags,
87,585 catalogue movies and 200,948 rating users. Ratings cover84,432 movies;
3,153 movies have tags but no ratings. All four local CSV MD5 values match the
supplied release checksum manifest. This is local integrity evidence, not
independent authentication of the acquisition channel.

Zero invalid/orphan rating rows, duplicate rating keys or exact rating rows
were found. Six NBSP-only tags were rejected to a separate metadata log.
There are 7,080 (no genres listed) records,124 missing TMDB references and 36
duplicated TMDB-ID groups affecting 72 source rows. These mapping relations
remain quarantined; original source rows remain intact.

## Intended use and limits

Use ratings for Scala/Spark ingestion, rating/user/genre analytics and later
explicit-feedback ALS. Tags support feature preparation and RDD exercises.
Neither ratings nor tags supplies full movie reviews, neutral sentiment labels,
aspect spans, summary references or authenticity ground truth.

Do not equate anonymized source users with application accounts. The mapping
export preserves movielens:<id> source keys and canonical_movie_id=null.
No canonical movie identity or external conflict resolution is invented.

## Terms and attribution

The supplied README permits research use and conditional redistribution,
including transformations, under the same conditions; acknowledgement and
no implied endorsement are required. Commercial/revenue use needs permission.
External providers' metadata/artwork rights are separate. Keep datasets out of
Git under the project's explicit storage policy.

Requested citation: Harper and Konstan,2015,The MovieLens Datasets: History and
Context,ACM TiiS5(4), DOI https://doi.org/10.1145/2827872.

## Reproducible execution evidence

- Full report: artifacts/data_quality/movielens-20261108T152814Z-34bd388b/report.json
- Rejections: same directory/rejected_rows.jsonl
- Provisional mapping: artifacts/data_quality/movie-map-20261108T153013Z-8a93b553/
- Runtime:73.348 seconds; peak process working set95,907,840 bytes.
- Source timestamps/sizes were stable across inspection.
- Report status invalid/exit2 reflects genuine source-quality issues; it is not
  a failed automated test or fabricated processing failure.

Canonical conflict review, provenance approval, temporal evaluation protocol,
Spark execution and held-out ALS experiments remain pending. No model trained.
