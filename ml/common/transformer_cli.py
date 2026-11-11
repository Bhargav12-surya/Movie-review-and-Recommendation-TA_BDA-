"""Thin commands shared by sentiment/multilingual/sarcasm component bundles."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .config import load_config


def train_main(component: str, default_config: Path) -> int:
    parser = argparse.ArgumentParser(description="Local-only supervised training; default is preflight, never a fit.")
    parser.add_argument("--config", default=str(default_config))
    parser.add_argument("--execute", action="store_true", help="Explicitly execute the separately approved run.")
    parser.add_argument("--resume-checkpoint")
    args = parser.parse_args()
    try:
        from .transformer_engine import preflight, train
        config = load_config(args.config)
        report = train(config, component, args.resume_checkpoint) if args.execute else preflight(config, component)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if args.execute or report["ready"] else 2
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        import traceback
        print(json.dumps({"status": "blocked_or_failed", "error_type": type(error).__name__,
                          "resource_check": getattr(error, "resource_check", None),
                          "failure_location": [{"file": Path(frame.filename).name,
                              "function": frame.name, "line": frame.lineno}
                              for frame in traceback.extract_tb(error.__traceback__)],
                          "detail": "Inspect local prerequisites/configuration and retained run reports; no automatic retry/download."}))
        return 2


def evaluate_main(default_config: Path) -> int:
    parser = argparse.ArgumentParser(description="Evaluate an owned trained artifact on a fixed held-out split.")
    parser.add_argument("--config", default=str(default_config))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--split", choices=("tuning", "calibration", "test"), default="tuning")
    parser.add_argument("--final-test", action="store_true")
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    args = parser.parse_args()
    try:
        from .transformer_engine import evaluate
        print(json.dumps(evaluate(load_config(args.config), args.run_dir, args.split, args.final_test, args.device), indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(json.dumps({"status": "unavailable", "error_type": type(error).__name__}))
        return 2


def predict_main(default_config: Path) -> int:
    parser = argparse.ArgumentParser(description="Inference from real local trained weights; no fallback predictions.")
    parser.add_argument("--config", default=str(default_config))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    args = parser.parse_args()
    try:
        from .transformer_engine import predict
        print(json.dumps(predict(load_config(args.config), args.run_dir, [args.text], args.language, args.device), indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(json.dumps({"status": "model_unavailable", "error_type": type(error).__name__, "predictions": None}))
        return 2
