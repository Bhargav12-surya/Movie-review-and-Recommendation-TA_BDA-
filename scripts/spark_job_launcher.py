"""Launch only an already installed local Spark distribution and built project JAR.

No build tool, dependency resolver, downloader, installer or model is invoked.
Preflight/dry-run inspect metadata and render arguments without starting Spark.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _verification_common as common
from _toolchain_discovery import selected_home

JOBS = ("preflight", "batch", "rdd", "smoke", "stream")
UNSAFE = re.compile(r'[\x00-\x1f"&|<>^%!]')
INHERITED_OPTIONS = ("SPARK_SUBMIT_OPTS", "JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS",
                     "JDK_JAVA_OPTIONS", "SPARK_DIST_CLASSPATH", "SPARK_DRIVER_EXTRA_CLASSPATH",
                     "SPARK_PREPEND_CLASSES", "CLASSPATH", "HADOOP_CONF_DIR", "YARN_CONF_DIR")


def shell_safe(value: str) -> str:
    if UNSAFE.search(value):
        raise ValueError("A launcher argument contains an unsupported command-shell character.")
    return value


def local_path(root: Path, value: str | Path, *, output: bool = False) -> Path:
    given = Path(value)
    resolved = (given if given.is_absolute() else root / given).resolve()
    shell_safe(str(resolved))
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError("Project input/output/JAR paths must stay inside the workspace.")
    for prefix in ("data/raw", "temp", ".git", ".venv", "models"):
        protected = (root / prefix).resolve()
        # Raw data is read-only input; the other locations are never job data.
        if (output or prefix != "data/raw") and (
                resolved == protected or resolved.is_relative_to(protected)):
            raise ValueError(f"Unsupported project path under {prefix}.")
    if any(p.lower() in {".git", ".venv", "node_modules"} for p in resolved.relative_to(root).parts):
        raise ValueError("Project paths cannot enter dependency or Git directories.")
    return resolved


def _manifest(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if archive.getinfo("META-INF/MANIFEST.MF").file_size > 65536:
            raise ValueError("JAR manifest exceeds the bounded metadata limit.")
        text = archive.read("META-INF/MANIFEST.MF").decode("utf-8")
    attributes: dict[str, str] = {}
    previous = None
    for line in text.splitlines():
        if line.startswith(" ") and previous:
            attributes[previous] += line[1:]
        elif ": " in line:
            previous, value = line.split(": ", 1)
            attributes[previous] = value
    attributes["_has_main"] = str("com/movieintel/Main$.class" in names)
    return attributes


def runtime_checks(report: dict, config: dict, java_home: Path, spark_home: Path | None,
                   jar: Path) -> tuple[Path | None, bool]:
    java = java_home / "bin" / ("java.exe" if os.name == "nt" else "java")
    release = java_home / "release"
    valid_java = False
    if java.is_file() and release.is_file() and release.stat().st_size < 65536:
        match = re.search(r'^JAVA_VERSION="([^"]+)"', release.read_text(encoding="utf-8"),
                          flags=re.MULTILINE)
        valid_java = bool(match and match.group(1).split(".")[0] == str(config["java"]["major"]))
    common.add_check(report, "java.installation", "pass" if valid_java else "missing",
                     "Selected JDK files/release metadata match the configured major; no installer ran."
                     if valid_java else "Selected JDK installation/release metadata is absent or incompatible.",
                     required=True, path=str(java))
    submit = None
    expected = config["spark"]
    names = [
        f"spark-core_2.13-{expected['version']}.jar",
        f"spark-sql_2.13-{expected['version']}.jar",
        f"spark-mllib_2.13-{expected['version']}.jar",
        f"scala-library-{expected['scala_version']}.jar",
        f"hadoop-client-api-{expected.get('hadoop_version', '3.5.0')}.jar",
        f"hadoop-client-runtime-{expected.get('hadoop_version', '3.5.0')}.jar",
    ]
    missing = names[:]
    if spark_home:
        submit = spark_home / "bin" / ("spark-submit.cmd" if os.name == "nt" else "spark-submit")
        missing = [name for name in names if not (spark_home / "jars" / name).is_file()]
    valid_spark = bool(submit and submit.is_file() and not missing)
    common.add_check(report, "spark.distribution", "pass" if valid_spark else "missing",
                     "Pinned Spark/Scala/Hadoop distribution files found; actual execution remains separate."
                     if valid_spark else "Manually install the pinned Spark distribution; no resolver fallback exists.",
                     required=True, path=str(submit) if submit else None, missing_files=missing)
    manifest = {}
    try:
        if jar.is_file():
            manifest = _manifest(jar)
    except (OSError, zipfile.BadZipFile, KeyError, UnicodeError, ValueError):
        pass
    valid_jar = (manifest.get("Spark-Version") == expected["version"]
                 and manifest.get("Scala-Version") == expected["scala_version"]
                 and manifest.get("_has_main") == "True")
    common.add_check(report, "project.jar", "pass" if valid_jar else "missing",
                     "Built JAR manifest and entry point match the pinned project."
                     if valid_jar else "Build the pinned Scala project manually after dependency preparation.",
                     required=True, path=str(jar))
    conf = None
    # Use a project-owned empty config directory, never arbitrary global defaults.
    # SPARK_CONF_DIR is supplied only to the launched child.
    conf = Path(report["workspace"]) / "configs" / "spark-local"
    network_defaults = bool(conf and any((conf / name).exists() for name in ("spark-env.cmd", "spark-env.sh")))
    if conf and (conf / "spark-defaults.conf").is_file():
        file = conf / "spark-defaults.conf"
        if file.stat().st_size > 1024 * 1024:
            network_defaults = True
        else:
            for line in file.read_text(encoding="utf-8").splitlines():
                active = line.strip()
                if active and not active.startswith("#") and re.match(
                        r"spark\.(jars|files|archives|master)([.\s=]|$)", active):
                    network_defaults = True
    inherited = [name for name in INHERITED_OPTIONS if os.environ.get(name)]
    common.add_check(report, "runtime.unreviewed_options",
                     "blocked" if network_defaults or inherited else "pass",
                     "Unreviewed JVM/Spark options or resolver defaults require manual review."
                     if network_defaults or inherited else "No automatic dependency resolution option was found.",
                     required=True, variable_names=inherited,
                     resolver_defaults_found=network_defaults)
    return submit, valid_spark


def build_command(args: argparse.Namespace, root: Path, submit: Path | None, jar: Path,
                  input_path: Path, output: Path | None, event_input: Path | None,
                  checkpoint: Path | None) -> list[str]:
    if args.job == "preflight":
        return []
    command = [str(submit) if submit else "<SPARK_HOME>/bin/spark-submit.cmd",
               "--master", args.master, "--driver-memory", args.driver_memory,
               "--conf", "spark.driver.bindAddress=127.0.0.1",
               "--conf", "spark.driver.host=127.0.0.1",
               "--conf", "spark.jars.packages=",
               "--class", "com.movieintel.Main", str(jar),
               "--job", args.job, "--workspace", str(root), "--input", str(input_path),
               "--output", str(output), "--master", args.master,
               "--shuffle-partitions", str(args.shuffle_partitions),
               "--input-partitions", str(args.input_partitions),
               "--hold-ui-seconds", str(args.hold_ui_seconds)]
    if args.job == "stream":
        command += ["--event-input", str(event_input), "--checkpoint", str(checkpoint),
                    "--watermark", args.watermark, "--max-files-per-trigger", str(args.max_files_per_trigger)]
        if args.continuous:
            command.append("--continuous")
    if args.resume:
        command.append("--resume")
    if args.allow_synthetic_events:
        command.append("--allow-synthetic-events")
    # The placeholder preview is never executable. Every real argument is checked.
    for value in command[1:]:
        shell_safe(value)
    if submit:
        shell_safe(command[0])
    return command


def child_environment(java_home: Path, spark_home: Path, root: Path) -> dict[str, str]:
    child = os.environ.copy()
    child["JAVA_HOME"] = str(java_home)
    child["SPARK_HOME"] = str(spark_home)
    child["SPARK_LOCAL_IP"] = "127.0.0.1"
    child["SPARK_CONF_DIR"] = str(root / "configs" / "spark-local")
    for name in INHERITED_OPTIONS:
        child.pop(name, None)
    child["PATH"] = str(java_home / "bin") + os.pathsep + str(spark_home / "bin") + os.pathsep + child.get("PATH", "")
    return child




def execute_command(command: list[str], environment: dict[str, str], logs: Path) -> int:
    """Start one owned local job hidden; retain logs, never bootstrap software."""

    for value in command:
        shell_safe(value)

    actual = command
    flags = 0

    if os.name == "nt":
        comspec = Path(
            os.environ.get("SystemRoot", "C:/Windows")
        ) / "System32" / "cmd.exe"

        # Quote each argument individually.
        command_line = subprocess.list2cmdline(command)

        # Do not wrap the entire command in additional quotes.
        # CALL correctly invokes the batch file and preserves arguments.
        actual = f'"{comspec}" /d /c call {command_line}'

        flags = (
            subprocess.CREATE_NO_WINDOW
            | subprocess.CREATE_NEW_PROCESS_GROUP
        )

    with (logs / "stdout.log").open("xb") as stdout, \
         (logs / "stderr.log").open("xb") as stderr:

        process = subprocess.Popen(
            actual,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            env=environment,
            shell=False,
            creationflags=flags
        )

        try:
            return process.wait()

        except KeyboardInterrupt:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                process.terminate()

            process.wait(timeout=10)
            return 130




def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    value.add_argument("--config-path")
    value.add_argument("--job", choices=JOBS, default="preflight")
    value.add_argument("--spark-home")
    value.add_argument("--java-home")
    value.add_argument("--input", default="data/raw/movielens/ml-32m")
    value.add_argument("--output")
    value.add_argument("--jar", default="scala/target/scala-2.13/movieintel-spark_2.13-0.1.0.jar")
    value.add_argument("--master", default="local[2]")
    value.add_argument("--driver-memory", choices=("1g", "2g", "3g", "4g"), default="3g")
    value.add_argument("--shuffle-partitions", type=int, default=8)
    value.add_argument("--input-partitions", type=int, default=4)
    value.add_argument("--event-input")
    value.add_argument("--checkpoint")
    value.add_argument("--watermark", default="24 hours")
    value.add_argument("--max-files-per-trigger", type=int, default=5)
    value.add_argument("--continuous", action="store_true")
    value.add_argument("--resume", action="store_true")
    value.add_argument("--allow-synthetic-events", action="store_true")
    value.add_argument("--hold-ui-seconds", type=int, default=0)
    value.add_argument("--dry-run", action="store_true")
    value.add_argument("--json", action="store_true")
    value.add_argument("--report-path")
    return value


def inspect(args: argparse.Namespace, report: dict) -> tuple[list[str], dict[str, str]]:
    root = Path(args.workspace).resolve()
    if not root.is_dir():
        raise ValueError("Workspace does not exist.")
    if not re.fullmatch(r"local(?:\[[1-4]\])?", args.master):
        raise ValueError("Only bounded local or local[1] through local[4] masters are permitted.")
    if not 1 <= args.shuffle_partitions <= 128 or not 1 <= args.input_partitions <= 32:
        raise ValueError("Partition counts exceed the laptop limits.")
    if not 0 <= args.hold_ui_seconds <= 3600:
        raise ValueError("UI hold must be between 0 and 3600 seconds.")
    if not re.fullmatch(r"[1-9][0-9]* (seconds|minutes|hours|days)", args.watermark):
        raise ValueError("Watermark must be a positive whole interval.")
    if not 1 <= args.max_files_per_trigger <= 100:
        raise ValueError("File-trigger limit must be in 1..100.")
    if args.continuous and args.job != "stream":
        raise ValueError("Continuous triggering applies only to streaming.")
    if args.resume and args.job != "stream":
        raise ValueError("Resume is supported only for the streaming job.")
    if args.allow_synthetic_events and args.job != "stream":
        raise ValueError("Synthetic event permission applies only to streaming.")
    config, _ = common.load_config(root, args.config_path)
    java_home = Path(args.java_home or config["java"]["home"]).resolve()
    shell_safe(str(java_home))
    spark_home = selected_home(root, args.spark_home, os.environ.get("SPARK_HOME"),
                               config["spark"].get("home"))
    if spark_home:
        shell_safe(str(spark_home))
    jar = local_path(root, args.jar)
    input_path = local_path(root, args.input)
    output = local_path(root, args.output, output=True) if args.output else None
    event_input = local_path(root, args.event_input) if args.event_input else None
    checkpoint = local_path(root, args.checkpoint, output=True) if args.checkpoint else None
    if args.job != "preflight" and output is None:
        raise ValueError("An explicit new --output path is required.")
    if args.job == "stream":
        if event_input is None or checkpoint is None:
            raise ValueError("Streaming needs explicit, separate --event-input and --checkpoint paths.")
        if output.is_relative_to(event_input) or event_input.is_relative_to(output):
            raise ValueError("Streaming input and output must not overlap.")
        if (checkpoint.is_relative_to(event_input) or event_input.is_relative_to(checkpoint)
                or checkpoint.is_relative_to(output) or output.is_relative_to(checkpoint)):
            raise ValueError("Checkpoint, input and output must be distinct nonoverlapping paths.")
    if output and args.job in ("batch", "rdd"):
        if output.is_relative_to(input_path) or input_path.is_relative_to(output):
            raise ValueError("Batch input and output must not overlap.")
    if output:
        if args.resume and (not output.is_dir() or not checkpoint or not checkpoint.is_dir()):
            raise ValueError("Resume requires existing output and checkpoint directories.")
        if not args.resume and (output.exists() or (checkpoint and checkpoint.exists())):
            raise ValueError("Output/checkpoint already exists; no overwrite is permitted.")
    submit, _ = runtime_checks(report, config, java_home, spark_home, jar)
    resources = common.resource_snapshot(root)
    report["resources"] = resources
    common.add_check(report, "resources.disk",
                     "pass" if resources["disk"]["free_bytes"] >= 20 * 1024**3 else "blocked",
                     "Retain the 20 GiB workspace-drive reserve.", required=True)
    memory = resources["memory"]
    minimum = (int(args.driver_memory[0]) + 1) * 1024**3
    enough = memory.get("status") == "measured" and memory.get("available_bytes", 0) >= minimum
    common.add_check(report, "resources.ram", "pass" if enough else "blocked",
                     f"Driver heap plus 1 GiB headroom requires {minimum // 1024**3} GiB available RAM.",
                     required=True, minimum_available_bytes=minimum)
    if args.job in ("batch", "rdd"):
        required_files = ("movies.csv", "links.csv", "ratings.csv", "tags.csv")
        present = all((input_path / name).is_file() for name in required_files)
        common.add_check(report, "input.movielens", "pass" if present else "missing",
                         "The four local source CSV files must be present.", required=True)
    if args.job == "stream":
        common.add_check(report, "input.events", "pass" if event_input.is_dir() else "missing",
                         "Streaming source directory must already exist.", required=True)
    command = build_command(args, root, submit, jar, input_path, output, event_input, checkpoint)
    report.update(job=args.job, dry_run=args.dry_run, executed=False, command_preview=command,
                  selected_java_home=str(java_home), selected_spark_home=str(spark_home) if spark_home else None,
                  output_path=str(output) if output else None,
                  checkpoint_path=str(checkpoint) if checkpoint else None)
    report["notes"] += [
        "No installer, SBT, Scala launcher, resolver, dataset download or model is invoked.",
        "A file/manifest preflight is not Scala compilation or actual Spark execution evidence.",
        "The driver JVM receives process-scoped Java/Spark settings; global variables are unchanged.",
    ]
    return command, child_environment(java_home, spark_home, root) if spark_home else {}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.workspace).resolve()
    report = common.new_report("run_spark_jobs", root)
    report["profile"] = args.job
    try:
        output_report = common.validate_output_path(root, args.report_path)
        command, environment = inspect(args, report)
        exit_code = common.finalize(report)
        if not exit_code and args.job != "preflight" and not args.dry_run:
            log_root = local_path(root, "artifacts/spark-launcher", output=True)
            logs = log_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
            logs.mkdir(parents=True, exist_ok=False)
            code = execute_command(command, environment, logs)
            report.update(executed=True, process_exit_code=code, log_directory=str(logs))
            common.add_check(report, "spark.execution", "pass" if code == 0 else "fail",
                             f"Owned Spark process exited {code}; inspect saved stdout/stderr.",
                             required=True)
            common.finalize(report)
            report["exit_code"] = code
            common.emit_report(report, logs / "launcher_report.json", True)
            exit_code = code
        common.emit_report(report, output_report, args.json)
        return exit_code
    except (OSError, ValueError, KeyError, TypeError) as error:
        return common.fail_report(report, error, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
