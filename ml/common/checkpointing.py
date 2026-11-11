"""Owned versioned checkpoints with verified hashes and weights-only reload."""
from __future__ import annotations
import random
from pathlib import Path
from .artifacts import read_json, sha256, write_json
from .hardware import guard_resources


def seed_everything(seed: int) -> None:
    import numpy as np
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def rng_state() -> dict:
    import numpy as np
    import torch
    numpy = np.random.get_state()
    return {"python": random.getstate(), "numpy": [numpy[0], numpy[1].tolist(), *numpy[2:]],
            "torch": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else []}


def restore_rng(state: dict) -> None:
    import numpy as np
    import torch
    random.setstate(state["python"])
    numpy = state["numpy"]
    np.random.set_state((numpy[0], np.asarray(numpy[1], dtype="uint32"), *numpy[2:]))
    torch.set_rng_state(state["torch"])
    if state["cuda"]:
        if not torch.cuda.is_available() or len(state["cuda"]) != torch.cuda.device_count():
            raise RuntimeError("CUDA checkpoint devices differ; explicit migration review required.")
        torch.cuda.set_rng_state_all(state["cuda"])


def save_checkpoint(path: Path, model, optimizer, scheduler, scaler, progress: dict,
                    manifest_hashes: dict, config: dict) -> None:
    import torch
    # Preserve earlier checkpoints; never delete/overwrite artifacts to make room.
    maximum = int(config.get("training", {}).get("maximum_checkpoint_count", 8))
    if path.parent.exists() and len(list(path.parent.glob("checkpoint-*"))) >= maximum:
        raise RuntimeError("Checkpoint-count budget reached; review run/retention before continuing.")
    estimated = sum(value.numel() * value.element_size() for value in model.parameters()) * 4
    guard_resources(config, estimated, operation="checkpoint")
    path.mkdir(parents=True, exist_ok=False)
    state = {"model": model.state_dict(), "optimizer": optimizer.state_dict(),
             "scheduler": scheduler.state_dict(), "scaler": scaler.state_dict(),
             "rng": rng_state(), "progress": progress}
    state_path = path / "state.pt"
    torch.save(state, state_path)
    write_json(path / "checkpoint.json", {"schema_version": 1, "kind": "owned_training_state",
        "state_sha256": sha256(state_path), "manifest_hashes": manifest_hashes,
        "config_sha256": sha256(config["_config_path"]),
        "input_contract_sha256": config["_input_contract_sha256"], "progress": progress})


def load_checkpoint(path: Path, model, optimizer, scheduler, scaler,
                    manifest_hashes: dict, config: dict) -> dict:
    import torch
    metadata = read_json(path / "checkpoint.json")
    if metadata.get("kind") != "owned_training_state" or metadata.get("schema_version") != 1:
        raise ValueError("Not an owned checkpoint. Legacy/untrusted weights are not loaded.")
    if metadata.get("manifest_hashes") != manifest_hashes or metadata.get("config_sha256") != sha256(config["_config_path"]):
        raise ValueError("Resume dataset/configuration differs from its checkpoint.")
    if metadata.get("input_contract_sha256") != config["_input_contract_sha256"]:
        raise ValueError("Resume tokenizer/base model/text view differs from its checkpoint.")
    state_path = path / "state.pt"
    if sha256(state_path) != metadata.get("state_sha256"):
        raise ValueError("Checkpoint hash verification failed.")
    state = torch.load(state_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state["model"])
    optimizer.load_state_dict(state["optimizer"])
    scheduler.load_state_dict(state["scheduler"])
    scaler.load_state_dict(state["scaler"])
    restore_rng(state["rng"])
    return state["progress"]
