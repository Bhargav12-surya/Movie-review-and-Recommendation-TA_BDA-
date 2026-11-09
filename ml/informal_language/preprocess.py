"""Immutable originals and aligned optional feature views; default is identity."""
from dataclasses import dataclass
import hashlib
from .emoji_processing import symbol_spans
from .language_detection import observe_scripts
from .slang_normalization import expansion_candidates


@dataclass(frozen=True)
class AlignedView:
    original: str
    text: str
    alignment: tuple[tuple[int, int], ...]
    method: str = "identity-v1"

    def __post_init__(self):
        if len(self.text) != len(self.alignment) or any(not 0 <= start < end <= len(self.original)
                                                       for start, end in self.alignment):
            raise ValueError("Every view code point requires a valid original-text interval.")
        if any(left[0] > right[0] for left, right in zip(self.alignment, self.alignment[1:])):
            raise ValueError("Alignment must preserve source order.")

    def original_span(self, start: int, end: int) -> tuple[int, int]:
        if not 0 <= start < end <= len(self.text):
            raise ValueError("View span is outside the aligned representation.")
        return min(pair[0] for pair in self.alignment[start:end]), max(pair[1] for pair in self.alignment[start:end])


def preserve(text: str) -> AlignedView:
    if not isinstance(text, str) or not text.strip() or len(text) > 200000:
        raise ValueError("Review must contain bounded nonempty Unicode text.")
    text.encode("utf-8", errors="strict")
    return AlignedView(text, text, tuple((index, index + 1) for index in range(len(text))))


def replace_spans(view: AlignedView, replacements: list[dict], method: str) -> AlignedView:
    cursor, pieces, alignment = 0, [], []
    for change in sorted(replacements, key=lambda row: row["start"]):
        start, end, replacement = change["start"], change["end"], change["replacement"]
        if not cursor <= start < end <= len(view.text) or not isinstance(replacement, str):
            raise ValueError("Replacement spans overlap or are invalid.")
        pieces.append(view.text[cursor:start])
        alignment.extend(view.alignment[cursor:start])
        source = view.original_span(start, end)
        pieces.append(replacement)
        alignment.extend([source] * len(replacement))
        cursor = end
    pieces.append(view.text[cursor:])
    alignment.extend(view.alignment[cursor:])
    return AlignedView(view.original, "".join(pieces), tuple(alignment), method)


def feature_view(text: str, emoji_policy: str = "preserve", slang_mapping: dict | None = None) -> AlignedView:
    view = preserve(text)
    if emoji_policy not in {"preserve", "remove_for_ablation"}:
        raise ValueError("Unknown emoji policy.")
    if emoji_policy == "remove_for_ablation":
        view = replace_spans(view, [{**span, "replacement": " "} for span in symbol_spans(view.text)],
                             "symbol-removal-ablation-v1")
    if slang_mapping:
        candidates = expansion_candidates(view.text, slang_mapping)
        view = replace_spans(view, [{**span, "replacement": span["expansion"]} for span in candidates],
                             view.method + "+reviewed-slang-expansion")
    return view


def observations(text: str) -> dict:
    view = preserve(text)
    return {"original_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "code_points": len(text), "symbols": symbol_spans(text), "scripts": observe_scripts(text),
            "normalization": view.method, "sentiment": None, "sarcasm": None,
            "offset_unit": "original_unicode_code_points"}


def utf16_offset(text: str, code_point_offset: int) -> int:
    if not 0 <= code_point_offset <= len(text):
        raise ValueError("Offset is outside original text.")
    return len(text[:code_point_offset].encode("utf-16-le")) // 2
