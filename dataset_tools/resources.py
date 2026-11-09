"""Read-only resource preflight for bounded data jobs."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

from scripts._verification_common import resource_snapshot


def preflight(workspace: str | Path, memory_mib: int = 512, disk_gib: int = 20) -> dict:
    measured = resource_snapshot(Path(workspace).resolve())
    blockers = []
    if measured["disk"]["free_bytes"] < disk_gib * 1024**3:
        blockers.append(f"Less than the {disk_gib} GiB free-disk reserve.")
    memory = measured["memory"]
    if memory.get("status") == "measured" and memory["available_bytes"] < memory_mib * 1024**2:
        blockers.append(f"Less than {memory_mib} MiB available RAM for a full validation run.")
    return {"measurements": measured, "blockers": blockers}


def peak_working_set_bytes() -> int | None:
    if os.name != "nt":
        return None
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong),
                    ("peak", ctypes.c_size_t), ("working", ctypes.c_size_t),
                    ("peak_paged", ctypes.c_size_t), ("paged", ctypes.c_size_t),
                    ("peak_nonpaged", ctypes.c_size_t), ("nonpaged", ctypes.c_size_t),
                    ("pagefile", ctypes.c_size_t), ("peak_pagefile", ctypes.c_size_t)]
    value = Counters()
    value.cb = ctypes.sizeof(value)
    if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(value), value.cb):
        return int(value.peak)
    return None
