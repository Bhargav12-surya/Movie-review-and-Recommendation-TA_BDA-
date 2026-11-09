# Movie identity and mapping review

MovieLens movieId, IMDb title IDs, TMDB IDs and application movie IDs have
different namespaces. Identical integers do not establish identity.

The Phase 1 mapping tool preserves every source MovieLens movie and emits a
provisional source key movielens:<id>. canonical_movie_id remains null until
an approved registry/import assigns it. The tool does not invent application
IDs, fetch metadata, infer title matches, or merge movies automatically.

IMDb values are kept as strings, including leading zeros. An explicitly named
normalized tt-prefixed field may accompany the unchanged original value.

The supplied MovieLens links contain 124 missing TMDB IDs and 36 duplicated TMDB
ID groups affecting 72 rows. These relationships are quarantined for review;
source movies and their MovieLens IDs remain intact. Missing IDs stay null.
Do not blindly enforce one source-movie row per external ID or join conflicts
into a multiplying many-to-many result.

For each conflict, inspect the original source rows and permitted user-supplied
metadata. Record the resolution, reviewer, supporting source/hash and timestamp.
Leave uncertain relationships quarantined. Fuzzy title/year comparisons may
produce review candidates, never automatic identity decisions.

MovieLens users are anonymized source users, not application accounts. Keep
separate namespaces and reversible Spark int32 factor maps. Reviews require a
validated application movie ID. The source IMDb URLs used for binary benchmark
grouping are not a validated application/MovieLens/TMDB join.
