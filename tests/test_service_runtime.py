"""Frozen real-artifact integration on fabricated records; never dataset examples."""

from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
from unittest.mock import Mock

from fastapi.testclient import TestClient
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from credit_risk.api import main, manifest
from credit_risk.explainability import contract as explanation_contract
from credit_risk.explainability.local import explain_record, synthetic_records
from credit_risk.features import prepare
from credit_risk.features.definitions import PRIMARY_MODEL_FEATURES
from credit_risk.features.engineering import engineer_features
from credit_risk.features.preprocessing import transform_split
from credit_risk.modeling import contract as data_contract
from credit_risk.modeling.calibrators import ProbabilityCalibrator
from credit_risk.service import runtime
from credit_risk.service.inference import InferenceService
from test_api import configured, database, ROOT, record


def require_artifacts():
    for name, field in (("xgboost_model_manifest", "artifact_relative_path"),
                         ("preprocessing_manifest", "serialization_artifact_path")):
        metadata = json.loads((ROOT / "data/metadata" / (name + ".json")).read_text())
        if not (ROOT / metadata[field]).is_file():
            pytest.skip("Requires trusted ignored frozen artifacts for real integration; never trains replacements")


@pytest.fixture
def artifact_project(tmp_path):
    require_artifacts()
    for folder in ("configs", "data/metadata"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
        for path in (ROOT / folder).iterdir():
            if path.is_file():
                shutil.copyfile(path, tmp_path / folder / path.name)
    for name, field in (("xgboost_model_manifest", "artifact_relative_path"),
                         ("preprocessing_manifest", "serialization_artifact_path")):
        metadata = json.loads((ROOT / "data/metadata" / (name + ".json")).read_text())
        dest = tmp_path / metadata[field]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / metadata[field], dest)
    # There is deliberately no raw data directory or TEST split in this project.
    return tmp_path


def test_startup_once_no_fit_no_dataset_and_exact_synthetic_api_consistency(artifact_project, configured, database, monkeypatch):
    failure = Mock(side_effect=AssertionError("No fitting or dataset loading in Phase 8"))
    for cls, method in ((Pipeline, "fit"), (Pipeline, "fit_transform"), (XGBClassifier, "fit"), (ProbabilityCalibrator, "fit")):
        monkeypatch.setattr(cls, method, failure)
    monkeypatch.setattr(prepare, "verify_dataset_manifest", failure)
    monkeypatch.setattr(data_contract, "load_modeling_data", failure)
    monkeypatch.setattr(explanation_contract, "load_frozen", failure)
    pre_load = Mock(wraps=runtime.load_preprocessor)
    model_load = Mock(wraps=runtime.load_native)
    shap_load = Mock(wraps=runtime.MarginExplainer)
    score_load = Mock(wraps=runtime.InternalScore)
    monkeypatch.setattr(runtime, "load_preprocessor", pre_load)
    monkeypatch.setattr(runtime, "load_native", model_load)
    monkeypatch.setattr(runtime, "MarginExplainer", shap_load)
    monkeypatch.setattr(runtime, "InternalScore", score_load)
    app = main.create_app(settings=replace(configured, project_root=artifact_project), database_factory=lambda url: database)
    assert pre_load.call_count == model_load.call_count == shap_load.call_count == 0
    with TestClient(app) as client:
        client.headers["X-API-Key"] = configured.api_key
        assert pre_load.call_count == model_load.call_count == shap_load.call_count == score_load.call_count == 1
        r = app.state.runtime
        original_read = Path.read_text
        read_spy = Mock(wraps=original_read)
        # Explicit wrapper preserves Path binding while counting manifest reads.
        monkeypatch.setattr(Path, "read_text", lambda path, *a, **k: read_spy(path, *a, **k))
        measurements = []
        for name, financial in synthetic_records().items():
            X = transform_split(r.preprocessor, engineer_features(pd.DataFrame([financial], columns=PRIMARY_MODEL_FEATURES)))
            direct_margin = float(r.model.predict(X.toarray(), output_margin=True)[0])
            direct_probability = float(r.model.predict_proba(X.toarray())[0, 1])
            direct_score = float(r.mapping.transform([direct_probability])[0][0])
            response = client.post("/v1/predict", json=financial)
            assert response.status_code == 200
            result = response.json()
            differences = {"raw_margin": abs(result["raw_margin"] - direct_margin),
                "raw_probability": abs(result["raw_probability"] - direct_probability),
                "reported_probability": abs(result["reported_probability"] - direct_probability),
                "internal_risk_score": abs(result["internal_risk_score"] - direct_score)}
            assert all(value == 0 for value in differences.values())
            direct = explain_record(financial, r, r.explainer, r.mapping, r.rows)
            explained = client.post("/v1/explain", json=financial)
            assert explained.status_code == 200
            value = explained.json()
            assert value["raw_probability"] == direct["raw_probability"]
            assert value["internal_risk_score"] == direct["internal_risk_score"]
            exp = value["explanation"]
            assert exp["base_margin"] == direct["shap_base_margin"]
            assert exp["raw_margin"] == direct["raw_margin"]
            for direction in ("risk_increasing", "risk_decreasing"):
                expected = [{"source_feature": row["source_feature"], "direction": direction,
                             "shap_margin_contribution": row["contribution_to_raw_margin"],
                             "score_point_contribution": row["score_point_contribution"]} for row in direct["drivers"][direction]]
                assert exp[direction + "_drivers"] == expected
                assert len(expected) <= r.options["local_reason_top_k"]
            again = client.post("/v1/explain", json=financial).json()
            assert {k: v for k, v in again.items() if k not in {"request_id", "timestamp"}} == {
                   k: v for k, v in value.items() if k not in {"request_id", "timestamp"}}
            measurements.append((name, result["raw_probability"], result["internal_risk_score"], differences))
        assert measurements[1][1] > measurements[0][1] and measurements[1][2] < measurements[0][2]
        assert read_spy.call_count == 0
        assert pre_load.call_count == model_load.call_count == shap_load.call_count == score_load.call_count == 1
        failure.assert_not_called()
        print("SYNTHETIC real-artifact comparisons:", measurements)


