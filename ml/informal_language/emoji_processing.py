"""Conservative Unicode symbol observations; symbols have no fixed polarity."""
import unicodedata


def symbol_spans(text: str) -> list[dict]:
    result = []
    index = 0
    while index < len(text):
        character = text[index]
        if unicodedata.category(character) == "So" or 0x1F000 <= ord(character) <= 0x1FAFF or 0x2600 <= ord(character) <= 0x27BF:
            end = index + 1
            while end < len(text) and (text[end] in "\ufe0f\ufe0e\u200d" or
                    unicodedata.category(text[end]) in {"So", "Mn", "Sk"}):
                end += 1
            result.append({"start": index, "end": end, "text": text[index:end],
                           "kind": "unicode_symbol_run", "polarity": None})
            index = end
        else:
            index += 1
    return result


def remove_symbols_for_ablation(text: str) -> str:
    spans = symbol_spans(text)
    pieces, cursor = [], 0
    for span in spans:
        pieces.extend([text[cursor:span["start"]], " "])
        cursor = span["end"]
    pieces.append(text[cursor:])
    return "".join(pieces)
