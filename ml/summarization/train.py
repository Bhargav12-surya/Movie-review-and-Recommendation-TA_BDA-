"""Pretrained hierarchical inference is the initial strategy, not local fine-tuning."""
from ml.common.local_assets import approved_assets


def preflight(config):
    if config.get("mode", "extractive") == "extractive":
        return {"ready": False, "strategy": "extractive_evidence", "pretrained_model_required": False,
                "blockers": ["Supply and validate actual permission-backed canonical movie evidence before running."], "locally_trained": False}
    try:
        from importlib.metadata import version
        version("transformers")
        _, permission = approved_assets(config)
        return {"ready": True, "strategy": "licensed_pretrained_hierarchical_candidate", "model_revision": permission["model_revision"],
                "publication_requires_human_factuality_approval": True, "locally_trained": False}
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        return {"ready": False, "blockers": ["Reviewed local generation assets/dependencies missing."], "locally_trained": False}


def train(*args, **kwargs):
    raise ValueError("Optional summary fine-tuning requires genuine permitted review-summary targets, held-out splits and separate approval. No training is claimed.")
