"""Descriptive output distributions, not feature drift or realized performance."""

from collections import Counter
import numpy as np


def bin_counts(values, boundaries):
    edges = np.asarray(boundaries, dtype=float)
    values = np.asarray(values, dtype=float)
    if edges.ndim != 1 or not np.isfinite(edges).all() or np.any(np.diff(edges) <= 0) or not np.isfinite(values).all():
        raise ValueError("Invalid finite values or ordered bin boundaries")
    # (-infinity, edge0), [edge0, edge1), ..., [edgeN, infinity).
    return np.bincount(np.searchsorted(edges, values, side="right"), minlength=len(edges)+1).tolist()


def psi(actual, expected, epsilon=1e-6):
    a, e = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if a.ndim != 1 or a.shape != e.shape or not len(a) or not 0 < epsilon < 1:
        raise ValueError("Invalid PSI dimensions or epsilon")
    if not np.isfinite(a).all() or not np.isfinite(e).all() or np.any(a < 0) or np.any(e < 0) or a.sum() <= 0 or e.sum() <= 0:
        raise ValueError("Invalid PSI counts/proportions")
    a, e = a/a.sum(), e/e.sum()
    a, e = np.maximum(a, epsilon), np.maximum(e, epsilon)
    a, e = a/a.sum(), e/e.sum()
    return float(np.sum((a-e)*np.log(a/e)))


def statistics(values, quantiles):
    if not values: return {"mean": None, "quantiles": {key: None for key in quantiles}}
    return {"mean": float(np.mean(values)), "quantiles": {key: float(np.quantile(values, q)) for key, q in quantiles.items()}}


def summarize(rows, baseline, minimum_count=100):
    if type(minimum_count) is not int or minimum_count < 1: raise ValueError("Invalid minimum count")
    scores = [r["internal_risk_score"] for r in rows]
    probabilities = [r["reported_probability"] for r in rows]
    latencies = [r["inference_latency_ms"] for r in rows]
    if any(not np.isfinite(values).all() for values in (scores, probabilities, latencies)):
        raise ValueError("Nonfinite monitoring values")
    score_counts = bin_counts(scores, baseline["score_bin_boundaries"])
    quantiles = {"p01": .01, "p05": .05, "p50": .5, "p95": .95, "p99": .99}
    return {"event_count": len(rows), "predict_count": sum(r["endpoint_type"] == "predict" for r in rows),
        "explain_count": sum(r["endpoint_type"] == "explain" for r in rows),
        "version_counts": {field: dict(sorted(Counter(r[field] for r in rows).items())) for field in ("model_version", "calibration_version", "score_version")},
        "reported_probability": statistics(probabilities, quantiles), "internal_score": statistics(scores, quantiles),
        "inference_latency_ms": statistics(latencies, {"p50": .5, "p95": .95, "p99": .99}),
        "score_bin_counts": score_counts, "probability_bin_boundaries": [n/10 for n in range(1,10)],
        "probability_bin_counts": bin_counts(probabilities, [n/10 for n in range(1,10)]),
        "score_psi": psi(score_counts, baseline["expected_bin_proportions"], baseline["psi_epsilon"]) if rows else None,
        "baseline_version": baseline["baseline_version"], "minimum_count": minimum_count,
        "sample_size_limited": len(rows) < minimum_count, "successful_audited_events_only": True,
        "test_set_evaluated": False}
