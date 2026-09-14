"""TRAIN-CV XGBoost challenger and provisional validation comparison; TEST stays sealed."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import tempfile

import numpy as np
import sklearn
from threadpoolctl import threadpool_limits
import xgboost
from xgboost import XGBClassifier

from credit_risk.config import load_config
from credit_risk.data.download import AcquisitionError, sha256_file
from credit_risk.data.source import TARGET
from credit_risk.features.definitions import EXCLUDED_FIELDS
from credit_risk.features.engineering import engineer_features, select_primary_features
from credit_risk.features.prepare import verify_dataset_manifest
from credit_risk.features.split import split_dataset
from credit_risk.modeling.baseline import validate_matrix
from credit_risk.modeling.comparison import load_baseline, metric_deltas, paired_bootstrap, provisional_status
from credit_risk.modeling.contract import load_modeling_data
from credit_risk.modeling.experiment_metadata import XGBOOST_MODULES, implementation_hashes, publish_experiment
from credit_risk.modeling.metrics import binary_target, evaluate, validate_probabilities
from credit_risk.modeling.search import load_settings, run_search, search_table

MODEL_VERSION = "xgboost-challenger-1.0.0"


def load_training_features(root: Path, data):
    """Reuse Phase-3 raw split/engineering; return no project holdout inputs to CV."""
    config = load_config(root)
    canonical, digest = verify_dataset_manifest(root)
    if digest != data.dataset_sha256:
        raise ValueError("CV source identity disagrees with final modeling data")
    partitions = split_dataset(canonical, config.split, config.random_seed)
    train = partitions.pop("train")
    del partitions  # No access to holdout frames beyond Phase-3 structural splitting.
    if not np.array_equal(train[TARGET].to_numpy(dtype=int), data.y_train):
        raise ValueError("CV training target alignment disagrees with verified split")
    return engineer_features(select_primary_features(train))


def build_model(settings: dict, parameters: dict, seed: int, scale_pos_weight: float = 1.0) -> XGBClassifier:
    if set(parameters) != set(settings["space"]):
        raise ValueError("Selected parameters must match the declared search dimensions")
    for name, value in parameters.items():
        if value not in settings["space"][name]:
            raise ValueError(f"Selected parameter is outside search space: {name}")
    if not np.isfinite(scale_pos_weight) or scale_pos_weight <= 0:
        raise ValueError("Class weight must be positive and finite")
    fixed = {**settings["fixed"], "scale_pos_weight": float(scale_pos_weight)}
    return XGBClassifier(**fixed, **parameters, random_state=seed)


def fit_model(model: XGBClassifier, X_train, y_train) -> XGBClassifier:
    validate_matrix(X_train)
    target = binary_target(y_train, X_train.shape[0])
    # Numeric values and column order remain exactly the Phase-3 representation.
    with threadpool_limits(limits=1):
        model.fit(X_train.toarray(), target)
    return model


def raw_probabilities(model: XGBClassifier, X) -> np.ndarray:
    validate_matrix(X)
    if not np.array_equal(model.classes_, [0, 1]):
        raise ValueError("XGBoost class order must be [0, 1]")
    output = model.predict_proba(X.toarray())
    if output.shape != (X.shape[0], 2):
        raise ValueError("XGBoost probability shape mismatch")
    return validate_probabilities(output[:, 1], X.shape[0])


def feature_importance(model, names, trace) -> dict:
    names = list(names)
    if len(set(names)) != len(names) or [row["name"] for row in trace] != names:
        raise ValueError("Feature importance names/lineage mismatch")
    booster = model.get_booster()
    if booster.num_features() != len(names):
        raise ValueError("Booster feature width disagrees with transformed names")
    gains = booster.get_score(importance_type="gain")
    counts = booster.get_score(importance_type="weight")
    known = {f"f{i}" for i in range(len(names))}
    if not set(gains).issubset(known) or not set(counts).issubset(known):
        raise ValueError("Unknown native booster feature identifier")
    if any(not np.isfinite(v) or v < 0 for v in list(gains.values()) + list(counts.values())):
        raise ValueError("Gain/count must be finite and nonnegative")
    total = sum(gains.values())
    rows = []
    for i, (name, lineage) in enumerate(zip(names, trace)):
        if set(lineage["canonical_sources"]) & set(EXCLUDED_FIELDS):
            raise ValueError("Forbidden field in native importance")
        gain = float(gains.get(f"f{i}", 0.0))
        source = lineage["input_feature"]
        family = ("repayment_status" if source.startswith("repayment_status") else
                  "bill" if source.startswith("bill_") else "payment" if source.startswith("payment_") else
                  "documented_delay" if "delay" in source else "credit_limit")
        rows.append({"transformed_feature_name": name, "source_feature": source,
                     "canonical_sources": lineage["canonical_sources"], "feature_family": family,
                     "feature_type": "standardized_numeric" if lineage["category"] is None else "one_hot_category",
                     "gain": gain, "normalized_gain": gain / total if total else 0.0,
                     "split_count": int(counts.get(f"f{i}", 0))})
    return {"model_version": MODEL_VERSION, "test_set_evaluated": False,
            "definition": "gain is mean training loss reduction per split using a feature; normalized across features",
            "interpretation": "aggregate split diagnostic, not SHAP, causality or a per-customer reason",
            "features": sorted(rows, key=lambda row: (-row["gain"], row["transformed_feature_name"]))}


def save_native(model: XGBClassifier, directory: Path) -> tuple[Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".json", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        model.save_model(temporary)
        content = temporary.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        destination = directory / f"{MODEL_VERSION}_{digest}.json"
        if destination.exists():
            if destination.read_bytes() != content:
                raise ValueError("Existing native artifact has unexpected bytes")
        else:
            with destination.open("xb") as stream:
                stream.write(content)
        return destination, digest
    finally:
        temporary.unlink(missing_ok=True)


def load_native(path: Path, digest: str) -> XGBClassifier:
    """Only trusted locally generated native models; hashes are identity checks."""
    if sha256_file(path) != digest:
        raise ValueError("Native XGBoost checksum mismatch")
    model = XGBClassifier(n_jobs=1, device="cpu")
    model.load_model(path)
    return model


def run_challenger(project_root: str | Path) -> dict:
    root = Path(project_root).resolve()
    config, settings = load_config(root), load_settings(root)
    data = load_modeling_data(root)
    baseline_manifest, baseline_metrics, baseline_probability = load_baseline(root, data)
    engineered = load_training_features(root, data)
    print("Verified contracts and stored baseline; starting TRAIN-only fold-local search.", flush=True)
    with threadpool_limits(limits=1):
        search = run_search(engineered, data.y_train, settings, config.random_seed)
    parameters = {key.removeprefix("model__"): value for key, value in search.best_params_.items()}
    table = search_table(search)
    print(f"Completed {len(table)} candidates; selected candidate {search.best_index_}.", flush=True)
    model = fit_model(build_model(settings, parameters, config.random_seed), data.X_train, data.y_train)
    train_probability = raw_probabilities(model, data.X_train)
    validation_probability = raw_probabilities(model, data.X_validation)
    train_metrics = evaluate(data.y_train, train_probability)
    validation_metrics = evaluate(data.y_validation, validation_probability)
    positive = int(np.count_nonzero(data.y_train == 1))
    negative = int(np.count_nonzero(data.y_train == 0))
    weight = negative / positive
    sensitivity = fit_model(build_model(settings, parameters, config.random_seed, weight), data.X_train, data.y_train)
    sensitivity_metrics = evaluate(data.y_validation, raw_probabilities(sensitivity, data.X_validation))
    del sensitivity  # Temporary diagnostic only; never replace or serialize as canonical.
    metrics = {"model_version": MODEL_VERSION, "reference_threshold": .5, "test_set_evaluated": False,
               "probability_semantics": "raw / uncalibrated next-month default-payment probability",
               "train": train_metrics, "validation": validation_metrics,
               "train_minus_validation": metric_deltas(validation_metrics, train_metrics),
               "imbalance_sensitivity": {"canonical": False, "scale_pos_weight": weight,
                   "train_negative_count": negative, "train_positive_count": positive,
                   "validation": sensitivity_metrics, "test_set_evaluated": False}}
    comparison = {"baseline_model_version": baseline_manifest["model_version"], "xgboost_model_version": MODEL_VERSION,
                  "baseline_validation": baseline_metrics["validation"], "xgboost_validation": validation_metrics,
                  "xgboost_minus_baseline": metric_deltas(baseline_metrics["validation"], validation_metrics),
                  "paired_bootstrap": paired_bootstrap(data.y_validation, baseline_probability, validation_probability, config.random_seed),
                  "provisional_discrimination_status": provisional_status(baseline_metrics["validation"], validation_metrics),
                  "test_set_evaluated": False, "final_model_selected": False,
                  "final_selection": "deferred to Phase-6 calibration analysis and later project requirements"}
    importance = feature_importance(model, data.feature_names, data.trace)
    artifact, digest = save_native(model, config.paths.artifacts / "models")
    loaded = load_native(artifact, digest)
    for X, probability in ((data.X_train, train_probability), (data.X_validation, validation_probability)):
        if not np.allclose(raw_probabilities(loaded, X), probability, rtol=0, atol=1e-12):
            raise ValueError("Native model round-trip changed probabilities")
    pre = data.preprocessing_manifest
    best = table.loc[table.selected].iloc[0]
    manifest = {"model_name": "xgboost_challenger", "model_version": MODEL_VERSION,
                "model_type": "xgboost.XGBClassifier", "objective": "binary:logistic", "target": TARGET,
                "dataset_sha256": data.dataset_sha256, "split_strategy": data.split_manifest["split_strategy"],
                "split_version": data.split_manifest["split_version"], "random_seed": config.random_seed,
                "feature_engineering_version": pre["feature_engineering_version"],
                "preprocessing_version": pre["preprocessing_version"],
                "preprocessing_artifact_reference": pre["serialization_artifact_path"],
                "preprocessing_artifact_sha256": pre["serialization_sha256"],
                "transformed_feature_count": len(data.feature_names), "training_rows": len(data.y_train),
                "validation_rows": len(data.y_validation), "test_rows": data.split_manifest["test_rows"],
                "test_rows_source": "Phase-3 structural metadata only",
                "search_strategy": "RandomizedSearchCV; TRAIN-only StratifiedKFold; fold-local preprocessing",
                "search_iterations": len(table), "cv_folds": settings["search"]["cv_folds"],
                "total_candidate_fits": len(table) * settings["search"]["cv_folds"],
                "search_refit_fits": 1, "canonical_fits": 1, "sensitivity_fits": 1,
                "total_xgboost_fits": len(table) * settings["search"]["cv_folds"] + 3,
                "scoring_metrics": ["roc_auc", "average_precision"], "primary_selection_metric": "roc_auc",
                "selection_rule": "max mean CV AUC; machine-epsilon tie: AP, smaller depth, fewer trees, larger lambda/alpha/gamma, earlier candidate",
                "selected_candidate_index": int(search.best_index_), "selected_hyperparameters": parameters,
                "selected_cv_scores": {key: float(best[key]) for key in ("mean_test_roc_auc", "std_test_roc_auc", "mean_test_average_precision", "std_test_average_precision")},
                **settings["fixed"], "settings": settings, "early_stopping": False,
                "matrix_storage": "dense view of identical Phase-3 numeric values; zeros are not missing",
                "artifact_relative_path": artifact.relative_to(root).as_posix(), "artifact_sha256": digest,
                "artifact_format": "XGBoost native JSON", "serialization_roundtrip_passed": True,
                "xgboost_version": xgboost.__version__, "sklearn_version": sklearn.__version__,
                "python_version": platform.python_version(), "numpy_version": np.__version__,
                "baseline_model_version": baseline_manifest["model_version"],
                "baseline_manifest_sha256": sha256_file(config.paths.metadata / "baseline_model_manifest.json"),
                "baseline_metrics_sha256": sha256_file(config.paths.metadata / "baseline_metrics.json"),
                "configuration_sha256": sha256_file(root / "configs/xgboost.yaml"),
                "implementation_sha256": implementation_hashes(XGBOOST_MODULES),
                "test_set_evaluated": False}
    manifest = publish_experiment(config.paths.metadata / "xgboost_model_manifest.json", manifest, {
        "xgboost_metrics.json": metrics, "model_comparison.json": comparison,
        "xgboost_feature_importance.json": importance}, table)
    return {"model_version": MODEL_VERSION, "selected_parameters": parameters,
            "selected_cv_scores": manifest["selected_cv_scores"], "metrics": metrics,
            "comparison": comparison, "artifact_sha256": digest, "test_set_evaluated": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = run_challenger(args.project_root)
    except (AcquisitionError, OSError, ValueError, xgboost.core.XGBoostError) as exc:
        parser.exit(1, f"Challenger failed: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
    print("TEST SET REMAINS SEALED.")


if __name__ == "__main__":
    main()
