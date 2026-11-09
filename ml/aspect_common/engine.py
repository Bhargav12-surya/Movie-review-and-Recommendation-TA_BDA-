"""Shared local supervised trainer for explicit aspects and multi-label themes.

Only explicit CLI execution reaches fitting. Preflight does not load a model.
Model/data/run approvals, frozen inputs, held-out selection and fresh artifacts
remain mandatory. No remote model resolution or heuristic predictions.
"""
from contextlib import nullcontext
from importlib import import_module, metadata
import math
from pathlib import Path
import time
from ml.common.artifacts import create_run, read_json, safe_path, sha256, write_json
from ml.common.calibration import fit_temperature
from ml.common.checkpointing import seed_everything, save_checkpoint, load_checkpoint
from ml.common.gates import training_preflight, reserve_final_test
from ml.common.hardware import guard_resources, resources, verify_device
from ml.common.model_source import verify_local_model, dependency_blockers
from ml.common.transformer_engine import _settings

COMPONENTS = {"aspect_extraction", "aspect_sentiment", "themes"}


def load_bundle(config):
    module = import_module("ml.themes.data" if config["task"] == "themes" else "ml.aspect_common.data")
    return module.load_experiment(config)


def adapter(component):
    if component not in COMPONENTS:
        raise ValueError("Unknown supervised component.")
    return import_module("ml." + component + ".task")


