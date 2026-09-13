"""Phase-3 split, domain formulas, isolation and integration tests using synthetic data."""

import json
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from credit_risk.config import SplitConfig, load_config
from credit_risk.data.schema import DataSchemaError
from credit_risk.data.source import EXPECTED_SHA256, RAW_FILENAME, TARGET
from credit_risk.features.definitions import (
    BILL_COLUMNS, CATEGORICAL_FEATURES, ENGINEERED_FEATURES, EXCLUDED_FIELDS,
    FAIRNESS_REVIEW_FIELDS, MODEL_INPUT_FEATURES, NUMERIC_FEATURES, PAYMENT_COLUMNS,
    PRIMARY_MODEL_FEATURES, REPAYMENT_COLUMNS,
)
from credit_risk.features.engineering import engineer_features, select_primary_features
from credit_risk.features import prepare
from credit_risk.features.preprocessing import (
    build_preprocessor, fit_preprocessor, load_preprocessor, save_preprocessor, transform_split,
)
from credit_risk.features.split import split_dataset


@pytest.fixture
def population(canonical_frame):
    rows = pd.concat([canonical_frame.iloc[[0]]] * 200, ignore_index=True)
    rows["customer_id"] = pd.Series(range(1, 201), dtype="Int64")
    rows[TARGET] = (rows["customer_id"] % 5 == 0).astype("Int64")
    rows["credit_limit"] = rows["customer_id"] * 100
    for i, name in enumerate(BILL_COLUMNS):
        rows[name] = rows["customer_id"] * (i - 2)
    for i, name in enumerate(PAYMENT_COLUMNS):
        rows[name] = rows["customer_id"] * (i + 1)
    for i, name in enumerate(REPAYMENT_COLUMNS):
        rows[name] = (rows["customer_id"] + i) % 6 - 2
    return rows


@pytest.fixture
def split_config():
    return load_config(Path(__file__).resolve().parents[1]).split


@pytest.fixture
def seed():
    return load_config(Path(__file__).resolve().parents[1]).random_seed


def engineered(frame):
    return engineer_features(select_primary_features(frame))


def test_split_integrity_and_determinism(population, split_config, seed):
    before = population.copy(deep=True)
    first = split_dataset(population, split_config, seed)
    second = split_dataset(population.iloc[::-1], split_config, seed)
    assert [len(frame) for frame in first.values()] == [140, 30, 30]
    ids = [set(frame.customer_id) for frame in first.values()]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
    assert set.union(*ids) == set(population.customer_id)
    for name in first:
        pd.testing.assert_frame_equal(first[name], second[name])
        assert first[name][TARGET].mean() == .2
    changed = split_dataset(population, split_config, seed + 1)
    assert set(first["train"].customer_id) != set(changed["train"].customer_id)
    pd.testing.assert_frame_equal(before, population)


@pytest.mark.parametrize("values", [(0,.5,.5), (-.1,.6,.5), (.7,.2,.2), (True,.15,.15), (float('nan'),.15,.15), (float('inf'),.15,.15), (1,0,0), ('0.7',.15,.15)])
def test_invalid_fractions(values):
    with pytest.raises(ValueError):
        SplitConfig(*values)


def test_config_split_is_loaded_and_validated(data_project):
    assert load_config(data_project).split == SplitConfig(.7,.15,.15)
    path = data_project / "configs/base.yaml"
    path.write_text(path.read_text().replace("train_fraction: 0.70", "train_fraction: 0.60"))
    with pytest.raises(ValueError, match="sum"):
        load_config(data_project)


@pytest.mark.parametrize("defect", ["duplicate_id", "null_id", "single_class", "null_target"])
def test_invalid_split_population(population, split_config, seed, defect):
    if defect == "duplicate_id":
        population.loc[1, "customer_id"] = population.loc[0, "customer_id"]
    elif defect == "null_id":
        population.loc[1, "customer_id"] = pd.NA
    elif defect == "single_class":
        population[TARGET] = 0
    else:
        population.loc[0, TARGET] = pd.NA
    with pytest.raises(DataSchemaError):
        split_dataset(population, split_config, seed)


