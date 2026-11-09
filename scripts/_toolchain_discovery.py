"""Read installed JVM tool metadata without launching a resolver or JVM.

These checks establish local files/version metadata only. They never certify a
successful build, a complete transitive classpath or an executed Spark job.
"""
from __future__ import annotations

import os
from pathlib import Path
import re

MAX_METADATA_BYTES = 65536


def selected_home(workspace: Path, explicit: str | None = None,
                  environment: str | None = None, configured: str | None = None) -> Path | None:
    """Honor explicit > named environment value > project configuration.

    An explicitly selected but missing installation is reported as missing;
    silently falling back could run a different tool than the user selected.
    """
    value = explicit or environment or configured
    if not value:
        return None
    supplied = Path(value)
    return (supplied if supplied.is_absolute() else workspace / supplied).resolve()


def _text(path: Path) -> str | None:
    if not path.is_file() or path.stat().st_size > MAX_METADATA_BYTES:
        return None
    return path.read_text(encoding="utf-8-sig", errors="strict")


def spark_metadata(home: Path | None, expected: dict) -> dict:
    binary = "spark-submit.cmd" if os.name == "nt" else "spark-submit"
    shell = "spark-shell.cmd" if os.name == "nt" else "spark-shell"
    jars = [f"spark-{name}_2.13-{expected['version']}.jar" for name in ("core", "sql", "mllib")]
    jars += [f"scala-library-{expected['scala_version']}.jar",
             f"hadoop-client-api-{expected.get('hadoop_version', '3.5.0')}.jar",
             f"hadoop-client-runtime-{expected.get('hadoop_version', '3.5.0')}.jar"]
    result = {"status": "missing", "home": str(home) if home else None,
              "submit": str(home / "bin" / binary) if home else None,
              "shell": str(home / "bin" / shell) if home else None,
              "missing_jars": jars, "version": None, "hadoop_version": None,
              "runtime_executed": False, "metadata_only": True}
    if home is None:
        return result
    release = _text(home / "RELEASE")
    match = re.search(r"\bSpark\s+([0-9]+\.[0-9]+\.[0-9]+)\b.*\bHadoop\s+([0-9]+\.[0-9]+\.[0-9]+)\b",
                      release or "")
    result["missing_jars"] = [name for name in jars if not (home / "jars" / name).is_file()]
    if match:
        result["version"], result["hadoop_version"] = match.groups()
    if not (home / "bin" / binary).is_file() or result["missing_jars"]:
        return result
    if not match:
        result["status"] = "unverified"
    else:
        result["status"] = "pass" if (
            result["version"] == str(expected["version"])
            and result["hadoop_version"] == str(expected.get("hadoop_version", "3.5.0"))) else "fail"
    return result


def sbt_metadata(home: Path | None, expected_version: str) -> dict:
    binary = "sbt.bat" if os.name == "nt" else "sbt"
    launcher = home / "bin" / binary if home else None
    result = {"status": "missing", "home": str(home) if home else None,
              "launcher": str(launcher) if launcher else None,
              "launcher_default_version": None, "bootstrap_verified": False,
              "runtime_executed": False, "metadata_only": True}
    if launcher is None or not launcher.is_file() or not (home / "bin/sbt-launch.jar").is_file():
        return result
    source = _text(launcher)
    match = re.search(r"(?m)^\s*(?:set\s+|declare\s+(?:-r\s+)?)?init_sbt_version=[\"']?([0-9]+\.[0-9]+\.[0-9]+)",
                      source or "")
    if not match:
        result["status"] = "unverified"
    else:
        result["launcher_default_version"] = match.group(1)
        result["status"] = "pass" if match.group(1) == str(expected_version) else "fail"
    return result
