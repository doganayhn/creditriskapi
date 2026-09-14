"""Synthetic Phase-6 isolation, selection, reliability and serialization checks."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from sklearn.model_selection import StratifiedKFold
import yaml

from credit_risk.config import load_config
from credit_risk.features.definitions import NUMERIC_FEATURES, CATEGORICAL_FEATURES
from credit_risk.modeling import baseline, calibration, calibrators, calibration_metrics as metrics
from credit_risk.modeling import contract, thresholds, xgboost_challenger as challenger
from test_modeling import model_project
from test_xgboost import settings, xgb_project, parameters


@pytest.mark.parametrize("method", calibrators.METHODS)
def test_mapping_monotonic_bounded_and_input_unchanged(method):
    p = np.linspace(0, 1, 80)
    y = np.tile([0, 0, 1, 1], 20)
    original = p.copy()
    mapping = calibrators.ProbabilityCalibrator(method).fit(p, y)
    actual = mapping.transform(p)
    assert np.isfinite(actual).all() and ((actual >= 0) & (actual <= 1)).all()
    assert (np.diff(actual) >= 0).all()
    np.testing.assert_array_equal(p, original)
    if method == "identity":
        np.testing.assert_array_equal(actual, p)
    if method == "sigmoid":
        assert mapping.slope_ >= 0


@pytest.mark.parametrize("method", calibrators.METHODS)
@pytest.mark.parametrize("bad", [[np.nan, .3], [np.inf, .3], [-.1, .3], [.3, 1.1], [.3], [[.3], [.4]]])
def test_invalid_mapping_input_rejected(method, bad):
    with pytest.raises(ValueError):
        calibrators.ProbabilityCalibrator(method).fit(bad, [0, 1])


@pytest.mark.parametrize("method", calibrators.METHODS)
def test_mapping_unfitted_and_single_class_rejected(method):
    mapping = calibrators.ProbabilityCalibrator(method)
    with pytest.raises(ValueError, match="not fitted"):
        mapping.transform([.2, .8])
    with pytest.raises(ValueError):
        mapping.fit([.2, .8], [1, 1])


def test_isotonic_out_of_range_clips_and_sigmoid_cannot_reverse():
    mapping = calibrators.ProbabilityCalibrator("isotonic").fit([.2, .4, .6, .8], [0, 0, 1, 1])
    np.testing.assert_array_equal(mapping.transform([0, .2, .8, 1]), [0, 0, 1, 1])
    reverse = calibrators.ProbabilityCalibrator("sigmoid").fit([.1, .2, .8, .9], [1, 1, 0, 0])
    assert reverse.slope_ == pytest.approx(0)
    np.testing.assert_allclose(reverse.transform([0, 1]), [.5, .5], atol=1e-8)


def test_failed_sigmoid_optimizer_is_not_silenced(monkeypatch):
    monkeypatch.setattr(calibrators, "minimize", lambda *a, **k: SimpleNamespace(success=False, message="forced"))
    with pytest.raises(ValueError, match="did not converge"):
        calibrators.ProbabilityCalibrator("sigmoid").fit([.2, .8], [0, 1])


@pytest.mark.parametrize("method", calibrators.METHODS)
def test_artifact_roundtrip_hash_and_identity_no_binary(tmp_path, method):
    p = np.linspace(0, 1, 40)
    mapping = calibrators.ProbabilityCalibrator(method).fit(p, np.arange(40) % 2)
    path, digest = calibrators.save_calibrator(mapping, tmp_path / "calibration", "test-1.0.0")
    if method == "identity":
        assert path is digest is None and not (tmp_path / "calibration").exists()
        return
    loaded = calibrators.load_calibrator(path, digest)
    np.testing.assert_allclose(mapping.transform(p), loaded.transform(p), rtol=0, atol=1e-12)
    assert calibrators.save_calibrator(mapping, path.parent, "test-1.0.0") == (path, digest)
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        calibrators.load_calibrator(path, digest)


def test_selection_priority_tolerance_and_simplicity():
    rows = {name: {"mean_brier_score": .2, "mean_log_loss": .5} for name in calibrators.METHODS}
    assert calibration.choose_method(rows, 1e-12) == "identity"
    rows["sigmoid"]["mean_log_loss"] = .4
    assert calibration.choose_method(rows, 1e-12) == "sigmoid"
    rows["isotonic"]["mean_brier_score"] = .19
    assert calibration.choose_method(rows, 1e-12) == "isotonic"
    rows["isotonic"]["mean_brier_score"] = .2 - 1e-13
    assert calibration.choose_method(rows, 1e-12) == "sigmoid"
    rows["identity"]["mean_brier_score"] = np.nan
    with pytest.raises(ValueError, match="finite"):
        calibration.choose_method(rows, 1e-12)


def test_reliability_known_weighted_ece_and_tied_edges():
    result = metrics.reliability([0, 0, 1, 1], [.1, .2, .7, .9], bins=2)
    assert result["ece"] == pytest.approx(.175)
    assert [r["count"] for r in result["bins"]] == [2, 2]
    constant = metrics.reliability([0, 0, 0, 1], [.5] * 4)
    assert constant["actual_nonempty_bins"] == 1 and constant["ece"] == .25
    tied = metrics.reliability([0, 1, 0, 1, 1, 0], [.1, .1, .1, .8, .8, .8])
    assert tied["actual_nonempty_bins"] <= 2
    assert sum(r["count"] for r in tied["bins"]) == 6
    assert all(r["minimum_probability"] == r["maximum_probability"] for r in tied["bins"])


def test_downstream_pareto_requires_no_metric_regression():
    base = dict(roc_auc=.7, average_precision=.5, brier_score=.2, log_loss=.5)
    better = dict(roc_auc=.8, average_precision=.5, brier_score=.19, log_loss=.4)
    assert metrics.downstream_status(base, better) == "XGBOOST_SELECTED_FOR_DOWNSTREAM"
    assert metrics.downstream_status(better, base) == "LOGISTIC_SELECTED_FOR_DOWNSTREAM"
    assert metrics.downstream_status(base, base) == "MIXED_VALIDATION_RESULT"
    assert metrics.downstream_status(base, {**better, "log_loss": .6}) == "MIXED_VALIDATION_RESULT"


def test_threshold_tie_confusion_grid_and_reference():
    y, p = [1, 0, 1, 0], [.9, .8, .7, .6]
    threshold = thresholds.select_train_threshold(y, p)
    assert threshold == .9  # J=.5 at .9 and .7: take the highest threshold.
    result = thresholds.threshold_metrics(y, p, .7)
    assert [result[k] for k in ("tn", "fp", "fn", "tp")] == [1, 1, 0, 2]
    assert result["precision"] == pytest.approx(2/3) and result["recall"] == 1
    rows = thresholds.train_threshold_table(y, p, threshold)
    assert {r["threshold"] for r in rows} == set(thresholds.THRESHOLD_GRID)
    assert sum(r["is_max_ks"] for r in rows) == sum(r["is_reference"] for r in rows) == 1
    assert all(r["source"] == "train_oof" and r["test_set_evaluated"] is False for r in rows)


def test_quality_bootstrap_paired_sign_reproducibility_and_skips():
    result = metrics.paired_quality_bootstrap([0, 1], [.9, .1], [.1, .9], 42, 60)
    assert result == metrics.paired_quality_bootstrap([0, 1], [.9, .1], [.1, .9], 42, 60)
    np.testing.assert_allclose(result["delta_brier_score_95_ci"], [-.8, -.8])
    assert result["delta_log_loss_95_ci"][1] < 0
    assert result["delta_roc_auc_95_ci"] == [1, 1]
    assert result["successful_replicates"] + result["skipped_single_class"] == 60
    assert result["skipped_single_class"] > 0


@pytest.mark.parametrize("name", ["logistic", "xgboost"])
def test_oof_fold_local_statistics_exclusion_coverage_and_repeat(xgb_project, settings, monkeypatch, name):
    data = contract.load_modeling_data(xgb_project)
    X = challenger.load_training_features(xgb_project, data)
    special = X.index[0]
    X.loc[special, CATEGORICAL_FEATURES[0]] = "status_9"
    X.loc[special, NUMERIC_FEATURES[0]] = 1e9
    original_build = calibration.build_preprocessor
    expected = list(StratifiedKFold(2, shuffle=True, random_state=42).split(X, data.y_train))
    fit_indices, transformed_indices = [], []
    def build():
        pipeline = original_build()
        original_fit, original_transform = pipeline.fit, pipeline.transform
        def fit(frame, y=None):
            assert y is None
            result = original_fit(frame)
            fit_indices.append(set(frame.index))
            columns = pipeline.named_steps["columns"]
            medians = columns.named_transformers_["numeric"].named_steps["imputer"].statistics_
            np.testing.assert_allclose(medians, frame.loc[:, list(NUMERIC_FEATURES)].median())
            vocab = columns.named_transformers_["repayment"].named_steps["encoder"].categories_[0]
            assert ("status_9" in vocab) == (special in frame.index)
            return result
        def transform(frame):
            transformed_indices.append(set(frame.index))
            return original_transform(frame)
        pipeline.fit, pipeline.transform = fit, transform
        return pipeline
    monkeypatch.setattr(calibration, "build_preprocessor", build)
    first, summary = calibration.generate_oof(X, data.y_train, name, parameters(settings), settings, 42, 2)
    second, repeated = calibration.generate_oof(X, data.y_train, name, parameters(settings), settings, 42, 2)
    np.testing.assert_array_equal(first, second)
    assert summary == repeated and summary["every_row_exactly_once"]
    assert summary["coverage_min"] == summary["coverage_max"] == 1
    assert fit_indices == [set(X.iloc[train].index) for train, _ in expected] * 2
    for i, fit_set in enumerate(fit_indices):
        assert transformed_indices[i * 2] == fit_set
        assert not fit_set & transformed_indices[i * 2 + 1]
        assert fit_set | transformed_indices[i * 2 + 1] == set(X.index)


def test_selection_cv_fit_rows_exclude_holdout_and_final_fit(monkeypatch):
    p, y = np.linspace(.01, .99, 100), np.arange(100) % 2
    config = calibration.load_settings(Path(__file__).resolve().parents[1])
    fits = []
    original = calibrators.ProbabilityCalibrator.fit
    def fit(self, probability, target):
        fits.append((self.method, probability.copy(), target.copy()))
        return original(self, probability, target)
    monkeypatch.setattr(calibrators.ProbabilityCalibrator, "fit", fit)
    mapping, summaries = calibration.select_calibrator(p, y, config, 42)
    folds = list(StratifiedKFold(5, shuffle=True, random_state=42).split(p, y))
    for i, (name, probability, target) in enumerate(fits[:-1]):
        train, holdout = folds[i % 5]
        np.testing.assert_array_equal(probability, p[train])
        np.testing.assert_array_equal(target, y[train])
        assert not set(probability) & set(p[holdout])
    assert len(fits) == 16 and len(fits[-1][1]) == 100
    assert set(summaries) == set(calibrators.METHODS) and mapping.fit_rows_ == 100


def test_orchestration_freezes_before_validation_and_rejects_metadata(xgb_project, monkeypatch):
    challenger.run_challenger(xgb_project)
    config = calibration.load_settings(Path(__file__).resolve().parents[1])
    config.update(oof_folds=2, selection_folds=2, bootstrap_replicates=20)
    (xgb_project / "configs/calibration.yaml").write_text(yaml.safe_dump(config))
    data = contract.load_modeling_data(xgb_project)
    assert not hasattr(data, "X_test") and not hasattr(data, "y_test")
    candidates = calibration.load_candidates(xgb_project, data)
    monkeypatch.setattr(calibration, "load_modeling_data", lambda root: data)
    monkeypatch.setattr(calibration, "load_candidates", lambda root, value: candidates)
    selected = []
    original_select = calibration.select_calibrator
    def select(p, y, settings, seed):
        assert y is data.y_train
        result = original_select(p, y, settings, seed)
        selected.append(result[0])
        return result
    monkeypatch.setattr(calibration, "select_calibrator", select)
    for module, name in ((baseline, "logistic"), (challenger, "xgboost")):
        original = module.raw_probabilities
        def predict(model, X, original=original, name=name):
            if model is candidates[name]["model"]:
                assert X is data.X_validation and len(selected) == 2
            return original(model, X)
        monkeypatch.setattr(module, "raw_probabilities", predict)
    original_threshold = calibration.select_train_threshold
    def threshold(y, p, tolerance):
        assert y is data.y_train and len(p) == len(data.y_train)
        return original_threshold(y, p, tolerance)
    monkeypatch.setattr(calibration, "select_train_threshold", threshold)
    result = calibration.run_calibration(xgb_project)
    assert result["test_set_evaluated"] is False
    metadata = load_config(xgb_project).paths.metadata
    record = json.loads((metadata / "calibration_manifest.json").read_text())
    assert record["validation_used_for_calibrator_fit"] is False
    assert record["validation_used_for_calibrator_selection"] is False
    assert all(row["fit_rows"] == len(data.y_train) for row in record["models"].values())
    # A stored validation mismatch is detected without allowing a method override.
    candidates["logistic"]["metrics"]["validation"]["roc_auc"] += .01
    selected.clear()
    with pytest.raises(ValueError, match="metric disagrees"):
        calibration.run_calibration(xgb_project)
    assert len(selected) == 2


def test_candidate_identity_mismatch_fails_before_prediction(xgb_project, monkeypatch):
    challenger.run_challenger(xgb_project)
    data = contract.load_modeling_data(xgb_project)
    metadata = load_config(xgb_project).paths.metadata
    for prefix in ("baseline", "xgboost"):
        path = metadata / f"{prefix}_model_manifest.json"
        original = json.loads(path.read_text())
        for field, value in (("dataset_sha256", "wrong"), ("model_version", "wrong"),
                             ("test_set_evaluated", True), ("preprocessing_version", "wrong")):
            path.write_text(json.dumps({**original, field: value}))
            with pytest.raises(ValueError):
                calibration.load_candidates(xgb_project, data)
        path.write_text(json.dumps(original))
