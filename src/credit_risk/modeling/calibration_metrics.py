"""Aggregate quantile reliability and frozen validation probability-quality comparison."""

import numpy as np
from sklearn.metrics import brier_score_loss, log_loss

from credit_risk.modeling.comparison import paired_bootstrap
from credit_risk.modeling.metrics import binary_target, evaluate, validate_probabilities


def reliability(y, probability, bins: int = 10) -> dict:
    y = binary_target(y, len(y))
    p = validate_probabilities(probability, len(y))
    if type(bins) is not int or bins < 1:
        raise ValueError("Reliability bins must be a positive integer")
    # Equal-frequency targets; collapse duplicate boundaries and never split tied
    # probabilities across bins. Constant predictions produce one nonempty bin.
    edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)[1:-1]))
    edges = edges[(edges > p.min()) & (edges < p.max())]
    labels = np.searchsorted(edges, p, side="right")
    rows = []
    for label in np.unique(labels):
        mask = labels == label
        mean, observed = float(p[mask].mean()), float(y[mask].mean())
        rows.append({"bin": len(rows) + 1, "count": int(mask.sum()),
                     "minimum_probability": float(p[mask].min()), "maximum_probability": float(p[mask].max()),
                     "mean_probability": mean, "observed_default_rate": observed,
                     "absolute_calibration_gap": abs(mean - observed)})
    return {"ece": sum(row["count"] / len(y) * row["absolute_calibration_gap"] for row in rows),
            "requested_bins": bins, "actual_nonempty_bins": len(rows),
            "binning": "quantile edges; duplicate edges collapsed; ties kept together; empty bins omitted",
            "bins": rows}


def probability_metrics(y, probability, bins: int = 10) -> dict:
    values = evaluate(y, probability)
    values.pop("threshold_0_5")
    values["ece"] = reliability(y, probability, bins)["ece"]
    return values


def downstream_status(logistic: dict, xgboost: dict) -> str:
    keys = ("roc_auc", "average_precision", "brier_score", "log_loss")
    directions = (1, 1, -1, -1)
    values = np.array([direction * (xgboost[key] - logistic[key]) for key, direction in zip(keys, directions)])
    if not np.isfinite(values).all():
        raise ValueError("Downstream selection requires finite metrics")
    if (values >= 0).all() and (values > 0).any():
        return "XGBOOST_SELECTED_FOR_DOWNSTREAM"
    if (values <= 0).all() and (values < 0).any():
        return "LOGISTIC_SELECTED_FOR_DOWNSTREAM"
    return "MIXED_VALIDATION_RESULT"


def paired_quality_bootstrap(y, logistic, xgboost, seed: int, replicates: int = 1000) -> dict:
    """Extend Phase-5 paired discrimination intervals with Brier/log-loss intervals."""
    result = paired_bootstrap(y, logistic, xgboost, seed, replicates)
    y = binary_target(y, len(y))
    logistic = validate_probabilities(logistic, len(y))
    xgboost = validate_probabilities(xgboost, len(y))
    rng = np.random.default_rng(seed)
    differences = []
    for _ in range(replicates):
        indices = rng.integers(0, len(y), len(y))  # Same deterministic pairs as Phase 5.
        target = y[indices]
        if len(np.unique(target)) == 1:
            continue
        differences.append([
            brier_score_loss(target, xgboost[indices]) - brier_score_loss(target, logistic[indices]),
            log_loss(target, xgboost[indices], labels=[0, 1]) - log_loss(target, logistic[indices], labels=[0, 1]),
        ])
    if len(differences) != result["successful_replicates"]:
        raise ValueError("Paired bootstrap replication mismatch")
    ci = np.percentile(differences, [2.5, 97.5], axis=0)
    result.update(delta_brier_score_95_ci=ci[:, 0].tolist(), delta_log_loss_95_ci=ci[:, 1].tolist())
    return result
