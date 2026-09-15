"""Application factory with explicit startup-scoped frozen runtime and database."""

from contextlib import asynccontextmanager
from dataclasses import asdict
import logging
from time import perf_counter

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.security import APIKeyHeader
from starlette.exceptions import HTTPException

from credit_risk.api.errors import APIError, error_response
from credit_risk.api.middleware import RequestGuard, logger
from credit_risk.api.rate_limit import RateLimiter
from credit_risk.api.schemas import FinancialRecord, PredictionResponse, ExplanationResponse, ErrorResponse, ModelInfoResponse, HealthResponse
from credit_risk.api.settings import Settings, API_VERSION, SERVICE_VERSION, INPUT_SCHEMA_VERSION
from credit_risk.features.definitions import PRIMARY_MODEL_FEATURES
from credit_risk.persistence.database import Database
from credit_risk.persistence.repository import PersistenceError, PredictionRepository
from credit_risk.service.inference import InferenceService
from credit_risk.service.runtime import load_runtime


def create_app(*, settings=None, runtime_loader=None, database_factory=None, limiter=None):
    @asynccontextmanager
    async def lifespan(app):
        database = None
        try:
            configured = settings or Settings.from_env()
            runtime = (runtime_loader or load_runtime)(configured.project_root)
            database = (database_factory or Database.connect)(configured.database_url)
            database.check_ready()
            app.state.settings = configured
            app.state.runtime = runtime
            app.state.service = InferenceService(runtime)
            app.state.database = database
            app.state.repository = PredictionRepository(database.sessions)
            app.state.limiter = limiter or RateLimiter(configured.requests_per_minute)
            logger.setLevel(logging.INFO)
            if not logger.handlers:
                logger.addHandler(logging.StreamHandler())
        except Exception:
            if database is not None:
                database.close()
            raise RuntimeError("API startup failed: verify environment, frozen artifact contracts and migrated database") from None
        try:
            yield
        finally:
            app.state.runtime = None
            database.close()

    app = FastAPI(title="Credit Risk Model API", version=SERVICE_VERSION, lifespan=lifespan,
        description="Model outputs for dataset-defined default payment next month. No business lending decisions. SHAP explains raw margin, not probability.")
    app.add_middleware(RequestGuard)
    # Header dependency documents security in OpenAPI. RequestGuard performs actual
    # constant-time verification before body reading and schema processing.
    secured = [Depends(APIKeyHeader(name="X-API-Key", auto_error=False))]
    errors = {code: {"model": ErrorResponse} for code in (401, 413, 415, 422, 429, 500, 503)}

    @app.exception_handler(APIError)
    async def api_error(request, exc):
        return error_response(exc.code, exc.status, request.state.request_id)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Unknown field names can themselves contain sensitive strings. Never echo
        # arbitrary locations, rejected input, custom exception messages or context.
        allowed = set(PRIMARY_MODEL_FEATURES) | {"body"}
        fields = [{"location": [part if part in allowed else "unknown_field" for part in item["loc"]],
                   "type": item["type"]} for item in exc.errors()[:25]]
        return error_response("VALIDATION_ERROR", 422, request.state.request_id, fields=fields)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "VALIDATION_ERROR")
        return error_response(code, exc.status_code, request.state.request_id)

    @app.get("/v1/health/live", response_model=HealthResponse)
    def live():
        return {"status": "ok"}

    @app.get("/v1/health/ready", response_model=HealthResponse, responses={503: {"model": ErrorResponse}})
    def ready(request: Request):
        if getattr(request.app.state, "runtime", None) is None:
            raise APIError("SERVICE_NOT_READY", 503)
        try:
            request.app.state.database.check_ready()
        except Exception:
            raise APIError("SERVICE_NOT_READY", 503) from None
        return {"status": "ready"}

    @app.get("/v1/model-info", dependencies=secured, response_model=ModelInfoResponse, responses=errors)
    def model_info(request: Request):
        r = request.app.state.runtime
        if r is None:
            raise APIError("SERVICE_NOT_READY", 503)
        return {"api_version": API_VERSION, "service_version": SERVICE_VERSION,
            "model": {"name": r.explanation_manifest["model_name"], "version": r.model_manifest["model_version"],
                      "sha256": r.model_manifest["artifact_sha256"]},
            "calibration": {"version": r.calibration["calibration_version"], "method": r.calibration["method"]},
            "explainability": {"version": r.explanation_manifest["explainability_version"], "output_space": "raw_margin"},
            "internal_score": {"version": r.mapping.version, "higher_score_means": "lower modeled default risk"},
            "target": r.dataset_manifest["canonical_target_column"],
            "business_decision_defined": False, "test_set_evaluated": False}

    def infer(record, request, explain):
        if getattr(request.app.state, "runtime", None) is None:
            raise APIError("SERVICE_NOT_READY", 503)
        state = request.app.state
        start = perf_counter()
        result = state.service.explain(record.model_dump()) if explain else state.service.predict(record.model_dump())
        latency = (perf_counter() - start) * 1000
        payload = {**asdict(result), "request_id": request.state.request_id, "timestamp": request.state.timestamp,
                   "api_version": API_VERSION}
        if not explain:
            del payload["explanation"]
        response = (ExplanationResponse if explain else PredictionResponse).model_validate(payload)
        try:
            state.repository.save_prediction(result, request_id=request.state.request_id, timestamp=request.state.timestamp,
                endpoint_type="explain" if explain else "predict", api_key_id=request.state.api_key_id,
                model_name=state.runtime.explanation_manifest["model_name"],
                model_sha256=state.runtime.model_manifest["artifact_sha256"], api_version=API_VERSION,
                schema_version=INPUT_SCHEMA_VERSION, latency_ms=latency)
        except PersistenceError:
            request.state.persistence_status = "failed"
            raise APIError("PERSISTENCE_ERROR", 503) from None
        request.state.persistence_status = "committed"
        return response

    @app.post("/v1/predict", dependencies=secured, response_model=PredictionResponse, responses=errors)
    def predict(record: FinancialRecord, request: Request):
        return infer(record, request, False)

    @app.post("/v1/explain", dependencies=secured, response_model=ExplanationResponse, responses=errors)
    def explain(record: FinancialRecord, request: Request):
        return infer(record, request, True)

    return app
