"""Actual Sentence Transformer inference from reviewed cached weights."""
import hashlib
import math
from ml.common.local_assets import approved_assets


def encode(texts, config):
    if not isinstance(texts, list) or not texts or len(texts) > 10000 or any(not isinstance(text, str) or not text.strip() or len(text) > 20000 for text in texts):
        raise ValueError("Supply bounded actual metadata/review text.")
    folder, permission = approved_assets(config)
    # SentenceTransformers modules.json is an array, unlike ordinary metadata.
    import json
    definitions = json.loads((folder / "modules.json").read_text(encoding="utf-8"))
    if not isinstance(definitions, list) or any(not row.get("type", "").startswith("sentence_transformers.models.") for row in definitions):
        raise ValueError("Only reviewed built-in Sentence Transformer modules are allowed.")
    batch = config.get("batch_size", 8)
    if type(batch) is not int or not 1 <= batch <= 32:
        raise ValueError("Bound embedding inference batches to1..32.")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(str(folder), device=config.get("device", "cpu"), local_files_only=True, trust_remote_code=False)
    vectors = model.encode(texts, batch_size=batch, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    if vectors.ndim != 2 or vectors.shape[0] != len(texts) or not all(math.isfinite(float(value)) for value in vectors.flat):
        raise ValueError("Invalid embedding output.")
    return {"vectors": vectors, "dimension": int(vectors.shape[1]), "model_revision": permission["model_revision"],
            "content_sha256": [hashlib.sha256(text.encode("utf-8")).hexdigest() for text in texts],
            "normalized": True, "locally_fine_tuned": False}
