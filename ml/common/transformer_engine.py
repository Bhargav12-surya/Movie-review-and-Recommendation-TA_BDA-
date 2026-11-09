"""Local-only supervised Transformer training, calibration and inference.

Called only by explicit CLI actions. No remote model identifiers, downloads,
synthetic-label generation, test-set training or heuristic polarity overlays.
"""
from __future__ import annotations
from contextlib import nullcontext
import importlib.metadata
import math
from pathlib import Path
import platform
import subprocess
import sys
import time
from .artifacts import create_run, read_json, safe_path, sha256, write_json
from .calibration import fit_temperature, softmax
from .checkpointing import load_checkpoint, save_checkpoint, seed_everything
from .data import load_experiment
from .gates import require_training_approval, reserve_final_test, training_preflight
from .hardware import guard_resources, resources, verify_device
from .metrics import classification_metrics
from .model_source import dependency_blockers, verify_local_model


def preflight(config: dict, component: str) -> dict:
    report = training_preflight(config, component=component)
    try:
        _settings(config)
        _view_settings(config)
    except (OSError, ValueError, TypeError, KeyError):
        report["blockers"].append("Training/text-view configuration is invalid or unavailable.")
    _, blockers = verify_local_model(config)
    report["blockers"].extend(blockers + dependency_blockers())
    try:
        permission_hash = sha256(safe_path(config["model"]["permission_path"], config["_workspace"]))
        approval = read_json(safe_path(config["approval_path"], config["_workspace"]))
        if approval.get("model_permission_sha256") != permission_hash:
            report["blockers"].append("Run approval does not match the reviewed model permission record.")
        report["model_permission_sha256"] = permission_hash
    except (OSError, KeyError, ValueError, TypeError):
        report["blockers"].append("Run/model permission binding is incomplete.")
    reports = config.get("baseline_reports", [])
    algorithms = set()
    for name in reports:
        try:
            baseline = read_json(safe_path(name, config["_workspace"]))
            if baseline.get("task") != config["task"] or baseline.get("component") != "tfidf" or baseline.get("trained") is not True:
                raise ValueError()
            if not report["data"] or baseline.get("manifest_hashes") != report["data"]["manifest_hashes"]:
                raise ValueError()
            if not isinstance(baseline.get("tuning_metrics"), dict):
                raise ValueError()
            algorithms.add(baseline.get("estimator"))
        except (OSError, ValueError, TypeError):
            report["blockers"].append("A baseline report is missing, invalid or uses different task/splits.")
    if algorithms != {"logistic_regression", "linear_svm"}:
        report["blockers"].append("Run/review both Logistic Regression and Linear SVM baselines first.")
    report["ready"] = not report["blockers"]
    return report


def _settings(config: dict) -> dict:
    value = dict(config.get("training", {}))
    defaults = {"epochs": 2, "micro_batch_size": 4, "gradient_accumulation_steps": 8,
                "maximum_sequence_length": 128, "maximum_updates": 2000,
                "checkpoint_every_updates": 200, "patience": 2, "seed": 42,
                "learning_rate": 2e-5, "weight_decay": 0.01, "warmup_ratio": 0.1,
                "gradient_clip": 1.0, "gradient_checkpointing": False, "num_workers": 0}
    defaults.update(value)
    value = defaults
    bounds = {"epochs": (1, 10), "micro_batch_size": (1, 32), "gradient_accumulation_steps": (1, 128),
              "maximum_sequence_length": (16, 512), "maximum_updates": (1, 20000),
              "checkpoint_every_updates": (1, 20000), "patience": (1, 10)}
    for key, (minimum, maximum) in bounds.items():
        if type(value[key]) is not int or not minimum <= value[key] <= maximum:
            raise ValueError("Training setting outside the bounded range: " + key)
    if type(value["seed"]) is not int or not 0 <= value["seed"] <= 2**32 - 1:
        raise ValueError("An explicit bounded random seed is required.")
    if type(value["gradient_checkpointing"]) is not bool:
        raise ValueError("Gradient checkpointing must be a boolean.")
    if type(value["num_workers"]) is not int or value["num_workers"] != 0:
        raise ValueError("This reproducible Windows implementation starts with zero loader workers.")
    for key in ("learning_rate", "weight_decay", "warmup_ratio", "gradient_clip"):
        if isinstance(value[key], bool) or not isinstance(value[key], (float, int)) or not math.isfinite(value[key]) or value[key] < 0:
            raise ValueError("Invalid finite training setting: " + key)
    if value["learning_rate"] <= 0 or value["warmup_ratio"] > 1:
        raise ValueError("Learning rate/warmup settings are invalid.")
    return value


