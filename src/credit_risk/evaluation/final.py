"""Evaluate the frozen Phase-3 TEST once; reproduce without replacing publication."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import csv
import io
import json
from pathlib import Path
import subprocess

import numpy as np

from credit_risk.config import load_config
from credit_risk.data.download import sha256_file
from credit_risk.data.source import TARGET
from credit_risk.features.definitions import FAIRNESS_REVIEW_FIELDS
from credit_risk.features.engineering import engineer_features, select_primary_features
from credit_risk.features.prepare import verify_dataset_manifest
from credit_risk.features.preprocessing import transform_split
from credit_risk.features.split import split_dataset
from credit_risk.modeling.artifacts import load_model
from credit_risk.modeling.baseline import raw_probabilities as logistic_probabilities
from credit_risk.modeling.calibration_metrics import probability_metrics, reliability
from credit_risk.modeling.contract import read_contracts
from credit_risk.modeling.thresholds import threshold_metrics
from credit_risk.modeling.xgboost_challenger import raw_probabilities as xgboost_probabilities
from credit_risk.explainability.score import rank_validation, score_summary
from credit_risk.service.runtime import load_runtime
from credit_risk.evaluation.diagnostics import bootstrap, ranking_tables, subgroup_metrics
from credit_risk.evaluation.reporting import report

VERSION = "final-test-evaluation-1.0.0"
RELEASE = "credit-risk-system-1.0.0"
POLICY = {"bootstrap_replicates": 1000, "bootstrap_seed": 42, "reliability_bins": 10,
          "shap_sample_count": 32, "shap_sample": "first rows in existing deterministic TEST order",
          "subgroup_minimum_count": 100, "subgroup_values": "literal raw codes and individual ages",
          "decile_order": "lowest score / highest modeled risk first; stable split-position ties"}


def read(root, name):
    return json.loads((root / "data/metadata" / (name + ".json")).read_text(encoding="utf-8"))


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def csv_bytes(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode()


def frozen_contract(root):
    """Verify identities and load trusted objects without opening a dataset partition."""
    config = load_config(root)
    runtime = load_runtime(root)
    phase3 = read_contracts(config.paths.metadata)
    split = phase3["split_manifest"]
    if (config.random_seed != split["random_seed"] or config.target_column != TARGET or
            any(split[k] != v for k, v in asdict(config.split).items())):
        raise ValueError("Frozen split configuration changed")
    baseline = read(root, "baseline_model_manifest")
    calibration = read(root, "calibration_manifest")["models"]["logistic"]
    for key in ("dataset_sha256", "split_version", "feature_engineering_version", "preprocessing_version"):
        if baseline[key] != runtime.model_manifest[key]:
            raise ValueError("Baseline comparison identity disagrees")
    if (baseline["preprocessing_artifact_sha256"] != runtime.preprocessing_manifest["serialization_sha256"] or
            calibration["underlying_model_artifact_sha256"] != baseline["artifact_sha256"] or
            calibration["underlying_model_version"] != baseline["model_version"] or
            calibration["method"] != "identity" or calibration["selected_method"] != "identity" or
            calibration["artifact_relative_path"] is not None or calibration["artifact_sha256"] is not None):
        raise ValueError("Frozen baseline/calibration disagrees")
    baseline_path = (root / baseline["artifact_relative_path"]).resolve()
    if not baseline_path.is_relative_to(config.paths.artifacts):
        raise ValueError("Baseline must be inside trusted artifact storage")
    logistic = load_model(baseline_path, baseline["artifact_sha256"])
    if logistic.n_features_in_ != 103 or logistic.get_params() != baseline["model_parameters"]:
        raise ValueError("Frozen Logistic parameters/width disagree")
    threshold = read(root, "phase6_model_selection")["technical_threshold"]
    if threshold["model"] != "xgboost" or threshold["technical_threshold_source"] != "train_oof_max_ks":
        raise ValueError("Frozen TRAIN OOF threshold required")
    metadata = {p.relative_to(root).as_posix(): sha256_file(p) for p in sorted(config.paths.metadata.iterdir())
                if p.is_file() and not p.name.startswith("final_") and p.name != ".gitkeep"}
    # Explicit inference/evaluation dependencies, not a broad modeling-directory digest.
    source_names = ["config.py", "data/source.py", "data/load.py", "data/schema.py", "data/download.py",
                    "features/definitions.py", "features/engineering.py", "features/preprocessing.py",
                    "features/prepare.py", "features/split.py", "modeling/artifacts.py", "modeling/baseline.py",
                    "modeling/xgboost_challenger.py", "modeling/contract.py", "modeling/metrics.py",
                    "modeling/calibration_metrics.py", "modeling/thresholds.py", "service/runtime.py",
                    "explainability/contract.py", "explainability/aggregation.py", "explainability/score.py",
                    "explainability/shap_explainer.py", "evaluation/final.py", "evaluation/diagnostics.py", "evaluation/reporting.py"]
    sources = {"src/credit_risk/" + name: sha256_file(root / "src/credit_risk" / name) for name in source_names}
    files = {**metadata, **sources}
    for relative in (baseline["artifact_relative_path"], runtime.model_manifest["artifact_relative_path"],
                     runtime.preprocessing_manifest["serialization_artifact_path"], "configs/base.yaml",
                     "configs/experiment.yaml", "configs/explainability.yaml", "configs/calibration.yaml"):
        files[relative] = sha256_file(root / relative)
    api, ops = read(root, "api_manifest"), read(root, "operations_manifest")
    identity = {"evaluation_version": VERSION, "dataset_sha256": runtime.dataset_manifest["sha256"],
                "split_version": split["split_version"], "split_seed": split["random_seed"], "test_count": split["test_rows"],
                "feature_engineering_version": baseline["feature_engineering_version"],
                "preprocessing_version": baseline["preprocessing_version"],
                "preprocessor_sha256": baseline["preprocessing_artifact_sha256"],
                "models": {"logistic": {"version": baseline["model_version"], "sha256": baseline["artifact_sha256"],
                                        "calibration_version": calibration["calibration_version"], "calibration_method": "identity"},
                           "xgboost": {"version": runtime.model_manifest["model_version"], "sha256": runtime.model_manifest["artifact_sha256"],
                                       "calibration_version": runtime.calibration["calibration_version"], "calibration_method": "identity"}},
                "selected_model": "xgboost", "explainability_version": runtime.explanation_manifest["explainability_version"],
                "score_version": runtime.mapping.version, "score_parameters": asdict(runtime.mapping),
                "technical_threshold": {"value": threshold["threshold"], "source": threshold["technical_threshold_source"],
                                        "identity": "phase6_model_selection.json SHA-256", "sha256": metadata["data/metadata/phase6_model_selection.json"]},
                "api_version": api["api_version"], "service_version": api["service_version"],
                "database_schema_revision": api["database_schema_revision"], "operations_version": ops["operations_version"],
                "monitoring_baseline_version": ops["monitoring_baseline_version"], "policy": POLICY, "readonly_sha256": files}
    return identity, runtime, logistic


def assert_readonly(root, identity):
    if any(sha256_file(root / name) != digest for name, digest in identity["readonly_sha256"].items()):
        raise ValueError("Frozen file changed during evaluation; publication stopped")


def snapshot(root, identity):
    path = root / "data/metadata/final_pre_unseal_snapshot.json"
    if path.exists():
        value = json.loads(path.read_text(encoding="utf-8"))
        if value["frozen_contract"] != identity:
            raise ValueError("Pre-unseal identity changed; owner review required")
        return value
    if list((root / "data/metadata").glob("final_test_*")) or (root / "data/metadata/final_release_manifest.json").exists():
        raise ValueError("Existing results without pre-unseal snapshot; stop")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    value = {"git_head_before_unsealing": head, "recorded_at": datetime.now(timezone.utc).isoformat(),
             "frozen_contract": identity, "test_probabilities_computed_at_snapshot": False}
    with path.open("xb") as stream:
        stream.write(json_bytes(value))
    return value


def evaluate(root, identity, runtime, logistic):
    """Open existing TEST once; only transform/predict; arrays never leave this function."""
    config = load_config(root)
    canonical, digest = verify_dataset_manifest(root)
    if digest != identity["dataset_sha256"]:
        raise ValueError("Frozen dataset checksum disagrees")
    partitions = split_dataset(canonical, config.split, config.random_seed)
    test = partitions.pop("test")
    del partitions, canonical
    split = read(root, "split_manifest")
    if len(test) != 4500 or len(test) != identity["test_count"] or int(test[TARGET].sum()) != split["test_positive_count"]:
        raise ValueError("Frozen TEST population disagrees")
    primary = select_primary_features(test)
    review = test.loc[:, list(FAIRNESS_REVIEW_FIELDS)].copy()
    if not review.index.equals(primary.index):
        raise ValueError("Demographic review alignment changed")
    X = transform_split(runtime.preprocessor, engineer_features(primary))
    y = test[TARGET].to_numpy(dtype=int)
    del test, primary
    if X.shape != (4500, 103):
        raise ValueError("Frozen TEST matrix shape disagrees")
    raw = {"logistic": logistic_probabilities(logistic, X), "xgboost": xgboost_probabilities(runtime.model, X)}
    reported = {name: p.copy() for name, p in raw.items()}  # Verified metadata-only identity mappings.
    equality = {name: float(np.max(np.abs(raw[name] - reported[name]))) for name in raw}
    repeated = {"logistic": logistic_probabilities(logistic, X), "xgboost": xgboost_probabilities(runtime.model, X)}
    if any(not np.array_equal(raw[name], repeated[name]) for name in raw):
        raise ValueError("Frozen predictions are not deterministic")
    metrics = {name: probability_metrics(y, p, POLICY["reliability_bins"]) for name, p in reported.items()}
    p = reported["xgboost"]
    deciles, lift = ranking_tables(runtime.mapping, y, p)
    sample = X[:POLICY["shap_sample_count"]]
    shap = runtime.explainer.explain(sample)
    points = runtime.mapping.decompose(shap["base"], shap["values"], shap["raw_probability"],
                                     calibration_method="identity", tolerance=runtime.options["score_tolerance"])
    shap_summary = {key: shap[key] for key in ("additivity", "probability_reconstruction", "shap_linked_probability_reconstruction")}
    shap_summary.update(sample_count=sample.shape[0], sample_policy=POLICY["shap_sample"],
                        score_point_decomposition_supported=points["score_point_decomposition_supported"],
                        score_point_max_absolute_residual=points["max_absolute_residual"],
                        score_point_mean_absolute_residual=points["mean_absolute_residual"])
    reliability_rows = [{"model": name, **row} for name, prob in reported.items()
                        for row in reliability(y, prob, POLICY["reliability_bins"])["bins"]]
    result = {"evaluation_version": VERSION, "frozen_contract": identity, "dataset_sha256": digest,
              "test_count": len(y), "negative_count": int((y == 0).sum()), "positive_count": int(y.sum()),
              "observed_default_rate": float(y.mean()), "models": metrics,
              "raw_reported_max_absolute_difference": equality, "repeat_predictions_exact": True,
              "bootstrap": bootstrap(y, reported["logistic"], p, seed=POLICY["bootstrap_seed"], replicates=POLICY["bootstrap_replicates"]),
              "paired_deltas_xgboost_minus_logistic": {k: metrics["xgboost"][k] - metrics["logistic"][k]
                                                       for k in ("roc_auc", "average_precision", "ks", "brier_score", "log_loss")},
              "technical_threshold": {"label": "TECHNICAL REFERENCE ONLY", "business_policy": False,
                                      **threshold_metrics(y, p, identity["technical_threshold"]["value"])},
              "score_summary": score_summary(runtime.mapping, p), "score_validation": rank_validation(runtime.mapping, y, p),
              "shap_technical_validation": shap_summary, "test_set_evaluated": True,
              "customer_level_test_artifacts_exported": False}
    if result["score_validation"]["inverse_max_absolute_error"] > 1e-12 or result["score_summary"]["probability_clipping_count"]:
        raise ValueError("Unexpected score clipping or inverse residual")
    assert_readonly(root, identity)
    return result, {"final_test_reliability.csv": reliability_rows, "final_test_score_deciles.csv": deciles,
                    "final_test_lift.csv": lift, "final_test_subgroup_metrics.csv": subgroup_metrics(review, y, p, minimum_count=POLICY["subgroup_minimum_count"])}


def publish(outputs, *, verify_existing=False):
    """Preflight the whole bundle; never overwrite any file, including partial bundles."""
    present = [p.exists() for p in outputs]
    if any(present):
        if not all(present):
            raise ValueError("Incomplete final publication; investigate rather than repair silently")
        if any(p.read_bytes() != content for p, content in outputs.items()):
            raise ValueError("Final identity/result differs; publication is immutable")
        return "verified_existing"
    if verify_existing:
        raise ValueError("No existing final evaluation to verify")
    # Exclusive creation makes concurrent writers fail closed. Interrupted publication
    # is deliberately detected as incomplete on rerun, never silently filled in.
    for path, content in outputs.items():
        with path.open("xb") as stream:
            stream.write(content)
    return "published"


def run(root, *, verify_existing=False, snapshot_only=False):
    root = Path(root).resolve()
    identity, runtime, logistic = frozen_contract(root)
    if verify_existing and not (root / "data/metadata/final_test_metrics.json").exists():
        raise ValueError("No existing final evaluation to verify")
    before = snapshot(root, identity)
    if snapshot_only:
        return {"status": "pre_unseal_snapshot_verified", "test_set_evaluated": False}
    existing = root / "data/metadata/final_test_metrics.json"
    old = json.loads(existing.read_text(encoding="utf-8")) if existing.exists() else None
    if old is not None and old["frozen_contract"] != identity:
        raise ValueError("Final identity differs before TEST loading")
    result, tables = evaluate(root, identity, runtime, logistic)
    result["generated_at"] = old["generated_at"] if old else datetime.now(timezone.utc).isoformat()
    result["pre_unseal_git_head"] = before["git_head_before_unsealing"]
    ops = read(root, "operations_manifest")
    release = {"release_version": RELEASE, "generated_at": result["generated_at"], "frozen_contract": identity,
               "dataset": "UCI Default of Credit Card Clients (350), pinned 2005 workbook snapshot",
               "docker_runtime_information": {"image": "creditrisk-api:phase9", "base": "python:3.14.6-slim-bookworm",
                                              "operations_validated_runtime": ops["validated_runtime"], "workers": 1,
                                              "artifact_delivery": "read_only_mount"},
               "test_set_evaluated": True, "business_decision_defined": False, "regulatory_validation": False,
               "customer_level_test_artifacts_exported": False}
    outputs = {root / "data/metadata/final_test_metrics.json": json_bytes(result),
               root / "data/metadata/final_release_manifest.json": json_bytes(release)}
    outputs.update({root / "data/metadata" / name: csv_bytes(rows) for name, rows in tables.items()})
    validation = {name: values["validation_reported"] for name, values in read(root, "calibration_metrics")["models"].items()}
    outputs[root / "docs/final_evaluation_report.md"] = report(result, tables, validation)
    status = publish(outputs, verify_existing=verify_existing)
    return {"status": status, "test_count": result["test_count"], "models": result["models"], "test_set_evaluated": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--verify-existing", action="store_true")
    parser.add_argument("--snapshot-only", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.project_root, verify_existing=args.verify_existing, snapshot_only=args.snapshot_only)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Final evaluation stopped: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
