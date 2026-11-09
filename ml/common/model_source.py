"""Locally supplied safetensors/tokenizer artifacts and explicit model license gate."""
from importlib import metadata
from pathlib import Path
from .artifacts import read_json, safe_path, sha256


def verify_local_model(config: dict) -> tuple[Path | None, list[str]]:
    blockers = []
    source = config.get("model", {}).get("local_path")
    approval = config.get("model", {}).get("permission_path")
    if not source or not approval:
        return None, ["Supply local pretrained safetensors/tokenizer and a reviewed model permission record."]
    try:
        folder = safe_path(source, config["_workspace"])
        record = read_json(safe_path(approval, config["_workspace"]))
        if record.get("model_license_reviewed") is not True or not record.get("license_reference") or not record.get("model_revision"):
            blockers.append("Model license/revision review is incomplete.")
        if not (folder / "config.json").is_file() or not list(folder.glob("*.safetensors")):
            blockers.append("Local model config/safetensors weights are missing.")
        tokenizer_assets = ((folder / "tokenizer.json").is_file() or (folder / "vocab.txt").is_file() or
            (folder / "sentencepiece.bpe.model").is_file() or (folder / "spiece.model").is_file() or
            (folder / "tokenizer.model").is_file() or
            ((folder / "vocab.json").is_file() and (folder / "merges.txt").is_file()))
        if not (folder / "tokenizer_config.json").is_file() or not tokenizer_assets:
            blockers.append("Reviewed tokenizer configuration/assets are incomplete.")
        files = record.get("files_sha256", {})
        required = [path for path in folder.iterdir() if path.is_file() and path.suffix in
                    {".json", ".safetensors", ".txt", ".model", ".vocab"}]
        if not required or any(files.get(path.name) != sha256(path) for path in required):
            blockers.append("Model/tokenizer files do not match the reviewed hashes.")
        return folder, blockers
    except (OSError, ValueError, TypeError):
        return None, ["Local model source/permission metadata is unavailable or invalid."]


def dependency_blockers() -> list[str]:
    missing = []
    for package in ("torch", "transformers", "datasets", "safetensors", "numpy"):
        try:
            metadata.version(package)
        except metadata.PackageNotFoundError:
            missing.append("Missing manually installed dependency: " + package)
    return missing
