# Credit Risk Scoring & Explainability System

A portfolio fintech project intended to estimate borrower default risk from information available at scoring time, explain model outputs and eventually expose auditable predictions through a versioned API.

## Current status
Phases 1–7 are COMPLETED. Implemented scope includes reproducible ingestion/quality, leakage-safe features, Logistic Regression, XGBoost, TRAIN-only OOF calibration assessment, frozen validation comparison, TRAIN-derived technical thresholds, raw-margin Tree SHAP, aggregate global explanations, diagnostic local drivers and a project-specific internal risk score. Phases 8–10 remain NOT_STARTED. See the [Phase 7 completion report](docs/phase_reports/phase_07_completion_report.md). Historical Phase 1–6 reports remain unchanged. TEST SET REMAINS SEALED.

## Intended architecture
Public dataset → validation → leakage-safe preprocessing/features → baseline/challenger → TRAIN OOF calibration selection → versioned mapping → reported default probability → validation model comparison → TRAIN-derived technical threshold analysis. These steps are implemented. The frozen XGBoost model now supplies raw-margin SHAP and reported-probability internal scores. Versioned policy, production API, PostgreSQL persistence/audit, authentication, Docker, monitoring, final TEST evaluation and regulatory validation remain unimplemented.

## Development
Python 3.11 or newer is required. From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest
```

On POSIX use `.venv/bin/python` for the last two commands. Runtime dependencies: PyYAML, pandas, xlrd (original XLS reader), scikit-learn 1.8.0, XGBoost 3.2.0 and SHAP 0.51.0. NumPy/SciPy/joblib are used through declared dependencies; HTTP uses the standard library. Development dependency: pytest. Configuration is explicit YAML, not environment-driven; `.env.example` documents this. Configuration loading creates no directories and changes no random generators.

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

The original workbook stays ignored under `data/raw/`. The manifest and quality summary under `data/metadata/` contain only aggregate/schema information and are intended for Git. Profiling does not download anything, change raw values, fit preprocessing or produce a modeled dataset. Offline tests use mocks and a four-row synthetic XLS fixture with no live network. An additional Phase-7 integration test checks the frozen real model on VALIDATION when trusted ignored data/model/preprocessor artifacts are present; otherwise that test explicitly skips.

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

## Run calibration and technical threshold analysis

```powershell
.venv\Scripts\python.exe -m credit_risk.modeling.calibration
```

The CLI verifies both fixed model artifacts and the shared data contract. Five stratified TRAIN folds generate exactly one OOF raw probability per row and model, with fresh preprocessing in each fold. A second five-fold TRAIN-only CV compares identity, nonnegative-slope sigmoid and monotonic isotonic mappings. Minimum mean Brier selects the method; log loss then simplicity break ties within 1e-12. Both final mappings are frozen before canonical VALIDATION scoring. Settings are in `configs/calibration.yaml`; the seed remains 42 in base.yaml. This command performs no model hyperparameter search.

**Identity was selected for both models**, so reported_probability equals raw_probability. This is an assessed passthrough decision, not proof of perfect calibration or regulatory PD. XGBoost is selected for downstream development because reported validation AUC/AP are no lower and Brier/log loss no higher, with strict improvements. This does not establish untouched-test performance or production readiness.

The XGBoost TRAIN OOF max-KS threshold is **0.21430689096450806**, evaluated unchanged on VALIDATION alongside reference 0.50. It is a technical classification diagnostic, not a lending cut-off. Aggregate manifests, metrics, ten-bin reliability, paired bootstrap and TRAIN threshold tables are saved under metadata. Identity decisions are versioned metadata with null binary paths; non-identity serialization is implemented and tested under ignored artifacts/calibration. No customer probabilities are exported. See the [calibration report](docs/calibration_report.md) and [ADR 005](docs/decisions/005-calibration-and-model-selection.md).

## Explain the frozen model and map internal scores

```powershell
.venv\Scripts\python.exe -m credit_risk.explainability.run
```

This CLI accepts `--project-root PATH`. It verifies frozen data, feature/preprocessor, XGBoost and identity-calibration contracts, then explains all 4,500 VALIDATION rows across the same 103 features. It never retrains a model, refits preprocessing or consumes TRAIN/TEST for prediction. The required preparation command separately performs its existing structural split checks.

SHAP 0.51.0 TreeExplainer uses explicit `raw` output and `tree_path_dependent` perturbation with frozen training path counts. Signed local contributions are summed to 45 source features and seven families before global mean absolute importance. Local source-level top-five drivers are deterministic diagnostics, not causal or regulatory adverse-action reasons. No customer explanations, scores or reason codes are persisted, and no explainer binary is created.

The continuous `internal-risk-score-1.0.0` uses reported probability, base score 600, good:bad odds 50 and PDO 20; higher predicted risk lowers score. It is not FICO, a regulatory score or a lending decision policy. Exact additive score points are supported only for binary logistic raw-margin SHAP with identity calibration and no numerical clipping. The frozen TRAIN OOF threshold maps to technical reference score 524.608630; it is not a business cutoff. Score deciles are validation diagnostics, not risk bands.

TRAIN OOF score statistics are unavailable because row-level OOF probabilities were not retained in Phase 6. The owner explicitly required no retraining; no in-sample TRAIN scores replace them. Five deterministic aggregate metadata files record the actual validation results. See [explainability](docs/explainability_report.md), [internal score](docs/internal_risk_score.md) and [ADR 006](docs/decisions/006-explainability-and-internal-score.md). Existing model/calibration CLIs above reproduce historical experiments and are not prerequisites for this frozen Phase-7 workflow.

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
`src/credit_risk/config.py` handles shared configuration; `data/` contains ingestion and quality code, `features/` handles preparation and `modeling/` implements training, fold-safe search, contract verification, calibration, comparison, reliability, technical thresholds and local serialization. Tests use synthetic data and mocks. Aggregate metadata is intended for tracking under `data/metadata/`; customer data, local preprocessing/model/calibrator artifacts, secrets and environments are ignored. `explainability/` implements frozen-contract checks, public Tree SHAP, signed aggregation, diagnostic local drivers, the score mapping and aggregate publication. Serving remains future work.

## Limitations
The selected historical Taiwan credit-card dataset contains 30,000 rows, 25 columns and 6,636 positive next-month labels (22.12%). Undocumented codes and negative bills remain; no regulatory default threshold or event-level scoring dates are supplied. Within-row history is not out-of-time validation. Demographic exclusion does not remove proxies or prove fairness. Related features affect both coefficients and gain; neither is causal. Only TRAIN/CV/VALIDATION performance has been evaluated. The bounded search, calibration selection and paired bootstrap do not establish deployment generalization. Identity selection does not turn raw probability into regulatory PD. VALIDATION is a reused development set; TEST remains reserved. SHAP remains noncausal and correlated-feature attribution depends on the declared perturbation semantics. The internal score is a monotonic representation, not another predictive model. TEST evaluation, API, PostgreSQL, Docker and model operations are not implemented.

This repository is educational / portfolio work, not a regulatory or production lending authority. Outputs are not real lending decisions; no real lending decision should rely on this project.
