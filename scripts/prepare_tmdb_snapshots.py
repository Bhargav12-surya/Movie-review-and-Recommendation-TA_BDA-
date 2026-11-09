"""Validate manually supplied TMDB snapshots; never call an external API."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dataset_tools.io import status_exit
from dataset_tools.tmdb import validate_tmdb_snapshots


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default=str(ROOT / "data/raw/tmdb_snapshots"))
    parser.add_argument("--provenance")
    parser.add_argument("--output")
    parser.add_argument("--workspace", default=str(ROOT))
    parser.add_argument("--write-accepted", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = validate_tmdb_snapshots(args.source, args.provenance, args.output,
                                         args.workspace, args.write_accepted)
    except (OSError, ValueError) as error:
        report = {"schema_version": 1, "source": "tmdb_local_metadata", "status": "invalid",
                  "blockers": [str(error)], "issues": {}, "counts": {}}
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    return status_exit(report)


if __name__ == "__main__":
    raise SystemExit(main())
