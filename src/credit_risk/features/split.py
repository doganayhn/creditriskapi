"""Deterministic stratified random splitting, never temporal validation."""

import pandas as pd
from sklearn.model_selection import train_test_split

from credit_risk.config import SplitConfig
from credit_risk.data.schema import DataSchemaError, validate_frame
from credit_risk.data.source import TARGET
from credit_risk.features.definitions import IDENTIFIER


def split_dataset(canonical: pd.DataFrame, split: SplitConfig, random_seed: int) -> dict[str, pd.DataFrame]:
    """Sort by ID, then split twice with the same explicit centralized seed."""
    validate_frame(canonical)
    if type(random_seed) is not int or not 0 <= random_seed <= 2**32 - 1:
        raise ValueError("random_seed must be an unsigned 32-bit integer")
    if canonical[IDENTIFIER].isna().any() or canonical[IDENTIFIER].duplicated().any():
        raise DataSchemaError("Split requires non-null unique customer IDs; investigate duplicates")
    if canonical[TARGET].nunique() != 2:
        raise DataSchemaError("Stratification requires both target classes")
    ordered = canonical.sort_values(IDENTIFIER, kind="stable").reset_index(drop=True)
    temporary_fraction = split.validation_fraction + split.test_fraction
    try:
        train, temporary = train_test_split(
            ordered, test_size=temporary_fraction, random_state=random_seed, stratify=ordered[TARGET]
        )
        validation, test = train_test_split(
            temporary, test_size=split.test_fraction / temporary_fraction,
            random_state=random_seed, stratify=temporary[TARGET],
        )
    except ValueError as exc:
        raise DataSchemaError(f"Cannot create the requested stratified partitions: {exc}") from exc
    partitions = {"train": train.copy(), "validation": validation.copy(), "test": test.copy()}
    ids = pd.concat([part[IDENTIFIER] for part in partitions.values()], ignore_index=True)
    if len(ids) != len(ordered) or ids.duplicated().any() or set(ids) != set(ordered[IDENTIFIER]):
        raise DataSchemaError("Split integrity failed: overlap or incomplete coverage")
    if any(part[TARGET].nunique() != 2 for part in partitions.values()):
        raise DataSchemaError("Each split must contain both target classes; insufficient class counts")
    return partitions
