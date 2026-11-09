"""Streaming inventory of local raw sources, without reading private text."""
from __future__ import annotations

from collections import Counter
import os
from pathlib import Path

from .io import base_report


def inventory_raw(root: str | Path) -> dict:
    source = Path(root).resolve()
    report = base_report("local_raw_inventory")
    if not source.is_dir():
        report.update(status="missing", blockers=["Raw dataset directory is absent."])
        return report
    extensions: Counter = Counter()
    sources: dict[str, dict] = {
        path.name: {"files": 0, "bytes": 0}
        for path in source.iterdir()
        if path.is_dir() and not path.is_symlink()
        and path.name not in {".git", ".venv", "node_modules", "__pycache__"}
    }
    files = total_bytes = 0
    # os.walk yields bounded directory batches; no full file-list materialization.
    for current, directories, filenames in os.walk(source, followlinks=False):
        directories[:] = [name for name in directories
                          if name not in {".git", ".venv", "node_modules", "__pycache__"}
                          and not (Path(current) / name).is_symlink()
                          and (Path(current) / name).resolve().is_relative_to(source)]
        for name in filenames:
            path = Path(current) / name
            if path.is_symlink() or not path.resolve().is_relative_to(source):
                continue
            relative = path.relative_to(source)
            key = relative.parts[0] if len(relative.parts) > 1 else "_root"
            info = sources.setdefault(key, {"files": 0, "bytes": 0})
            size = path.stat().st_size
            files += 1
            total_bytes += size
            info["files"] += 1
            info["bytes"] += size
            extensions[path.suffix.lower() or "(none)"] += 1
    report["counts"] = {"files": files, "bytes": total_bytes,
                        "extensions": dict(sorted(extensions.items())),
                        "sources": dict(sorted(sources.items()))}
    report["checks_complete"] = ["streaming_file_inventory"]
    report["notes"] = ["No content, recursive file list, model or legacy database was loaded.",
                       "File counts are a snapshot, not integrity or licensing verification."]
    return report
