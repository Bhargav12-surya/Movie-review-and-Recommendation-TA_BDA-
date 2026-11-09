"""CLI dispatch; never installs dependencies or fetches input data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .inventory import inventory_raw
from .io import base_report, project_root, status_exit, write_json_new
from .mapping import build_provisional_movie_map, validate_movie_ids
from .movielens import audit_movielens


def main(argv: list[str] | None = None, kind: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    if kind is None:
        parser.add_argument("--kind", choices=("inventory", "movielens", "mapping"),
                            default="inventory")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workspace", type=Path, default=project_root())
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    selected = kind or args.kind
    root = args.workspace.resolve()
    source = args.source or root / ("data/raw" if selected == "inventory"
                                  else "data/raw/movielens/ml-32m")
    try:
        if not source.resolve().is_relative_to(root):
            raise ValueError("Input must remain inside the explicitly selected workspace.")
        if any(part in {".git", ".venv", "temp", "node_modules"}
               for part in source.resolve().relative_to(root).parts):
            raise ValueError("Legacy, Git and dependency directories are not raw dataset sources.")
        if args.max_rows is not None and selected != "movielens":
            raise ValueError("--max-rows is only supported by the MovieLens CSV validator.")
        if selected == "inventory":
            report = inventory_raw(source)
            if args.output:
                # Inventory writes one new JSON file, other commands write new dirs.
                write_json_new(args.output, report, root)
        elif selected == "movielens":
            expected = None
            if args.config:
                with args.config.open(encoding="utf-8") as handle:
                    config = json.load(handle)
                if not isinstance(config, dict):
                    raise ValueError("Dataset configuration must be a JSON object.")
                expected = config.get("expected_counts")
                if expected is not None and (not isinstance(expected, dict) or any(
                        key not in {"movies", "links", "ratings", "tags", "users"}
                        or isinstance(value, bool) or not isinstance(value, int) or value < 0
                        for key, value in expected.items())):
                    raise ValueError("expected_counts must contain known source names and nonnegative integers.")
            report = audit_movielens(source, args.output, args.max_rows, expected, root)
        elif selected == "mapping":
            report = validate_movie_ids(source)
            if args.output:
                report = build_provisional_movie_map(source, args.output, root)
        elif selected == "build_mapping":
            if not args.output:
                raise ValueError("A new --output directory is required for mapping export.")
            report = build_provisional_movie_map(source, args.output, root)
        else:
            raise ValueError("Unknown validator.")
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = base_report(selected)
        report.update(status="invalid",
                      blockers=[f"Validation could not run safely: {type(error).__name__}: {error}"])
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    return status_exit(report)
