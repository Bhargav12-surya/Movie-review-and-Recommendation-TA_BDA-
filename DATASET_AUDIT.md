# Dataset audit

Latest follow-up,9 November2026 (Asia/Calcutta): the initial audit below is a
historical snapshot. MovieLens and Stanford IMDb were subsequently supplied and
fully audited; see section11 and IMPLEMENTATION_STATUS.md for actual evidence.
The current source-only delivery does not rescan raw data or manufacture missing
review/annotation inputs. Its stop boundary supersedes the initial audit stop.

Audit date: **8 November 2026**, Asia/Calcutta. Scope: Phase 0 inspection of files already in `D:\BDA_TA`. Final availability: **MovieLens 32M was placed locally during the audit and is present with its archive, four CSVs, README and checksums. Stanford IMDb, full TMDB snapshots and research annotations remain absent. Historical demonstration data and model artifacts are also present.**

## 1. Scope, method and limits

The primary specification is the root [ARCHITECTURE.md](ARCHITECTURE.md), especially sections 4–7, 9–11, 21–22 and 32. The user's current instructions override its automatic acquisition examples: **the user downloads datasets manually**. No source was searched, visited, scraped or downloaded for this audit. No package was installed, model trained, prediction generated, or raw data altered.

Inspection used a workspace file inventory, bounded UTF-8 JSON/CSV reads, Python 3.11 standard-library parsing, SHA-256 on local artifacts, ZIP/NPY headers, and SQLite connections opened with `mode=ro` and `PRAGMA query_only=ON`. After MovieLens 32M arrived, its CSVs were scanned sequentially using `csv.reader` and hashed in 4 MiB byte blocks; only bounded identifier sets/counters were retained. No large dataframe or full ratings list/set was loaded. Existing project modules were not imported. The `joblib` artifact was **not deserialized**. NumPy factors were **not loaded**; their shapes/types were inspected from array headers inside the ZIP container.

**SQLite filesystem side effect, detected and cleaned:** although queries were logically read-only, opening these WAL-mode databases created a `cinescope.sqlite3-shm` file (32,768 bytes) and an empty `cinescope.sqlite3-wal` file beside each database. All connections were closed. The root audit verified these four files were absent from the pre-audit baseline, both WAL files were empty, exclusive file handles succeeded, and original database hashes were unchanged; it then removed only these four audit-created bookkeeping files. A final directory listing confirms no sidecars remain. No original file was deleted or edited, and both original `.sqlite3` SHA-256 hashes remain unchanged. Future static snapshot inspection should use SQLite `immutable=1` only after confirming there is no active writer; `mode=ro` alone does not guarantee zero filesystem writes.

The inventory excluded `.git`, virtual environments, package fixtures, bytecode and dependency directories. Scikit-learn/package test fixtures inside `temp/.venv` and `temp/CineScope/.venv` are dependencies, not project research datasets. The initial snapshot had no official raw datasets. **During final verification, a manually placed MovieLens 32M ZIP and extracted files appeared; the current-state findings below supersede that initial absence.** No agent downloaded or extracted the dataset. No `aclImdb` corpus, full TMDB response snapshot, Parquet lake, or annotated training split was found. A historical download manifest is evidence of a past claim, not proof that its referenced archive is present today.

The working tree already contains many tracked deletions and an untracked `temp/` archive. This audit does not restore, delete, move or stage them. Dataset locations below refer to files physically present today, not deleted Git paths.

## 2. Availability against requirements

| Required input | Intended local location | Observed status | Consequence |
|---|---|---|---|
| MovieLens **32M**, original README and terms | `data/raw/movielens/ml-32m/` plus `data/raw/movielens/ml-32m.zip` | Present; four CSVs, README and checksums; all four supplied MD5s match | Suitable for real Scala ingestion/ALS; 124 missing TMDB links and 36 duplicated external TMDB IDs require mapping policy; see section 4A |
| Stanford IMDb binary benchmark | `data/raw/acl_imdb/` | Empty; train/test/unsup text absent | Cannot reproduce binary model benchmark, duplicates, splits or leakage checks |
| Cached permitted TMDB metadata | `data/raw/tmdb_snapshots/` | Empty | Existing curated demo catalogue is not an API response snapshot or a current metadata validation |
| Permitted movie-linked review corpus | `data/raw/licensed_reviews/` | Empty | No licensed audience review collection for movie-level intelligence |
| First-party review export with consent/provenance | `data/raw/first_party_reviews/` | Empty | Four legacy user-tagged rows are not an approved corpus; see section 6 |
| Human sentiment/aspect/theme annotations | `data/raw/manual_annotations/` | Empty | Final three-class sentiment, ABSA and controlled themes cannot be trained/evaluated honestly |
| Gold summary references | Versioned annotations/processed summary set, to be specified in Phase 1 | None | ROUGE/BERTScore against human references cannot yet be measured |
| Deception/moderation ground truth | Approved annotation export, if legitimate labels become available | None | No supervised fake-review accuracy claim is supportable |

The missing inputs do not justify fetching alternative sources. Continue environment, contract and implementation preparation; wait for the user to place inputs in the requested folders.

## 3. Folder structure created during this audit

Only missing directories were created. No placeholder dataset, `.gitkeep`, record, mapping or fabricated annotation was written. All directories were empty of files immediately after creation; MovieLens files were subsequently placed by the user under `raw/movielens/`. Empty directories are not tracked by Git by themselves.

```text
data/
├── raw/
│   ├── movielens/
│   │   └── ml-32m/
│   ├── acl_imdb/
│   ├── tmdb_snapshots/
│   ├── licensed_reviews/
│   ├── manual_annotations/
│   └── first_party_reviews/
├── bronze/
├── silver/
├── gold/
├── processed/
│   ├── sentiment/
│   ├── absa/
│   ├── themes/
│   └── recommendation/
├── exports/
└── dataset_cards/
```

