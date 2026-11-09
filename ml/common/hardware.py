"""Explicit device selection, precision probes and laptop resource guards."""
from __future__ import annotations
import ctypes
import os
import shutil
from pathlib import Path


def resources(workspace: str | Path) -> dict:
    result = {"free_disk_bytes": shutil.disk_usage(workspace).free, "available_memory_bytes": None}
    if os.name == "nt":
        class Status(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in ("total", "available", "page", "available_page",
                                                       "virtual", "available_virtual", "extended")]
        status = Status()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            result["available_memory_bytes"] = status.available
    return result


def guard_resources(config: dict, checkpoint_bytes: int = 0) -> dict:
    result = resources(config["_workspace"])
    settings = config.get("resources", {})
    disk = int(settings.get("minimum_disk_free_gib", 20)) * 1024**3 + checkpoint_bytes
    memory = int(settings.get("minimum_available_memory_mib", 3072)) * 1024**2
    if result["free_disk_bytes"] < disk:
        raise RuntimeError("Insufficient SSD reserve for this run/checkpoint.")
    if result["available_memory_bytes"] is not None and result["available_memory_bytes"] < memory:
        raise RuntimeError("Insufficient currently available RAM; close workloads before training.")
    return result


def verify_device(settings: dict) -> tuple[object, object | None, dict]:
    import torch
    requested = settings.get("device", "cuda")
    if requested not in {"cpu", "cuda"}:
        raise ValueError("Training device must explicitly be cpu or cuda.")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested CUDA is unavailable; a long CPU fallback is not authorized.")
    device = torch.device(requested)
    info = {"torch_version": torch.__version__, "cuda_runtime": torch.version.cuda,
            "device": requested, "precision": "float32"}
    if requested == "cpu":
        if settings.get("precision", "float32") not in {"auto", "float32"}:
            raise ValueError("CPU tests use explicit float32 precision.")
        return device, None, info
    info.update(gpu=torch.cuda.get_device_name(0), capability=list(torch.cuda.get_device_capability(0)),
                compiled_architectures=torch.cuda.get_arch_list())
    probe = torch.randn((8, 8), device=device)
    torch.cuda.synchronize()
    if not torch.isfinite(probe @ probe.T).all().item():
        raise RuntimeError("CUDA tensor verification failed.")
    requested_precision = settings.get("precision", "auto")
    if requested_precision not in {"auto", "float32", "fp16", "bf16"}:
        raise ValueError("Unknown precision choice.")
    candidates = ["bf16", "fp16"] if requested_precision == "auto" else [requested_precision]
    for name in candidates:
        if name == "float32":
            return device, None, info
        if name == "bf16" and not torch.cuda.is_bf16_supported():
            continue
        dtype = torch.bfloat16 if name == "bf16" else torch.float16
        value = probe.to(dtype=dtype)
        try:
            valid = bool(torch.isfinite(value @ value.T).all().item())
            torch.cuda.synchronize()
        except RuntimeError:
            valid = False
        if valid:
            del probe, value
            torch.cuda.reset_peak_memory_stats()
            info["precision"] = name
            return device, dtype, info
    raise RuntimeError("Requested mixed precision did not pass an actual tensor probe.")
