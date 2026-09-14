"""Deterministic model diagnostic drivers, with no lending or causal semantics."""

import numpy as np

from credit_risk.features.definitions import MODEL_INPUT_FEATURES


def reason_codes(sources, contributions, *, top_k=5, score_factor=None):
    values = np.asarray(contributions, dtype=float)
    if (values.shape != (len(sources),) or not np.isfinite(values).all() or
            len(set(sources)) != len(sources) or not set(sources).issubset(MODEL_INPUT_FEATURES)):
        raise ValueError("Invalid source-level diagnostic contributions")
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    result = {}
    for direction, sign in (("risk_increasing", 1), ("risk_decreasing", -1)):
        ranked = sorted([(name, float(value)) for name, value in zip(sources, values) if sign * value > 0],
                        key=lambda item: (-sign * item[1], item[0]))[:top_k]
        result[direction] = [{"source_feature": name, "contribution_to_raw_margin": value,
                              "direction_on_default_risk": direction,
                              **({"score_point_contribution": -score_factor * value} if score_factor is not None else {})}
                             for name, value in ranked]
    return {"interpretation": "model diagnostic drivers", **result}