def preflight(config, component):
    blockers, bundle = [], None
    if component != config["task"] or component not in COMPONENTS:
        blockers.append("Component and explicit task differ.")
    try:
        bundle = load_bundle(config)
        report = training_preflight(config, bundle, component)
        blockers.extend(report["blockers"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        blockers.append("Validated annotation manifests are unavailable: " + type(error).__name__)
    try:
        _settings(config)
    except (ValueError, TypeError, KeyError):
        blockers.append("Bounded training settings are invalid.")
    _, model_blockers = verify_local_model(config)
    blockers.extend(model_blockers + dependency_blockers())
    try:
        permission_hash = sha256(safe_path(config["model"]["permission_path"], config["_workspace"]))
        approval = read_json(safe_path(config["approval_path"], config["_workspace"]))
        if approval.get("model_permission_sha256") != permission_hash:
            blockers.append("Run approval does not bind the reviewed model source.")
    except (OSError, ValueError, KeyError, TypeError):
        permission_hash = None
        blockers.append("Run/model permission binding is missing.")
    try:
        review = read_json(safe_path(config.get("dataset_review_path"), config["_workspace"]))
        if any(review.get(key) is not True for key in ("eda_reviewed", "duplicate_leakage_reviewed", "baseline_reviewed")):
            raise ValueError()
        if not bundle or review.get("manifest_hashes") != bundle.manifest_hashes or not review.get("reviewed_by"):
            raise ValueError()
        baseline = read_json(safe_path(review["baseline_report_path"], config["_workspace"]))
        if baseline.get("task") != component or baseline.get("manifest_hashes") != bundle.manifest_hashes:
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        blockers.append("EDA/leakage/baseline review with matching real report is required.")
    return {"ready": not blockers, "component": component, "blockers": blockers,
        "data": bundle.summary() if bundle else None, "config_sha256": sha256(config["_config_path"]),
        "model_permission_sha256": permission_hash, "training_started": False, "automatic_downloads": False}


def _loader(rows, tokenizer, task, batch_size, seed, shuffle):
    import torch
    from torch.utils.data import DataLoader
    generator = torch.Generator().manual_seed(seed)
    order = torch.randperm(len(rows), generator=generator).tolist() if shuffle else list(range(len(rows)))
    return DataLoader(rows, sampler=order, batch_size=batch_size, num_workers=0,
        collate_fn=lambda batch: task.collate(batch, tokenizer), generator=torch.Generator().manual_seed(seed))


def _contract(config, bundle):
    root = config["_workspace"]
    permission = safe_path(config["model"]["permission_path"], root)
    reviewed = read_json(permission)
    review_path = safe_path(config["dataset_review_path"], root)
    review = read_json(review_path)
    source_files = [path for name in (config["task"], "aspect_common", "common")
                    for path in (root / "ml" / name).glob("*.py")]
    return {"manifest_hashes": bundle.manifest_hashes, "labels": bundle.labels,
        "taxonomy": config.get("taxonomy"), "language_scope": config["language_scope"],
        "tokenization": config.get("tokenization", {}), "conditioning": config.get("conditioning", {}),
        "model_permission_sha256": sha256(permission), "base_files_sha256": reviewed["files_sha256"],
        "dataset_review_sha256": sha256(review_path),
        "baseline_sha256": sha256(safe_path(review["baseline_report_path"], root)),
        "code_sha256": {path.relative_to(root).as_posix(): sha256(path) for path in sorted(source_files)}}


def train(config, component, resume_checkpoint=None):
    if not preflight(config, component)["ready"]:
        raise ValueError("Training blocked; inspect component preflight.")
    bundle, task = load_bundle(config), adapter(component)
    settings = _settings(config)
    resource_before = guard_resources(config)
    import torch
    from datasets import Dataset
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForTokenClassification
    from transformers import get_linear_schedule_with_warmup
    device, dtype, hardware = verify_device(settings)
    seed_everything(settings["seed"])
    if resume_checkpoint:
        run = safe_path(config["output_dir"], config["_workspace"], output=True)
        if (run / "model_manifest.json").exists():
            raise ValueError("Completed runs are immutable.")
        if read_json(run / "experiment.json")["source_config_sha256"] != sha256(config["_config_path"]):
            raise ValueError("Resume config differs.")
    else:
        run = create_run(config, component)
    contract = _contract(config, bundle)
    if resume_checkpoint:
        if read_json(run / "input_contract.json") != contract:
            raise ValueError("Frozen source/data/model/tokenizer protocol changed.")
    else:
        write_json(run / "input_contract.json", contract)
    config["_input_contract_sha256"] = sha256(run / "input_contract.json")
    source, errors = verify_local_model(config)
    if errors:
        raise ValueError("Reviewed local model changed.")
    tokenizer = AutoTokenizer.from_pretrained(str(source), local_files_only=True, trust_remote_code=False, use_fast=True)
    if not tokenizer.is_fast:
        raise ValueError("An actual fast tokenizer is required for the original-offset protocol.")
    alignment = task.alignment_report(bundle.records["train"], tokenizer, config) if hasattr(task, "alignment_report") else None
    # Streaming generator writes Arrow cache under this owned run, not raw storage.
    def generate():
        yield from task.iter_rows(bundle.records["train"], tokenizer, config)
    rows = Dataset.from_generator(generate, cache_dir=str(run / "dataset_cache"))
    if not len(rows):
        raise ValueError("No eligible supervised rows.")
    model_class = AutoModelForTokenClassification if component == "aspect_extraction" else AutoModelForSequenceClassification
    arguments = {"num_labels": len(bundle.labels), "id2label": {value: key for key, value in bundle.labels.items()}, "label2id": bundle.labels}
    if component == "themes":
        arguments["problem_type"] = "multi_label_classification"
    model = model_class.from_pretrained(str(source), local_files_only=True, trust_remote_code=False,
                                       use_safetensors=True, **arguments)
    if verify_local_model(config)[1] or contract != _contract(config, bundle):
        raise ValueError("Training inputs changed during initialization.")
    if settings["gradient_checkpointing"]:
        model.gradient_checkpointing_enable()
        if hasattr(model.config, "use_cache"):
            model.config.use_cache = False
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=settings["learning_rate"], weight_decay=settings["weight_decay"])
    batches = math.ceil(len(rows) / settings["micro_batch_size"])
    accumulation = settings["gradient_accumulation_steps"]
    maximum_updates = min(settings["maximum_updates"], settings["epochs"] * math.ceil(batches / accumulation))
    scheduler = get_linear_schedule_with_warmup(optimizer, int(maximum_updates * settings["warmup_ratio"]), maximum_updates)
    scaler = torch.amp.GradScaler("cuda", enabled=(dtype == torch.float16 and device.type == "cuda"))
    progress = {"epoch": 0, "next_batch": 0, "updates": 0, "best_score": -1.0, "best_directory": None, "patience_used": 0, "history": []}
    if resume_checkpoint:
        checkpoint = safe_path(resume_checkpoint, config["_workspace"])
        if not checkpoint.is_relative_to(run / "checkpoints"):
            raise ValueError("Checkpoint is not owned by this run.")
        progress = load_checkpoint(checkpoint, model, optimizer, scheduler, scaler, bundle.manifest_hashes, config)
    if progress["next_batch"] % accumulation and progress["next_batch"] != batches:
        raise ValueError("Resume only at an optimizer boundary.")
    started, processed = time.monotonic(), 0
    optimizer.zero_grad(set_to_none=True)
    try:
        for epoch in range(progress["epoch"], settings["epochs"]):
            loader = _loader(rows, tokenizer, task, settings["micro_batch_size"], settings["seed"] + epoch, True)
            first = progress["next_batch"] if progress["epoch"] == epoch else 0
            model.train()
            for index, batch in enumerate(loader):
                if index < first:
                    continue
                if progress["updates"] >= maximum_updates:
                    break
                batch = {key: value.to(device) for key, value in batch.items()}
                window = min(accumulation, batches - index // accumulation * accumulation)
                with torch.autocast("cuda", dtype=dtype) if dtype is not None else nullcontext():
                    loss = model(**batch).loss / window
                if not torch.isfinite(loss).item():
                    raise RuntimeError("Nonfinite loss.")
                scaler.scale(loss).backward()
                processed += int(batch["input_ids"].shape[0])
                if (index + 1) % accumulation == 0 or index + 1 == batches:
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), settings["gradient_clip"])
                    old_scale = scaler.get_scale()
                    scaler.step(optimizer)
                    scaler.update()
                    stepped = scaler.get_scale() >= old_scale
                    if stepped:
                        scheduler.step()
                        progress["updates"] += 1
                    optimizer.zero_grad(set_to_none=True)
                    progress.update(epoch=epoch, next_batch=index + 1)
                    if stepped and progress["updates"] % settings["checkpoint_every_updates"] == 0:
                        save_checkpoint(run / "checkpoints" / ("checkpoint-%08d" % progress["updates"]),
                            model, optimizer, scheduler, scaler, progress, bundle.manifest_hashes, config)
            predictions = task.predict_examples(model, tokenizer, bundle.records["tuning"], config, device, dtype)
            metrics = task.score(bundle.records["tuning"], predictions, config)
            progress["history"].append({"epoch": epoch + 1, "updates": progress["updates"], "metrics": metrics})
            if metrics["primary_score"] > progress["best_score"]:
                best = run / ("best-epoch-%02d" % (epoch + 1))
                best.mkdir(exist_ok=False)
                model.save_pretrained(str(best), safe_serialization=True)
                tokenizer.save_pretrained(str(best))
                progress.update(best_score=metrics["primary_score"], best_directory=best.name, patience_used=0)
            else:
                progress["patience_used"] += 1
            progress.update(epoch=epoch + 1, next_batch=0)
            save_checkpoint(run / "checkpoints" / ("checkpoint-epoch-%02d" % (epoch + 1)),
                model, optimizer, scheduler, scaler, progress, bundle.manifest_hashes, config)
            if progress["updates"] >= maximum_updates or progress["patience_used"] >= settings["patience"]:
                break
    except Exception as error:
        write_json(run / ("failure-%d.json" % time.time_ns()), {"error_type": type(error).__name__,
            "note": "Preserve owned checkpoints; no automatic retry,CPU fallback or cleanup."})
        raise
    if not progress["updates"]:
        raise RuntimeError("No optimizer update; do not claim fine-tuning.")
    del model, optimizer, scheduler, scaler
    if device.type == "cuda":
        torch.cuda.empty_cache()
    model = model_class.from_pretrained(str(run / progress["best_directory"]), local_files_only=True,
                                       trust_remote_code=False, use_safetensors=True).to(device)
    temperature, calibration = 1.0, {"status": "not_applied_uncalibrated_extraction"}
    if component == "aspect_sentiment":
        logits, targets = task.calibration_logits(model, tokenizer, bundle.records["calibration"], config, device, dtype)
        temperature = fit_temperature(logits, targets)
        calibration = {"method": "temperature_scaling", "fit_split": "calibration", "temperature": temperature}
    elif component == "themes":
        calibration = task.calibrate(model, tokenizer, bundle, config, device, dtype)
        config["_calibration"] = calibration
    final = run / "model"
    final.mkdir(exist_ok=False)
    model.save_pretrained(str(final), safe_serialization=True)
    tokenizer.save_pretrained(str(final))
    manifest = {"schema_version": 1, "component": component, "task": component, "trained": True,
        "labels": bundle.labels, "manifest_hashes": bundle.manifest_hashes, "input_contract_sha256": sha256(run / "input_contract.json"),
        "temperature": temperature, "calibration": calibration, "experimental": True,
        "files_sha256": {str(path.relative_to(run)): sha256(path) for path in final.iterdir() if path.is_file()}}
    write_json(run / "model_manifest.json", manifest)
    report = {"trained": True, "component": component, "task": component, "manifest_hashes": bundle.manifest_hashes,
        "tuning_history": progress["history"], "calibration": calibration, "alignment": alignment,
        "hardware": hardware, "resources_before": resource_before, "resources_after": resources(config["_workspace"]),
        "elapsed_seconds": time.monotonic() - started, "processed_training_rows_this_session": processed,
        "peak_vram_allocated_bytes": torch.cuda.max_memory_allocated() if device.type == "cuda" else None,
        "environment": {name: metadata.version(name) for name in ("torch", "transformers", "datasets", "numpy")},
        "test_evaluated": False, "model_manifest_sha256": sha256(run / "model_manifest.json")}
    write_json(run / "training_report.json", report)
    return report


