"""Compare actual fixed-split experiment reports; never infer improvements."""
import argparse
import json
from pathlib import Path
from ml.common.artifacts import read_json


def compare_reports(paths: list[str | Path]) -> dict:
    if len(paths) < 2:
        raise ValueError("At least two actual evaluation reports are required.")
    reports = [read_json(path) for path in paths]
    first = reports[0]
    if first.get("split") != "test":
        raise ValueError("Final ablation comparison requires frozen held-out test reports.")
    for report in reports:
        if any(report.get(key) != first.get(key) for key in ("task", "split", "manifest_hashes")):
            raise ValueError("Ablation reports use different tasks or held-out datasets.")
        if not report.get("metrics", {}).get("count"):
            raise ValueError("An actual evaluation support count is required.")
    return {"task": first["task"], "manifest_hashes": first["manifest_hashes"],
            "baseline": reports[0]["metrics"], "comparisons": [
                {"metrics": report["metrics"], "macro_f1_difference": report["metrics"]["macro_f1"] - first["metrics"]["macro_f1"],
                 "accuracy_difference": report["metrics"]["accuracy"] - first["metrics"]["accuracy"]}
                for report in reports[1:]], "causality_claim": False,
            "note": "Input reports must identify the controlled ablation; differences alone do not prove causation."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+")
    args = parser.parse_args()
    print(json.dumps(compare_reports(args.reports), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
