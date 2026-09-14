"""Public Tree SHAP raw-margin semantics with independent numerical checks."""

import numpy as np
from scipy.special import expit
import shap

from credit_risk.modeling.baseline import validate_matrix
from credit_risk.modeling.xgboost_challenger import raw_probabilities


def residual_summary(residual):
    values = np.abs(np.asarray(residual, dtype=float))
    if not values.size or not np.isfinite(values).all():
        raise ValueError("Invalid numerical residuals")
    return {"max_absolute_error": float(values.max()), "mean_absolute_error": float(values.mean()),
            "p50_absolute_error": float(np.quantile(values, .5)),
            "p95_absolute_error": float(np.quantile(values, .95)),
            "p99_absolute_error": float(np.quantile(values, .99))}


class MarginExplainer:
    def __init__(self, model, names, *, margin_tolerance=1e-5, probability_tolerance=1e-7):
        self.model, self.names = model, tuple(names)
        if len(set(self.names)) != len(self.names) or model.n_features_in_ != len(self.names):
            raise ValueError("Model feature width/names disagree")
        booster = model.get_booster()
        known = {f"f{i}" for i in range(len(self.names))}
        if booster.feature_names is not None and tuple(booster.feature_names) != self.names:
            raise ValueError("Native model feature names disagree")
        if not set(booster.get_score()).issubset(known | set(self.names)):
            raise ValueError("Unknown XGBoost feature index")
        self.margin_tolerance, self.probability_tolerance = margin_tolerance, probability_tolerance
        self.explainer = shap.TreeExplainer(model, model_output="raw",
            feature_perturbation="tree_path_dependent", feature_names=list(names))

    def explain(self, X):
        validate_matrix(X)
        if X.shape[1] != len(self.names):
            raise ValueError("Explanation feature width changed")
        dense = X.toarray()  # Preserve the canonical XGBoost zero semantics.
        margins = np.asarray(self.model.predict(dense, output_margin=True), dtype=float)
        probability = raw_probabilities(self.model, X)
        reconstruction = residual_summary(expit(margins) - probability)
        if reconstruction["max_absolute_error"] > self.probability_tolerance:
            raise ValueError("Raw-margin probability reconstruction failed")
        values = np.asarray(self.explainer.shap_values(dense, check_additivity=True, approximate=False), dtype=float)
        base = np.asarray(self.explainer.expected_value, dtype=float)
        if values.shape != X.shape or base.size != 1 or not np.isfinite(values).all():
            raise ValueError("Unexpected binary raw-margin SHAP dimensions/values")
        bases = np.full(X.shape[0], float(base.reshape(-1)[0]))
        additivity = residual_summary(bases + values.sum(axis=1) - margins)
        linked = residual_summary(expit(bases + values.sum(axis=1)) - probability)
        if additivity["max_absolute_error"] > self.margin_tolerance:
            raise ValueError("Independent SHAP raw-margin additivity failed")
        # Margin residual propagated through the logistic link has Lipschitz bound 1/4.
        if linked["max_absolute_error"] > self.margin_tolerance / 4 + self.probability_tolerance:
            raise ValueError("SHAP-linked probability reconstruction failed")
        return {"values": values, "base": bases, "raw_margin": margins, "raw_probability": probability,
                "probability_reconstruction": reconstruction, "additivity": additivity,
                "shap_linked_probability_reconstruction": linked}
