"""Explicit commit-before-success and rollback-on-failure audit persistence."""

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from credit_risk.persistence.models import PredictionEvent
from credit_risk.service.inference import InferenceResult


class PersistenceError(Exception):
    pass


class PredictionRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save_prediction(self, result: InferenceResult, *, request_id: UUID, timestamp: datetime,
                        endpoint_type: str, api_key_id: str, model_name: str, model_sha256: str,
                        api_version: str, schema_version: str, latency_ms: float):
        explanation = result.explanation
        reasons = None if explanation is None else {
            "risk_increasing_drivers": [asdict(row) for row in explanation.risk_increasing_drivers],
            "risk_decreasing_drivers": [asdict(row) for row in explanation.risk_decreasing_drivers]}
        event = PredictionEvent(request_id=request_id, created_at=timestamp, endpoint_type=endpoint_type,
            api_version=api_version, request_schema_version=schema_version, api_key_id=api_key_id,
            model_name=model_name, model_version=result.model_version, model_artifact_sha256=model_sha256,
            calibration_version=result.calibration_version, calibration_method=result.calibration_method,
            explainability_version=explanation.version if explanation else None, score_version=result.score_version,
            raw_margin=result.raw_margin, raw_probability=result.raw_probability,
            reported_probability=result.reported_probability, internal_risk_score=result.internal_risk_score,
            display_score=result.display_score, explanation_requested=explanation is not None,
            score_point_decomposition_supported=explanation.score_point_decomposition_supported if explanation else None,
            reason_codes_json=reasons, inference_latency_ms=latency_ms, test_set_evaluated=False)
        try:
            with self.session_factory() as session:
                try:
                    session.add(event)
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
        except Exception:
            raise PersistenceError("Required audit persistence failed") from None
