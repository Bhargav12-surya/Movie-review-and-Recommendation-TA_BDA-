"""Bounded, local record readers and shared validation safeguards.

No reader evaluates input, imports project applications, or opens a network.
Errors identify a format/location without echoing private record content.
"""
from __future__ import annotations

import csv
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import tempfile

from .io import create_output_dir, snapshot_file

MAX_RECORD_BYTES = 2 * 1024 * 1024
SUPPORTED_SUFFIXES = {".csv", ".json", ".jsonl", ".ndjson"}


class RecordFormatError(ValueError):
    """A sanitized source-format error, without input text in its message."""


def _reject_constant(_value):
    raise RecordFormatError("Non-finite JSON numbers are not permitted.")


def _finite_float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise RecordFormatError("Non-finite JSON numbers are not permitted.")
    return parsed


def _unicode_values(value):
    if isinstance(value, str):
        value.encode("utf-8")
    elif isinstance(value, dict):
        for key, item in value.items():
            key.encode("utf-8")
            _unicode_values(item)
    elif isinstance(value, list):
        for item in value:
            _unicode_values(item)


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RecordFormatError("Duplicate JSON object keys are not permitted.")
        result[key] = value
    return result


DECODER = json.JSONDecoder(parse_constant=_reject_constant,
                           parse_float=_finite_float, object_pairs_hook=_object_pairs)


def parse_json(value: str):
    """Decode strict JSON; exception messages never include source snippets."""
    try:
        result, end = DECODER.raw_decode(value.lstrip())
        if value.lstrip()[end:].strip():
            raise RecordFormatError("Unexpected trailing JSON content.")
        _unicode_values(result)
        return result
    except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
        raise RecordFormatError("Malformed JSON record.") from None


def _json_values(handle, maximum: int, chunk_size: int):
    """Stream a single object or array of objects using a bounded text window."""
    buffer = ""
    eof = False

    def read_more():
        nonlocal buffer, eof
        fragment = handle.read(chunk_size)
        if fragment:
            buffer += fragment
        else:
            eof = True

    def whitespace():
        nonlocal buffer
        buffer = buffer.lstrip()
        while not buffer and not eof:
            read_more()
            buffer = buffer.lstrip()

    whitespace()
    if not buffer:
        raise RecordFormatError("Empty JSON input.")
    array = buffer.startswith("[")
    if array:
        buffer = buffer[1:]
    elif not buffer.startswith("{"):
        raise RecordFormatError("Expected a JSON object or array of objects.")

    first = True
    while True:
        whitespace()
        if array and buffer.startswith("]"):
            buffer = buffer[1:]
            break
        if not first:
            if not array:
                break
            if not buffer.startswith(","):
                raise RecordFormatError("Expected a comma between JSON records.")
            buffer = buffer[1:]
            whitespace()
            if buffer.startswith("]"):
                raise RecordFormatError("Trailing commas are not permitted.")
        if not buffer:
            raise RecordFormatError("Incomplete JSON input.")
        while True:
            try:
                value, end = DECODER.raw_decode(buffer)
                break
            except json.JSONDecodeError:
                if eof:
                    raise RecordFormatError("Malformed or incomplete JSON record.") from None
                if len(buffer.encode("utf-8")) > maximum:
                    raise RecordFormatError("JSON record exceeds configured byte limit.")
                read_more()
            except RecursionError:
                raise RecordFormatError("JSON nesting exceeds the parser limit.") from None
        if len(buffer[:end].encode("utf-8")) > maximum:
            raise RecordFormatError("JSON record exceeds configured byte limit.")
        if not isinstance(value, dict):
            raise RecordFormatError("Every data record must be a JSON object.")
        try:
            _unicode_values(value)
        except (UnicodeError, RecursionError):
            raise RecordFormatError("JSON contains invalid Unicode values or nesting.") from None
        yield value
        buffer = buffer[end:]
        first = False
        whitespace()
        if not array:
            break
        if not buffer and eof:
            raise RecordFormatError("JSON array has no closing bracket.")
    whitespace()
    if buffer:
        raise RecordFormatError("Unexpected trailing JSON content.")