@pytest.mark.parametrize("artifact,fault", [("model", "missing"), ("model", "checksum"),
                                          ("preprocessor", "missing"), ("preprocessor", "checksum")])
def test_artifact_startup_failure(artifact_project, configured, database, artifact, fault):
    filename, field = ("xgboost_model_manifest", "artifact_relative_path") if artifact == "model" else ("preprocessing_manifest", "serialization_artifact_path")
    value = json.loads((artifact_project / "data/metadata" / (filename + ".json")).read_text())
    path = artifact_project / value[field]
    if fault == "missing": path.unlink()  # Only the isolated temporary copy.
    else: path.write_bytes(b"corrupt temporary test artifact")
    with pytest.raises(RuntimeError, match="API startup failed"):
        with TestClient(main.create_app(settings=replace(configured, project_root=artifact_project), database_factory=lambda url: database)):
            pass


@pytest.mark.parametrize("file,keys,value", [
    ("phase6_model_selection", ["selected_downstream_model"], "logistic"),
    ("calibration_manifest", ["models", "xgboost", "method"], "isotonic"),
    ("internal_score_manifest", ["pdo"], 40),
    ("internal_score_manifest", ["factor"], 1),
    ("explainability_manifest", ["model_output"], "probability"),
    ("explainability_manifest", ["calibration_version"], "changed"),
    ("explainability_manifest", ["test_set_evaluated"], True),
    ("xgboost_model_manifest", ["model_version"], "changed"),
])
def test_startup_rejects_contract_changes(artifact_project, file, keys, value):
    path = artifact_project / "data/metadata" / (file + ".json")
    data = json.loads(path.read_text())
    item = data
    for key in keys[:-1]: item = item[key]
    item[keys[-1]] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        runtime.load_runtime(artifact_project)


def test_import_and_factory_without_startup_side_effects(monkeypatch):
    loader, database = Mock(side_effect=AssertionError("startup only")), Mock(side_effect=AssertionError("startup only"))
    app = main.create_app(runtime_loader=loader, database_factory=database)
    assert app is not None
    loader.assert_not_called()
    database.assert_not_called()


def test_manifest_reproduction_is_aggregate_and_deterministic(artifact_project):
    first = manifest.generate_manifest(artifact_project)
    path = artifact_project / "data/metadata/api_manifest.json"
    before = path.read_bytes()
    second = manifest.generate_manifest(artifact_project)
    assert first == second and path.read_bytes() == before
    assert first["test_set_evaluated"] is False and first["database_schema_revision"] == "phase8_001"
    assert not {"api_key", "database_url", "record", "raw_probability", "reason_codes"} & set(first)
