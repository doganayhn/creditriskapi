"""Portable audit schema; PostgreSQL is the production target."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, Integer, JSON, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

SCHEMA_REVISION = "phase8_001"


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Audit timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)  # Isolated SQLite test dialect.
        return value


class Base(DeclarativeBase):
    pass


class PredictionEvent(Base):
    __tablename__ = "prediction_events"
    __table_args__ = (
        CheckConstraint("raw_probability >= 0 AND raw_probability <= 1", name="ck_raw_probability"),
        CheckConstraint("reported_probability >= 0 AND reported_probability <= 1", name="ck_reported_probability"),
        CheckConstraint("test_set_evaluated = false", name="ck_test_sealed"),
        CheckConstraint("inference_latency_ms >= 0", name="ck_latency"),
        CheckConstraint("endpoint_type IN ('predict', 'explain')", name="ck_endpoint"),
    )
    request_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    endpoint_type: Mapped[str] = mapped_column(String(16))
    api_version: Mapped[str] = mapped_column(String(16))
    request_schema_version: Mapped[str] = mapped_column(String(100))
    api_key_id: Mapped[str] = mapped_column(String(100), index=True)
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(100), index=True)
    model_artifact_sha256: Mapped[str] = mapped_column(String(64))
    calibration_version: Mapped[str] = mapped_column(String(100))
    calibration_method: Mapped[str] = mapped_column(String(32))
    explainability_version: Mapped[str | None] = mapped_column(String(100))
    score_version: Mapped[str] = mapped_column(String(100))
    raw_margin: Mapped[float] = mapped_column(Float)
    raw_probability: Mapped[float] = mapped_column(Float)
    reported_probability: Mapped[float] = mapped_column(Float)
    internal_risk_score: Mapped[float] = mapped_column(Float)
    display_score: Mapped[int] = mapped_column(Integer)
    explanation_requested: Mapped[bool] = mapped_column(Boolean)
    score_point_decomposition_supported: Mapped[bool | None] = mapped_column(Boolean)
    reason_codes_json: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    inference_latency_ms: Mapped[float] = mapped_column(Float)
    test_set_evaluated: Mapped[bool] = mapped_column(Boolean, default=False)