`raw/first_party_reviews/` is a documented addition to architecture section 4.8: a place for user-supplied, permitted first-party exports, separate from third-party licensed reviews and annotations. It changes no storage engine or collection policy.

## 4. Existing local data and artifact inventory

For compactness, **A** means `temp/`; **B** means `temp/CineScope/`; **M** means `temp/CineScope_Midsem/`. Paths are relative to the repository. Both A and B contain the files listed as A/B; this is duplication, not extra observations.

| Relative path under prefix | Prefixes | Bytes per copy | Content |
|---|---|---:|---|
| `data/demo/catalog.json` | A, B | 6,881 | 13 demonstration movie records |
| `data/demo/reviews.json` | A, B | 9,438 | 36 synthetic movie-linked review records |
| `frontend/catalog.json` | A, B | 6,881 | Byte-identical catalogue copy |
| `frontend/reviews.json` | A, B | 9,438 | Byte-identical synthetic review copy |
| `data/taxonomy.json` | A, B | 17,812 | Lexicons, genre/theme terms and eight aspect categories |
| `frontend/taxonomy.json` | A, B | 17,812 | Byte-identical taxonomy copy |
| `data/demo-app/cinescope.sqlite3` | A | 32,768 | 36 synthetic reviews; zero ratings |
| `data/demo-app/cinescope.sqlite3` | B | 32,768 | 36 synthetic + four user-tagged reviews; two ratings |
| `artifacts/aspect_annotation_template.csv` | A, B | 47 | Header only; zero annotations |
| `artifacts/sentiment_tfidf_metrics.json` | A, B | 916 | Historical binary benchmark metrics |
| `artifacts/als_metrics.json` | A, B | 153 | Historical MovieLens-small ALS metrics |
| `artifacts/ranking_metrics.json` | A, B | 773 | Historical ALS/popularity ranking comparison |
| `artifacts/runtime_versions.json` | A, B | 229 | Historical runtime report; not current environment detection |
| `artifacts/notebook_execution.json` | A, B | 1,631 | Historical notebook execution record |
| `models/model-card.json` | A, B | 1,439 | Historical binary sentiment and small ALS card |
| `models/sentiment_tfidf.joblib` | A, B | 4,754,916 | Serialized classifier; only bytes/hash inspected |
| `models/als_factors.npz` | A, B | 830,910 | Exported item factors and IDs; headers inspected |
| `docs/data-provenance.json` | A, B | 503 | Two historical source/download claims |
| `docs/asset-sources.json` | A, B | 10,310 | Existing artwork provenance/usage notes |
| `data/catalog.json` | M | 3,669 | 12 explicitly fictional movies, one synthetic review each |
| `data/aspect_annotations_template.csv` | M | 34 | Header only; zero annotations |
| `data/evaluation_template.json` | M | 207 | Empty evaluation collections, `k=10` |

Also present are existing poster/backdrop/logo files under `A/frontend/assets/` and `B/frontend/assets/`. The manifest refers to **12 posters, one backdrop and one logo**, totaling **1,193,449 bytes per asset set**; all 14 referenced local files exist. These are UI assets, not audience review evidence. The manifest itself says no open reuse license was verified for promotional artwork; public redistribution requires a separate rights/terms review.

### Byte identity and checksums

These SHA-256 values were computed from current local bytes. Matching A/B and frontend hashes demonstrate duplication; they do not validate truth, licenses or origin.

| File family | SHA-256 |
|---|---|
| Demo catalogue: all four JSON copies | `6388fcf8b87e9cdb526f3d3bad28310a819ec5a2a1fd39cd0505eab67fbdcb9d` |
| Synthetic reviews: all four JSON copies | `4efa62dacfaa30a7cc3073daba63e2e443d5d1cd6622f36e0e3f1d0775913cfb` |
| Taxonomy: all four JSON copies | `dfabac1523b7f5a6cbf5c66ab8df42feb1bc7edf1af260bde279b8f7f3044444` |
| A SQLite | `0900051d17f16bb7d4518a062997d48b50a6c238090aa5f53ca2aa5ce3e47505` |
| B SQLite | `e1d6f1b769efe1ff44d8fceecdae8f9633e29b3578b8078dee7e8a3287363301` |
| A/B annotation template | `c78936360b46cc3d5129a5c080c21664f4f9f5903639d814a73437440c791d70` |
| A/B binary sentiment artifact | `aa74f37f611882bea074e64a417990bf080d04486194210c8c048cb8edde65a7` |
| A/B ALS factor artifact | `61cfebe7300543fe137e42e9d3c66319b1d2ea9cf097d6904588c086b14dbb1c` |
| A/B model card | `14ff6f3f9727e125c64ecd70ee1a5ff40b065188070d2a85ab90b67f4750a942` |
| A/B sentiment metrics | `9225c5dbbb1513e08a327285fb83000d6a806cf09c6665d17042f9b9d4811f97` |
| A/B ALS metrics | `b454dcd44c310a35e4c22caed91e7f1d09440feb3b4cf049c180f394440b13c0` |
| A/B ranking metrics | `9413cdca77ae9f8cd5782057c236e7cd21ed7c70a455306919cf482742048075` |
| A/B runtime versions | `41d8c386c1d78a49654ed8cafd74e9084e2ea75df1d7a22f9b71be58043171c2` |
| A/B notebook execution report | `7dfa4c2152632351dfd0cc14a715a3798615ae242f3270e182190b0bce5ae14b` |
| A/B source provenance | `b86ee5a1d3dea8d0e0dafb787fe0665e44dc34bd383e3b0606584497bf02287a` |
| A/B artwork provenance | `99986aadd0bd5f553265212e5256a7a7e73676eb3d68fa2999096408deec215a` |
| M fictional catalogue | `85dc876c0385b8272bda269e6d5f53aa875bd9768c0745ac7094d0e533d39bb9` |
| M annotation template | `439988f546617bcc09aa5cdfcb05b61e0285cf49c0bf3ec7e616c59cb8a8130a` |
| M empty evaluation template | `365bb16319906a782b3a53f4ed61119609895fb593b5144df883afedf82dad8c` |

