"""Evaluate a frozen trained local artifact; final test is explicitly reserved."""
from pathlib import Path
from ml.common.transformer_cli import evaluate_main

if __name__ == "__main__":
    raise SystemExit(evaluate_main(Path(__file__).with_name("config.yaml")))
