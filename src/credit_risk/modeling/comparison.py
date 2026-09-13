"""Verified stored-baseline comparison and paired validation-only uncertainty."""

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from credit_risk.config import load_config
from credit_risk.data.source import TARGET
from credit_risk.modeling.artifacts import load_model
from credit_risk.modeling.baseline import MODEL_VERSION, raw_probabilities
from credit_risk.modeling.metrics import binary_target, evaluate, validate_probabilities


def verify_metrics(actual: dict, recorded: dict) -> None:
    if set(actual) != set(recorded):
        raise ValueError("Stored baseline metric keys disagree with reproduction")
    for key, value in actual.items():
        if isinstance(value, dict):
            verify_metrics(value, recorded[key])
        elif not np.isclose(value, recorded[key], rtol=0, atol=1e-12):
            raise ValueError(f"Stored baseline metric disagrees: {key}")


def load_baseline(root: Path, data) -> tuple[dict, dict, np.ndarray]:
    config = load_config(root)
    try:
        manifest = json.loads((config.paths.metadata / "baseline_model_manifest.json").read_text(encoding="utf-8"))
        metrics = json.loads((config.paths.metadata / "baseline_metrics.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Phase-4 baseline metadata missing/unreadable") from exc
    pre = data.preprocessing_manifest
    expected = {"model_version": MODEL_VERSION, "model_type": "sklearn.linear_model.LogisticRegression",
                "target": TARGET, "dataset_sha256": data.dataset_sha256,
                "split_version": data.split_manifest["split_version"],
                "split_strategy": data.split_manifest["split_strategy"],
                "random_seed": config.random_seed, "preprocessing_version": pre["preprocessing_version"],
                "feature_engineering_version": pre["feature_engineering_version"],
                "preprocessing_artifact_sha256": pre["serialization_sha256"],
                "transformed_feature_count": len(data.feature_names),
                "training_rows": len(data.y_train), "validation_rows": len(data.y_validation),
                "test_rows": data.split_manifest["test_rows"], "convergence_status": "converged"}
    if not isinstance(manifest, dict) or any(manifest.get(k) != v for k, v in expected.items()):
        raise ValueError("Phase-4 baseline identity conflicts with modeling contract")
    if (manifest.get("test_set_evaluated") is not False or metrics.get("test_set_evaluated") is not False or
            metrics.get("model_version") != MODEL_VERSION or metrics.get("reference_threshold") != .5 or
            "test" in metrics):
        raise ValueError("Baseline version/threshold/test-sealing contract failed")
    path = (root / manifest["artifact_relative_path"]).resolve()
    if not path.is_relative_to(config.paths.artifacts):
        raise ValueError("Baseline artifact must be inside configured artifacts")
    model = load_model(path, manifest["artifact_sha256"])
    if model.n_features_in_ != len(data.feature_names) or model.get_params() != manifest["model_parameters"]:
        raise ValueError("Baseline artifact parameters/width disagree with metadata")
    probability = raw_probabilities(model, data.X_validation)
    verify_metrics(evaluate(data.y_validation, probability), metrics["validation"])
    verify_metrics(evaluate(data.y_train, raw_probabilities(model, data.X_train)), metrics["train"])
    return manifest, metrics, probability


def provisional_status(baseline: dict, challenger: dict) -> str:
    auc = challenger["roc_auc"] - baseline["roc_auc"]
    ap = challenger["average_precision"] - baseline["average_precision"]
    if auc > 0 and ap > 0:
        return "XGBOOST_LEADS_ON_VALIDATION_DISCRIMINATION"
    if auc < 0 and ap < 0:
        return "LOGISTIC_BASELINE_LEADS_ON_VALIDATION_DISCRIMINATION"
    return "MIXED_VALIDATION_RESULT"


def metric_deltas(baseline: dict, challenger: dict) -> dict:
    return {key: metric_deltas(value, challenger[key]) if isinstance(value, dict)
            else challenger[key] - value for key, value in baseline.items()}


def paired_bootstrap(y_validation, baseline_probability, challenger_probability, seed: int, replicates: int = 1000) -> dict:
    y = binary_target(y_validation, len(y_validation))
    baseline = validate_probabilities(baseline_probability, len(y))
    challenger = validate_probabilities(challenger_probability, len(y))
    if type(replicates) is not int or replicates < 1:
        raise ValueError("Bootstrap replicate count must be a positive integer")
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(replicates):
        indices = rng.integers(0, len(y), len(y))
        target = y[indices]
        if len(np.unique(target)) == 1:
            continue
        deltas.append([roc_auc_score(target, challenger[indices]) - roc_auc_score(target, baseline[indices]),
                       average_precision_score(target, challenger[indices]) - average_precision_score(target, baseline[indices])])
    if not deltas:
        raise ValueError("No valid paired bootstrap replicates")
    intervals = np.percentile(deltas, [2.5, 97.5], axis=0)
    return {"delta_roc_auc_95_ci": intervals[:, 0].tolist(),
            "delta_average_precision_95_ci": intervals[:, 1].tolist(),
            "requested_replicates": replicates, "successful_replicates": len(deltas),
            "skipped_single_class": replicates - len(deltas), "random_seed": seed,
            "method": "paired validation row bootstrap; replacement; percentile 95%",
            "test_set_evaluated": False}
