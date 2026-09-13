"""Offline Phase-4 model, contract, metric and test-sealing checks; synthetic rows only."""

import json
from pathlib import Path
from unittest.mock import Mock
import warnings

import numpy as np
import pandas as pd
import pytest
from scipy import sparse
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from credit_risk.config import load_config
from credit_risk.data.source import EXPECTED_SHA256, TARGET
from credit_risk.features import prepare
from credit_risk.features.definitions import BILL_COLUMNS, PAYMENT_COLUMNS, REPAYMENT_COLUMNS
from credit_risk.modeling import artifacts, baseline, contract, metrics


@pytest.fixture
def training():
    rng = np.random.default_rng(42)
    X = sparse.csr_matrix(rng.normal(size=(100, 4)))
    y = (X.toarray()[:, 0] + rng.normal(size=100) > 0).astype(int)
    return X, y


@pytest.fixture
def model_project(data_project, canonical_frame, monkeypatch):
    rows = pd.concat([canonical_frame.iloc[[0]]] * 200, ignore_index=True)
    rows["customer_id"] = pd.Series(range(1, 201), dtype="Int64")
    rows[TARGET] = (rows.customer_id % 5 == 0).astype("Int64")
    rows["credit_limit"] = rows.customer_id * 100
    for i, name in enumerate(BILL_COLUMNS + PAYMENT_COLUMNS):
        rows[name] = rows.customer_id * (i + 1)
    for i, name in enumerate(REPAYMENT_COLUMNS):
        rows[name] = (rows.customer_id + i) % 6 - 2
    monkeypatch.setattr(prepare, "verify_dataset_manifest", lambda root: (rows.copy(), EXPECTED_SHA256))
    prepare.run_preparation(data_project)
    metadata = load_config(data_project).paths.metadata
    identities = {name: contract.manifest_identity(json.loads((metadata / f"{name}.json").read_text()))
                  for name in contract.PHASE3_IDENTITIES}
    monkeypatch.setattr(contract, "PHASE3_IDENTITIES", identities)
    monkeypatch.setattr(baseline, "PHASE3_IDENTITIES", identities)
    return data_project


def test_model_specification():
    model = baseline.build_model()
    assert isinstance(model, LogisticRegression)
    assert model.l1_ratio == 0 and model.C == 1  # sklearn 1.8 L2 representation
    assert model.class_weight is None and model.solver == "lbfgs"
    assert model.fit_intercept and model.max_iter == 5000 and model.tol == 1e-8
    assert model.random_state is None and not model.warm_start


def test_training_convergence_and_probabilities(training):
    X, y = training
    model = baseline.fit_baseline(X, y)
    assert model.n_iter_[0] < model.max_iter
    probability = baseline.raw_probabilities(model, X)
    np.testing.assert_array_equal(probability, model.predict_proba(X)[:, 1])
    assert probability.shape == (100,) and np.isfinite(probability).all()
    assert ((0 <= probability) & (probability <= 1)).all()


@pytest.mark.parametrize("target", [np.zeros(100), np.full(100, 2), np.arange(99) % 2,
                                     np.full(100, np.nan), np.ones((100, 1))])
def test_bad_training_target_fails(training, target):
    with pytest.raises(ValueError, match="Target|target|classes"):
        baseline.fit_baseline(training[0], target)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_matrix_fails(training, value):
    X, y = training
    X.data[0] = value
    with pytest.raises(ValueError, match="NaN or infinity"):
        baseline.fit_baseline(X, y)


def test_empty_dense_and_mismatched_width_fail(training):
    X, y = training
    for bad in (X.toarray(), sparse.csr_matrix((0, 4)), sparse.csr_matrix((100, 0))):
        with pytest.raises(ValueError):
            baseline.fit_baseline(bad, y)
    model = baseline.fit_baseline(X, y)
    with pytest.raises(ValueError):
        baseline.raw_probabilities(model, X[:, :3])


def test_convergence_warning_is_failure(training, monkeypatch):
    def fail(self, X, y):
        warnings.warn("synthetic non-convergence", ConvergenceWarning)
    monkeypatch.setattr(LogisticRegression, "fit", fail)
    with pytest.raises(ValueError, match="failed to converge"):
        baseline.fit_baseline(*training)


def test_iteration_limit_without_warning_is_failure(training, monkeypatch):
    model = Mock(n_iter_=np.array([5000]), max_iter=5000)
    monkeypatch.setattr(baseline, "build_model", lambda: model)
    with pytest.raises(ValueError, match="iteration limit"):
        baseline.fit_baseline(*training)


