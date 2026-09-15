"""Explicit environment configuration; never display secrets in repr/errors."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import re

from sqlalchemy.engine import make_url

SERVICE_VERSION = "credit-risk-api-1.0.0"
API_VERSION = "v1"
INPUT_SCHEMA_VERSION = "financial-record-1.0.0"


def postgres_url(value):
    try:
        url = make_url(value)
        if url.drivername != "postgresql+psycopg" or not url.database or not url.host:
            raise ValueError
    except Exception:
        raise ValueError("DATABASE_URL must specify PostgreSQL with psycopg") from None
    return url


@dataclass(frozen=True)
class Settings:
    project_root: Path
    api_key: str = field(repr=False)
    api_key_id: str
    database_url: str = field(repr=False)
    app_env: str = "development"
    requests_per_minute: int = 60
    max_body_bytes: int = 65536

    def __post_init__(self):
        if (len(self.api_key) < 32 or "replace" in self.api_key.lower() or
                self.api_key.lower() in {"password", "changeme"} or len(set(self.api_key)) < 8):
            raise ValueError("CREDIT_RISK_API_KEY requires a non-placeholder secret of at least 32 characters")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", self.api_key_id) or self.api_key in self.api_key_id:
            raise ValueError("CREDIT_RISK_API_KEY_ID requires a non-secret identifier")
        if self.app_env not in {"development", "test", "production"}:
            raise ValueError("Invalid APP_ENV")
        if type(self.requests_per_minute) is not int or not 1 <= self.requests_per_minute <= 100000:
            raise ValueError("Invalid RATE_LIMIT_REQUESTS_PER_MINUTE")
        if type(self.max_body_bytes) is not int or not 1 <= self.max_body_bytes <= 1048576:
            raise ValueError("Invalid MAX_REQUEST_BODY_BYTES")
        postgres_url(self.database_url)

    @classmethod
    def from_env(cls):
        # No dotenv import or implicit file loading; operators inject environment.
        try:
            return cls(Path(os.environ.get("CREDIT_RISK_PROJECT_ROOT", ".")).resolve(),
                os.environ["CREDIT_RISK_API_KEY"], os.environ["CREDIT_RISK_API_KEY_ID"], os.environ["DATABASE_URL"],
                os.environ.get("APP_ENV", "development"), int(os.environ.get("RATE_LIMIT_REQUESTS_PER_MINUTE", "60")),
                int(os.environ.get("MAX_REQUEST_BODY_BYTES", "65536")))
        except (KeyError, TypeError, ValueError):
            raise ValueError("Invalid or missing API environment configuration; consult .env.example") from None
