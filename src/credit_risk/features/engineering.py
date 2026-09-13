"""Stateless, target-free financial feature engineering."""

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from credit_risk.data.schema import DataSchemaError
from credit_risk.features.definitions import (
    BILL_COLUMNS, MODEL_INPUT_FEATURES, MONTHS, NUMERIC_FEATURES,
    PAYMENT_COLUMNS, PRIMARY_MODEL_FEATURES, REPAYMENT_COLUMNS,
)


def select_primary_features(canonical: pd.DataFrame) -> pd.DataFrame:
    """Explicit allowlist; ID, target and demographics cannot propagate to X."""
    if canonical.columns.duplicated().any():
        raise DataSchemaError("Duplicate canonical columns")
    missing = set(PRIMARY_MODEL_FEATURES) - set(canonical.columns)
    if missing:
        raise DataSchemaError(f"Missing financial fields: {sorted(missing)}")
    return canonical.loc[:, list(PRIMARY_MODEL_FEATURES)].copy()


def engineer_features(financial: pd.DataFrame) -> pd.DataFrame:
    """Accept only the 19 raw financial fields; return 39 numeric + 6 categorical inputs."""
    if financial.empty or list(financial.columns) != list(PRIMARY_MODEL_FEATURES):
        raise DataSchemaError("Engineering requires exactly the ordered primary financial allowlist")
    for name in PRIMARY_MODEL_FEATURES:
        if not is_numeric_dtype(financial[name].dtype) or is_bool_dtype(financial[name].dtype):
            raise DataSchemaError(f"{name} must be numeric; no string/boolean coercion")
    raw = financial.astype(float).copy()
    if np.isinf(raw.to_numpy()).any():
        raise DataSchemaError("Infinite financial input")
    limit = raw["credit_limit"]
    if limit.isna().any() or (limit <= 0).any():
        raise DataSchemaError("credit_limit must be present and strictly positive")
    statuses = raw.loc[:, list(REPAYMENT_COLUMNS)]
    observed = statuses.to_numpy()
    valid = np.isnan(observed) | np.isin(observed, [-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    if not valid.all():
        raise DataSchemaError("Repayment code outside source-documented/observed domain; investigate before feature preparation")
    output = raw.copy()
    bills, payments = raw.loc[:, list(BILL_COLUMNS)], raw.loc[:, list(PAYMENT_COLUMNS)]
    output["bill_amount_mean"] = bills.mean(axis=1, skipna=False)
    output["bill_amount_std"] = bills.std(axis=1, skipna=False, ddof=0)
    output["bill_amount_min"] = bills.min(axis=1, skipna=False)
    output["bill_amount_max"] = bills.max(axis=1, skipna=False)
    output["payment_amount_mean"] = payments.mean(axis=1, skipna=False)
    output["payment_amount_sum"] = payments.sum(axis=1, min_count=6)
    output["payment_amount_max"] = payments.max(axis=1, skipna=False)
    for family in ("bill", "payment"):
        ratios = []
        for month in MONTHS:
            name = f"{family}_to_limit_{month}"
            output[name] = raw[f"{family}_amount_{month}"] / limit
            ratios.append(name)
        output[f"{family}_to_limit_mean"] = output[ratios].mean(axis=1, skipna=False)
        output[f"{family}_to_limit_max"] = output[ratios].max(axis=1, skipna=False)
    complete = statuses.notna().all(axis=1)
    positive = statuses > 0
    output["months_with_documented_delay"] = positive.sum(axis=1).where(complete)
    output["max_documented_delay"] = statuses.where(positive, 0).max(axis=1).where(complete)
    output["recent_documented_delay_flag"] = positive.iloc[:, 0].astype(float).where(statuses.iloc[:, 0].notna())
    for name in REPAYMENT_COLUMNS:
        output[name] = raw[name].map(lambda value: np.nan if pd.isna(value) else f"status_{int(value)}")
    if np.isinf(output.loc[:, list(NUMERIC_FEATURES)].to_numpy(dtype=float)).any():
        raise DataSchemaError("Financial feature arithmetic overflowed; no clipping applied")
    return output.loc[:, list(MODEL_INPUT_FEATURES)].copy()
