"""Optional adapter boundary; no invented Hindi transliterations or downloads."""
from .preprocess import AlignedView, preserve


def transliterate(text: str, reviewed_local_adapter=None) -> AlignedView:
    preserve(text)
    if reviewed_local_adapter is None:
        raise RuntimeError("No reviewed local transliteration adapter supplied; retain original input.")
    result = reviewed_local_adapter(text)
    if not isinstance(result, AlignedView) or result.original != text:
        raise ValueError("Transliteration requires original-text alignment and an unchanged original.")
    return result
