"""Synthetic diagnostics and explicit, no-fit reproduction of published TEST aggregates."""

import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from credit_risk.evaluation import final
from credit_risk.evaluation.diagnostics import bootstrap, ranking_tables, subgroup_metrics
from credit_risk.explainability.score import InternalScore
from credit_risk.features.definitions import FAIRNESS_REVIEW_FIELDS, PRIMARY_MODEL_FEATURES

ROOT = Path(__file__).resolve().parents[1]


def require_local_artifacts(*, raw=False):
    from credit_risk.data.source import RAW_FILENAME
    manifests = (final.read(ROOT, "baseline_model_manifest"), final.read(ROOT, "xgboost_model_manifest"),
                 final.read(ROOT, "preprocessing_manifest"))
    paths = [ROOT / m.get("artifact_relative_path", m.get("serialization_artifact_path")) for m in manifests]
    if raw:
        paths.append(ROOT / "data/raw" / RAW_FILENAME)
    if not all(p.is_file() for p in paths):
        pytest.skip("Trusted ignored frozen artifacts/raw data unavailable; never train replacements")


def test_bootstrap_paired_deterministic_and_sign():
    y = np.tile([0, 1], 30)
    poor, good = np.full(len(y), .5), np.where(y, .8, .2)
    result = bootstrap(y, poor, good, replicates=40)
    assert result == bootstrap(y, poor, good, replicates=40)
    assert result["successful_replicates"] == 40
    for key in ("roc_auc", "average_precision"):
        assert result["delta_xgboost_minus_logistic_95_ci"][key][0] > 0
    for key in ("brier_score", "log_loss"):
        assert result["delta_xgboost_minus_logistic_95_ci"][key][1] < 0
    identical = bootstrap(y, good, good, replicates=20)
    assert all(ci == [0., 0.] for ci in identical["delta_xgboost_minus_logistic_95_ci"].values())


def test_bootstrap_skips_degenerate_rows():
    result = bootstrap([0, 1], [.2, .8], [.1, .9], replicates=40)
    assert 0 < result["skipped_single_class"] < 40
    assert result["successful_replicates"] + result["skipped_single_class"] == 40


@pytest.mark.parametrize("count", [0, -1, 1.5, True])
def test_bootstrap_invalid_count(count):
    with pytest.raises(ValueError):
        bootstrap([0, 1], [.2, .8], [.1, .9], replicates=count)


def test_deciles_and_lift_orientation_ties_and_coverage():
    y = np.tile([0, 1], 25)
    p = np.repeat(np.linspace(.05, .95, 10), 5)
    deciles, lift = ranking_tables(InternalScore(), y, p)
    assert sum(row["count"] for row in deciles) == len(y)
    assert all(row["count"] == 5 for row in deciles)
    assert all(a["max_score"] <= b["min_score"] for a, b in zip(deciles, deciles[1:]))
    assert lift[-1]["cumulative_defaults_captured"] == int(y.sum())
    assert lift[-1]["cumulative_population_percentage"] == 100
    assert lift[-1]["cumulative_lift"] == 1
    assert (deciles, lift) == ranking_tables(InternalScore(), y, p)


def test_subgroups_literal_categories_minimum_and_single_class():
    review = pd.DataFrame({name: [0] * 100 + [5] * 100 + [6] for name in FAIRNESS_REVIEW_FIELDS})
    y = np.array([0] * 100 + [0, 1] * 50 + [1])
    rows = subgroup_metrics(review, y, np.full(201, .3))
    assert len(rows) == 12
    assert set(FAIRNESS_REVIEW_FIELDS).isdisjoint(PRIMARY_MODEL_FEATURES)
    for row in rows:
        if row["raw_value"] == 6:
            assert row["status"] == "insufficient_sample"
            assert row["roc_auc"] is None and row["brier_score"] is None
        elif row["raw_value"] == 0:
            assert row["status"] == "single_class_auc_undefined"
            assert row["roc_auc"] is None and row["brier_score"] == pytest.approx(.09)
        else:
            assert row["status"] == "sufficient" and row["roc_auc"] == .5


def test_subgroup_alignment_shape_rejected():
    with pytest.raises(ValueError, match="Aligned"):
        subgroup_metrics(pd.DataFrame({"sex": [1, 2]}), [0, 1], [.2, .8])


def test_publication_immutable_timestamp_and_whole_bundle(tmp_path):
    outputs = {tmp_path / "a.json": b'{"generated_at":"original"}\n', tmp_path / "b.csv": b"count\n10\n"}
    assert final.publish(outputs) == "published"
    times = {p: p.stat().st_mtime_ns for p in outputs}
    assert final.publish(outputs, verify_existing=True) == "verified_existing"
    assert times == {p: p.stat().st_mtime_ns for p in outputs}
    changed = {**outputs, tmp_path / "b.csv": b"count\n11\n"}
    with pytest.raises(ValueError, match="immutable"):
        final.publish(changed)
    assert all(p.read_bytes() == value for p, value in outputs.items())


def test_partial_publication_rejected(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"original")
    with pytest.raises(ValueError, match="Incomplete"):
        final.publish({first: b"original", second: b"new"})
    assert not second.exists()


def test_verify_missing_rejected(tmp_path):
    with pytest.raises(ValueError, match="No existing"):
        final.publish({tmp_path / "missing": b"value"}, verify_existing=True)
    assert not list(tmp_path.iterdir())


