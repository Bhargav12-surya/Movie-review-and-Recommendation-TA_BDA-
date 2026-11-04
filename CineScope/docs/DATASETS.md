# Data contracts and sources

Verified official references during development, 26 September 2026. Review the source terms for your intended use; this package includes code, synthetic review text and an attributed UI sample, not copies of the full external datasets.

| Source | Actual role | Important boundary | Official reference |
|---|---|---|---|
| MovieLens small / 32M | User–movie ratings, genres, tags, cross-source links | No full review text; reviewers cannot be linked to IMDb/TMDB users | https://grouplens.org/datasets/movielens/ and https://files.grouplens.org/datasets/movielens/ml-32m-README.html |
| Stanford Large Movie Review Dataset (aclImdb) | Binary sentiment training; official 25k train / 25k test polarized reviews | Does not label neutral sentiment, aspects, themes or fake reviews; older/domain-specific distribution | https://ai.stanford.edu/~amaas/data/sentiment/ |
| IMDb noncommercial TSVs | Title identifiers, metadata and aggregate ratings | TSV metadata is not a downloadable full-review corpus | https://developer.imdb.com/non-commercial-datasets/ |
| TMDB | Movie metadata, keywords, posters, linked review API | API credential, attribution and usage terms required; review availability is sparse | https://developer.themoviedb.org/docs/getting-started and https://developer.themoviedb.org/docs/faq |

The MovieLens research license includes conditions and does not automatically grant unrestricted redistribution. Consult its README. TMDB's developer API is intended for noncommercial use under its terms; commercial use requires appropriate arrangements. The app includes the approved TMDB logo and notice in Credits. Poster/backdrop copyright belongs to the respective rights holders; no open image license is asserted. Exact image URLs/source pages are recorded in `asset-sources.json`.

## IDs and schemas

Canonical `movie_id` is an integer in the currently selected catalog. A real catalog uses MovieLens `movieId`. The sample IDs 1–13 are **not real MovieLens IDs**. Avoid loading demo and real records into the same database.

Canonical movie JSON:

```json
{
  "movie_id": 109487,
  "title": "Interstellar",
  "year": 2014,
  "runtime": 169,
  "genres": ["Sci-Fi", "Drama"],
  "themes": ["Space", "Family"],
  "overview": "Project-authored or appropriately sourced synopsis",
  "imdb_id": "tt0816692",
  "tmdb_id": 157336,
  "poster": "",
  "backdrop": "",
  "source": "movielens+tmdb",
  "fictional": false
}
```

Historical review JSONL: one object per line with `review_id` (source-prefixed), `movie_id`, `text`, `source`, `created_at` (ISO 8601); optional provenance fields include `source_url`. `ingest_reviews.py` skips unknown movie IDs and empties and uses `INSERT OR IGNORE` on review ID, so reruns do not multiply records.

MovieLens ratings: `userId,movieId,rating,timestamp`; scale 0.5–5, Unix timestamp. Explicit star ratings are used by ALS. User history in the live app uses its own local user IDs and folds ratings into learned item factors; it does not claim that a local person is one of the original dataset users.

## New titles

Add a metadata record with a fresh integer `movie_id` that does not collide with existing IDs. Do not create fake ratings or reviews. Themes may come from keywords, reviewed taxonomy matches, or annotated classifiers. The content path can recommend the new title before any ALS factor exists. The summary states that no eligible reviews are available, and aspect scores remain null.

## Review quality and consent

Use dataset terms and authorized APIs; this project does not scrape authenticated IMDb pages. Source text may contain identifying information; use pseudonymous IDs and avoid unnecessary author details. Synthetic sample reviews are explicitly marked `synthetic-demo`. Training flags are audit signals, not fraud labels. Do not silently auto-label positive reviews as genuine or critical reviews as fake.

## Reproducibility

Archive downloads record SHA-256, original URL, retrieval time and bytes. For published experiments pin data snapshots/model revisions and retain requirements, random seed, hardware and split manifests. Never use review text from test to fit vocabulary, IDF, thresholds or summary evaluation references.
