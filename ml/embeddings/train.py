"""Pretrained-only component readiness; supervised fine-tuning is not claimed."""
from ml.common.local_assets import approved_assets


def preflight(config):
    try:
        from importlib.metadata import version
        version("sentence-transformers")
        _, permission = approved_assets(config)
        return {"ready": True, "strategy": "licensed_pretrained_inference", "model_revision": permission["model_revision"], "locally_trained": False,
                "readiness_scope": "local_assets_and_dependency_metadata; actual_forward_pass_not_verified"}
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        return {"ready": False, "blockers": ["Reviewed local embedding model assets are missing."], "locally_trained": False}


def train(*args, **kwargs):
    raise ValueError("This component uses actual pretrained weights. Contrastive fine-tuning needs separately approved paired relevance data and protocol.")