def _view_settings(config: dict) -> dict:
    settings = config.get("preprocessing", {})
    policy = settings.get("emoji_policy", "preserve")
    mapping_path = settings.get("slang_mapping_path")
    mapping = read_json(safe_path(mapping_path, config["_workspace"])) if mapping_path else {}
    if policy not in {"preserve", "remove_for_ablation"} or any(
        not isinstance(key, str) or not key or key != key.casefold() or
        not isinstance(value, str) or not value.strip() for key, value in mapping.items()):
        raise ValueError("Invalid reviewed text-view configuration.")
    return {"emoji_policy": policy, "slang_mapping": mapping}


def _model_text(text: str, view_settings: dict) -> str:
    from ml.informal_language.preprocess import feature_view
    return feature_view(text, view_settings["emoji_policy"], view_settings["slang_mapping"]).text


def _dataset(records, names: list[str], directory: Path, view_settings: dict):
    from datasets import ClassLabel, Dataset, Features, Value
    def generate(rows):
        for row in rows:
            yield {"text": _model_text(row.read_text(), view_settings), "label": row.label}
    return Dataset.from_generator(generate, gen_kwargs={"rows": records},
        features=Features({"text": Value("string"), "label": ClassLabel(names=names)}),
        cache_dir=str(directory))


class _Collator:
    def __init__(self, tokenizer, maximum: int):
        self.tokenizer, self.maximum = tokenizer, maximum

    def __call__(self, rows):
        import torch
        features = self.tokenizer([row["text"] for row in rows], truncation=True,
            max_length=self.maximum, padding=True, return_tensors="pt")
        if all("label" in row for row in rows):
            features["labels"] = torch.tensor([row["label"] for row in rows], dtype=torch.long)
        elif any("label" in row for row in rows):
            raise ValueError("A batch cannot mix labelled/unlabelled examples.")
        return features


def _loader(dataset, collator, batch_size: int, seed: int, shuffle: bool):
    import torch
    from torch.utils.data import DataLoader
    generator = torch.Generator().manual_seed(seed)
    order = torch.randperm(len(dataset), generator=generator).tolist() if shuffle else list(range(len(dataset)))
    # Dedicated RNG avoids consuming the restored model RNG when an iterator is recreated.
    return DataLoader(dataset, batch_size=batch_size, sampler=order, num_workers=0,
                      collate_fn=collator, generator=torch.Generator().manual_seed(seed), pin_memory=False)


def _logits(model, dataset, tokenizer, maximum: int, batch_size: int, device, dtype):
    import torch
    values, labels = [], []
    model.eval()
    with torch.inference_mode():
        for batch in _loader(dataset, _Collator(tokenizer, maximum), batch_size, 0, False):
            targets = batch.pop("labels", None)
            if targets is not None:
                labels.extend(targets.tolist())
            inputs = {key: tensor.to(device) for key, tensor in batch.items()}
            context = torch.autocast(device_type="cuda", dtype=dtype) if dtype is not None else nullcontext()
            with context:
                output = model(**inputs).logits
            values.extend(output.float().cpu().tolist())
    return values, labels