def test_small_population_fails(canonical_frame, split_config, seed):
    with pytest.raises(DataSchemaError):
        split_dataset(canonical_frame, split_config, seed)


def test_definitions_have_disjoint_roles():
    assert len(PRIMARY_MODEL_FEATURES) == 19
    assert len(ENGINEERED_FEATURES) == 26
    assert len(NUMERIC_FEATURES) == 39 and len(CATEGORICAL_FEATURES) == 6
    assert len(MODEL_INPUT_FEATURES) == len(set(MODEL_INPUT_FEATURES)) == 45
    assert not set(EXCLUDED_FIELDS) & set(MODEL_INPUT_FEATURES)
    assert not set(NUMERIC_FEATURES) & set(CATEGORICAL_FEATURES)


def test_financial_formulas_and_no_mutation(population):
    frame = population.iloc[[0]].copy()
    frame.loc[:, "credit_limit"] = 10
    frame.loc[:, list(BILL_COLUMNS)] = [-10, 0, 10, 20, 30, 40]
    frame.loc[:, list(PAYMENT_COLUMNS)] = [0, 10, 20, 30, 40, 50]
    frame.loc[:, list(REPAYMENT_COLUMNS)] = [2, -2, -1, 0, 3, 1]
    before = frame.copy(deep=True)
    result = engineered(frame).iloc[0]
    assert result.bill_amount_mean == 15
    assert result.bill_amount_std == pytest.approx(np.std([-10,0,10,20,30,40], ddof=0))
    assert result.bill_amount_min == -10 and result.bill_amount_max == 40
    assert result.payment_amount_mean == 25 and result.payment_amount_sum == 150
    assert result.payment_amount_max == 50
    assert result.bill_to_limit_2005_09 == -1 and result.bill_to_limit_2005_04 == 4
    assert result.bill_to_limit_mean == 1.5 and result.bill_to_limit_max == 4
    assert result.payment_to_limit_2005_04 == 5
    assert result.payment_to_limit_mean == 2.5 and result.payment_to_limit_max == 5
    assert result.months_with_documented_delay == 3
    assert result.max_documented_delay == 3 and result.recent_documented_delay_flag == 1
    assert result.repayment_status_2005_08 == "status_-2"
    assert result.repayment_status_2005_07 == "status_-1"
    assert result.repayment_status_2005_06 == "status_0"
    pd.testing.assert_frame_equal(frame, before)


def test_no_positive_delays_and_target_independence(population):
    population.loc[:, list(REPAYMENT_COLUMNS)] = [-2, -1, 0, -2, -1, 0]
    first = engineered(population)
    assert (first[["months_with_documented_delay", "max_documented_delay", "recent_documented_delay_flag"]] == 0).all().all()
    population[TARGET] = 1 - population[TARGET]
    population["age"] = 150
    pd.testing.assert_frame_equal(first, engineered(population))


@pytest.mark.parametrize("limit", [0,-1,None])
def test_invalid_credit_limit(population, limit):
    population.loc[0,"credit_limit"] = limit
    with pytest.raises(DataSchemaError, match="credit_limit"):
        engineered(population)


def test_missing_values_propagate_conservatively(population):
    population.loc[0,BILL_COLUMNS[0]] = pd.NA
    population.loc[0,PAYMENT_COLUMNS[0]] = pd.NA
    population.loc[0,REPAYMENT_COLUMNS[1]] = pd.NA
    result = engineered(population)
    assert pd.isna(result.loc[0,"bill_amount_mean"])
    assert pd.isna(result.loc[0,"payment_amount_sum"])
    assert pd.isna(result.loc[0,"months_with_documented_delay"])
    assert pd.isna(result.loc[0,"max_documented_delay"])
    assert pd.notna(result.loc[0,"recent_documented_delay_flag"])
    fitted = fit_preprocessor(result)
    assert np.isfinite(transform_split(fitted,result).data).all()