## 4A. MovieLens 32M — newly supplied local raw dataset

The files appeared during final verification after the initial empty-folder audit. They were inspected in place without downloading, extracting, modifying, preprocessing or training. The ZIP central directory contains the expected `ml-32m/` directory and six files. Extracted sizes match its central-directory sizes. The ZIP payload was not extracted again or independently decompressed/tested end-to-end; the four extracted CSVs match the bundled MD5 manifest.

### Files, source identity and integrity

The supplied README describes release **ml-32m**, generated **13 October 2023**, comprising 32,000,204 ratings, 2,000,072 tag applications, 87,585 movies and 200,948 anonymized users. Full local scans independently confirmed those counts. Source generation date and historical observation period are distinct from the November 2026 local audit date.

| File under `data/raw/movielens/` | Bytes | SHA-256 |
|---|---:|---|
| `ml-32m.zip` | 238,950,008 | `e4a68655d7386b8f95f2f2424b2ff975dfdd15ffd59e0d864a14dca43e99d6ee` |
| `ml-32m/ratings.csv` | 877,076,222 | `91159850e41ee59c86231165a688709647e2726cab2e7ba9faf04001bd5261ee` |
| `ml-32m/tags.csv` | 72,353,890 | `c52e458a89b9deee410f50813e7a64491fbe92a6f07b5c4b58e64c0b3cc95b89` |
| `ml-32m/movies.csv` | 4,242,926 | `b37ca1abc7798de741138ed252b62f69f7e37c84b8a8fab1b82d409b4c6c5cc2` |
| `ml-32m/links.csv` | 1,950,748 | `ef17da7710be76f7d510d5768d1b61826e3af4bf57812b9ca377e4c912123b22` |
| `ml-32m/README.txt` | 9,227 | `aadef501245798f04f085b1edc024bad41343e0f065b5e4682eff38d54e1cb32` |
| `ml-32m/checksums.txt` | 178 | `99ba602a83a00640aa40a5862212de7c16558499b9efced3cc63a470b88e6758` |

The six extracted files occupy **955,633,191 bytes**; ZIP plus extracted files occupy **1,194,583,199 bytes**. All seven files had identical sizes and nanosecond modification timestamps before and after scanning, so no concurrent extraction/change was detected during this inspection. No raw byte was rewritten.

| CSV | Bundled expected MD5 | Local result |
|---|---|---|
| `ratings.csv` | `cf12b74f9ad4b94a011f079e26d4270a` | Match |
| `tags.csv` | `963bf4fa4de6b8901868fddd3eb54567` | Match |
| `movies.csv` | `0df90835c19151f9d819d0822e190797` | Match |
| `links.csv` | `8f033867bcb4e6be8792b21468b4fa6e` | Match |

These comparisons verify local consistency with the supplied README/manifest. They do not authenticate the download channel: an independent official checksum was not fetched, and the user's acquisition/source record remains to be documented in a dataset card.

### Supplied usage terms — correction to the architecture

The local [README.txt](data/raw/movielens/ml-32m/README.txt) permits research use subject to acknowledgement, no implied University/GroupLens endorsement, and the stated conditions. **It explicitly permits redistribution, including transformations, under the same license conditions.** Commercial or revenue-bearing use requires prior permission. Its warranty/liability disclaimers also apply.

Architecture section 4.2's broad statement that GroupLens generally does not permit redistribution is therefore inaccurate for this supplied release. This is a documented proposed correction; `ARCHITECTURE.md` has not been changed. Keeping raw files out of Git remains appropriate for repository size, privacy and controlled provenance, regardless of the conditional redistribution permission.

The README requests citation of F. Maxwell Harper and Joseph A. Konstan, *The MovieLens Datasets: History and Context*, ACM TiiS 5(4), 2015, DOI `10.1145/2827872`. External IMDb/TMDB resources have their own terms; MovieLens permission does not grant a separate artwork or external metadata license.

### Headers, inferred types and actual sample records

All CSVs decoded as UTF-8 and parsed with the expected number of fields on every row. Types below are inferred by complete parsing; a CSV has no native schema.

| File | Header | Validated interpretation |
|---|---|---|
| ratings | `userId,movieId,rating,timestamp` | Positive integer user/movie IDs, numeric half-star rating, integer UTC Unix seconds |
| tags | `userId,movieId,tag,timestamp` | Positive integer user/movie IDs, UTF-8 tag text, integer UTC Unix seconds |
| movies | `movieId,title,genres` | Unique integer movie ID, title text, pipe-separated genre labels |
| links | `movieId,imdbId,tmdbId` | Integer movie ID; external IDs preserved as strings, optional TMDB ID |

Actual first data rows:

```csv
# ratings.csv
1,17,4.0,944249077
# tags.csv
22,26479,Kevin Kline,1583038886
# movies.csv
1,Toy Story (1995),Adventure|Animation|Children|Comedy|Fantasy
# links.csv
1,0114709,862
```

Keep `0114709` as an IMDb identifier string; parsing through floating point or discarding leading zeros would corrupt the source representation. A normalization contract may add `tt`, but it must retain provenance and avoid changing raw values.

### Ratings — complete bounded-memory scan

