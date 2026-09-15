"""Typed single-record inference; reuse Phase-3 and Phase-7 mathematics."""

from dataclasses import dataclass
from threading import Lock
from typing import Literal

import numpy as np
import pandas as pd
from scipy.special import expit

from credit_risk.explainability.local import explain_record
from credit_risk.features.definitions import PRIMARY_MODEL_FEATURES
from credit_risk.features.engineering import engineer_features
from credit_risk.features.preprocessing import transform_split
from credit_risk.modeling.xgboost_challenger import raw_probabilities
from credit_risk.service.runtime import FrozenRuntime


@dataclass(frozen=True)
class Driver:
    source_feature: str
    direction: Literal["risk_increasing", "risk_decreasing"]
    shap_margin_contribution: float
    score_point_contribution: float | None


@dataclass(frozen=True)
class Explanation:
    version: str
    output_space: Literal["raw_margin"]
    raw_margin: float
    base_margin: float
    score_point_decomposition_supported: bool
    risk_increasing_drivers: tuple[Driver, ...]
    risk_decreasing_drivers: tuple[Driver, ...]


@dataclass(frozen=True)
class InferenceResult:
    model_version: str
    calibration_version: str
    calibration_method: str
    score_version: str
    raw_margin: float
    raw_probability: float
    reported_probability: float
    internal_risk_score: float
    display_score: int
    probability_event: str
    explanation: Explanation | None = None


class InferenceService:
    def __init__(self, runtime: FrozenRuntime):
        self.runtime = runtime
        # TreeExplainer updates expected_value internally; protect its entire local
        # explanation call. Prediction-only requests use read-only native inference.
        self._explanation_lock = Lock()

    def predict(self, record: dict) -> InferenceResult:
        if set(record) != set(PRIMARY_MODEL_FEATURES):
            raise ValueError("Expected exactly the financial predictor fields")
        r = self.runtime
        X = transform_split(r.preprocessor, engineer_features(pd.DataFrame([record], columns=PRIMARY_MODEL_FEATURES)))
        margin = float(r.model.predict(X.toarray(), output_margin=True)[0])
        probability = float(raw_probabilities(r.model, X)[0])
        if not np.isfinite(margin) or abs(expit(margin) - probability) > r.options["probability_tolerance"]:
            raise ValueError("Raw margin/probability contract failed")
        score = float(r.mapping.transform([probability])[0][0])
        return self._result(margin, probability, score)

    def explain(self, record: dict) -> InferenceResult:
        r = self.runtime
        with self._explanation_lock:
            local = explain_record(record, r, r.explainer, r.mapping, r.rows,
                top_k=r.options["local_reason_top_k"], score_tolerance=r.options["score_tolerance"])
        def drivers(direction):
            return tuple(Driver(item["source_feature"], direction, item["contribution_to_raw_margin"],
                                item.get("score_point_contribution")) for item in local["drivers"][direction])
        explanation = Explanation(r.explanation_manifest["explainability_version"], "raw_margin", local["raw_margin"],
            local["shap_base_margin"], local["score_point_decomposition_supported"],
            drivers("risk_increasing"), drivers("risk_decreasing"))
        return self._result(local["raw_margin"], local["raw_probability"], local["internal_risk_score"], explanation)

    def _result(self, margin, probability, score, explanation=None):
        r = self.runtime
        return InferenceResult(r.model_manifest["model_version"], r.calibration["calibration_version"],
            r.calibration["method"], r.mapping.version, margin, probability, probability, score, int(round(score)),
            r.dataset_manifest["original_target_column"], explanation)
