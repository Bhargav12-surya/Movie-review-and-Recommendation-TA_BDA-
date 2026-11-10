"""Compile and package standalone validation runners using local Spark distribution and project JAR.

Strictly offline: no SBT, Ivy, Coursier, Maven, or network resolution.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verification_common import load_config, resource_snapshot


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_latest_project_jar(root: Path) -> Path:
    candidates = sorted((root / "artifacts/scala-build").glob("*/movieintel-spark_2.13-0.1.0.jar"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("No built movieintel-spark_2.13-0.1.0.jar found under artifacts/scala-build/")
    return candidates[0]


def compile_and_package(root: Path, runner_name: str, config: dict, spark_home: Path, java: Path, project_jar: Path) -> int:
    runners = {
        "bronze": {
            "source": root / "scripts/test-harness/BronzeIngestionRunner.scala",
            "main_class": "com.movieintel.harness.BronzeIngestionRunner",
            "target_jar": root / "artifacts/scala-build/bronze-validation-runner.jar",
            "classes_dir": root / "artifacts/scala-build/bronze-runner-classes",
            "report_name": "bronze_runner_build_report.json"
        },
        "silver": {
            "source": root / "scripts/test-harness/SilverCleaningRunner.scala",
            "main_class": "com.movieintel.harness.SilverCleaningRunner",
            "target_jar": root / "artifacts/scala-build/silver-validation-runner.jar",
            "classes_dir": root / "artifacts/scala-build/silver-runner-classes",
            "report_name": "silver_runner_build_report.json"
        },
        "analytics": {
            "source": root / "scripts/test-harness/TransformationsAnalyticsRunner.scala",
            "main_class": "com.movieintel.harness.TransformationsAnalyticsRunner",
            "target_jar": root / "artifacts/scala-build/analytics-validation-runner.jar",
            "classes_dir": root / "artifacts/scala-build/analytics-runner-classes",
            "report_name": "analytics_runner_build_report.json"
        }
    }

    info = runners[runner_name]
    runner_source = info["source"]
    target_jar = info["target_jar"]
    classes_dir = info["classes_dir"]
    main_class = info["main_class"]
    report_name = info["report_name"]

    if not runner_source.is_file():
        print(f"Error: Runner source file missing: {runner_source}")
        return 1

    installed_jars = sorted((spark_home / "jars").glob("*.jar"))
    if not installed_jars:
        print(f"Error: No Spark distribution JARs found in {spark_home / 'jars'}")
        return 1

    classes_dir.mkdir(parents=True, exist_ok=True)
    for existing in classes_dir.glob("*"):
        if existing.is_file():
            existing.unlink()

    all_classpath_jars = installed_jars + [project_jar]
    classpath = os.pathsep.join(str(j) for j in all_classpath_jars)

    compiler_arguments = [
        "-Xmx512m",
        "-cp", classpath,
        "scala.tools.nsc.Main",
        "-deprecation",
        "-feature",
        "-unchecked",
        "-release", "17",
        "-classpath", classpath,
        "-d", str(classes_dir),
        str(runner_source),
    ]

    output_dir = root / "artifacts/scala-build"
    output_dir.mkdir(parents=True, exist_ok=True)
    arg_file = output_dir / f"{runner_name}-runner-compiler.arguments"
    arg_file.write_text(
        "\n".join(json.dumps(part, ensure_ascii=False) for part in compiler_arguments) + "\n",
        encoding="utf-8"
    )

    cmd = [str(java), "@" + str(arg_file)]
    env = os.environ.copy()
    for k in ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH"):
        env.pop(k, None)

    started = time.monotonic()
    print(f"\nCompiling {runner_source.name} using latest project JAR {project_jar.parent.name}...")
    res = subprocess.run(
        cmd,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )
    duration = time.monotonic() - started

    print(f"Compiler return code: {res.returncode} (duration: {duration:.2f}s)")
    if res.stdout.strip():
        print("STDOUT:\n" + res.stdout)
    if res.stderr.strip():
        print("STDERR:\n" + res.stderr)

    if res.returncode != 0:
        print(f"Compilation failed for {runner_name} runner!")
        return 1

    if target_jar.exists():
        target_jar.unlink()

    manifest = (
        "Manifest-Version: 1.0\r\n"
        f"Main-Class: {main_class}\r\n"
        f"Spark-Version: {config['spark']['version']}\r\n"
        f"Scala-Version: {config['spark']['scala_version']}\r\n"
        "Build-Method: offline-scalac-harness\r\n\r\n"
    )

    with zipfile.ZipFile(target_jar, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/MANIFEST.MF", manifest)
        for path in sorted(classes_dir.rglob("*.class")):
            archive.write(path, path.relative_to(classes_dir).as_posix())
        with zipfile.ZipFile(project_jar, "r") as proj:
            for item in proj.infolist():
                if item.filename.endswith(".class") and not item.filename.startswith("META-INF/"):
                    archive.writestr(item.filename, proj.read(item.filename))

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner": runner_name,
        "runner_source": str(runner_source),
        "runner_source_sha256": digest(runner_source),
        "runner_jar": str(target_jar),
        "runner_jar_sha256": digest(target_jar),
        "runner_jar_size_bytes": target_jar.stat().st_size,
        "project_jar_used": str(project_jar),
        "compiler_returncode": res.returncode,
        "compiler_duration_seconds": round(duration, 3),
        "status": "compiled"
    }

    report_path = output_dir / report_name
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print(f"Compilation and packaging successful for {runner_name} runner!")
    print(f"Runner JAR: {target_jar}")
    print(f"Runner JAR SHA-256: {report['runner_jar_sha256']}")
    print(f"Runner JAR Size: {report['runner_jar_size_bytes']:,} bytes")
    print(f"Report: {report_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--runner", choices=["bronze", "silver", "analytics", "all"], default="analytics")
    args = parser.parse_args()
    root = Path(args.workspace).resolve()

    config, _ = load_config(root, None)
    spark_home = Path(config["spark"]["home"]).resolve()
    java = Path(config["java"]["home"]) / "bin" / ("java.exe" if os.name == "nt" else "java")

    project_jar = find_latest_project_jar(root)
    print(f"Using latest project JAR: {project_jar}")

    runners_to_build = ["bronze", "silver"] if args.runner == "all" else [args.runner]
    for r in runners_to_build:
        rc = compile_and_package(root, r, config, spark_home, java, project_jar)
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