| Check | Observed result |
|---|---|
| Rows | **32,000,204** |
| Distinct users | **200,948**; IDs 1–200,948 |
| Distinct rated movies | **84,432** |
| Ratings per user | Minimum **20**, maximum **33,332** |
| Missing/whitespace fields | **0** in every column |
| Malformed field counts or numeric parse failures | **0** |
| Nonpositive IDs / orphan movie IDs | **0** |
| Invalid ratings outside 0.5–5.0 in half-star increments | **0** |
| Negative timestamps | **0** |
| Global `(userId,movieId)` order violations | **0** |
| Repeated adjacent `(userId,movieId)` keys | **0** |
| Exact duplicate rating rows | **0**, proved by sorted unique keys |
| Earliest UTC timestamp | `1995-01-09T11:46:44+00:00` (`789652004`) |
| Latest UTC timestamp | `2023-10-13T02:29:07+00:00` (`1697164147`) |

The README describes the ending date as October 12, while the maximum raw timestamp falls on October 13 in UTC. Preserve Unix seconds and document the date boundary rather than rewriting timestamps to match prose. This is not evidence of invalid data.

The full scan took approximately **81.96 seconds** in this audit process, including Python checks/counters. This is a local inspection measurement, not a Spark throughput or distributed speedup claim. An in-progress Windows process sample reported peak working set **54,669,312 bytes** (about 52.1 MiB); it is an observed sample, not a complete benchmark. No full 32M-row list/set or pandas dataframe was created.

| Rating | Exact count |
|---:|---:|
| 0.5 | 525,132 |
| 1.0 | 946,675 |
| 1.5 | 531,063 |
| 2.0 | 2,028,622 |
| 2.5 | 1,685,386 |
| 3.0 | 6,054,990 |
| 3.5 | 4,290,105 |
| 4.0 | 8,367,654 |
| 4.5 | 2,974,000 |
| 5.0 | 4,596,577 |

This is a **rating distribution**, not a sentiment-label distribution. There is no full review text or neutral/positive/negative supervision in ratings.csv. These anonymized dataset users must not be equated with the application's signed-in users.

### Movies and genres — complete scan

All **87,585** movie IDs are unique, with range **1–292,757**. There are zero blank/null titles or genre fields, zero malformed rows, and zero duplicate movie IDs. However, **7,080** records use the semantic missing-value marker **`(no genres listed)`**; a nonblank CSV value is not necessarily usable genre metadata.

Observed genre labels and counts (movies may have multiple labels):

| Genre | Movie count | Genre | Movie count |
|---|---:|---|---:|
| Action | 9,668 | Adventure | 5,402 |
| Animation | 4,617 | Children | 4,520 |
| Comedy | 23,124 | Crime | 6,976 |
| Documentary | 9,363 | Drama | 34,175 |
| Fantasy | 3,851 | Film-Noir | 353 |
| Horror | 8,654 | IMAX | 195 |
| Musical | 1,059 | Mystery | 4,013 |
| Romance | 10,369 | Sci-Fi | 4,907 |
| Thriller | 11,823 | War | 2,325 |
| Western | 1,696 | (no genres listed) | 7,080 |

Actual data contains **`Children`** and **`IMAX`**; the supplied README uses a different children's label and omits IMAX from its enumerated list. Validate against observed values and document canonical genre/format normalization. Do not silently discard IMAX as an invalid row or pretend it is necessarily a narrative genre. Titles may be inconsistent; no external title verification or fuzzy merge was performed.

### Tags — complete scan and bounded duplicate check

There are **2,000,072** tag applications from **15,848** distinct users across **51,323** distinct movies. All tag users occur in the ratings user set; all movie references occur in movies.csv. Every row has four fields and valid parsed IDs/timestamps. No nonpositive ID, negative timestamp, or unknown movie/user reference was found.

There are **six whitespace-only tag strings**, all a single nonbreaking space (`U+00A0`). Other columns have zero missing/whitespace values. Tag lengths span **1–241 characters**. These six rows must be flagged/quarantined or excluded in a separately documented processed copy; the original raw text remains unchanged.

Tags are globally sorted by `(userId,movieId)`, with zero order violations. A second complete streaming pass retained only the current user's movie group (at most **813 distinct rows** in the observed data): **zero exact duplicate tag rows** were found. There are **23 repeated casefolded/whitespace-normalized tag values within the same user/movie pair**. Different timestamps or original spelling can make these distinct applications; their treatment requires an explicit feature/deduplication policy rather than a silent raw deletion. No global semantic/near-duplicate clustering was attempted.

Tag timestamps span `2005-12-24T13:00:10+00:00` to `2023-10-12T23:56:23+00:00`. The first full tag validation pass took about **4.01 seconds**; this is a local CSV audit measurement only.

**3,153 catalogue movies have tags but no rating.** All 87,585 movies occur in at least one of ratings/tags. Those 3,153 items are a real ALS item-cold-start cohort; retain them for metadata/content recommendation and report model coverage rather than silently removing them from every evaluation denominator.

### External movie links — complete scan and conflicts

links.csv has **87,585 unique movie IDs**, exactly covering movies.csv, with no orphan or duplicate internal source IDs. All IMDb IDs are present and digit-formatted; no duplicated IMDb ID was found. **124 TMDB IDs are missing**. Among **87,461 populated TMDB references**, there are **87,425 distinct TMDB IDs**: **36 IDs are each attached to two different MovieLens movies**, affecting **72 source rows**.

These are mapping conflicts to inspect, not permission to merge records automatically. A database `UNIQUE(source, external_id)` constraint will reject a blind one-row-per-source-movie import of these collisions. Preserve original rows and quarantine mapping candidates until the intended canonical movies and approved alias relationships are resolved.

