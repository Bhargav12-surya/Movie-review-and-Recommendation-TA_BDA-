# Source and derived data dictionary

## MovieLens 32M

ratings.csv: userId and movieId are positive integer source IDs; rating is
0.5–5.0 in half-star steps; timestamp is integer Unix seconds in UTC.
These are explicit star ratings, not textual sentiment.

movies.csv: movieId is unique; title is source text; genres is a pipe-separated
source list. (no genres listed) represents missing usable genre metadata.
Observed Children and IMAX must not be rejected because prose documentation
uses a different enumeration. Any canonical genre/format mapping is versioned.

tags.csv: userId,movieId,tag,timestamp represent tag applications. Empty or
whitespace-only tags are invalid features; preserve source values and quarantine
separately. Repeated normalized tags with different event timestamps are not
automatically the same event.

links.csv: movieId references source movies; imdbId is an identifier string;
tmdbId is optional. External collisions are mapping-review cases.

## Stanford aclImdb

train/neg and train/pos contain binary-labelled review files. test/neg and
test/pos are the official final test. train/unsup has no supervised labels.
Filename IDs and scores must be consistent with the original source folder.
Text is read as strict UTF-8, never rewritten in raw.

The provided urls_<label>.txt associates zero-based filename IDs with source
IMDb movie pages as documented in the local README. This supports source-level
grouping after validation, not a verified application catalogue mapping.
Do not fit from bundled imdb.vocab/imdbEr.txt or full-corpus precomputed
features without proving train-only provenance; the planned baselines build
their own training-only vocabulary.

Derived review-index records contain source path/split/label, original and
normalized hashes, source movie association, byte/character length and source
mtime. The normalized representation is for duplicate auditing only.

## Reports and manifests

Reports identify schema_version, source, full/sample scope, actual counts,
bounded metadata-only issue samples, completed checks, blockers, input hashes,
timestamps, resources and artifact paths. complete is not permission to train.
partial/missing/invalid states remain explicit.

IMDb train/validation/test reference manifests contain original source paths,
raw hashes, task-specific labels, duplicate/movie group IDs and exclusions.
All valid official test records stay in test. Training groups connected to
test through exact/verified-near/source-movie associations are excluded;
contradictory training labels require exclusion or adjudication.

The near-duplicate method retrieves bottom-k token-trigram hash candidates and
verifies them using exact shingle Jaccard. Its thresholds/candidate caps are
configuration, not validated semantic-equivalence claims. It can miss pairs;
capped searches and unresolved cases remain blockers before training.

## Missing review/annotation/metadata contracts

See schemas/datasets and ANNOTATION_GUIDELINES.md for actual field validation.
Canonical identity approval, consent/license provenance, human sentiment/aspect/
theme labels and gold summaries are not supplied by the benchmark corpora.
