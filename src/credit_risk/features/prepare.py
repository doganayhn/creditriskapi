"""Prepare stratified datasets and train-fitted preprocessing; never train a predictor."""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
import scipy
import sklearn
from sklearn.pipeline import Pipeline

from credit_risk.config import SplitConfig, load_config
from credit_risk.data.download import AcquisitionError, sha256_file, verify_raw, write_json
from credit_risk.data.load import load_source
from credit_risk.data.schema import DataSchemaError, column_mapping
from credit_risk.data.source import DOI, RAW_FILENAME, TARGET
from credit_risk.features.definitions import (
    CATEGORICAL_FEATURES, ENGINEERED_FEATURES, EXCLUDED_FIELDS, FAIRNESS_REVIEW_FIELDS,
    FEATURE_VERSION, IDENTIFIER, NUMERIC_FEATURES, PREPROCESSING_VERSION,
    PRIMARY_MODEL_FEATURES, SPLIT_VERSION,
)
from credit_risk.features.engineering import engineer_features, select_primary_features
from credit_risk.features.preprocessing import (
    fit_preprocessor, load_preprocessor, save_preprocessor, transform_split,
)
from credit_risk.features.split import split_dataset


@dataclass
class PreparedSplit:
    X: sparse.csr_matrix
    y: pd.Series
    review: pd.DataFrame


@dataclass
class PreparedDataset:
    partitions: dict[str, PreparedSplit]
    preprocessor: Pipeline
    feature_names: tuple[str, ...]


def prepare_dataset(canonical: pd.DataFrame, split: SplitConfig, random_seed: int) -> PreparedDataset:
    """Split first; fit exactly once on train; targets/review remain outside the transformer."""
    raw_splits = split_dataset(canonical, split, random_seed)
    features = {name: engineer_features(select_primary_features(frame)) for name, frame in raw_splits.items()}
    preprocessor = fit_preprocessor(features["train"])
    partitions = {}
    for name, frame in raw_splits.items():
        y = frame[TARGET].copy()
        if y.isna().any() or not y.isin([0, 1]).all():
            raise DataSchemaError("Target arrays must remain complete and binary")
        partitions[name] = PreparedSplit(
            X=transform_split(preprocessor, features[name]),
            y=y,
            review=frame.loc[:, [IDENTIFIER, *FAIRNESS_REVIEW_FIELDS]].copy(),
        )
    return PreparedDataset(partitions, preprocessor, tuple(preprocessor.get_feature_names_out()))


def verify_dataset_manifest(root: Path) -> tuple[pd.DataFrame, str]:
    """Require agreement among the Phase-2 manifest, pinned raw bytes and loaded schema."""
    config = load_config(root)
    raw = config.paths.raw / RAW_FILENAME
    digest = verify_raw(raw)
    path = config.paths.metadata / "dataset_manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DataSchemaError("Phase-2 dataset manifest is missing or unreadable") from exc
    required = {
        "sha256": digest, "raw_filename": RAW_FILENAME, "file_size_bytes": raw.stat().st_size,
        "uci_dataset_id": 350, "doi": DOI, "canonical_target_column": TARGET,
        "original_target_column": "default payment next month", "target_positive_value": 1,
        "target_negative_value": 0, "source_to_canonical": column_mapping(),
        "column_count_raw": 25, "column_count_canonical": 25,
    }
    if not isinstance(manifest, dict) or any(manifest.get(key) != value for key, value in required.items()):
        raise DataSchemaError("Phase-2 manifest identity/schema disagrees with the verified dataset")
    canonical = load_source(raw)
    if manifest.get("row_count") != len(canonical):
        raise DataSchemaError("Manifest row count disagrees with loaded data")
    return canonical, digest


def transformed_trace(preprocessor: Pipeline) -> list[dict]:
    """Map every final encoded column to canonical inputs and original source fields."""
    reverse_mapping = {value: key for key, value in column_mapping().items()}
    engineered = {feature.name: feature for feature in ENGINEERED_FEATURES}
    trace = []
    for name in NUMERIC_FEATURES:
        sources = engineered[name].sources if name in engineered else (name,)
        trace.append({"name": f"numeric__{name}", "input_feature": name, "category": None,
                      "canonical_sources": list(sources), "source_columns": [reverse_mapping[s] for s in sources]})
    encoder = preprocessor.named_steps["columns"].named_transformers_["repayment"].named_steps["encoder"]
    for name, categories in zip(CATEGORICAL_FEATURES, encoder.categories_):
        for category in categories:
            trace.append({"name": f"repayment__{name}_{category}", "input_feature": name,
                          "category": str(category), "canonical_sources": [name], "source_columns": [reverse_mapping[name]]})
    if [item["name"] for item in trace] != list(preprocessor.get_feature_names_out()):
        raise DataSchemaError("Encoded feature-name trace disagrees with the transformer")
    return trace


def _write_timestamped(path: Path, manifest: dict) -> None:
    """Preserve generation time when regenerated aggregate content is unchanged."""
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(old, dict):
            generated_at = old.pop("generated_at", None)
            if old == manifest and isinstance(generated_at, str):
                manifest["generated_at"] = generated_at
    if "generated_at" not in manifest:
        manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(path, manifest)


