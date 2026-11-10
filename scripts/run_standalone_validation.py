"""Execute standalone Big Data pipeline integration tests using local spark-submit.

Complies strictly with offline, local[2], driver-memory <= 1G constraints.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verification_common import load_config, resource_snapshot

INHERITED_OPTIONS = (
    "SPARK_SUBMIT_OPTS", "JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS",
    "JDK_JAVA_OPTIONS", "SPARK_DIST_CLASSPATH", "SPARK_DRIVER_EXTRA_CLASSPATH",
    "SPARK_PREPEND_CLASSES", "CLASSPATH", "HADOOP_CONF_DIR", "YARN_CONF_DIR"
)


def find_latest_project_jar(root: Path) -> Path:
    candidates = sorted((root / "artifacts/scala-build").glob("*/movieintel-spark_2.13-0.1.0.jar"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("No built movieintel-spark_2.13-0.1.0.jar found under artifacts/scala-build/")
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--driver-memory", default="1g")
    parser.add_argument("--target", choices=["bronze", "silver", "analytics"], default="analytics")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    config, _ = load_config(root, None)

    spark_home = Path(config["spark"]["home"]).resolve()
    java_home = Path(config["java"]["home"]).resolve()

    submit_cmd = spark_home / "bin" / ("spark-submit.cmd" if os.name == "nt" else "spark-submit")
    project_jar = find_latest_project_jar(root)

    target_configs = {
        "bronze": {
            "runner_jar": root / "artifacts/scala-build/bronze-validation-runner.jar",
            "main_class": "com.movieintel.harness.BronzeIngestionRunner",
            "log_dir": root / "artifacts/standalone-validation",
            "title": "STANDALONE BRONZE INGESTION INTEGRATION VALIDATION"
        },
        "silver": {
            "runner_jar": root / "artifacts/scala-build/silver-validation-runner.jar",
            "main_class": "com.movieintel.harness.SilverCleaningRunner",
            "log_dir": root / "artifacts/silver-standalone-validation",
            "title": "STANDALONE SILVER CLEANING & STANDARDIZATION VALIDATION"
        },
        "analytics": {
            "runner_jar": root / "artifacts/scala-build/analytics-validation-runner.jar",
            "main_class": "com.movieintel.harness.TransformationsAnalyticsRunner",
            "log_dir": root / "artifacts/analytics-standalone-validation",
            "title": "STANDALONE TRANSFORMATIONS & ANALYTICS INTEGRATION VALIDATION"
        }
    }

    info = target_configs[args.target]
    runner_jar = info["runner_jar"]
    main_class = info["main_class"]
    log_dir = info["log_dir"]
    title = info["title"]

    if not submit_cmd.is_file():
        print(f"Error: spark-submit not found at {submit_cmd}")
        return 1
    if not runner_jar.is_file():
        print(f"Error: Runner JAR not found at {runner_jar}")
        return 1

    command = [
        str(submit_cmd),
        "--master", "local[2]",
        "--driver-memory", args.driver_memory,
        "--conf", "spark.driver.host=127.0.0.1",
        "--conf", "spark.driver.bindAddress=127.0.0.1",
        "--conf", "spark.jars.packages=",
        "--conf", "spark.ui.enabled=false",
        "--jars", str(project_jar),
        "--class", main_class,
        str(runner_jar),
        "--workspace", str(root)
    ]

    env = os.environ.copy()
    env["JAVA_HOME"] = str(java_home)
    env["SPARK_HOME"] = str(spark_home)
    env["SPARK_LOCAL_IP"] = "127.0.0.1"
    env["SPARK_CONF_DIR"] = str(root / "configs" / "spark-local")

    for key in INHERITED_OPTIONS:
        env.pop(key, None)

    env["PATH"] = str(java_home / "bin") + os.pathsep + str(spark_home / "bin") + os.pathsep + env.get("PATH", "")

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "spark_execution.log"

    print("=" * 80)
    print(f"STARTING {title} VIA SPARK-SUBMIT")
    print("=" * 80)
    print(f"Command: {' '.join(command)}")
    print(f"Driver Memory: {args.driver_memory}")
    print(f"Master: local[2]")
    print(f"Project JAR: {project_jar}")
    print(f"Runner JAR: {runner_jar}")
    print(f"Main Class: {main_class}")
    print(f"SPARK_HOME: {spark_home}")
    print(f"JAVA_HOME: {java_home}")
    print(f"Log file: {log_file}")
    print("-" * 80)

    started = time.monotonic()
    with log_file.open("w", encoding="utf-8") as log_stream:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        for line in iter(process.stdout.readline, ""):
            sys.stdout.write(line)
            sys.stdout.flush()
            log_stream.write(line)
        process.wait()

    duration = time.monotonic() - started
    print("-" * 80)
    print(f"Execution completed in {duration:.2f} seconds with exit code: {process.returncode}")
    print(f"Full execution log saved to: {log_file}")
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
