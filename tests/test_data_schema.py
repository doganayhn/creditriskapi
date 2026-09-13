from dataclasses import replace

import pandas as pd
import pytest

from credit_risk.data.schema import COLUMNS, DataSchemaError, canonicalize, column_mapping, validate_target


def test_explicit_mapping(source_frame):
    mapping = column_mapping()
    assert len(mapping) == len(set(mapping.values())) == 25
    assert mapping["ID"] == "customer_id"
    assert mapping["default payment next month"] == "default_next_month"
    assert mapping["PAY_0"] == "repayment_status_2005_09"
    assert mapping["PAY_2"] == "repayment_status_2005_08"
    assert mapping["PAY_AMT6"] == "payment_amount_2005_04"
    frame = canonicalize(source_frame)
    assert frame["customer_id"].tolist() == [1, 2, 3, 4]
    assert frame["default_next_month"].tolist() == [0, 0, 0, 1]
    assert all(str(dtype) == "Int64" for dtype in frame.dtypes)
    assert "ID" in source_frame  # Caller input was not changed.


def test_missing_column(source_frame):
    with pytest.raises(DataSchemaError, match="missing=.*AGE"):
        canonicalize(source_frame.drop(columns="AGE"))


def test_unexpected_column(source_frame):
    source_frame["extra"] = 1
    with pytest.raises(DataSchemaError, match="unexpected=.*extra"):
        canonicalize(source_frame)


def test_duplicate_source_columns(source_frame):
    source_frame.columns = ["ID"] * 25
    with pytest.raises(DataSchemaError, match="Duplicate source"):
        canonicalize(source_frame)


@pytest.mark.parametrize("field", ["source", "name"])
def test_duplicate_mapping(field):
    broken = (COLUMNS[0], replace(COLUMNS[1], **{field: getattr(COLUMNS[0], field)}))
    with pytest.raises(DataSchemaError, match="Duplicate"):
        column_mapping(broken)


@pytest.mark.parametrize("value", ["not a number", "21", 1.5, float("inf"), True])
def test_corrupted_values_are_not_coerced(source_frame, value):
    source_frame["AGE"] = pd.Series([value] * len(source_frame))
    with pytest.raises(DataSchemaError):
        canonicalize(source_frame)


def test_empty_source(source_frame):
    with pytest.raises(DataSchemaError, match="no records"):
        canonicalize(source_frame.iloc[:0])


def test_valid_target(canonical_frame):
    validate_target(canonical_frame)


def test_missing_target(canonical_frame):
    with pytest.raises(DataSchemaError, match="Missing target column"):
        validate_target(canonical_frame.drop(columns="default_next_month"))


@pytest.mark.parametrize("value", [None, 2, -1])
def test_invalid_target_value(canonical_frame, value):
    canonical_frame.loc[0, "default_next_month"] = value
    with pytest.raises(DataSchemaError):
        validate_target(canonical_frame)
