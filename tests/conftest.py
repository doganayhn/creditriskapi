"""Small synthetic records; no customer-level source data in tests."""

from pathlib import Path

import pandas as pd
import pytest

from credit_risk.data.schema import COLUMNS, canonicalize


@pytest.fixture
def source_frame():
    rows = []
    for i in range(1, 5):
        row = {col.source: 0 for col in COLUMNS}
        row.update(ID=i, LIMIT_BAL=10000 * i, SEX=1, EDUCATION=2, MARRIAGE=1, AGE=20 + i)
        row["default payment next month"] = 1 if i == 4 else 0
        rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture
def canonical_frame(source_frame):
    return canonicalize(source_frame)


@pytest.fixture
def data_project(tmp_path):
    configs = tmp_path / "configs"
    configs.mkdir()
    root = Path(__file__).resolve().parents[1]
    for filename in ("base.yaml", "experiment.yaml"):
        (configs / filename).write_bytes((root / "configs" / filename).read_bytes())
    return tmp_path