| Duplicated TMDB ID | MovieLens IDs | Duplicated TMDB ID | MovieLens IDs |
|---:|---|---:|---|
| 4912 | 6003, 144606 | 9775 | 34330, 178755 |
| 10991 | 4241, 174533 | 12600 | 5672, 174543 |
| 13020 | 33154, 202599 | 15028 | 5264, 144426 |
| 19666 | 6776, 181751 | 21753 | 145972, 222065 |
| 24487 | 79329, 232217 | 30508 | 66511, 191775 |
| 34696 | 65633, 137813 | 39172 | 93928, 137809 |
| 45555 | 144858, 219145 | 46667 | 110515, 213187 |
| 58451 | 200908, 258991 | 69234 | 31026, 123107 |
| 79782 | 895, 181393 | 84198 | 2679, 103208 |
| 97995 | 70155, 163246 | 132641 | 864, 134006 |
| 133919 | 7396, 272905 | 159898 | 167510, 275753 |
| 264068 | 176543, 266856 | 265189 | 114342, 175813 |
| 298721 | 142861, 162632 | 372631 | 148976, 215011 |
| 411012 | 174527, 215119 | 411081 | 168000, 218855 |
| 412862 | 195339, 208020 | 413765 | 163585, 187127 |
| 521777 | 203218, 258279 | 542757 | 203453, 215891 |
| 566222 | 204294, 229671 | 604196 | 203449, 206117 |
| 642732 | 254100, 258689 | 792517 | 239670, 242100 |

### Suitability and outstanding work

The supplied dataset is suitable for **real Scala/Spark ingestion, RDD/tag exercises, rating/user analytics, temporal ALS experiments, and content/genre feature preparation**. It supplies no full textual reviews, neutral labels, aspect spans, summary references or verified deception labels. The presence of valid MovieLens 32M does not unblock those NLP tasks.

Full exact-row duplicate checks, basic missingness/types/ranges and source-reference checks were completed for these CSVs. Still pending are the approved canonical mapping decisions, temporal train/validation/test manifests, train-only user/genre feature construction, formal dataset card, richer outlier/popularity/time EDA, semantic tag normalization review, local Spark reproducibility and all held-out recommendation experiments. Phase 1 is not complete and no preprocessing/training has started.

## 5. Observed JSON schemas and quality

### A/B demonstration catalogue

All **13 records** contain the same 13 fields:

| Fields | Observed JSON types | Missing/null/empty findings |
|---|---|---|
| `movie_id`, `year`, `runtime` | integer | No missing/null values |
| `title`, `overview`, `source` | string | No missing/null/empty values; all source values are `demo` |
| `genres`, `themes` | array | No missing/null/empty arrays |
| `fictional` | boolean | Present on all records; true for one record |
| `tmdb_id` | integer on 12, null on one | Fictional movie has no TMDB ID |
| `imdb_id` | string on 12, null on one | Fictional movie has no IMDb ID |
| `poster`, `backdrop` | string | One empty poster; 12 empty backdrops |

IDs are unique integers **1–13**. `temp/docs/DATASETS.md` explicitly states that these are **not real MovieLens IDs**. The fictional record is ID 13, **The Last Signal**, with no external identifiers. Years span 1999–2026 and runtimes 89–169 minutes. Populated TMDB IDs and IMDb IDs have no within-file duplicates. No external API validation was attempted; absence of a duplicate does not establish correctness.

A real sample read from the file, shown without treating it as a verified mapping:

```json
{"movie_id":1,"title":"Interstellar","year":2014,"runtime":169,"tmdb_id":157336,"imdb_id":"tt0816692","source":"demo","fictional":false}
```

The sample is a subset of an actual existing demo record. It must never establish an `internal_id=MovieLens_id` relationship. Store external IDs in a source-qualified mapping table after validation.

### A/B synthetic review JSON

There are **36 records**, each with `review_id:string`, `movie_id:integer`, `text:string`, `source:string`, `created_at:string`. Every source is **`synthetic-demo`**. Core fields have no missing/null/empty values. Review IDs are unique; lowercasing and collapsing whitespace found zero exact duplicate texts within one copy. Normalized text lengths range 94–149 characters. Timestamps range `2026-09-10T12:00:00Z` to `2026-09-12T12:00:00Z`.

There are exactly three reviews for each movie ID 1–12, none for fictional ID 13, and zero orphan movie references against the demo catalogue. There are **no human sentiment labels, aspect spans, theme labels, annotator fields, user identifiers, consent versions, moderation labels or split assignments**.

An actual existing synthetic review excerpt is “The family story is heartfelt.” It demonstrates the shape of the authored sample, not a genuine audience view. These records may test contracts in an explicitly identified demo/test environment. They cannot substantiate audience consensus, realistic model metrics, calibrated confidence, genuine spam detection or final acceptance of the integrated application.

Because all four JSON copies match byte-for-byte, concatenating them would create 144 rows containing only 36 unique synthetic reviews. Randomly splitting such a concatenation would introduce duplicate leakage. Keep archival/demo namespaces isolated from research and production inputs.

### M fictional catalogue

`M/data/catalog.json` contains **12 records** with `id:string`, `title:string`, `genres:array`, `reviews:array`, `provenance:string`. All core fields are present and non-null; genre arrays are non-empty. IDs `demo:1` through `demo:12` are unique. Each record contains one review string, for **12 synthetic reviews** in total. Every provenance value is `fictional title and synthetic review; authored for demo`.

An actual first record is `demo:1`, **The Lantern Club**, with Comedy/Drama genres. This is a deliberately fictional title. It supplies no real movie mapping, rating history, audience measurements or human training labels. M's `id` schema differs from A/B's `movie_id` schema and must not be merged implicitly.

