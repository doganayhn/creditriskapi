"""Public errors contain fixed safe messages, never underlying exception text."""

from starlette.responses import JSONResponse

MESSAGES = {
    "AUTHENTICATION_FAILED": "Authentication failed.",
    "RATE_LIMIT_EXCEEDED": "Request rate limit exceeded.",
    "VALIDATION_ERROR": "Request validation failed.",
    "REQUEST_TOO_LARGE": "Request body exceeds the permitted size.",
    "UNSUPPORTED_MEDIA_TYPE": "A JSON request body is required.",
    "SERVICE_NOT_READY": "Service is not ready.",
    "PERSISTENCE_ERROR": "Required audit persistence failed.",
    "INTERNAL_ERROR": "Internal service error.",
    "NOT_FOUND": "Route not found.",
    "METHOD_NOT_ALLOWED": "Method not allowed.",
}


class APIError(Exception):
    def __init__(self, code, status):
        self.code, self.status = code, status
        super().__init__(code)


def error_response(code, status, request_id, *, headers=None, fields=None):
    error = {"code": code, "message": MESSAGES[code], "request_id": str(request_id)}
    if fields is not None:
        error["fields"] = fields
    return JSONResponse({"error": error}, status_code=status, headers=headers)
