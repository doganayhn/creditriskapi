"""Bounded ASGI body handling, pre-body authentication and safe request logging."""

from datetime import datetime, timezone
import json
import logging
from time import perf_counter
from uuid import uuid4

from credit_risk.api.errors import error_response
from credit_risk.api.security import valid_api_key

logger = logging.getLogger("credit_risk.api.requests")
PROTECTED = {"/v1/model-info", "/v1/predict", "/v1/explain"}
INFERENCE = {"/v1/predict", "/v1/explain"}
KNOWN = PROTECTED | {"/v1/health/live", "/v1/health/ready", "/docs", "/openapi.json", "/redoc"}


class RequestGuard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started, status = False, 500
        start = perf_counter()
        state = scope.setdefault("state", {})
        request_id = uuid4()
        state.update(request_id=request_id, timestamp=datetime.now(timezone.utc), api_key_id=None,
                     persistence_status="not_attempted")
        path = scope["path"]
        async def safe_send(message):
            nonlocal status, started
            if message["type"] == "http.response.start":
                status, started = message["status"], True
                message = {**message, "headers": [*message.get("headers", []),
                            (b"x-request-id", str(request_id).encode("ascii")), (b"cache-control", b"no-store")]}
            await send(message)
        async def reject(code, number, headers=None):
            await error_response(code, number, request_id, headers=headers)(scope, receive, safe_send)
        try:
            app_state = scope["app"].state
            settings = getattr(app_state, "settings", None)
            if path in PROTECTED:
                if settings is None:
                    return await reject("SERVICE_NOT_READY", 503)
                keys = [value for key, value in scope["headers"] if key.lower() == b"x-api-key"]
                if len(keys) != 1 or not valid_api_key(keys[0], settings.api_key):
                    return await reject("AUTHENTICATION_FAILED", 401)
                state["api_key_id"] = settings.api_key_id
                if path in INFERENCE:
                    retry = app_state.limiter.acquire(settings.api_key_id)
                    if retry is not None:
                        return await reject("RATE_LIMIT_EXCEEDED", 429, {"Retry-After": str(retry)})
            if path in INFERENCE and scope["method"] == "POST":
                types = [value for key, value in scope["headers"] if key.lower() == b"content-type"]
                if len(types) != 1 or types[0].split(b";", 1)[0].strip().lower() != b"application/json":
                    return await reject("UNSUPPORTED_MEDIA_TYPE", 415)
                lengths = [value for key, value in scope["headers"] if key.lower() == b"content-length"]
                if len(lengths) > 1 or (lengths and not lengths[0].isdigit()):
                    return await reject("VALIDATION_ERROR", 400)
                if lengths and int(lengths[0]) > settings.max_body_bytes:
                    return await reject("REQUEST_TOO_LARGE", 413)
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > settings.max_body_bytes:
                        return await reject("REQUEST_TOO_LARGE", 413)
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
                delivered = False
                async def bounded_receive():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await receive()
                await self.app(scope, bounded_receive, safe_send)
            else:
                await self.app(scope, receive, safe_send)
        except Exception:
            if not started:
                await reject("INTERNAL_ERROR", 500)
        finally:
            runtime = getattr(scope["app"].state, "runtime", None)
            logger.info(json.dumps({"request_id": str(request_id), "endpoint": path if path in KNOWN else "unmatched",
                "status_code": status, "api_key_id": state["api_key_id"],
                "model_version": runtime.model_manifest["model_version"] if runtime else None,
                "latency_ms": round((perf_counter() - start) * 1000, 3),
                "persistence_status": state["persistence_status"]}, allow_nan=False))
