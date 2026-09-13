"""Synthetic fold-leakage, comparison, native artifact and sealed-test checks."""

import copy
import json
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
from scipy import sparse
from sklearn.model_selection import StratifiedKFold
from sklearn.utils.validation import check_is_fitted
from sklearn.exceptions import NotFittedError
import yaml
from xgboost import XGBClassifier

from credit_risk.config import load_config
from credit_risk.features import prepare
from credit_risk.features.definitions import NUMERIC_FEATURES, CATEGORICAL_FEATURES
from credit_risk.modeling import baseline, comparison, contract, search
from credit_risk.modeling import xgboost_challenger as challenger
from test_modeling import model_project, training  # Reuse synthetic-only Phase-4 fixtures.


@pytest.fixture
def settings():
    config = search.load_settings(Path(__file__).resolve().parents[1])
    config["search"] = {"n_iter": 2, "cv_folds": 2}
    config["space"] = {k: [v[0]] for k, v in config["space"].items()}
    config["space"]["n_estimators"] = [5, 10]
    return config


@pytest.fixture
def xgb_project(model_project, settings, monkeypatch):
    (model_project / "configs/xgboost.yaml").write_text(yaml.safe_dump(settings))
    baseline.run_baseline(model_project)
    monkeypatch.setattr(challenger, "verify_dataset_manifest", prepare.verify_dataset_manifest)
    return model_project


def parameters(settings):
    return {k: v[0] for k, v in settings["space"].items()}


def test_real_search_configuration_and_unfitted_pipeline():
    settings = search.load_settings(Path(__file__).resolve().parents[1])
    experiment = search.build_search(settings, 42)
    assert experiment.n_iter == 24 and experiment.n_jobs == 1
    assert isinstance(experiment.cv, StratifiedKFold)
    assert experiment.cv.n_splits == 4 and experiment.cv.shuffle
    assert experiment.cv.random_state == experiment.random_state == 42
    assert experiment.scoring == {"roc_auc": "roc_auc", "average_precision": "average_precision"}
    assert experiment.refit is search.select_candidate
    assert experiment.error_score == "raise" and not experiment.return_train_score
    model = experiment.estimator.named_steps["model"]
    assert isinstance(model, XGBClassifier)
    for name, value in settings["fixed"].items():
        assert model.get_params()[name] == value
    assert model.random_state == 42 and model.early_stopping_rounds is None
    with pytest.raises(NotFittedError):
        check_is_fitted(experiment.estimator.named_steps["preprocessing"])


def test_config_cost_and_invariant_guards(tmp_path, settings):
    (tmp_path / "configs").mkdir()
    for section, key, value in [("search", "n_iter", 25), ("search", "cv_folds", 5),
                                 ("fixed", "scale_pos_weight", 2), ("fixed", "device", "cuda"),
                                 ("space", "max_depth", [20]), ("space", "learning_rate", [0])]:
        bad = copy.deepcopy(settings)
        bad[section][key] = value
        (tmp_path / "configs/xgboost.yaml").write_text(yaml.safe_dump(bad))
        with pytest.raises(ValueError):
            search.load_settings(tmp_path)


def test_candidate_selection_ties_are_deterministic(settings):
    p = {f"model__{k}": v for k, v in parameters(settings).items()}
    first, second = dict(p), dict(p)
    first["model__max_depth"] = 3
    results = {"params": [first, second], "mean_test_roc_auc": [.7, .8], "mean_test_average_precision": [.8, .7]}
    assert search.select_candidate(results) == 1  # AUC first, regardless of AP.
    results["mean_test_roc_auc"] = [.8, .8]
    assert search.select_candidate(results) == 0  # AP tie breaker.
    results["mean_test_average_precision"] = [.7, .7]
    assert search.select_candidate(results) == 1  # Smaller depth.
    first["model__max_depth"] = second["model__max_depth"]
    first["model__n_estimators"] = second["model__n_estimators"] - 1
    assert search.select_candidate(results) == 0
    first["model__n_estimators"] = second["model__n_estimators"]
    second["model__reg_lambda"] = first["model__reg_lambda"] + 1
    assert search.select_candidate(results) == 1
    results["mean_test_roc_auc"][0] = np.nan
    with pytest.raises(ValueError):
        search.select_candidate(results)