### Taxonomy and annotation templates

The taxonomy JSON contains lexical dictionaries plus **eight** aspects: Story, Acting, Visuals, Music, Pacing, Ending, Direction, Dialogue. This is not the architecture's 16-category annotation scheme and is not an independently trained extraction model. Terms such as `script` appear across categories, so lexical matching can overlap; annotations and canonical taxonomy versioning must resolve this explicitly.

The two template formats have zero data rows:

```csv
# A/B, actual header
review_id,movie_id,aspect,text,label,annotator
# M, actual header
review_id,text,aspect,label,split
```

Neither supplies token spans or adjudicated labels. A future contract should include original-text character offsets, review text hash/version, taxonomy version, annotator/adjudication state and split manifest references; do not silently pretend the current templates meet BIO/span-training needs.

## 6. SQLite snapshots and first-party evidence

Both SQLite files passed read-only `PRAGMA quick_check` with `ok`. They contain two tables:

The inventory below describes the final retained snapshots. Temporary SQLite bookkeeping files created during inspection were detected and cleaned as documented in section 1; neither snapshot was changed.

```text
reviews(review_id TEXT PRIMARY KEY, movie_id INTEGER NOT NULL,
        text TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL)
ratings(user_id TEXT NOT NULL, movie_id INTEGER NOT NULL,
        rating REAL NOT NULL CHECK(rating BETWEEN 0.5 AND 5),
        updated_at TEXT NOT NULL, PRIMARY KEY(user_id,movie_id))
```

| Check | A snapshot | B snapshot |
|---|---:|---:|
| Reviews | 36 | 40 |
| `synthetic-demo` reviews | 36 | 36 |
| `user` reviews | 0 | 4 |
| Ratings | 0 | 2 |
| Missing/null/blank review text | 0 | 0 |
| Exact duplicate review texts within DB | 0 | 0 |
| Review IDs/text matching demo JSON | 36 | 36 |
| Orphan references against current demo catalogue | 0 | 0 |
| Declared movie foreign keys | 0 | 0 |

B's four user-tagged review strings are **85, 3, 4 and 22 characters** long. Their text was not reproduced in this report. The snapshot's latest review time is `2026-09-29T04:34:08.719181+00:00`. The records lack consent, reviewer identity, human sentiment/aspect labels, moderation eligibility and validated canonical source mappings. A `source=user` string does not establish that the review is authentic, consented, useful for training or sufficient for audience scoring. Two ratings likewise supply no meaningful collaborative evaluation dataset.

Preserve these snapshots. Do not import them into the final PostgreSQL audience tables or use them for training until their origin, consent, valid movie association and eligibility have been reviewed. A/B hashes differ because they are distinct snapshots; do not discard one as a duplicate without approval.

## 7. Existing artifacts and historical claims

### Sentiment

The existing model card identifies a **binary** TF-IDF 1–2 gram logistic regression model, `C=2.0`, seed 42, scikit-learn 1.7.2, with 19,733 train, 5,046 validation and 24,799 test rows. It describes validation grouping by IMDb movie IDs derived during the historical experiment, and an exact-deduplicated official test subset. Those historical IDs are not current validated MovieLens/TMDB joins.

The saved JSON reports binary test accuracy **0.900520182265414** and macro-F1 **0.9005199726261817**. These values were read from existing files and **not reproduced during this audit**. They are not new project metrics, not an untouched 25,000-row Stanford benchmark, and not evidence of three-class performance. The raw corpus and split manifests needed to validate those claims are unavailable.

The card says runtime probabilities were blended with negation, neutral-cue and mixed-evidence rules to produce **negative/neutral/mixed/positive** labels. This is incompatible with claiming a trained, calibrated three-class positive/negative/neutral model. Preserve the binary artifact as a candidate baseline after provenance/version validation; do not reuse its binary benchmark as the accuracy of the rule overlay or final sentiment service.

### ALS

The model card names **`ml-latest-small`**, Spark **3.5.7**, Scala **2.12.18**, rank 32 and regularization 0.1. This is historical small-dataset work, not a MovieLens 32M result or the requested Scala 2.13 stack.

The NPZ ZIP headers show three members:

| Member | Uncompressed bytes | Header type/shape |
|---|---:|---|
| `movie_ids.npy` | 65,968 | little-endian int64, `(8230,)` |
| `factors.npy` | 1,053,568 | little-endian float32, `(8230,32)` |
| `reg_param.npy` | 136 | little-endian float64 scalar |

Headers confirm that a factor export exists; they do not prove it was trained on the declared split or validate mappings. No complete Spark `ALSModel`, current reversible ID mapping, 32M dataset, or new evaluation was demonstrated here.

Historical metric files report RMSE **0.9528706756413112**, scorable test coverage **0.9072214713265109**, 10,358 test interactions and 80,419 train interactions. At K=10, 573 eligible users and a 100-item ALS candidate cap, saved ALS Recall@10 is **0.010471028210472218** versus train-popularity **0.042303614005534486**. The saved ALS result therefore does not support a superiority claim. Candidate cap, relevance threshold, warm/cold exclusions and all user denominators must be restated in a future reproducible run.

### Untrained or unavailable components

The historical card explicitly lists DistilBERT sentiment, aspect Transformer, supervised fake-review classifier, and semantic/Whisper generation weights as not trained. No final three-class/ABSA/theme checkpoint, calibrated movie score model, summary reference dataset or benchmarked hybrid ranker is available in the project artifacts inspected.

### Provenance and licensing records

`docs/data-provenance.json` records two September 26, 2026 retrieval claims: MovieLens **small** ZIP (978,202 bytes) and Stanford archive (84,125,825 bytes), with URLs and hashes. The archives themselves are absent, so current source integrity cannot be checked against those recorded hashes. No new download was made.