def train(config: dict, component: str, resume_checkpoint: str | None = None) -> dict:
    report = preflight(config, component)
    if not report["ready"]:
        raise ValueError("Training prerequisites/approval are incomplete; inspect preflight.")
    bundle = load_experiment(config)
    require_training_approval(config, bundle, component)
    settings = _settings(config)
    view_settings = _view_settings(config)
    resource_before = guard_resources(config)
    source, blockers = verify_local_model(config)
    if blockers:
        raise ValueError("Local pretrained model verification failed.")
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    device, dtype, hardware = verify_device(settings)
    seed_everything(settings["seed"])
    if resume_checkpoint:
        run = safe_path(config["output_dir"], config["_workspace"], output=True)
        if (run / "model_manifest.json").exists():
            raise ValueError("Completed runs are immutable; use a fresh approved experiment.")
        previous = read_json(run / "experiment.json")
        if previous.get("source_config_sha256") != sha256(config["_config_path"]):
            raise ValueError("Resume run configuration differs.")
    else:
        run = create_run(config, component)
    permission_path = safe_path(config["model"]["permission_path"], config["_workspace"])
    permission = read_json(permission_path)
    input_contract = {"model_permission_sha256": sha256(permission_path),
                      "base_files_sha256": permission["files_sha256"], "text_view": view_settings,
                      "manifest_hashes": bundle.manifest_hashes}
    if resume_checkpoint:
        if read_json(run / "input_contract.json") != input_contract:
            raise ValueError("Resume base/tokenizer/text-view inputs changed at their configured paths.")
    else:
        write_json(run / "input_contract.json", input_contract)
    config["_input_contract_sha256"] = sha256(run / "input_contract.json")
    # Verify raw text one review at a time, including on resume with an existing Arrow cache.
    for split in ("train", "tuning", "calibration"):
        for row in bundle.records[split]:
            row.read_text()
    datasets = {split: _dataset(bundle.records[split], bundle.label_names, run / "dataset_cache" / split, view_settings)
                for split in ("train", "tuning", "calibration")}
    tokenizer = AutoTokenizer.from_pretrained(str(source), local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(str(source), local_files_only=True,
        trust_remote_code=False, use_safetensors=True, num_labels=len(bundle.labels),
        id2label={index: name for name, index in bundle.labels.items()}, label2id=bundle.labels)
    _, source_changed = verify_local_model(config)
    if source_changed or sha256(permission_path) != input_contract["model_permission_sha256"]:
        raise ValueError("Base model/tokenizer inputs changed during initialization.")
    if settings["gradient_checkpointing"]:
        model.gradient_checkpointing_enable()
        if hasattr(model.config, "use_cache"):
            model.config.use_cache = False
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=settings["learning_rate"], weight_decay=settings["weight_decay"])
    batches = math.ceil(len(datasets["train"]) / settings["micro_batch_size"])
    updates_per_epoch = math.ceil(batches / settings["gradient_accumulation_steps"])
    total_updates = min(settings["maximum_updates"], settings["epochs"] * updates_per_epoch)
    scheduler = get_linear_schedule_with_warmup(optimizer,
        num_warmup_steps=int(total_updates * settings["warmup_ratio"]), num_training_steps=total_updates)
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda" and dtype == torch.float16))
    progress = {"epoch": 0, "next_batch": 0, "updates": 0, "best_macro_f1": -1.0,
                "patience_used": 0, "best_directory": None, "history": []}
    if resume_checkpoint:
        checkpoint = safe_path(resume_checkpoint, config["_workspace"])
        if not checkpoint.is_relative_to(run / "checkpoints"):
            raise ValueError("Resume checkpoint is not owned by the configured run.")
        progress = load_checkpoint(checkpoint, model, optimizer, scheduler, scaler, bundle.manifest_hashes, config)
    if progress["next_batch"] % settings["gradient_accumulation_steps"] and progress["next_batch"] != batches:
        raise ValueError("Checkpoint does not fall on an optimizer boundary.")
    started = time.monotonic()
    trained_examples = 0
    optimizer.zero_grad(set_to_none=True)
    try:
        for epoch in range(progress["epoch"], settings["epochs"]):
            loader = _loader(datasets["train"], _Collator(tokenizer, settings["maximum_sequence_length"]),
                             settings["micro_batch_size"], settings["seed"] + epoch, True)
            model.train()
            start_batch = progress["next_batch"] if epoch == progress["epoch"] else 0
            for index, batch in enumerate(loader):
                if index < start_batch:
                    continue
                if progress["updates"] >= total_updates:
                    break
                batch = {key: tensor.to(device) for key, tensor in batch.items()}
                window_start = (index // settings["gradient_accumulation_steps"]) * settings["gradient_accumulation_steps"]
                window_size = min(settings["gradient_accumulation_steps"], batches - window_start)
                context = torch.autocast(device_type="cuda", dtype=dtype) if dtype is not None else nullcontext()
                with context:
                    loss = model(**batch).loss / window_size
                if not torch.isfinite(loss).item():
                    raise RuntimeError("Nonfinite training loss; preserve run and diagnose.")
                scaler.scale(loss).backward()
                trained_examples += int(batch["labels"].shape[0])
                if (index + 1) % settings["gradient_accumulation_steps"] == 0 or index + 1 == batches:
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), settings["gradient_clip"])
                    before_scale = scaler.get_scale()
                    scaler.step(optimizer)
                    scaler.update()
                    stepped = scaler.get_scale() >= before_scale
                    if stepped:
                        scheduler.step()
                        progress["updates"] += 1
                    optimizer.zero_grad(set_to_none=True)
                    progress.update(epoch=epoch, next_batch=index + 1)
                    if stepped and progress["updates"] and progress["updates"] % settings["checkpoint_every_updates"] == 0:
                        save_checkpoint(run / "checkpoints" / ("checkpoint-%08d" % progress["updates"]),
                            model, optimizer, scheduler, scaler, progress, bundle.manifest_hashes, config)
            logits, targets = _logits(model, datasets["tuning"], tokenizer, settings["maximum_sequence_length"],
                                     settings["micro_batch_size"], device, dtype)
            tuning = classification_metrics(targets, softmax(logits), bundle.label_names)
            progress["history"].append({"epoch": epoch + 1, "updates": progress["updates"], "tuning_metrics": tuning})
            if tuning["macro_f1"] > progress["best_macro_f1"]:
                best = run / ("best-epoch-%02d" % (epoch + 1))
                best.mkdir(exist_ok=False)
                model.save_pretrained(str(best), safe_serialization=True)
                tokenizer.save_pretrained(str(best))
                progress.update(best_macro_f1=tuning["macro_f1"], best_directory=best.name, patience_used=0)
            else:
                progress["patience_used"] += 1
            progress.update(epoch=epoch + 1, next_batch=0)
            save_checkpoint(run / "checkpoints" / ("checkpoint-epoch-%02d" % (epoch + 1)),
                model, optimizer, scheduler, scaler, progress, bundle.manifest_hashes, config)
            if progress["patience_used"] >= settings["patience"] or progress["updates"] >= total_updates:
                break
    except Exception as error:
        write_json(run / ("failure-%d.json" % time.time_ns()), {"error_type": type(error).__name__,
                   "progress": {key: value for key, value in progress.items() if key != "history"},
                   "note": "No automatic OOM retry or CPU fallback; resume a reviewed owned checkpoint."})
        raise
    if progress["updates"] == 0:
        raise RuntimeError("No optimizer update completed; the model is not claimed to be fine-tuned.")
    best = (run / progress["best_directory"]).resolve()
    if not best.is_relative_to(run):
        raise ValueError("Best-model path escaped the run.")
    # Free optimizer/current model before loading the selected model, avoiding two large encoders.
    del model, optimizer, scheduler, scaler
    if device.type == "cuda":
        torch.cuda.empty_cache()
    model = AutoModelForSequenceClassification.from_pretrained(str(best), local_files_only=True,
        trust_remote_code=False, use_safetensors=True).to(device)
    logits, targets = _logits(model, datasets["calibration"], tokenizer, settings["maximum_sequence_length"],
                             settings["micro_batch_size"], device, dtype)
    temperature = fit_temperature(logits, targets)
    calibration = classification_metrics(targets, softmax(logits, temperature), bundle.label_names)
    final = run / "model"
    final.mkdir(exist_ok=False)
    model.save_pretrained(str(final), safe_serialization=True)
    tokenizer.save_pretrained(str(final))
    weight_hashes = {str(path.relative_to(run)): sha256(path) for path in sorted(final.iterdir()) if path.is_file()}
    metadata = {"schema_version": 1, "trained": True, "component": component, "task": config["task"],
        "labels": bundle.labels, "manifest_hashes": bundle.manifest_hashes, "temperature": temperature,
        "calibration_split": "calibration", "maximum_sequence_length": settings["maximum_sequence_length"],
        "text_view": view_settings, "original_text_retained": True, "files_sha256": weight_hashes,
        "language_scope": config.get("language_scope", []), "experimental": True,
        "base_model_permission": config["model"]["permission_path"]}
    metadata["input_contract_sha256"] = config["_input_contract_sha256"]
    write_json(run / "model_manifest.json", metadata)
    result = {"component": component, "task": config["task"], "trained": True, "labels": bundle.labels,
        "manifest_hashes": bundle.manifest_hashes, "tuning_history": progress["history"],
        "calibration_metrics": calibration, "temperature": temperature, "hardware": hardware,
        "elapsed_seconds": round(time.monotonic() - started, 3), "updates": progress["updates"],
        "resources_before": resource_before, "resources_after": resources(config["_workspace"]),
        "processed_training_examples_this_session": trained_examples,
        "session_examples_per_second_including_validation_calibration": trained_examples / max(time.monotonic() - started, 1e-9),
        "peak_vram_allocated_bytes": torch.cuda.max_memory_allocated() if device.type == "cuda" else None,
        "test_evaluated": False, "model_manifest_sha256": sha256(run / "model_manifest.json")}
    packages = {}
    for name in ("torch", "transformers", "datasets", "safetensors", "numpy"):
        packages[name] = importlib.metadata.version(name)
    result["environment"] = {"python": sys.version, "platform": platform.platform(), "packages": packages}
    source_root = Path(__file__).resolve().parents[1]
    result["code_sha256"] = {str(path.relative_to(source_root)): sha256(path)
                             for path in source_root.rglob("*.py")}
    result["base_model_permission_sha256"] = sha256(safe_path(config["model"]["permission_path"], config["_workspace"]))
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config["_workspace"],
            capture_output=True, text=True, timeout=5, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
        result["git_revision"] = revision if len(revision) == 40 else None
    except (OSError, subprocess.TimeoutExpired):
        result["git_revision"] = None
    write_json(run / "training_report.json", result)
    return result


