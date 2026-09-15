"""Strict financial allowlist and finite output schemas; never lending decisions."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator
import pandas as pd
import numpy as np

from credit_risk.features.definitions import PRIMARY_MODEL_FEATURES, REPAYMENT_COLUMNS
from credit_risk.features.engineering import engineer_features
from credit_risk.service.inference import Explanation

FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class FinancialBase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    @model_validator(mode="after")
    def domain_contract(self):
        # Reuse the existing domain validator, including status codes and numerical
        # overflow. Negative monetary values are retained by the Phase-3 contract.
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                engineer_features(pd.DataFrame([self.model_dump()], columns=PRIMARY_MODEL_FEATURES))
        except (ValueError, ArithmeticError, TypeError):
            raise ValueError("Financial record violates the supported feature contract") from None
        return self


FinancialRecord = create_model("FinancialRecord", __base__=FinancialBase,
    **{name: (Annotated[int, Field(strict=True)] if name in REPAYMENT_COLUMNS else
              Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)] if name == "credit_limit" else FiniteNumber, ...)
       for name in PRIMARY_MODEL_FEATURES})
FinancialRecord.__doc__ = "One financial record: 19 required fields; no identity, demographics or outcome label."


class PredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    request_id: UUID
    api_version: Literal["v1"]
    model_version: str
    calibration_version: str
    calibration_method: Literal["identity"]
    score_version: str
    raw_margin: FiniteNumber
    raw_probability: Probability
    reported_probability: Probability
    internal_risk_score: FiniteNumber = Field(description="Continuous project-specific score; higher means lower modeled risk, not FICO or lending policy.")
    display_score: int
    probability_event: str
    timestamp: datetime


class ExplanationResponse(PredictionResponse):
    explanation: Explanation = Field(description="Top-k model diagnostics in raw log-odds. Full contributions sum to margin, not probability; this excerpt is not the full sum.")


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: UUID
    fields: list[dict] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SafeMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ModelIdentity(SafeMetadata):
    name: str
    version: str
    sha256: str


class CalibrationIdentity(SafeMetadata):
    version: str
    method: Literal["identity"]


class ExplanationIdentity(SafeMetadata):
    version: str
    output_space: Literal["raw_margin"]


class ScoreIdentity(SafeMetadata):
    version: str
    higher_score_means: str


class ModelInfoResponse(SafeMetadata):
    api_version: Literal["v1"]
    service_version: str
    model: ModelIdentity
    calibration: CalibrationIdentity
    explainability: ExplanationIdentity
    internal_score: ScoreIdentity
    target: str
    business_decision_defined: Literal[False]
    test_set_evaluated: Literal[False]


class HealthResponse(SafeMetadata):
    status: Literal["ok", "ready"]
