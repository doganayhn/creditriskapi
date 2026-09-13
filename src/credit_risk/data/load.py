"""Read the original XLS without guessing headers or coercing corrupt cells."""

from pathlib import Path

import pandas as pd
import xlrd

from credit_risk.data.schema import DataSchemaError, canonicalize, column_mapping


def load_source(path: str | Path) -> pd.DataFrame:
    """Validate the two original header rows and return canonical customer records."""
    try:
        book = xlrd.open_workbook(str(path), on_demand=True)
    except (OSError, xlrd.XLRDError) as exc:
        raise DataSchemaError(f"Cannot read source XLS {path}: {exc}") from exc
    try:
        if book.sheet_names() != ["Data"]:
            raise DataSchemaError("Expected exactly one worksheet named Data")
        sheet = book.sheet_by_name("Data")
        if sheet.nrows < 3 or sheet.ncols != 25:
            raise DataSchemaError("Expected two header rows and data with exactly 25 columns")
        artifacts = [""] + [f"X{i}" for i in range(1, 24)] + ["Y"]
        if sheet.row_values(0) != artifacts:
            raise DataSchemaError("Unexpected first header row; refusing to guess skipped rows")
        headers = sheet.row_values(1)
        if headers != list(column_mapping()):
            raise DataSchemaError(f"Unexpected source columns in second header row: {headers}")
        records = []
        for row in range(2, sheet.nrows):
            values = []
            for col, cell in enumerate(sheet.row(row)):
                if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    values.append(None)
                elif cell.ctype == xlrd.XL_CELL_NUMBER:
                    values.append(cell.value)
                else:
                    raise DataSchemaError(f"Non-numeric cell at Excel row {row + 1}, column {headers[col]}; no coercion applied")
            records.append(values)
        # dtype=float retains genuine blank cells as null, even for entirely blank columns.
        return canonicalize(pd.DataFrame(records, columns=headers, dtype=float))
    finally:
        book.release_resources()
