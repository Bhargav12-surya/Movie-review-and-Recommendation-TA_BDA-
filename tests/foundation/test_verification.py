"""Behavioral tests for safe, local-only environment and health diagnostics.

HTTP responses in this file are isolated synthetic test fixtures, never
application evidence, movie predictions, or academic model measurements.
"""
from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
import uuid

WORKSPACE = Path(__file__).resolve().parents[2]
SCRIPTS = WORKSPACE / "scripts"
PYTHON = WORKSPACE / ".venv/Scripts/python.exe"
POWERSHELL = shutil.which("powershell.exe")


def load_owned_module(name: str):
    spec = util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = load_owned_module("_verification_common")


def cli(name: str, *arguments: str, powershell: bool = False):
    if powershell:
        command = [POWERSHELL, "-NoLogo", "-NoProfile", "-File",
                   str(SCRIPTS / f"{name}.ps1"), "-Json", *arguments]
    else:
        command = [str(PYTHON), "-I", "-B", str(SCRIPTS / f"{name}.py"),
                   "--json", *arguments]
    completed = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=45, check=False, cwd=WORKSPACE,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if completed.stderr:
        raise AssertionError(f"Unexpected diagnostic stderr: {completed.stderr}")
    return completed.returncode, json.loads(completed.stdout)


