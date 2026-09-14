"""Standalone monotonic mappings fitted only on TRAIN OOF probabilities."""

import hashlib
import io
from pathlib import Path

import joblib
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit
from sklearn.isotonic import IsotonicRegression

from credit_risk.modeling.metrics import binary_target, validate_probabilities

METHODS = ("identity", "sigmoid", "isotonic")


class ProbabilityCalibrator:
    """One probability input, no customer features; sigmoid slope is constrained >= 0."""

    def __init__(self, method: str, epsilon: float = 1e-6):
        if method not in METHODS:
            raise ValueError("Unknown calibration method")
        if type(epsilon) not in (int, float) or not np.isfinite(epsilon) or not 0 < epsilon < .5:
            raise ValueError("Logit epsilon must be finite and in (0, .5)")
        self.method, self.epsilon = method, epsilon

    def fit(self, raw_probability, y):
        probability = validate_probabilities(raw_probability, len(y))
        target = binary_target(y, len(probability))
        self.fit_rows_ = len(target)
        if self.method == "sigmoid":
            x = logit(np.clip(probability, self.epsilon, 1 - self.epsilon))
            def objective(parameters):
                a, b = parameters
                z = a * x + b
                residual = expit(z) - target
                loss = float(np.mean(np.logaddexp(0, z) - target * z))
                gradient = np.array([np.mean(residual * x), np.mean(residual)])
                return loss, gradient
            result = minimize(objective, [1., 0.], jac=True, method="L-BFGS-B",
                              bounds=[(0., None), (None, None)],
                              options={"maxiter": 2000, "ftol": 1e-14, "gtol": 1e-9})
            if not result.success or not np.isfinite(result.x).all():
                raise ValueError(f"Sigmoid calibration did not converge: {result.message}")
            self.slope_, self.intercept_ = map(float, result.x)
            self.iterations_ = int(result.nit)
        elif self.method == "isotonic":
            self.mapping_ = IsotonicRegression(increasing=True, out_of_bounds="clip", y_min=0., y_max=1.)
            self.mapping_.fit(probability, target)
        self.fitted_ = True
        return self

    def transform(self, raw_probability) -> np.ndarray:
        if not getattr(self, "fitted_", False):
            raise ValueError("Calibration mapping is not fitted")
        probability = validate_probabilities(raw_probability, len(raw_probability))
        if self.method == "identity":
            result = probability.copy()  # Exact passthrough, including 0/1 endpoints.
        elif self.method == "sigmoid":
            x = logit(np.clip(probability, self.epsilon, 1 - self.epsilon))
            result = expit(self.slope_ * x + self.intercept_)
        else:
            result = self.mapping_.predict(probability)
        return validate_probabilities(result, len(probability))

    def parameters(self) -> dict:
        if not getattr(self, "fitted_", False):
            raise ValueError("Calibration mapping is not fitted")
        if self.method == "sigmoid":
            return {"slope": self.slope_, "intercept": self.intercept_, "iterations": self.iterations_,
                    "epsilon": self.epsilon, "slope_constraint": "nonnegative"}
        if self.method == "isotonic":
            return {"knots": len(self.mapping_.X_thresholds_), "out_of_bounds": "clip",
                    "fitted_input_min": float(self.mapping_.X_min_), "fitted_input_max": float(self.mapping_.X_max_)}
        return {"transformation": "none"}


def save_calibrator(calibrator, directory: Path, version: str) -> tuple[Path | None, str | None]:
    calibrator.parameters()  # Require fitted state, even for identity decisions.
    if calibrator.method == "identity":
        return None, None
    buffer = io.BytesIO()
    joblib.dump(calibrator, buffer)
    content = buffer.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{version}_{digest}.joblib"
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("Existing calibrator artifact has unexpected bytes")
    else:
        with path.open("xb") as stream:
            stream.write(content)
    return path, digest


def load_calibrator(path: Path, digest: str) -> ProbabilityCalibrator:
    """Load only trusted local artifacts; a matching hash cannot make untrusted pickle safe."""
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError("Calibrator artifact checksum mismatch")
    calibrator = joblib.load(io.BytesIO(content))
    if not isinstance(calibrator, ProbabilityCalibrator):
        raise ValueError("Expected ProbabilityCalibrator artifact")
    calibrator.parameters()
    return calibrator
