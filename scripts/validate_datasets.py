"""Inventory only local raw datasets; use --kind for the supported validators."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataset_tools.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
