"""TRAIN-OOF calibration selection, frozen validation assessment and technical thresholds."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import StratifiedKFold

from credit_risk.config import _read, load_config
from credit_risk.data.download import AcquisitionError, sha256_file, write_json
from credit_risk.data.source import TARGET
from credit_risk.features.preprocessing import build_preprocessor, transform_split
from credit_risk.modeling import baseline, xgboost_challenger as challenger
from credit_risk.modeling.artifacts import load_model
from credit_risk.modeling.calibrators import METHODS, ProbabilityCalibrator, load_calibrator, save_calibrator
from credit_risk.modeling.calibration_metrics import downstream_status, paired_quality_bootstrap, probability_metrics, reliability
from credit_risk.modeling.comparison import metric_deltas, verify_metrics
from credit_risk.modeling.contract import load_modeling_data
from credit_risk.modeling.metrics import binary_target, evaluate, validate_probabilities
from credit_risk.modeling.search import load_settings as load_xgboost_settings
from credit_risk.modeling.thresholds import select_train_threshold, threshold_metrics, train_threshold_table

VERSIONS = {"logistic": "logistic-calibration-1.0.0", "xgboost": "xgboost-calibration-1.0.0"}


def load_settings(root: Path) -> dict:
    settings = _read(root / "configs/calibration.yaml", {
        "oof_folds", "selection_folds", "reliability_bins", "bootstrap_replicates",
        "numerical_epsilon", "selection_tolerance", "reference_threshold"})
    for key in ("oof_folds", "selection_folds", "reliability_bins", "bootstrap_replicates"):
        minimum = 2 if key.endswith("folds") else 1
        if type(settings[key]) is not int or not minimum <= settings[key] <= (5 if key.endswith("folds") else 1000):
            raise ValueError(f"Invalid bounded calibration setting: {key}")
    for key, limit in (("numerical_epsilon", .5), ("selection_tolerance", 1e-6)):
        value = settings[key]
        if type(value) not in (int, float) or not np.isfinite(value) or not 0 < value < limit:
            raise ValueError(f"Invalid numerical calibration setting: {key}")
    if settings["reference_threshold"] != .5:
        raise ValueError("Reference threshold must remain 0.50")
    return settings


def load_candidates(root: Path, data) -> dict:
    """Verify artifacts/metadata without generating validation probabilities yet."""
    config, xgb_settings = load_config(root), load_xgboost_settings(root)
    candidates = {}
    for name, prefix, version in (("logistic", "baseline", baseline.MODEL_VERSION),
                                   ("xgboost", "xgboost", challenger.MODEL_VERSION)):
        try:
            manifest = json.loads((config.paths.metadata / f"{prefix}_model_manifest.json").read_text(encoding="utf-8"))
            metrics = json.loads((config.paths.metadata / f"{prefix}_metrics.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"Missing/unreadable {name} metadata") from exc
        expected = {"model_version": version, "dataset_sha256": data.dataset_sha256,
                    "split_version": data.split_manifest["split_version"],
                    "preprocessing_version": data.preprocessing_manifest["preprocessing_version"],
                    "feature_engineering_version": data.preprocessing_manifest["feature_engineering_version"],
                    "preprocessing_artifact_sha256": data.preprocessing_manifest["serialization_sha256"],
                    "transformed_feature_count": len(data.feature_names), "target": TARGET,
                    "training_rows": len(data.y_train), "validation_rows": len(data.y_validation),
                    "random_seed": config.random_seed, "sklearn_version": sklearn.__version__}
        if not isinstance(manifest, dict) or any(manifest.get(k) != v for k, v in expected.items()):
            raise ValueError(f"{name} identity disagrees with verified modeling contract")
        if (manifest.get("test_set_evaluated") is not False or metrics.get("test_set_evaluated") is not False or
                metrics.get("model_version") != version or "test" in metrics or metrics.get("reference_threshold") != .5):
            raise ValueError(f"{name} probability/TEST-sealing contract failed")
        artifact = (root / manifest["artifact_relative_path"]).resolve()
        if not artifact.is_relative_to(config.paths.artifacts):
            raise ValueError("Underlying model artifact must stay inside configured artifacts")
        if name == "logistic":
            model = load_model(artifact, manifest["artifact_sha256"])
            if model.get_params() != baseline.build_model().get_params() or model.get_params() != manifest["model_parameters"]:
                raise ValueError("Logistic configuration differs from fixed Phase-4 definition")
        else:
            if manifest["settings"] != xgb_settings or manifest["scale_pos_weight"] != 1.0:
                raise ValueError("Canonical XGBoost settings disagree with Phase 5")
            selected = manifest["selected_hyperparameters"]
            rows = pd.read_csv(config.paths.metadata / "xgboost_search_results.csv")
            winner = rows.loc[rows.candidate_index == manifest["selected_candidate_index"]]
            if len(winner) != 1 or any(winner.iloc[0][key] != value for key, value in selected.items()):
                raise ValueError("XGBoost selected parameters disagree with recorded Phase-5 search")
            challenger.build_model(xgb_settings, selected, config.random_seed)  # Validate, never fit/search.
            model = challenger.load_native(artifact, manifest["artifact_sha256"])
            if model.get_booster().num_boosted_rounds() != selected["n_estimators"]:
                raise ValueError("XGBoost artifact tree count disagrees with selected parameters")
        if model.n_features_in_ != len(data.feature_names):
            raise ValueError("Underlying model width disagrees with transformed features")
        candidates[name] = {"manifest": manifest, "metrics": metrics, "model": model}
    return candidates


def generate_oof(X_train_engineered, y_train, model_name: str, xgb_parameters: dict,
                 xgb_settings: dict, seed: int, folds: int = 5) -> tuple[np.ndarray, dict]:
    """No project holdout arguments; each position is scored exactly once outside its fit."""
    if model_name not in VERSIONS:
        raise ValueError("Unknown fixed candidate model")
    target = binary_target(y_train, len(X_train_engineered))
    probabilities = np.full(len(target), np.nan)
    coverage = np.zeros(len(target), dtype=int)
    summaries = []
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    for number, (train, holdout) in enumerate(cv.split(X_train_engineered, target), 1):
        if np.intersect1d(train, holdout).size or np.any(coverage[holdout]):
            raise ValueError("OOF fold overlap or repeated holdout assignment")
        preprocessor = build_preprocessor().fit(X_train_engineered.iloc[train])
        X_fit = transform_split(preprocessor, X_train_engineered.iloc[train])
        X_holdout = transform_split(preprocessor, X_train_engineered.iloc[holdout])
        if model_name == "logistic":
            model = baseline.fit_baseline(X_fit, target[train])
            probability = baseline.raw_probabilities(model, X_holdout)
            iterations = model.n_iter_.tolist()
        else:
            model = challenger.fit_model(challenger.build_model(xgb_settings, xgb_parameters, seed), X_fit, target[train])
            probability = challenger.raw_probabilities(model, X_holdout)
            iterations = [model.get_booster().num_boosted_rounds()]
        probabilities[holdout] = probability
        coverage[holdout] += 1
        summaries.append({"fold": number, "fit_rows": len(train), "holdout_rows": len(holdout),
                          "feature_count": X_fit.shape[1], "iterations_or_boosting_rounds": iterations})
    if not np.all(coverage == 1):
        raise ValueError("OOF coverage must be exactly one prediction per TRAIN row")
    return validate_probabilities(probabilities, len(target)), {
        "rows": len(target), "folds": summaries, "coverage_min": int(coverage.min()),
        "coverage_max": int(coverage.max()), "every_row_exactly_once": True,
        "probability_summary": distribution(probabilities), "test_set_evaluated": False}


def distribution(probability) -> dict:
    p = validate_probabilities(probability, len(probability))
    return {"min": float(p.min()), "max": float(p.max()), "mean": float(p.mean()), "std": float(p.std()),
            "unique_values": len(np.unique(p)), "exact_zero_count": int((p == 0).sum()),
            "exact_one_count": int((p == 1).sum())}


def choose_method(summaries: dict, tolerance: float) -> str:
    if set(summaries) != set(METHODS):
        raise ValueError("Exactly identity, sigmoid and isotonic candidates are required")
    for result in summaries.values():
        if not np.isfinite([result["mean_brier_score"], result["mean_log_loss"]]).all():
            raise ValueError("Calibrator selection metrics must be finite")
    best_brier = min(result["mean_brier_score"] for result in summaries.values())
    tied = [name for name in METHODS if abs(summaries[name]["mean_brier_score"] - best_brier) <= tolerance]
    best_loss = min(summaries[name]["mean_log_loss"] for name in tied)
    return next(name for name in tied if abs(summaries[name]["mean_log_loss"] - best_loss) <= tolerance)


def select_calibrator(oof_probability, y_train, settings: dict, seed: int):
    target = binary_target(y_train, len(y_train))
    p = validate_probabilities(oof_probability, len(target))
    cv = list(StratifiedKFold(settings["selection_folds"], shuffle=True, random_state=seed).split(p, target))
    summaries = {}
    keys = ("brier_score", "log_loss", "ece", "mean_predicted_probability", "observed_positive_rate")
    for method in METHODS:
        results = []
        for train, holdout in cv:
            calibrator = ProbabilityCalibrator(method, settings["numerical_epsilon"]).fit(p[train], target[train])
            measured = probability_metrics(target[holdout], calibrator.transform(p[holdout]), settings["reliability_bins"])
            results.append({key: measured[key] for key in keys})
        summaries[method] = {**{f"mean_{key}": float(np.mean([row[key] for row in results])) for key in keys},
                             "fold_metrics": results}
    method = choose_method(summaries, settings["selection_tolerance"])
    fitted = ProbabilityCalibrator(method, settings["numerical_epsilon"]).fit(p, target)
    return fitted, summaries


def run_calibration(project_root: str | Path) -> dict:
    root = Path(project_root).resolve()
    config, settings = load_config(root), load_settings(root)
    xgb_settings = load_xgboost_settings(root)
    data = load_modeling_data(root)
    candidates = load_candidates(root, data)
    engineered = challenger.load_training_features(root, data)
    mappings, oof, selection_cv, model_manifests = {}, {}, {}, {}
    print("Verified models; generating TRAIN-only OOF probabilities and calibration CV.", flush=True)
    for name in VERSIONS:
        oof[name], summary = generate_oof(engineered, data.y_train, name,
            candidates["xgboost"]["manifest"]["selected_hyperparameters"], xgb_settings, config.random_seed, settings["oof_folds"])
        mappings[name], selection_cv[name] = select_calibrator(oof[name], data.y_train, settings, config.random_seed)
        mapping = mappings[name]
        artifact, digest = save_calibrator(mapping, config.paths.artifacts / "calibration", VERSIONS[name])
        if artifact is not None:
            loaded = load_calibrator(artifact, digest)
            if not np.allclose(mapping.transform(oof[name]), loaded.transform(oof[name]), rtol=0, atol=1e-12):
                raise ValueError("Calibrator round-trip changed TRAIN probabilities")
        source = candidates[name]["manifest"]
        model_manifests[name] = {
            "underlying_model_version": source["model_version"], "underlying_model_artifact_sha256": source["artifact_sha256"],
            "calibration_version": VERSIONS[name], "method": mapping.method, "selected_method": mapping.method,
            "dataset_sha256": data.dataset_sha256, "split_version": data.split_manifest["split_version"],
            "feature_engineering_version": source["feature_engineering_version"], "preprocessing_version": source["preprocessing_version"],
            "oof_folds": settings["oof_folds"], "selection_folds": settings["selection_folds"],
            "train_oof_rows": len(data.y_train), "fit_rows": mapping.fit_rows_,
            "selection_metrics": selection_cv[name], "oof_integrity": summary,
            "mapping_parameters": mapping.parameters(), "artifact_relative_path": artifact.relative_to(root).as_posix() if artifact else None,
            "artifact_sha256": digest, "serialization_roundtrip_passed": True if artifact else None,
            "sklearn_version": sklearn.__version__, "python_version": platform.python_version(),
            "validation_used_for_calibrator_fit": False, "validation_used_for_calibrator_selection": False,
            "test_set_evaluated": False}
        print(f"{name}: TRAIN-only selection chose {mapping.method}.", flush=True)
    # Both methods AND fitted parameters are now frozen. Only now score canonical VALIDATION.
    frozen = {name: json.dumps(mapping.parameters(), sort_keys=True) for name, mapping in mappings.items()}
    metrics, reported, reliability_rows = {}, {}, []
    for name, candidate in candidates.items():
        predict = baseline.raw_probabilities if name == "logistic" else challenger.raw_probabilities
        raw = predict(candidate["model"], data.X_validation)
        verify_metrics(evaluate(data.y_validation, raw), candidate["metrics"]["validation"])
        reported[name] = mappings[name].transform(raw)
        raw_metrics = probability_metrics(data.y_validation, raw, settings["reliability_bins"])
        reported_metrics = probability_metrics(data.y_validation, reported[name], settings["reliability_bins"])
        metrics[name] = {"underlying_model_version": candidate["manifest"]["model_version"],
                         "calibration_version": VERSIONS[name], "selected_method": mappings[name].method,
                         "calibration_selection_cv": selection_cv[name], "validation_raw": raw_metrics,
                         "validation_reported": reported_metrics, "reported_minus_raw": metric_deltas(raw_metrics, reported_metrics),
                         "raw_distribution": distribution(raw), "reported_distribution": distribution(reported[name]),
                         "test_set_evaluated": False}
        for kind, probability in (("raw", raw), ("reported", reported[name])):
            bins = reliability(data.y_validation, probability, settings["reliability_bins"])
            reliability_rows.extend({"model": name, "probability_type": kind,
                "requested_bins": bins["requested_bins"], "actual_nonempty_bins": bins["actual_nonempty_bins"],
                "source": "validation", "test_set_evaluated": False, **row} for row in bins["bins"])
    status = downstream_status(metrics["logistic"]["validation_reported"], metrics["xgboost"]["validation_reported"])
    selected = "xgboost" if status == "XGBOOST_SELECTED_FOR_DOWNSTREAM" else "logistic" if status == "LOGISTIC_SELECTED_FOR_DOWNSTREAM" else None
    selection = {"models": {name: {"model_version": candidates[name]["manifest"]["model_version"],
        "calibration_method": mappings[name].method, "calibration_version": VERSIONS[name],
        "validation_reported": metrics[name]["validation_reported"]} for name in VERSIONS},
        "xgboost_minus_logistic": metric_deltas(metrics["logistic"]["validation_reported"], metrics["xgboost"]["validation_reported"]),
        "paired_bootstrap": paired_quality_bootstrap(data.y_validation, reported["logistic"], reported["xgboost"], config.random_seed, settings["bootstrap_replicates"]),
        "downstream_selection_status": status, "selected_downstream_model": selected,
        "final_test_evaluation_pending": True, "test_set_evaluated": False,
        "selection_scope": "development selection, not untouched-test confirmation or production approval"}
    threshold_rows = []
    if selected is not None:
        oof_reported = mappings[selected].transform(oof[selected])
        threshold = select_train_threshold(data.y_train, oof_reported, settings["selection_tolerance"])
        threshold_rows = train_threshold_table(data.y_train, oof_reported, threshold)
        selection["technical_threshold"] = {"model": selected, "technical_threshold_source": "train_oof_max_ks",
            "threshold": threshold, "train_oof": threshold_metrics(data.y_train, oof_reported, threshold),
            "validation_frozen": threshold_metrics(data.y_validation, reported[selected], threshold),
            "validation_reference_0_50": threshold_metrics(data.y_validation, reported[selected], .5),
            "business_policy": False, "test_set_evaluated": False}
    else:
        selection["technical_threshold"] = None
    for name, mapping in mappings.items():
        if json.dumps(mapping.parameters(), sort_keys=True) != frozen[name]:
            raise ValueError("Frozen calibration parameters changed during validation")
    manifest = {"models": model_manifests, "settings": settings, "random_seed": config.random_seed,
                "underlying_model_hyperparameters_retuned": False, "test_set_evaluated": False,
                "validation_used_for_calibrator_fit": False, "validation_used_for_calibrator_selection": False,
                "selection_rule": "lowest mean Brier; within tolerance lowest mean log loss; identity, sigmoid, isotonic",
                "implementation_sha256": {p.name: sha256_file(p) for p in sorted(Path(__file__).parent.glob("*.py"))}}
    path = config.paths.metadata / "calibration_manifest.json"
    timestamp = None
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        old_time = old.pop("generated_at", None)
        if old == manifest:
            timestamp = old_time
    manifest["generated_at"] = timestamp or datetime.now(timezone.utc).isoformat()
    write_json(path, manifest)
    write_json(config.paths.metadata / "calibration_metrics.json", {"models": metrics, "test_set_evaluated": False})
    write_json(config.paths.metadata / "phase6_model_selection.json", selection)
    pd.DataFrame(reliability_rows).to_csv(config.paths.metadata / "calibration_reliability.csv", index=False, lineterminator="\n")
    threshold_columns = ["threshold", "predicted_positive_count", "predicted_positive_rate", "tn", "fp", "fn", "tp",
        "precision", "recall", "specificity", "f1", "false_positive_rate", "false_negative_rate", "source", "is_max_ks", "is_reference", "test_set_evaluated"]
    pd.DataFrame(threshold_rows, columns=threshold_columns).to_csv(config.paths.metadata / "threshold_analysis.csv", index=False, lineterminator="\n")
    return {"selected_methods": {name: mapping.method for name, mapping in mappings.items()},
            "metrics": metrics, "selection": selection, "test_set_evaluated": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = run_calibration(args.project_root)
    except (AcquisitionError, OSError, ValueError) as exc:
        parser.exit(1, f"Calibration failed: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
    print("TEST SET REMAINS SEALED.")


if __name__ == "__main__":
    main()
