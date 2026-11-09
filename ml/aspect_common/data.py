"""Permission-backed, movie-linked original-offset aspect manifests."""
from collections import Counter
from dataclasses import dataclass
import hashlib
import unicodedata
from ml.common.artifacts import safe_path, sha256
from ml.common.data import _rows
from .config import SENTIMENT_LABELS

SPLITS = ("train", "tuning", "calibration", "test")


@dataclass(frozen=True)
class AspectSpan:
    aspect: str
    start: int
    end: int
    text: str
    sentiment: int | None = None


@dataclass(frozen=True)
class ReviewExample:
    record_id: str
    review_id: str
    review_revision: int
    movie_id: str
    text: str
    text_sha256: str
    group_id: str
    language_code: str
    script: str | None = None
    cohorts: tuple[str, ...] = ()
    aspects: tuple[AspectSpan, ...] = ()

    def read_text(self) -> str:
        if hashlib.sha256(self.text.encode("utf-8")).hexdigest() != self.text_sha256:
            raise ValueError("Original review text/hash differs.")
        return self.text


@dataclass
class AspectBundle:
    labels: dict
    records: dict[str, list[ReviewExample]]
    manifest_hashes: dict

    @property
    def label_names(self):
        return sorted(self.labels, key=self.labels.get)

    def summary(self):
        return {"labels": self.labels, "manifest_hashes": self.manifest_hashes,
            "splits": {role: {"reviews": len(rows), "explicit_targets": sum(len(row.aspects) for row in rows),
                "reviewed_empty_reviews": sum(not row.aspects for row in rows),
                "aspect_counts": dict(Counter(span.aspect for row in rows for span in row.aspects)),
                "aspect_sentiment_counts": dict(Counter(span.sentiment for row in rows for span in row.aspects)),
                "language_counts": dict(Counter(row.language_code for row in rows))} for role, rows in self.records.items()}}


def validate_record(row: dict, canonical_ids: set[str], config: dict) -> ReviewExample:
    from dataset_tools.annotations import validate_annotation_record
    if validate_annotation_record(row, canonical_ids):
        raise ValueError("Phase1 annotation/permission/original-span validation failed.")
    if (row.get("aspects_complete") is not True or row.get("aspect_schema_version") != "explicit-aspect-spans-v1"
        or row.get("annotation_status") != "adjudicated" or row.get("training_permitted") is not True):
        raise ValueError("Complete, permission-backed adjudicated explicit-aspect labels are required.")
    for key in ("is_synthetic", "synthetic", "is_deleted", "consent_withdrawn"):
        if key in row and (type(row[key]) is not bool or row[key]):
            raise ValueError("Synthetic, deleted, withdrawn or non-boolean eligibility flags are ineligible.")
    if row.get("language_code") not in config["language_scope"]:
        raise ValueError("Unresolved/out-of-scope annotation language.")
    group = row.get("group_id")
    if not isinstance(group, str) or not group.strip():
        raise ValueError("Frozen leakage groups are required.")
    text = row["review_text"]
    if len(text.encode("utf-8")) > 512 * 1024:
        raise ValueError("Review exceeds the bounded original-text size.")
    aspects = row.get("aspects")
    if not isinstance(aspects, list) or len(aspects) > 128:
        raise ValueError("Explicit structured spans are required; maximum128 per review.")
    spans = []
    for span in aspects:
        polarity = span.get("sentiment")
        if polarity not in SENTIMENT_LABELS or span.get("implicit", False) is not False:
            raise ValueError("Mixed/implicit aspects require a separate approved scheme; no relabelling.")
        spans.append(AspectSpan(span["aspect"], span["start"], span["end"], span["text"], SENTIMENT_LABELS[polarity]))
    cohorts = row.get("cohorts", [])
    if not isinstance(cohorts, list) or len(cohorts) > 32 or any(not isinstance(tag, str) or not tag.strip() for tag in cohorts):
        raise ValueError("Explicit bounded cohort strings are required.")
    script = row.get("script")
    if script is not None and (not isinstance(script, str) or not script.strip()):
        raise ValueError("Script is a separate annotation string.")
    review_id = row["review_id"]
    return ReviewExample(review_id + ":" + str(row["review_revision"]), review_id, row["review_revision"],
        str(row["movie_id"]), text, row["text_sha256"], group, row["language_code"], script,
        tuple(cohorts), tuple(sorted(spans, key=lambda span: (span.start, span.end, span.aspect))))


def load_experiment(config: dict) -> AspectBundle:
    from dataset_tools.recordio import load_registry
    root, data = config["_workspace"], config["data"]
    if data.get("format") != "annotated_reviews":
        raise ValueError("Actual movie-linked complete aspect annotation manifests are required; IMDb is not an aspect source.")
    registry = safe_path(data["canonical_registry_path"], root)
    canonical_ids, blockers = load_registry(registry)
    if blockers:
        raise ValueError("An approved canonical registry is required; no guessed movie mapping.")
    hashes = {"canonical_registry": sha256(registry),
              "taxonomy": sha256(safe_path(config.get("taxonomy_path", "configs/data/annotations.json"), root))}
    records, owners, inline_bytes = {}, {}, 0
    maximum = data.get("maximum_records_per_split", 10000)
    budget = data.get("maximum_inline_bytes", 128 * 1024**2)
    if type(maximum) is not int or not 1 <= maximum <= 100000 or type(budget) is not int or not 1024 <= budget <= 256 * 1024**2:
        raise ValueError("Annotation metadata/text budget is invalid.")
    for role in SPLITS:
        path = safe_path(data["manifests"][role], root)
        hashes[role] = sha256(path)
        examples = []
        for row in _rows(path):
            if len(examples) >= maximum or row.get("split") != role:
                raise ValueError("Annotation count/split contract violated.")
            example = validate_record(row, canonical_ids, config)
            inline_bytes += len(example.text.encode("utf-8"))
            if inline_bytes > budget:
                raise ValueError("Inline annotation memory budget exceeded.")
            normalized = " ".join(unicodedata.normalize("NFKC", example.text).casefold().split())
            keys = [("review", example.review_id), ("group", example.group_id), ("text", example.text_sha256),
                    ("normalized", hashlib.sha256(normalized.encode("utf-8")).hexdigest())]
            if data.get("group_by_movie", True):
                keys.append(("movie", example.movie_id))
            for field in ("reviewer_group_id", "source_movie_id"):
                if row.get(field):
                    if not isinstance(row[field], str):
                        raise ValueError("Leakage group keys must be strings.")
                    keys.append((field, row[field]))
            for key in keys:
                if key in owners and (owners[key] != role or key[0] == "review"):
                    raise ValueError("Duplicate review/revision or cross-split group/text/movie leakage.")
                owners[key] = role
            examples.append(example)
        if not examples or not any(row.aspects for row in examples):
            raise ValueError("Each split needs real explicit-aspect evidence; reviewed empty rows remain valid negatives.")
        if config["task"] == "aspect_sentiment" and {span.sentiment for row in examples for span in row.aspects} != {0, 1, 2}:
            raise ValueError("Every aspect-sentiment split needs genuine support for all three classes.")
        if sha256(path) != hashes[role]:
            raise ValueError("Annotation manifest changed during validation.")
        records[role] = examples
    if sha256(registry) != hashes["canonical_registry"]:
        raise ValueError("Canonical registry changed during validation.")
    return AspectBundle(config["labels"], records, hashes)