@pytest.mark.parametrize("defect", ["target", "missing", "non_numeric", "infinite", "invalid_status"])
def test_feature_input_contract(population, defect):
    frame = select_primary_features(population)
    if defect == "target": frame[TARGET] = 0
    elif defect == "missing": frame = frame.drop(columns=BILL_COLUMNS[0])
    elif defect == "non_numeric": frame[BILL_COLUMNS[0]] = "10"
    elif defect == "infinite": frame[BILL_COLUMNS[0]] = float('inf')
    else: frame[REPAYMENT_COLUMNS[0]] = 99
    with pytest.raises(DataSchemaError):
        engineer_features(frame)


def test_train_only_statistics_and_unknown_categories(population):
    train = engineered(population.iloc[:100])
    train.loc[0,"credit_limit"] = np.nan
    held = population.iloc[100:].copy()
    held.loc[:,"credit_limit"] = 1_000_000_000
    held.loc[:, list(REPAYMENT_COLUMNS)] = 9  # Documented, absent from synthetic training.
    validation = engineered(held.iloc[:50])
    test = engineered(held.iloc[50:])
    fitted = fit_preprocessor(train)
    numeric = fitted.named_steps["columns"].named_transformers_["numeric"]
    expected = train[list(NUMERIC_FEATURES)].median().to_numpy()
    np.testing.assert_allclose(numeric.named_steps["imputer"].statistics_, expected)
    means = train[list(NUMERIC_FEATURES)].fillna(train[list(NUMERIC_FEATURES)].median()).mean().to_numpy()
    np.testing.assert_allclose(numeric.named_steps["scaler"].mean_, means)
    assert means[0] != pd.concat([train, validation, test]).credit_limit.mean()
    encoder = fitted.named_steps["columns"].named_transformers_["repayment"].named_steps["encoder"]
    assert all("status_9" not in vocabulary for vocabulary in encoder.categories_)
    before = numeric.named_steps["scaler"].mean_.copy()
    names = fitted.get_feature_names_out()
    for holdout in (validation,test):
        matrix = transform_split(fitted, holdout)
        assert matrix[:,len(NUMERIC_FEATURES):].nnz == 0
        assert np.isfinite(matrix.data).all()
        assert matrix.shape[1] == len(names) == len(set(names))
    np.testing.assert_array_equal(before,numeric.named_steps["scaler"].mean_)
    assert not any(TARGET in name for name in names)


@pytest.mark.parametrize("excluded", EXCLUDED_FIELDS)
def test_preprocessor_rejects_forbidden_fields(population, excluded):
    features = engineered(population)
    features[excluded] = 0
    with pytest.raises(DataSchemaError):
        fit_preprocessor(features)


def test_preprocessor_rejects_target_argument_and_all_null_column(population):
    features = engineered(population)
    with pytest.raises(DataSchemaError, match="target"):
        build_preprocessor().fit(features, population[TARGET])
    features["bill_amount_mean"] = np.nan
    with pytest.raises(DataSchemaError, match="No training median"):
        fit_preprocessor(features)


def test_serialization_and_names(population, tmp_path):
    features = engineered(population)
    fitted = fit_preprocessor(features)
    path, digest = save_preprocessor(fitted,tmp_path)
    loaded = load_preprocessor(path,digest)
    a,b = transform_split(fitted,features),transform_split(loaded,features)
    assert (a != b).nnz == 0
    names = fitted.get_feature_names_out()
    np.testing.assert_array_equal(names,loaded.get_feature_names_out())
    np.testing.assert_array_equal(names,fit_preprocessor(features).get_feature_names_out())
    assert [r["name"] for r in prepare.transformed_trace(fitted)] == list(names)
    path.write_bytes(b'corrupt artifact')
    with pytest.raises(DataSchemaError, match="checksum"):
        load_preprocessor(path,digest)


