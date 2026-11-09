"""Manual extraction training entry point; default is readiness inspection."""
from pathlib import Path
from ml.aspect_common.cli import train_main


if __name__ == "__main__":
    raise SystemExit(train_main("aspect_extraction", Path(__file__).with_name("config.yaml")))
