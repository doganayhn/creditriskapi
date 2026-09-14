"""Historical experiment publication must preserve records and reject result drift."""

import json

import pandas as pd
import pytest

from credit_risk.config import load_config
from credit_risk.modeling import baseline, xgboost_challenger as challenger
from credit_risk.modeling import experiment_metadata as metadata
from test_modeling import model_project
from test_xgboost import settings, xgb_project


def test_scoped_hashes_ignore_later_modules_but_detect_dependencies(tmp_path):
    for name in metadata.XGBOOST_MODULES:
        (tmp_path / name).write_text(name)
    before = metadata.implementation_hashes(metadata.BASELINE_MODULES, tmp_path)
    (tmp_path / "calibration.py").write_text("unrelated later module")
    (tmp_path / "search.py").write_text("changed challenger search")
    assert metadata.implementation_hashes(metadata.BASELINE_MODULES, tmp_path) == before
    xgb_before = metadata.implementation_hashes(metadata.XGBOOST_MODULES, tmp_path)
    (tmp_path / "search.py").write_text("another search change")
    assert metadata.implementation_hashes(metadata.XGBOOST_MODULES, tmp_path) != xgb_before
    (tmp_path / "baseline.py").write_text("changed baseline")
    assert metadata.implementation_hashes(metadata.BASELINE_MODULES, tmp_path) != before


@pytest.fixture
def experiment(tmp_path):
    manifest = {"model_version": "fixed-1", "dataset_sha256": "data", "configuration": {"C": 1},
                "preprocessing_artifact_sha256": "pre", "artifact_sha256": "model",
                "implementation_sha256": {"old.py": "old"}}
    outputs = {"metrics.json": {"validation": {"roc_auc": .75}, "test_set_evaluated": False}}
    table = pd.DataFrame([{"candidate_index": 0, "selected": True, "mean_test_roc_auc": .75,
                           "mean_fit_time": 2.1, "mean_score_time": .01}])
    path = tmp_path / "manifest.json"
    metadata.publish_experiment(path, manifest, outputs, table)
    return path, manifest, outputs, table


def snapshot(directory):
    return {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir() if p.is_file()}


def test_reproduction_preserves_bytes_mtime_provenance_and_original_timings(experiment):
    path, manifest, outputs, table = experiment
    previous = snapshot(path.parent)
    manifest["implementation_sha256"] = {"scoped.py": "new", "metadata.py": "new"}
    manifest["generated_at"] = "later"
    table["mean_fit_time"], table["mean_score_time"] = 999., 999.
    result = metadata.publish_experiment(path, manifest, outputs, table)
    assert result == json.loads(previous[path.name][0])
    assert snapshot(path.parent) == previous


@pytest.mark.parametrize("field,value", [("dataset_sha256", "changed"), ("configuration", {"C": 2}),
    ("preprocessing_artifact_sha256", "changed"), ("artifact_sha256", "changed")])
def test_semantic_change_rejected_without_any_metadata_write(experiment, field, value):
    path, manifest, outputs, table = experiment
    previous = snapshot(path.parent)
    manifest[field] = value
    with pytest.raises(ValueError, match="identity/result changed"):
        metadata.publish_experiment(path, manifest, outputs, table)
    assert snapshot(path.parent) == previous


@pytest.mark.parametrize("change", ["predictive_metric", "cv_score", "candidate", "missing_output"])
def test_output_drift_or_missing_record_rejected_without_partial_writes(experiment, change):
    path, manifest, outputs, table = experiment
    if change == "predictive_metric":
        outputs["metrics.json"]["validation"]["roc_auc"] = .76
    elif change == "cv_score":
        table.loc[0, "mean_test_roc_auc"] = .76
    elif change == "candidate":
        table.loc[0, "candidate_index"] = 1
    else:
        (path.parent / "metrics.json").unlink()
    previous = snapshot(path.parent)
    with pytest.raises(ValueError, match="Historical"):
        metadata.publish_experiment(path, manifest, outputs, table)
    assert snapshot(path.parent) == previous


def test_actual_baseline_and_challenger_reproduction_preserves_historical_records(xgb_project, monkeypatch):
    challenger.run_challenger(xgb_project)
    directory = load_config(xgb_project).paths.metadata
    # Simulate legacy broad provenance. It must remain the original run's record.
    for name in ("baseline_model_manifest.json", "xgboost_model_manifest.json"):
        path = directory / name
        record = json.loads(path.read_text())
        record["implementation_sha256"]["unrelated_future_module.py"] = "historical digest"
        path.write_text(json.dumps(record, indent=3) + "\n")
    xgb_path = directory / "xgboost_model_manifest.json"
    record = json.loads(xgb_path.read_text())
    record["baseline_manifest_sha256"] = metadata.sha256_file(directory / "baseline_model_manifest.json")
    xgb_path.write_text(json.dumps(record, indent=3) + "\n")
    before = snapshot(directory)
    original_table = challenger.search_table
    def changed_timings(search):
        table = original_table(search)
        table.loc[:, list(metadata.TIMING_COLUMNS)] = 999.
        return table
    monkeypatch.setattr(challenger, "search_table", changed_timings)
    baseline.run_baseline(xgb_project)
    challenger.run_challenger(xgb_project)
    assert snapshot(directory) == before
