"""Decode actual BIO argmax outputs and resolve overlapping window evidence."""
from __future__ import annotations
import math
from .windows import TokenWindow


def decode_window(window: TokenWindow, label_ids, confidences, text: str, names: list[str]) -> tuple[list[dict], dict]:
    if not len(label_ids) == len(confidences) == len(window.offsets):
        raise ValueError("Model token output dimensions do not match original offsets.")
    content_indices = [index for index, active in enumerate(window.content) if active]
    first_content, last_content = content_indices[0], content_indices[-1]
    candidates, current, repaired, clipped = [], None, 0, 0

    def finish():
        nonlocal current, clipped
        if current is None:
            return
        # A span touching a non-final window edge may be a clipped fragment.
        left_cut = current["first_token"] == first_content and bool(text[:current["start"]].strip())
        right_cut = current["last_token"] == last_content and bool(text[current["end"]:].strip())
        if left_cut or right_cut:
            clipped += 1
        else:
            candidates.append({"aspect": current["aspect"], "start": current["start"], "end": current["end"],
                "text": text[current["start"]:current["end"]],
                "token_confidence": sum(current["values"]) / len(current["values"]),
                "confidence_calibrated": False, "confidence_method": "mean_assigned_token_softmax",
                "window_index": window.index, "implicit": False,
                "offset_unit": "original_unicode_code_points"})
        current = None

    for index, ((start, end), active, predicted, confidence) in enumerate(
            zip(window.offsets, window.content, label_ids, confidences)):
        if not active:
            finish()
            continue
        if type(predicted) is not int or not 0 <= predicted < len(names) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("Invalid model BIO label/confidence.")
        label = names[predicted]
        if label == "O":
            finish()
            continue
        prefix, category = label.split("-", 1)
        if prefix not in {"B", "I"}:
            raise ValueError("Model artifact contains an unsupported BIO label.")
        if prefix == "B" or current is None or current["aspect"] != category:
            if prefix == "I":
                repaired += 1
            finish()
            current = {"aspect": category, "start": start, "end": end, "first_token": index,
                       "last_token": index, "values": [float(confidence)]}
        else:
            if start < current["start"]:
                raise ValueError("Tokenizer offsets reverse original-text order.")
            current["end"] = max(current["end"], end)
            current["last_token"] = index
            current["values"].append(float(confidence))
    finish()
    return candidates, {"invalid_i_repaired_as_b": repaired, "boundary_candidates_discarded": clipped}


def merge_candidates(candidates: list[dict]) -> tuple[list[dict], dict]:
    # Highest assigned-token confidence wins; stable ties prefer earlier/shorter
    # evidence and taxonomy spelling. Never splice two fragments into a new span.
    ordered = sorted(candidates, key=lambda row: (-row["token_confidence"], row["start"], row["end"],
                                                 row["aspect"], row.get("window_index", 0)))
    kept, seen, duplicate, conflict = [], set(), 0, 0
    for candidate in ordered:
        key = candidate["aspect"], candidate["start"], candidate["end"]
        if key in seen:
            duplicate += 1
            continue
        seen.add(key)
        if any(candidate["start"] < other["end"] and candidate["end"] > other["start"] for other in kept):
            conflict += 1
            continue
        kept.append(candidate)
    return sorted(kept, key=lambda row: (row["start"], row["end"], row["aspect"])), {
        "duplicate_window_candidates": duplicate, "overlap_candidates_discarded": conflict,
        "merge_policy": "confidence_then_offsets_no_fragment_splicing_v1"}
