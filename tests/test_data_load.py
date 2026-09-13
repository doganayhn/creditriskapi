from pathlib import Path
from unittest.mock import MagicMock

import pytest
import xlrd

from credit_risk.data.load import load_source
from credit_risk.data.schema import DataSchemaError, column_mapping


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_credit.xls"


def test_valid_xls_fixture():
    result = load_source(FIXTURE)
    assert result.shape == (4, 25)
    assert result["customer_id"].tolist() == [1, 2, 3, 4]
    assert result["default_next_month"].tolist() == [0, 0, 0, 1]


@pytest.fixture
def workbook(monkeypatch):
    book = MagicMock()
    book.sheet_names.return_value = ["Data"]
    sheet = book.sheet_by_name.return_value
    sheet.nrows, sheet.ncols = 3, 25
    sheet.row_values.side_effect = lambda row: ([""] + [f"X{i}" for i in range(1, 24)] + ["Y"]) if row == 0 else list(column_mapping())
    sheet.row.return_value = [xlrd.sheet.Cell(xlrd.XL_CELL_NUMBER, 0)] * 25
    monkeypatch.setattr("credit_risk.data.load.xlrd.open_workbook", lambda *a, **kw: book)
    return book, sheet


@pytest.mark.parametrize("defect", ["sheet", "width", "no_data", "header", "duplicate", "string_cell", "error_cell"])
def test_malformed_workbook(workbook, defect):
    book, sheet = workbook
    if defect == "sheet":
        book.sheet_names.return_value = ["unexpected"]
    elif defect == "width":
        sheet.ncols = 24
    elif defect == "no_data":
        sheet.nrows = 2
    elif defect == "header":
        sheet.row_values.side_effect = lambda row: ["bad"] * 25
    elif defect == "duplicate":
        artifact = [""] + [f"X{i}" for i in range(1, 24)] + ["Y"]
        sheet.row_values.side_effect = lambda row: artifact if row == 0 else ["ID"] * 25
    else:
        kind = xlrd.XL_CELL_TEXT if defect == "string_cell" else xlrd.XL_CELL_ERROR
        sheet.row.return_value = [xlrd.sheet.Cell(kind, "invalid")] * 25
    with pytest.raises(DataSchemaError):
        load_source("synthetic.xls")
    book.release_resources.assert_called_once()


def test_null_non_target_retained(workbook):
    _, sheet = workbook
    cells = [xlrd.sheet.Cell(xlrd.XL_CELL_NUMBER, 0)] * 25
    cells[5] = xlrd.sheet.Cell(xlrd.XL_CELL_EMPTY, "")
    sheet.row.return_value = cells
    assert load_source("synthetic.xls")["age"].isna().sum() == 1


def test_missing_file(tmp_path):
    with pytest.raises(DataSchemaError, match="Cannot read"):
        load_source(tmp_path / "absent.xls")


def test_corrupt_xls(tmp_path):
    path = tmp_path / "corrupt.xls"
    path.write_bytes(b"not an Excel file")
    with pytest.raises(DataSchemaError, match="Cannot read"):
        load_source(path)
