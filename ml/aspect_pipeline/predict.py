"""Never holds both substantial models on the GPU at once."""
from dataclasses import replace
import gc
from ml.aspect_common.data import AspectSpan
from ml.aspect_common.engine import load_trained


def predict(examples, extraction_config, extraction_run, sentiment_config, sentiment_run, device_name="cpu"):
    examples = list(examples)
    if extraction_config["taxonomy"] != sentiment_config["taxonomy"]:
        raise ValueError("Pipeline taxonomies differ.")
    if any(row.language_code not in extraction_config["language_scope"] or row.language_code not in sentiment_config["language_scope"] for row in examples):
        raise ValueError("Pipeline language is outside one component's declared scope.")
    from ml.aspect_extraction.task import predict_examples as extract
    _, extractor_manifest, model, tokenizer, device = load_trained(extraction_config, extraction_run, device_name)
    extracted = extract(model, tokenizer, examples, extraction_config, device)
    del model, tokenizer
    gc.collect()
    import torch
    if device.type == "cuda":
        torch.cuda.empty_cache()
    targets = []
    for row, prediction in zip(examples, extracted):
        if prediction.get("aspects") is None:
            raise ValueError("Extractor unavailable/unsupported; no replacement targets.")
        targets.append(replace(row, aspects=tuple(AspectSpan(item["aspect"], item["start"], item["end"],
            row.text[item["start"]:item["end"]]) for item in prediction["aspects"])))
    from ml.aspect_sentiment.task import predict_examples as classify
    _, sentiment_manifest, model, tokenizer, device = load_trained(sentiment_config, sentiment_run, device_name)
    if extractor_manifest["manifest_hashes"] != sentiment_manifest["manifest_hashes"]:
        raise ValueError("Paired components must use the same frozen study manifests.")
    result = classify(model, tokenizer, targets, sentiment_config, device, temperature=sentiment_manifest["temperature"])
    for row, extraction in zip(result, extracted):
        row.update(extraction_coverage=extraction.get("coverage"), status="analysed",
            implicit_aspects_supported=False, experimental=True,
            extraction_model_version=extractor_manifest["input_contract_sha256"],
            sentiment_model_version=sentiment_manifest["input_contract_sha256"])
    return result
