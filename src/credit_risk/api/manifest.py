"""Explicit offline aggregate API manifest publication, never on request/startup."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from credit_risk.api.settings import API_VERSION, SERVICE_VERSION, INPUT_SCHEMA_VERSION
from credit_risk.config import load_config
from credit_risk.data.download import write_json
from credit_risk.persistence.models import SCHEMA_REVISION
from credit_risk.service.runtime import load_runtime


def generate_manifest(root):
    runtime = load_runtime(root)
    path = load_config(Path(root)).paths.metadata / "api_manifest.json"
    value = {"api_version": API_VERSION, "service_version": SERVICE_VERSION, "input_schema_version": INPUT_SCHEMA_VERSION,
        "selected_model_name": runtime.explanation_manifest["model_name"],
        "selected_model_version": runtime.model_manifest["model_version"],
        "model_artifact_sha256": runtime.model_manifest["artifact_sha256"],
        "dataset_sha256": runtime.dataset_manifest["sha256"],
        "feature_engineering_version": runtime.preprocessing_manifest["feature_engineering_version"],
        "preprocessing_version": runtime.preprocessing_manifest["preprocessing_version"],
        "preprocessor_sha256": runtime.preprocessing_manifest["serialization_sha256"],
        "calibration_version": runtime.calibration["calibration_version"], "calibration_method": runtime.calibration["method"],
        "explainability_version": runtime.explanation_manifest["explainability_version"], "score_version": runtime.mapping.version,
        "endpoints": ["GET /v1/health/live", "GET /v1/health/ready", "GET /v1/model-info", "POST /v1/predict", "POST /v1/explain"],
        "authentication": "api_key", "rate_limit_type": "in_process", "default_requests_per_minute": 60,
        "persistence_target": "PostgreSQL", "database_schema_revision": SCHEMA_REVISION,
        "raw_inputs_persisted": False, "business_decision_defined": False, "test_set_evaluated": False}
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if {k: v for k, v in previous.items() if k != "generated_at"} == value:
            return previous
    value["generated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(path, value)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(generate_manifest(args.project_root), indent=2, allow_nan=False))
