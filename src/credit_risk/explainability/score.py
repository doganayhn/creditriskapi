"""Versioned probability-to-score mapping; no learned parameters or business policy."""

from dataclasses import dataclass

import numpy as np
from scipy.special import expit
from sklearn.metrics import roc_auc_score

from credit_risk.modeling.metrics import binary_target, validate_probabilities

SCORE_VERSION = "internal-risk-score-1.0.0"


@dataclass(frozen=True)
class InternalScore:
    base_score: float = 600.
    base_good_to_bad_odds: float = 50.
    pdo: float = 20.
    epsilon: float = 1e-12
    version: str = SCORE_VERSION

    def __post_init__(self):
        if (self.version != SCORE_VERSION or self.base_score != 600 or
                self.base_good_to_bad_odds != 50 or self.pdo != 20 or self.epsilon != 1e-12):
            raise ValueError("Changing internal score V1 parameters requires a new reviewed version")

    @property
    def factor(self):
        return self.pdo / np.log(2.)

    @property
    def offset(self):
        return self.base_score - self.factor * np.log(self.base_good_to_bad_odds)

    def transform(self, probability):
        if not len(probability):
            raise ValueError("Probability must be a nonempty vector")
        p = validate_probabilities(probability, len(probability))
        safe = np.clip(p, self.epsilon, 1 - self.epsilon)
        return self.offset + self.factor * (np.log1p(-safe) - np.log(safe)), safe != p

    def inverse(self, scores):
        values = np.asarray(scores, dtype=float)
        if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
            raise ValueError("Scores must be a nonempty finite vector")
        return expit((self.offset - values) / self.factor)

    def decompose(self, base, contributions, probability, *, calibration_method,
                  model_output="raw", objective="binary:logistic", tolerance=1e-3):
        scores, clipped = self.transform(probability)
        if (calibration_method != "identity" or model_output != "raw" or
                objective != "binary:logistic" or clipped.any()):
            return {"score_point_decomposition_supported": False,
                    "reason": "Requires binary logistic raw-margin SHAP, identity calibration and no probability clipping"}
        values, bases = np.asarray(contributions, dtype=float), np.asarray(base, dtype=float)
        if (values.ndim != 2 or values.shape[0] != len(scores) or bases.shape != scores.shape or
                not np.isfinite(values).all() or not np.isfinite(bases).all()):
            raise ValueError("Invalid score decomposition shapes or values")
        points = -self.factor * values
        score_base = self.offset - self.factor * bases
        residual = np.abs(score_base + points.sum(axis=1) - scores)
        if residual.max() > tolerance:
            raise ValueError("Score-point decomposition exceeds numerical tolerance")
        return {"score_point_decomposition_supported": True, "score_base_value": score_base,
                "score_point_contributions": points, "max_absolute_residual": float(residual.max()),
                "mean_absolute_residual": float(residual.mean())}


def score_summary(mapping, probability):
    scores, clipped = mapping.transform(probability)
    summary = {"count": len(scores), "mean": float(scores.mean()), "std": float(scores.std()),
               "min": float(scores.min()), "max": float(scores.max()),
               "probability_clipping_count": int(clipped.sum()), "probability_clipping_rate": float(clipped.mean())}
    summary.update({f"p{percent:02}": float(np.quantile(scores, percent / 100))
                    for percent in (1, 5, 10, 25, 50, 75, 90, 95, 99)})
    return summary


def rank_validation(mapping, y, probability):
    p = validate_probabilities(probability, len(y))
    target = binary_target(y, len(p))
    scores, clipped = mapping.transform(p)
    order = np.argsort(p, kind="stable")
    delta_p, delta_score = np.diff(p[order]), np.diff(scores[order])
    inverse_ranking = bool(np.all(delta_score[delta_p > 0] < 0) and np.all(delta_score[delta_p == 0] == 0))
    auc_p, auc_score = float(roc_auc_score(target, p)), float(roc_auc_score(target, -scores))
    if not inverse_ranking or abs(auc_p - auc_score) > 1e-12:
        raise ValueError("Score ranking does not preserve inverse probability ranking")
    return {"inverse_ranking_verified": inverse_ranking, "probability_roc_auc": auc_p,
            "negative_score_roc_auc": auc_score, "auc_absolute_difference": abs(auc_p - auc_score),
            "inverse_max_absolute_error": float(np.max(np.abs(mapping.inverse(scores) - p))),
            "probability_clipping_count": int(clipped.sum())}


def score_deciles(mapping, y, probability):
    p = validate_probabilities(probability, len(y))
    target = binary_target(y, len(p))
    scores, _ = mapping.transform(p)
    # Stable original row position breaks exact score ties; equal-count diagnostics,
    # not reusable thresholds or risk bands. Every position appears exactly once.
    ordered = np.argsort(-scores, kind="stable")
    groups = np.array_split(ordered, min(10, len(scores)))
    return [{"decile": i, "count": len(indices), "min_score": float(scores[indices].min()),
             "max_score": float(scores[indices].max()), "mean_score": float(scores[indices].mean()),
             "mean_reported_probability": float(p[indices].mean()),
             "observed_default_rate": float(target[indices].mean()), "source": "validation",
             "test_set_evaluated": False} for i, indices in enumerate(groups, 1)]
