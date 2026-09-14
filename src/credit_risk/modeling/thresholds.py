"""TRAIN-OOF technical thresholds; no lending actions or validation optimization."""

import numpy as np
from sklearn.metrics import confusion_matrix, roc_curve

from credit_risk.modeling.metrics import binary_target, validate_probabilities

REFERENCE_THRESHOLD = .50
THRESHOLD_GRID = tuple(i / 20 for i in range(1, 20))


def threshold_metrics(y, probability, threshold: float) -> dict:
    y = binary_target(y, len(y))
    p = validate_probabilities(probability, len(y))
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Technical threshold must be finite and in [0, 1]")
    prediction = p >= threshold
    tn, fp, fn, tp = map(int, confusion_matrix(y, prediction, labels=[0, 1]).ravel())
    precision = tp / (tp + fp) if tp + fp else 0.
    recall, specificity = tp / (tp + fn), tn / (tn + fp)
    return {"threshold": float(threshold), "predicted_positive_count": int(prediction.sum()),
            "predicted_positive_rate": float(prediction.mean()), "tn": tn, "fp": fp, "fn": fn, "tp": tp,
            "precision": precision, "recall": recall, "specificity": specificity,
            "f1": 2 * tp / (2 * tp + fp + fn), "false_positive_rate": 1 - specificity,
            "false_negative_rate": 1 - recall}


def select_train_threshold(y_train, oof_reported_probability, tolerance: float = 1e-12) -> float:
    target = binary_target(y_train, len(y_train))
    p = validate_probabilities(oof_reported_probability, len(target))
    fpr, tpr, thresholds = roc_curve(target, p, drop_intermediate=False)
    finite = np.isfinite(thresholds) & (thresholds >= 0) & (thresholds <= 1)
    j, candidates = (tpr - fpr)[finite], thresholds[finite]
    # roc_curve's +inf sentinel is not an actionable probability threshold.
    return float(np.max(candidates[np.abs(j - j.max()) <= tolerance]))


def train_threshold_table(y_train, oof_reported_probability, selected: float) -> list[dict]:
    thresholds = sorted(set((*THRESHOLD_GRID, selected)))
    return [{**threshold_metrics(y_train, oof_reported_probability, value),
             "source": "train_oof", "is_max_ks": value == selected,
             "is_reference": value == REFERENCE_THRESHOLD, "test_set_evaluated": False} for value in thresholds]
