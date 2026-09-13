"""Versioned, immutable financial feature policy and formulas."""

from dataclasses import dataclass

from credit_risk.data.schema import MONTHS
from credit_risk.data.source import TARGET

IDENTIFIER = "customer_id"
FAIRNESS_REVIEW_FIELDS = ("sex", "age", "education", "marital_status")
EXCLUDED_FIELDS = (IDENTIFIER, TARGET) + FAIRNESS_REVIEW_FIELDS
REPAYMENT_COLUMNS = tuple(f"repayment_status_{month}" for month in MONTHS)
BILL_COLUMNS = tuple(f"bill_amount_{month}" for month in MONTHS)
PAYMENT_COLUMNS = tuple(f"payment_amount_{month}" for month in MONTHS)
RAW_NUMERIC_FEATURES = ("credit_limit",) + BILL_COLUMNS + PAYMENT_COLUMNS
PRIMARY_MODEL_FEATURES = ("credit_limit",) + REPAYMENT_COLUMNS + BILL_COLUMNS + PAYMENT_COLUMNS
FEATURE_VERSION = "financial_features_v1"
PREPROCESSING_VERSION = "train_median_scale_onehot_v1"
SPLIT_VERSION = "sorted_id_two_stage_stratified_v1"


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    formula: str
    sources: tuple[str, ...]
    interpretation: str
    edge_cases: str


AGGREGATE_EDGE = "Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping."
RATIO_EDGE = "Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained."
ENGINEERED_FEATURES = tuple(
    FeatureDefinition(f"bill_amount_{stat}", f"{stat}(six bill amounts)" + ("; population std, ddof=0" if stat == "std" else ""), BILL_COLUMNS, "Six-month bill-statement level or dispersion", AGGREGATE_EDGE)
    for stat in ("mean", "std", "min", "max")
) + tuple(
    FeatureDefinition(f"payment_amount_{stat}", f"{stat}(six payment amounts)", PAYMENT_COLUMNS, "Six-month payment amount summary", AGGREGATE_EDGE)
    for stat in ("mean", "sum", "max")
) + tuple(
    FeatureDefinition(f"{family}_to_limit_{month}", f"{family}_amount_{month} / credit_limit", (f"{family}_amount_{month}", "credit_limit"), "Statement/payment amount relative to given credit; not regulatory utilization", RATIO_EDGE)
    for family in ("bill", "payment") for month in MONTHS
) + tuple(
    FeatureDefinition(f"{family}_to_limit_{stat}", f"{stat}(six {family}_amount_month / credit_limit ratios)", ("credit_limit",) + (BILL_COLUMNS if family == "bill" else PAYMENT_COLUMNS), "Six-month normalized amount summary", RATIO_EDGE + " " + AGGREGATE_EDGE)
    for family in ("bill", "payment") for stat in ("mean", "max")
) + (
    FeatureDefinition("months_with_documented_delay", "sum(status > 0 over six months)", REPAYMENT_COLUMNS, "Number of recorded history months with positive documented delay", "NaN if any status missing; -2/-1/0 contribute no positive-delay evidence, not a no-risk meaning."),
    FeatureDefinition("max_documented_delay", "max(positive statuses), or 0 if none", REPAYMENT_COLUMNS, "Largest documented positive delay level; code 9 is top-coded at nine or more months", "NaN if any status missing; zero means no observed positive code, not proven absence of arrears."),
    FeatureDefinition("recent_documented_delay_flag", "1 if repayment_status_2005_09 > 0 else 0", (REPAYMENT_COLUMNS[0],), "Positive documented delay in the most recent source month", "NaN if most recent status missing; no interpretation assigned to -2/0."),
)
NUMERIC_FEATURES = RAW_NUMERIC_FEATURES + tuple(feature.name for feature in ENGINEERED_FEATURES)
CATEGORICAL_FEATURES = REPAYMENT_COLUMNS
MODEL_INPUT_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
