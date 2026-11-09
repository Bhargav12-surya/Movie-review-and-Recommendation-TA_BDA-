"""Static-only Phase 3 handoff checks, without importing project/model code.

Uses only the standard library. Parses source/config/notebook files, records
fingerprints and checks file contracts. Does not read dataset contents, execute
notebook cells, run tests, fit/evaluate models, start services or fetch anything.
"""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

COMPONENTS = ("sentiment_tfidf", "sentiment_transformer", "multilingual_sentiment", "sarcasm")
NOTEBOOKS = (
    "03_review_preprocessing", "04_tfidf_baseline", "05_transformer_sentiment", "06_sentiment_evaluation",
    "informal_language_analysis", "hinglish_sentiment_analysis", "sarcasm_detection",
    "emoji_sentiment_analysis", "multilingual_model_comparison",
)
EXTRA_PYTHON = (
    "scripts/prepare_sentiment_splits.py", "scripts/verify_phase3_sources.py", "scripts/build_scala_offline.py",
    "scripts/_toolchain_discovery.py", "scripts/spark_job_launcher.py", "scripts/verify_environment.py",
    "tests/foundation/test_toolchain_discovery.py", "tests/foundation/test_spark_launcher.py",
)


def validate(root: Path) -> dict:
    errors, files = [], set()
    counts = {"python_files": 0, "authored_ml_test_methods": 0, "json_yaml_schema_files": 0,
              "notebooks": 0, "notebook_cells": 0, "notebook_code_cells": 0}
    required = [root / "ml" / name / filename for name in COMPONENTS for filename in
                ("train.py", "evaluate.py", "predict.py", "config.yaml", "README.md", "model_card.md")]
    required += [root / "ml/informal_language" / filename for filename in
                 ("preprocess.py", "emoji_processing.py", "slang_normalization.py", "transliteration.py",
                  "language_detection.py", "evaluate.py", "config.yaml", "README.md")]
    required += [root / "documentation/phase3" / filename for filename in ("RUNBOOK.md", "GENERATED_FILES.md")]
    required += [root / "documentation/dataset/LANGUAGE_ANNOTATION_ADDENDUM.md"]
    for path in required:
        if not path.is_file():
            errors.append({"file": path.relative_to(root).as_posix(), "error": "required_file_missing"})
        else:
            files.add(path)
    python_files = sorted(set((root / "ml").rglob("*.py")) |
                          set((root / "tests/ml").glob("*.py")) | {root / name for name in EXTRA_PYTHON})
    for path in python_files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=path.relative_to(root).as_posix())
            counts["python_files"] += 1
            if path.is_relative_to(root / "tests/ml"):
                counts["authored_ml_test_methods"] += sum(isinstance(node, ast.FunctionDef) and
                    node.name.startswith("test_") for node in ast.walk(tree))
            files.add(path)
        except (OSError, UnicodeError, SyntaxError) as error:
            errors.append({"file": path.relative_to(root).as_posix(), "error": type(error).__name__})
    metadata = sorted((root / "ml").glob("*/config.yaml"))
    metadata += sorted((root / "configs/training").glob("*.json"))
    metadata += sorted((root / "configs/training").glob("*.yaml"))
    metadata += [root / "schemas/datasets/phase3_review_manifest.schema.json", root / "configs/environment.json"]
    def reject_constant(value):
        raise ValueError("Nonfinite JSON constant")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    for path in metadata:
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique,
                               parse_constant=reject_constant)
            if not isinstance(value, dict):
                raise ValueError("Metadata must be an object")
            counts["json_yaml_schema_files"] += 1
            files.add(path)
        except (OSError, ValueError, UnicodeError) as error:
            errors.append({"file": path.relative_to(root).as_posix(), "error": type(error).__name__})
    for name in NOTEBOOKS:
        path = root / "notebooks" / (name + ".ipynb")
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique,
                                  parse_constant=reject_constant)
            if notebook["nbformat"] != 4:
                raise ValueError("Expected nbformat4")
            ids, disabled = set(), False
            for index, cell in enumerate(notebook["cells"]):
                counts["notebook_cells"] += 1
                if not cell.get("id") or cell["id"] in ids:
                    raise ValueError("Every cell needs a unique ID")
                ids.add(cell["id"])
                if cell["cell_type"] == "code":
                    if cell.get("execution_count") is not None or cell.get("outputs") != []:
                        raise ValueError("Notebook contains executed state")
                    tree = ast.parse("".join(cell["source"]), filename=name + ":cell" + str(index))
                    counts["notebook_code_cells"] += 1
                    disabled |= any(isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and
                        node.value.value is False and any(isinstance(target, ast.Name) and
                        target.id == "RUN_APPROVED_EXPERIMENTS" for target in node.targets)
                        for node in tree.body)
            if not disabled:
                raise ValueError("Explicit disabled-by-default experiment flag is missing")
            counts["notebooks"] += 1
            files.add(path)
        except (OSError, ValueError, KeyError, TypeError, UnicodeError, SyntaxError) as error:
            errors.append({"file": path.relative_to(root).as_posix(), "error": type(error).__name__})
    return {"schema_version": 1, "status": "passed" if not errors else "failed",
        "scope": "static_syntax_and_file_contracts_only", "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts, "errors": errors,
        "project_modules_imported": False, "dataset_contents_read": False, "unit_tests_executed": False,
        "training_or_evaluation_executed": False, "spark_or_services_started": False,
        "downloads_or_installations": False, "json_schema_semantically_validated": False,
        "files_sha256": {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted(files)},
        "limitations": ["AST/JSON parsing does not establish runtime correctness, package ABI or GPU support.",
                        "Notebook cells and authored tests were not executed.",
                        "Model quality and phase acceptance remain unmeasured."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report")
    args = parser.parse_args()
    root = Path(args.workspace).resolve()
    report = validate(root)
    path = Path(args.report) if args.report else Path("artifacts/source_validation/phase3-" + uuid.uuid4().hex + ".json")
    path = (path if path.is_absolute() else root / path).resolve()
    if not path.is_relative_to(root / "artifacts"):
        raise ValueError("Static reports must remain in the ignored artifacts directory.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: value for key, value in report.items() if key != "files_sha256"}, indent=2))
    print("Report: " + str(path))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
