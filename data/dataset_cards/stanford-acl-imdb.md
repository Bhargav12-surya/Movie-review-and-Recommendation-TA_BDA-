# Stanford aclImdb dataset card

Local README identifies Large Movie Review Dataset v1.0. Direct layout:
data/raw/acl_imdb/{train,test}, with the original supplied ZIP retained.
Publisher source recorded in the specification:
https://ai.stanford.edu/~amaas/data/sentiment/.
The owner's actual download URL/date and permitted-use record remain pending.

## Observed corpus and labels

The executed validator read 100,000 UTF-8 review files:
12,500 negative and 12,500 positive reviews in each official train/test split,
plus50,000 unlabelled train/unsup reviews. There were no parsing/label/size
errors in that run. Original text was not normalized or overwritten.

This is a binary benchmark. Final binary manifests use negative0/positive1;
unlabelled examples have null labels and are isolated from supervised splits.
There is no neutral label and no validated application movie ID.

The supplied README documents filename-ID-to-URL-line associations.
Validated source URLs support source movie grouping, not a MovieLens/TMDB or
application catalogue join. The actual source associations include one movie
present in both official splits despite the README's general disjointness claim.

## Duplicate and split findings

Across the 100,000 reviews, the audit found1,471 byte-identical duplicate
groups/1,531 redundant rows and 1,477 normalized groups/1,537 redundant rows.
There are 123 labelled train/test duplicate groups. No contradictory exact
normalized label groups were found.

The approximate bottom16 token-trigram candidate procedure compared235 pairs,
verified27 near-duplicate pairs at Jaccard0.9, and found zero verified near pairs
crossing the official train/test boundary. This does not prove all semantic
duplicates are absent. Candidate retrieval was not capped in the executed run.

Connected exact/verified-near/source-movie groups produced reference manifests:

| Manifest | Rows | Negative | Positive |
|---|---:|---:|---:|
| train | 19,521 | 9,825 | 9,696 |
| validation | 5,328 | 2,578 | 2,750 |
| official test | 25,000 | 12,500 | 12,500 |
| excluded from train/validation | 151 | Not a model evaluation set | Not a model evaluation set |
| unsup | 50,000 | Unlabelled | Unlabelled |

All 25,000 official test records remain in test. The 151 training exclusions
remain in raw; their reasons are recorded in excluded.jsonl. Do not fit on the
official test, its vocabulary, or unsupported precomputed full-corpus features.

## Evidence and limitations

The full report and five reference manifests are in
artifacts/data_quality/imdb-20261108-full-fe07af53/.
The scan took 1,710.307 seconds with a57,323,520-byte peak working set.
This is validation time, not training or model performance.

Independent manifest verification is in
artifacts/data_quality/imdb-manifest-verification-20261109-bdf9f8fa/manifest_verification.json.
It confirmed source hashes/reference coverage, original test preservation,
both-class support and zero group/normalized-text/source-movie overlap across
train,validation,test.

The initial full report did not record an implementation-code fingerprint.
The hardened current validator now does; independent verification records its
own code fingerprint. Do not retroactively assign a code revision to the old run.

The README requests citation of Maas et al.,2011,Learning Word Vectors for
Sentiment Analysis,ACL2011,https://aclanthology.org/P11-1015/.
Acquisition/permission provenance and academic split review remain pending.
No trained model, new prediction or model metric was produced.
