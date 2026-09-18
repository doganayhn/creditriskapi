# Model Overview

Frozen `xgboost-challenger-1.0.0`, selected in Phase 6; final evaluation `final-test-evaluation-1.0.0`; project release identity `credit-risk-system-1.0.0`. Logistic remains the frozen reference comparator.

# Intended Use

Educational/portfolio credit-risk modeling and a structured PD-like binary classification architecture. Not suitable without additional validation for real lending production, automated credit approval, regulatory capital, IFRS 9, Basel PD or adverse-action generation.

# Target

`default_next_month`: default payment next month, exactly the original workbook target. The available definition does not establish 90+ DPD default, 12-month Basel PD or IFRS-9 lifetime PD.

# Dataset

UCI Default of Credit Card Clients (350), historical Taiwan 2005; 30,000 rows. Pinned dataset SHA-256 `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`. See [dataset card](dataset_card.md) for attribution and source semantics.

# Development Population

Seed 42 stratified random split: TRAIN 21,000, VALIDATION 4,500, TEST 4,500. TRAIN supplied fitting and fold-local search/OOF calibration analysis. VALIDATION supplied development comparison and model selection. TEST stayed predictively sealed through Phase 9 and was opened only for final Phase-10 evaluation. This is not out-of-time validation.

# Features

19 raw financial fields plus 26 engineered features. Frozen TRAIN-fitted median/scaling/one-hot preprocessing maps 45 inputs to 103 features. Versions: `financial_features_v1` and `train_median_scale_onehot_v1`. Repayment codes remain literal; undocumented meanings are not invented.

# Excluded Features

Customer ID, target and demographics (sex, age, education, marital status) are excluded from model input. Demographics remain in a separate aligned review frame for aggregate subgroup diagnostics. Exclusion does not remove possible proxies.

# Modeling Approach

Fixed L2 Logistic baseline (C=1, unweighted) and unweighted XGBoost binary-logistic challenger with TRAIN-only four-fold, 24-candidate search and fresh preprocessing inside each fold. CPU hist, one job. Frozen XGBoost selected on reported VALIDATION discrimination and probability quality in Phase 6. No TEST-based reselection.

# Calibration

TRAIN OOF analysis selected identity for both models. Versions `logistic-calibration-1.0.0` and `xgboost-calibration-1.0.0`. Raw probability equals reported probability exactly. No calibrator binary or TEST recalibration. TEST ECE uses Phase-6 quantile-bin semantics; Logistic has lower TEST ECE than XGBoost.

# Internal Score

`internal-risk-score-1.0.0`: base score 600 at good:bad odds 50:1, PDO 20, epsilon 1e-12. Higher score means lower modeled default risk. Continuous canonical score; display rounding is separate. Not FICO, risk bands or a lending decision.

# Explainability

`xgboost-shap-1.0.0`: exact path-dependent Tree SHAP in raw-margin units. Signed source/family aggregation and diagnostic local drivers. Under identity calibration, affine score points are checked independently. SHAP is noncausal and not additive probability or certified adverse action. Global importance remains VALIDATION-based; only aggregate residuals from 32 predeclared TEST rows are published.

# Final TEST Performance

| Metric | Logistic TEST | XGBoost TEST |
| --- | --- | --- |
| average_precision | 0.52981208 | 0.55493342 |
| brier_score | 0.13815888 | 0.13517626 |
| ece | 0.013705673 | 0.018104312 |
| gini | 0.5206425 | 0.56029254 |
| ks | 0.40494512 | 0.43652693 |
| log_loss | 0.44034703 | 0.43003453 |
| mean_predicted_probability | 0.22051946 | 0.22103783 |
| observed_positive_rate | 0.22133333 | 0.22133333 |
| roc_auc | 0.76032125 | 0.78014627 |

XGBoost 95% bootstrap AUC CI: [0.7627072303638124, 0.79666808856661]. One thousand row-bootstrap replicates, seed 42, no skipped single-class replicate. See [final evaluation](final_evaluation_report.md) for paired intervals, reliability, frozen threshold, score deciles and lift.

| Metric | VALIDATION | TEST | TEST minus VALIDATION |
| --- | --- | --- | --- |
| roc_auc | 0.7843044 | 0.78014627 | -0.0041581336 |
| average_precision | 0.55621193 | 0.55493342 | -0.0012785098 |
| brier_score | 0.13528487 | 0.13517626 | -0.00010861231 |
| log_loss | 0.42882662 | 0.43003453 | 0.0012079071 |
| ece | 0.011402129 | 0.018104312 | 0.0067021838 |

Observed differences are small on this sample and consistent with similar generalization behavior, subject to sampling uncertainty. They do not prove absence of development overfitting.

# Subgroup Diagnostics

Aligned sex, individual age, education and marital-status raw values; n≥100 required for metrics. Smaller groups report insufficient sample; single-class AUC is undefined. [Aggregate diagnostics](subgroup_diagnostics.md) are descriptive, not a fairness score, causal analysis or legal/regulatory assessment.

# API / Deployment

FastAPI `/v1`, service `credit-risk-api-1.0.0`; PostgreSQL 17 and Alembic `phase8_001`; API-key auth, process-local rate limiting, fail-closed audit writes. Local Docker Compose runs one non-root worker, separate migration and read-only artifacts. No raw dataset mounts or training fallback. See [deployment](deployment.md).

# Monitoring

`model-operations-1.0.0` checks audit contracts and output aggregates. `output-monitoring-baseline-1.0.0` is frozen VALIDATION-only. Descriptive score PSI never triggers retraining or policy. No feature drift or realized-performance monitoring.

# Privacy

Final TEST artifacts contain aggregates only. No row-level TEST probability, score, labels, IDs, feature matrix or SHAP is persisted. API audit excludes raw financial inputs, demographics, secrets and full feature/SHAP vectors. Retained outputs still require access/retention controls.

# Known Limitations

Historical static population, uncertain generalization, undocumented codes, no bureau/affordability/reject inference/LGD/EAD, no expected-loss engine, no modern OOT validation and no production/regulatory claim. See [limitations](limitations.md).

# Governance / Versioning

Dataset, features, preprocessing, models, calibration, explanation, score, service/API, database, operations and final release retain separate identities. [Pre-unseal snapshot](../data/metadata/final_pre_unseal_snapshot.json) freezes exact hashes. Historical reports and manifests remain unchanged. Final publication fails closed on identity/result differences; reproduction preserves timestamps. TEST results did not feed back into development.

# Reproducibility

Use the trusted existing local model/preprocessor artifacts with the pinned compatible numerical environment. Run `python -m credit_risk.evaluation.final --verify-existing`; it never fits anything. Missing artifacts must be supplied, not retrained as part of final verification. Historical development commands are documented separately. The ordinary real-artifact test skips explicitly when prerequisites are absent.

# Ethical / Responsible Use Notes

Educational system only; no real lending decision should rely on it. Demographic associations are noncausal, and removing demographics is not fairness certification. Any modern deployment needs independent context-specific evaluation, privacy controls and jurisdiction-specific governance. No repository license has been chosen.
