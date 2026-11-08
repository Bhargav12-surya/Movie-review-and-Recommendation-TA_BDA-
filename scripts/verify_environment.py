"""Inspect local prerequisites without installation, downloads, or training."""
from __future__ import annotations

import argparse
from importlib import metadata, util
import json
import os
from pathlib import Path
import re
import struct
import sys

# Load this project's owned helper by exact path even under Python -I.
_spec = util.spec_from_file_location(
    "_verification_common", Path(__file__).with_name("_verification_common.py")
)
common = util.module_from_spec(_spec)
_spec.loader.exec_module(common)

PACKAGE_PHASES = {
    "numpy": 1, "pandas": 1, "scikit-learn": 1, "pyarrow": 1,
    "PyYAML": 1, "pytest": 1, "httpx": 1, "matplotlib": 1,
    "seaborn": 1, "python-dotenv": 1, "jupyterlab": 1,
    "torch": 3, "transformers": 3, "datasets": 3, "accelerate": 3,
    "tokenizers": 3, "safetensors": 3, "sentence-transformers": 5,
    "bertopic": 5, "fastapi": 9, "uvicorn": 9, "sqlalchemy": 9,
    "psycopg": 9, "pgvector": 9, "alembic": 9, "pydantic": 9,
    "pydantic-settings": 9,
    "faster-whisper": 11,
}

CUDA_CODE = r"""
import json
import torch
if not torch.cuda.is_available():
    print(json.dumps({"status":"fail","reason":"torch.cuda.is_available() is false",
        "torch_version":torch.__version__,"runtime":torch.version.cuda}))
else:
    torch.cuda.reset_peak_memory_stats()
    x=torch.randn(8,8,device="cuda")
    result=x@x.T
    torch.cuda.synchronize()
    capability=list(torch.cuda.get_device_capability(0))
    architectures=torch.cuda.get_arch_list()
    precisions={}
    for name,dtype in (("fp16",torch.float16),("bf16",torch.bfloat16)):
        if name=="bf16" and not torch.cuda.is_bf16_supported():
            precisions[name]={"supported":False,"reason":"runtime reports BF16 unsupported"}
            continue
        try:
            a=x.to(dtype=dtype)
            y=a@a.T
            torch.cuda.synchronize()
            precisions[name]={"supported":bool(torch.isfinite(y).all().item())}
        except Exception as error:
            precisions[name]={"supported":False,"reason":str(error)}
    finite=bool(torch.isfinite(result).all().item())
    sm120=any(value in ("sm_120","compute_120") for value in architectures)
    print(json.dumps({"status":"pass" if finite and capability==[12,0] and sm120 else "fail",
        "torch_version":torch.__version__,"runtime":torch.version.cuda,
        "device":torch.cuda.get_device_name(0),"capability":capability,
        "architectures":architectures,"sm120_listed":sm120,"finite_result":finite,
        "precisions":precisions,"peak_allocated_bytes":torch.cuda.max_memory_allocated(),
        "reserved_bytes":torch.cuda.memory_reserved(),
        "note":"Tiny tensor inference checks only; no model, backward pass, or training."}))
"""


def package_metadata(report: dict) -> dict[str, str | None]:
    installed = {}
    nlp_packages = {"torch", "transformers", "datasets", "accelerate", "tokenizers", "safetensors"}
    backend_packages = {"fastapi", "uvicorn", "sqlalchemy", "psycopg", "pgvector",
                        "alembic", "pydantic", "pydantic-settings"}
    optional_packages = {"bertopic", "faster-whisper"}
    for package, phase in PACKAGE_PHASES.items():
        try:
            version = metadata.version(package)
        except metadata.PackageNotFoundError:
            version = None
        installed[package] = version
        required = (
            report["profile"] == "Nlp" and package in nlp_packages
            or report["profile"] == "Backend" and package in backend_packages
            or report["profile"] == "All" and package not in optional_packages
        )
        common.add_check(
            report, f"package.{package}", "pass" if version else "missing",
            f"Installed metadata: {version}; import not tested." if version else
            f"Not installed in selected interpreter; relevant from phase {phase}.",
            phase=phase, version=version, required=required,
            optional=package in optional_packages,
        )
    report["notes"].append(
        "Package metadata is not import, ABI, model, or GPU validation. Foundation/Data "
        "readiness covers the standard-library validation tools only; missing scientific "
        "and notebook packages remain explicit prerequisites for the affected work."
    )
    return installed


def check_program(report: dict, check_id: str, name: str, arguments: list[str],
                  required: bool, phase: int, expected: str | None = None) -> dict | None:
    location = common.executable(name)
    if location is None:
        common.add_check(report, check_id, "missing", f"{name} not found on PATH.",
                         required=required, phase=phase)
        return None
    result = common.run_program([location, *arguments])
    text = (result["stdout"] + "\n" + result["stderr"]).strip()
    ok = result["exit_code"] == 0 and (expected is None or expected in text)
    common.add_check(report, check_id, "pass" if ok else "fail",
                     text[:1200] if text else result.get("error", "No version output."),
                     required=required, phase=phase, path=location,
                     exit_code=result["exit_code"], timed_out=result["timed_out"])
    return result


