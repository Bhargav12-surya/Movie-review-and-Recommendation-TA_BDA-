"""Continue only the two remaining checks after the known subprocess NameError.

Default is read-only. --execute resumes an existing isolated synthetic stream.
Original failure reports and logs stay unchanged; new evidence uses a fresh folder.
"""
import argparse
import json
from pathlib import Path
import re
import os
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_stream_edge_cases import read_state, verify, fingerprint
from verify_stream_lifecycle import run, sha, write
from publish_review_events import validate_event

EXPECTED = ["initial", "duplicate", "event-conflict", "revision-conflict", "identity-conflict"]


def rejection_check(source, destination, log, root):
    with log.open("x", encoding="utf-8") as f:
        result = subprocess.run([sys.executable, "-I", "-B", str(root / "scripts/publish_review_events.py"),
            "--input", str(source), "--publish-to", str(destination), "--allow-synthetic-events"],
            cwd=root, stdout=f, stderr=subprocess.STDOUT, check=False)
    if result.returncode != 2 or list(destination.glob("events-*.jsonl")):
        raise ValueError("Publisher did not reject invalid input without publication.")
    report = json.loads(log.read_text(encoding="utf-8"))
    if report.get("status") != "rejected" or report.get("reason") != "invalid_event_at_line_1":
        raise ValueError("Publisher failed for an unexpected reason; inspect " + str(log))


