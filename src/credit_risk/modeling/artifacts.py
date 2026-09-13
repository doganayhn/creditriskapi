"""Content-addressed serialization for trusted locally trained models only."""

import hashlib
import io
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.utils.validation import check_is_fitted


def save_model(model: LogisticRegression, directory: Path, version: str) -> tuple[Path, str]:
    check_is_fitted(model)
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    content = buffer.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{version}_{digest}.joblib"
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("Existing model artifact has unexpected bytes")
    else:
        with path.open("xb") as stream:
            stream.write(content)
    return path, digest


def load_model(path: Path, expected_sha256: str) -> LogisticRegression:
    """Only for trusted local storage; matching hashes do not make untrusted pickle safe."""
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("Model artifact checksum mismatch")
    model = joblib.load(io.BytesIO(content))
    if not isinstance(model, LogisticRegression):
        raise ValueError("Expected a fitted LogisticRegression artifact")
    check_is_fitted(model)
    return model
