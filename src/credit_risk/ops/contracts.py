"""Read frozen identities from tracked metadata, never hard-coded hashes."""

import json
from pathlib import Path


def contracts(root):
    directory = Path(root) / "data/metadata"
    def read(name):
        return json.loads((directory / (name + ".json")).read_text(encoding="utf-8"))
    api = read("api_manifest")
    model = read("xgboost_model_manifest")
    calibration = read("calibration_manifest")["models"]["xgboost"]
    score = read("internal_score_manifest")
    explanation = read("explainability_manifest")
    expected = {"api_version": api["api_version"], "request_schema_version": api["input_schema_version"],
        "model_name": api["selected_model_name"], "model_version": model["model_version"],
        "model_artifact_sha256": model["artifact_sha256"],
        "calibration_version": calibration["calibration_version"], "calibration_method": calibration["method"],
        "score_version": score["score_version"], "explainability_version": explanation["explainability_version"]}
    if (api["selected_model_version"] != expected["model_version"] or
            api["model_artifact_sha256"] != expected["model_artifact_sha256"] or
            any(api[k] != expected[k] for k in ("calibration_version", "calibration_method", "score_version", "explainability_version")) or
            any(x.get("test_set_evaluated") is not False for x in (api, model, calibration, score, explanation))):
        raise ValueError("Operational metadata contract mismatch")
    return expected
