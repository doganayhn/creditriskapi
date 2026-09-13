# Credit Risk Scoring & Explainability System

A portfolio fintech project intended to estimate borrower default risk from information available at scoring time, explain model outputs and eventually expose auditable predictions through a versioned API.

## Current status
Phases 1–5 are COMPLETED. Implemented scope includes reproducible ingestion/quality, leakage-safe features, Logistic Regression, XGBoost with TRAIN-only fold-safe CV, validation model comparison, class-weight sensitivity and native gain diagnostics. Phases 6–10 remain NOT_STARTED. See the [Phase 5 completion report](docs/phase_reports/phase_05_completion_report.md). Historical Phase 1–4 reports remain unchanged. TEST SET REMAINS SEALED.

## Intended architecture
Public dataset → validation → leakage-safe preprocessing/features → baseline/challenger → calibration when justified → PD → explainability/internal score → versioned policy → API → persistence/audit. Acquisition, quality, financial features, train-only preprocessing, Logistic Regression, XGBoost and validation comparison are implemented. Final TEST evaluation, calibration, SHAP, internal score, production API, PostgreSQL and Docker deployment are not implemented.

## Development
Python 3.11 or newer is required. From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest
```

On POSIX use `.venv/bin/python` for the last two commands. Runtime dependencies: PyYAML, pandas, xlrd (original XLS reader), scikit-learn 1.8.0 and XGBoost 3.2.0. NumPy/SciPy/joblib are used through declared dependencies; HTTP uses the standard library. Development dependency: pytest. Configuration is explicit YAML, not environment-driven; `.env.example` documents this. Configuration loading creates no directories and changes no random generators.

```python
from pathlib import Path
from credit_risk.config import load_config