def run_preparation(project_root: str | Path) -> dict:
    """Run the verified real-source workflow and write only aggregate metadata to Git paths."""
    root = Path(project_root).resolve()
    config = load_config(root)
    if config.target_column != TARGET:
        raise DataSchemaError(f"Preparation requires target {TARGET}")
    canonical, digest = verify_dataset_manifest(root)
    prepared = prepare_dataset(canonical, config.split, config.random_seed)
    artifact, artifact_hash = save_preprocessor(prepared.preprocessor, config.paths.artifacts / "preprocessing")
    loaded = load_preprocessor(artifact, artifact_hash)
    # Serialization equality is checked on train only; no evaluation or refitting.
    train_review = prepared.partitions["train"].review
    train_rows = canonical.set_index(IDENTIFIER, drop=False).loc[train_review[IDENTIFIER]]
    roundtrip = transform_split(loaded, engineer_features(select_primary_features(train_rows)))
    delta = roundtrip - prepared.partitions["train"].X
    if delta.nnz and not np.allclose(delta.data, 0, rtol=0, atol=1e-12):
        raise DataSchemaError("Preprocessor serialization round-trip changed transformed values")
    split_manifest = {
        "dataset_sha256": digest, "split_strategy": "stratified_random", "split_version": SPLIT_VERSION,
        "random_seed": config.random_seed, **asdict(config.split),
        "identifier_column": IDENTIFIER, "target_column": TARGET,
        "population_rows": len(canonical), "complete_coverage": True, "customer_overlap_count": 0,
        "ordering": "Sort canonical rows by customer_id ascending before two-stage sklearn train_test_split",
        "sklearn_version": sklearn.__version__,
    }
    for name, part in prepared.partitions.items():
        split_manifest.update({f"{name}_rows": len(part.y), f"{name}_positive_count": int(part.y.sum()),
                               f"{name}_negative_count": int((part.y == 0).sum()), f"{name}_positive_rate": float(part.y.mean())})
    feature_manifest = {
        "dataset_sha256": digest, "target": TARGET, "identifier": IDENTIFIER,
        "excluded_from_primary_model": list(EXCLUDED_FIELDS),
        "excluded_demographic_fields": list(FAIRNESS_REVIEW_FIELDS), "fairness_review_fields": list(FAIRNESS_REVIEW_FIELDS),
        "raw_financial_features": list(PRIMARY_MODEL_FEATURES),
        "engineered_features": {feature.name: asdict(feature) for feature in ENGINEERED_FEATURES},
        "numeric_features": list(NUMERIC_FEATURES), "categorical_features": list(CATEGORICAL_FEATURES),
        "repayment_categorical_columns": list(CATEGORICAL_FEATURES),
        "feature_engineering_version": FEATURE_VERSION, "preprocessing_version": PREPROCESSING_VERSION,
        "transformed_feature_names": list(prepared.feature_names),
        "transformed_feature_trace": transformed_trace(prepared.preprocessor),
    }
    preprocessing_manifest = {
        "preprocessing_version": PREPROCESSING_VERSION, "feature_engineering_version": FEATURE_VERSION,
        "dataset_sha256": digest, "split_seed": config.random_seed, "split_version": SPLIT_VERSION,
        "input_numeric_features": list(NUMERIC_FEATURES), "input_categorical_features": list(CATEGORICAL_FEATURES),
        "raw_primary_feature_count": len(PRIMARY_MODEL_FEATURES), "engineered_feature_count": len(ENGINEERED_FEATURES),
        "numeric_feature_count": len(NUMERIC_FEATURES), "categorical_feature_count": len(CATEGORICAL_FEATURES),
        "fitted_train_row_count": len(prepared.partitions["train"].y),
        "transformed_shapes": {name: list(part.X.shape) for name, part in prepared.partitions.items()},
        "finite_matrices": {name: bool(np.isfinite(part.X.data).all()) for name, part in prepared.partitions.items()},
        "final_encoded_feature_count": len(prepared.feature_names), "matrix_format": "scipy.sparse.csr_matrix float64",
        "sklearn_version": sklearn.__version__, "numpy_version": np.__version__, "pandas_version": pd.__version__,
        "scipy_version": scipy.__version__, "joblib_version": joblib.__version__,
        "serialization_artifact_path": artifact.relative_to(root).as_posix(),
        "serialization_sha256": artifact_hash, "serialization_roundtrip_passed": True,
        "numeric_pipeline": "training median imputation then StandardScaler; all-null training columns rejected",
        "categorical_pipeline": "constant status_missing imputation then train-only OneHotEncoder(handle_unknown=ignore)",
        "implementation_sha256": {p.name: sha256_file(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
    }
    write_json(config.paths.metadata / "split_manifest.json", split_manifest)
    write_json(config.paths.metadata / "feature_manifest.json", feature_manifest)
    _write_timestamped(config.paths.metadata / "preprocessing_manifest.json", preprocessing_manifest)
    return {"splits": {name: {"rows": len(part.y), "positive_count": int(part.y.sum()), "positive_rate": float(part.y.mean()), "shape": list(part.X.shape)} for name, part in prepared.partitions.items()},
            "raw_features": len(PRIMARY_MODEL_FEATURES), "engineered_features": len(ENGINEERED_FEATURES),
            "numeric_features": len(NUMERIC_FEATURES), "categorical_features": len(CATEGORICAL_FEATURES),
            "encoded_features": len(prepared.feature_names), "finite_matrices": preprocessing_manifest["finite_matrices"],
            "serialization_roundtrip_passed": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = run_preparation(args.project_root)
    except (AcquisitionError, DataSchemaError, OSError, ValueError) as exc:
        parser.exit(1, f"Dataset preparation failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
