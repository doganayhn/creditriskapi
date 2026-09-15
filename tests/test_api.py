"""HTTP security/privacy and isolated migration/repository tests; synthetic inputs."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
import json
import io
import logging
from pathlib import Path
import secrets
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

from credit_risk.api import security
from credit_risk.api.main import create_app
from credit_risk.api.rate_limit import RateLimiter
from credit_risk.api.settings import Settings, postgres_url
from credit_risk.explainability.local import synthetic_records
from credit_risk.features.definitions import PRIMARY_MODEL_FEATURES
from credit_risk.persistence.database import Database
from credit_risk.persistence.models import PredictionEvent, SCHEMA_REVISION
from credit_risk.persistence.repository import PredictionRepository, PersistenceError
from credit_risk.service.inference import InferenceResult, Driver, Explanation

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def configured():
    return Settings(ROOT, secrets.token_urlsafe(40), "synthetic-client", "postgresql+psycopg://user:password@localhost/creditrisk")


def migrate(engine, target="head", downgrade=False):
    cfg = Config(str(ROOT / "alembic.ini"))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        (command.downgrade if downgrade else command.upgrade)(cfg, target)


@pytest.fixture
def database(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "isolated.db"), hide_parameters=True)
    migrate(engine)
    database = Database(engine)
    yield database
    database.close()


@pytest.fixture
def fake_runtime():
    def read(name):
        return json.loads((ROOT / "data/metadata" / (name + ".json")).read_text())
    return SimpleNamespace(model_manifest=read("xgboost_model_manifest"),
        calibration=read("calibration_manifest")["models"]["xgboost"],
        explanation_manifest=read("explainability_manifest"), mapping=SimpleNamespace(version=read("internal_score_manifest")["score_version"]),
        dataset_manifest=read("dataset_manifest"))


class StubService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.calls = 0

    def predict(self, record):
        self.calls += 1
        r = self.runtime
        return InferenceResult(r.model_manifest["model_version"], r.calibration["calibration_version"], "identity",
            r.mapping.version, -1., .25, .25, 520., 520, "default payment next month")

    def explain(self, record):
        return replace(self.predict(record), explanation=Explanation(self.runtime.explanation_manifest["explainability_version"],
            "raw_margin", -1., -.5, True, (Driver("credit_limit", "risk_increasing", .1, -2.),),
            (Driver("bill_amount_mean", "risk_decreasing", -.6, 12.),)))


@pytest.fixture
def client(configured, database, fake_runtime):
    app = create_app(settings=configured, runtime_loader=lambda root: fake_runtime, database_factory=lambda url: database)
    with TestClient(app) as client:
        app.state.service = StubService(fake_runtime)
        client.headers["X-API-Key"] = configured.api_key
        yield client


@pytest.fixture
def record():
    return next(iter(synthetic_records().values())).copy()


def test_prediction_audit_and_request_log_identity(client, record, database, configured, caplog):
    with caplog.at_level(logging.INFO, logger="credit_risk.api.requests"):
        response = client.post("/v1/predict", json=record, headers={"X-Request-ID": "client-supplied"})
    assert response.status_code == 200
    value = response.json()
    identifier = UUID(value["request_id"])
    assert identifier.version == 4 and response.headers["X-Request-ID"] == str(identifier)
    assert datetime.fromisoformat(value["timestamp"]).utcoffset().total_seconds() == 0
    assert value["raw_probability"] == value["reported_probability"]
    assert not {"decision", "recommendation", "risk_band", "explanation", "source_contributions"} & set(value)
    with database.sessions() as session:
        events = session.scalars(select(PredictionEvent)).all()
        assert len(events) == 1
        event = events[0]
        assert event.request_id == identifier and event.api_key_id == configured.api_key_id
        assert event.model_version == value["model_version"] and event.created_at.tzinfo is not None
        assert event.reason_codes_json is None and event.explainability_version is None
        assert event.raw_probability == value["raw_probability"] and event.internal_risk_score == value["internal_risk_score"]
    logs = [json.loads(item.message) for item in caplog.records if item.name == "credit_risk.api.requests"]
    assert logs[-1]["request_id"] == str(identifier) and logs[-1]["persistence_status"] == "committed"
    assert configured.api_key not in caplog.text and configured.database_url not in caplog.text
    assert "200000" not in caplog.text


def test_explain_audit_topk_only(client, record, database, configured):
    response = client.post("/v1/explain", json=record)
    assert response.status_code == 200
    result = response.json()
    explanation = result["explanation"]
    assert explanation["output_space"] == "raw_margin"
    assert "source_contributions" not in explanation and "values" not in explanation
    for direction in ("risk_increasing_drivers", "risk_decreasing_drivers"):
        assert len(explanation[direction]) <= 5
        for row in explanation[direction]:
            assert set(row) == {"source_feature", "direction", "shap_margin_contribution", "score_point_contribution"}
            assert row["shap_margin_contribution"] * row["score_point_contribution"] < 0
    with database.sessions() as session:
        event = session.get(PredictionEvent, UUID(result["request_id"]))
        assert event.reason_codes_json == {key: explanation[key] for key in ("risk_increasing_drivers", "risk_decreasing_drivers")}
        assert event.explainability_version == explanation["version"]
        persisted = {col.name: str(getattr(event, col.name)) for col in PredictionEvent.__table__.columns}
        assert configured.api_key not in json.dumps(persisted)
        assert not {"credit_limit", "customer_id", "raw_input", "features", "shap_values", "api_key"} & set(persisted)


@pytest.mark.parametrize("endpoint", ["model-info", "predict", "explain"])
@pytest.mark.parametrize("key", [None, "invalid"])
def test_missing_invalid_auth(client, record, endpoint, key):
    client.headers.pop("X-API-Key")
    headers = {} if key is None else {"X-API-Key": key}
    response = client.get("/v1/" + endpoint, headers=headers) if endpoint == "model-info" else client.post("/v1/" + endpoint, json=record, headers=headers)
    assert response.status_code == 401 and response.json()["error"]["code"] == "AUTHENTICATION_FAILED"
    assert client.app.state.service.calls == 0


def test_constant_time_helper_used(client, record, monkeypatch):
    compare = Mock(wraps=security.hmac.compare_digest)
    monkeypatch.setattr(security.hmac, "compare_digest", compare)
    assert client.post("/v1/predict", json=record).status_code == 200
    assert compare.call_count >= 1


@pytest.mark.parametrize("field,value", [("credit_limit", 0), ("credit_limit", -1), ("credit_limit", "200000"),
    ("credit_limit", True), ("credit_limit", None), ("bill_amount_2005_09", float("nan")),
    ("bill_amount_2005_09", float("inf")), ("bill_amount_2005_09", float("-inf")),
    ("bill_amount_2005_09", 1e308), ("repayment_status_2005_09", 10),
    ("repayment_status_2005_09", -3), ("repayment_status_2005_09", 1.5), ("repayment_status_2005_09", True)])
def test_invalid_schema_no_input_echo(client, record, field, value):
    record[field] = value
    response = client.post("/v1/predict", content=json.dumps(record), headers={"Content-Type": "application/json"})
    assert response.status_code == 422 and response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.app.state.service.calls == 0
    assert "20000" not in response.text and "input" not in response.json()["error"]


@pytest.mark.parametrize("field", ["customer_id", "sex", "age", "education", "marital_status", "default_next_month", "email", "unknown"])
def test_unknown_and_forbidden_fields_rejected(client, record, field):
    record[field] = "private-invalid-value"
    response = client.post("/v1/predict", json=record)
    assert response.status_code == 422 and "private-invalid-value" not in response.text


def test_missing_fields_batch_and_negative_money_policy(client, record):
    incomplete = record.copy()
    incomplete.pop("credit_limit")
    assert client.post("/v1/predict", json=incomplete).status_code == 422
    assert client.post("/v1/predict", json=[record]).status_code == 422
    record["bill_amount_2005_09"] = -10
    record["payment_amount_2005_09"] = -10  # Existing Phase-3 contract preserves monetary negatives.
    assert client.post("/v1/predict", json=record).status_code == 200


def test_rate_limit_window_health_and_retry(client, record):
    now = [0.]
    client.app.state.limiter = RateLimiter(2, clock=lambda: now[0])
    assert client.post("/v1/predict", json=record).status_code == 200
    assert client.post("/v1/explain", json=record).status_code == 200
    response = client.post("/v1/predict", json=record)
    assert response.status_code == 429 and response.headers["Retry-After"] == "60"
    assert client.get("/v1/health/live").status_code == 200
    now[0] = 60
    assert client.post("/v1/predict", json=record).status_code == 200


def test_rate_limiter_concurrency():
    limiter = RateLimiter(7, clock=lambda: 0)
    with ThreadPoolExecutor(max_workers=12) as pool:
        result = list(pool.map(lambda i: limiter.acquire("same-id"), range(100)))
    assert result.count(None) == 7
    assert limiter.acquire("different-id") is None


def test_body_size_and_media_type_before_inference(client, record):
    client.app.state.settings = replace(client.app.state.settings, max_body_bytes=1024)
    assert client.post("/v1/predict", content="x" * 2048, headers={"Content-Type": "application/json"}).status_code == 413
    assert client.post("/v1/explain", content="x", headers={"Content-Type": "text/plain"}).status_code == 415
    assert client.app.state.service.calls == 0


def test_chunked_body_limit_stops_receiving(client, configured):
    # Direct ASGI messages prove the guard caps bodies without Content-Length.
    app = client.app
    app.state.settings = replace(configured, max_body_bytes=12)
    received, sent = [], []
    async def receive():
        received.append(True)
        return {"type": "http.request", "body": b"x" * 8, "more_body": True}
    async def send(message):
        sent.append(message)
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
             "scheme": "http", "path": "/v1/predict", "raw_path": b"/v1/predict", "query_string": b"",
             "root_path": "", "headers": [(b"x-api-key", configured.api_key.encode()), (b"content-type", b"application/json")],
             "client": ("127.0.0.1", 1000), "server": ("testserver", 80)}
    asyncio.run(app(scope, receive, send))
    assert len(received) == 2 and sent[0]["status"] == 413
    assert app.state.service.calls == 0


def test_persistence_failure_rolls_back_and_hides_details(client, record, configured, caplog, monkeypatch):
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    session.commit.side_effect = RuntimeError(configured.database_url + configured.api_key + str(record))
    client.app.state.repository = PredictionRepository(lambda: session)
    with caplog.at_level(logging.INFO, logger="credit_risk.api.requests"):
        response = client.post("/v1/predict", json=record)
    assert response.status_code == 503 and response.json()["error"]["code"] == "PERSISTENCE_ERROR"
    session.rollback.assert_called_once()
    assert "raw_probability" not in response.text
    assert all(secret not in response.text + caplog.text for secret in (configured.api_key, configured.database_url, "200000"))


def test_error_privacy_for_internal_and_unknown_keys(client, record, configured, caplog):
    with caplog.at_level(logging.INFO, logger="credit_risk.api.requests"):
        response = client.post("/v1/predict", json={**record, configured.api_key: configured.database_url})
        assert response.status_code == 422
        assert configured.api_key not in response.text and configured.database_url not in response.text
        client.app.state.service.predict = Mock(side_effect=RuntimeError(configured.api_key + configured.database_url + "C:/private/model.joblib"))
        response = client.post("/v1/predict", json=record)
    assert response.status_code == 500 and response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert all(value not in response.text + caplog.text for value in (configured.api_key, configured.database_url, "C:/private", "Traceback", "200000"))


def test_health_readiness_failure_and_safe_model_info(client, database, monkeypatch, configured):
    assert client.get("/v1/health/ready").status_code == 200
    monkeypatch.setattr(database, "check_ready", Mock(side_effect=RuntimeError(configured.database_url)))
    assert client.get("/v1/health/ready").status_code == 503
    assert client.get("/v1/health/live").status_code == 200
    assert client.app.state.service.calls == 0
    info = client.get("/v1/model-info")
    assert info.status_code == 200 and info.json()["test_set_evaluated"] is False
    assert configured.api_key not in info.text and str(ROOT) not in info.text
    assert "threshold" not in info.text
    client.app.state.runtime = None
    assert client.get("/v1/health/ready").status_code == 503


def test_versioned_routes_openapi_and_no_cors(client, record):
    assert client.post("/predict", json=record).status_code == 404
    assert client.post("/v1/predict", json=record, headers={"Origin": "https://other.invalid"}).headers.get("access-control-allow-origin") is None
    schema = client.get("/openapi.json").json()
    assert set(schema["components"]["schemas"]["FinancialRecord"]["properties"]) == set(PRIMARY_MODEL_FEATURES)
    assert schema["paths"]["/v1/predict"]["post"]["security"] == [{"APIKeyHeader": []}]


def test_migration_upgrade_repeat_downgrade_and_schema(database):
    migrate(database.engine)
    database.check_ready()
    inspector = inspect(database.engine)
    assert {col["name"] for col in inspector.get_columns("prediction_events")} == set(PredictionEvent.__table__.columns.keys())
    assert {tuple(index["column_names"]) for index in inspector.get_indexes("prediction_events")} == {("created_at",), ("model_version",), ("api_key_id",)}
    migrate(database.engine, "base", downgrade=True)
    assert not inspect(database.engine).has_table("prediction_events")
    with pytest.raises(Exception):
        database.check_ready()
    migrate(database.engine)
    database.check_ready()


def test_postgresql_dialect_and_driver_configuration():
    sql = str(CreateTable(PredictionEvent.__table__).compile(dialect=postgresql.dialect()))
    assert "TIMESTAMP WITH TIME ZONE" in sql and "UUID" in sql and "ck_test_sealed" in sql
    assert postgres_url("postgresql+psycopg://user:password@localhost/db").get_driver_name() == "psycopg"
    for invalid in ("", "sqlite:///audit.db", "postgresql://user@localhost/db"):
        with pytest.raises(ValueError):
            postgres_url(invalid)


@pytest.mark.parametrize("field,value", [("api_key", ""), ("api_key", "replace-with-a-long-random-secret"),
    ("api_key_id", ""), ("database_url", ""), ("requests_per_minute", 0), ("max_body_bytes", 0)])
def test_bad_configuration(configured, field, value):
    with pytest.raises(ValueError):
        replace(configured, **{field: value})
    assert configured.api_key not in repr(configured) and configured.database_url not in repr(configured)


def test_startup_missing_env_and_database_failure(configured, fake_runtime, database, monkeypatch):
    for key in ("CREDIT_RISK_API_KEY", "CREDIT_RISK_API_KEY_ID", "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(RuntimeError, match="API startup failed"):
        with TestClient(create_app()):
            pass
    monkeypatch.setattr(database, "check_ready", Mock(side_effect=RuntimeError("private-db-detail")))
    close = Mock(wraps=database.close)
    monkeypatch.setattr(database, "close", close)
    with pytest.raises(RuntimeError, match="API startup failed"):
        with TestClient(create_app(settings=configured, runtime_loader=lambda root: fake_runtime, database_factory=lambda url: database)):
            pass
    close.assert_called_once()


@pytest.mark.parametrize("change", ["probability", "test_flag", "timestamp", "duplicate_id"])
def test_database_constraints_rollback(client, record, database, change):
    assert client.post("/v1/predict", json=record).status_code == 200
    with database.sessions() as session:
        original = session.scalars(select(PredictionEvent)).one()
        values = {col.name: getattr(original, col.name) for col in PredictionEvent.__table__.columns}
    values["request_id"] = uuid4()
    if change == "probability": values["reported_probability"] = 2
    elif change == "test_flag": values["test_set_evaluated"] = True
    elif change == "timestamp": values["created_at"] = datetime.now()
    else: values["request_id"] = original.request_id
    with database.sessions() as session:
        session.add(PredictionEvent(**values))
        with pytest.raises(Exception): session.commit()
        session.rollback()
        assert len(session.scalars(select(PredictionEvent)).all()) == 1


def test_schema_revision_mismatch_fails_readiness(database):
    with database.engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = 'unexpected'"))
    with pytest.raises(ValueError, match="revision"):
        database.check_ready()


def test_secret_cannot_be_used_as_audit_identity(configured):
    with pytest.raises(ValueError):
        replace(configured, api_key_id=configured.api_key)


def test_alembic_offline_postgresql_sql(monkeypatch):
    # Placeholder URL selects the dialect only; offline mode opens no connection.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost/creditrisk")
    output = io.StringIO()
    cfg = Config(str(ROOT / "alembic.ini"), output_buffer=output)
    command.upgrade(cfg, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE prediction_events" in sql and "TIMESTAMP WITH TIME ZONE" in sql
    assert "phase8_001" in sql and "ck_test_sealed" in sql and "UUID" in sql
