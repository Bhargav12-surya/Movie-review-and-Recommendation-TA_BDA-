"""Bounded permission-checked local records for non-sentiment experiments."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
from .artifacts import read_json, safe_path, sha256
from .data import _rows


@dataclass
class RecordBundle:
    records: dict
    manifest_hashes: dict
    labels: dict

    def summary(self):
        return {"manifest_hashes": self.manifest_hashes, "splits": {key: {"count": len(rows)} for key, rows in self.records.items()}, "labels": self.labels}


def load_config(path):
    path = Path(path).resolve()
    config = read_json(path)
    config.update(_config_path=path, _workspace=Path(config.get("workspace") or Path(__file__).resolve().parents[2]).resolve())
    return config


def permitted_rows(path, maximum=10000, purpose="training"):
    permission = {"training": "training_permitted", "inference": "inference_permitted", "evidence": "evidence_permitted", "moderation": "moderation_use_permitted"}.get(purpose)
    if permission is None:
        raise ValueError("Specify the actual permitted processing purpose.")
    rows, total = [], 0
    for row in _rows(path):
        if len(rows) >= maximum:
            raise ValueError("Local input record budget exceeded.")
        if row.get("is_synthetic") is not False or row.get("is_deleted") is not False or row.get(permission) is not True or not row.get("consent_or_license_ref"):
            raise ValueError("Original source permission and non-synthetic eligibility are required.")
        if any(term in str(row.get("source", "")).casefold() for term in ("synthetic", "fictional", "demo")):
            raise ValueError("Synthetic/demo sources cannot enter real experiments or evidence.")
        if "text" in row and (not isinstance(row["text"], str) or not row["text"].strip() or
            hashlib.sha256(row["text"].encode("utf-8")).hexdigest() != row.get("text_sha256")):
            raise ValueError("Actual original-text SHA256 is required.")
        total += len(str(row).encode("utf-8"))
        if total > 128 * 1024**2:
            raise ValueError("Local record memory budget exceeded.")
        rows.append(row)
    if not rows:
        raise ValueError("No legitimate local records supplied.")
    return rows


def load_bundle(config):
    root, data = config["_workspace"], config["data"]
    hashes, records, owners = {}, {}, {}
    for split in ("train", "tuning", "calibration", "test"):
        path = safe_path(data["manifests"][split], root)
        hashes[split] = sha256(path)
        rows = permitted_rows(path)
        for row in rows:
            if row.get("split") != split or not isinstance(row.get("record_id"), str) or not row["record_id"] or not isinstance(row.get("group_id"), str) or not row["group_id"]:
                raise ValueError("Explicit record/split/leakage-group identities are required.")
            keys = [("id", row["record_id"]), ("group", row["group_id"])]
            if row.get("text_sha256"):
                keys.append(("text", row["text_sha256"]))
            for key in keys:
                if key in owners and (owners[key] != split or key[0] == "id"):
                    raise ValueError("Duplicate or cross-split experimental record/group.")
                owners[key] = split
        if sha256(path) != hashes[split]:
            raise ValueError("Input changed during validation.")
        records[split] = rows
    return RecordBundle(records, hashes, {})
