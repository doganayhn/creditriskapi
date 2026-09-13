"""Run one fixed Logistic Regression baseline; TRAIN fit, TRAIN/VALIDATION diagnostics."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import warnings

import joblib
import numpy as np
from scipy import sparse
import scipy
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.utils.validation import check_is_fitted
from threadpoolctl import threadpool_limits

from credit_risk.config import load_config
from credit_risk.data.download import AcquisitionError, sha256_file, write_json
from credit_risk.data.source import TARGET
from credit_risk.features.definitions import EXCLUDED_FIELDS
from credit_risk.modeling.artifacts import load_model, save_model
from credit_risk.modeling.contract import PHASE3_IDENTITIES, load_modeling_data
from credit_risk.modeling.metrics import (
    REFERENCE_THRESHOLD, binary_target, bootstrap_validation, evaluate, validate_probabilities,
)

MODEL_VERSION = "logistic-baseline-1.0.0"


def build_model() -> LogisticRegression:
    # sklearn 1.8's non-deprecated spelling for L2 is l1_ratio=0.0.
    # LBFGS supports CSR and is deterministic; random_state has no effect on it.
    return LogisticRegression(l1_ratio=0.0, C=1.0, solver="lbfgs", fit_intercept=True,
                              class_weight=None, max_iter=5000, tol=1e-8)


def validate_matrix(X) -> None:
    if not sparse.issparse(X) or X.ndim != 2 or min(X.shape) == 0:
        raise ValueError("Expected a nonempty sparse two-dimensional predictor matrix")
    if not np.isfinite(X.data).all():
        raise ValueError("Predictor matrix contains NaN or infinity")


def fit_baseline(X_train, y_train) -> LogisticRegression:
    validate_matrix(X_train)
    target = binary_target(y_train, X_train.shape[0])
    model = build_model()
    try:
        with warnings.catch_warnings(), threadpool_limits(limits=1):
            warnings.simplefilter("error", ConvergenceWarning)
            model.fit(X_train, target)
    except ConvergenceWarning as exc:
        raise ValueError("Logistic Regression failed to converge; investigate, do not publish") from exc
    if np.any(model.n_iter_ >= model.max_iter):
        raise ValueError("Logistic Regression reached its iteration limit")
    if not np.isfinite(model.coef_).all() or not np.isfinite(model.intercept_).all():
        raise ValueError("Model coefficients/intercept must be finite")
    return model


def raw_probabilities(model, X) -> np.ndarray:
    validate_matrix(X)
    check_is_fitted(model)
    classes = np.asarray(model.classes_)
    if classes.shape != (2,) or set(classes) != {0, 1}:
        raise ValueError("Model classes must be exactly 0 and 1")
    output = np.asarray(model.predict_proba(X))
    if output.shape != (X.shape[0], 2):
        raise ValueError("Probability output shape disagrees with predictor rows")
    return validate_probabilities(output[:, int(np.flatnonzero(classes == 1)[0])], X.shape[0])


def coefficient_table(model, feature_names, trace: list[dict]) -> list[dict]:
    names = list(feature_names)
    if (model.coef_.shape != (1, len(names)) or len(set(names)) != len(names) or
            [item["name"] for item in trace] != names):
        raise ValueError("Coefficient/feature-name alignment failed")
    rows = []
    for name, beta, lineage in zip(names, model.coef_[0], trace):
        if lineage["input_feature"] in EXCLUDED_FIELDS or set(lineage["canonical_sources"]) & set(EXCLUDED_FIELDS):
            raise ValueError("Forbidden field in coefficient lineage")
        if not np.isfinite(beta) or abs(beta) > np.log(np.finfo(float).max):
            raise ValueError("Non-finite coefficient or exponential")
        rows.append({"transformed_feature_name": name, "source_feature": lineage["input_feature"],
                     "canonical_sources": lineage["canonical_sources"], "source_columns": lineage["source_columns"],
                     "feature_type": "standardized_numeric" if lineage["category"] is None else "one_hot_category",
                     "coefficient": float(beta), "abs_coefficient": float(abs(beta)),
                     "exp_coefficient": float(np.exp(beta)),
                     "direction": "positive" if beta > 0 else "negative" if beta < 0 else "zero"})
    return rows  # Exact transformed-column order; consumers can rank without losing lineage.


def run_baseline(project_root: str | Path) -> dict:
    root = Path(project_root).resolve()
    config = load_config(root)
    data = load_modeling_data(root)
    model = fit_baseline(data.X_train, data.y_train)
    train_probability = raw_probabilities(model, data.X_train)
    validation_probability = raw_probabilities(model, data.X_validation)
    metrics = {
        "model_version": MODEL_VERSION, "reference_threshold": REFERENCE_THRESHOLD,
        "probability_semantics": "raw model probability of next-month default payment; uncalibrated",
        "test_set_evaluated": False,
        "train": evaluate(data.y_train, train_probability),
        "validation": evaluate(data.y_validation, validation_probability),
        "validation_uncertainty": bootstrap_validation(data.y_validation, validation_probability, config.random_seed),
    }
    coefficients = coefficient_table(model, data.feature_names, data.trace)
    artifact, digest = save_model(model, config.paths.artifacts / "models", MODEL_VERSION)
    loaded = load_model(artifact, digest)
    if not np.allclose(raw_probabilities(loaded, data.X_train), train_probability, rtol=0, atol=1e-12):
        raise ValueError("Model serialization changed training probabilities")
    pre = data.preprocessing_manifest
    manifest = {
        "model_name": "logistic_baseline", "model_version": MODEL_VERSION,
        "model_type": "sklearn.linear_model.LogisticRegression",
        "objective": "binary next-month default-payment classification", "target": TARGET,
        "dataset_sha256": data.dataset_sha256,
        "split_strategy": data.split_manifest["split_strategy"], "split_version": data.split_manifest["split_version"],
        "random_seed": config.random_seed, "solver_uses_random_state": False,
        "preprocessing_version": pre["preprocessing_version"],
        "preprocessing_artifact_relative_path": pre["serialization_artifact_path"],
        "preprocessing_artifact_sha256": pre["serialization_sha256"],
        "feature_engineering_version": pre["feature_engineering_version"],
        "phase3_contract_identities": PHASE3_IDENTITIES,
        "transformed_feature_count": len(data.feature_names),
        "training_rows": len(data.y_train), "validation_rows": len(data.y_validation),
        "test_rows": data.split_manifest["test_rows"], "test_rows_source": "Phase-3 split metadata only",
        "model_parameters": model.get_params(), "effective_penalty": "l2",
        "class_weight": None, "solver": model.solver, "convergence_status": "converged",
        "iterations_used": model.n_iter_.tolist(), "intercept": model.intercept_.tolist(),
        "artifact_relative_path": artifact.relative_to(root).as_posix(), "artifact_sha256": digest,
        "serialization_roundtrip_passed": True, "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(), "numpy_version": np.__version__,
        "scipy_version": scipy.__version__, "joblib_version": joblib.__version__,
        "platform": platform.platform(), "fit_thread_limit": 1,
        "implementation_sha256": {p.name: sha256_file(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
        "configuration": {"base_yaml_sha256": sha256_file(root / "configs/base.yaml"),
                          "experiment_yaml_sha256": sha256_file(root / "configs/experiment.yaml")},
        "test_set_evaluated": False,
    }
    # Preserve timestamp on materially identical reruns; content-addressed binaries
    # are never overwritten. Aggregate manifests describe the latest fixed baseline.
    manifest_path = config.paths.metadata / "baseline_model_manifest.json"
    generated_at = None
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        old_time = previous.pop("generated_at", None)
        if previous == manifest:
            generated_at = old_time
    manifest["generated_at"] = generated_at or datetime.now(timezone.utc).isoformat()
    write_json(manifest_path, manifest)
    write_json(config.paths.metadata / "baseline_metrics.json", metrics)
    write_json(config.paths.metadata / "baseline_coefficients.json",
               {"model_version": MODEL_VERSION, "intercept": model.intercept_.tolist(), "coefficients": coefficients})
    return {"model_version": MODEL_VERSION, "convergence_status": "converged",
            "iterations_used": model.n_iter_.tolist(), "metrics": metrics,
            "artifact_relative_path": manifest["artifact_relative_path"], "artifact_sha256": digest,
            "test_set_evaluated": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = run_baseline(args.project_root)
    except (AcquisitionError, OSError, ValueError) as exc:
        parser.exit(1, f"Baseline failed: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
    print("TEST SET REMAINS SEALED.")


if __name__ == "__main__":
    main()