def test_positive_class_selection_not_column_assumption(training):
    X, y = training
    model = baseline.fit_baseline(X, y)
    model.classes_ = np.array([1, 0])
    model.predict_proba = lambda X: np.tile([.8, .2], (X.shape[0], 1))
    np.testing.assert_array_equal(baseline.raw_probabilities(model, X), np.full(100, .8))


@pytest.mark.parametrize("probability", [[np.nan, .2], [-.1, .2], [.1, 1.1], [.1], [[.1], [.2]]])
def test_invalid_probability_rejected(probability):
    with pytest.raises(ValueError):
        metrics.evaluate([0, 1], probability)


def test_metrics_known_example_and_half_threshold():
    result = metrics.evaluate([0, 0, 1, 1], [.1, .5, .4, .9])
    assert result["roc_auc"] == .75
    assert result["average_precision"] == pytest.approx(5 / 6)
    assert result["ks"] == .5 and result["gini"] == .5
    assert result["brier_score"] == pytest.approx(.1575)
    assert result["log_loss"] == pytest.approx(-np.log([.9, .5, .4, .9]).mean())
    assert result["mean_predicted_probability"] == pytest.approx(.475)
    assert result["observed_positive_rate"] == .5
    assert metrics.REFERENCE_THRESHOLD == .5
    assert result["threshold_0_5"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1,
                                       "precision": .5, "recall": .5, "specificity": .5, "f1": .5}


def test_no_positive_predictions_defined_without_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = metrics.evaluate([0, 1], [.1, .2])["threshold_0_5"]
    assert result["precision"] == result["recall"] == result["f1"] == 0
    assert result["specificity"] == 1


def test_bootstrap_deterministic_and_single_class_skips():
    first = metrics.bootstrap_validation([0, 1], [.2, .8], 42, 100)
    assert first == metrics.bootstrap_validation([0, 1], [.2, .8], 42, 100)
    assert first["roc_auc_95_ci"] == [1, 1]
    assert first["average_precision_95_ci"] == [1, 1]
    assert 0 < first["bootstrap_successful_replicates"] < 100
    assert first["bootstrap_successful_replicates"] + first["bootstrap_skipped_single_class"] == 100
    with pytest.raises(ValueError, match="No two-class"):
        metrics.bootstrap_validation([0, 1], [.2, .8], 0, 1)


def test_determinism_and_serialization(training, tmp_path):
    X, y = training
    first, second = baseline.fit_baseline(X, y), baseline.fit_baseline(X, y)
    np.testing.assert_allclose(first.coef_, second.coef_, rtol=0, atol=1e-12)
    p1, p2 = baseline.raw_probabilities(first, X), baseline.raw_probabilities(second, X)
    np.testing.assert_allclose(p1, p2, rtol=0, atol=1e-12)
    assert metrics.evaluate(y, p1) == metrics.evaluate(y, p2)
    path, digest = artifacts.save_model(first, tmp_path, baseline.MODEL_VERSION)
    loaded = artifacts.load_model(path, digest)
    np.testing.assert_allclose(baseline.raw_probabilities(loaded, X), p1, rtol=0, atol=1e-12)
    assert artifacts.save_model(first, tmp_path, baseline.MODEL_VERSION) == (path, digest)
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        artifacts.load_model(path, digest)


@pytest.mark.parametrize("name", list(contract.PHASE3_IDENTITIES))
def test_contract_tampering_fails_before_data_access(model_project, monkeypatch, name):
    path = load_config(model_project).paths.metadata / f"{name}.json"
    value = json.loads(path.read_text())
    value["dataset_sha256"] = "changed"
    path.write_text(json.dumps(value))
    spy = Mock(side_effect=AssertionError("must fail before raw data access"))
    monkeypatch.setattr(prepare, "verify_dataset_manifest", spy)
    with pytest.raises(ValueError, match="identity disagrees"):
        contract.load_modeling_data(model_project)
    spy.assert_not_called()


def test_missing_contract_fails(model_project):
    (load_config(model_project).paths.metadata / "feature_manifest.json").unlink()
    with pytest.raises(ValueError, match="Missing/unreadable"):
        contract.load_modeling_data(model_project)


