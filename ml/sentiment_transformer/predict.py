"""Predictions come only from the actual trained local model artifact."""
from pathlib import Path
from ml.common.transformer_cli import predict_main

if __name__ == "__main__":
    raise SystemExit(predict_main(Path(__file__).with_name("config.yaml")))
