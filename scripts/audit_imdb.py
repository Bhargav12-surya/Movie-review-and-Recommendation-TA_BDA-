"""Inspect only local aclImdb files; never download or train."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataset_tools.imdb import audit_imdb
from dataset_tools.io import status_exit
from dataset_tools.imdb import resolve_layout
from dataset_tools.resources import preflight


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="data/raw/acl_imdb")
    parser.add_argument("--output")
    parser.add_argument("--max-reviews", type=int)
    parser.add_argument("--near-duplicates", action="store_true")
    parser.add_argument("--near-threshold", type=float, default=.9)
    parser.add_argument("--candidate-limit", type=int, default=128)
    args = parser.parse_args()
    resources = preflight(Path(__file__).resolve().parents[1])
    if not args.max_reviews and resolve_layout(args.source).is_dir() and resources["blockers"]:
        print(json.dumps({"status": "partial", **resources}))
        return 4
    try:
        report = audit_imdb(args.source, args.output, max_reviews=args.max_reviews,
                            near_duplicates=args.near_duplicates,
                            near_threshold=args.near_threshold, candidate_limit=args.candidate_limit)
    except (ValueError, OSError, json.JSONDecodeError):
        print(json.dumps({"status": "invalid", "error": "Input/configuration/output validation failed; no training ran."}))
        return 2
    print(json.dumps(report, ensure_ascii=False, allow_nan=False))
    return status_exit(report)


if __name__ == "__main__":
    raise SystemExit(main())
