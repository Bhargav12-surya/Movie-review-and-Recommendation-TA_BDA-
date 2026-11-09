"""Bounded fast-tokenizer windows retaining original Unicode offsets."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenWindow:
    index: int
    features: dict[str, list[int]]
    offsets: tuple[tuple[int, int], ...]
    content: tuple[bool, ...]


def window_settings(config: dict, tokenizer) -> dict:
    supplied = config.get("tokenization", {})
    result = {"maximum_sequence_length": 128, "stride": 32,
              "maximum_windows_per_review": 128, "maximum_training_rows": 30000}
    result.update(supplied)
    bounds = {"maximum_sequence_length": (16, 512), "stride": (0, 480),
              "maximum_windows_per_review": (1, 512), "maximum_training_rows": (1, 100000)}
    for key, (low, high) in bounds.items():
        if type(result[key]) is not int or not low <= result[key] <= high:
            raise ValueError("Invalid bounded extraction window setting: " + key)
    if not getattr(tokenizer, "is_fast", False):
        raise ValueError("Extraction requires a fast tokenizer with original-text offsets.")
    budget = result["maximum_sequence_length"] - tokenizer.num_special_tokens_to_add(pair=False)
    if budget <= 0 or result["stride"] >= budget:
        raise ValueError("Window overlap must be smaller than the actual content-token budget.")
    return result


def encode_windows(text: str, tokenizer, config: dict) -> list[TokenWindow]:
    if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 512 * 1024:
        raise ValueError("Extraction expects bounded nonempty original review text.")
    options = window_settings(config, tokenizer)
    encoded = tokenizer(text, truncation=True, max_length=options["maximum_sequence_length"],
        stride=options["stride"], padding=False, return_overflowing_tokens=True,
        return_offsets_mapping=True, return_attention_mask=True)
    count = len(encoded["input_ids"])
    if not 1 <= count <= options["maximum_windows_per_review"]:
        raise ValueError("Review exceeds the reviewed window budget; no silent truncation is allowed.")
    windows = []
    for index in range(count):
        features = {key: list(encoded[key][index]) for key in ("input_ids", "attention_mask", "token_type_ids")
                    if key in encoded}
        offsets = tuple(tuple(pair) for pair in encoded["offset_mapping"][index])
        sequence_ids = encoded.sequence_ids(index)
        if not len(offsets) == len(sequence_ids) == len(features["input_ids"]) or any(
                len(values) != len(offsets) for values in features.values()):
            raise ValueError("Tokenizer window/offset dimensions disagree.")
        if any(len(pair) != 2 or any(type(value) is not int for value in pair) or
               not 0 <= pair[0] <= pair[1] <= len(text) for pair in offsets):
            raise ValueError("Tokenizer offsets do not address the original Unicode text.")
        content = tuple(sequence == 0 and start < end for sequence, (start, end) in zip(sequence_ids, offsets))
        if not any(content):
            raise ValueError("Tokenizer produced a window without usable text offsets.")
        windows.append(TokenWindow(index, features, offsets, content))
    return windows
