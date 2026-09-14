"""Explain frozen XGBoost on VALIDATION; persist only aggregate diagnostics."""

import argparse
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import shap
import xgboost

from credit_risk.config import load_config
from credit_risk.data.download import AcquisitionError, sha256_file, write_json
from credit_risk.explainability.aggregation import AGGREGATION_VERSION, global_importance, lineage
from credit_risk.explainability.contract import load_frozen, settings
from credit_risk.explainability.local import explain_record, synthetic_records
from credit_risk.explainability.score import InternalScore, rank_validation, score_deciles, score_summary
from credit_risk.explainability.shap_explainer import MarginExplainer, residual_summary
from credit_risk.modeling.calibration_metrics import probability_metrics
from credit_risk.modeling.comparison import verify_metrics


def run_explainability(project_root):
    root = Path(project_root).resolve()
    config, options = load_config(root), settings(root)
    context = load_frozen(root)
    data = context.data
    if data.X_train is not None or data.y_train is not None:
        raise ValueError("Explanation consumer must expose VALIDATION only")
    mapping = InternalScore(options["base_score"], options["base_good_to_bad_odds"], options["pdo"],
                            options["numerical_epsilon"], options["score_version"])
    rows = lineage(data.feature_names, data.trace)
    explainer = MarginExplainer(context.model, data.feature_names,
        margin_tolerance=options["margin_tolerance"], probability_tolerance=options["probability_tolerance"])
    explanation = explainer.explain(data.X_validation)
    reported = explanation["raw_probability"]  # Verified frozen identity calibration.
    metrics = probability_metrics(data.y_validation, reported)
    verify_metrics(metrics, context.selection["models"]["xgboost"]["validation_reported"])
    global_rows, sources, source_values, families, family_values = global_importance(explanation["values"], rows)
    decompositions = {}
    for level, values in (("transformed_feature", explanation["values"]),
                          ("source_feature", source_values), ("feature_family", family_values)):
        result = mapping.decompose(explanation["base"], values, reported,
            calibration_method=context.calibration["method"], tolerance=options["score_tolerance"])
        if not result["score_point_decomposition_supported"]:
            raise ValueError("Frozen identity score decomposition unexpectedly unavailable")
        decompositions[level] = {key: value for key, value in result.items()
                                 if key not in ("score_base_value", "score_point_contributions")}
    rank = rank_validation(mapping, data.y_validation, reported)
    base, _ = mapping.transform([1 / 51, 1 / 101])
    if not np.allclose(base, [600, 620], rtol=0, atol=1e-10):
        raise ValueError("Score base/PDO identities failed")
    threshold = context.selection["technical_threshold"]
    threshold_score = float(mapping.transform([threshold["threshold"]])[0][0])
    synthetic = {}
    for name, record in synthetic_records().items():
        local = explain_record(record, context, explainer, mapping, rows,
            top_k=options["local_reason_top_k"], score_tolerance=options["score_tolerance"])
        reconstructed = local["score_base_value"] + sum(row["score_points"] for row in local["source_contributions"])
        # Persist validation status only, never local explanations or customer rows.
        synthetic[name] = {"synthetic_input": True, "source_feature_count": len(local["source_contributions"]),
                           "score_absolute_residual": abs(reconstructed - local["internal_risk_score"]), "passed": True}
    gain_top = [row["transformed_feature_name"] for row in
                sorted(context.gain["features"], key=lambda row: (-row["gain"], row["transformed_feature_name"]))[:10]]
    shap_top = [row["name"] for row in global_rows["transformed_feature"][:10]]
    common = sorted(set(gain_top) & set(shap_top))
    identity = {"dataset_sha256": data.dataset_sha256, "split_version": data.split_manifest["split_version"],
        "feature_engineering_version": data.preprocessing_manifest["feature_engineering_version"],
        "preprocessing_version": data.preprocessing_manifest["preprocessing_version"],
        "preprocessing_artifact_sha256": data.preprocessing_manifest["serialization_sha256"],
        "model_version": context.model_manifest["model_version"],
        "model_artifact_sha256": context.model_manifest["artifact_sha256"],
        "calibration_version": context.calibration["calibration_version"], "calibration_method": "identity",
        "test_set_evaluated": False}
    manifest = {**identity, "explainability_version": options["version"], "explainer_type": "shap.TreeExplainer",
        "method": "Tree SHAP", "shap_version": shap.__version__, "model_name": "xgboost",
        "explained_output": "raw_margin", "validation_rows_explained": len(reported), "test_rows_explained": 0,
        "source_aggregation_enabled": True, "family_aggregation_enabled": True,
        "score_point_decomposition_supported": True, "score_version": mapping.version,
        "customer_level_explanations_exported": False,
        "model_output": options["model_output"], "output_units": "raw_margin_log_odds",
        "feature_perturbation": options["feature_perturbation"],
        "background": "Frozen model training path counts; no background rows supplied",
        "population": "validation", "validation_rows": len(reported), "transformed_feature_count": len(rows),
        "source_feature_count": len(sources), "feature_family_count": len(families),
        "missing_lineage_count": 0, "forbidden_feature_count": 0, "lineage": rows,
        "aggregation_version": AGGREGATION_VERSION, "aggregation_rule": "signed local sum, then global mean absolute value",
        "margin_tolerance": options["margin_tolerance"], "probability_tolerance": options["probability_tolerance"],
        "probability_reconstruction": explanation["probability_reconstruction"], "additivity": explanation["additivity"],
        "shap_linked_probability_reconstruction": explanation["shap_linked_probability_reconstruction"],
        "source_total_residual": residual_summary(source_values.sum(axis=1) - explanation["values"].sum(axis=1)),
        "family_total_residual": residual_summary(family_values.sum(axis=1) - explanation["values"].sum(axis=1)),
        "native_gain_comparison": {"top_k": 10, "overlap_count": len(common), "overlap_features": common,
            "gain_top_features": gain_top, "shap_top_features": shap_top, "diagnostic_only": True},
        "local_reason_top_k": options["local_reason_top_k"], "local_tie_breaking": "source feature name ascending",
        "synthetic_local_validation": synthetic, "validation_metrics_unchanged": metrics,
        "runtime_versions": {"python": platform.python_version(), "numpy": np.__version__,
            "shap": shap.__version__, "xgboost": xgboost.__version__},
        "implementation_sha256": {path.name: sha256_file(path) for path in sorted(Path(__file__).parent.glob("*.py"))},
        "config_sha256": sha256_file(root / "configs/explainability.yaml"),
        "row_level_outputs_persisted": False, "model_retrained": False}
    score_manifest = {**identity, "score_version": mapping.version, "probability_source": "selected_model_reported_probability",
        "score_name": "Project-specific internal risk score", "source_model_name": "xgboost",
        "source_model_version": identity["model_version"], "source_model_artifact_sha256": identity["model_artifact_sha256"],
        "probability_field": "reported_probability", "numerical_epsilon": mapping.epsilon,
        "higher_score_means": "lower predicted default probability", "canonical_score_type": "continuous",
        "FICO_equivalent": False, "business_cutoff_defined": False,
        "base_score": mapping.base_score, "base_good_to_bad_odds": mapping.base_good_to_bad_odds,
        "pdo": mapping.pdo, "factor": float(mapping.factor), "offset": float(mapping.offset), "epsilon": mapping.epsilon,
        "formula": "offset + factor * ln((1 - reported_probability) / reported_probability)",
        "inverse_formula": "sigmoid((offset - score) / factor)",
        "direction": "higher score means lower predicted default probability",
        "numerical_clipping": "clip probability to [epsilon, 1-epsilon] only for logarithm; retain original probability",
        "cosmetic_score_bounds": None, "canonical_score": "continuous_float64",
        "display_rounding": options["display_rounding"], "business_policy": False, "is_fico": False, "regulatory_score": False,
        "score_point_decomposition_supported": True, "score_base_formula": "offset - factor * shap_base_margin",
        "score_point_formula": "-factor * shap_margin_contribution", "score_tolerance": options["score_tolerance"],
        "score_point_decomposition": decompositions,
        "decomposition_guard": "binary logistic raw margin, identity calibration, no probability clipping",
        "mathematical_validation": {"score_at_odds_50": float(base[0]), "score_at_odds_100": float(base[1]),
            "pdo_increment": float(base[1] - base[0]), **rank},
        "technical_threshold": {"probability": threshold["threshold"], "technical_reference_score": threshold_score,
            "source": "phase6_train_oof_max_ks_probability_threshold", "business_policy": False, "optimized_in_phase7": False}}
    summary = {"score_version": mapping.version, "test_set_evaluated": False,
        "train_oof": {"available": False, "reason": "Phase 6 retained aggregate OOF statistics only. Project owner instructed no retraining; exact OOF score statistics are unavailable.",
                      "in_sample_training_scores_substituted": False},
        "validation": {"available": True, **score_summary(mapping, reported)}}
    artifacts = {"explainability_manifest.json": manifest,
        "shap_global_importance.json": {**identity, "population": "validation", "validation_rows": len(reported),
            "aggregation_version": AGGREGATION_VERSION, "units": "raw_margin_log_odds", **global_rows},
        "internal_score_manifest.json": score_manifest, "internal_score_summary.json": summary}
    # All checks finish before publication. Only five aggregate artifact schemas are emitted.
    deciles = pd.DataFrame(score_deciles(mapping, data.y_validation, reported)).to_csv(index=False, lineterminator="\n")
    for name, value in artifacts.items():
        write_json(config.paths.metadata / name, value)
    csv_path = config.paths.metadata / "score_decile_analysis.csv"
    if not csv_path.exists() or csv_path.read_text(encoding="utf-8") != deciles:
        csv_path.write_text(deciles, encoding="utf-8", newline="\n")
    return {"validation_rows": len(reported), "transformed_features": len(rows),
            "additivity": explanation["additivity"], "score_summary": summary,
            "score_point_decomposition": decompositions, "test_set_evaluated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = run_explainability(args.project_root)
    except (AcquisitionError, OSError, ValueError) as exc:
        parser.exit(1, f"Explainability failed: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
    print("TEST SET REMAINS SEALED.")


if __name__ == "__main__":
    main()
