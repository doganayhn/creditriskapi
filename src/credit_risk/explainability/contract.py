"""Verify and consume frozen selected artifacts without training or historical writes."""

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from credit_risk.config import _read, load_config
from credit_risk.features.preprocessing import load_preprocessor
from credit_risk.modeling.contract import load_modeling_data
from credit_risk.modeling.xgboost_challenger import MODEL_VERSION, load_native
from credit_risk.explainability.score import InternalScore


def settings(root):
    value = _read(Path(root) / "configs/explainability.yaml", {
        "version", "model_output", "feature_perturbation", "local_reason_top_k", "margin_tolerance",
        "probability_tolerance", "score_tolerance", "score_version", "base_score", "base_good_to_bad_odds",
        "pdo", "numerical_epsilon", "display_rounding"})
    fixed = {"version": "xgboost-shap-1.0.0", "model_output": "raw", "feature_perturbation": "tree_path_dependent",
             "display_rounding": "nearest_integer_ties_to_even"}
    if any(value[key] != expected for key, expected in fixed.items()):
        raise ValueError("Unsupported explanation V1 configuration")
    if type(value["local_reason_top_k"]) is not int or not 1 <= value["local_reason_top_k"] <= 45:
        raise ValueError("Invalid local reason top_k")
    for key, maximum in (("margin_tolerance", 1e-5), ("probability_tolerance", 1e-7), ("score_tolerance", 1e-3)):
        if type(value[key]) not in (float, int) or not np.isfinite(value[key]) or not 0 < value[key] <= maximum:
            raise ValueError("Invalid numerical explanation tolerance")
    InternalScore(value["base_score"], value["base_good_to_bad_odds"], value["pdo"],
                  value["numerical_epsilon"], value["score_version"])
    return value


@dataclass
class FrozenContext:
    data: object
    model: object
    preprocessor: object
    model_manifest: dict
    calibration: dict
    selection: dict
    gain: dict


def load_frozen(root):
    root = Path(root).resolve()
    config = load_config(root)
    data = load_modeling_data(root, validation_only=True)
    def read(name):
        return json.loads((config.paths.metadata / name).read_text(encoding="utf-8"))
    model = read("xgboost_model_manifest.json")
    calibration_manifest = read("calibration_manifest.json")
    calibration = calibration_manifest["models"]["xgboost"]
    selection = read("phase6_model_selection.json")
    gain = read("xgboost_feature_importance.json")
    chosen = selection["models"]["xgboost"]
    pre = data.preprocessing_manifest
    if (selection["downstream_selection_status"] != "XGBOOST_SELECTED_FOR_DOWNSTREAM" or
            selection["selected_downstream_model"] != "xgboost" or model["model_version"] != MODEL_VERSION or
            model["objective"] != "binary:logistic" or len(data.feature_names) != 103 or
            model["transformed_feature_count"] != 103):
        raise ValueError("Phase-6 selected binary XGBoost contract disagrees")
    for key, expected in {"dataset_sha256": data.dataset_sha256,
            "split_version": data.split_manifest["split_version"],
            "feature_engineering_version": pre["feature_engineering_version"],
            "preprocessing_version": pre["preprocessing_version"]}.items():
        if model[key] != expected or calibration[key] != expected:
            raise ValueError("Selected model/calibration data identity disagrees")
    if (model["preprocessing_artifact_sha256"] != pre["serialization_sha256"] or
            chosen["model_version"] != model["model_version"] or
            calibration["underlying_model_version"] != model["model_version"] or
            calibration["underlying_model_artifact_sha256"] != model["artifact_sha256"] or
            chosen["calibration_version"] != calibration["calibration_version"] or
            chosen["calibration_method"] != calibration["method"] or calibration["method"] != "identity" or
            calibration["selected_method"] != "identity" or calibration["artifact_relative_path"] is not None or
            calibration["artifact_sha256"] is not None or gain["model_version"] != model["model_version"]):
        raise ValueError("Frozen model/preprocessing/calibration identity disagrees")
    records = (model, calibration_manifest, calibration, selection, gain, selection["technical_threshold"])
    if any(record.get("test_set_evaluated") is not False for record in records):
        raise ValueError("TEST sealing contract disagrees")
    threshold = selection["technical_threshold"]
    if (threshold["model"] != "xgboost" or threshold["technical_threshold_source"] != "train_oof_max_ks" or
            threshold["business_policy"] is not False or not 0 < threshold["threshold"] < 1):
        raise ValueError("Frozen technical threshold contract disagrees")
    artifact = (root / model["artifact_relative_path"]).resolve()
    if not artifact.is_relative_to(config.paths.artifacts):
        raise ValueError("Selected artifact must remain in trusted local artifacts")
    frozen_model = load_native(artifact, model["artifact_sha256"])
    objective = json.loads(frozen_model.get_booster().save_config())["learner"]["objective"]["name"]
    if frozen_model.n_features_in_ != 103 or objective != "binary:logistic":
        raise ValueError("Frozen native model output/width disagrees")
    preprocessor = load_preprocessor(root / pre["serialization_artifact_path"], pre["serialization_sha256"])
    return FrozenContext(data, frozen_model, preprocessor, model, calibration, selection, gain)
