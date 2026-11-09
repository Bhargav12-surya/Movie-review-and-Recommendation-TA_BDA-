"""Static-only verification for the Phase4-8 source delivery; no project imports."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid


def verify(root):
    errors, files = [], set()
    counts = {"python_files": 0, "authored_test_methods": 0, "json_yaml_schema_files": 0,
              "notebooks": 0, "notebook_code_cells": 0, "scala_source_files_recorded_not_compiled": 0}
    required = []
    for component in ("aspect_extraction", "aspect_sentiment", "themes", "topics", "embeddings", "summarization", "review_risk"):
        required += [root / "ml" / component / name for name in ("train.py", "evaluate.py", "predict.py", "config.yaml", "README.md", "model_card.md")]
    required += [root / "documentation/phases4-8/RUNBOOK.md", root / "documentation/phases4-8/GENERATED_FILES.md"]
    for path in required:
        if path.is_file():
            files.add(path)
        else:
            errors.append({"file": path.relative_to(root).as_posix(), "error": "required_file_missing"})
    python_files = set()
    for folder in ("ml", "scoring", "recommender", "tests/aspects", "tests/phases4_8"):
        python_files.update((root / folder).rglob("*.py"))
    python_files.update(root / "scripts" / name for name in ("run_offline_phase.py", "prepare_aspect_baseline.py", "recommendation_readiness.py", "verify_generated_phases.py", "parse_scala_sources.py"))
    for path in sorted(python_files):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=path.relative_to(root).as_posix())
            counts["python_files"] += 1
            if path.is_relative_to(root / "tests"):
                counts["authored_test_methods"] += sum(isinstance(node, ast.FunctionDef) and node.name.startswith("test_") for node in ast.walk(tree))
            files.add(path)
        except (OSError, UnicodeError, SyntaxError) as error:
            errors.append({"file": path.relative_to(root).as_posix(), "error": type(error).__name__})
    metadata = set((root / "ml").glob("*/config.yaml"))
    for folder in ("schemas/predictions", "schemas/datasets", "configs/training", "configs/recommendation", "scoring"):
        metadata.update((root / folder).glob("*.json"))
    for path in sorted(metadata):
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
            counts["json_yaml_schema_files"] += 1
            files.add(path)
        except (OSError, ValueError, UnicodeError) as error:
            errors.append({"file": path.relative_to(root).as_posix(), "error": type(error).__name__})
    for path in sorted((root / "notebooks").glob("*.ipynb")):
        if path.name.startswith(("01_", "02_")):
            continue
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            disabled = False
            for index, cell in enumerate(notebook["cells"]):
                if cell["cell_type"] != "code":
                    continue
                if cell.get("execution_count") is not None or cell.get("outputs") != []:
                    raise ValueError("Notebook contains executed outputs")
                tree = ast.parse("".join(cell["source"]), filename=path.name + ":cell" + str(index))
                disabled |= any(isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and node.value.value is False and
                    any(isinstance(target, ast.Name) and target.id == "RUN_APPROVED_EXPERIMENTS" for target in node.targets) for node in tree.body)
                counts["notebook_code_cells"] += 1
            if not disabled:
                raise ValueError("Explicit disabled experiment flag missing")
            counts["notebooks"] += 1
            files.add(path)
        except (OSError, UnicodeError, ValueError, SyntaxError, KeyError) as error:
            errors.append({"file": path.relative_to(root).as_posix(), "error": type(error).__name__})
    for name in ("analytics/ReviewAnalytics.scala", "recommendation/TemporalSplit.scala", "recommendation/RankingEvaluation.scala", "recommendation/RecommendationJob.scala"):
        path = root / "scala/src/main/scala/com/movieintel" / name
        try:
            path.read_text(encoding="utf-8")
            files.add(path)
            counts["scala_source_files_recorded_not_compiled"] += 1
        except (OSError, UnicodeError) as error:
            errors.append({"file": path.relative_to(root).as_posix(), "error": type(error).__name__})
    for name in ("train_aspects.ps1", "run_recommendation.ps1"):
        files.add(root / "scripts" / name)
    files.add(root / "scala/src/test/scala/com/movieintel/AudienceAndTemporalSpec.scala")
    return {"schema_version": 1, "status": "passed" if not errors else "failed", "scope": "static_source_file_contracts_only",
        "generated_at": datetime.now(timezone.utc).isoformat(), "counts": counts, "errors": errors,
        "tests_executed": False, "model_inference_or_training_executed": False, "project_modules_imported": False,
        "scala_compiled_or_spark_started": False, "datasets_read": False, "dependencies_installed_or_downloaded": False,
        "json_schema_semantically_validated": False,
        "files_sha256": {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report")
    args = parser.parse_args()
    root = Path(args.workspace).resolve()
    report = verify(root)
    target = Path(args.report or ("artifacts/source_validation/phases4-8-" + uuid.uuid4().hex + ".json"))
    target = (target if target.is_absolute() else root / target).resolve()
    if not target.is_relative_to(root / "artifacts"):
        raise ValueError("Static reports must stay under ignored artifacts.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: value for key, value in report.items() if key != "files_sha256"}, indent=2))
    print("Report: " + str(target))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
