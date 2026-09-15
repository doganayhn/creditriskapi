"""Load and verify trusted artifacts once, without opening any dataset partition."""

from dataclasses import dataclass
from importlib.metadata import version
import json
from pathlib import Path

from credit_risk.config import load_config
from credit_risk.data.download import sha256_file
from credit_risk.explainability.aggregation import lineage
from credit_risk.explainability.contract import settings
from credit_risk.explainability.score import InternalScore
from credit_risk.explainability.shap_explainer import MarginExplainer
from credit_risk.features import prepare
from credit_risk.features.definitions import PRIMARY_MODEL_FEATURES, MODEL_INPUT_FEATURES
from credit_risk.features.preprocessing import load_preprocessor
from credit_risk.modeling.contract import read_contracts
from credit_risk.modeling.xgboost_challenger import load_native


@dataclass(frozen=True)
class FrozenRuntime:
    preprocessor: object
    model: object
    model_manifest: dict
    calibration: dict
    explanation_manifest: dict
    score_manifest: dict
    preprocessing_manifest: dict
    dataset_manifest: dict
    options: dict
    feature_names: tuple[str, ...]
    rows: list[dict]
    mapping: InternalScore
    explainer: MarginExplainer


def load_runtime(project_root):
    """Artifact-only boundary: no raw data, labels, splits, training or publication."""
    root = Path(project_root).resolve()
    config = load_config(root)
    phase3 = read_contracts(config.paths.metadata)
    pre, features = phase3["preprocessing_manifest"], phase3["feature_manifest"]
    def read(name):
        return json.loads((config.paths.metadata / (name + ".json")).read_text(encoding="utf-8"))
    dataset, model, calibration_all, selection, explanation, score = [read(name) for name in
        ("dataset_manifest", "xgboost_model_manifest", "calibration_manifest", "phase6_model_selection",
         "explainability_manifest", "internal_score_manifest")]
    calibration = calibration_all["models"]["xgboost"]
    chosen = selection["models"]["xgboost"]
    options = settings(root)
    if (selection["selected_downstream_model"] != "xgboost" or
            selection["downstream_selection_status"] != "XGBOOST_SELECTED_FOR_DOWNSTREAM" or
            model["objective"] != "binary:logistic" or calibration["method"] != "identity" or
            calibration["selected_method"] != "identity" or
            calibration["artifact_relative_path"] is not None or calibration["artifact_sha256"] is not None):
        raise ValueError("Unsupported selected model/calibration contract")
    if any(item.get("test_set_evaluated") is not False for item in
           (model, calibration_all, calibration, selection, explanation, score)):
        raise ValueError("TEST sealing contract disagrees")
    for item in (model, calibration, explanation, score):
        for key, expected in (("dataset_sha256", dataset["sha256"]),
                              ("feature_engineering_version", pre["feature_engineering_version"]),
                              ("preprocessing_version", pre["preprocessing_version"]),
                              ("split_version", phase3["split_manifest"]["split_version"])):
            if item[key] != expected:
                raise ValueError("Frozen dataset/feature identity disagrees")
    if dataset["sha256"] != pre["dataset_sha256"] or dataset["canonical_target_column"] != config.target_column:
        raise ValueError("Dataset/target contract disagrees")
    if (chosen["model_version"] != model["model_version"] or
            calibration["underlying_model_version"] != model["model_version"] or
            calibration["underlying_model_artifact_sha256"] != model["artifact_sha256"] or
            chosen["calibration_version"] != calibration["calibration_version"] or
            chosen["calibration_method"] != "identity" or
            model["preprocessing_artifact_sha256"] != pre["serialization_sha256"]):
        raise ValueError("Selected model artifact identity disagrees")
    for item in (explanation, score):
        for key, expected in (("model_version", model["model_version"]), ("model_artifact_sha256", model["artifact_sha256"]),
                ("preprocessing_artifact_sha256", pre["serialization_sha256"]),
                ("calibration_version", calibration["calibration_version"]), ("calibration_method", "identity")):
            if item[key] != expected:
                raise ValueError("Explanation/score artifact identity disagrees")
    if (explanation["explainability_version"] != options["version"] or explanation["model_output"] != "raw" or
            explanation["feature_perturbation"] != options["feature_perturbation"] or
            explanation["config_sha256"] != sha256_file(root / "configs/explainability.yaml") or
            explanation["local_reason_top_k"] != options["local_reason_top_k"] or
            explanation["score_version"] != score["score_version"]):
        raise ValueError("Explanation configuration disagrees")
    mapping = InternalScore(options["base_score"], options["base_good_to_bad_odds"], options["pdo"],
                            options["numerical_epsilon"], options["score_version"])
    for key, expected in (("score_version", mapping.version), ("base_score", mapping.base_score),
            ("base_good_to_bad_odds", mapping.base_good_to_bad_odds), ("pdo", mapping.pdo),
            ("factor", float(mapping.factor)), ("offset", float(mapping.offset)),
            ("numerical_epsilon", mapping.epsilon), ("probability_field", "reported_probability"),
            ("canonical_score_type", "continuous"), ("display_rounding", options["display_rounding"]),
            ("score_point_decomposition_supported", True), ("business_cutoff_defined", False)):
        if score[key] != expected:
            raise ValueError("Internal score configuration disagrees")
    for package, key in (("scikit-learn", "sklearn"), ("numpy", "numpy"), ("pandas", "pandas"),
                         ("scipy", "scipy"), ("joblib", "joblib")):
        if version(package) != pre[key + "_version"]:
            raise ValueError("Preprocessing runtime version disagrees")
    if version("shap") != explanation["shap_version"] or version("xgboost") != explanation["runtime_versions"]["xgboost"]:
        raise ValueError("Explanation runtime version disagrees")
    for module, hashes in (("features", pre["implementation_sha256"]),
                           ("explainability", explanation["implementation_sha256"])):
        directory = Path(__file__).resolve().parents[1] / module
        for name, digest in hashes.items():
            path = (directory / name).resolve()
            if path.parent != directory or sha256_file(path) != digest:
                raise ValueError("Frozen feature/explanation implementation disagrees")
    if list(PRIMARY_MODEL_FEATURES) != features["raw_financial_features"]:
        raise ValueError("Raw predictor schema disagrees")
    def trusted(relative):
        path = (root / relative).resolve()
        if not path.is_relative_to(config.paths.artifacts):
            raise ValueError("Artifact is outside trusted project artifacts")
        return path
    preprocessor = load_preprocessor(trusted(pre["serialization_artifact_path"]), pre["serialization_sha256"])
    names = tuple(preprocessor.get_feature_names_out())
    trace = prepare.transformed_trace(preprocessor)
    if (list(names) != features["transformed_feature_names"] or trace != features["transformed_feature_trace"] or
            len(names) != 103 or model["transformed_feature_count"] != len(names) or
            list(preprocessor.feature_names_in_) != list(MODEL_INPUT_FEATURES)):
        raise ValueError("Frozen preprocessing feature order/width disagrees")
    rows = lineage(names, trace)
    if rows != explanation["lineage"]:
        raise ValueError("Explanation lineage disagrees")
    frozen_model = load_native(trusted(model["artifact_relative_path"]), model["artifact_sha256"])
    objective = json.loads(frozen_model.get_booster().save_config())["learner"]["objective"]["name"]
    if frozen_model.n_features_in_ != len(names) or objective != "binary:logistic":
        raise ValueError("Native objective/width disagrees")
    explainer = MarginExplainer(frozen_model, names, margin_tolerance=options["margin_tolerance"],
                               probability_tolerance=options["probability_tolerance"])
    return FrozenRuntime(preprocessor, frozen_model, model, calibration, explanation, score, pre, dataset,
                         options, names, rows, mapping, explainer)
