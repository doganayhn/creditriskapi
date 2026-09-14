"""Reuse Phase-3 lineage; aggregate signed local contributions before global magnitude."""

import numpy as np

from credit_risk.features.definitions import EXCLUDED_FIELDS, MODEL_INPUT_FEATURES

AGGREGATION_VERSION = "source_family_signed_sum_v1"


def family(source):
    if source == "credit_limit":
        return "credit_limit"
    for prefix in ("repayment_status", "bill_amount", "payment_amount", "bill_to_limit", "payment_to_limit"):
        if source.startswith(prefix + "_"):
            return prefix
    if source in {"months_with_documented_delay", "max_documented_delay", "recent_documented_delay_flag"}:
        return "delay_summary"
    raise ValueError(f"Unknown financial feature family: {source}")


def lineage(names, trace):
    if len(set(names)) != len(names) or [row["name"] for row in trace] != list(names):
        raise ValueError("Duplicate or misaligned transformed feature lineage")
    rows = []
    for name, row in zip(names, trace):
        source = row["input_feature"]
        if (source not in MODEL_INPUT_FEATURES or not row["canonical_sources"] or
                set(row["canonical_sources"]) & set(EXCLUDED_FIELDS) or
                any(field in name for field in EXCLUDED_FIELDS)):
            raise ValueError("Missing or forbidden explanation lineage")
        rows.append({"name": name, "source_feature": source, "feature_family": family(source),
                     "feature_type": "standardized_numeric" if row["category"] is None else "one_hot_category"})
    return rows


def aggregate(values, labels):
    values = np.asarray(values, dtype=float)
    if values.ndim != 2 or values.shape[1] != len(labels) or not np.isfinite(values).all():
        raise ValueError("Invalid contribution matrix/labels")
    names = sorted(set(labels))
    grouped = np.column_stack([values[:, [i for i, label in enumerate(labels) if label == name]].sum(axis=1)
                               for name in names])
    if not np.allclose(grouped.sum(axis=1), values.sum(axis=1), rtol=0, atol=1e-12):
        raise ValueError("Signed aggregation changed row totals")
    return names, grouped


def importance(values, rows):
    magnitude, signed = np.mean(np.abs(values), axis=0), np.mean(values, axis=0)
    total = float(magnitude.sum())
    output = [{**row, "mean_abs_shap_margin": float(magnitude[i]), "mean_signed_shap_margin": float(signed[i]),
               "normalized_mean_abs_shap": float(magnitude[i] / total) if total else 0.}
              for i, row in enumerate(rows)]
    output.sort(key=lambda row: (-row["mean_abs_shap_margin"], row["name"]))
    return [{**row, "rank": rank} for rank, row in enumerate(output, 1)]


def global_importance(values, rows):
    sources, source_values = aggregate(values, [row["source_feature"] for row in rows])
    families, family_values = aggregate(source_values, [family(source) for source in sources])
    return {"transformed_feature": importance(values, rows),
            "source_feature": importance(source_values, [{"name": name, "feature_family": family(name)} for name in sources]),
            "feature_family": importance(family_values, [{"name": name} for name in families])}, sources, source_values, families, family_values
