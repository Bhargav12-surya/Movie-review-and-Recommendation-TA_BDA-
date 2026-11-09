"""Bounded hashing, safe new output paths and metadata-only quality issues."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def snapshot_file(path: str | Path) -> dict:
    value = Path(path).stat()
    return {"bytes": value.st_size, "mtime_ns": value.st_mtime_ns}


def fingerprint_file(path: str | Path, algorithms: Iterable[str] = ("sha256",)) -> dict:
    """Hash sequentially without retaining file bytes; detect concurrent writes."""
    source = Path(path)
    before = snapshot_file(source)
    hashes = {name: hashlib.new(name, usedforsecurity=False) for name in algorithms}
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            for digest in hashes.values():
                digest.update(chunk)
    after = snapshot_file(source)
    if before != after:
        raise ValueError(f"Input changed while hashing: {source.name}")
    return {"path": str(source.resolve()), **before,
            **{name: digest.hexdigest() for name, digest in hashes.items()}}


def ensure_safe_output(path: str | Path, workspace: str | Path | None = None) -> Path:
    root = Path(workspace or project_root()).resolve()
    supplied = Path(path)
    target = (supplied if supplied.is_absolute() else root / supplied).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError("Output must be a new path inside the workspace.")
    for prefix in ("data/raw", "temp", ".git", ".venv"):
        protected = (root / prefix).resolve()
        if target == protected or target.is_relative_to(protected):
            raise ValueError(f"Output cannot be inside protected path: {prefix}")
    if any(part in {".git", ".venv", "node_modules"} for part in target.relative_to(root).parts):
        raise ValueError("Output cannot be inside dependency or Git directories.")
    return target


def create_output_dir(path: str | Path, workspace: str | Path | None = None) -> Path:
    target = ensure_safe_output(path, workspace)
    target.mkdir(parents=True, exist_ok=False)
    return target


def write_json_new(path: str | Path, payload: object,
                   workspace: str | Path | None = None) -> Path:
    target = ensure_safe_output(path, workspace)
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    return target


class IssueCollector:
    """Exact counters with a capped sample; never accepts raw review text."""

    def __init__(self, max_samples: int = 40) -> None:
        self.counters: Counter = Counter()
        self.severities: dict[str, str] = {}
        self.samples: list[dict] = []
        self.max_samples = max_samples

    def add(self, code: str, record: int | None = None, field: str | None = None,
            severity: str = "error", identifiers: dict | None = None) -> None:
        if severity not in {"error", "warning", "info"}:
            raise ValueError("Unknown issue severity.")
        self.counters[code] += 1
        if code not in self.severities or severity == "error":
            self.severities[code] = severity
        if len(self.samples) < self.max_samples:
            sample = {"code": code, "severity": severity}
            if record is not None:
                sample["record"] = record
            if field is not None:
                sample["field"] = field
            if identifiers:
                # Identifiers are source IDs/column names, never text excerpts.
                sample["identifiers"] = identifiers
            self.samples.append(sample)

    @property
    def has_errors(self) -> bool:
        return any(self.severities.get(code) == "error" for code in self.counters)

    def as_dict(self) -> dict:
        return {"counters": dict(sorted(self.counters.items())),
                "severities": self.severities, "bounded_samples": self.samples,
                "sample_limit": self.max_samples}


def base_report(source: str, scope: str = "full") -> dict:
    return {"schema_version": 1, "source": source, "status": "complete",
            "scope": scope, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "checks_complete": [], "counts": {}, "issues": {}, "blockers": [],
            "input_fingerprints": {}, "artifacts": {}}


def status_exit(report: dict) -> int:
    return {"complete": 0, "invalid": 2, "missing": 3, "partial": 4}[report["status"]]
