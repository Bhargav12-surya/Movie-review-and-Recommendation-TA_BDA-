"""Bounded, read-only inspection of existing local build cache filenames.

Never invokes SBT, coursier, Scala CLI, network access or package resolution.
Finding jars is not proof that a complete build classpath is available.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verification_common import emit_report, load_config, new_report, validate_output_path


def inspect(cache: Path, scala: str, spark: str, sbt: str, limit: int = 50000) -> dict:
    wanted = {f"{name}-{scala}.jar" for name in ("scala-compiler", "scala-library", "scala-reflect")}
    wanted |= {f"spark-{name}_2.13-{spark}.jar" for name in ("core", "sql", "mllib")}
    wanted |= {f"sbt-launch-{sbt}.jar", "scalatest_2.13-3.2.19.jar", "scalatest-funsuite_2.13-3.2.19.jar"}
    found = {name: [] for name in sorted(wanted)}
    examined = 0
    capped = False
    if cache.is_dir():
        for parent, directories, files in os.walk(cache, followlinks=False):
            directories[:] = [name for name in directories if not (Path(parent) / name).is_symlink()]
            for name in files:
                examined += 1
                if name in wanted and len(found[name]) < 10:
                    found[name].append(str(Path(parent) / name))
                if examined >= limit:
                    capped = True
                    break
            if capped:
                break
    return {"cache_root_exists": cache.is_dir(), "files_examined": examined,
            "scan_capped": capped, "matching_files": found,
            "missing_requested_filenames": [name for name, paths in found.items() if not paths],
            "complete_classpath_verified": False, "network_used": False, "resolver_invoked": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--cache-root")
    parser.add_argument("--report-path")
    args = parser.parse_args()
    root = Path(args.workspace).resolve()
    config, _ = load_config(root, None)
    target = validate_output_path(root, args.report_path)
    cache = Path(args.cache_root).resolve() if args.cache_root else (
        Path(os.environ.get("LOCALAPPDATA", "")) / "Coursier/cache")
    report = new_report("verify_spark_cache", root)
    report.update(inspect(cache, config["spark"]["scala_version"], config["spark"]["version"], config["sbt"]["version"]))
    report["notes"].append("Read-only filename inspection; missing entries do not authorize a download.")
    emit_report(report, target, True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
