"""Versioned aspect taxonomy and bounded local experiment configuration."""
from pathlib import Path
from ml.common.artifacts import read_json, safe_path

COMPONENTS = {"aspect_extraction", "aspect_sentiment"}
SENTIMENT_LABELS = {"negative": 0, "neutral": 1, "positive": 2}


def load_config(path: str | Path) -> dict:
    import yaml
    path = Path(path).resolve()
    if path.stat().st_size > 1024**2:
        raise ValueError("Aspect configuration exceeds its metadata bound.")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1 or value.get("task") not in COMPONENTS:
        raise ValueError("An explicit supported aspect task and schema_version=1 are required.")
    def reject_secrets(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if str(key).casefold() in {"password", "secret", "api_key", "access_token", "database_url", "token"}:
                    raise ValueError("Credentials do not belong in model configurations.")
                reject_secrets(child)
        elif isinstance(item, list):
            for child in item:
                reject_secrets(child)
    reject_secrets(value)
    root = Path(value.get("workspace") or Path(__file__).resolve().parents[2]).resolve()
    value.update(_workspace=root, _config_path=path)
    taxonomy_path = safe_path(value.get("taxonomy_path", "configs/data/annotations.json"), root)
    taxonomy = read_json(taxonomy_path)
    aspects = taxonomy.get("aspects")
    if (taxonomy.get("aspect_taxonomy_version") != "movie-aspects-v1" or not isinstance(aspects, list)
        or len(aspects) != 16 or len(set(aspects)) != 16 or any(not isinstance(name, str) or not name for name in aspects)):
        raise ValueError("The approved starting sixteen-aspect taxonomy is required.")
    value["taxonomy"] = {"version": taxonomy["aspect_taxonomy_version"], "aspects": aspects}
    labels = dict(SENTIMENT_LABELS)
    if value["task"] == "aspect_extraction":
        names = ["O"] + [prefix + name for name in aspects for prefix in ("B-", "I-")]
        labels = {name: index for index, name in enumerate(names)}
    if value.get("labels", labels) != labels:
        raise ValueError("Configured class order differs from the frozen task taxonomy.")
    value["labels"] = labels
    if not isinstance(value.get("data"), dict) or not isinstance(value.get("output_dir"), str):
        raise ValueError("Data contracts and a fresh output directory are required.")
    languages = value.get("language_scope")
    if not isinstance(languages, list) or not languages or any(code not in {"en", "hi", "hi-Latn", "mul"} for code in languages):
        raise ValueError("Declare the requested, later evaluated language scope.")
    tokens = value.setdefault("tokenization", {})
    for key, default, low, high in (("maximum_sequence_length", 128, 32, 512), ("stride", 32, 0, 256),
                                  ("maximum_windows_per_review", 128, 1, 256), ("maximum_training_rows", 30000, 1, 100000)):
        tokens.setdefault(key, default)
        if type(tokens[key]) is not int or not low <= tokens[key] <= high:
            raise ValueError("Tokenization setting is outside its laptop bound: " + key)
    if tokens["stride"] >= tokens["maximum_sequence_length"] - 16:
        raise ValueError("Stride leaves insufficient token-window progress.")
    return value