def inspect(workspace: Path, config: dict, args: argparse.Namespace, report: dict) -> None:
    profile = args.profile
    required = lambda scope: profile in (scope, "All")
    expected_version = str(config["python"].get("version", "3.11.9"))
    actual_version = ".".join(map(str, sys.version_info[:3]))
    version_ok = actual_version == expected_version and struct.calcsize("P") * 8 == 64
    common.add_check(report, "python.interpreter", "pass" if version_ok else "fail",
                     f"Python {actual_version}, {struct.calcsize('P') * 8}-bit; "
                     f"expected {expected_version}, 64-bit.", required=True,
                     executable=sys.executable)
    configured_python = Path(config["python"].get("path", ".venv/Scripts/python.exe"))
    if not configured_python.is_absolute():
        configured_python = workspace / configured_python
    correct_environment = (
        sys.prefix != sys.base_prefix
        and Path(sys.executable).resolve() == configured_python.resolve()
    )
    common.add_check(report, "python.project_environment",
                     "pass" if correct_environment else "fail",
                     "Selected interpreter matches the isolated configured project environment."
                     if correct_environment else
                     "Use the configured isolated root .venv; global/legacy interpreters do not qualify.",
                     required=True, prefix=sys.prefix, base_prefix=sys.base_prefix,
                     configured_executable=str(configured_python.resolve()))

    resources = common.resource_snapshot(workspace)
    report["resources"] = resources
    disk_floor = float(config["resources"].get("minimum_disk_free_gib", 20))
    disk_ok = resources["disk"]["free_bytes"] >= disk_floor * 1024**3
    common.add_check(report, "resources.disk", "pass" if disk_ok else "fail",
                     f"{resources['disk']['free_gib']} GiB free; "
                     f"configured reserve {disk_floor:g} GiB.", required=True)
    memory = resources["memory"]
    memory_floor = float(config["resources"].get("minimum_available_memory_mib", 512))
    if memory["status"] == "measured":
        available = memory["available_mib"]
        common.add_check(report, "resources.memory",
                         "warning" if available < max(2048, memory_floor) else "pass",
                         f"{available} MiB available; configured diagnostic floor "
                         f"{memory_floor:g} MiB. This does not certify Spark/training headroom.")
    else:
        common.add_check(report, "resources.memory", "warning", memory["reason"])

    packages = package_metadata(report)
    check_program(report, "tool.git", "git", ["--version"], True, 0)
    git = common.executable("git")
    if git:
        result = common.run_program([git, "-C", str(workspace), "status", "--porcelain=v1"])
        if result["exit_code"] == 0:
            statuses = [line[:2] for line in result["stdout"].splitlines() if len(line) >= 2]
            report["git"] = {
                "tracked_deletions": sum("D" in status for status in statuses),
                "untracked_entries": statuses.count("??"),
                "staged_entries": sum(status[0] not in (" ", "?") for status in statuses),
                "note": "Status inspected only; no staging, restoration, or commit.",
            }
        else:
            common.add_check(report, "git.status", "fail", "Git status could not be read.",
                             required=True, exit_code=result["exit_code"])

    java_home = Path(args.java_home or config["java"].get("home", ""))
    java_binary = java_home / "bin" / ("java.exe" if os.name == "nt" else "java")
    if java_binary.is_file():
        result = common.run_program([str(java_binary), "-version"])
        output = (result["stdout"] + result["stderr"]).strip()
        match = re.search(r'version "(\d+)', output)
        java_ok = result["exit_code"] == 0 and match and int(match[1]) == int(config["java"].get("major", 21))
        common.add_check(report, "java.project", "pass" if java_ok else "fail",
                         output[:1200], required=True, path=str(java_binary),
                         exit_code=result["exit_code"])
    else:
        common.add_check(report, "java.project", "missing",
                         "Configured JDK executable not found.", required=True,
                         path=str(java_binary))
    global_home = os.environ.get("JAVA_HOME")
    same_home = bool(global_home) and Path(global_home).resolve() == java_home.resolve()
    common.add_check(report, "java.global_home", "pass" if same_home else "warning",
                     "Process JAVA_HOME matches the selected project JDK." if same_home else
                     "Process JAVA_HOME differs/unset; the verifier used the configured JDK "
                     "directly. Future Spark launchers must select it in the child process.",
                     observed=global_home, selected=str(java_home))

    for name, phase in (("sbt", 2), ("spark-submit", 2), ("spark-shell", 2),
                        ("node", 10), ("npm", 10), ("psql", 9), ("pg_config", 9)):
        location = common.executable(name)
        scope = "Spark" if phase == 2 else "Frontend" if phase == 10 else "Backend"
        if name == "sbt" and location:
            common.add_check(report, f"tool.{name}", "unverified",
                             "Launcher found. It was not executed because SBT may resolve "
                             "and download dependencies; manual setup approval is required.",
                             phase=phase, required=required(scope), path=location)
        elif location and name in ("node", "npm", "psql", "pg_config"):
            check_program(report, f"tool.{name}", name, ["--version"],
                          required(scope), phase,
                          expected="v24." if name == "node" else None)
        elif location and name == "spark-submit":
            result = common.run_program([location, "--version"], environment={
                "JAVA_HOME": str(java_home),
                "PATH": str(java_home / "bin") + os.pathsep + os.environ.get("PATH", ""),
            })
            output = result["stdout"] + result["stderr"]
            version_ok = result["exit_code"] == 0 and str(config["spark"].get("version", "4.3.0")) in output
            common.add_check(report, f"tool.{name}", "pass" if version_ok else "fail",
                             output.strip()[:1800] or result.get("error", "No version output."),
                             phase=phase, required=required(scope), path=location,
                             exit_code=result["exit_code"])
        else:
            common.add_check(report, f"tool.{name}", "present" if location else "missing",
                             "Launcher found; interactive shell was not started." if location else
                             f"{name} not found on PATH; required for phase {phase}.",
                             phase=phase, required=required(scope) and name != "spark-shell",
                             path=location)

    nvidia = check_program(
        report, "gpu.driver", "nvidia-smi",
        ["--query-gpu=name,driver_version,memory.total,memory.free,compute_cap",
         "--format=csv,noheader"], required("Nlp"), 3,
    )
    if nvidia and nvidia["exit_code"] == 0:
        report["gpu_driver_query"] = nvidia["stdout"].strip()
    cuda_requested = args.check_cuda or profile in ("Nlp", "All")
    if not cuda_requested:
        common.add_check(report, "gpu.pytorch_cuda", "deferred",
                         "Not requested. Use -CheckCuda after manually installing the approved "
                         "CUDA PyTorch wheel in the project environment.", phase=3)
    elif not packages.get("torch"):
        common.add_check(report, "gpu.pytorch_cuda", "missing",
                         "torch is absent from the project environment; no import or GPU "
                         "operation attempted.", required=True, phase=3)
    elif memory["status"] == "measured" and memory["available_mib"] < memory_floor:
        common.add_check(report, "gpu.pytorch_cuda", "blocked",
                         "Insufficient currently available RAM for the configured diagnostic "
                         "floor. No torch import attempted.", required=True, phase=3)
    else:
        result = common.run_program([sys.executable, "-I", "-B", "-c", CUDA_CODE], timeout=45)
        try:
            evidence = json.loads(result["stdout"]) if result["exit_code"] == 0 else None
        except json.JSONDecodeError:
            evidence = None
        status = evidence.get("status", "fail") if isinstance(evidence, dict) else "fail"
        common.add_check(report, "gpu.pytorch_cuda", status,
                         "Actual tiny CUDA tensor/precision checks; no training." if evidence else
                         "CUDA diagnostic did not complete successfully.",
                         required=True, phase=3, evidence=evidence,
                         exit_code=result["exit_code"], timed_out=result["timed_out"],
                         diagnostic_error=result.get("error") or result["stderr"][:2000])

    if args.check_imports:
        for package, module in (("numpy", "numpy"), ("pandas", "pandas"),
                                ("scikit-learn", "sklearn"), ("pyarrow", "pyarrow"),
                                ("PyYAML", "yaml"), ("pytest", "pytest")):
            if not packages.get(package):
                common.add_check(report, f"import.{package}", "missing",
                                 "Package absent; import was not attempted.", phase=1)
                continue
            result = common.run_program(
                [sys.executable, "-I", "-B", "-c", f"import {module}; print('IMPORT_OK')"],
                timeout=20,
            )
            ok = result["exit_code"] == 0 and "IMPORT_OK" in result["stdout"]
            common.add_check(report, f"import.{package}", "pass" if ok else "fail",
                             "Runtime import passed." if ok else "Runtime import failed.",
                             phase=1, required=profile == "All",
                             exit_code=result["exit_code"],
                             timed_out=result["timed_out"],
                             diagnostic_error=result.get("error") or result["stderr"][:1500])
    report["notes"].append(
        "No installation, SBT dependency resolution, download, model loading, training, "
        "application startup, global environment change, or raw-data mutation was performed."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--config-path")
    parser.add_argument("--java-home")
    parser.add_argument("--profile", choices=common.PROFILES, default="Foundation")
    parser.add_argument("--check-cuda", action="store_true")
    parser.add_argument("--check-imports", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output-path")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    report = common.new_report("verify_environment", workspace)
    report["profile"] = args.profile
    try:
        output = common.validate_output_path(workspace, args.output_path)
        config, path = common.load_config(workspace, args.config_path)
        report["configuration_path"] = path
        inspect(workspace, config, args, report)
        code = common.finalize(report)
        common.emit_report(report, output, args.json)
        return code
    except (OSError, ValueError, TypeError, KeyError) as error:
        return common.fail_report(report, error, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
