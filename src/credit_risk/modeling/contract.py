"""Verified Phase-3 consumer boundary exposing only TRAIN and VALIDATION to modeling."""

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
import scipy
import sklearn

from credit_risk.config import load_config
from credit_risk.data.download import sha256_file
from credit_risk.data.source import TARGET
from credit_risk.features import prepare
from credit_risk.features.definitions import EXCLUDED_FIELDS
from credit_risk.features.engineering import engineer_features, select_primary_features
from credit_risk.features.preprocessing import load_preprocessor, transform_split
from credit_risk.features.split import split_dataset

# Semantic JSON hashes of the committed Phase-3 V1 contracts at 819e449.
# Ignore only generated_at, JSON whitespace and key ordering. Definition changes
# require an explicit new contract review, never automatic repair during training.
PHASE3_IDENTITIES = {
    "split_manifest": "aef0a3fb52c7d62fb12d1ad6a1acabd030a42bb74f720f20fe0fbd2d2d7a60e9",
    "feature_manifest": "412cc60a2166086604ab8989ab20619f6a8583ba7479d9d616d395accd692624",
    "preprocessing_manifest": "3ee9a3d6e787e1e945a1c22888b727f28beb288cf2e55db528c9abad8676384f",
}


def manifest_identity(value: dict) -> str:
    payload = {k: v for k, v in value.items() if k != "generated_at"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass
class ModelingData:
    X_train: sparse.csr_matrix | None
    y_train: np.ndarray | None
    X_validation: sparse.csr_matrix
    y_validation: np.ndarray
    feature_names: tuple[str, ...]
    trace: list[dict]
    split_manifest: dict
    preprocessing_manifest: dict
    dataset_sha256: str


def read_contracts(metadata: Path) -> dict:
    manifests = {}
    for name, expected in PHASE3_IDENTITIES.items():
        try:
            value = json.loads((metadata / f"{name}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"Missing/unreadable Phase-3 {name}") from exc
        if not isinstance(value, dict) or manifest_identity(value) != expected:
            raise ValueError(f"Phase-3 {name} identity disagrees; investigate before training")
        manifests[name] = value
    return manifests


def load_modeling_data(project_root: Path, *, validation_only: bool = False) -> ModelingData:
    root = project_root.resolve()
    config = load_config(root)
    manifests = read_contracts(config.paths.metadata)
    split = manifests["split_manifest"]
    feature = manifests["feature_manifest"]
    preprocessing = manifests["preprocessing_manifest"]
    if config.target_column != TARGET or config.random_seed != split["random_seed"]:
        raise ValueError("Configuration target/seed disagrees with Phase 3")
    if any(split[key] != value for key, value in asdict(config.split).items()):
        raise ValueError("Configuration split fractions disagree with Phase 3")
    versions = {"sklearn": sklearn.__version__, "numpy": np.__version__,
                "pandas": pd.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__}
    if any(preprocessing[f"{name}_version"] != version for name, version in versions.items()):
        raise ValueError("Runtime versions disagree with Phase-3 preprocessing")
    implementation = {p.name: sha256_file(p) for p in sorted(Path(prepare.__file__).parent.glob("*.py"))}
    if implementation != preprocessing["implementation_sha256"]:
        raise ValueError("Feature implementation disagrees with Phase-3 manifest")
    canonical, digest = prepare.verify_dataset_manifest(root)
    if digest != split["dataset_sha256"] or len(canonical) != split["population_rows"]:
        raise ValueError("Dataset identity/population disagrees with Phase 3")
    artifact = (root / preprocessing["serialization_artifact_path"]).resolve()
    if not artifact.is_relative_to(config.paths.artifacts):
        raise ValueError("Preprocessing artifact must remain inside configured artifacts")
    preprocessor = load_preprocessor(artifact, preprocessing["serialization_sha256"])
    names = tuple(preprocessor.get_feature_names_out())
    trace = prepare.transformed_trace(preprocessor)
    if (list(names) != feature["transformed_feature_names"] or
            trace != feature["transformed_feature_trace"] or len(set(names)) != len(names)):
        raise ValueError("Transformed feature names/lineage disagree with Phase 3")
    if any(set(item["canonical_sources"]) & set(EXCLUDED_FIELDS) for item in trace):
        raise ValueError("Forbidden identifier/target/demographic predictor")
    # Reuse the existing split's structural integrity checks. Discard TEST immediately;
    # never engineer, transform, predict or evaluate its rows in Phase-4 modeling.
    partitions = split_dataset(canonical, config.split, config.random_seed)
    if set(partitions) != {"train", "validation", "test"}:
        raise ValueError("Missing expected partitions")
    del partitions["test"]
    if validation_only:
        del partitions["train"]  # Frozen explanation consumers never transform TRAIN.
    matrices, targets = {}, {}
    for name in partitions:
        frame = partitions[name]
        if len(frame) != split[f"{name}_rows"] or int(frame[TARGET].sum()) != split[f"{name}_positive_count"]:
            raise ValueError(f"{name} population disagrees with Phase 3")
        matrix = transform_split(preprocessor, engineer_features(select_primary_features(frame)))
        if list(matrix.shape) != preprocessing["transformed_shapes"][name]:
            raise ValueError(f"{name} transformed shape disagrees with Phase 3")
        matrices[name], targets[name] = matrix, frame[TARGET].to_numpy(dtype=int)
    return ModelingData(matrices.get("train"), targets.get("train"), matrices["validation"],
                        targets["validation"], names, trace, split, preprocessing, digest)
