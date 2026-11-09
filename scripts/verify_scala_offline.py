"""Use only existing cached Scala jars; never invoke a resolver or install tools.

Compiles/runs dependency-free config checks and parses Spark Scala sources.
Parsing is NOT Spark API type checking, ScalaTest execution or a Spark job.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verification_common import load_config
from spark_job_launcher import local_path


def fingerprint(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output")
    parser.add_argument("--cache-root")
    args = parser.parse_args()
    root = Path(args.workspace).resolve()
    config, _ = load_config(root, None)
    version = config["spark"]["scala_version"]
    cache = Path(args.cache_root).resolve() if args.cache_root else (
        Path(os.environ.get("LOCALAPPDATA", "")) / "Coursier/cache/v1/https/repo1.maven.org/maven2/org/scala-lang")
    jars = [cache / name / version / f"{name}-{version}.jar"
            for name in ("scala-compiler", "scala-library", "scala-reflect")]
    java = Path(config["java"]["home"]) / "bin" / ("java.exe" if os.name == "nt" else "java")
    target_name = args.output or ("artifacts/scala-offline/" +
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    output = local_path(root, target_name, output=True)
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
              "network_used": False, "spark_api_compilation": "not_run_missing_spark_dependencies",
              "spark_runtime_tests": "not_run", "checks": [], "ready": False}
    if not java.is_file() or not all(path.is_file() for path in jars):
        report["missing"] = [str(path) for path in [java, *jars] if not path.is_file()]
        print(json.dumps(report, indent=2))
        return 2
    output.mkdir(parents=True, exist_ok=False)
    classes, parsed = output / "pure-classes", output / "parser-output"
    classes.mkdir()
    parsed.mkdir()
    fixture = output / "synthetic-workspace"
    fixture.mkdir()
    source_root = root / "scala/src"
    sources = sorted(source_root.rglob("*.scala"))
    pure = [source_root / "main/scala/com/movieintel" / part for part in
            ("config/PathPolicy.scala", "config/JobConfig.scala", "io/JsonCodec.scala")]
    pure.append(source_root / "test/scala/com/movieintel/PureConfigChecks.scala")
    report.update(scala_version=version, tools=[fingerprint(path) for path in [java, *jars]],
                  sources=[fingerprint(path) for path in sources])
    child = os.environ.copy()
    # Do not honor injected JVM agents/options during the offline checks.
    for key in ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH"):
        child.pop(key, None)
    base = [str(java), "-Xmx512m", "-cp", os.pathsep.join(map(str, jars)), "scala.tools.nsc.Main"]
    commands = [
        ("scala.compiler_version", base + ["-version"]),
        ("scala.pure_compile", base + ["-release", "17", "-classpath", str(jars[1]), "-d", str(classes), *map(str, pure)]),
        ("scala.pure_execute", [str(java), "-Xmx256m", "-cp", str(classes) + os.pathsep + str(jars[1]),
                                "com.movieintel.PureConfigChecks", str(fixture)]),
        ("scala.all_sources_parse_only", base + ["-Ystop-after:parser", "-classpath", str(jars[1]),
                                                "-d", str(parsed), *map(str, sources)]),
    ]
    for name, command in commands:
        try:
            result = subprocess.run(command, cwd=root, env=child, capture_output=True,
                                    text=True, encoding="utf-8", errors="replace", timeout=120,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            text = result.stdout + result.stderr
            passed = result.returncode == 0
            if name == "scala.compiler_version":
                passed = passed and ("version " + version) in text
            if name == "scala.pure_execute":
                match = re.search(r"PURE_SCALA_CHECKS_PASSED=(\d+)", text)
                passed = passed and bool(match)
                report["pure_checks_passed"] = int(match.group(1)) if match else 0
            report["checks"].append({"name": name, "status": "pass" if passed else "fail",
                                      "exit_code": result.returncode, "output": text})
        except (OSError, subprocess.TimeoutExpired) as error:
            report["checks"].append({"name": name, "status": "fail", "error_type": type(error).__name__})
            passed = False
        if not passed:
            break
    report["ready"] = len(report["checks"]) == len(commands) and all(
        check["status"] == "pass" for check in report["checks"])
    report["output_directory"] = str(output)
    with (output / "verification.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in ("ready", "checks", "spark_api_compilation", "output_directory")}, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