def load_trained(config: dict, run_directory: str, device_name: str = "cpu"):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    run = safe_path(run_directory, config["_workspace"], output=True)
    manifest = read_json(run / "model_manifest.json")
    if manifest.get("trained") is not True or manifest.get("task") != config["task"] or manifest.get("labels") != config["labels"]:
        raise ValueError("Trained model/task/label contract mismatch.")
    if sha256(run / "input_contract.json") != manifest.get("input_contract_sha256"):
        raise ValueError("Frozen preprocessing/source contract hash does not match the trained artifact.")
    contract = read_json(run / "input_contract.json")
    if contract.get("text_view") != manifest.get("text_view") or contract.get("manifest_hashes") != manifest.get("manifest_hashes"):
        raise ValueError("Trained preprocessing/data differs from the frozen input contract.")
    actual_files = {str(path.relative_to(run)) for path in (run / "model").iterdir() if path.is_file()}
    if not actual_files or actual_files != set(manifest.get("files_sha256", {})):
        raise ValueError("Every trained model/tokenizer file requires an exact recorded hash.")
    for name, checksum in manifest["files_sha256"].items():
        path = (run / name).resolve()
        if not path.is_relative_to(run) or sha256(path) != checksum:
            raise ValueError("Trained model artifact hash verification failed.")
    if device_name not in {"cpu", "cuda", "auto"}:
        raise ValueError("Inference device must be cpu,cuda or auto.")
    device = torch.device("cuda" if device_name == "auto" and torch.cuda.is_available() else
                          "cpu" if device_name == "auto" else device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Explicit CUDA inference is unavailable; choose cpu or auto.")
    model = AutoModelForSequenceClassification.from_pretrained(str(run / "model"), local_files_only=True,
        trust_remote_code=False, use_safetensors=True).to(device)
    if model.config.label2id != manifest["labels"]:
        raise ValueError("Saved model class ordering differs from its manifest.")
    tokenizer = AutoTokenizer.from_pretrained(str(run / "model"), local_files_only=True, trust_remote_code=False)
    return run, manifest, model, tokenizer, device


def evaluate(config: dict, run_directory: str, split: str = "tuning", final_test: bool = False,
             device_name: str = "cpu") -> dict:
    if split not in {"tuning", "calibration", "test"}:
        raise ValueError("Evaluation excludes training data.")
    bundle = load_experiment(config)
    run, manifest, model, tokenizer, device = load_trained(config, run_directory, device_name)
    if bundle.manifest_hashes != manifest["manifest_hashes"]:
        raise ValueError("Evaluation data differs from the frozen model experiment.")
    if split == "test":
        selection = read_json(run / "selection.json")
        if selection.get("model_frozen") is not True or selection.get("selected_for_final_test") is not True or (
            selection.get("model_manifest_sha256") != sha256(run / "model_manifest.json") or
            selection.get("manifest_hashes") != bundle.manifest_hashes or not selection.get("reviewed_by")):
            raise ValueError("Final test needs a human-reviewed frozen model selection record.")
    reserve_final_test(run, bundle, split, final_test)
    dataset = _dataset(bundle.records[split], bundle.label_names, run / "evaluation_cache" / split, manifest["text_view"])
    started = time.monotonic()
    logits, targets = _logits(model, dataset, tokenizer, manifest["maximum_sequence_length"], 4, device, None)
    probabilities = softmax(logits, manifest["temperature"])
    metrics = classification_metrics(targets, probabilities, bundle.label_names)
    cohorts = {}
    for index, row in enumerate(bundle.records[split]):
        tags = list(row.metadata.get("cohorts") or [])
        for key in ("language_code", "script"):
            if row.metadata.get(key):
                tags.append(("language" if key == "language_code" else "script") + ":" + row.metadata[key])
        for tag in set(tags):
            cohorts.setdefault(tag, []).append(index)
    cohort_metrics = {tag: classification_metrics([targets[i] for i in indices],
        [probabilities[i] for i in indices], bundle.label_names) for tag, indices in cohorts.items()}
    result = {"task": config["task"], "split": split, "metrics": metrics, "cohorts": cohort_metrics,
        "manifest_hashes": bundle.manifest_hashes, "model_manifest_sha256": sha256(run / "model_manifest.json"),
        "evaluation_seconds_including_cohort_metrics": time.monotonic() - started,
        "calibration_scope": "fit_split_diagnostic" if split == "calibration" else "held_out_from_calibration",
        "cohort_policy": "Human/source metadata only; absence does not imply a tested language capability."}
    write_json(run / ("evaluation-" + split + "-%d.json" % time.time_ns()), result)
    return result


def predict(config: dict, run_directory: str, texts: list[str], language_code: str,
            device_name: str = "cpu") -> list[dict]:
    if not texts or len(texts) > 32 or any(not isinstance(text, str) or not text.strip() or len(text) > 20000 for text in texts):
        raise ValueError("Prediction expects 1..32 nonempty reviews of at most20000 code points.")
    _, manifest, model, tokenizer, device = load_trained(config, run_directory, device_name)
    if language_code not in manifest["language_scope"]:
        return [{"status": "unsupported_language", "task": config["task"], "label": None,
                 "probabilities": None, "language_code": language_code} for _ in texts]
    names = sorted(manifest["labels"], key=manifest["labels"].get)
    dataset = [{"text": _model_text(text, manifest["text_view"])} for text in texts]
    logits, _ = _logits(model, dataset, tokenizer, manifest["maximum_sequence_length"], 4, device, None)
    probabilities = softmax(logits, manifest["temperature"])
    return [{"status": "analysed", "task": config["task"], "language_code": language_code,
             "label": names[max(range(len(names)), key=row.__getitem__)],
             "probabilities": dict(zip(names, row)), "calibrated": True, "experimental": True,
             "long_review_policy": "truncate_at_" + str(manifest["maximum_sequence_length"]),
             "sarcasm_does_not_reverse_sentiment": True} for row in probabilities]