Existing artwork manifests provide URLs and attribution notes but explicitly disclaim a verified open artwork reuse license. No new legal conclusion or license permission is inferred. Dataset/model terms need to accompany manually supplied inputs and be reviewed before use/redistribution; this audit does not research alternative sources.

## 8. Data validity gaps and recommended corrections

1. **Canonical identities:** preserve source-qualified IDs and a distinct internal key; resolve the observed 36 duplicated TMDB mapping groups and 124 missing TMDB links through an approved mapping workflow. Never equate legacy demo IDs with MovieLens IDs. IMDb ID strings retain leading zeros/`tt` normalization by an explicit contract. Missing mappings remain null/quarantined; title/year matching proposes candidates only.
2. **Real three-class supervision:** binary IMDb cannot create neutral labels. Author annotation guidance before labeling, measure overlap agreement, adjudicate mixed-versus-neutral cases and uncertainty, and retain a genuinely held-out movie-/author-/duplicate-aware evaluation set where IDs permit. Do not label every low-confidence prediction neutral.
3. **Aspect training:** collect original-text spans and aspect-conditioned sentiment labels. The current empty templates and eight-category lexicon do not train the required extraction/sentiment architecture. Version the proposed 16 aspects and define implicit aspects, multiword spans and mixed polarity.
4. **First-party collection before UI phases:** use a manually supplied, consented offline export/annotation workflow in Phase 1. Waiting for the Phase 9 backend or Phase 10 frontend would make the prescribed phase sequence circular. The later application imports the same validated contract.
5. **Audience evidence:** synthetic and unapproved legacy rows stay out of audience scores and summaries. Show `Not enough audience reviews yet.` for insufficient eligible real reviews. Thresholds, shrinkage and confidence must be selected on legitimate evidence; 36 authored examples cannot calibrate them.
6. **Theme relevance versus reception:** synopsis/tag themes do not provide theme-specific audience sentiment. Require evidence spans that discuss a theme with evaluated sentiment. Whole-review polarity must not be copied to every theme/aspect.
7. **Risk ground truth:** duplicate/similarity/behavior signals may support a documented anomaly risk calculation. Missing behavior stays unavailable. No deception probability or supervised fake-review metrics without appropriate ground truth.
8. **Reproducible splits:** copied JSON, SQLite seeds, duplicate reviews and revisions must share one deduplication group. Fit TF-IDF, thresholds and recommendation popularity only on training partitions. Keep movie-level and temporal evaluation protocols explicit.
9. **Terms and retention:** first-party training requires permission and a withdrawal/deletion policy; raw research source preservation does not authorize indefinite retention of personal reviews after a valid deletion request. Track approved retention rules separately.

These are proposals to be reviewed with the implementation plan; no existing data, code, mappings or architectural document was changed.

## 9. Phase 1 validation and preprocessing specification — proposed, not implemented

The immediate instruction is inspection only. The following files belong to the first approved implementation phase; they do **not** exist as newly created scripts from this audit.

| Proposed file | Purpose and output |
|---|---|
| `scripts/validate_datasets.py` | Local-only manifest inventory; bounded sample mode and explicit full-scan mode; schema/label/null/duplicate reports; source checksums and audit JSON |
| `scripts/prepare_imdb.py` | Preserve official train/test; deterministic validation within train; text-hash/group leakage audit; write separate processed splits and manifests |
| `scripts/prepare_annotations.py` | Validate consent/provenance, label taxonomy, original-text span offsets, annotator agreement/adjudication; write training copies only |
| `scripts/validate_movie_ids.py` | Validate source uniqueness, one-to-many conflicts, referential integrity, absent IDs and quarantine report; no fabricated/fuzzy auto-merges |
| `scripts/prepare_tmdb_snapshots.py` | Import only user-provided cached files; validate fields, metadata source/date/terms and artwork references; no network requests |
| `data/dataset_cards/<source>.md` | Source/version/rights, retrieval supplied by user, byte counts/hash, field dictionary, exclusions, split policy and limitations |
| `tests/data_quality/` | Small explicitly synthetic fixtures for schema, raw immutability, mapping conflicts, label/span errors, leakage and idempotency |

### Exact input checks once files arrive

| Source | Checks before preprocessing |
|---|---|
| MovieLens ratings | Explicit integer user/movie IDs, rating numeric and allowed range/step, integer Unix seconds, nulls, invalid timestamps, exact duplicate rows, repeated user/movie semantics, orphan movie references; stream/Spark full scans |
| MovieLens movies | `movieId,title,genres`; unique IDs, valid pipe-separated genres, documented `(no genres listed)` handling; title/year is not a definitive ID |
| MovieLens tags | `userId,movieId,tag,timestamp`; nullable/blank tags, encoding, duplicate events, valid references and timestamp handling; tags are not full reviews |
| MovieLens links | `movieId,imdbId,tmdbId`; preserve source IDs without float corruption, leading-zero handling, blank TMDB IDs, duplicate/conflicting assignments and join-coverage report |
| Stanford IMDb | Directory/file-count audit for train/test positive/negative and unlabelled data, label balance, byte encoding, missing text, exact/near duplicates within/across splits, training-only validation; no assumed neutral/movie mapping |
| TMDB cached snapshots | JSON parse validity, source IDs, nullable overview/runtime/date/language/credits/keywords, record timestamp, source terms and attribution, mapped versus unmatched rows |
| First-party reviews | Valid internal `movie_id` after catalogue mapping, review ID/version, reviewer pseudonym if lawful, timestamp, language, moderation, consent/retention, non-empty text, revision hashes, deletion eligibility |
| Annotations | Three-class sentiment policy; per-aspect class/span rules; theme labels versus theme sentiment; annotator/adjudication, allowed values, null/abstain policy, split isolation |

