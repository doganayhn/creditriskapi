import json

import pandas as pd
import pytest

from credit_risk.data.quality import profile
from credit_risk.data.schema import DataSchemaError


def test_numeric_summaries_and_no_mutation(canonical_frame):
    before = canonical_frame.copy(deep=True)
    result = profile(canonical_frame)
    assert result["target"]["positive_rate"] == .25
    assert result["target"]["negative_count"] == 3
    assert result["target"]["positive_count"] == 1
    limit = result["column_profiles"]["credit_limit"]
    assert limit["min"] == 10000 and limit["max"] == 40000
    assert limit["mean"] == limit["median"] == 25000
    assert limit["std_sample"] == pytest.approx(12909.944487358056)
    assert limit["quantiles"]["0.25"] == 17500
    pd.testing.assert_frame_equal(before, canonical_frame)
    json.dumps(result, allow_nan=False)


def test_missingness(canonical_frame):
    canonical_frame.loc[0, "age"] = pd.NA
    result = profile(canonical_frame)
    assert result["missingness"]["age"] == {"count": 1, "percentage": 25.0}
    assert result["column_profiles"]["age"]["unique_count"] == 3


def test_duplicates_distinguished(canonical_frame):
    canonical_frame.loc[1, "customer_id"] = 1
    frame = pd.concat([canonical_frame, canonical_frame.iloc[[0]]], ignore_index=True)
    result = profile(frame)
    assert result["duplicates"]["exact_rows"] == 1
    assert result["duplicates"]["duplicate_ids"] == 2
    assert result["identifier"]["all_present_and_unique"] is False


def test_missing_ids_not_counted_as_duplicates(canonical_frame):
    canonical_frame.loc[[0, 1], "customer_id"] = pd.NA
    result = profile(canonical_frame)
    assert result["identifier"]["missing_count"] == 2
    assert result["duplicates"]["duplicate_ids"] == 0


def test_undocumented_codes_and_negative_bills_retained(canonical_frame):
    canonical_frame.loc[0, "education"] = 5
    canonical_frame.loc[1, "marital_status"] = 0
    canonical_frame.loc[0, "bill_amount_2005_09"] = -50
    canonical_frame.loc[0, "repayment_status_2005_09"] = -2
    result = profile(canonical_frame)
    assert result["unexpected_codes"]["education"] == {"5": 1}
    assert result["unexpected_codes"]["marital_status"] == {"0": 1}
    assert result["unexpected_codes"]["repayment_status_2005_09"] == {"-2": 1, "0": 3}
    assert result["column_profiles"]["bill_amount_2005_09"]["negative_count"] == 1
    assert canonical_frame.loc[0, "bill_amount_2005_09"] == -50


def test_nonpositive_and_extreme_numeric_values_only_flagged(canonical_frame):
    canonical_frame.loc[0, "age"] = -1
    canonical_frame.loc[1, "age"] = 150
    canonical_frame.loc[0, "credit_limit"] = 0
    canonical_frame.loc[0, "payment_amount_2005_09"] = -10
    result = profile(canonical_frame)
    assert result["column_profiles"]["age"]["nonpositive_count"] == 1
    assert result["column_profiles"]["age"]["max"] == 150
    assert result["column_profiles"]["credit_limit"]["nonpositive_count"] == 1
    assert result["column_profiles"]["payment_amount_2005_09"]["negative_count"] == 1
    assert len(canonical_frame) == 4


def test_entirely_null_column_and_single_row(canonical_frame):
    frame = canonical_frame.iloc[[0]].copy()
    frame["age"] = pd.Series([pd.NA], dtype="Int64")
    result = profile(frame)
    assert result["column_profiles"]["age"]["mean"] is None
    assert result["column_profiles"]["credit_limit"]["std_sample"] is None
    json.dumps(result, allow_nan=False)


def test_invalid_target_stops_profiling(canonical_frame):
    canonical_frame.loc[0, "default_next_month"] = pd.NA
    with pytest.raises(DataSchemaError, match="missing labels"):
        profile(canonical_frame)