def iter_records(path: str | Path, max_record_bytes: int = MAX_RECORD_BYTES,
                 chunk_size: int = 65536):
    """Yield objects from UTF-8 CSV, JSONL/NDJSON, JSON arrays, or one object.

    CSV has a header; nested annotation columns may contain strict JSON strings.
    A record byte limit is enforced before a JSONL line or JSON object is kept.
    """
    source = Path(path)
    if max_record_bytes < 1 or chunk_size < 1:
        raise ValueError("Reader limits must be positive.")
    if source.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise RecordFormatError("Unsupported record file extension.")
    try:
        if source.suffix.lower() in {".jsonl", ".ndjson"}:
            with source.open("rb") as handle:
                line = 0
                while True:
                    raw = handle.readline(max_record_bytes + 1)
                    if not raw:
                        return
                    line += 1
                    if len(raw) > max_record_bytes:
                        raise RecordFormatError(f"Record byte limit exceeded at line {line}.")
                    if not raw.strip():
                        continue
                    try:
                        value = parse_json(raw.decode("utf-8-sig" if line == 1 else "utf-8"))
                    except UnicodeError:
                        raise RecordFormatError(f"Invalid UTF-8 at line {line}.") from None
                    if not isinstance(value, dict):
                        raise RecordFormatError(f"Expected an object at line {line}.")
                    yield value
        elif source.suffix.lower() == ".json":
            with source.open("r", encoding="utf-8-sig", newline="") as handle:
                yield from _json_values(handle, max_record_bytes, chunk_size)
        else:
            previous_limit = csv.field_size_limit()
            csv.field_size_limit(max_record_bytes)
            try:
                with source.open("r", encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle, strict=True)
                    if not reader.fieldnames or any(not name for name in reader.fieldnames):
                        raise RecordFormatError("CSV requires nonempty header names.")
                    if len(set(reader.fieldnames)) != len(reader.fieldnames):
                        raise RecordFormatError("Duplicate CSV headers are not permitted.")
                    for value in reader:
                        if None in value or any(v is None for v in value.values()):
                            raise RecordFormatError(f"CSV field-count mismatch at line {reader.line_num}.")
                        if sum(len(v.encode("utf-8")) for v in value.values()) > max_record_bytes:
                            raise RecordFormatError(f"Record byte limit exceeded at line {reader.line_num}.")
                        yield value
            finally:
                csv.field_size_limit(previous_limit)
    except UnicodeError:
        raise RecordFormatError("Source contains invalid UTF-8.") from None
    except csv.Error:
        raise RecordFormatError("Malformed CSV record or oversized field.") from None


def input_files(source: str | Path, exclude=(), max_files: int = 10000) -> list[Path]:
    """Find only supported local record files, with a bounded file manifest."""
    path = Path(source)
    omitted = {Path(value).resolve() for value in exclude if value}
    if path.is_file():
        return [] if path.resolve() in omitted else [path]
    if not path.is_dir():
        return []
    files = []
    for candidate in path.rglob("*"):
        if (candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES
                and candidate.resolve() not in omitted
                and candidate.name not in {"provenance.json", "manifest.json"}):
            files.append(candidate)
            if len(files) > max_files:
                raise ValueError("Source file count exceeds configured manifest limit.")
    return sorted(files)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def anonymous_key(value) -> str:
    return text_hash(str(value))[:16]


def strict_int(value, minimum: int = 0) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= minimum else None
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        parsed = int(value)
        return parsed if parsed >= minimum else None
    return None


def bool_value(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return None


def utc_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def nested(value, default):
    if value in (None, ""):
        return default
    return parse_json(value) if isinstance(value, str) else value


def load_registry(path: str | Path | None) -> tuple[set[str], list[str]]:
    """Load an explicitly approved canonical registry, never provisional keys."""
    if path is None or not Path(path).is_file():
        return set(), ["approved_canonical_registry_missing"]
    ids: set[str] = set()
    blockers: list[str] = []
    for item in iter_records(path):
        wrapper = isinstance(item.get("movies"), list)
        rows = item["movies"] if wrapper else [item]
        globally_approved = wrapper and item.get("status") == "approved"
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Canonical registry contains a non-object entry.")
            movie_id = row.get("movie_id")
            if (movie_id is None or isinstance(movie_id, bool)
                    or not str(movie_id).strip()
                    or (isinstance(movie_id, int) and movie_id < 1)
                    or str(movie_id).startswith(("movielens:", "tmdb:", "imdb:", "demo:"))
                    or row.get("mapping_status") not in {"validated", "approved"}
                    or not (globally_approved or bool_value(row.get("approved")) is True)):
                raise ValueError("Canonical registry contains an unapproved or provisional entry.")
            key = str(movie_id)
            if key in ids:
                raise ValueError("Canonical registry contains duplicate internal IDs.")
            ids.add(key)
            if len(ids) > 250000:
                raise ValueError("Canonical registry exceeds the configured local catalogue limit.")
    if not ids:
        blockers.append("approved_canonical_registry_empty")
    return ids, blockers


@contextmanager
def validation_workspace(output: str | Path | None, workspace=None):
    """A fresh report directory or disposable private disk-backed index."""
    if output is not None:
        folder = create_output_dir(output, workspace)
        with closing(sqlite3.connect(folder / "validation-index.sqlite3")) as database:
            with database:
                database.execute("PRAGMA cache_size=-4096")
                yield folder, database
    else:
        with tempfile.TemporaryDirectory(prefix="movie-validation-") as temporary:
            with closing(sqlite3.connect(Path(temporary) / "index.sqlite3")) as database:
                with database:
                    database.execute("PRAGMA cache_size=-4096")
                    yield None, database


def stable_inputs(before: dict[str, dict]) -> bool:
    return all(Path(path).is_file() and snapshot_file(path) == value
               for path, value in before.items())
