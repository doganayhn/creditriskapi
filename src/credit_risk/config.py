"""Load explicit, validated project configuration without global state."""

from dataclasses import dataclass
import math
from pathlib import Path, PureWindowsPath
from typing import Any

import yaml


@dataclass(frozen=True)
class ProjectPaths:
    """Resolved data and model-artifact directories."""

    raw: Path
    interim: Path
    processed: Path
    artifacts: Path
    metadata: Path


@dataclass(frozen=True)
class SplitConfig:
    """Validated partition fractions; uses the centralized project seed."""

    train_fraction: float
    validation_fraction: float
    test_fraction: float

    def __post_init__(self) -> None:
        fractions = (self.train_fraction, self.validation_fraction, self.test_fraction)
        if any(type(value) not in (int, float) or not math.isfinite(value) or not 0 < value < 1 for value in fractions):
            raise ValueError("Split fractions must be finite numbers strictly between 0 and 1")
        if not math.isclose(sum(fractions), 1.0, rel_tol=0, abs_tol=1e-12):
            raise ValueError("Split fractions must sum to 1.0")


@dataclass(frozen=True)
class ProjectConfig:
    """Validated experiment settings; target may be unset for new experiments."""

    random_seed: int
    experiment_name: str
    target_column: str | None
    paths: ProjectPaths
    split: SplitConfig


class _UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate keys rather than silently replacing settings."""


def _mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str):
            raise ValueError("Configuration keys must be strings")
        if key in result:
            raise ValueError(f"Duplicate configuration key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping
)


def _read(path: Path, keys: set[str]) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = yaml.load(stream, Loader=_UniqueKeyLoader)
    return _check_keys(value, keys, str(path))


def _check_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} must contain exactly: {', '.join(sorted(keys))}")
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a nonempty string without outer whitespace")
    return value


def _resolve_path(root: Path, value: Any, label: str) -> Path:
    relative = _nonempty_string(value, label)
    windows = PureWindowsPath(relative)
    path = Path(relative)
    if path.is_absolute() or windows.drive or windows.root or "\\" in relative:
        raise ValueError(f"{label} must be a portable relative path using forward slashes")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} must remain inside the project root")
    return resolved


def load_config(project_root: str | Path) -> ProjectConfig:
    """Read both YAML files under an explicit root; never create directories.

    Missing files raise FileNotFoundError, invalid YAML raises yaml.YAMLError,
    and invalid configuration values raise ValueError. No environment overrides
    or implicit defaults are applied.
    """
    root = Path(project_root).resolve()
    base = _read(root / "configs/base.yaml", {"random_seed", "paths", "split"})
    experiment = _read(
        root / "configs/experiment.yaml", {"experiment_name", "target_column"}
    )
    seed = base["random_seed"]
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("random_seed must be an integer between 0 and 2**32 - 1")
    name = _nonempty_string(experiment["experiment_name"], "experiment_name")
    target = experiment["target_column"]
    if target is not None:
        target = _nonempty_string(target, "target_column")
    paths = _check_keys(
        base["paths"], {"raw", "interim", "processed", "artifacts", "metadata"}, "paths"
    )
    resolved_paths = ProjectPaths(
        **{key: _resolve_path(root, value, f"paths.{key}") for key, value in paths.items()}
    )
    split = SplitConfig(**_check_keys(
        base["split"], {"train_fraction", "validation_fraction", "test_fraction"}, "split"
    ))
    return ProjectConfig(seed, name, target, resolved_paths, split)
