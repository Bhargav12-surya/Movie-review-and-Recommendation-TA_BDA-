from dataclasses import dataclass
import math
from ml.common.artifacts import read_json, sha256


@dataclass(frozen=True)
class ScorePolicy:
    method_version: str
    model_version: str
    minimum_reviews: int
    minimum_distinct_reviewers: int
    minimum_effective_reviews: float
    shrinkage_strength: float
    prior: float | None
    bootstrap_samples: int = 300
    seed: int = 42

    def __post_init__(self):
        if not self.method_version or not self.model_version or type(self.minimum_reviews) is not int or self.minimum_reviews < 1 or type(self.minimum_distinct_reviewers) is not int or self.minimum_distinct_reviewers < 1:
            raise ValueError("Versioned models/method and reviewed positive evidence thresholds are required.")
        if not math.isfinite(self.minimum_effective_reviews) or self.minimum_effective_reviews < 1 or not math.isfinite(self.shrinkage_strength) or self.shrinkage_strength < 0:
            raise ValueError("Invalid effective support/shrinkage policy.")
        if self.shrinkage_strength and (self.prior is None or not math.isfinite(self.prior) or not 0 <= self.prior <= 100):
            raise ValueError("Shrinkage needs a reviewed population prior; never display it without evidence.")
        if type(self.bootstrap_samples) is not int or not 0 <= self.bootstrap_samples <= 1000:
            raise ValueError("Bound uncertainty resampling to0..1000.")


def load_policy(config_path, approval_path):
    config, approval = read_json(config_path), read_json(approval_path)
    if approval.get("methodology_approved") is not True or not approval.get("approved_by") or approval.get("config_sha256") != sha256(config_path):
        raise ValueError("A human-reviewed evidence/shrinkage methodology is required.")
    return ScorePolicy(**config)
