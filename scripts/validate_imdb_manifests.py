"""Verify a completed local IMDb audit/split run without rescanning review text."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataset_tools.manifest_validation import validate_imdb_manifests
from dataset_tools.io import status_exit

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = validate_imdb_manifests(args.run, args.output)
    except (ValueError, OSError, json.JSONDecodeError):
        result = {"status": "invalid", "error": "Manifest or output validation failed safely."}
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(status_exit(result))
