"""Compile/package Scala using ONLY an already installed Spark distribution.

No SBT bootstrap, Maven/Ivy resolution, installation or network request occurs.
This complements the SBT build; ScalaTest still needs its manually prepared jars.
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
import time
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verification_common import load_config, resource_snapshot
from spark_job_launcher import local_path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(data)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--spark-home")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.workspace).resolve()
    config, _ = load_config(root, None)
    supplied = args.spark_home or os.environ.get("SPARK_HOME") or config["spark"].get("home")
    if not supplied:
        print(json.dumps({"status": "blocked", "reason": "Supply an installed Spark home; no download fallback."}))
        return 2
    spark_home = Path(supplied).resolve()
    scala, spark, hadoop = (config["spark"][key] for key in ("scala_version", "version", "hadoop_version"))
    jar_names = [f"scala-{name}-{scala}.jar" for name in ("compiler", "library", "reflect")]
    jar_names += [f"spark-{name}_2.13-{spark}.jar" for name in ("core", "sql", "sql-api", "mllib")]
    jar_names += [f"hadoop-client-api-{hadoop}.jar", f"hadoop-client-runtime-{hadoop}.jar"]
    required = [spark_home / "jars" / name for name in jar_names]
    java = Path(config["java"]["home"]) / "bin" / ("java.exe" if os.name == "nt" else "java")
    missing = [str(path) for path in [java, spark_home / "RELEASE", *required] if not path.is_file()]
    resources = resource_snapshot(root)
    if missing or resources["disk"]["free_bytes"] < 20 * 1024**3 or (
            resources["memory"]["status"] == "measured" and resources["memory"]["available_bytes"] < 640 * 1024**2):
        print(json.dumps({"status": "blocked", "missing_files": missing, "resources": resources,
                          "minimum_memory_mib": 640, "network_used": False}, indent=2))
        return 2
    release = (spark_home / "RELEASE").read_text(encoding="utf-8")
    if not re.search(r"\bSpark " + re.escape(spark) + r"\b", release) or ("Hadoop " + hadoop) not in release:
        raise ValueError("Installed Spark release metadata does not match project versions.")
    output = local_path(root, args.output or ("artifacts/scala-build/" +
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]), output=True)
    output.mkdir(parents=True, exist_ok=False)
    classes = output / "classes"
    classes.mkdir()
    sources = sorted((root / "scala/src/main/scala").rglob("*.scala"))
    source_hashes = {str(path.relative_to(root)): digest(path) for path in sources}
    installed_jars = sorted((spark_home / "jars").glob("*.jar"))
    if len(installed_jars) > 2000:
        raise ValueError("Unexpected distribution jar count.")
    # The compiler's -classpath does not expand Java launcher wildcards reliably.
    # A JVM argument file also avoids Windows' command-line length limit.
    classpath = os.pathsep.join(str(path) for path in installed_jars)
    compiler_arguments = ["-Xmx384m", "-cp", classpath, "scala.tools.nsc.Main",
               "-deprecation", "-feature", "-unchecked", "-release", "17",
               "-classpath", classpath, "-d", str(classes), *map(str, sources)]
    argument_file = output / "compiler.arguments"
    argument_file.write_text("\n".join(json.dumps(part, ensure_ascii=False) for part in compiler_arguments) + "\n",
                             encoding="utf-8")
    command = [str(java), "@" + str(argument_file)]
    child = os.environ.copy()
    for key in ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH"):
        child.pop(key, None)
    started = time.monotonic()
    result = subprocess.run(command, cwd=root, env=child, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=180,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    stable = all(digest(path) == source_hashes[str(path.relative_to(root))] for path in sources)
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
              "spark_version": spark, "scala_version": scala, "spark_home": str(spark_home),
              "network_used": False, "resolver_invoked": False, "source_count": len(sources),
              "distribution_jar_count": len(installed_jars),
              "source_hashes": source_hashes, "inputs_stable": stable, "resources_before": resources,
              "compiler_exit_code": result.returncode, "compiler_output": result.stdout + result.stderr,
              "duration_seconds": round(time.monotonic() - started, 3),
              "status": "compiled" if result.returncode == 0 and stable else "failed",
              "scalatest_executed": False, "spark_job_executed": False}
    if report["status"] == "compiled":
        target = output / "movieintel-spark_2.13-0.1.0.jar"
        manifest = ("Manifest-Version: 1.0\r\nMain-Class: com.movieintel.Main\r\n" +
                    "Spark-Version: " + spark + "\r\nScala-Version: " + scala +
                    "\r\nBuild-Method: offline-scalac\r\n\r\n")
        with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("META-INF/MANIFEST.MF", manifest)
            for path in sorted(classes.rglob("*.class")):
                archive.write(path, path.relative_to(classes).as_posix())
        report.update(jar_path=str(target), jar_sha256=digest(target))
    with (output / "build_report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "compiled" else 1


if __name__ == "__main__":
    raise SystemExit(main())
