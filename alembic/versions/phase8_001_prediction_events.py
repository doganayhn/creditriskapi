"""Create privacy-minimized inference audit events."""

from alembic import op
import sqlalchemy as sa

revision = "phase8_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("prediction_events",
        sa.Column("request_id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("endpoint_type", sa.String(16), nullable=False),
        sa.Column("api_version", sa.String(16), nullable=False),
        sa.Column("request_schema_version", sa.String(100), nullable=False),
        sa.Column("api_key_id", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("model_artifact_sha256", sa.String(64), nullable=False),
        sa.Column("calibration_version", sa.String(100), nullable=False),
        sa.Column("calibration_method", sa.String(32), nullable=False),
        sa.Column("explainability_version", sa.String(100), nullable=True),
        sa.Column("score_version", sa.String(100), nullable=False),
        sa.Column("raw_margin", sa.Float(), nullable=False),
        sa.Column("raw_probability", sa.Float(), nullable=False),
        sa.Column("reported_probability", sa.Float(), nullable=False),
        sa.Column("internal_risk_score", sa.Float(), nullable=False),
        sa.Column("display_score", sa.Integer(), nullable=False),
        sa.Column("explanation_requested", sa.Boolean(), nullable=False),
        sa.Column("score_point_decomposition_supported", sa.Boolean(), nullable=True),
        sa.Column("reason_codes_json", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("inference_latency_ms", sa.Float(), nullable=False),
        sa.Column("test_set_evaluated", sa.Boolean(), nullable=False),
        sa.CheckConstraint("raw_probability >= 0 AND raw_probability <= 1", name="ck_raw_probability"),
        sa.CheckConstraint("reported_probability >= 0 AND reported_probability <= 1", name="ck_reported_probability"),
        sa.CheckConstraint("test_set_evaluated = false", name="ck_test_sealed"),
        sa.CheckConstraint("inference_latency_ms >= 0", name="ck_latency"),
        sa.CheckConstraint("endpoint_type IN ('predict', 'explain')", name="ck_endpoint"))
    for column in ("created_at", "model_version", "api_key_id"):
        op.create_index("ix_prediction_events_" + column, "prediction_events", [column])


def downgrade():
    op.drop_table("prediction_events")
