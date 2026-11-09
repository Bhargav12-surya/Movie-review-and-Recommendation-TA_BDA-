"""Fresh-only local experiment artifacts. No pickle/joblib deserialization."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def sha256(path: str | Path) -> str:
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(part)
    return result.hexdigest()


def safe_path(value: str | Path, workspace: str | Path, output: bool = False) -> Path:
    root = Path(workspace).resolve()
    given = Path(value)
    target = (given if given.is_absolute() else root / given).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError("Experiment paths must remain below the workspace.")
    relative = [part.casefold() for part in target.relative_to(root).parts]
    if any(part in {".git", ".venv", "venv", "node_modules", "temp"} for part in relative):
        raise ValueError("Experiment path enters preserved source/dependency storage.")
    if output and target.is_relative_to((root / "data/raw").resolve()):
        raise ValueError("Raw datasets are read-only.")
    return target


def read_json(path: str | Path, max_bytes: int = 4 * 1024 * 1024) -> dict:
    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise ValueError("JSON metadata exceeds its bounded size.")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON metadata key.")
            result[key] = value
        return result
    def reject(value):
        raise ValueError("Nonfinite JSON metadata.")
    result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=reject)
    if not isinstance(result, dict):
        raise ValueError("Expected a metadata object.")
    return result


def write_json(path: str | Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


def create_run(config: dict, component: str) -> Path:
    target = safe_path(config["output_dir"], config["_workspace"], output=True)
    target.mkdir(parents=True, exist_ok=False)
    public = {key: value for key, value in config.items() if not key.startswith("_")}
    # Configuration has paths/settings only. Credentials have no role in model runs.
    write_json(target / "experiment.json", {"component": component, "config": public,
        "source_config_sha256": sha256(config["_config_path"]), "status": "started"})
    return target