def test_snapshot_identity_mismatch_fails_before_dataset_loading(tmp_path):
    metadata = tmp_path / "data/metadata"
    metadata.mkdir(parents=True)
    path = metadata / "final_pre_unseal_snapshot.json"
    path.write_text(json.dumps({"frozen_contract": {"model": "original"}}))
    with pytest.raises(ValueError, match="Pre-unseal identity changed"):
        final.snapshot(tmp_path, {"model": "different"})
    assert json.loads(path.read_text())["frozen_contract"]["model"] == "original"


def test_readonly_guard_detects_mutation(tmp_path):
    path = tmp_path / "model"
    path.write_bytes(b"frozen")
    identity = {"readonly_sha256": {"model": final.sha256_file(path)}}
    final.assert_readonly(tmp_path, identity)
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Frozen file changed"):
        final.assert_readonly(tmp_path, identity)


@pytest.fixture
def published():
    path = ROOT / "data/metadata/final_test_metrics.json"
    if not path.exists():
        pytest.skip("Final TEST has not been explicitly published; tests never unseal it automatically")
    return json.loads(path.read_text())


def test_real_no_fit_no_threshold_selection_and_reproduction(published, monkeypatch):
    require_local_artifacts(raw=True)
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.isotonic import IsotonicRegression
    from credit_risk.modeling.calibrators import ProbabilityCalibrator
    from credit_risk.modeling import thresholds, calibration_metrics
    import xgboost
    import xgboost.training
    def forbidden(*args, **kwargs):
        raise AssertionError("Final evaluation must never fit, train, select or optimize")
    for cls in (Pipeline, ColumnTransformer, LogisticRegression, IsotonicRegression,
                ProbabilityCalibrator, xgboost.XGBClassifier):
        monkeypatch.setattr(cls, "fit", forbidden)
        if hasattr(cls, "fit_transform"):
            monkeypatch.setattr(cls, "fit_transform", forbidden)
    monkeypatch.setattr(xgboost, "train", forbidden)
    monkeypatch.setattr(xgboost.training, "train", forbidden)
    monkeypatch.setattr(xgboost.Booster, "update", forbidden)
    monkeypatch.setattr(xgboost.Booster, "boost", forbidden)
    monkeypatch.setattr(thresholds, "select_train_threshold", forbidden)
    monkeypatch.setattr(calibration_metrics, "downstream_status", forbidden)
    paths = list((ROOT / "data/metadata").glob("final_*")) + [ROOT / "docs/final_evaluation_report.md"]
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
    identity = published["frozen_contract"]
    final.assert_readonly(ROOT, identity)
    result = final.run(ROOT, verify_existing=True)
    assert result["status"] == "verified_existing" and result["test_count"] == 4500
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
    final.assert_readonly(ROOT, identity)


def test_real_metrics_score_threshold_and_identity(published):
    r = published
    assert r["test_count"] == r["positive_count"] + r["negative_count"] == 4500
    assert r["repeat_predictions_exact"]
    assert r["raw_reported_max_absolute_difference"] == {"logistic": 0., "xgboost": 0.}
    for m in r["models"].values():
        assert all(np.isfinite(v) for v in m.values())
        assert m["gini"] == 2 * m["roc_auc"] - 1
    assert r["score_validation"]["inverse_ranking_verified"]
    assert r["score_validation"]["auc_absolute_difference"] <= 1e-12
    assert r["score_validation"]["inverse_max_absolute_error"] <= 1e-12
    assert r["score_summary"]["probability_clipping_count"] == 0
    assert r["technical_threshold"]["threshold"] == final.read(ROOT, "phase6_model_selection")["technical_threshold"]["threshold"]
    assert sum(r["technical_threshold"][k] for k in ("tn", "fp", "fn", "tp")) == 4500
    assert r["frozen_contract"]["selected_model"] == "xgboost"


def test_real_corrupt_model_preprocessor_hashes_rejected(published, tmp_path):
    require_local_artifacts()
    for directory in ("configs", "data/metadata", "src/credit_risk", "artifacts/models", "artifacts/preprocessing"):
        shutil.copytree(ROOT / directory, tmp_path / directory, ignore=shutil.ignore_patterns("__pycache__"))
    manifests = (final.read(tmp_path, "baseline_model_manifest"), final.read(tmp_path, "xgboost_model_manifest"),
                 final.read(tmp_path, "preprocessing_manifest"))
    for manifest in manifests:
        relative = manifest.get("artifact_relative_path", manifest.get("serialization_artifact_path"))
        path = tmp_path / relative
        content = path.read_bytes()
        path.write_bytes(content + b"corrupt")
        with pytest.raises(ValueError, match="checksum"):
            final.frozen_contract(tmp_path)
        path.write_bytes(content)


def test_real_aggregate_artifact_privacy(published):
    forbidden = {"customer_id", "row_index", "labels", "raw_predictor_values", "shap_values", "probabilities", "scores"}
    def inspect(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for item in value.values():
                inspect(item)
        elif isinstance(value, list):
            assert len(value) < 1000
            for item in value:
                inspect(item)
    for path in (ROOT / "data/metadata").glob("final_*"):
        if path.suffix == ".json":
            inspect(json.loads(path.read_text()))
        else:
            frame = pd.read_csv(path)
            assert len(frame) < 1000
            assert not forbidden.intersection(frame.columns)
            assert not set(PRIMARY_MODEL_FEATURES).intersection(frame.columns)
    subgroup = pd.read_csv(ROOT / "data/metadata/final_test_subgroup_metrics.csv")
    assert all(n == 4500 for n in subgroup.groupby("field")["count"].sum())
    assert subgroup.loc[subgroup["count"] < 100, "roc_auc"].isna().all()
