"""Bounded reference manifests and lazy, hash-checked original review reads."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path, PurePosixPath
from .artifacts import safe_path, sha256
from .config import LABELS

SPLITS = ("train", "tuning", "calibration", "test")


@dataclass(frozen=True)
class ReviewRecord:
    record_id: str
    label: int
    group_id: str
    text_sha256: str
    source_path: Path | None = None
    inline_text: str | None = None
    metadata: dict = field(default_factory=dict)

    def read_text(self, maximum_bytes: int = 512 * 1024) -> str:
        if self.source_path is not None:
            if self.source_path.stat().st_size > maximum_bytes:
                raise ValueError("Review exceeds the bounded text size.")
            raw = self.source_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != self.text_sha256:
                raise ValueError("Raw review hash changed; re-audit the source.")
            text = raw.decode("utf-8", errors="strict")
        else:
            text = self.inline_text
            if not isinstance(text, str):
                raise ValueError("Review text is unavailable.")
            raw = text.encode("utf-8", errors="strict")
            if len(raw) > maximum_bytes or hashlib.sha256(raw).hexdigest() != self.text_sha256:
                raise ValueError("Original annotation text/hash mismatch.")
        if not text.strip():
            raise ValueError("Empty review text.")
        return text


@dataclass
class DataBundle:
    labels: dict[str, int]
    records: dict[str, list[ReviewRecord]]
    manifest_hashes: dict[str, str]

    @property
    def label_names(self) -> list[str]:
        return sorted(self.labels, key=self.labels.get)

    def summary(self) -> dict:
        return {"labels": self.labels, "manifest_hashes": self.manifest_hashes,
                "splits": {split: {"count": len(rows), "class_counts": dict(Counter(row.label for row in rows))}
                           for split, rows in self.records.items()}}

    def texts_labels(self, split: str, max_text_bytes: int = 256 * 1024**2) -> tuple[list[str], list[int]]:
        if split not in SPLITS:
            raise ValueError("Unknown experiment split.")
        texts, labels, total = [], [], 0
        for row in self.records[split]:
            text = row.read_text()
            total += len(text.encode("utf-8"))
            if total > max_text_bytes:
                raise ValueError("Text materialization budget exceeded; use lazy/batched processing.")
            texts.append(text)
            labels.append(row.label)
        return texts, labels


def _rows(path: Path):
    with path.open("rb") as stream:
        number = 0
        while True:
            line = stream.readline(2 * 1024 * 1024 + 1)
            if not line:
                break
            number += 1
            if len(line) > 2 * 1024 * 1024 or not line.strip():
                raise ValueError("Oversized/blank manifest record.")
            try:
                def unique(pairs):
                    result = {}
                    for key, value in pairs:
                        if key in result:
                            raise ValueError("Duplicate manifest key.")
                        result[key] = value
                    return result
                def reject(value):
                    raise ValueError("Nonfinite manifest value.")
                row = json.loads(line.decode("utf-8"), object_pairs_hook=unique, parse_constant=reject)
            except (ValueError, UnicodeError):
                raise ValueError("Malformed manifest record at line " + str(number)) from None
            if not isinstance(row, dict):
                raise ValueError("Expected manifest objects.")
            yield row


def _imdb_reference_path(row: dict, split: str, label: int, source: Path) -> Path:
    """Admit only official labelled buckets; unsup is never a binary label source."""
    expected_source = "test" if split == "test" else "train"
    if row.get("source_split") != expected_source:
        raise ValueError("Official IMDb labelled train/test boundary violated.")
    name = row.get("source_path")
    if not isinstance(name, str) or "\\" in name:
        raise ValueError("IMDb references require the audited forward-slash relative path.")
    parts = PurePosixPath(name).parts
    bucket = "neg" if label == 0 else "pos"
    if len(parts) != 3 or parts[:2] != (expected_source, bucket) or not parts[2].endswith(".txt"):
        raise ValueError("IMDb path must agree with its official split and genuine class bucket.")
    # Require the canonical spelling, rather than accepting ./ or normalized aliases.
    if name != "/".join(parts) or ":" in name:
        raise ValueError("IMDb reference is not a canonical relative corpus path.")
    path = (source / Path(*parts)).resolve()
    if not path.is_relative_to(source) or not path.is_file():
        raise ValueError("Source reference escapes or is missing.")
    return path


def load_experiment(config: dict) -> DataBundle:
    data, root, task = config["data"], config["_workspace"], config["task"]
    kind = data.get("format")
    if kind not in {"imdb_references", "annotated_reviews"}:
        raise ValueError("Unsupported local manifest format.")
    if (kind == "imdb_references") != (task == "binary_imdb"):
        raise ValueError("IMDb is a distinct binary task, never a neutral/sarcasm source.")
    source = safe_path(data["source_root"], root)
    records, hashes, owners = {}, {}, {}
    canonical_ids = None
    if kind == "annotated_reviews":
        from dataset_tools.recordio import load_registry
        registry_name = data.get("canonical_registry_path")
        if not registry_name:
            raise ValueError("An approved canonical movie registry is required.")
        registry = safe_path(registry_name, root)
        canonical_ids, blockers = load_registry(registry)
        if blockers:
            raise ValueError("Approved canonical movie registry is unavailable.")
        hashes["canonical_registry"] = sha256(registry)
    inlined_bytes = 0
    for split in SPLITS:
        name = data.get("manifests", {}).get(split)
        if not name:
            raise ValueError("Missing explicit " + split + " manifest. Never reuse tuning for calibration.")
        manifest = safe_path(name, root)
        hashes[split] = sha256(manifest)
        current = []
        for row in _rows(manifest):
            if len(current) >= int(data.get("maximum_records_per_split", 100000)):
                raise ValueError("Manifest metadata record limit exceeded.")
            if any(key in row and type(row[key]) is not bool for key in
                   ("is_synthetic", "synthetic", "is_deleted", "consent_withdrawn")):
                raise ValueError("Eligibility flags must be explicit JSON booleans.")
            if row.get("is_synthetic") is True or row.get("synthetic") is True or any(
                term in str(row.get("source", "")).casefold() for term in ("synthetic", "demo", "fictional")):
                raise ValueError("Synthetic fixtures cannot enter real training/evaluation.")
            if row.get("is_deleted") is True or row.get("consent_withdrawn") is True:
                raise ValueError("Deleted/withdrawn reviews are ineligible for training/evaluation.")
            label = row.get("label") if kind == "imdb_references" else row.get(
                "sarcasm" if task == "sarcasm" else "sentiment")
            if isinstance(label, str):
                label = LABELS[task].get(label)
            if type(label) is not int or label not in LABELS[task].values():
                raise ValueError("Invalid/missing genuine task label.")
            group = row.get("group_id")
            if not isinstance(group, str) or not group:
                raise ValueError("Every example requires a frozen leakage group.")
            if kind == "imdb_references":
                if row.get("label_task") != "binary_imdb" or row.get("application_movie_id") is not None:
                    raise ValueError("IMDb task/movie identity contract violated.")
                expected = "validation" if split in {"tuning", "calibration"} else split
                if row.get("split") != expected or row.get("experiment_split", split) != split:
                    raise ValueError("Reference manifest has the wrong split role.")
                path = _imdb_reference_path(row, split, label, source)
                record_id, checksum, inline = row["source_path"], row["raw_sha256"], None
            else:
                if row.get("split") != split or row.get("training_permitted") is not True:
                    raise ValueError("Annotation split/permission is not explicit.")
                if row.get("annotation_status") != "adjudicated" or not row.get("consent_or_license_ref"):
                    raise ValueError("Only permission-backed adjudicated annotations are eligible.")
                if not row.get("movie_id") or str(row["movie_id"]).startswith("movielens:"):
                    raise ValueError("A validated canonical movie ID is required.")
                if str(row["movie_id"]) not in canonical_ids:
                    raise ValueError("Movie is absent from the approved canonical registry.")
                if task != "sarcasm":
                    from dataset_tools.annotations import validate_annotation_record
                    if validate_annotation_record(row, canonical_ids):
                        raise ValueError("Phase1 annotation contract failed.")
                elif row.get("label_schema_version") != "sarcasm-binary-v1":
                    raise ValueError("Independent human sarcasm labels are required.")
                if not isinstance(row.get("review_id"), str) or not row["review_id"].strip() or (
                    type(row.get("review_revision")) is not int or row["review_revision"] < 1) or not row.get("adjudicator_id"):
                    raise ValueError("Review identity/revision/adjudication is incomplete.")
                record_id = str(row["review_id"]) + ":" + str(row["review_revision"])
                checksum, inline, path = row["text_sha256"], row["review_text"], None
                inlined_bytes += len(inline.encode("utf-8"))
                if inlined_bytes > int(data.get("maximum_inline_bytes", 128 * 1024**2)):
                    raise ValueError("Inline annotation memory budget exceeded.")
            if not isinstance(checksum, str) or len(checksum) != 64 or any(c not in "0123456789abcdef" for c in checksum):
                raise ValueError("Missing valid source SHA256.")
            # Movie source association and exact/normalized groups stay isolated.
            keys = [("id", record_id), ("group", group), ("text", checksum)]
            if row.get("normalized_sha256"):
                keys.append(("normalized", row["normalized_sha256"]))
            if row.get("source_movie_id"):
                keys.append(("source_movie", row["source_movie_id"]))
            if kind == "annotated_reviews" and data.get("group_by_movie", True):
                keys.append(("canonical_movie", str(row["movie_id"])))
            if row.get("reviewer_group_id"):
                keys.append(("reviewer", row["reviewer_group_id"]))
            for key in keys:
                if key in owners and (owners[key] != split or key[0] == "id"):
                    raise ValueError("Duplicate example or cross-split leakage detected.")
                owners[key] = split
            metadata = {key: row.get(key) for key in ("language_code", "script", "cohorts", "source_movie_id")}
            if any(metadata[key] is not None and (not isinstance(metadata[key], str) or not metadata[key].strip())
                   for key in ("language_code", "script", "source_movie_id")):
                raise ValueError("Language/script/source movie metadata must be explicit nonempty strings.")
            if kind == "annotated_reviews" and (metadata["language_code"] not in {"en", "hi", "hi-Latn", "mul"} or
                metadata["language_code"] not in config.get("language_scope", [])):
                raise ValueError("Supervised annotations require a resolved language within the reviewed experiment scope.")
            if metadata["cohorts"] is not None and (not isinstance(metadata["cohorts"], list) or
                any(not isinstance(item, str) or not item.strip() for item in metadata["cohorts"])):
                raise ValueError("Cohorts must be explicit annotation strings.")
            current.append(ReviewRecord(record_id, label, group, checksum, path, inline, metadata))
        if not current or set(record.label for record in current) != set(LABELS[task].values()):
            raise ValueError("Every split must contain observed support for every task class.")
        if sha256(manifest) != hashes[split]:
            raise ValueError("Manifest changed during validation.")
        records[split] = current
    return DataBundle(dict(LABELS[task]), records, hashes)