def test_cv_preprocessing_fits_inside_each_fold(xgb_project, settings, monkeypatch):
    data = contract.load_modeling_data(xgb_project)
    X = challenger.load_training_features(xgb_project, data)
    special = X.index[0]
    X.loc[special, CATEGORICAL_FEATURES[0]] = "status_9"
    X.loc[special, NUMERIC_FEATURES[0]] = 1e9
    snapshots = []
    original = search.FoldPreprocessor.fit
    def fit(self, frame, y=None):
        result = original(self, frame, y)
        columns = self.preprocessor_.named_steps["columns"]
        medians = columns.named_transformers_["numeric"].named_steps["imputer"].statistics_
        np.testing.assert_allclose(medians, frame.loc[:, list(NUMERIC_FEATURES)].median().to_numpy())
        vocab = columns.named_transformers_["repayment"].named_steps["encoder"].categories_[0]
        assert ("status_9" in vocab) == (special in frame.index)
        snapshots.append(set(frame.index))
        return result
    monkeypatch.setattr(search.FoldPreprocessor, "fit", fit)
    result = search.run_search(X, data.y_train, settings, 42)
    folds = list(StratifiedKFold(2, shuffle=True, random_state=42).split(X, data.y_train))
    expected = [set(X.iloc[train].index) for train, _ in folds]
    assert snapshots[:-1] == expected * 2 and snapshots[-1] == set(X.index)
    assert len(result.cv_results_["params"]) == 2
    assert all(len(indices) == 70 for indices in snapshots[:-1])


def test_training_probabilities_and_zero_semantics(training, settings):
    X, y = training
    X.data[::3] = 0
    X.eliminate_zeros()
    model = challenger.fit_model(challenger.build_model(settings, parameters(settings), 42), X, y)
    result = challenger.raw_probabilities(model, X)
    np.testing.assert_array_equal(result, model.predict_proba(X.toarray())[:, 1])
    assert result.shape == (100,) and np.isfinite(result).all()
    assert ((result >= 0) & (result <= 1)).all()


@pytest.mark.parametrize("y", [np.zeros(100), np.full(100, 2), np.zeros(99), np.full(100, np.nan)])
def test_bad_target_fails(training, settings, y):
    with pytest.raises(ValueError):
        challenger.fit_model(challenger.build_model(settings, parameters(settings), 42), training[0], y)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_predictors_fail(training, settings, value):
    X, y = training
    X.data[0] = value
    with pytest.raises(ValueError):
        challenger.fit_model(challenger.build_model(settings, parameters(settings), 42), X, y)


def test_baseline_loaded_and_conflicting_metadata_rejected(xgb_project):
    data = contract.load_modeling_data(xgb_project)
    metadata = load_config(xgb_project).paths.metadata
    manifest, metrics, probability = comparison.load_baseline(xgb_project, data)
    assert metrics == json.loads((metadata / "baseline_metrics.json").read_text())
    assert len(probability) == 30
    path = metadata / "baseline_model_manifest.json"
    for field, bad in [("dataset_sha256", "wrong"), ("split_version", "wrong"), ("preprocessing_version", "wrong"),
                       ("transformed_feature_count", 999), ("model_version", "wrong"), ("test_set_evaluated", True)]:
        changed = {**manifest, field: bad}
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError):
            comparison.load_baseline(xgb_project, data)
    path.write_text(json.dumps(manifest))
    metrics["validation"]["roc_auc"] += .01
    (metadata / "baseline_metrics.json").write_text(json.dumps(metrics))
    with pytest.raises(ValueError, match="metric disagrees"):
        comparison.load_baseline(xgb_project, data)


@pytest.mark.parametrize("auc,ap,status", [(.8,.8,"XGBOOST_LEADS_ON_VALIDATION_DISCRIMINATION"),
    (.6,.6,"LOGISTIC_BASELINE_LEADS_ON_VALIDATION_DISCRIMINATION"),
    (.8,.6,"MIXED_VALIDATION_RESULT"), (.7,.8,"MIXED_VALIDATION_RESULT")])
def test_comparison_status_and_deltas(auc, ap, status):
    base = {"roc_auc": .7, "average_precision": .7, "threshold_0_5": {"recall": .2}}
    xgb = {"roc_auc": auc, "average_precision": ap, "threshold_0_5": {"recall": .4}}
    assert comparison.provisional_status(base, xgb) == status
    delta = comparison.metric_deltas(base, xgb)
    assert delta["roc_auc"] == pytest.approx(auc - .7)
    assert delta["threshold_0_5"]["recall"] == pytest.approx(.2)


def test_paired_bootstrap_indices_determinism_sign_and_single_class(monkeypatch):
    original = comparison.roc_auc_score
    targets = []
    def score(y, p):
        targets.append(y.copy())
        return original(y, p)
    monkeypatch.setattr(comparison, "roc_auc_score", score)
    result = comparison.paired_bootstrap([0, 1], [.9, .1], [.1, .9], 42, 100)
    for i in range(0, len(targets), 2):
        np.testing.assert_array_equal(targets[i], targets[i + 1])
    assert result == comparison.paired_bootstrap([0, 1], [.9, .1], [.1, .9], 42, 100)
    assert result["delta_roc_auc_95_ci"] == [1, 1]
    assert result["delta_average_precision_95_ci"] == [.5, .5]
    assert 0 < result["successful_replicates"] < 100 and result["skipped_single_class"] > 0
    assert comparison.paired_bootstrap([0, 1], [.1, .9], [.1, .9], 42, 100)["delta_roc_auc_95_ci"] == [0, 0]