def load_trained(config, run_directory, device_name="cpu"):
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForTokenClassification
    run = safe_path(run_directory, config["_workspace"], output=True)
    manifest = read_json(run / "model_manifest.json")
    if manifest.get("trained") is not True or manifest.get("task") != config["task"] or manifest.get("labels") != config["labels"]:
        raise ValueError("Trained component/class contract mismatch.")
    if sha256(run / "input_contract.json") != manifest["input_contract_sha256"]:
        raise ValueError("Frozen input contract changed.")
    contract = read_json(run / "input_contract.json")
    for key in ("tokenization", "conditioning", "taxonomy", "language_scope"):
        expected = config.get(key, {} if key in {"tokenization", "conditioning"} else None)
        if expected != contract.get(key):
            raise ValueError("Inference preprocessing differs from the trained artifact: " + key)
    files = {str(path.relative_to(run)) for path in (run / "model").iterdir() if path.is_file()}
    if not files or files != set(manifest["files_sha256"]):
        raise ValueError("Trained files differ from the recorded set.")
    for name, checksum in manifest["files_sha256"].items():
        path = (run / name).resolve()
        if not path.is_relative_to(run / "model") or sha256(path) != checksum:
            raise ValueError("Trained model/tokenizer hash failed.")
    if device_name not in {"cpu", "cuda", "auto"}:
        raise ValueError("Explicit cpu,cuda or auto inference device required.")
    device = torch.device("cuda" if device_name == "auto" and torch.cuda.is_available() else "cpu" if device_name == "auto" else device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA inference unavailable; explicitly select cpu.")
    cls = AutoModelForTokenClassification if config["task"] == "aspect_extraction" else AutoModelForSequenceClassification
    model = cls.from_pretrained(str(run / "model"), local_files_only=True, trust_remote_code=False, use_safetensors=True).to(device)
    if model.config.label2id != config["labels"]:
        raise ValueError("Model class ordering differs.")
    tokenizer = AutoTokenizer.from_pretrained(str(run / "model"), local_files_only=True, trust_remote_code=False, use_fast=True)
    config["_calibration"] = manifest["calibration"]
    return run, manifest, model, tokenizer, device


def evaluate(config, component, run_directory, split="tuning", final_test=False, device_name="cpu"):
    if split not in {"tuning", "calibration", "test"}:
        raise ValueError("Evaluation excludes train.")
    bundle = load_bundle(config)
    run, manifest, model, tokenizer, device = load_trained(config, run_directory, device_name)
    if manifest["manifest_hashes"] != bundle.manifest_hashes:
        raise ValueError("Frozen experiment data differs.")
    if split == "test":
        selection = read_json(run / "selection.json")
        if any(selection.get(key) is not True for key in ("model_frozen", "selected_for_final_test")) or not selection.get("reviewed_by") or (
            selection.get("model_manifest_sha256") != sha256(run / "model_manifest.json") or selection.get("manifest_hashes") != bundle.manifest_hashes):
            raise ValueError("Human frozen model selection is required before final test.")
    reserve_final_test(run, bundle, split, final_test)
    task = adapter(component)
    started = time.monotonic()
    predicted = task.predict_examples(model, tokenizer, bundle.records[split], config, device, temperature=manifest["temperature"])
    metrics = task.score(bundle.records[split], predicted, config)
    result = {"component": component, "task": component, "split": split, "metrics": metrics,
        "manifest_hashes": bundle.manifest_hashes, "model_manifest_sha256": sha256(run / "model_manifest.json"),
        "elapsed_seconds": time.monotonic() - started, "review_count": len(predicted),
        "calibration_scope": "fit_split_diagnostic" if split == "calibration" else "held_out_from_calibration"}
    if component == "aspect_extraction":
        result["secondary_token_metrics"] = task.token_diagnostics(model, tokenizer, bundle.records[split], config, device)
    write_json(run / ("evaluation-" + split + "-%d.json" % time.time_ns()), result)
    return result
