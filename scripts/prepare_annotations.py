"""Validate supplied human labels and character spans; never generate labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dataset_tools.annotations import validate_annotations
from dataset_tools.io import status_exit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default=str(ROOT / "data/raw/manual_annotations"))
    parser.add_argument("--registry")
    parser.add_argument("--output")
    parser.add_argument("--config", help="Explicit approved annotation taxonomy configuration.")
    parser.add_argument("--workspace", default=str(ROOT))
    parser.add_argument("--write-accepted", action="store_true")
    parser.add_argument("--allow-mixed", action="store_true",
                        help="Use only after approving a separate mixed aspect/theme label policy.")
    args = parser.parse_args(argv)
    try:
        report = validate_annotations(args.source, args.registry, args.output, args.workspace,
                                      args.allow_mixed, args.write_accepted, args.config)
    except (OSError, ValueError) as error:
        report = {"schema_version": 1, "source": "human_movie_review_annotations", "status": "invalid",
                  "blockers": [str(error)], "issues": {}, "counts": {}}
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    return status_exit(report)


if __name__ == "__main__":
    raise SystemExit(main())
