"""Script observations are distinct from a trained language identification model."""
from collections import Counter
import unicodedata


def observe_scripts(text: str) -> dict:
    counts = Counter()
    for character in text:
        if not character.isalpha():
            continue
        name = unicodedata.name(character, "")
        counts["Devanagari" if "DEVANAGARI" in name else "Latin" if "LATIN" in name else "Other"] += 1
    return {"script_letter_counts": dict(counts), "contains_multiple_scripts": len(counts) > 1,
            "language_code": None, "status": "script_observation_only",
            "note": "Latin letters do not distinguish English, Romanized Hindi or Hinglish."}


def detect_language(text: str, trained_detector=None) -> dict:
    if trained_detector is None:
        return {**observe_scripts(text), "status": "language_model_unavailable"}
    result = trained_detector.predict(text)
    if not isinstance(result, dict) or not result.get("model_version") or not result.get("language_code"):
        raise ValueError("A versioned trained language-detector contract is required.")
    return result
