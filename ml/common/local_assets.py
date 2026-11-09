"""Review every local pretrained file before loading; never resolve a remote ID."""
from pathlib import Path
from .artifacts import read_json, safe_path, sha256


def approved_assets(config):
    root = config["_workspace"]
    folder = safe_path(config["model"]["local_path"], root)
    approval = read_json(safe_path(config["model"]["permission_path"], root))
    if approval.get("model_license_reviewed") is not True or not approval.get("license_reference") or not approval.get("model_revision"):
        raise ValueError("Reviewed local model license/revision is required.")
    files = [path for path in folder.rglob("*") if path.is_file()]
    if not files or len(files) > 2000 or not any(path.suffix == ".safetensors" for path in files):
        raise ValueError("A bounded local safetensors model is required.")
    for path in files:
        if not path.resolve().is_relative_to(folder):
            raise ValueError("Model file link escapes its approved directory.")
        if approval.get("files_sha256", {}).get(path.relative_to(folder).as_posix()) != sha256(path):
            raise ValueError("Local model file differs from its reviewed fingerprint.")
    return folder, approval
