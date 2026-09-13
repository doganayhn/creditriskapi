"""Pure binary diagnostics at one fixed reference threshold, never policy selection."""

import numpy as np
from sklearn.metrics import (
    average_precision_score, brier_score_loss, confusion_matrix, f1_score,
    log_loss, precision_score, recall_score, roc_auc_score, roc_curve,
)

REFERENCE_THRESHOLD = 0.50


def binary_target(y, rows: int) -> np.ndarray:
    target = np.asarray(y, dtype=float)
    if target.ndim != 1 or len(target) != rows or rows == 0:
        raise ValueError("Target must be a nonempty aligned one-dimensional array")
    if not np.isfinite(target).all() or not np.isin(target, [0, 1]).all():
        raise ValueError("Target must be finite and binary (0/1)")
    if len(np.unique(target)) != 2:
        raise ValueError("Both target classes are required")
    return target.astype(int)


def validate_probabilities(raw_probability, rows: int) -> np.ndarray:
    values = np.asarray(raw_probability, dtype=float)
    if values.shape != (rows,) or not np.isfinite(values).all():
        raise ValueError("Raw probabilities must be finite and aligned with rows")
    if ((values < 0) | (values > 1)).any():
        raise ValueError("Raw probabilities must lie in [0, 1]")
    return values


def evaluate(y, raw_probability) -> dict:
    target = binary_target(y, len(y))
    probability = validate_probabilities(raw_probability, len(target))
    prediction = probability >= REFERENCE_THRESHOLD
    tn, fp, fn, tp = confusion_matrix(target, prediction, labels=[0, 1]).ravel()
    auc = float(roc_auc_score(target, probability))
    fpr, tpr, _ = roc_curve(target, probability)
    return {
        "roc_auc": auc,
        "average_precision": float(average_precision_score(target, probability)),
        "ks": float(np.max(tpr - fpr)), "gini": 2 * auc - 1,
        "brier_score": float(brier_score_loss(target, probability)),
        "log_loss": float(log_loss(target, probability, labels=[0, 1])),
        "mean_predicted_probability": float(probability.mean()),
        "observed_positive_rate": float(target.mean()),
        "threshold_0_5": {
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            "precision": float(precision_score(target, prediction, zero_division=0)),
            "recall": float(recall_score(target, prediction, zero_division=0)),
            "specificity": float(tn / (tn + fp)),
            "f1": float(f1_score(target, prediction, zero_division=0)),
        },
    }


def bootstrap_validation(y, raw_probability, seed: int, replicates: int = 1000) -> dict:
    """Conditional percentile intervals for fixed validation predictions, not refits."""
    target = binary_target(y, len(y))
    probability = validate_probabilities(raw_probability, len(target))
    if type(replicates) is not int or replicates < 1:
        raise ValueError("Bootstrap replicates must be a positive integer")
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(replicates):
        indices = rng.integers(0, len(target), size=len(target))
        sampled = target[indices]
        if len(np.unique(sampled)) == 1:
            continue
        scores.append([roc_auc_score(sampled, probability[indices]),
                       average_precision_score(sampled, probability[indices])])
    if not scores:
        raise ValueError("No two-class bootstrap replicates; cannot estimate intervals")
    intervals = np.percentile(scores, [2.5, 97.5], axis=0)
    return {
        "roc_auc_95_ci": intervals[:, 0].tolist(),
        "average_precision_95_ci": intervals[:, 1].tolist(),
        "bootstrap_requested_replicates": replicates,
        "bootstrap_successful_replicates": len(scores),
        "bootstrap_skipped_single_class": replicates - len(scores),
        "random_seed": seed, "method": "row bootstrap with replacement; percentile 95%",
    }
