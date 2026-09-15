# PostgreSQL Target

PostgreSQL through SQLAlchemy 2.0.53 and psycopg 3.3.5 is the production persistence target. DATABASE_URL must use postgresql+psycopg with a host and database. Production never silently falls back to SQLite. Phase 8 had no live PostgreSQL server. Phase 9 subsequently verified PostgreSQL 17.10 through local Compose. Isolated tests use temporary SQLite databases; PostgreSQL dialect/driver configuration and generated migration SQL are also checked.

# SQLAlchemy Architecture

The application creates one engine/session factory during lifespan startup, uses pool pre-ping and bounded connection/pool acquisition waits, and disposes the engine at shutdown. A separate repository owns audit writes. Routes contain no SQL. Each request uses a separate session. SQL echo is disabled and bound parameters are hidden in SQLAlchemy exception formatting; application error handling never logs exception strings.

# Alembic Migration

Initial revision: phase8_001. Run `.venv\Scripts\python.exe -m alembic upgrade head` with DATABASE_URL configured before starting the API. Startup never calls create_all or runs migrations. Migrations permit an explicitly injected connection for isolated testing; this is not an embedded production fallback.

Isolated upgrade creates the table, repeated upgrade is safe, downgrade removes it, and re-upgrade works. Readiness checks SELECT 1, the exact Alembic revision, column names/types/nullability, primary identity, required constraints and a zero-row schema query. PostgreSQL timestamps must retain timezone. No historical customer row is read for readiness.

# prediction_events Schema

| Group | Columns |
| --- | --- |
| Request | request_id (UUID primary key), created_at (timezone-aware UTC), endpoint_type, api_version, request_schema_version, api_key_id |
| Model | model_name, model_version, model_artifact_sha256 |
| Calibration | calibration_version, calibration_method |
| Explanation/score | nullable explainability_version, score_version |
| Outputs | raw_margin, raw_probability, reported_probability, internal_risk_score, display_score |
| Diagnostics | explanation_requested, nullable score_point_decomposition_supported, nullable reason_codes_json |
| Operations | inference_latency_ms, test_set_evaluated |

Required version/output fields are non-null. Probability constraints require values between zero and one; endpoint_type is predict/explain; latency is nonnegative; test_set_evaluated must be false. Request UUID is unique. Indexes cover created_at, model_version and api_key_id. Float columns retain canonical continuous values; display_score is additional presentation data. SQLite tests explicitly restore UTC on read because that dialect drops timezone information.

# What Is Persisted

Successful inference output and audit identities only. Explanation events may store the safe top-k source name, direction, margin contribution and score-point contribution. Prediction events store null explanation version/reasons. Request ID and UTC timestamp match the API response; the same request ID appears in the structured operational log.

# What Is Not Persisted

Raw request financial inputs are not persisted in V1. Neither are API-key secrets, direct customer identity, demographic fields, target labels, full transformed features, full SHAP/source vectors or TEST data. No deterministic input fingerprint is stored or described as anonymization.

# Transaction Semantics

Calculate inference, validate the response, construct an allowlisted audit event, commit the database transaction, then return success. A failed write/commit triggers rollback and session cleanup. There is no automatic retry that could create duplicate events.

# Fail-Closed Audit Policy

Mandatory audit failure returns HTTP 503 with PERSISTENCE_ERROR and a request ID. No successful probability/score response is returned. The safe log records persistence_status=failed without SQL, credentials or payload. A connection failure after the server committed can leave an uncertain outcome; there is no V1 idempotency/reconciliation API. Each retry receives a fresh request ID. Operational recovery and retention policy require future work.

# API Key Audit Identity

CREDIT_RISK_API_KEY_ID is an explicitly configured non-secret identifier. It is persisted; the credential is not. The configuration rejects using the actual API secret inside the audit ID. Credential rotation and multiple-client management are future operational work.

# Privacy Considerations

Financial output probabilities, scores and top-k diagnostics remain sensitive even without raw input. An operator must control database access, retention and backups. Omitting raw inputs reduces retention but prevents exact reconstruction of a historical request from this table alone. Stronger reconstruction would require a separate secure/encrypted retention design and authorization.

# Current Limitations

Phase 9 passed actual PostgreSQL migration/schema inspection, UUID/timezone/index/constraint checks, synthetic predict/explain write/read matching, API/DB restart persistence, controlled outage/recovery and 10 concurrent requests. Temporary SQLite remains the ordinary unit-test dependency. Local Docker is implemented; external secret management, TLS termination, distributed rate limiting, observability infrastructure and business policy remain absent. TEST remains sealed.


# Phase-9 Validation

The dedicated creditrisk-phase9 project uses its own named volume and synthetic records only. Existing rows survived API and database restarts. Readiness returned 503 during DB outage; prediction/explanation did not return unaudited success, and recovery passed. Raw financial inputs, secrets and full vectors remain excluded. The API schema/revision and transaction policy were not changed. See [deployment](deployment.md) and the [Phase-9 report](phase_reports/phase_09_completion_report.md).
