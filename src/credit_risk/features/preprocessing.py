"""Guarded sklearn preprocessing fitted only by the preparation lifecycle's train branch."""

import hashlib
import io
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted

from credit_risk.data.schema import DataSchemaError
from credit_risk.features.definitions import CATEGORICAL_FEATURES, MODEL_INPUT_FEATURES, NUMERIC_FEATURES


class FeatureSchemaGuard(TransformerMixin, BaseEstimator):
    """Reject extra fields (including target), order drift and undefined training medians."""

    def fit(self, X: pd.DataFrame, y=None):
        if y is not None:
            raise DataSchemaError("Preprocessing must never receive target values")
        self._validate(X)
        empty = X.loc[:, list(NUMERIC_FEATURES)].isna().all()
        if empty.any():
            raise DataSchemaError(f"No training median exists for: {empty[empty].index.tolist()}")
        self.feature_names_in_ = np.asarray(MODEL_INPUT_FEATURES, dtype=object)
        self.n_features_in_ = len(MODEL_INPUT_FEATURES)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self)
        self._validate(X)
        return X.copy()

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self)
        return self.feature_names_in_.copy()

    @staticmethod
    def _validate(X: pd.DataFrame) -> None:
        if not isinstance(X, pd.DataFrame) or X.empty or list(X.columns) != list(MODEL_INPUT_FEATURES):
            raise DataSchemaError("Preprocessor accepts only the ordered engineered financial feature schema")
        for name in NUMERIC_FEATURES:
            if not pd.api.types.is_numeric_dtype(X[name].dtype) or pd.api.types.is_bool_dtype(X[name].dtype):
                raise DataSchemaError(f"Non-numeric engineered input: {name}")
        if np.isinf(X.loc[:, list(NUMERIC_FEATURES)].to_numpy(dtype=float, na_value=np.nan)).any():
            raise DataSchemaError("Infinite engineered input")
        for name in CATEGORICAL_FEATURES:
            if not X[name].dropna().map(lambda value: isinstance(value, str) and value.startswith("status_")).all():
                raise DataSchemaError(f"{name} requires literal status tokens or nulls")


def build_preprocessor() -> Pipeline:
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="status_missing", keep_empty_features=True)),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
    ])
    columns = ColumnTransformer(
        [("numeric", numeric, list(NUMERIC_FEATURES)), ("repayment", categorical, list(CATEGORICAL_FEATURES))],
        remainder="drop", sparse_threshold=1.0, verbose_feature_names_out=True,
    )
    return Pipeline([("schema", FeatureSchemaGuard()), ("columns", columns)])


def fit_preprocessor(train_features: pd.DataFrame) -> Pipeline:
    """The caller must pass the training partition only; no target argument exists."""
    return build_preprocessor().fit(train_features)


def transform_split(preprocessor: Pipeline, features: pd.DataFrame) -> sparse.csr_matrix:
    matrix = sparse.csr_matrix(preprocessor.transform(features), dtype=np.float64)
    names = preprocessor.get_feature_names_out()
    if matrix.shape != (len(features), len(names)) or len(set(names)) != len(names):
        raise DataSchemaError("Transformed shape/feature-name integrity failed")
    if not np.isfinite(matrix.data).all():
        raise DataSchemaError("Transformed matrix contains NaN or infinity")
    return matrix


def save_preprocessor(preprocessor: Pipeline, directory: Path) -> tuple[Path, str]:
    """Serialize trusted locally fitted state under a content-addressed ignored path."""
    buffer = io.BytesIO()
    joblib.dump(preprocessor, buffer)
    content = buffer.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"preprocessor_{digest}.joblib"
    if path.exists():
        if path.read_bytes() != content:
            raise DataSchemaError("Existing preprocessing artifact has unexpected bytes")
    else:
        with path.open("xb") as stream:
            stream.write(content)
    return path, digest


def load_preprocessor(path: Path, expected_sha256: str) -> Pipeline:
    """Load only trusted local artifacts; a checksum does not make untrusted pickle safe."""
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise DataSchemaError("Preprocessor artifact checksum mismatch")
    preprocessor = joblib.load(io.BytesIO(content))
    if not isinstance(preprocessor, Pipeline):
        raise DataSchemaError("Expected a fitted preprocessing Pipeline")
    check_is_fitted(preprocessor)
    return preprocessor
