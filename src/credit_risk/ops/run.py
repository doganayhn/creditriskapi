"""Read-only audit/summary CLI. Generic failures never disclose DB credentials."""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from sqlalchemy import select

from credit_risk.persistence.database import Database
from credit_risk.persistence.models import PredictionEvent
from credit_risk.ops.audit import audit_rows
from credit_risk.ops.contracts import contracts
from credit_risk.ops.monitoring import summarize


def collect(database, start, end):
    # Do not even fetch top-k reasons, key IDs or full records for monitoring.
    names = ("request_id", "api_version", "request_schema_version", "model_name", "model_version",
        "model_artifact_sha256", "calibration_version", "calibration_method", "score_version",
        "explainability_version", "explanation_requested", "score_point_decomposition_supported",
        "raw_probability", "reported_probability", "raw_margin", "internal_risk_score",
        "inference_latency_ms", "test_set_evaluated", "endpoint_type")
    query = select(*(getattr(PredictionEvent, n) for n in names)).where(
        PredictionEvent.created_at >= start, PredictionEvent.created_at < end)
    with database.engine.connect() as connection:
        return list(connection.execute(query).mappings())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "summary"))
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--minimum-count", type=int, default=100)
    args = parser.parse_args(argv)
    database = None
    try:
        if not 0 < args.hours <= 24*366: raise ValueError("Invalid window")
        root = Path(os.environ.get("CREDIT_RISK_PROJECT_ROOT", "."))
        expected = contracts(root)
        database = Database.connect(os.environ["DATABASE_URL"])
        database.check_ready()
        end = datetime.now(timezone.utc); start = end-timedelta(hours=args.hours)
        rows = collect(database, start, end)
        audit = audit_rows(rows, expected)
        result = {"window_start": start.isoformat(), "window_end": end.isoformat(), "audit": audit, "test_set_evaluated": False}
        if args.command == "summary" and audit["valid"]:
            baseline = json.loads((root / "data/metadata/monitoring_baseline.json").read_text())
            for key, field in (("source_model_version", "model_version"), ("calibration_version", "calibration_version"), ("score_version", "score_version")):
                if baseline[key] != expected[field]: raise ValueError("Baseline identity mismatch")
            if baseline["source_population"] != "validation" or baseline["test_set_evaluated"] is not False: raise ValueError("Invalid baseline")
            result["summary"] = summarize(rows, baseline, args.minimum_count)
        print(json.dumps(result, allow_nan=False, sort_keys=True))
        return 0 if audit["valid"] else 1
    except Exception:
        print(json.dumps({"error": "Operational check failed; verify configuration, database and metadata", "test_set_evaluated": False}))
        return 1
    finally:
        if database is not None: database.close()


if __name__ == "__main__":
    raise SystemExit(main())
