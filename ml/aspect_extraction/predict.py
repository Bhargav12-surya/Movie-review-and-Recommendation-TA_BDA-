"""Predict explicit aspect evidence using an actual owned trained artifact."""
from pathlib import Path
from ml.aspect_common.cli import predict_main


if __name__ == "__main__":
    raise SystemExit(predict_main("aspect_extraction", Path(__file__).with_name("config.yaml")))
