"""Manual evaluation of an actual trained, frozen aspect-sentiment artifact."""
from pathlib import Path
from ml.aspect_common.cli import evaluate_main

if __name__ == "__main__":
    raise SystemExit(evaluate_main("aspect_sentiment", Path(__file__).with_name("config.yaml")))

