"""Create leakage-aware local reference manifests, never alter official splits."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataset_tools.imdb import prepare_imdb
from dataset_tools.io import status_exit
from dataset_tools.imdb import resolve_layout
from dataset_tools.resources import preflight


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="data/raw/acl_imdb")
    parser.add_argument("--output", required=True)
    parser.add_argument("--validation-fraction", type=float, default=.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-near-duplicates", action="store_true")
    parser.add_argument("--provenance")
    args = parser.parse_args()
    resources = preflight(Path(__file__).resolve().parents[1])
    if resolve_layout(args.source).is_dir() and resources["blockers"]:
        print(json.dumps({"status": "partial", **resources}))
        return 4
    try:
        report = prepare_imdb(args.source, args.output, validation_fraction=args.validation_fraction,
                              seed=args.seed, near_duplicates=not args.skip_near_duplicates,
                              provenance=args.provenance)
    except (ValueError, OSError, json.JSONDecodeError):
        print(json.dumps({"status": "invalid", "error": "Input/configuration/output validation failed; raw data preserved."}))
        return 2
    print(json.dumps(report, ensure_ascii=False, allow_nan=False))
    return status_exit(report)


if __name__ == "__main__":
    raise SystemExit(main())