config = load_config(Path.cwd())  # Explicit repository root
print(config.random_seed, config.paths.raw, config.target_column)
```

`configs/base.yaml` owns the centralized seed, validated 70/15/15 split fractions and relative data/artifact/metadata paths. `configs/experiment.yaml` owns the experiment name and target, now `default_next_month`. Both files are mandatory; unknown/missing keys and invalid values fail explicitly. Paths resolve from the supplied root, independent of the working directory. Configurations remain external to the package; wheel users must supply the configuration directory in their project root.

## Acquire and profile the official dataset

```powershell
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.data.quality
```

Both commands accept `--project-root PATH`; by default the CLI uses the current directory as the root. Download requires HTTPS access to UCI and a filesystem supporting hard links for atomic no-overwrite publication. It reuses a matching file offline and fails on a changed checksum, unexpected workbook schema or invalid target. Do not manually edit the raw XLS. The checksum pins the bytes verified from UCI, not a publisher-signed version. A different official version requires investigation and an explicit update.

The original workbook stays ignored under `data/raw/`. The manifest and quality summary under `data/metadata/` contain only aggregate/schema information and are intended for Git. Profiling does not download anything, change raw values, fit preprocessing or produce a modeled dataset. The automated suite uses mocks and a four-row synthetic XLS fixture, with no live network or real-data dependency.

See the [dataset card](docs/dataset_card.md), [quality report](docs/data_quality_report.md), [physical contract](docs/data_contract.md) and [selection ADR](docs/decisions/001-dataset-selection.md) for attribution, target meaning, observed issues and traceability.

## Prepare modeling data

```powershell
.venv\Scripts\python.exe -m credit_risk.features.prepare
```

The command verifies raw/manifest identity, sorts by customer ID, creates a seeded stratified random 70/15/15 split, engineers 26 financial features and fits preprocessing only on train. ID, target and demographics are excluded from primary predictors; ID/demographics remain separately available for review. Repayment codes stay literal categories, including unresolved -2/0.

Real results: train 21,000 × 103; validation 4,500 × 103; test 4,500 × 103. All matrices are finite. The 103 columns comprise 39 numeric features and 64 train-learned one-hot columns from six categorical fields. This is not an out-of-time split. The test partition is reserved for future final evaluation.

The command writes aggregate split/feature/preprocessing manifests under configured metadata and a trusted local fitted preprocessor under ignored artifacts/preprocessing. It validates serialization on training data. Customer matrices/targets/review frames are available through `prepare_dataset` in memory; none are exported to tracked paths. Repeated execution preserves materially identical metadata and does not rewrite unchanged files. It accepts `--project-root PATH`.

See [feature engineering](docs/feature_engineering.md), [modeling dataset contract](docs/modeling_dataset.md) and [ADR 002](docs/decisions/002-feature-policy-and-split.md).

## Run the fixed baseline

```powershell
.venv\Scripts\python.exe -m credit_risk.modeling.baseline
```

The CLI accepts `--project-root PATH`, verifies the Phase-3 V1 contracts and trusted local preprocessor, fits one L2 LogisticRegression on TRAIN only, and evaluates raw probabilities on TRAIN and VALIDATION only. Version: `logistic-baseline-1.0.0`. Fixed C=1.0, class_weight=None, LBFGS; no tuning or resampling. It does not refit preprocessing or score TEST. A missing artifact requires the documented Phase-3 preparation command; contract disagreements fail instead of being silently repaired.

Validation ROC-AUC: **0.765638**; Average Precision: **0.519684**. Probabilities remain raw/uncalibrated. The reference threshold 0.50 is a diagnostic, not a business policy. Aggregate metrics, validation bootstrap intervals, coefficient lineage and model provenance are written under metadata. The content-addressed model binary stays ignored under artifacts/models. Only trusted project-created joblib files may be loaded; hashes do not make untrusted pickle safe. See the [baseline model report](docs/baseline_model_report.md) and [ADR 003](docs/decisions/003-logistic-baseline.md).

## Run the XGBoost challenger

```powershell
.venv\Scripts\python.exe -m credit_risk.modeling.xgboost_challenger
```

The CLI accepts `--project-root PATH`, verifies the stored baseline and Phase-3 contracts, then searches 24 candidates across four stratified folds inside TRAIN. Every fold fits fresh preprocessing. `configs/xgboost.yaml` is the authoritative search/invariant configuration; the seed remains centralized in base.yaml. There are 96 candidate-fold fits, one search refit, one final canonical fit and one temporary weighted sensitivity fit. CPU hist and n_jobs=1 are used throughout; no early stopping or project-validation fitting occurs.

The final unweighted challenger uses the same 103 transformed values as Logistic Regression. Dense arrays preserve zero semantics for XGBoost. Validation AUC is **0.784304**, AP **0.556212**; paired-bootstrap deltas favor XGBoost on this sample. Status: **XGBOOST_LEADS_ON_VALIDATION_DISCRIMINATION**, a provisional comparison, not final model selection. Raw probabilities remain uncalibrated. The separate weighted model is diagnostic only and is not serialized.

Aggregate search results, metrics, comparison and native gain importance are written under metadata. The native JSON model stays ignored under artifacts/models; no customer outputs are exported. Only trusted XGBoost-generated native models may be loaded. Gain is not SHAP or a customer explanation. See the [XGBoost report](docs/xgboost_model_report.md) and [ADR 004](docs/decisions/004-xgboost-challenger.md).

## Ten-phase plan
1. Foundation and data contract
2. Ingestion and data quality
3. Feature engineering
4. Baseline risk model
5. XGBoost challenger
6. Calibration and thresholds
7. Explainability and internal risk score
8. API and persistence
9. Testing, Docker and operations
10. Final validation and portfolio release

See [ROADMAP.md](ROADMAP.md) for scope/status and [AGENTS.md](AGENTS.md) for instruction precedence. Each phase follows phase prompt → Codex implementation → tests → phase completion report → technical review by the project owner. If issues exist, apply fixes and verify them; if no issues remain, the project owner creates the Git commit. The next phase starts only when explicitly requested. Codex must not automatically commit or start the next phase.

## Repository layout
`src/credit_risk/config.py` handles shared configuration; `data/` contains ingestion and quality code, `features/` handles preparation and `modeling/` implements baseline/challenger training, fold-safe search, contract verification, comparison, metrics and local serialization. Tests use synthetic data and mocks. Aggregate metadata is tracked under `data/metadata/`; raw/interim/processed customer data, local preprocessing/model artifacts, secrets and environments are ignored. Calibration, explainability and serving remain future work.

## Limitations
The selected historical Taiwan credit-card dataset contains 30,000 rows, 25 columns and 6,636 positive next-month labels (22.12%). Undocumented codes and negative bills remain; no regulatory default threshold or event-level scoring dates are supplied. Within-row history is not out-of-time validation. Demographic exclusion does not remove proxies or prove fairness. Related features affect both coefficients and gain; neither is causal. Only TRAIN/CV/VALIDATION performance has been evaluated. The bounded search and paired bootstrap do not establish deployment generalization. Raw probabilities are not calibrated PD. TEST evaluation, calibration, SHAP, scores, API, PostgreSQL, Docker and model operations are not implemented.

This repository is educational / portfolio work, not a regulatory or production lending authority. Outputs are not real lending decisions; no real lending decision should rely on this project.
