"""Static Scala parser only, using the already installed exact compiler JARs.

Stops before typing, code generation or execution. No SBT/resolver/Spark job.
"""
import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess
import uuid


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-harness',action='store_true',help='Also parse existing scripts/test-harness Scala sources,without executing them.')
    arguments=parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "configs/environment.json").read_text(encoding="utf-8-sig"))
    java = Path(config["java"]["home"]) / "bin/java.exe"
    version = config["spark"]["scala_version"]
    jars = [Path(config["spark"]["home"]) / "jars" / ("scala-" + name + "-" + version + ".jar") for name in ("compiler", "library", "reflect")]
    if not java.is_file() or any(not path.is_file() for path in jars):
        print(json.dumps({"status": "blocked", "reason": "Exact local parser toolchain missing; no resolver fallback."}))
        return 2
    sources = sorted((root / "scala/src").rglob("*.scala"))
    if arguments.include_harness:sources += sorted((root/'scripts/test-harness').glob('*.scala'))
    classpath = os.pathsep.join(map(str, jars))
    environment = os.environ.copy()
    for name in ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH"):
        environment.pop(name, None)
    command = [str(java), "-Xmx256m", "-cp", classpath, "scala.tools.nsc.Main", "-usejavacp", "-Ystop-after:parser", *map(str, sources)]
    result = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    report = {"status": "parsed" if result.returncode == 0 else "failed", "source_count": len(sources),
        "scope": "scala_parser_only_no_typing_codegen_or_execution", "compiler_exit_code": result.returncode,
        "diagnostics": result.stdout + result.stderr, "spark_executed": False, "resolver_invoked": False,
        "files_sha256": {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}}
    output = root / "artifacts/source_validation" / ("scala-parser-" + uuid.uuid4().hex + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({key: value for key, value in report.items() if key != "files_sha256"}, indent=2))
    print("Report: " + str(output))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
