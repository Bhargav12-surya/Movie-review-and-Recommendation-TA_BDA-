"""Read-only helpers shared by the project verification commands.

Only an explicitly requested new report file may be written. No application,
legacy module, package installer, dataset reader, or model loader is imported.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone


PROFILES = ("Foundation", "Data", "Spark", "Nlp", "Backend", "Frontend", "All")


def default_config() -> dict:
    return {
        "schema_version": 1,
        "python": {"path": ".venv/Scripts/python.exe", "version": "3.11.9"},
        "java": {
            "home": "C:/Program Files/Eclipse Adoptium/jdk-21.0.12.101-hotspot",
            "major": 21,
        },
        "spark": {"version": "4.3.0", "scala_version": "2.13.18"},
        "sbt": {"version": "1.10.7"},
        "resources": {
            "minimum_disk_free_gib": 20,
            "minimum_available_memory_mib": 512,
        },
    }


def load_config(workspace: Path, config_path: str | None) -> tuple[dict, str | None]:
    path = Path(config_path) if config_path else workspace / "configs/environment.json"
    if not path.is_absolute():
        path = workspace / path
    if not path.exists():
        if config_path:
            raise ValueError(f"Explicit configuration file does not exist: {path}")
        return default_config(), None
    with path.open(encoding="utf-8-sig") as handle:
        config = json.load(handle)
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("Environment configuration must be an object with schema_version=1.")
    for key in ("python", "java", "spark", "sbt", "resources"):
        if not isinstance(config.get(key), dict):
            raise ValueError(f"Configuration section {key!r} must be an object.")
    return config, str(path.resolve())


def executable(name: str) -> str | None:
    """Look only on the current process PATH; do not start a resolver."""
    return shutil.which(name)


def run_program(arguments: list[str], timeout: float = 15,
                environment: dict[str, str] | None = None) -> dict:
    """Run a bounded, noninteractive local diagnostic without a console window."""
    child_env = os.environ.copy()
    if environment:
        child_env.update(environment)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        process = subprocess.run(
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env=child_env,
            creationflags=flags,
        )
        return {
            "exit_code": process.returncode,
            "stdout": process.stdout[:12000],
            "stderr": process.stderr[:4000],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": None, "stdout": "", "stderr": "",
                "timed_out": True, "error": f"Diagnostic exceeded {timeout:g} seconds."}
    except OSError as error:
        return {"exit_code": None, "stdout": "", "stderr": "",
                "timed_out": False, "error": str(error)}


def memory_snapshot() -> dict:
    if os.name != "nt":
        return {"status": "unavailable", "reason": "Windows memory API is unavailable."}

    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong), ("load_percent", ctypes.c_ulong),
            ("total_physical", ctypes.c_ulonglong),
            ("available_physical", ctypes.c_ulonglong),
            ("total_pagefile", ctypes.c_ulonglong),
            ("available_pagefile", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("available_virtual", ctypes.c_ulonglong),
            ("available_extended_virtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return {"status": "unavailable", "reason": "GlobalMemoryStatusEx failed."}
    return {
        "status": "measured",
        "method": "GlobalMemoryStatusEx",
        "total_bytes": status.total_physical,
        "available_bytes": status.available_physical,
        "available_mib": round(status.available_physical / 1024**2, 2),
        "load_percent": status.load_percent,
    }


def resource_snapshot(workspace: Path) -> dict:
    disk = shutil.disk_usage(workspace)
    return {
        "disk": {
            "path": str(workspace),
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "free_gib": round(disk.free / 1024**3, 3),
        },
        "memory": memory_snapshot(),
    }


def new_report(command: str, workspace: Path) -> dict:
    return {
        "schema_version": 1,
        "command": command,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace),
        "platform": platform.platform(),
        "checks": [],
        "notes": [],
    }


def add_check(report: dict, check_id: str, status: str, detail: str,
              *, required: bool = False, phase: int = 0, **evidence) -> None:
    report["checks"].append({
        "id": check_id, "status": status, "required": required,
        "phase": phase, "detail": detail, **evidence,
    })


def finalize(report: dict) -> int:
    blocked = [
        check["id"] for check in report["checks"]
        if check["required"] and check["status"] != "pass"
    ]
    report["ready"] = not blocked
    report["blocking_checks"] = blocked
    report["missing_prerequisites"] = [
        check["id"] for check in report["checks"]
        if check["status"] == "missing"
    ]
    report["exit_code"] = 2 if blocked else 0
    return report["exit_code"]


def validate_output_path(workspace: Path, output: str | None) -> Path | None:
    if not output:
        return None
    requested = Path(output)
    if not requested.is_absolute():
        requested = workspace / requested
    # resolve() follows existing junctions/symlinks before containment checks.
    target = requested.resolve()
    workspace = workspace.resolve()
    if not target.is_relative_to(workspace):
        raise ValueError("Report output must stay inside the project workspace.")
    for relative in ("data/raw", ".git", ".venv", "temp"):
        protected = (workspace / relative).resolve()
        if target == protected or target.is_relative_to(protected):
            raise ValueError(f"Reports cannot be written under protected path {relative}.")
    if target.exists():
        raise ValueError("Report output already exists; existing files are never overwritten.")
    if not target.parent.is_dir():
        raise ValueError("Report parent directory must already exist; no folders are auto-created.")
    return target


def emit_report(report: dict, output: Path | None, as_json: bool) -> None:
    payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)
    if output is not None:
        # Exclusive creation closes a time-of-check/time-of-use overwrite race.
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload + "\n")
    if as_json:
        print(payload)
    else:
        print(f"{report['command']} — {report.get('profile', 'services')}")
        for check in report["checks"]:
            print(f"{check['status'].upper():12} {check['id']}: {check['detail']}")
        print(f"Ready for selected scope: {report.get('ready', False)}")
        if report.get("blocking_checks"):
            print("Blocked: " + ", ".join(report["blocking_checks"]))


def fail_report(report: dict, error: Exception, as_json: bool) -> int:
    # Never echo configuration objects or environment-variable dumps.
    add_check(report, "verification.error", "fail", str(error), required=True)
    report.update(ready=False, blocking_checks=["verification.error"], exit_code=1)
    emit_report(report, None, as_json)
    return 1
