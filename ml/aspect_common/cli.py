"""Explicit manual command entry points; source import never starts fitting."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path


def configuration(component, path):
    if component == "themes":
        from ml.themes.data import load_config
    else:
        from .config import load_config
    value = load_config(path)
    if value["task"] != component:
        raise ValueError("The CLI component and task differ.")
    return value


def train_main(component, default_config):
    parser = argparse.ArgumentParser(description="Preflight by default; no automatic downloads or fitting.")
    parser.add_argument("--config", default=str(default_config))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume-checkpoint")
    args = parser.parse_args()
    try:
        from .engine import preflight, train
        config = configuration(component, args.config)
        report = train(config, component, args.resume_checkpoint) if args.execute else preflight(config, component)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if args.execute or report["ready"] else 2
    except Exception as error:
        print(json.dumps({"status": "blocked_or_failed", "error_type": type(error).__name__, "training_started_by_default": False}))
        return 2


def evaluate_main(component, default_config):
    parser = argparse.ArgumentParser(description="Evaluate an actual owned frozen supervised artifact.")
    parser.add_argument("--config", default=str(default_config))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--split", choices=("tuning", "calibration", "test"), default="tuning")
    parser.add_argument("--final-test", action="store_true")
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    args = parser.parse_args()
    try:
        from .engine import evaluate
        print(json.dumps(evaluate(configuration(component, args.config), component, args.run_dir,
                                  args.split, args.final_test, args.device), indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"status": "evaluation_unavailable", "error_type": type(error).__name__, "metrics": None}))
        return 2


def inference_example(text, language):
    from .data import ReviewExample
    if not isinstance(text, str) or not text.strip() or len(text) > 20000:
        raise ValueError("Supply bounded nonempty original Unicode text.")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ReviewExample("inference:" + digest, "inference", 1, "", text, digest, "inference", language)


def predict_main(component, default_config):
    parser = argparse.ArgumentParser(description="Actual local inference; missing artifacts produce unavailability.")
    parser.add_argument("--config", default=str(default_config))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    parser.add_argument("--aspect-category")
    parser.add_argument("--aspect-start", type=int)
    parser.add_argument("--aspect-end", type=int)
    args = parser.parse_args()
    try:
        from .engine import load_trained, adapter
        config = configuration(component, args.config)
        if args.language not in config["language_scope"]:
            print(json.dumps({"status": "unsupported_language", "aspects": None}))
            return 2
        example = inference_example(args.text, args.language)
        if component == "aspect_sentiment":
            from .data import AspectSpan
            if args.aspect_category not in config["taxonomy"]["aspects"] or args.aspect_start is None or args.aspect_end is None or not 0 <= args.aspect_start < args.aspect_end <= len(args.text):
                raise ValueError("An exact original target category/span is required.")
            span = AspectSpan(args.aspect_category, args.aspect_start, args.aspect_end, args.text[args.aspect_start:args.aspect_end])
            example = replace(example, aspects=(span,))
        _, manifest, model, tokenizer, device = load_trained(config, args.run_dir, args.device)
        result = adapter(component).predict_examples(model, tokenizer, [example], config, device, temperature=manifest["temperature"])
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0
    except Exception as error:
        print(json.dumps({"status": "model_unavailable", "error_type": type(error).__name__, "aspects": None}))
        return 2
