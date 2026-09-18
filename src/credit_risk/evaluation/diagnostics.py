"""Aggregate holdout diagnostics; no fitting, selection or row-level export."""

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from credit_risk.modeling.metrics import binary_target, validate_probabilities
from credit_risk.features.definitions import FAIRNESS_REVIEW_FIELDS


def bootstrap(y, logistic, xgboost, *, seed=42, replicates=1000):
    """Same resampled rows for both models; conditional percentile intervals."""
    y = binary_target(y, len(y))
    logistic = validate_probabilities(logistic, len(y))
    xgboost = validate_probabilities(xgboost, len(y))
    if type(replicates) is not int or replicates < 1:
        raise ValueError("Positive bootstrap replicate count required")
    def metrics(target, p):
        return np.array([roc_auc_score(target, p), average_precision_score(target, p),
                         brier_score_loss(target, p), log_loss(target, p, labels=[0, 1])])
    rng = np.random.default_rng(seed)
    selected, differences = [], []
    for _ in range(replicates):
        indices = rng.integers(0, len(y), len(y))
        target = y[indices]
        if np.unique(target).size < 2:
            continue
        x = metrics(target, xgboost[indices])
        selected.append(x)
        differences.append(x - metrics(target, logistic[indices]))
    if not selected:
        raise ValueError("No two-class bootstrap replicates")
    keys = ("roc_auc", "average_precision", "brier_score", "log_loss")
    def intervals(values):
        bounds = np.percentile(values, [2.5, 97.5], axis=0, method="linear")
        return {key: bounds[:, i].tolist() for i, key in enumerate(keys)}
    return {"requested_replicates": replicates, "successful_replicates": len(selected),
            "skipped_single_class": replicates - len(selected), "seed": seed,
            "method": "paired row bootstrap with replacement; percentile 95%; linear interpolation",
            "xgboost_95_ci": intervals(selected), "delta_xgboost_minus_logistic_95_ci": intervals(differences)}


def ranking_tables(mapping, y, probability):
    y = binary_target(y, len(y))
    p = validate_probabilities(probability, len(y))
    scores, _ = mapping.transform(p)
    # Lowest score/highest risk first. Existing split position breaks exact ties.
    groups = np.array_split(np.argsort(scores, kind="stable"), min(10, len(y)))
    deciles, gains = [], []
    cumulative_n = cumulative_defaults = 0
    for number, indices in enumerate(groups, 1):
        count, defaults = len(indices), int(y[indices].sum())
        cumulative_n += count
        cumulative_defaults += defaults
        deciles.append({"decile": number, "count": count, "min_score": float(scores[indices].min()),
                        "max_score": float(scores[indices].max()), "mean_score": float(scores[indices].mean()),
                        "mean_reported_probability": float(p[indices].mean()),
                        "observed_default_rate": float(y[indices].mean())})
        gains.append({"decile": number, "cumulative_count": cumulative_n,
                      "cumulative_population_percentage": 100 * cumulative_n / len(y),
                      "cumulative_defaults_captured": cumulative_defaults,
                      "cumulative_default_capture_percentage": 100 * cumulative_defaults / int(y.sum()),
                      "cumulative_lift": (cumulative_defaults / cumulative_n) / float(y.mean())})
    return deciles, gains


def subgroup_metrics(review, y, probability, *, minimum_count=100):
    """Aligned review fields only; retain raw codes and individual ages literally."""
    y = binary_target(y, len(y))
    p = validate_probabilities(probability, len(y))
    if tuple(review.columns) != FAIRNESS_REVIEW_FIELDS or len(review) != len(y):
        raise ValueError("Aligned demographic review contract required")
    if type(minimum_count) is not int or minimum_count < 1 or review.isna().any().any():
        raise ValueError("Invalid subgroup minimum or missing review values")
    rows = []
    for field in FAIRNESS_REVIEW_FIELDS:
        for value in sorted(review[field].unique()):
            mask = review[field].to_numpy(dtype=int) == value
            n = int(mask.sum())
            row = {"field": field, "raw_value": int(value), "count": n,
                   "status": "sufficient" if n >= minimum_count else "insufficient_sample",
                   "observed_default_rate": None, "mean_reported_probability": None,
                   "roc_auc": None, "brier_score": None, "calibration_gap": None}
            if n >= minimum_count:
                target, prob = y[mask], p[mask]
                row.update(observed_default_rate=float(target.mean()), mean_reported_probability=float(prob.mean()),
                           brier_score=float(brier_score_loss(target, prob)),
                           calibration_gap=float(prob.mean() - target.mean()))
                if np.unique(target).size == 2:
                    row["roc_auc"] = float(roc_auc_score(target, prob))
                else:
                    row["status"] = "single_class_auc_undefined"
            rows.append(row)
    return rows