def prepare(root, given):
    demo = (given if given.is_absolute() else root / given).resolve()
    if demo.parent != root / "artifacts" or not re.fullmatch(r"stream-edge-[0-9a-f]{32}", demo.name):
        raise ValueError("Select the existing isolated stream-edge fixture.")
    failure = json.loads((demo / "failure.json").read_text(encoding="utf-8"))
    if (failure.get("error_type") != "NameError" or failure.get("detail") != "name 'subprocess' is not defined"
            or failure.get("completed_steps") != EXPECTED):
        raise ValueError("Continuation only supports the recorded missing-subprocess failure after five passes.")
    for name in EXPECTED:
        result = json.loads((demo / (name + "-verification.json")).read_text(encoding="utf-8"))
        if result.get("passed") is not True or result.get("step") != name:
            raise ValueError("Missing passed verification for " + name)
    if not (demo / "checkpoint/metadata").is_file() or not (demo / "checkpoint/offsets").is_dir():
        raise ValueError("Original checkpoint metadata/offsets are missing.")
    if any(not (demo / "checkpoint/commits" / str(i)).is_file() for i in range(5)):
        raise ValueError("The five completed checkpoint commits are missing.")
    verify(read_state(demo), 5, 6, 0, 6)
    if len(list((demo / "events").glob("*.jsonl"))) != 5:
        raise ValueError("Unexpected newly published input; do not republish or retry blindly.")
    base = json.loads((demo / "sources/initial.jsonl").read_text(encoding="utf-8"))
    validate_event(base, allow_synthetic=True)
    if base["is_synthetic"] is not True:
        raise ValueError("Only a synthetic fixture may be continued.")
    expected = dict(base, event_id="synthetic-invalid-probabilities", positive_probability=0.9)
    text = (demo / "sources/malformed.jsonl").read_text(encoding="utf-8").splitlines()
    if len(text) != 2 or json.loads(text[0]) != expected or text[1] != '{"is_synthetic":true,"event_id":':
        raise ValueError("Retained invalid test fixture differs from the expected input.")
    jar = root / "artifacts/scala-build/manual-final-002/movieintel-spark_2.13-0.1.0.jar"
    inputs = json.loads((demo / "inputs.json").read_text(encoding="utf-8"))
    if inputs.get("synthetic_fixture") is not True or inputs.get("jar_sha256") != sha(jar):
        raise ValueError("Project JAR differs from the initial test run.")
    return demo, jar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-root", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    evidence, completed = None, []
    try:
        demo, jar = prepare(root, Path(args.demo_root))
        print(json.dumps({"ready": True, "verified_completed_steps": EXPECTED,
                          "remaining_steps": ["malformed-input", "unchanged-restart"],
                          "execution_requested": args.execute}), flush=True)
        if not args.execute:
            return 0
        evidence = demo / ("continuation-" + uuid.uuid4().hex)
        evidence.mkdir(exist_ok=False)
        source = demo / "sources/malformed.jsonl"
        old_failure_hash, source_hash = sha(demo / "failure.json"), sha(source)
        write(evidence / "inputs.json", {"original_failure_sha256": old_failure_hash,
              "malformed_source_sha256": source_hash, "jar_sha256": sha(jar),
              "helper_sha256": sha(Path(__file__)), "synthetic_fixture": True})
        print("Running malformed-input check...", flush=True)
        rejection_check(source, evidence / "publisher-rejected", evidence / "malformed-publisher.log", root)
        # Intentional bypass only to test rejection by downstream ingestion inside this synthetic run.
        partial = demo / "events" / (".invalid-" + uuid.uuid4().hex)
        with partial.open("xb") as f:
            f.write(source.read_bytes())
            f.flush()
            os.fsync(f.fileno())
        os.rename(partial, demo / "events" / ("invalid-test-" + uuid.uuid4().hex + ".jsonl"))
        common = [sys.executable, "-I", "-B", str(root / "scripts/spark_job_launcher.py"),
                  "--workspace", str(root), "--job", "stream", "--spark-home", r"C:\spark\spark-4.3.0-bin-hadoop3",
                  "--jar", str(jar), "--driver-memory", "1g", "--master", "local[2]",
                  "--shuffle-partitions", "8", "--input-partitions", "4", "--watermark", "24 hours",
                  "--max-files-per-trigger", "5", "--event-input", str(demo / "events"),
                  "--output", str(demo / "output"), "--checkpoint", str(demo / "checkpoint"),
                  "--resume", "--allow-synthetic-events", "--json"]
        run(common, evidence / "malformed-spark.log", root)
        state = read_state(demo)
        verify(state, 6, 6, 0, 6, rejected=2)
        reasons = {r["rejection_reason"] for r in state["details"]["rejected_input"]}
        if not {"invalid_sentiment_probabilities", "malformed_json_or_field_type"}.issubset(reasons):
            raise ValueError("Expected invalid-probability and malformed-JSON rejection reasons missing.")
        completed.append("malformed-input")
        write(evidence / "malformed-verification.json", state)
        print("PASS: malformed-input", flush=True)
        before = fingerprint(demo)
        print("Running unchanged-restart check...", flush=True)
        run(common, evidence / "unchanged-restart-spark.log", root)
        if fingerprint(demo) != before:
            raise ValueError("Committed snapshots changed on restart without new input.")
        verify(read_state(demo), 6, 6, 0, 6, rejected=2)
        completed.append("unchanged-restart")
        if sha(demo / "failure.json") != old_failure_hash or sha(source) != source_hash:
            raise ValueError("Original failure evidence or invalid fixture changed.")
        print("PASS: unchanged-restart", flush=True)
        report = {"passed": True, "previously_verified_steps": EXPECTED, "completed_steps": completed,
                  "synthetic_fixture": True, "audience_evidence_rows": 0, "final_snapshot": read_state(demo),
                  "original_failure_preserved": True, "report_directory": str(evidence),
                  "limitations": ["Concurrent writers, interrupted commits, and ScalaTest execution remain unverified."]}
        write(evidence / "report.json", report)
        print(json.dumps(report, indent=2))
        return 0
    except Exception as error:
        report = {"passed": False, "error_type": type(error).__name__, "detail": str(error),
                  "completed_steps": completed, "report_directory": str(evidence) if evidence else None,
                  "note": "Retain all artifacts; do not republish inputs or delete/reset the checkpoint."}
        if evidence is not None:
            write(evidence / "failure.json", report)
        print(json.dumps(report, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