Default audits report **sample estimates as samples**, not exact dataset-wide missingness. Full count/null/range/duplicate checks must scan in chunks or Spark with bounded aggregation. Large text duplicate checks need external/disk-backed hash indexes or Spark; do not retain the entire corpus and embeddings in RAM. Full archive hashing is a streaming pass, not `read_bytes()` on a large dataset.

Preprocessing writes new versioned Parquet/JSONL copies under `silver`, `gold` or `processed` and quarantines malformed records outside `raw`. A manifest links each output to original checksums, schema version, code revision, parameters, timestamps and rejected-row reasons. A Bronze manifest/reference may preserve raw lineage without copying every large byte again. Derived outputs never overwrite originals.

### Tests and acceptance

- Validate empty/missing folders without downloading anything or crashing unrelated audits.
- Reject conflicting external mappings, invalid types/ranges, malformed timestamps, unknown labels and out-of-bounds Unicode spans.
- Verify deterministic split IDs, no duplicate-group overlap, training-only vocabulary/calibration fitting, and unchanged raw checksums.
- Ensure demo/fictional/synthetic sources cannot enter research evaluation or audience aggregates by default.
- Re-run preprocessing to a fresh version and verify deterministic logical rows/idempotent keys; never overwrite the prior run silently.
- Produce exact audit results only for completed full checks; leave unresolved consent/license/mapping checks explicitly pending.

## 10. Completion and approval boundary

- [x] Inventory available project data/artifacts without loading a large dataset.
- [x] Inspect present JSON/CSV schemas, sample records, counts, missingness and exact duplicates.
- [x] Inspect both SQLite snapshots read-only and preserve their differences.
- [x] Separate synthetic/fictional samples, historical metrics and unapproved user-tagged rows.
- [x] Create the required empty dataset folder structure.
- [x] Specify local validation/preprocessing work and dataset blockers.
- [x] Receive and inspect locally supplied MovieLens 32M archive, CSVs, README and checksums; verify all four supplied MD5s.
- [x] Complete streaming MovieLens row counts, field missingness/types/ranges, exact duplicate checks, rating distribution and source-reference coverage.
- [ ] Receive Stanford IMDb, approved metadata snapshots, review/annotation inputs and source/consent provenance records.
- [ ] Resolve the 36 duplicated TMDB mapping groups, retain 124 missing TMDB links explicitly, and define canonical identities without invented joins.
- [ ] Create approved split manifests, expanded EDA and train/test leakage checks; validate the remaining sources when supplied.
- [ ] Collect/adjudicate legitimate three-class/ABSA/theme/summary annotations.
- [ ] Obtain approval for implementation/dependency setup; no preprocessing, training or package installation has begun.

**Stop after the Phase 0 audit documents are reviewed. Dataset acquisition remains the user's responsibility.**

## 11. Executed Phase 1 evidence and Phase 3 input handoff

Reported9 November2026,Asia/Calcutta. These are earlier completed local audit
results, not measurements invented or rerun for file generation:

| Source | Executed evidence | Remaining limitation |
|---|---|---|
| MovieLens32M | Four raw CSV MD5s match;32,000,204ratings,2,000,072tags,87,585movies,200,948rating users |36 duplicated TMDB groups/72 rows,124missingTMDB; no canonical identity approval |
| IMDb |100,000source reviews; supervised train19,521,validation5,328,official test25,000;151excluded training references;50,000unsupervised |Binary only; no app movie mapping or genuine neutral/Hindi/sarcasm labels; source permission review still required |
| First-party/licensed reviews,manual annotations,TMDB snapshots |Last bounded inventory found zero substantive files in those designated source folders |No legitimate movie-linked training/evaluation/audience evidence can be inferred from placeholders |

MovieLens issues include six whitespace-only tags,7,080missing-genre markers
and3,153tag-only movies without ratings. These are explicit cleaning/cold-start
inputs, not reasons to fabricate metadata. Provisional mapping outputs retain
null canonical IDs and quarantine the72 conflicting external relationships.

The IMDb independent verification reported complete reference/hash/coverage
checks and zero retained cross-split group/normalized-text/source-movie overlaps.
The original audit found123exact/normalized labelled cross-split groups and one
source-movie overlap whose training references were excluded. Near-duplicate
search limitations remain documented; zero measured overlap is not a universal
semantic leakage guarantee. Test text was not used to train or tune a model.

Evidence:

- [MovieLens full audit](artifacts/data_quality/movielens-20261108T152814Z-34bd388b/report.json).
- [Provisional mapping outputs](artifacts/data_quality/movie-map-20261108T153013Z-8a93b553/).
- [IMDb full audit and reference manifests](artifacts/data_quality/imdb-20261108-full-fe07af53/).
- [Independent IMDb manifest verification](artifacts/data_quality/imdb-manifest-verification-20261109-bdf9f8fa/manifest_verification.json).

Phase3 source now requires separate train,tuning,calibration,test roles. The
generated scripts/prepare_sentiment_splits.py divides whole groups from the
verified validation references into two fresh files; it has not been executed.
It never reads review text,modifies raw files or changes official train/test.
The supervised loader rejects unsup and requires official labelled path/class
agreement. Training/calibration/evaluation have not occurred in this delivery.

Human domain manifests additionally require approved canonical IDs,adjudicated
real labels,consent/license records and frozen leakage groups. The language
addendum and schema document English/Hindi/Romanized Hindi/Hinglish,sarcasm and
cohort metadata. Unresolved labels/languages stay in annotation review rather
than being silently relabelled. Phase1 acceptance remains partial until its
rights,mapping and annotation conditions are actually met.
