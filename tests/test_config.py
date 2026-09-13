"""Dataset-independent tests for the Phase-1 public configuration behavior."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import random

import pytest
import yaml

import credit_risk
from credit_risk.config import load_config


@pytest.fixture
def project(tmp_path):
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "base.yaml").write_text(
        "random_seed: 42\npaths:\n  raw: data/raw\n  interim: data/interim\n"
        "  processed: data/processed\n  artifacts: artifacts\n  metadata: data/metadata\n", encoding="utf-8"
    )
    (configs / "experiment.yaml").write_text(
        "experiment_name: foundation\ntarget_column: null\n", encoding="utf-8"
    )
    return tmp_path


def replace(project, filename, old, new):
    path = project / "configs" / filename
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


def test_package_import():
    assert credit_risk.__name__ == "credit_risk"


def test_repository_configuration():
    root = Path(__file__).resolve().parents[1]
    config = load_config(root)
    assert config.random_seed == 42
    assert config.experiment_name == "foundation"
    assert config.target_column == "default_next_month"
    assert config.paths.artifacts == root / "artifacts"


def test_paths_independent_of_cwd(project, monkeypatch, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    config = load_config(project)
    assert config.paths.raw == project / "data/raw"
    assert config.paths.interim == project / "data/interim"
    assert config.paths.processed == project / "data/processed"
    assert config.paths.artifacts == project / "artifacts"
    assert config.paths.metadata == project / "data/metadata"
    assert not (project / "data").exists()
    assert not config.paths.artifacts.exists()


def test_explicit_values_and_no_random_side_effect(project):
    replace(project, "base.yaml", "42", "123")
    replace(project, "experiment.yaml", "foundation", "review")
    replace(project, "experiment.yaml", "null", "outcome")
    before = random.getstate()
    config = load_config(project)
    assert (config.random_seed, config.experiment_name, config.target_column) == (123, "review", "outcome")
    assert random.getstate() == before
    assert load_config(project) == config
    with pytest.raises(FrozenInstanceError):
        config.random_seed = 7


@pytest.mark.parametrize("seed", ["true", "-1", "4294967296", "1.5", "null", "'42'"])
def test_invalid_seed(project, seed):
    replace(project, "base.yaml", "42", seed)
    with pytest.raises(ValueError, match="random_seed"):
        load_config(project)


@pytest.mark.parametrize("path", ["/outside", "C:/outside", "C:outside", "../outside", "data/../../outside", "'data\\raw'", "''", "null", "7"])
def test_invalid_paths(project, path):
    replace(project, "base.yaml", "data/raw", path)
    with pytest.raises(ValueError, match="paths.raw"):
        load_config(project)


@pytest.mark.parametrize("field,value", [("experiment_name", "null"), ("experiment_name", "''"), ("target_column", "42"), ("target_column", "' '")])
def test_invalid_experiment(project, field, value):
    old = "foundation" if field == "experiment_name" else "null"
    replace(project, "experiment.yaml", old, value)
    with pytest.raises(ValueError, match=field):
        load_config(project)


@pytest.mark.parametrize("filename", ["base.yaml", "experiment.yaml"])
def test_missing_file(project, filename):
    (project / "configs" / filename).unlink()
    with pytest.raises(FileNotFoundError):
        load_config(project)


@pytest.mark.parametrize("content", ["", "[]", "random_seed: 42", "random_seed: 42\nextra: 1\npaths: {}", "random_seed: 42\npaths: []", "random_seed: 42\npaths: {}", "random_seed: 42\nrandom_seed: 7\npaths: {}"])
def test_invalid_structure(project, content):
    (project / "configs/base.yaml").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(project)


def test_malformed_yaml(project):
    (project / "configs/base.yaml").write_text("paths: [", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        load_config(project)


def test_unsafe_yaml_tag(project):
    (project / "configs/base.yaml").write_text("!!python/object:builtins.object {}", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        load_config(project)
