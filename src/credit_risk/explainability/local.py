"""One-record in-memory explanation with the same frozen engineering and lineage."""

import pandas as pd

from credit_risk.features.definitions import PRIMARY_MODEL_FEATURES, REPAYMENT_COLUMNS, BILL_COLUMNS, PAYMENT_COLUMNS
from credit_risk.features.engineering import engineer_features
from credit_risk.features.preprocessing import transform_split
from credit_risk.explainability.aggregation import aggregate
from credit_risk.explainability.reason_codes import reason_codes


def explain_record(record, context, explainer, mapping, rows, *, top_k=5, score_tolerance=1e-3):
    if set(record) != set(PRIMARY_MODEL_FEATURES):
        raise ValueError("Local input must contain exactly the 19 financial fields")
    frame = pd.DataFrame([record], columns=PRIMARY_MODEL_FEATURES)
    X = transform_split(context.preprocessor, engineer_features(frame))
    explanation = explainer.explain(X)
    raw = explanation["raw_probability"]
    if context.calibration["method"] != "identity":
        raise ValueError("Current local consumer requires the frozen identity calibration")
    score, clipped = mapping.transform(raw)
    sources, values = aggregate(explanation["values"], [row["source_feature"] for row in rows])
    decomposition = mapping.decompose(explanation["base"], values, raw,
        calibration_method=context.calibration["method"], tolerance=score_tolerance)
    supported = decomposition["score_point_decomposition_supported"]
    return {"raw_probability": float(raw[0]), "reported_probability": float(raw[0]),
            "raw_margin": float(explanation["raw_margin"][0]), "shap_base_margin": float(explanation["base"][0]),
            "internal_risk_score": float(score[0]), "display_score": int(round(float(score[0]))),
            "score_version": mapping.version, "calibration_method": context.calibration["method"],
            "calibration_version": context.calibration["calibration_version"],
            "model_version": context.model_manifest["model_version"],
            "probability_clipped_for_score": bool(clipped[0]), "score_point_decomposition_supported": supported,
            "score_base_value": float(decomposition["score_base_value"][0]) if supported else None,
            "source_contributions": [{"source_feature": name, "shap_margin": float(value),
                **({"score_points": float(-mapping.factor * value)} if supported else {})}
                for name, value in zip(sources, values[0])],
            "drivers": reason_codes(sources, values[0], top_k=top_k, score_factor=mapping.factor if supported else None)}


def synthetic_records():
    # Fabricated valid inputs only; never copied from customer rows or examples.
    base = {"credit_limit": 200000, **{name: -1 for name in REPAYMENT_COLUMNS},
            **{name: 20000 for name in BILL_COLUMNS}, **{name: 20000 for name in PAYMENT_COLUMNS}}
    return {"synthetic_regular_payments": base,
            "synthetic_recent_delay": {**base, REPAYMENT_COLUMNS[0]: 2, PAYMENT_COLUMNS[0]: 0},
            "synthetic_larger_statements": {**base, **{name: 180000 for name in BILL_COLUMNS}}}
