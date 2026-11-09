"""Explicit manual provenance, experiment approval and final-test reservations."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from .artifacts import read_json, safe_path, sha256, write_json
from .data import load_experiment


def training_preflight(config: dict, bundle=None, component: str = "transformer") -> dict:
    blockers = []
    try:
        bundle = bundle or load_experiment(config)
    except (OSError, ValueError, KeyError, TypeError) as error:
        blockers.append("Validated experiment manifests are missing or invalid: " + type(error).__name__)
    approval = config.get("approval_path")
    if not approval:
        blockers.append("A manually approved experiment record is required.")
    else:
        try:
            record = read_json(safe_path(approval, config["_workspace"]))
            if any(record.get(key) is not True for key in
                   ("source_permission_reviewed", "label_policy_approved", "split_reviewed", "training_approved")):
                blockers.append("Source/labels/split/training approvals are incomplete.")
            if record.get("task") != config["task"] or record.get("component") != component:
                blockers.append("Approval does not cover this task/component.")
            if bundle and record.get("manifest_hashes") != bundle.manifest_hashes:
                blockers.append("Approval does not match the frozen manifest hashes.")
            if record.get("config_sha256") != sha256(config["_config_path"]):
                blockers.append("Approval does not match this exact training configuration.")
            if not record.get("approved_by") or not record.get("run_id"):
                blockers.append("Approval attribution and run ID are missing.")
        except (OSError, ValueError, TypeError):
            blockers.append("Approval record is missing or unreadable.")
    provenance = config["data"].get("provenance_path")
    try:
        source = read_json(safe_path(provenance, config["_workspace"])) if provenance else {}
        if source.get("training_permitted") is not True or not source.get("license_or_consent_reference"):
            blockers.append("Reviewed training permission/provenance is missing.")
    except (OSError, ValueError, TypeError):
        blockers.append("Source provenance record is unavailable.")
    return {"ready": not blockers, "blockers": blockers,
            "data": bundle.summary() if bundle else None, "training_started": False,
            "config_sha256": sha256(config["_config_path"]),
            "automatic_downloads": False}


def require_training_approval(config: dict, bundle, component: str = "transformer") -> None:
    report = training_preflight(config, bundle, component)
    if not report["ready"]:
        raise ValueError("Training blocked: " + " ".join(report["blockers"]))


def reserve_final_test(run_dir: str | Path, bundle, split: str, final_test: bool) -> None:
    if split != "test":
        return
    if not final_test:
        raise ValueError("Held-out test needs an explicit final-test action after model selection.")
    marker = Path(run_dir) / "final_test_reservation.json"
    write_json(marker, {"reserved_at": datetime.now(timezone.utc).isoformat(),
                       "manifest_hashes": bundle.manifest_hashes,
                       "policy": "One final attempt; failed attempts remain visible and require review."})