def test_configuration_drift_fails(model_project):
    path = model_project / "configs/base.yaml"
    path.write_text(path.read_text().replace("random_seed: 42", "random_seed: 43"))
    with pytest.raises(ValueError, match="seed"):
        contract.load_modeling_data(model_project)


def test_implementation_drift_fails(model_project, monkeypatch):
    monkeypatch.setattr(contract, "sha256_file", lambda path: "changed")
    with pytest.raises(ValueError, match="implementation disagrees"):
        contract.load_modeling_data(model_project)


def test_preprocessor_corruption_fails(model_project):
    config = load_config(model_project)
    pre = json.loads((config.paths.metadata / "preprocessing_manifest.json").read_text())
    (model_project / pre["serialization_artifact_path"]).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        contract.load_modeling_data(model_project)


def test_sealed_test_never_engineered_or_exposed(model_project, monkeypatch):
    real_split = contract.split_dataset
    class SealedTest:
        def __getattribute__(self, name):
            raise AssertionError("Phase 4 must not access TEST rows")
    def split(*args):
        result = real_split(*args)
        result["test"] = SealedTest()
        return result
    monkeypatch.setattr(contract, "split_dataset", split)
    transform = Mock(wraps=contract.transform_split)
    monkeypatch.setattr(contract, "transform_split", transform)
    data = contract.load_modeling_data(model_project)
    assert transform.call_count == 2
    assert data.X_train.shape[0] == 140 and data.X_validation.shape[0] == 30
    assert not hasattr(data, "X_test") and not hasattr(data, "y_test")


def test_orchestration_train_fit_only_and_aggregate_outputs(model_project, monkeypatch):
    data = contract.load_modeling_data(model_project)
    monkeypatch.setattr(baseline, "load_modeling_data", lambda root: data)
    fit = Mock(wraps=baseline.fit_baseline)
    probability = Mock(wraps=baseline.raw_probabilities)
    monkeypatch.setattr(baseline, "fit_baseline", fit)
    monkeypatch.setattr(baseline, "raw_probabilities", probability)
    result = baseline.run_baseline(model_project)
    fit.assert_called_once_with(data.X_train, data.y_train)
    assert [call.args[1] is data.X_validation for call in probability.call_args_list] == [False, True, False]
    assert all(call.args[1] is data.X_train or call.args[1] is data.X_validation for call in probability.call_args_list)
    metadata = load_config(model_project).paths.metadata
    manifest = json.loads((metadata / "baseline_model_manifest.json").read_text())
    measured = json.loads((metadata / "baseline_metrics.json").read_text())
    assert not manifest["test_set_evaluated"] and not measured["test_set_evaluated"]
    assert "test" not in measured and set(measured) == {
        "model_version", "reference_threshold", "probability_semantics", "test_set_evaluated",
        "train", "validation", "validation_uncertainty"}
    assert manifest["dataset_sha256"] == EXPECTED_SHA256
    assert manifest["model_version"] == baseline.MODEL_VERSION
    assert manifest["split_version"] == data.split_manifest["split_version"]
    assert manifest["preprocessing_version"] == data.preprocessing_manifest["preprocessing_version"]
    assert manifest["artifact_sha256"] == result["artifact_sha256"]
    assert manifest["effective_penalty"] == "l2" and manifest["convergence_status"] == "converged"
    saved = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in metadata.glob("baseline*.json")}
    baseline.run_baseline(model_project)
    assert all((p.read_bytes(), p.stat().st_mtime_ns) == state for p, state in saved.items())


def test_coefficients_alignment_exponential_and_exclusions(model_project):
    data = contract.load_modeling_data(model_project)
    model = baseline.fit_baseline(data.X_train, data.y_train)
    rows = baseline.coefficient_table(model, data.feature_names, data.trace)
    assert len(rows) == len(data.feature_names)
    assert [r["transformed_feature_name"] for r in rows] == list(data.feature_names)
    np.testing.assert_allclose([r["exp_coefficient"] for r in rows], np.exp(model.coef_[0]))
    np.testing.assert_array_equal([r["coefficient"] for r in rows], model.coef_[0])
    for bad_names in (data.feature_names[::-1], data.feature_names[:-1], (data.feature_names[0],) * len(data.feature_names)):
        with pytest.raises(ValueError, match="alignment"):
            baseline.coefficient_table(model, bad_names, data.trace)
    data.trace[0]["canonical_sources"] = ["sex"]
    with pytest.raises(ValueError, match="Forbidden"):
        baseline.coefficient_table(model, data.feature_names, data.trace)