def test_native_roundtrip_and_determinism(training, settings, tmp_path):
    X, y = training
    model = challenger.fit_model(challenger.build_model(settings, parameters(settings), 42), X, y)
    other = challenger.fit_model(challenger.build_model(settings, parameters(settings), 42), X, y)
    expected = challenger.raw_probabilities(model, X)
    np.testing.assert_array_equal(expected, challenger.raw_probabilities(other, X))
    path, digest = challenger.save_native(model, tmp_path)
    loaded = challenger.load_native(path, digest)
    np.testing.assert_allclose(expected, challenger.raw_probabilities(loaded, X), rtol=0, atol=1e-12)
    assert challenger.save_native(model, tmp_path) == (path, digest)
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        challenger.load_native(path, digest)


def test_importance_mapping_and_invalid_indices(training, settings):
    X, y = training
    model = challenger.fit_model(challenger.build_model(settings, parameters(settings), 42), X, y)
    names = [f"numeric__feature{i}" for i in range(4)]
    trace = [{"name": name, "input_feature": name, "canonical_sources": ["credit_limit"], "category": None} for name in names]
    result = challenger.feature_importance(model, names, trace)
    assert sum(row["normalized_gain"] for row in result["features"]) == pytest.approx(1)
    assert {r["transformed_feature_name"] for r in result["features"]} == set(names)
    assert all(np.isfinite(r["gain"]) and r["gain"] >= 0 for r in result["features"])
    bad = Mock()
    bad.get_booster.return_value.num_features.return_value = 4
    bad.get_booster.return_value.get_score.return_value = {"f4": 1.0}
    with pytest.raises(ValueError, match="Unknown"):
        challenger.feature_importance(bad, names, trace)
    bad.get_booster.return_value.get_score.return_value = {"f0": float("nan")}
    with pytest.raises(ValueError, match="finite"):
        challenger.feature_importance(bad, names, trace)
    with pytest.raises(ValueError, match="names/lineage"):
        challenger.feature_importance(model, [names[0]] * 4, trace)


def test_orchestration_sealing_train_cv_and_weighted_separation(xgb_project, monkeypatch):
    data = contract.load_modeling_data(xgb_project)
    X = challenger.load_training_features(xgb_project, data)
    monkeypatch.setattr(challenger, "load_modeling_data", lambda root: data)
    monkeypatch.setattr(challenger, "load_training_features", lambda root, value: X)
    fitting = Mock(wraps=challenger.fit_model)
    predicting = Mock(wraps=challenger.raw_probabilities)
    saving = Mock(wraps=challenger.save_native)
    searching = Mock(wraps=challenger.run_search)
    monkeypatch.setattr(challenger, "fit_model", fitting)
    monkeypatch.setattr(challenger, "raw_probabilities", predicting)
    monkeypatch.setattr(challenger, "save_native", saving)
    monkeypatch.setattr(challenger, "run_search", searching)
    result = challenger.run_challenger(xgb_project)
    assert searching.call_count == 1 and searching.call_args.args[0] is X
    assert searching.call_args.args[1] is data.y_train
    assert fitting.call_count == 2
    for call in fitting.call_args_list:
        assert call.args[1] is data.X_train and call.args[2] is data.y_train
    canonical, sensitivity = [call.args[0] for call in fitting.call_args_list]
    assert canonical.scale_pos_weight == 1 and sensitivity.scale_pos_weight == 4
    saving.assert_called_once()
    assert saving.call_args.args[0] is canonical
    assert [call.args[1] is data.X_validation for call in predicting.call_args_list] == [False, True, True, False, True]
    assert all(call.args[1] is data.X_train or call.args[1] is data.X_validation for call in predicting.call_args_list)
    metadata = load_config(xgb_project).paths.metadata
    for name in ("xgboost_model_manifest", "xgboost_metrics", "model_comparison", "xgboost_feature_importance"):
        record = json.loads((metadata / f"{name}.json").read_text())
        assert record["test_set_evaluated"] is False and "test" not in record
    assert result["metrics"]["reference_threshold"] == .5
    assert result["metrics"]["imbalance_sensitivity"]["canonical"] is False
    assert set(result["metrics"]["imbalance_sensitivity"]) == {
        "canonical", "scale_pos_weight", "train_negative_count", "train_positive_count", "validation", "test_set_evaluated"}
    assert result["comparison"]["final_model_selected"] is False


def test_cv_input_loader_does_not_access_holdouts(xgb_project, monkeypatch):
    data = contract.load_modeling_data(xgb_project)
    original = challenger.split_dataset
    class Sealed:
        def __getattribute__(self, name):
            raise AssertionError("CV must not access project holdout rows")
    def split(*args):
        partitions = original(*args)
        partitions["test"] = partitions["validation"] = Sealed()
        return partitions
    monkeypatch.setattr(challenger, "split_dataset", split)
    assert len(challenger.load_training_features(xgb_project, data)) == len(data.y_train)
