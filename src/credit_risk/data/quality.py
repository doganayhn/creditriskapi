"""Descriptive quality profiling only: never fit, recode, drop or transform records."""

import argparse
import json
from pathlib import Path

import pandas as pd

from credit_risk.config import load_config
from credit_risk.data.download import AcquisitionError, verify_raw, write_json
from credit_risk.data.load import load_source
from credit_risk.data.schema import COLUMNS, DataSchemaError, validate_frame
from credit_risk.data.source import RAW_FILENAME, TARGET


def _number(value) -> float | None:
    return None if pd.isna(value) else float(value)


def profile(frame: pd.DataFrame) -> dict:
    """Return aggregate JSON-safe measurements; IQR flags are descriptive, not invalidity."""
    validate_frame(frame)
    rows = len(frame)
    columns, missingness, unexpected, warnings = {}, {}, {}, []
    for col in COLUMNS:
        values = frame[col.name]
        missing = int(values.isna().sum())
        present = rows - missing
        q = values.quantile([.01, .25, .50, .75, .99])
        lower = q.loc[.25] - 1.5 * (q.loc[.75] - q.loc[.25])
        upper = q.loc[.75] + 1.5 * (q.loc[.75] - q.loc[.25])
        missingness[col.name] = {"count": missing, "percentage": missing / rows * 100}
        summary = {
            "dtype": str(values.dtype),
            "missing_count": missing,
            "missing_percentage": missing / rows * 100,
            "unique_count": int(values.nunique(dropna=True)),
            "min": _number(values.min()), "max": _number(values.max()),
            "mean": _number(values.mean()) if present else None,
            "median": _number(values.median()) if present else None,
            "std_sample": _number(values.std(ddof=1)) if present > 1 else None,
            "quantiles": {str(p): _number(v) for p, v in q.items()},
            "iqr_lower_fence": _number(lower), "iqr_upper_fence": _number(upper),
            "iqr_outlier_count": int(((values < lower) | (values > upper)).sum()),
        }
        if missing:
            warnings.append({"column": col.name, "check": "true_nulls", "count": missing})
        if col.codes is not None:
            counts = values.value_counts(dropna=True).sort_index()
            undocumented = {str(int(k)): int(v) for k, v in counts.items() if k not in col.codes}
            summary.update({
                "documented_codes": list(col.codes),
                "observed_codes": [int(k) for k in counts.index],
                "value_counts": {str(int(k)): int(v) for k, v in counts.items()},
                "undocumented_codes": undocumented,
            })
            if undocumented:
                unexpected[col.name] = undocumented
                warnings.append({"column": col.name, "check": "undocumented_codes", "counts": undocumented, "action": "Report and retain; meanings require investigation"})
        if col.name in ("age", "credit_limit"):
            summary["nonpositive_count"] = int((values <= 0).sum())
            if summary["nonpositive_count"]:
                warnings.append({"column": col.name, "check": "nonpositive", "count": summary["nonpositive_count"]})
        if col.name.startswith(("bill_amount_", "payment_amount_")):
            summary["negative_count"] = int((values < 0).sum())
            if summary["negative_count"]:
                warnings.append({"column": col.name, "check": "negative_amount", "count": summary["negative_count"], "action": "Retain; bill credits/overpayments are possible but not verified"})
        if col.codes is None and col.name != "customer_id" and summary["iqr_outlier_count"]:
            warnings.append({"column": col.name, "check": "outside_1.5_IQR", "count": summary["iqr_outlier_count"], "action": "Descriptive flag only; no upper-age rejection or clipping"})
        columns[col.name] = summary
    ids = frame["customer_id"]
    duplicate_ids = int(ids.dropna().duplicated().sum())
    exact = int(frame.duplicated().sum())
    if duplicate_ids:
        warnings.append({"column": "customer_id", "check": "duplicate_ids", "count": duplicate_ids})
    if exact:
        warnings.append({"column": None, "check": "exact_duplicate_rows", "count": exact})
    return {
        "rows": rows, "columns": len(frame.columns),
        "memory_usage_bytes": int(frame.memory_usage(index=True, deep=True).sum()),
        "target": {"name": TARGET, "negative_count": int((frame[TARGET] == 0).sum()), "positive_count": int((frame[TARGET] == 1).sum()), "positive_rate": float(frame[TARGET].mean())},
        "duplicates": {"exact_rows": exact, "duplicate_ids": duplicate_ids, "definition": "Occurrences after the first; exact rows include ID and target; null IDs excluded from duplicate-ID count"},
        "identifier": {"missing_count": int(ids.isna().sum()), "unique_nonnull_count": int(ids.nunique()), "all_present_and_unique": bool(ids.notna().all() and ids.is_unique)},
        "missingness": missingness, "column_profiles": columns,
        "unexpected_codes": unexpected, "domain_warnings": warnings,
        "methodology": "Sample standard deviation (ddof=1); pandas linear quantiles; 1.5 IQR flags only; no recoding, imputation, dropping, winsorization, splitting or feature derivation",
    }


def run_quality(project_root: str | Path) -> dict:
    """Profile local verified raw bytes without performing any network request."""
    config = load_config(project_root)
    if config.target_column != TARGET:
        raise DataSchemaError(f"This dataset requires configured target {TARGET}")
    raw_path = config.paths.raw / RAW_FILENAME
    digest = verify_raw(raw_path)
    summary = profile(load_source(raw_path))
    summary["raw_sha256"] = digest
    summary["profiler_version"] = "phase_2_v1"
    summary["pandas_version"] = pd.__version__
    write_json(config.paths.metadata / "data_quality_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = run_quality(args.project_root)
    except (AcquisitionError, DataSchemaError, OSError, ValueError) as exc:
        parser.exit(1, f"Quality profiling failed: {exc}\n")
    print(json.dumps({"rows": result["rows"], "columns": result["columns"], "target": result["target"], "warning_count": len(result["domain_warnings"])}, indent=2))


if __name__ == "__main__":
    main()
