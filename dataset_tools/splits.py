"""Deterministic group splits and bounded near-duplicate candidate features.

These calculations inspect supplied text. They do not create labels or fit a
model. Approximate candidate retrieval is explicitly not an exhaustive proof
that no semantic duplicate exists.
"""
from __future__ import annotations

import hashlib
import heapq
import html
import re


def normalized_text(text: str) -> str:
    """Audit-only equivalence; callers retain original text and character offsets."""
    return " ".join(html.unescape(re.sub(r"<br\s*/?>", " ", text, flags=re.I)).casefold().split())


def text_shingles(text: str) -> set[str]:
    tokens = re.findall(r"\w+", normalized_text(text), flags=re.UNICODE)
    if len(tokens) < 3:
        return set(tokens)
    return {" ".join(tokens[i:i + 3]) for i in range(len(tokens) - 2)}


def candidate_fingerprints(text: str, size: int = 16) -> tuple[str, ...]:
    """Bottom-k stable shingle hashes, computed for one document at a time."""
    if not 4 <= size <= 128:
        raise ValueError("Signature size must be between 4 and 128.")
    values = (hashlib.blake2b(s.encode("utf-8"), digest_size=8).hexdigest()
              for s in text_shingles(text))
    return tuple(heapq.nsmallest(size, values))


def shingle_jaccard(left: str, right: str) -> float:
    a, b = text_shingles(left), text_shingles(right)
    return len(a & b) / len(a | b) if a or b else 0.0


class Groups:
    """Union-find over metadata keys, not over retained review text."""

    def __init__(self) -> None:
        self.parents: dict[str, str] = {}

    def find(self, key: str) -> str:
        self.parents.setdefault(key, key)
        while self.parents[key] != key:
            self.parents[key] = self.parents[self.parents[key]]
            key = self.parents[key]
        return key

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        # Stable representative makes the result independent of input iteration.
        if a != b:
            self.parents[max(a, b)] = min(a, b)


def validation_group(group_id: str, fraction: float, seed: int) -> bool:
    if not 0 < fraction < 1:
        raise ValueError("Validation fraction must lie strictly between 0 and 1.")
    number = int.from_bytes(hashlib.sha256(f"{seed}:{group_id}".encode()).digest()[:8], "big")
    return number / 2**64 < fraction
