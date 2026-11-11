"""Offline standalone stream recovery checks; default is read-only readiness.

--execute compiles a small Scala harness using installed jars and runs isolated
synthetic assertions. --build-only compiles without starting Spark. No installer,
resolver, model training, previous-run edits, or cleanup/deletion is performed.
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
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verification_common import resource_snapshot
from spark_job_launcher import INHERITED_OPTIONS, _manifest, shell_safe
from verify_stream_lifecycle import sha, write

MAIN_CLASS = "com.movieintel.harness.StreamingRecoveryRunner"


def prerequisites(root):
    config = json.loads((root / "configs/environment.json").read_text(encoding="utf-8"))
    java_home = Path(config["java"]["home"]).resolve()
    spark_home = Path(config["spark"]["home"]).resolve()
    java = java_home / "bin" / ("java.exe" if os.name == "nt" else "java")
    submit = spark_home / "bin" / ("spark-submit.cmd" if os.name == "nt" else "spark-submit")
    scala_library = spark_home / "jars" / ("scala-library-" + config["spark"]["scala_version"] + ".jar")
    source = root / "scripts/test-harness/StreamingRecoveryRunner.scala"
    project = root / "artifacts/scala-build/manual-final-002/movieintel-spark_2.13-0.1.0.jar"
    for path in (java, submit, scala_library, source, project,
                 spark_home / "jars" / ("scala-compiler-" + config["spark"]["scala_version"] + ".jar")):
        if not path.is_file():
            raise ValueError("Missing local prerequisite: " + str(path))
    manifest = _manifest(project)
    if manifest.get("Spark-Version") != config["spark"]["version"] or manifest.get("Scala-Version") != config["spark"]["scala_version"]:
        raise ValueError("Existing project JAR differs from the configured Spark/Scala versions.")
    # Reject injected resolver/JVM options; never echo their values.
    if any(os.environ.get(name) for name in INHERITED_OPTIONS):
        raise ValueError("Unreviewed inherited Spark/JVM options are present; use the standard launcher checks.")
    spark_conf = root / "configs/spark-local"
    if spark_conf.is_dir():
        for path in spark_conf.glob("*.conf"):
            text = path.read_text(encoding="utf-8")
            for raw in text.splitlines():
                line = raw.strip()
                if line and not line.startswith("#") and line.split()[0] in {
                    "spark.jars.packages", "spark.jars.repositories", "spark.jars", "spark.jars.ivySettings"}:
                    raise ValueError("Resolver/additional-jar defaults require review before this offline check.")
    env = os.environ.copy()
    env.update(JAVA_HOME=str(java_home), SPARK_HOME=str(spark_home), SPARK_LOCAL_IP="127.0.0.1",
               SPARK_LOCAL_HOSTNAME="localhost", SPARK_CONF_DIR=str(spark_conf))
    env["PATH"] = str(java_home / "bin") + os.pathsep + str(spark_home / "bin") + os.pathsep + env.get("PATH", "")
    return dict(java=java, submit=submit, scala_library=scala_library, source=source,
                project=project, spark_home=spark_home, env=env)


def require_resources(root, spark=True):
    snapshot = resource_snapshot(root)
    if snapshot["disk"]["free_bytes"] < 20 * 1024**3:
        raise ValueError("Retain at least 20 GiB free disk space.")
    memory = snapshot["memory"]
    floor = (2048 if spark else 1024) * 1024**2
    if memory.get("available_bytes") is None or memory["available_bytes"] < floor:
        raise ValueError("Insufficient measured available RAM: need " + str(floor // 1024**2) + " MiB.")
    return snapshot


def compile_harness(root, tools, output):
    classes = output / "classes"
    classes.mkdir(exist_ok=False)
    classpath = os.pathsep.join([str(tools["project"])] +
                               [str(p) for p in sorted((tools["spark_home"] / "jars").glob("*.jar"))])
    arguments = ["-Xmx512m", "-cp", classpath, "scala.tools.nsc.Main",
                 "-deprecation", "-feature", "-unchecked", "-release", "17",
                 "-classpath", classpath, "-d", str(classes), str(tools["source"])]
    argument_file = output / "compiler.arguments"
    with argument_file.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(json.dumps(arg) for arg in arguments) + "\n")
    hashes = {str(tools[key]): sha(tools[key]) for key in ("source", "project")}
    started = time.monotonic()
    result = subprocess.run([str(tools["java"]), "@" + str(argument_file)],
        cwd=root, env=tools["env"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=180, check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    with (output / "compiler.log").open("x", encoding="utf-8") as stream:
        stream.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Scala compilation failed; inspect " + str(output / "compiler.log"))
    if any(sha(Path(name)) != value for name, value in hashes.items()):
        raise ValueError("Harness/project inputs changed during compilation.")
    jar = output / "stream-recovery-runner.jar"
    with zipfile.ZipFile(jar, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/MANIFEST.MF",
            "Manifest-Version: 1.0\r\nMain-Class: " + MAIN_CLASS + "\r\n\r\n")
        for path in sorted(classes.rglob("*.class")):
            archive.write(path, path.relative_to(classes).as_posix())
        with zipfile.ZipFile(tools["project"]) as project:
            for info in project.infolist():
                if info.filename.endswith(".class") and not info.filename.startswith("META-INF/"):
                    archive.writestr(info.filename, project.read(info.filename))
    report = dict(compiled=True, source_sha256=hashes[str(tools["source"])],
                  project_sha256=hashes[str(tools["project"])], runner_sha256=sha(jar),
                  elapsed_seconds=round(time.monotonic() - started, 3),
                  network_used=False, resolver_invoked=False, spark_executed=False)
    write(output / "build_report.json", report)
    return jar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--execute", action="store_true")
    actions.add_argument("--build-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = None
    try:
        tools = prerequisites(root)
        before = require_resources(root, spark=not args.build_only)
        print(json.dumps({"ready": True, "execution_requested": args.execute,
                          "build_requested": args.build_only or args.execute,
                          "synthetic_fixture": True}), flush=True)
        if not args.execute and not args.build_only:
            return 0
        output = root / "artifacts" / ("stream-recovery-" + uuid.uuid4().hex)
        output.mkdir(exist_ok=False)
        write(output / "inputs.json", dict(helper_sha256=sha(Path(__file__)), resources_before=before,
              synthetic_fixture=True, prepared_at=datetime.now(timezone.utc).isoformat()))
        print("Compiling recovery harness from installed jars...", flush=True)
        jar = compile_harness(root, tools, output)
        if args.build_only:
            print(json.dumps({"compiled": True, "spark_executed": False, "report_directory": str(output)}))
            return 0
        require_resources(root)
        command = [str(tools["submit"]), "--master", "local[1]", "--driver-memory", "1g",
                   "--conf", "spark.driver.host=127.0.0.1",
                   "--conf", "spark.driver.bindAddress=127.0.0.1",
                   "--conf", "spark.ui.enabled=false", "--conf", "spark.jars.packages=",
                   "--conf", "spark.local.dir=" + str(output / "spark-scratch"),
                   "--class", MAIN_CLASS, str(jar), str(output), str(jar), str(tools["scala_library"])]
        for value in command:
            shell_safe(value)
        print("Running isolated writer-lock/checkpoint/staging checks...", flush=True)
        with (output / "spark.log").open("x", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=root, env=tools["env"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    if line.startswith(("PASS:", "FAIL:")):
                        print(line.rstrip(), flush=True)
                code = process.wait()
            finally:
                if process.stdout is not None:
                    process.stdout.close()
        report_path = output / "recovery_report.json"
        if not report_path.is_file():
            raise RuntimeError("Recovery report not produced; inspect " + str(output / "spark.log"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if code != 0 or report.get("passed") is not True:
            raise RuntimeError("Recovery assertions failed; inspect " + str(report_path))
        write(output / "execution.json", dict(passed=True, process_exit_code=code,
              report_directory=str(output), synthetic_fixture=True,
              resources_after=resource_snapshot(root)))
        print(json.dumps({"passed": True, "checks_passed": len(report["checks"]),
                          "report_directory": str(output), "limitations": report["limitations"]}, indent=2))
        return 0
    except Exception as error:
        result = {"passed": False, "error_type": type(error).__name__, "detail": str(error),
                  "report_directory": str(output) if output else None,
                  "note": "Preserve this isolated test directory; never reset previous stream checkpoints."}
        if output is not None:
            write(output / "failure.json", result)
        print(json.dumps(result, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

