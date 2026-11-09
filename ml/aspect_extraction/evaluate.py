"""Evaluate real frozen extraction artifacts, never an annotation lookup."""
from pathlib import Path
from ml.aspect_common.cli import evaluate_main


if __name__ == "__main__":
    raise SystemExit(evaluate_main("aspect_extraction", Path(__file__).with_name("config.yaml")))
