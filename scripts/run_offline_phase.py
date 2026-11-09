"""Explicit later entry points for Phases5-7; default is read-only preflight.

No dataset/model downloader, dependency installer, pickle loader or service.
Training requires the --execute flag AND matching owner approval records.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.common.artifacts import safe_path, read_json, write_json
from ml.common.records import load_config, permitted_rows, load_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", required=True, choices=("embeddings", "summarization", "topics", "review_risk", "scoring"))
    parser.add_argument("--config", required=True)
    parser.add_argument("--action", choices=("preflight", "train", "predict"), default="preflight")
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--movie-id")
    parser.add_argument("--policy-approval")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.action == "preflight":
            print(json.dumps({"status": "prepared_source_requires_user_inputs", "component": args.component,
                "model_path_supplied": bool(config.get("model", {}).get("local_path")),
                "manifests_supplied": all(config.get("data", {}).get("manifests", {}).values()) if config.get("data", {}).get("manifests") else False,
                "runtime_ready": False, "training_started": False}))
            return 2
        if not args.execute:
            raise ValueError("Explicit execution is required for data/model work.")
        if args.action == "train":
            bundle = load_bundle(config)
            if args.component == "topics":
                from ml.topics.train import train
            elif args.component == "review_risk":
                from ml.review_risk.train import train
            else:
                raise ValueError("This component uses pretrained inference or separate Transformer entry points.")
            result = {"run_directory": str(train(config, bundle))}
        else:
            root = config["_workspace"]
            input_path = safe_path(args.input, root)
            output = safe_path(args.output, root, output=True)
            output.mkdir(parents=True, exist_ok=False)
            if args.component == "scoring":
                from scoring.policy import load_policy
                from scoring.aggregate import aggregate
                from ml.common.data import _rows
                policy = load_policy(args.config, safe_path(args.policy_approval, root))
                result = aggregate(_rows(input_path), args.movie_id, policy)
            else:
                purpose = "evidence" if args.component == "summarization" else "moderation" if args.component == "review_risk" else "inference"
                rows = permitted_rows(input_path, purpose=purpose)
                if args.component == "summarization":
                    from dataset_tools.recordio import load_registry
                    registry = safe_path(config["data"]["canonical_registry_path"], root)
                    movie_ids, blockers = load_registry(registry)
                    if blockers or str(args.movie_id) not in movie_ids or any(str(row.get("movie_id")) not in movie_ids for row in rows):
                        raise ValueError("Summary inputs require approved actual canonical movie IDs.")
                if args.component == "embeddings":
                    from ml.embeddings.predict import encode
                    result = encode([row["text"] for row in rows], config)
                    import pyarrow as pa
                    import pyarrow.parquet as pq
                    table = pa.table({"record_id": [row["record_id"] for row in rows], "content_sha256": result["content_sha256"],
                                      "embedding": result.pop("vectors").tolist()})
                    pq.write_table(table, output / "vectors.parquet")
                elif args.component == "summarization":
                    from ml.summarization.predict import summarize
                    result = summarize(rows, args.movie_id, config)
                elif args.component == "topics":
                    from ml.topics.predict import predict
                    from ml.common.artifacts import sha256
                    run = safe_path(config["model"]["local_path"], root)
                    report = read_json(run / "training_report.json")
                    if sha256(run / "topic_model.json") != report.get("model_sha256"):
                        raise ValueError("Owned fitted topic model fingerprint differs.")
                    result = predict([row["text"] for row in rows], read_json(run / "topic_model.json", 32 * 1024**2))
                else:
                    from ml.review_risk.predict import predict, load_owned
                    query, history = rows[0], rows[1:]
                    model_path = config.get("model", {}).get("local_path")
                    state = load_owned(safe_path(model_path, root)) if model_path else None
                    result = predict(query["text"], [row["text"] for row in history], query.get("behaviour"), state)
            write_json(output / "result.json", result)
            result = {"status": "completed", "output_directory": str(output), "component": args.component}
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except Exception as error:
        print(json.dumps({"status": "blocked_or_failed", "error_type": type(error).__name__, "detail": "Supply legitimate reviewed local inputs; no automatic substitute/download."}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
