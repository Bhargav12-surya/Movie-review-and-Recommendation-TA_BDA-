"""Manual synthetic streaming duplicate/conflict/malformed-input acceptance.

Default is read-only. --execute creates a new isolated artifact tree and runs
sequential local Spark jobs. It never edits previous runs, raw data, or models.
"""
from datetime import datetime, timezone
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import sys
import uuid
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_stream_lifecycle import run, sha, write
from publish_review_events import validate_event

TABLES = ("ledger", "current_reviews", "active_reviews", "movie_analysis_inputs",
          "quarantined_history", "rejected_input")


def read_state(demo):
    import pyarrow.parquet as pq
    batches = sorted(p for p in (demo / "output/committed").iterdir() if p.is_dir())
    if not batches or [p.name for p in batches] != ["batch-%020d" % i for i in range(len(batches))]:
        raise ValueError("Missing or unexpected committed batch sequence.")
    latest = batches[-1]
    if not (latest / "commit.properties").is_file():
        raise ValueError("Missing commit marker.")
    counts = {}
    details = {}
    for name in TABLES:
        folder = latest / name
        if not folder.is_dir():
            raise ValueError("Missing table: " + name)
        files = list(folder.glob("*.parquet"))
        counts[name] = sum(pq.ParquetFile(p).metadata.num_rows for p in files)
        if counts[name] > 20:
            raise ValueError("Unexpectedly large synthetic fixture.")
        if name in ("current_reviews", "active_reviews", "rejected_input", "quarantined_history"):
            wanted = ("event_id", "review_id", "is_synthetic", "rejection_reason")
            rows = []
            for path in files:
                pf = pq.ParquetFile(path)
                rows.extend(pf.read(columns=[c for c in wanted if c in pf.schema_arrow.names]).to_pylist())
            details[name] = rows
    return {"batch_count": len(batches), "counts": counts, "details": details}


def verify(state, batches, ledger, current, quarantined, rejected=0):
    expected = dict(ledger=ledger, current_reviews=current, active_reviews=current,
                    movie_analysis_inputs=0, quarantined_history=quarantined, rejected_input=rejected)
    if state["batch_count"] != batches or state["counts"] != expected:
        raise ValueError("Snapshot count assertion failed: " + json.dumps(state))
    rows = state["details"]["current_reviews"] + state["details"]["active_reviews"] + state["details"]["quarantined_history"]
    if any(row["is_synthetic"] is not True for row in rows):
        raise ValueError("Unexpected non-synthetic accepted fixture.")


def fingerprint(demo):
    return {str(p.relative_to(demo)): sha(p) for p in (demo / "output/committed").rglob("*") if p.is_file()}


def base_event():
    return dict(event_id="synthetic-edge-event-1", review_id="synthetic-edge-review-1",
                review_revision=1, movie_id="synthetic-edge-movie-1", operation="upsert",
                event_time=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                positive_probability=0.7, neutral_probability=0.2, negative_probability=0.1,
                model_version="synthetic-test-only", canonical_movie_validated=True,
                consent_eligible=True, moderation_eligible=True, is_synthetic=True)