def unused_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@contextmanager
def synthetic_health_server(payload: dict | None = None, redirect: bool = False):
    class FixtureHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if redirect:
                self.send_response(302)
                self.send_header("Location", "https://example.com/never-request")
                self.end_headers()
                return
            body = json.dumps(payload or {"status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join(timeout=3)


class SharedSafetyTests(unittest.TestCase):
    def test_report_refuses_raw_or_outside_or_existing_paths(self):
        with tempfile.TemporaryDirectory(prefix=".foundation-test-", dir=WORKSPACE) as temporary:
            folder = Path(temporary)
            original = folder / "existing.json"
            original.write_text("original", encoding="utf-8")
            for target in (
                WORKSPACE / "data/raw" / f"forbidden-{uuid.uuid4().hex}.json",
                WORKSPACE.parent / "outside-report.json",
                WORKSPACE / ".git" / "report.json",
                WORKSPACE / "temp" / "report.json",
                original,
            ):
                with self.subTest(target=str(target)):
                    with self.assertRaises(ValueError):
                        common.validate_output_path(WORKSPACE, str(target))
            self.assertEqual(original.read_text(encoding="utf-8"), "original")

    def test_report_output_is_exclusively_created(self):
        with tempfile.TemporaryDirectory(prefix=".foundation-test-", dir=WORKSPACE) as temporary:
            target = Path(temporary) / "report.json"
            report = common.new_report("test_fixture", WORKSPACE)
            common.finalize(report)
            common.emit_report(report, target, False)
            saved = target.read_bytes()
            with self.assertRaises(FileExistsError):
                common.emit_report(report, target, False)
            self.assertEqual(target.read_bytes(), saved)
            self.assertTrue(json.loads(saved)["ready"])

    def test_missing_explicit_config_does_not_silently_use_defaults(self):
        with self.assertRaises(ValueError):
            common.load_config(WORKSPACE, "nonexistent-explicit-configuration.json")

    def test_malformed_configuration_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix=".foundation-test-", dir=WORKSPACE) as temporary:
            path = Path(temporary) / "invalid.json"
            path.write_text('{"schema_version":1,"python":[]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                common.load_config(WORKSPACE, str(path))

    def test_timeout_stops_owned_diagnostic_process(self):
        result = common.run_program(
            [str(PYTHON), "-I", "-B", "-c", "import time; time.sleep(10)"],
            timeout=0.15,
        )
        self.assertTrue(result["timed_out"])
        self.assertIsNone(result["exit_code"])

    def test_required_unverified_result_does_not_pass_readiness(self):
        report = common.new_report("synthetic_fixture", WORKSPACE)
        common.add_check(report, "fixture.service", "unverified",
                         "Synthetic transport-only fixture.", required=True)
        self.assertEqual(common.finalize(report), 2)
        self.assertFalse(report["ready"])

    def test_child_environment_override_does_not_change_parent(self):
        before = os.environ.get("JAVA_HOME")
        result = common.run_program(
            [str(PYTHON), "-I", "-B", "-c",
             "import os; print(os.environ['JAVA_HOME'])"],
            environment={"JAVA_HOME": "SYNTHETIC_CHILD_ONLY"},
        )
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"].strip(), "SYNTHETIC_CHILD_ONLY")
        self.assertEqual(os.environ.get("JAVA_HOME"), before)


@unittest.skipUnless(os.name == "nt" and PYTHON.exists() and POWERSHELL,
                     "Requires the Windows project environment and PowerShell.")
class WindowsCommandTests(unittest.TestCase):
    def test_powershell_scripts_parse(self):
        source = (
            "$failures=@(); foreach($file in @("
            + ",".join("'" + str(SCRIPTS / f"{name}.ps1").replace("'", "''") + "'"
                       for name in ("verify_environment", "check_health"))
            + ")){ $tokens=$null; $parseErrors=$null; "
            "[void][System.Management.Automation.Language.Parser]::ParseFile("
            "$file,[ref]$tokens,[ref]$parseErrors); $failures+=@($parseErrors) }; "
            "if($failures.Count){$failures | ForEach-Object {$_.Message}; exit 1}"
        )
        completed = subprocess.run(
            [POWERSHELL, "-NoLogo", "-NoProfile", "-Command", source],
            capture_output=True, text=True, timeout=15, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_actual_foundation_uses_project_interpreter_and_reports_later_blockers(self):
        code, report = cli("verify_environment", "-Profile", "Foundation", powershell=True)
        checks = {item["id"]: item for item in report["checks"]}
        self.assertEqual(code, report["exit_code"])
        self.assertEqual(checks["python.project_environment"]["status"], "pass")
        self.assertEqual(checks["python.interpreter"]["status"], "pass")
        self.assertEqual(checks["java.project"]["status"], "pass")
        self.assertEqual(checks["gpu.pytorch_cuda"]["status"], "deferred")
        self.assertEqual(checks["tool.node"]["phase"], 10)
        self.assertFalse(checks["tool.node"]["required"])
        # RAM/disk pressure may legitimately block a later run; inspect, do not fake it.
        if checks["resources.disk"]["status"] == "pass":
            self.assertEqual(code, 0)
        else:
            self.assertEqual(code, 2)

    def test_missing_selected_python_does_not_fall_back_to_global(self):
        missing = str(WORKSPACE / ".venv" / f"missing-{uuid.uuid4().hex}.exe")
        code, report = cli("verify_environment", "-PythonPath", missing, powershell=True)
        self.assertEqual(code, 2)
        self.assertEqual(report["blocking_checks"], ["python.executable"])
        self.assertFalse(report["ready"])

    def test_protected_report_target_never_creates_raw_file(self):
        target = WORKSPACE / "data/raw" / f"forbidden-{uuid.uuid4().hex}.json"
        code, report = cli("verify_environment", "-OutputPath", str(target), powershell=True)
        self.assertEqual(code, 1)
        self.assertFalse(target.exists())
        self.assertIn("protected", report["checks"][-1]["detail"])

    def test_explicit_bad_configuration_returns_structured_error(self):
        with tempfile.TemporaryDirectory(prefix=".foundation-test-", dir=WORKSPACE) as temporary:
            target = Path(temporary) / "invalid.json"
            target.write_text("{not-json", encoding="utf-8")
            code, report = cli("verify_environment", "-ConfigPath", str(target), powershell=True)
            self.assertEqual(code, 1)
            self.assertFalse(report["ready"])
            self.assertEqual(report["checks"][-1]["id"], "verification.error")

    def test_gpu_profile_reports_absence_without_fabricated_success(self):
        code, report = cli("verify_environment", "--profile", "Nlp")
        check = next(item for item in report["checks"] if item["id"] == "gpu.pytorch_cuda")
        transformers = next(item for item in report["checks"] if item["id"] == "package.transformers")
        self.assertNotEqual(check["status"], "deferred")
        self.assertEqual(check["required"], True)
        self.assertEqual(transformers["required"], True)
        self.assertEqual(code, 0 if report["ready"] else 2)

    def test_http_200_does_not_claim_backend_or_database_ready(self):
        with synthetic_health_server() as base_url:
            code, report = cli(
                "check_health", "--backend-url", base_url + "/health",
                "--frontend-url", base_url, "--postgres-port", str(unused_port()),
                "--timeout", "0.3",
            )
        checks = {item["id"]: item for item in report["checks"]}
        self.assertEqual(checks["backend.http"]["status"], "pass")
        self.assertEqual(checks["backend.readiness"]["status"], "unverified")
        self.assertEqual(checks["postgres.sql"]["status"], "deferred")
        self.assertEqual(code, 2)
        self.assertFalse(report["ready"])

    def test_external_targets_are_rejected_before_requests(self):
        code, report = cli("check_health", "--backend-url", "https://example.com/health")
        self.assertEqual(code, 1)
        self.assertEqual(len(report["checks"]), 1)
        self.assertIn("localhost", report["checks"][0]["detail"])

    def test_local_redirect_cannot_trigger_external_request(self):
        health = load_owned_module("check_health")
        with synthetic_health_server(redirect=True) as base_url:
            result = health.http_probe(base_url, 0.5)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["http_status"], 302)


if __name__ == "__main__":
    unittest.main()
