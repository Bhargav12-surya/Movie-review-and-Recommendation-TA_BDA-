"""Generate preflight by default; fitting needs explicit approved --execute."""
from pathlib import Path
from ml.common.transformer_cli import train_main

if __name__ == "__main__":
    raise SystemExit(train_main("sarcasm", Path(__file__).with_name("config.yaml")))
