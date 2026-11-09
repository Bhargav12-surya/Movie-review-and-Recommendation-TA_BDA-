"""All-subword BIO labels; partial spans are masked rather than taught as O."""
from __future__ import annotations
from .windows import TokenWindow


def span_key(span) -> tuple[str, int, int]:
    return span.aspect, span.start, span.end


def _covered(text: str, start: int, end: int, offsets) -> bool:
    cursor = start
    for left, right in sorted(offsets):
        if left > cursor and any(not character.isspace() for character in text[cursor:left]):
            return False
        cursor = max(cursor, right)
    return cursor == end and not any(not character.isspace() for character in text[cursor:end])


def aligned_labels(window: TokenWindow, spans, text: str, labels: dict[str, int]):
    targets = [labels["O"] if active else -100 for active in window.content]
    complete, partial = set(), set()
    occupied = set()
    for span in spans:
        if type(span.start) is not int or type(span.end) is not int or not 0 <= span.start < span.end <= len(text):
            raise ValueError("Invalid original aspect offsets.")
        if text[span.start:span.end] != span.text or "B-" + span.aspect not in labels:
            raise ValueError("Aspect evidence/taxonomy does not match the original review.")
        selected = [index for index, ((start, end), active) in enumerate(zip(window.offsets, window.content))
                    if active and start < span.end and end > span.start]
        if not selected:
            continue
        if occupied.intersection(selected):
            raise ValueError("Overlapping gold aspects cannot be represented by one BIO tag sequence.")
        occupied.update(selected)
        offsets = [window.offsets[index] for index in selected]
        # A token crossing a genuine annotation boundary is never rounded/snapped.
        if any(start < span.start or end > span.end for start, end in offsets):
            raise ValueError("An annotation boundary falls inside a tokenizer token; review the annotation/tokenizer.")
        key = span_key(span)
        if min(start for start, _ in offsets) == span.start and max(end for _, end in offsets) == span.end and (
                _covered(text, span.start, span.end, offsets)):
            for ordinal, index in enumerate(selected):
                targets[index] = labels[("B-" if ordinal == 0 else "I-") + span.aspect]
            complete.add(key)
        else:
            for index in selected:
                targets[index] = -100
            partial.add(key)
    return targets, complete, partial


def labelled_windows(windows, spans, text: str, labels: dict[str, int]):
    rows, complete, partial_occurrences = [], set(), 0
    for window in windows:
        targets, covered, partial = aligned_labels(window, spans, text, labels)
        complete.update(covered)
        partial_occurrences += len(partial)
        if any(label != -100 for label in targets):
            rows.append({**window.features, "labels": targets})
    required = {span_key(span) for span in spans}
    if complete != required:
        raise ValueError("At least one gold span has no complete, exactly aligned window; no silent training exclusion.")
    if not rows:
        raise ValueError("No supervised tokens remain after partial-span masking.")
    return rows, {"window_count": len(windows), "training_row_count": len(rows),
                  "gold_span_count": len(required), "fully_represented_gold_spans": len(complete),
                  "masked_partial_span_occurrences": partial_occurrences}
