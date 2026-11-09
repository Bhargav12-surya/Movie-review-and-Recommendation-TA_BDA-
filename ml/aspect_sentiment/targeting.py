"""Exact-target context construction without changing original review offsets.

The fixed markers below are ordinary text, not added tokenizer vocabulary.
Each request has one highlighted target and an aspect/category query. The code
checks the actual final pair tokenization rather than silently truncating the
target or relying on a repeated surface string to identify its occurrence.
"""
from __future__ import annotations
from dataclasses import dataclass

OPEN_MARKER = " <target> "
CLOSE_MARKER = " </target> "
CONDITIONING_VERSION = "category-surface-marked-context-v1"


@dataclass(frozen=True)
class TargetInput:
    features: dict
    context_start: int
    context_end: int
    target_start: int
    target_end: int
    marked_context: str
    query: str
    conditioning_version: str = CONDITIONING_VERSION


def _offsets(encoded) -> list[tuple[int, int]]:
    offsets = encoded.get("offset_mapping")
    if not isinstance(offsets, (list, tuple)) or any(
        not isinstance(pair, (list, tuple)) or len(pair) != 2 or
        any(type(value) is not int for value in pair) or not 0 <= pair[0] <= pair[1]
        for pair in offsets):
        raise ValueError("A fast tokenizer with bounded original-text offsets is required.")
    return [tuple(pair) for pair in offsets]


def target_input(example, span, tokenizer, config: dict) -> TargetInput:
    """Build an actual tokenizer pair that contains exactly the selected target.

    Context is selected in original token coordinates, then shrunk until the
    complete query/marked-context pair fits. An unrepresentable target or marker
    collision is an explicit error, never an automatic polarity/neutral label.
    """
    if not getattr(tokenizer, "is_fast", False):
        raise ValueError("Aspect sentiment requires a fast tokenizer.")
    text = example.read_text()
    start, end = span.start, span.end
    taxonomy = config["taxonomy"]["aspects"]
    if span.aspect not in taxonomy or type(start) is not int or type(end) is not int or not (
        0 <= start < end <= len(text)) or text[start:end] != span.text:
        raise ValueError("Target category/span must refer exactly to the original review.")
    if "<target>" in text or "</target>" in text:
        raise ValueError("Review collides with the frozen target-marker protocol; review separately.")
    options = config.get("tokenization", {})
    maximum = options.get("maximum_sequence_length", 128)
    maximum_text = options.get("maximum_review_code_points", 20000)
    if type(maximum) is not int or not 32 <= maximum <= 512 or len(text) > maximum_text:
        raise ValueError("Target input exceeds its reviewed sequence/review bound.")
    original = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True,
                         return_attention_mask=False, verbose=False)
    offsets = _offsets(original)
    if not offsets or len(offsets) > int(options.get("maximum_review_tokens", 50000)):
        raise ValueError("Original review tokenization exceeds the bounded context policy.")
    if any(end_offset > len(text) or start_offset == end_offset for start_offset, end_offset in offsets):
        raise ValueError("Original tokenizer offsets contain unsupported zero/out-of-range intervals.")
    overlapping = [index for index, (a, b) in enumerate(offsets) if a < end and b > start]
    if not overlapping or offsets[overlapping[0]][0] != start or offsets[overlapping[-1]][1] != end:
        raise ValueError("Target boundaries are not exactly representable by the reviewed tokenizer.")
    first, last = overlapping[0], overlapping[-1]
    # Begin with at most maximum original tokens. The pair is measured below;
    # query/marker tokens are never assumed to have a fixed token count.
    room = max(0, maximum - (last - first + 1))
    left = max(0, first - room // 2)
    right = min(len(offsets), last + 1 + room - (first - left))
    left = max(0, min(left, right - maximum))
    query = "aspect: " + span.aspect + "; mention: " + span.text
    if len(query) > 1024:
        raise ValueError("Target query exceeds its explicit character bound.")
    while True:
        context_start, context_end = offsets[left][0], offsets[right - 1][1]
        marked_start = start - context_start + len(OPEN_MARKER)
        marked_end = marked_start + len(span.text)
        marked = text[context_start:start] + OPEN_MARKER + span.text + CLOSE_MARKER + text[end:context_end]
        encoded = tokenizer(query, marked, add_special_tokens=True, truncation=False,
                            return_offsets_mapping=True, return_attention_mask=True, verbose=False)
        pair_offsets = _offsets(encoded)
        ids = encoded.get("input_ids")
        if not isinstance(ids, (list, tuple)) or len(ids) != len(pair_offsets):
            raise ValueError("Pair token/offset alignment is invalid.")
        if len(ids) <= maximum:
            sequence_ids = encoded.sequence_ids()
            if len(sequence_ids) != len(pair_offsets):
                raise ValueError("Pair sequence IDs do not align with tokenizer offsets.")
            target_tokens = [(a, b) for sequence, (a, b) in zip(sequence_ids, pair_offsets)
                             if sequence == 1 and a < marked_end and b > marked_start]
            if not target_tokens or target_tokens[0][0] != marked_start or target_tokens[-1][1] != marked_end:
                raise ValueError("Actual pair tokenization does not preserve the complete marked target.")
            features = {name: list(encoded[name]) for name in ("input_ids", "attention_mask", "token_type_ids")
                        if name in encoded and name in tokenizer.model_input_names}
            if "input_ids" not in features or any(len(value) != len(ids) for value in features.values()):
                raise ValueError("Final paired model inputs are incomplete or misaligned.")
            return TargetInput(features, context_start, context_end, start, end, marked, query)
        # Remove the farthest available context token, keeping the full target.
        left_extra, right_extra = first - left, right - last - 1
        if left_extra == 0 and right_extra == 0:
            raise ValueError("Target plus conditioning does not fit; approve a different length/tokenizer.")
        if left_extra >= right_extra and left_extra:
            left += 1
        else:
            right -= 1
