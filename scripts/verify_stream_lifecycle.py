"""Verify an isolated synthetic stream's edit/delete/delayed-revision lifecycle.

Read-only without --execute. Execution publishes three new synthetic files and
resumes the existing Spark checkpoint after each. Retain partial failures.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import re
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_review_events import FIELDS, validate_event


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def inspect(demo):
    import pyarrow.parquet as pq
    batches = sorted(p for p in (demo / "output/committed").iterdir() if p.is_dir())
    if not batches or any(not re.fullmatch(r"batch-[0-9]{20}", p.name) for p in batches):
        raise ValueError("Missing or unexpected committed batches.")
    if [int(p.name[6:]) for p in batches] != list(range(len(batches))):
        raise ValueError("Noncontiguous checkpoint batches.")
    latest = batches[-1]
    if not (latest / "commit.properties").is_file():
        raise ValueError("Missing commit marker.")
    counts = {}
    for name in ("ledger", "current_reviews", "active_reviews", "movie_analysis_inputs", "quarantined_history", "rejected_input"):
        folder = latest / name
        if not folder.is_dir():
            raise ValueError("Missing table: " + name)
        counts[name] = sum(pq.ParquetFile(p).metadata.num_rows for p in folder.glob("*.parquet"))
    if counts["current_reviews"] != 1 or counts["ledger"] > 10:
        raise ValueError("Only the isolated one-review synthetic smoke fixture is supported.")
    rows = []
    for p in (latest / "current_reviews").glob("*.parquet"):
        rows.extend(pq.ParquetFile(p).read(columns=sorted(FIELDS)).to_pylist())
    return dict(batch_count=len(batches), current=rows[0], counts=counts)


def verify(state, event, ledger, active):
    expected = dict(ledger=ledger, current_reviews=1, active_reviews=active,
                    movie_analysis_inputs=0, quarantined_history=0, rejected_input=0)
    if state["batch_count"] != ledger or state["current"] != event or state["counts"] != expected:
        raise ValueError("State verification failed: " + json.dumps(state))


def run(args, log, root):
    with log.open("x", encoding="utf-8") as f:
        result = subprocess.run(args, cwd=root, stdout=f, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError("Command failed; inspect " + str(log))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-root", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    given = Path(args.demo_root)
    demo = (given if given.is_absolute() else root / given).resolve()
    evidence, steps = None, []
    try:
        if demo.parent != root / "artifacts" or not re.fullmatch(r"stream-check-[0-9a-f]{32}", demo.name):
            raise ValueError("Select an existing artifacts/stream-check-<32 hex digits> fixture.")
        for folder in ("events", "output", "checkpoint"):
            if not (demo / folder).is_dir():
                raise ValueError("Retain original events, output, and checkpoint together.")
        source = demo / "source.jsonl"
        if source.stat().st_size > 65536:
            raise ValueError("Oversized source fixture.")
        source_hash = sha(source)
        base = json.loads(source.read_text(encoding="utf-8"))
        validate_event(base, allow_synthetic=True)
        if (base["is_synthetic"] is not True or base["review_revision"] != 1 or
                base["operation"] != "upsert" or not base["consent_eligible"] or not base["moderation_eligible"]):
            raise ValueError("Requires the original eligible synthetic revision-1 fixture.")
        initial = inspect(demo)
        verify(initial, base, 1, 1)
        jar = root / "artifacts/scala-build/manual-final-002/movieintel-spark_2.13-0.1.0.jar"
        if not jar.is_file():
            raise ValueError("Required compiled JAR is absent.")
        print(json.dumps(dict(ready=True, synthetic_fixture=True, execution_requested=args.execute)), flush=True)
        if not args.execute:
            return 0
        evidence = demo / ("lifecycle-" + uuid.uuid4().hex)
        evidence.mkdir(exist_ok=False)
        write(evidence / "initial.json", dict(snapshot=initial, source_sha256=source_hash,
              helper_sha256=sha(Path(__file__)), jar_sha256=sha(jar)))
        edit = dict(base, event_id="synthetic-edit-" + uuid.uuid4().hex, review_revision=2,
                    event_time=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    positive_probability=0.2, neutral_probability=0.2, negative_probability=0.6)
        deletion = dict(edit, event_id="synthetic-delete-" + uuid.uuid4().hex, review_revision=3,
                        operation="delete", positive_probability=None, neutral_probability=None,
                        negative_probability=None, model_version=None, consent_eligible=False, moderation_eligible=False)
        # Preserve every semantic field, including event_time; avoid creating a revision conflict.
        delayed = dict(edit, event_id="synthetic-delayed-" + uuid.uuid4().hex)
        scenarios = [("edit", edit, edit, 1), ("delete", deletion, deletion, 0), ("delayed", delayed, deletion, 0)]
        for i, (name, event, expected, active) in enumerate(scenarios, start=2):
            validate_event(event, allow_synthetic=True)
            event_path = evidence / (name + ".jsonl")
            with event_path.open("x", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(event, allow_nan=False) + "\n")
            print("Running " + name + " check...", flush=True)
            run([sys.executable, "-I", "-B", str(root / "scripts/publish_review_events.py"),
                 "--input", str(event_path), "--publish-to", str(demo / "events"), "--allow-synthetic-events"],
                evidence / (name + "-publish.log"), root)
            run([sys.executable, "-I", "-B", str(root / "scripts/spark_job_launcher.py"),
                 "--workspace", str(root), "--job", "stream", "--spark-home", r"C:\spark\spark-4.3.0-bin-hadoop3",
                 "--jar", str(jar), "--driver-memory", "1g", "--master", "local[2]",
                 "--shuffle-partitions", "8", "--input-partitions", "4",
                 "--event-input", str(demo / "events"), "--output", str(demo / "output"),
                 "--checkpoint", str(demo / "checkpoint"), "--watermark", "24 hours",
                 "--max-files-per-trigger", "5", "--resume", "--allow-synthetic-events", "--json"],
                evidence / (name + "-spark.log"), root)
            state = inspect(demo)
            verify(state, expected, i, active)
            step = dict(step=name, passed=True, snapshot=state)
            write(evidence / (name + "-verification.json"), step)
            steps.append(step)
            print("PASS: " + name, flush=True)
        if sha(source) != source_hash:
            raise ValueError("Original fixture source changed.")
        report = dict(passed=True, synthetic_fixture=True, steps=steps, original_source_unchanged=True,
                      audience_evidence_rows=0, report_directory=str(evidence),
                      limitations=["Does not test conflicts, malformed data, concurrent writers, or interrupted commits.",
                                   "Delayed revision is not a test of a 24-hour watermark policy."])
        write(evidence / "report.json", report)
        print(json.dumps(report, indent=2))
        return 0
    except Exception as error:
        report = dict(passed=False, error_type=type(error).__name__, detail=str(error),
                      completed_steps=[s["step"] for s in steps], report_directory=str(evidence) if evidence else None,
                      note="Retain output/checkpoint. Do not republish or retry blindly after partial execution.")
        if evidence is not None:
            write(evidence / "failure.json", report)
        print(json.dumps(report, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
