"""Phase-7 mathematical, frozen-contract, isolation and aggregate-publication checks."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from scipy import sparse
from scipy.special import expit
from xgboost import XGBClassifier

from credit_risk.config import load_config
from credit_risk.explainability import aggregation, contract, local, run
from credit_risk.explainability.reason_codes import reason_codes
from credit_risk.explainability.score import InternalScore, rank_validation, score_deciles, score_summary
from credit_risk.explainability.shap_explainer import MarginExplainer
from credit_risk.features.definitions import EXCLUDED_FIELDS, MODEL_INPUT_FEATURES
from credit_risk.features.preprocessing import load_preprocessor
from credit_risk.modeling import contract as data_contract
from credit_risk.modeling.calibration_metrics import probability_metrics
from test_modeling import model_project

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def small_model():
    rng = np.random.default_rng(42)
    X = rng.normal(size=(100, 4))
    X[::3, 1] = 0  # Dense-zero semantics matter for this model.
    y = (X[:, 0] + .4 * X[:, 1] > 0).astype(int)
    model = XGBClassifier(n_estimators=8, max_depth=2, random_state=42, n_jobs=1, tree_method="hist")
    model.fit(X, y)  # Synthetic fixture only; never the selected real-data model.
    return model, sparse.csr_matrix(X), y


def test_public_tree_shap_raw_margin_and_probability(small_model):
    model, X, _ = small_model
    explainer = MarginExplainer(model, [f"column_{i}" for i in range(4)])
    result = explainer.explain(X)
    assert explainer.explainer.model_output == "raw"
    assert explainer.explainer.feature_perturbation == "tree_path_dependent"
    assert result["values"].shape == (100, 4) and result["base"].shape == (100,)
    np.testing.assert_allclose(result["base"] + result["values"].sum(axis=1),
                               model.predict(X.toarray(), output_margin=True), rtol=0, atol=1e-5)
    np.testing.assert_allclose(expit(result["base"] + result["values"].sum(axis=1)),
                               model.predict_proba(X.toarray())[:, 1], rtol=0, atol=1e-6)


@pytest.mark.parametrize("fault", ["probability", "additivity", "base_shape", "feature_width", "nonfinite"])
def test_bad_explanation_fails(small_model, monkeypatch, fault):
    model, X, _ = small_model
    explainer = MarginExplainer(model, [f"c{i}" for i in range(4)])
    result = explainer.explain(X)
    if fault == "probability":
        monkeypatch.setattr(model, "predict_proba", lambda X: np.tile([.5, .5], (len(X), 1)))
    elif fault == "additivity":
        monkeypatch.setattr(explainer.explainer, "shap_values", lambda *a, **k: result["values"] + 1)
    elif fault == "base_shape":
        monkeypatch.setattr(explainer.explainer, "shap_values", lambda *a, **k: result["values"])
        explainer.explainer.expected_value = [0, 1]
    elif fault == "feature_width":
        X = X[:, :3]
    else:
        X.data[0] = np.nan
    with pytest.raises(ValueError):
        explainer.explain(X)


def test_all_103_committed_lineage_and_exclusions():
    manifest = json.loads((ROOT / "data/metadata/feature_manifest.json").read_text())
    rows = aggregation.lineage(manifest["transformed_feature_names"], manifest["transformed_feature_trace"])
    assert len(rows) == len({row["name"] for row in rows}) == 103
    assert {row["source_feature"] for row in rows} == set(MODEL_INPUT_FEATURES)
    assert len({row["feature_family"] for row in rows}) == 7
    assert all(not set(EXCLUDED_FIELDS) & set(row["canonical_sources"]) for row in manifest["transformed_feature_trace"])
    for field in EXCLUDED_FIELDS:
        bad = copy.deepcopy(manifest["transformed_feature_trace"])
        bad[0]["canonical_sources"] = [field]
        with pytest.raises(ValueError, match="forbidden"):
            aggregation.lineage(manifest["transformed_feature_names"], bad)
    bad = copy.deepcopy(manifest["transformed_feature_trace"])
    bad[0]["input_feature"] = "unknown"
    with pytest.raises(ValueError):
        aggregation.lineage(manifest["transformed_feature_names"], bad)
    with pytest.raises(ValueError):
        aggregation.lineage(manifest["transformed_feature_names"][::-1], manifest["transformed_feature_trace"])


def test_local_first_aggregation_cancellation_and_normalization():
    rows = [{"name": name, "source_feature": source, "feature_family": aggregation.family(source)} for name, source in
            [("a", "repayment_status_2005_09"), ("b", "repayment_status_2005_09"), ("c", "credit_limit")]]
    values = np.array([[2., -2., 1.], [-3., 3., -1.]])
    result, sources, sv, families, fv = aggregation.global_importance(values, rows)
    assert np.all(sv[:, sources.index("repayment_status_2005_09")] == 0)
    assert result["source_feature"][1]["mean_abs_shap_margin"] == 0
    for grouped in (sv, fv):
        np.testing.assert_array_equal(grouped.sum(axis=1), values.sum(axis=1))
    for ranked in result.values():
        assert sum(row["normalized_mean_abs_shap"] for row in ranked) == pytest.approx(1)
    assert sources == sorted(sources) and families == sorted(families)
    zero = aggregation.importance(np.zeros((2, 2)), [{"name": "b"}, {"name": "a"}])
    assert [row["name"] for row in zero] == ["a", "b"]
    assert all(row["normalized_mean_abs_shap"] == 0 for row in zero)


def test_reason_direction_topk_ties_and_guard():
    names = ["bill_amount_mean", "credit_limit", "payment_amount_sum", "payment_amount_max"]
    result = reason_codes(names, [2, 2, -3, -3], top_k=1, score_factor=InternalScore().factor)
    assert result["risk_increasing"][0]["source_feature"] == "bill_amount_mean"
    assert result["risk_decreasing"][0]["source_feature"] == "payment_amount_max"
    assert result["risk_increasing"][0]["score_point_contribution"] < 0
    assert result["risk_decreasing"][0]["score_point_contribution"] > 0
    assert result["interpretation"] == "model diagnostic drivers"
    for names, values in [(["age"], [1]), (["credit_limit"] * 2, [1, 1]), (["credit_limit"], [np.nan])]:
        with pytest.raises(ValueError):
            reason_codes(names, values)
    with pytest.raises(ValueError):
        reason_codes(["credit_limit"], [1], top_k=True)


def test_score_identities_monotonicity_inverse_and_boundaries():
    mapping = InternalScore()
    points, clipped = mapping.transform([1 / 51, 1 / 101])
    np.testing.assert_allclose(points, [600, 620], rtol=0, atol=1e-10)
    p = np.linspace(1e-10, 1 - 1e-10, 1000)
    scores, _ = mapping.transform(p)
    assert np.all(np.diff(scores) < 0)
    np.testing.assert_allclose(mapping.inverse(scores), p, rtol=0, atol=1e-15)
    original = np.array([0., .5, 1.])
    scores, clipped = mapping.transform(original)
    assert clipped.tolist() == [True, False, True] and np.isfinite(scores).all()
    np.testing.assert_array_equal(original, [0, .5, 1])
    assert scores.min() < 0 and scores.max() > 1000  # No cosmetic clamp.
    assert score_summary(mapping, original)["probability_clipping_count"] == 2
    with pytest.raises(ValueError):
        InternalScore(pdo=30)


@pytest.mark.parametrize("bad", [[], [np.nan], [np.inf], [-.1], [1.1], [[.2]]])
def test_invalid_score_probability(bad):
    with pytest.raises(ValueError):
        InternalScore().transform(bad)


def test_score_ranking_ties_and_decile_coverage():
    p = np.repeat(np.linspace(.05, .95, 10), 3)
    y = np.arange(30) % 2
    mapping = InternalScore()
    assert rank_validation(mapping, y, p)["auc_absolute_difference"] == 0
    result = score_deciles(mapping, y, p)
    assert sum(row["count"] for row in result) == 30 and len(result) == 10
    scores = mapping.transform(p)[0]
    for i, row in enumerate(result):
        indices = slice(3 * i, 3 * i + 3)
        assert row["count"] == 3
        assert row["mean_score"] == pytest.approx(scores[indices].mean())
        assert row["mean_reported_probability"] == pytest.approx(p[indices].mean())
        assert row["observed_default_rate"] == pytest.approx(y[indices].mean())
        assert row["test_set_evaluated"] is False
    tied = score_deciles(mapping, y, [.5] * 30)
    assert tied == score_deciles(mapping, y, [.5] * 30)
    assert all(row["count"] == 3 for row in tied)


def test_score_points_all_levels_and_nonidentity_raw_shap_available(small_model):
    model, X, _ = small_model
    explanation = MarginExplainer(model, [f"c{i}" for i in range(4)]).explain(X)
    mapping = InternalScore()
    source_names, sv = aggregation.aggregate(explanation["values"], ["a", "a", "b", "c"])
    _, fv = aggregation.aggregate(sv, ["one", "one", "two"])
    for values in (explanation["values"], sv, fv):
        result = mapping.decompose(explanation["base"], values, explanation["raw_probability"], calibration_method="identity")
        np.testing.assert_allclose(result["score_base_value"] + result["score_point_contributions"].sum(axis=1),
                                   mapping.transform(explanation["raw_probability"])[0], rtol=0, atol=1e-3)
        assert np.all(result["score_point_contributions"][values > 0] < 0)
    # A hypothetical non-identity reported probability leaves margin explanations
    # and score conversion usable, but cannot reuse the affine score attribution.
    reported = .1 + .8 * explanation["raw_probability"]
    assert np.isfinite(mapping.transform(reported)[0]).all()
    guarded = mapping.decompose(explanation["base"], explanation["values"], reported, calibration_method="sigmoid")
    assert guarded["score_point_decomposition_supported"] is False
    assert "score_point_contributions" not in guarded
    for kwargs in ({"model_output": "probability"}, {"objective": "reg:squarederror"}):
        assert not mapping.decompose(explanation["base"], explanation["values"], reported,
                                     calibration_method="identity", **kwargs)["score_point_decomposition_supported"]
    assert not mapping.decompose([0], [[1]], [0], calibration_method="identity")["score_point_decomposition_supported"]
    with pytest.raises(ValueError, match="tolerance"):
        mapping.decompose(explanation["base"], explanation["values"] + 1, explanation["raw_probability"], calibration_method="identity")


def test_validation_only_consumer_drops_train_and_test(model_project, monkeypatch):
    original_split = data_contract.split_dataset
    class Sealed:
        def __getattribute__(self, name):
            raise AssertionError("TRAIN/TEST must not be consumed by explainability")
    def split(*args):
        partitions = original_split(*args)
        partitions["train"] = Sealed()
        partitions["test"] = Sealed()
        return partitions
    monkeypatch.setattr(data_contract, "split_dataset", split)
    transform = Mock(wraps=data_contract.transform_split)
    monkeypatch.setattr(data_contract, "transform_split", transform)
    data = data_contract.load_modeling_data(model_project, validation_only=True)
    assert data.X_train is data.y_train is None
    assert not hasattr(data, "X_test") and not hasattr(data, "y_test")
    assert transform.call_count == 1 and data.X_validation.shape[0] == 30


@pytest.fixture
def synthetic_context(model_project):
    data = data_contract.load_modeling_data(model_project)
    model = XGBClassifier(n_estimators=8, max_depth=2, n_jobs=1, random_state=42)
    model.fit(data.X_train.toarray(), data.y_train)
    p = model.predict_proba(data.X_validation.toarray())[:, 1].astype(float)
    pre = data.preprocessing_manifest
    preprocessor = load_preprocessor(model_project / pre["serialization_artifact_path"], pre["serialization_sha256"])
    data.X_train = data.y_train = None
    read = lambda name: json.loads((ROOT / "data/metadata" / name).read_text())
    selection = read("phase6_model_selection.json")
    selection["models"]["xgboost"]["validation_reported"] = probability_metrics(data.y_validation, p)
    context = contract.FrozenContext(data, model, preprocessor, read("xgboost_model_manifest.json"),
        read("calibration_manifest.json")["models"]["xgboost"], selection,
        {"features": [{"transformed_feature_name": name, "gain": float(i)} for i, name in enumerate(data.feature_names)]})
    (model_project / "configs/explainability.yaml").write_bytes((ROOT / "configs/explainability.yaml").read_bytes())
    return model_project, context


def test_orchestration_no_fit_no_train_test_and_only_aggregate_outputs(synthetic_context, monkeypatch):
    project, context = synthetic_context
    monkeypatch.setattr(run, "load_frozen", lambda root: context)
    monkeypatch.setattr(XGBClassifier, "fit", Mock(side_effect=AssertionError("Phase 7 must not fit")))
    predict = Mock(wraps=context.model.predict)
    monkeypatch.setattr(context.model, "predict", predict)
    metadata = load_config(project).paths.metadata
    historical = {path.name: path.read_bytes() for path in metadata.iterdir() if path.is_file()}
    result = run.run_explainability(project)
    assert result["test_set_evaluated"] is False and result["score_summary"]["train_oof"]["available"] is False
    assert [call.args[0].shape[0] for call in predict.call_args_list] == [30, 1, 1, 1]
    expected = {"explainability_manifest.json", "shap_global_importance.json", "internal_score_manifest.json",
                "internal_score_summary.json", "score_decile_analysis.csv"}
    new = {path.name: path.read_bytes() for path in metadata.iterdir() if path.name not in historical}
    assert set(new) == expected
    for name, value in historical.items():
        assert (metadata / name).read_bytes() == value
    for name in expected - {"score_decile_analysis.csv"}:
        content = json.loads(new[name])
        assert content["test_set_evaluated"] is False
        assert not {"customer_id", "shap_values", "source_contributions", "reason_codes"} & set(content)
    assert len(pd.read_csv(metadata / "score_decile_analysis.csv")) == 10
    run.run_explainability(project)
    assert new == {name: (metadata / name).read_bytes() for name in expected}
    rows = aggregation.lineage(context.data.feature_names, context.data.trace)
    explainer = MarginExplainer(context.model, context.data.feature_names)
    record = next(iter(local.synthetic_records().values()))
    explanation = local.explain_record(record, context, explainer, InternalScore(), rows)
    assert len(explanation["source_contributions"]) == 45
    assert explanation == local.explain_record(record, context, explainer, InternalScore(), rows)
    with pytest.raises(ValueError, match="19 financial"):
        local.explain_record({**record, "age": 30}, context, explainer, InternalScore(), rows)


@pytest.fixture
def frozen_contract_project(data_project, monkeypatch):
    config = load_config(data_project)
    config.paths.metadata.mkdir(parents=True)
    for name in ("xgboost_model_manifest.json", "calibration_manifest.json", "phase6_model_selection.json", "xgboost_feature_importance.json"):
        (config.paths.metadata / name).write_bytes((ROOT / "data/metadata" / name).read_bytes())
    read = lambda name: json.loads((ROOT / "data/metadata" / name).read_text())
    pre, split, features = [read(name + ".json") for name in ("preprocessing_manifest", "split_manifest", "feature_manifest")]
    data = SimpleNamespace(preprocessing_manifest=pre, split_manifest=split, dataset_sha256=split["dataset_sha256"],
                           feature_names=features["transformed_feature_names"])
    monkeypatch.setattr(contract, "load_modeling_data", lambda root, validation_only: data)
    native = SimpleNamespace(n_features_in_=103,
        get_booster=lambda: SimpleNamespace(save_config=lambda: '{"learner":{"objective":{"name":"binary:logistic"}}}'))
    model_loader, pre_loader = Mock(return_value=native), Mock(return_value=object())
    monkeypatch.setattr(contract, "load_native", model_loader)
    monkeypatch.setattr(contract, "load_preprocessor", pre_loader)
    return data_project, model_loader, pre_loader


def test_frozen_contract_passes_exact_hashes_to_trusted_loaders(frozen_contract_project):
    project, model_loader, pre_loader = frozen_contract_project
    context = contract.load_frozen(project)
    assert model_loader.call_args.args[1] == context.model_manifest["artifact_sha256"]
    assert pre_loader.call_args.args[1] == context.data.preprocessing_manifest["serialization_sha256"]
    assert model_loader.call_args.args[0].is_relative_to(project / "artifacts")
    assert context.calibration["method"] == "identity"


@pytest.mark.parametrize("file,keys,value", [
    ("phase6_model_selection.json", ["selected_downstream_model"], "logistic"),
    ("phase6_model_selection.json", ["models", "xgboost", "model_version"], "changed"),
    ("phase6_model_selection.json", ["models", "xgboost", "calibration_version"], "changed"),
    ("xgboost_model_manifest.json", ["artifact_sha256"], "changed"),
    ("xgboost_model_manifest.json", ["preprocessing_artifact_sha256"], "changed"),
    ("xgboost_model_manifest.json", ["transformed_feature_count"], 102),
    ("xgboost_model_manifest.json", ["artifact_relative_path"], "../untrusted.json"),
    ("calibration_manifest.json", ["models", "xgboost", "method"], "sigmoid"),
    ("calibration_manifest.json", ["test_set_evaluated"], True),
    ("phase6_model_selection.json", ["technical_threshold", "technical_threshold_source"], "validation"),
])
def test_frozen_contract_rejects_semantic_drift(frozen_contract_project, file, keys, value):
    project, model_loader, _ = frozen_contract_project
    path = load_config(project).paths.metadata / file
    content = json.loads(path.read_text())
    target = content
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    path.write_text(json.dumps(content))
    with pytest.raises(ValueError):
        contract.load_frozen(project)
    model_loader.assert_not_called()


def test_real_frozen_validation_additivity_without_retraining(monkeypatch):
    model_manifest = json.loads((ROOT / "data/metadata/xgboost_model_manifest.json").read_text())
    pre_manifest = json.loads((ROOT / "data/metadata/preprocessing_manifest.json").read_text())
    required = [ROOT / model_manifest["artifact_relative_path"], ROOT / pre_manifest["serialization_artifact_path"]]
    if not all(path.is_file() for path in required) or not list((ROOT / "data/raw").glob("*.xls")):
        pytest.skip("Real-data integration requires trusted ignored dataset/model/preprocessor artifacts")
    monkeypatch.setattr(XGBClassifier, "fit", Mock(side_effect=AssertionError("Cannot retrain frozen model")))
    context = contract.load_frozen(ROOT)
    assert context.data.X_train is context.data.y_train is None
    assert context.data.X_validation.shape == (4500, 103)
    rows = aggregation.lineage(context.data.feature_names, context.data.trace)
    assert len(rows) == 103
    result = MarginExplainer(context.model, context.data.feature_names).explain(context.data.X_validation)
    assert result["additivity"]["max_absolute_error"] < 1e-5
    assert result["probability_reconstruction"]["max_absolute_error"] < 1e-7
    assert probability_metrics(context.data.y_validation, result["raw_probability"]) == context.selection["models"]["xgboost"]["validation_reported"]


@pytest.mark.parametrize("key,value", [("model_output", "probability"), ("pdo", 30),
    ("local_reason_top_k", True), ("margin_tolerance", .1), ("score_version", "unreviewed")])
def test_configuration_rejects_contract_changes(data_project, key, value):
    import yaml
    options = yaml.safe_load((ROOT / "configs/explainability.yaml").read_text())
    options[key] = value
    (data_project / "configs/explainability.yaml").write_text(yaml.safe_dump(options))
    with pytest.raises(ValueError):
        contract.settings(data_project)
