"""Check existing localhost services without starting them or changing a database."""
from __future__ import annotations

import argparse
from importlib import util
import json
from pathlib import Path
import socket
from urllib import error, parse, request

_spec = util.spec_from_file_location(
    "_verification_common", Path(__file__).with_name("_verification_common.py")
)
common = util.module_from_spec(_spec)
_spec.loader.exec_module(common)
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def local_url(value: str) -> str:
    url = parse.urlsplit(value)
    if url.scheme not in ("http", "https") or url.hostname not in LOCAL_HOSTS:
        raise ValueError("Health requests are restricted to explicit localhost HTTP(S) URLs.")
    if url.username is not None or url.password is not None or url.query or url.fragment:
        raise ValueError("Health URLs must not contain credentials, queries, or fragments.")
    return value


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A local service cannot redirect this checker to an external provider.
        return None


def http_probe(url: str, timeout: float) -> dict:
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(url, timeout=timeout) as response:
            body = response.read(65537)
            if len(body) > 65536:
                return {"status": "fail", "reason": "Health response exceeds 64 KiB."}
            result = {"status": "pass", "http_status": response.status}
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            # Return only health fields; never echo arbitrary response bodies.
            if isinstance(payload, dict):
                result["declared_ready"] = payload.get("ready") if isinstance(payload.get("ready"), bool) else None
                result["declared_status"] = payload.get("status") if payload.get("status") in {
                    "ok", "healthy", "ready", "degraded", "unavailable", "error"
                } else None
            return result
    except (error.URLError, TimeoutError, OSError) as failure:
        return {"status": "fail", "reason": type(failure).__name__,
                "http_status": getattr(failure, "code", None)}


def tcp_probe(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def inspect(args: argparse.Namespace, report: dict) -> None:
    backend = http_probe(local_url(args.backend_url), args.timeout)
    common.add_check(report, "backend.http", backend["status"],
                     "HTTP transport responds." if backend["status"] == "pass" else
                     "Backend health endpoint did not respond successfully.",
                     required=True, phase=9, evidence=backend)
    if backend.get("declared_ready") is True:
        ready_status, detail = "pass", "Backend explicitly reports ready=true."
    elif backend.get("declared_ready") is False:
        ready_status, detail = "fail", "Backend explicitly reports ready=false."
    else:
        ready_status, detail = "unverified", "Backend readiness was not verified; HTTP success alone is insufficient."
    common.add_check(report, "backend.readiness", ready_status, detail,
                     required=True, phase=9)
    frontend = http_probe(local_url(args.frontend_url), args.timeout)
    common.add_check(report, "frontend.http", frontend["status"],
                     "Frontend HTTP transport responds; integration is not asserted." if
                     frontend["status"] == "pass" else "Frontend did not respond successfully.",
                     required=True, phase=10, evidence=frontend)

    if args.postgres_host not in LOCAL_HOSTS:
        raise ValueError("Database health requests are restricted to localhost.")
    reachable = tcp_probe(args.postgres_host, args.postgres_port, args.timeout)
    common.add_check(report, "postgres.tcp", "pass" if reachable else "missing",
                     "TCP port accepts a connection; database identity/authentication remain unverified."
                     if reachable else "No reachable PostgreSQL TCP listener.",
                     required=True, phase=9)
    if args.check_database:
        if not args.database_name or not args.database_user:
            raise ValueError("Explicit -DatabaseName and -DatabaseUser are required for the read-only SQL check.")
        psql = common.executable("psql")
        if not psql:
            common.add_check(report, "postgres.sql", "missing",
                             "psql not found; no SQL check ran.", required=True, phase=9)
        else:
            result = common.run_program([
                psql, "-X", "--no-password", "--host", args.postgres_host,
                "--port", str(args.postgres_port), "--username", args.database_user,
                "--dbname", args.database_name, "--tuples-only", "--no-align",
                "--command", "SELECT current_setting('server_version'), "
                "coalesce((SELECT extversion FROM pg_extension WHERE extname='vector'),'NOT_INSTALLED');",
            ], timeout=10, environment={"PGCONNECT_TIMEOUT": "3"})
            fields = result["stdout"].strip().split("|")
            valid = result["exit_code"] == 0 and len(fields) == 2
            common.add_check(report, "postgres.sql", "pass" if valid else "fail",
                             "Read-only connection and version query succeeded." if valid else
                             "Noninteractive SQL check failed; no password prompt or schema change.",
                             required=True, phase=9, exit_code=result["exit_code"],
                             server_version=fields[0] if valid else None)
            common.add_check(report, "postgres.pgvector",
                             "pass" if valid and fields[1] != "NOT_INSTALLED" else "missing",
                             "vector extension found in the selected database." if
                             valid and fields[1] != "NOT_INSTALLED" else
                             "vector extension not verified in the selected database.",
                             required=True, phase=9,
                             extension_version=fields[1] if valid else None)
    else:
        common.add_check(report, "postgres.sql", "deferred",
                         "No database credentials were requested or used. Add -CheckDatabase "
                         "with explicit database/user to execute a read-only query.",
                         required=True, phase=9)
    report["notes"].append(
        "No service was started, database created/migrated, password requested, model "
        "loaded, external URL contacted, or application integration claimed."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000/api/v1/health")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:3000")
    parser.add_argument("--postgres-host", default="127.0.0.1")
    parser.add_argument("--postgres-port", type=int, default=5432)
    parser.add_argument("--timeout", type=float, default=2)
    parser.add_argument("--check-database", action="store_true")
    parser.add_argument("--database-name")
    parser.add_argument("--database-user")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output-path")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    report = common.new_report("check_health", workspace)
    try:
        if not 0 < args.timeout <= 30 or not 0 < args.postgres_port <= 65535:
            raise ValueError("Timeout must be in (0,30] seconds and port in 1..65535.")
        output = common.validate_output_path(workspace, args.output_path)
        # Validate all targets before making even a local request.
        local_url(args.backend_url)
        local_url(args.frontend_url)
        if args.postgres_host not in LOCAL_HOSTS:
            raise ValueError("Database health requests are restricted to localhost.")
        inspect(args, report)
        code = common.finalize(report)
        common.emit_report(report, output, args.json)
        return code
    except (OSError, ValueError, TypeError) as failure:
        return common.fail_report(report, failure, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