def scenarios(base):
    conflict = dict(base, positive_probability=0.1, negative_probability=0.7)
    revision_a = dict(base, event_id="synthetic-revision-a", review_id="synthetic-edge-review-2")
    revision_b = dict(revision_a, event_id="synthetic-revision-b", positive_probability=0.1, negative_probability=0.7)
    identity_a = dict(base, event_id="synthetic-identity-a", review_id="synthetic-edge-review-3")
    identity_b = dict(identity_a, event_id="synthetic-identity-b", review_revision=2, movie_id="synthetic-other-movie")
    return [("initial", [base], 1, 1, 0, None),
            ("duplicate", [dict(base)], 1, 1, 0, None),
            ("event-conflict", [conflict], 2, 0, 2, "conflicting_event_id"),
            ("revision-conflict", [revision_a, revision_b], 4, 0, 4, "conflicting_review_revision"),
            ("identity-conflict", [identity_a, identity_b], 6, 0, 6, "changed_review_identity")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    scripts = root / "scripts"
    jar = root / "artifacts/scala-build/manual-final-002/movieintel-spark_2.13-0.1.0.jar"
    demo, steps = None, []
    try:
        if not jar.is_file() or importlib.util.find_spec("pyarrow") is None:
            raise ValueError("Existing compiled JAR and manually installed PyArrow are required.")
        for _, events, *_ in scenarios(base_event()):
            for event in events:
                validate_event(event, allow_synthetic=True)
        print(json.dumps({"ready": True, "synthetic_fixture": True,
                          "execution_requested": args.execute,
                          "next": "Use --execute to create a fresh isolated test run."}), flush=True)
        if not args.execute:
            return 0
        demo = root / "artifacts" / ("stream-edge-" + uuid.uuid4().hex)
        demo.mkdir(exist_ok=False)
        (demo / "sources").mkdir()
        (demo / "events").mkdir()
        write(demo / "inputs.json", {"synthetic_fixture": True, "helper_sha256": sha(Path(__file__)),
              "shared_helper_sha256": sha(scripts / "verify_stream_lifecycle.py"), "jar_sha256": sha(jar)})
        common = [sys.executable, "-I", "-B", str(scripts / "spark_job_launcher.py"),
                  "--workspace", str(root), "--job", "stream", "--spark-home", r"C:\spark\spark-4.3.0-bin-hadoop3",
                  "--jar", str(jar), "--driver-memory", "1g", "--master", "local[2]",
                  "--shuffle-partitions", "8", "--input-partitions", "4", "--watermark", "24 hours",
                  "--max-files-per-trigger", "5", "--event-input", str(demo / "events"),
                  "--output", str(demo / "output"), "--checkpoint", str(demo / "checkpoint"),
                  "--allow-synthetic-events", "--json"]
        base = base_event()
        for index, (name, events, ledger, current, quarantined, reason) in enumerate(scenarios(base), start=1):
            print("Running " + name + "...", flush=True)
            source = demo / "sources" / (name + ".jsonl")
            with source.open("x", encoding="utf-8", newline="\n") as f:
                for event in events:
                    f.write(json.dumps(event, allow_nan=False) + "\n")
            source_hash = sha(source)
            run([sys.executable, "-I", "-B", str(scripts / "publish_review_events.py"),
                 "--input", str(source), "--publish-to", str(demo / "events"), "--allow-synthetic-events"],
                demo / (name + "-publish.log"), root)
            run(common + (["--resume"] if index > 1 else []), demo / (name + "-spark.log"), root)
            state = read_state(demo)
            verify(state, index, ledger, current, quarantined)
            if reason and not any(reason in (r.get("rejection_reason") or "") for r in state["details"]["quarantined_history"]):
                raise ValueError("Expected quarantine reason missing: " + reason)
            if sha(source) != source_hash:
                raise ValueError("Publisher changed its input fixture.")
            step = {"step": name, "passed": True, "snapshot": state}
            steps.append(step)
            write(demo / (name + "-verification.json"), step)
            print("PASS: " + name, flush=True)
        # Intentionally invalid synthetic fixture: exercise publisher and Spark rejection independently.
        invalid = dict(base, event_id="synthetic-invalid-probabilities", positive_probability=0.9)
        bad_text = json.dumps(invalid) + '\n{"is_synthetic":true,"event_id":\n'
        bad_source = demo / "sources/malformed.jsonl"
        with bad_source.open("x", encoding="utf-8", newline="\n") as f:
            f.write(bad_text)
        rejected_destination = demo / "publisher-rejected"
        with (demo / "malformed-publisher.log").open("x", encoding="utf-8") as f:
            rejected = subprocess.run([sys.executable, "-I", "-B", str(scripts / "publish_review_events.py"),
                "--input", str(bad_source), "--publish-to", str(rejected_destination), "--allow-synthetic-events"],
                cwd=root, stdout=f, stderr=subprocess.STDOUT, check=False)
        if rejected.returncode != 2 or list(rejected_destination.glob("events-*.jsonl")):
            raise ValueError("Publisher did not reject invalid input without publication.")
        # Bypass publisher only for this isolated negative test of downstream ingestion.
        partial = demo / "events" / (".invalid-" + uuid.uuid4().hex)
        with partial.open("x", encoding="utf-8", newline="\n") as f:
            f.write(bad_text)
        os.rename(partial, demo / "events" / ("invalid-test-" + uuid.uuid4().hex + ".jsonl"))
        run(common + ["--resume"], demo / "malformed-spark.log", root)
        state = read_state(demo)
        verify(state, 6, 6, 0, 6, rejected=2)
        reasons = {r["rejection_reason"] for r in state["details"]["rejected_input"]}
        if not {"invalid_sentiment_probabilities", "malformed_json_or_field_type"}.issubset(reasons):
            raise ValueError("Expected probability and malformed-JSON rejection reasons missing.")
        steps.append({"step": "malformed-input", "passed": True, "snapshot": state})
        print("PASS: malformed-input", flush=True)
        before = fingerprint(demo)
        run(common + ["--resume"], demo / "no-new-input-spark.log", root)
        if fingerprint(demo) != before:
            raise ValueError("Restart without new input changed committed snapshots.")
        verify(read_state(demo), 6, 6, 0, 6, rejected=2)
        steps.append({"step": "unchanged-restart", "passed": True})
        print("PASS: unchanged-restart", flush=True)
        report = {"passed": True, "synthetic_fixture": True, "steps": steps, "report_directory": str(demo),
                  "audience_evidence_rows": 0,
                  "limitations": ["Concurrent writers, interrupted commits, and ScalaTest execution remain unverified.",
                                  "Synthetic fixture validation does not establish real-review eligibility or end-to-end exactly-once delivery."]}
        write(demo / "report.json", report)
        print(json.dumps(report, indent=2))
        return 0
    except Exception as error:
        result = {"passed": False, "error_type": type(error).__name__, "detail": str(error),
                  "completed_steps": [s["step"] for s in steps],
                  "report_directory": str(demo) if demo else None,
                  "note": "Retain artifacts and logs. Do not modify or delete the output/checkpoint to retry."}
        if demo is not None:
            write(demo / "failure.json", result)
        print(json.dumps(result, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
