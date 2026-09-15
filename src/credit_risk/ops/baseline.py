"""Explicit one-time aggregate reference publication, never customer scoring."""

import csv
import hashlib
import json
from pathlib import Path
from credit_risk.ops import BASELINE_VERSION, OPERATIONS_VERSION
from credit_risk.ops.contracts import contracts


def build_baseline(root):
    root = Path(root); directory = root / "data/metadata"
    expected = contracts(root)
    path = directory / "score_decile_analysis.csv"
    with path.open(newline="", encoding="utf-8") as f: rows = list(csv.DictReader(f))
    if len(rows) != 10 or any(r["source"] != "validation" or r["test_set_evaluated"].lower() != "false" for r in rows):
        raise ValueError("Expected frozen validation aggregates")
    rows.sort(key=lambda r: float(r["min_score"]))
    boundaries = []
    for low, high in zip(rows, rows[1:]):
        if float(low["max_score"]) >= float(high["min_score"]):
            raise ValueError("Overlapping deciles cannot define exact bins from aggregates")
        boundaries.append((float(low["max_score"])+float(high["min_score"]))/2)
    counts = [int(r["count"]) for r in rows]; total = sum(counts)
    if min(counts) <= 0: raise ValueError("Empty reference bins")
    return {"baseline_version": BASELINE_VERSION, "source_population": "validation", "source_count": total,
        "source_aggregate_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_model_version": expected["model_version"], "calibration_version": expected["calibration_version"],
        "score_version": expected["score_version"], "binning_variable": "internal_risk_score",
        "score_bin_boundaries": boundaries, "bin_intervals": "left closed, right open; unbounded outer tails",
        "expected_bin_proportions": [n/total for n in counts],
        "expected_mean_reported_probability": sum(float(r["mean_reported_probability"])*n for r,n in zip(rows,counts))/total,
        "expected_mean_score": sum(float(r["mean_score"])*n for r,n in zip(rows,counts))/total,
        "psi_epsilon": 1e-6, "minimum_count": 100, "test_set_evaluated": False}


def operations_manifest(root, *, postgres_validated=False):
    api = json.loads((Path(root)/"data/metadata/api_manifest.json").read_text())
    return {"operations_version": OPERATIONS_VERSION, "api_version": api["api_version"],
        "service_version": api["service_version"], "model_version": api["selected_model_version"],
        "model_sha256": api["model_artifact_sha256"], "calibration_version": api["calibration_version"],
        "explainability_version": api["explainability_version"], "score_version": api["score_version"],
        "database_revision": api["database_schema_revision"], "containerized": True,
        "postgres_validated": postgres_validated, "artifact_delivery": "read_only_mount", "api_workers": 1,
        "rate_limit_type": "in_process", "monitoring_baseline_version": BASELINE_VERSION,
        "monitoring_metrics_supported": ["event_counts", "version_counts", "probability_statistics", "score_statistics", "latency_quantiles", "output_bins", "score_psi", "audit_contract_counts"],
        "customer_level_monitoring_artifacts_exported": False, "test_set_evaluated": False}


def publish_baseline(root):
    path = Path(root)/"data/metadata/monitoring_baseline.json"
    value = build_baseline(root)
    if path.exists() and json.loads(path.read_text()) != value:
        raise ValueError("Frozen baseline changed; a new reviewed version is required")
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
    return value


if __name__ == "__main__":
    publish_baseline(Path.cwd())
