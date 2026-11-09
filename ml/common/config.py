"""Strict task labels and local YAML configuration; no environment dumps."""
from pathlib import Path

LABELS = {
    "binary_imdb": {"negative": 0, "positive": 1},
    "three_class_movie": {"negative": 0, "neutral": 1, "positive": 2},
    "multilingual_movie": {"negative": 0, "neutral": 1, "positive": 2},
    "sarcasm": {"not_sarcastic": 0, "sarcastic": 1},
}


def load_config(path: str | Path) -> dict:
    path = Path(path).resolve()
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Oversized experiment configuration.")
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML is missing; install approved prerequisites manually.") from None
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1 or value.get("task") not in LABELS:
        raise ValueError("Configuration needs schema_version=1 and a supported explicit task.")
    def no_secrets(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if str(key).casefold() in {"password", "secret", "api_key", "token", "database_url", "access_token"}:
                    raise ValueError("Credentials do not belong in model configurations.")
                no_secrets(child)
        elif isinstance(item, list):
            for child in item:
                no_secrets(child)
    no_secrets(value)
    root = Path(value.get("workspace") or Path(__file__).resolve().parents[2]).resolve()
    # common is ml/common: repository root is parents[2].
    value["_workspace"] = root
    value["_config_path"] = path
    if value.get("labels", LABELS[value["task"]]) != LABELS[value["task"]]:
        raise ValueError("Configured labels conflict with the versioned task label map.")
    value["labels"] = dict(LABELS[value["task"]])
    if not isinstance(value.get("data"), dict) or not isinstance(value.get("output_dir"), str):
        raise ValueError("Configuration needs data and a fresh output_dir.")
    return value
