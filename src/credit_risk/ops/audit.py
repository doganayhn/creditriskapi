"""Check audit rows in memory; return counts only, never offending records."""

import math


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def audit_rows(rows, expected):
    counts = dict.fromkeys(("rows_checked", "invalid_rows", "version_mismatch_rows", "probability_violation_rows",
        "test_flag_violation_rows", "explanation_contract_violation_rows", "numeric_violation_rows",
        "endpoint_violation_rows", "duplicate_request_ids"), 0)
    seen = set()
    for row in rows:
        counts["rows_checked"] += 1
        flags = {
            "version_mismatch_rows": any(row.get(k) != v for k, v in expected.items() if k != "explainability_version"),
            "probability_violation_rows": any(not finite(row.get(k)) or not 0 <= row[k] <= 1 for k in ("raw_probability", "reported_probability")),
            "test_flag_violation_rows": row.get("test_set_evaluated") is not False,
            "numeric_violation_rows": any(not finite(row.get(k)) for k in ("internal_risk_score", "raw_margin", "inference_latency_ms")) or (finite(row.get("inference_latency_ms")) and row["inference_latency_ms"] < 0),
            "endpoint_violation_rows": row.get("endpoint_type") not in {"predict", "explain"},
            "duplicate_request_ids": row.get("request_id") is None or row["request_id"] in seen,
        }
        explain = row.get("endpoint_type") == "explain"
        flags["explanation_contract_violation_rows"] = (
            row.get("explanation_requested") is not explain or
            row.get("explainability_version") != (expected["explainability_version"] if explain else None) or
            (explain and not isinstance(row.get("score_point_decomposition_supported"), bool)))
        if expected["calibration_method"] == "identity" and row.get("raw_probability") != row.get("reported_probability"):
            flags["probability_violation_rows"] = True
        counts["invalid_rows"] += int(any(flags.values()))
        for key, failed in flags.items(): counts[key] += int(failed)
        seen.add(row.get("request_id"))
    return {**counts, "valid": counts["invalid_rows"] == 0, "test_set_evaluated": False}
