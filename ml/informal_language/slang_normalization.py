"""Optional user-reviewed lexical expansions; no slang-to-sentiment dictionary."""
import re


def expansion_candidates(text: str, reviewed_mapping: dict[str, str]) -> list[dict]:
    if any(not isinstance(key, str) or not isinstance(value, str) or not key for key, value in reviewed_mapping.items()):
        raise ValueError("Slang expansions need a reviewed string mapping.")
    candidates = []
    for match in re.finditer(r"\w+(?:['’]\w+)*", text, flags=re.UNICODE):
        replacement = reviewed_mapping.get(match.group(0).casefold())
        if replacement is not None:
            candidates.append({"start": match.start(), "end": match.end(),
                               "original": match.group(0), "expansion": replacement})
    return candidates


def repeated_letter_spans(text: str) -> list[dict]:
    return [{"start": match.start(), "end": match.end(), "original": match.group(0),
             "repetitions": len(match.group(0))} for match in re.finditer(r"(?u)([^\W\d_])\1{2,}", text)]


def context_cues(text: str, reviewed_terms: dict[str, list[str]]) -> list[dict]:
    """Locate configured linguistic cues; no label or automatic polarity reversal."""
    result = []
    for kind, terms in reviewed_terms.items():
        if kind not in {"negation", "contrast"} or not isinstance(terms, list):
            raise ValueError("Only versioned negation/contrast cue terms are accepted.")
        for term in terms:
            if not isinstance(term, str) or not term:
                raise ValueError("Invalid cue term.")
            for match in re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, flags=re.IGNORECASE):
                result.append({"start": match.start(), "end": match.end(), "kind": kind})
    return sorted(result, key=lambda row: (row["start"], row["end"], row["kind"]))
