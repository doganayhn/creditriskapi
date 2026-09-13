"""Explicit source-to-canonical schema and source-documented category domains."""

from dataclasses import dataclass
from collections.abc import Sequence
import math

import pandas as pd
from pandas.api.types import is_numeric_dtype, is_bool_dtype

from credit_risk.data.source import ORIGINAL_TARGET, TARGET


class DataSchemaError(ValueError):
    """The input does not match the verified physical or target schema."""


@dataclass(frozen=True)
class Column:
    source: str
    name: str
    meaning: str
    role: str = "CANDIDATE_FEATURE"
    eligibility: str = "CANDIDATE_FEATURE"
    sensitive: bool = False
    codes: tuple[int, ...] | None = None


MONTHS = ("2005_09", "2005_08", "2005_07", "2005_06", "2005_05", "2005_04")
COLUMNS = (
    Column("ID", "customer_id", "Source customer identifier", "IDENTIFIER", "EXCLUDED_IDENTIFIER"),
    Column("LIMIT_BAL", "credit_limit", "Given credit in NT dollars, including supplementary family credit"),
    Column("SEX", "sex", "Source sex code: 1 male, 2 female", eligibility="DEMOGRAPHIC_REVIEW_REQUIRED", sensitive=True, codes=(1, 2)),
    Column("EDUCATION", "education", "1 graduate school, 2 university, 3 high school, 4 others", eligibility="DEMOGRAPHIC_REVIEW_REQUIRED", sensitive=True, codes=(1, 2, 3, 4)),
    Column("MARRIAGE", "marital_status", "1 married, 2 single, 3 others", eligibility="DEMOGRAPHIC_REVIEW_REQUIRED", sensitive=True, codes=(1, 2, 3)),
    Column("AGE", "age", "Age in years", eligibility="DEMOGRAPHIC_REVIEW_REQUIRED", sensitive=True),
) + tuple(
    Column(source, f"repayment_status_{month}", f"Repayment status for {month.replace('_', '-')}; -1 duly paid; 1–8 months delay; 9 nine months or more", eligibility="REQUIRES_DOMAIN_REVIEW", codes=(-1, 1, 2, 3, 4, 5, 6, 7, 8, 9))
    for source, month in zip(("PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"), MONTHS)
) + tuple(
    Column(f"BILL_AMT{i}", f"bill_amount_{month}", f"Bill statement amount in NT dollars for {month.replace('_', '-')}", eligibility="REQUIRES_DOMAIN_REVIEW")
    for i, month in enumerate(MONTHS, 1)
) + tuple(
    Column(f"PAY_AMT{i}", f"payment_amount_{month}", f"Amount paid in NT dollars during {month.replace('_', '-')}")
    for i, month in enumerate(MONTHS, 1)
) + (Column(ORIGINAL_TARGET, TARGET, "Default payment next month: 1 yes, 0 no", "TARGET", "EXCLUDED_TARGET", codes=(0, 1)),)


def column_mapping(columns: Sequence[Column] = COLUMNS) -> dict[str, str]:
    """Reject ambiguous source or canonical names before constructing a mapping."""
    sources = [col.source for col in columns]
    names = [col.name for col in columns]
    if len(set(sources)) != len(sources) or len(set(names)) != len(names):
        raise DataSchemaError("Duplicate source or canonical column name in mapping")
    return dict(zip(sources, names))


def validate_target(frame: pd.DataFrame) -> None:
    """Require present, non-null, numeric binary outcome labels."""
    if TARGET not in frame:
        raise DataSchemaError(f"Missing target column: {TARGET}")
    target = frame[TARGET]
    if target.isna().any():
        raise DataSchemaError(f"{TARGET} contains missing labels")
    if is_bool_dtype(target.dtype) or not is_numeric_dtype(target.dtype) or not target.isin([0, 1]).all():
        raise DataSchemaError(f"{TARGET} must contain only numeric labels 0 and 1")


def validate_frame(frame: pd.DataFrame) -> None:
    """Validate shape and integral numeric cells; retain non-target nulls for profiling."""
    expected = list(column_mapping().values())
    if frame.columns.duplicated().any() or list(frame.columns) != expected:
        raise DataSchemaError("Canonical schema must have all 25 unique columns in documented order")
    if frame.empty:
        raise DataSchemaError("Dataset contains no records")
    for name in expected:
        values = frame[name].dropna()
        if is_bool_dtype(frame[name].dtype) or not is_numeric_dtype(frame[name].dtype):
            raise DataSchemaError(f"{name}: expected numeric cells, not strings/booleans")
        if not values.map(lambda value: math.isfinite(value) and value == int(value)).all():
            raise DataSchemaError(f"{name}: expected finite integral values; no coercion applied")
    validate_target(frame)


def canonicalize(source: pd.DataFrame) -> pd.DataFrame:
    """Rename and represent verified integer values without recoding or filtering rows."""
    mapping = column_mapping()
    if source.columns.duplicated().any():
        raise DataSchemaError("Duplicate source column names")
    missing, extra = set(mapping) - set(source.columns), set(source.columns) - set(mapping)
    if missing or extra:
        raise DataSchemaError(f"Source schema mismatch; missing={sorted(missing)}, unexpected={sorted(extra)}")
    frame = source.loc[:, list(mapping)].rename(columns=mapping).copy()
    validate_frame(frame)
    try:
        return frame.astype("Int64")
    except (TypeError, ValueError, OverflowError) as exc:
        raise DataSchemaError("Numeric values cannot be represented as nullable int64") from exc