def test_orchestration_fits_only_train_and_retains_review(population, split_config, seed, monkeypatch):
    train = split_dataset(population,split_config,seed)["train"]
    actual_fit = prepare.fit_preprocessor
    observed = []
    def spy(frame):
        pd.testing.assert_frame_equal(frame,engineered(train))
        observed.append(len(frame))
        return actual_fit(frame)
    monkeypatch.setattr(prepare,"fit_preprocessor",spy)
    result = prepare.prepare_dataset(population,split_config,seed)
    assert observed == [140]
    for part in result.partitions.values():
        assert list(part.review.columns) == ["customer_id",*FAIRNESS_REVIEW_FIELDS]
        assert part.y.name == TARGET and part.y.index.equals(part.review.index)
        assert part.X.shape[0] == len(part.review)
        assert np.isfinite(part.X.data).all()


def test_changing_holdouts_cannot_change_fitted_state(population, split_config, seed):
    initial = prepare.prepare_dataset(population,split_config,seed)
    train_ids = set(initial.partitions['train'].review.customer_id)
    changed = population.copy()
    mask = ~changed.customer_id.isin(train_ids)
    changed.loc[mask,'credit_limit'] = 1_000_000_000
    changed.loc[mask,list(REPAYMENT_COLUMNS)] = 9
    rerun = prepare.prepare_dataset(changed,split_config,seed)
    assert (initial.partitions['train'].X != rerun.partitions['train'].X).nnz == 0
    assert initial.feature_names == rerun.feature_names


def test_hash_failure_precedes_loading(data_project, monkeypatch):
    path = data_project/'data/raw'/RAW_FILENAME
    path.parent.mkdir(parents=True)
    path.write_bytes(b'changed raw')
    loader = Mock()
    monkeypatch.setattr(prepare,'load_source',loader)
    with pytest.raises(RuntimeError,match='mismatch'):
        prepare.run_preparation(data_project)
    loader.assert_not_called()


@pytest.fixture
def prepared_project(data_project, population, monkeypatch):
    path = data_project/'data/raw'/RAW_FILENAME
    path.parent.mkdir(parents=True)
    path.write_bytes(b'synthetic test only')
    repo = Path(__file__).resolve().parents[1]
    manifest = json.loads((repo/'data/metadata/dataset_manifest.json').read_text())
    manifest.update(row_count=len(population),file_size_bytes=path.stat().st_size)
    metadata = data_project/'data/metadata'
    metadata.mkdir()
    (metadata/'dataset_manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(prepare,'verify_raw',lambda path: EXPECTED_SHA256)
    monkeypatch.setattr(prepare,'load_source',lambda path: population.copy())
    return data_project


def test_manifest_mismatch_rejected(prepared_project):
    path = prepared_project/'data/metadata/dataset_manifest.json'
    manifest = json.loads(path.read_text())
    manifest['sha256'] = 'wrong'
    path.write_text(json.dumps(manifest))
    with pytest.raises(DataSchemaError,match='manifest identity'):
        prepare.run_preparation(prepared_project)


def test_full_synthetic_pipeline_and_metadata_idempotence(prepared_project, monkeypatch, tmp_path):
    other = tmp_path/'elsewhere'
    other.mkdir()
    monkeypatch.chdir(other)
    first = prepare.run_preparation(prepared_project)
    paths = [prepared_project/'data/metadata'/f'{name}_manifest.json' for name in ('split','feature','preprocessing')]
    before = [(path.read_bytes(),path.stat().st_mtime_ns) for path in paths]
    assert prepare.run_preparation(prepared_project) == first
    assert [(path.read_bytes(),path.stat().st_mtime_ns) for path in paths] == before
    assert first['splits']['train']['rows'] == 140
    assert first['raw_features'] == 19 and first['engineered_features'] == 26
    assert first['serialization_roundtrip_passed']
    assert not (other/'data').exists()
    for path in paths:
        manifest = json.loads(path.read_text())
        assert 'customer_ids' not in manifest and 'rows_data' not in manifest
