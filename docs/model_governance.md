# Model governance

Implemented Phase-4–8 model, calibration, explanation, internal-score and API audit controls are identified below. Business-policy and deployment controls remain requirements for future phases.

## Model versioning
Every deployed/serialized model must have an explicit version or immutable artifact identity; link preprocessing, feature schema and any calibrator to it.

Historical Phase-4/5 experiment records retain their original source provenance, timestamps and search timings when reproduced unchanged. New experiments hash explicit model-specific module lists rather than the entire modeling directory. Publication checks the experiment identity, artifact, predictive outputs and non-timing CV results before any metadata write. A mismatch fails without replacing historical records and requires an explicit new experiment record; source-only changes cannot rewrite the original experiment's provenance.

## Dataset traceability
Identify source/version/checksum, preparation configuration, feature set, seed, split membership and exclusions for each training experiment.

## Calibration governance
Evaluate calibration on held-out data using probability-quality metrics and reliability analysis. Do not assume a calibrator helps; keep fit/selection separate from final testing. Record calibrator identity or explicitly state none.

## Explanation governance
SHAP semantics and units must match the explained model output. Underlying-model SHAP does not automatically sum to calibrated PD. Disclose direction/ranking semantics and validate explanations; do not imply causality.

## Threshold governance
Do not select thresholds solely because 0.50 is conventional. Document objective, trade-offs, selection partition and performance uncertainty. Test data do not select thresholds.

## Business rules
Operational recommendation rules must be independently versioned from the model, with documented assumptions and ownership. No rules are implemented yet.

## Evaluation reproducibility
Compare models on the same eligible population and comparable splits, recording metrics, configurations, runtime/dependency versions and artifact identity. Record nondeterminism. Assess sensitive attributes and proxies explicitly; this is not a fairness certification.

## Portfolio disclaimer
This system is not a regulatory or production lending authority. No real lending decision should rely on this repository. Phase 8 adds API authentication, request safeguards and audit-minimization controls; deployment security, retention operations, monitoring and broader operational validation remain future work.

## Verified V1 data boundary
UCI 350 is selected under [ADR 001](decisions/001-dataset-selection.md). Experiments must identify the XLS checksum in the dataset manifest and the canonical schema. The label is next-month default payment, not a regulatory or 12-month PD. No event-level scoring dates or multiple calendar scoring cohorts exist in the verified workbook; the Phase-3 stratified random split is not out-of-time validation. Income/employment are absent. [ADR 002](decisions/002-feature-policy-and-split.md) excludes demographics from primary predictors while retaining separate review frames and preserves literal categorical repayment codes without assigning undocumented meanings.

Phase 3 fits preprocessing only, on 21,000 training rows. Manifests record split/feature/preprocessing versions, fitted row count, runtime versions and encoded lineage; a content-addressed local artifact has a verified serialization round-trip. The test set remains reserved for final evaluation. Future tuning/cross-validation must fit preprocessing inside each training fold and use consistent partitions across baseline/challenger comparisons.

## Implemented Phase-4 baseline

`logistic-baseline-1.0.0` uses fixed L2 LogisticRegression, C=1.0 and class_weight=None. TRAIN alone fits the model; the Phase-3 preprocessor is loaded without refitting. The model manifest links raw dataset SHA-256, split/feature/preprocessing identity, code/configuration/runtime versions, convergence and local artifact hash. Only trusted project-created joblib files may be loaded; a checksum cannot make arbitrary pickle safe. No customer predictions are exported.

TRAIN diagnostics and VALIDATION assessment include ROC-AUC, Average Precision, KS, Gini, Brier/log loss, mean probability, prevalence and fixed 0.50 reference-threshold metrics. VALIDATION bootstrap intervals do not alter the model. Threshold 0.50 is not optimized and has no lending-policy meaning. TEST probabilities, predictions and predictive metrics are prohibited in Phase 4; test_set_evaluated=false is recorded. TEST SET REMAINS SEALED.

Phase-4 outputs are raw model probabilities of next-month default payment. Phase 6 separately records the calibration assessment below. Future prediction metadata must identify model version, feature/preprocessing identity and raw_probability semantics; no API/persistence implementation exists yet. Comparisons use the same validation population without opening TEST. Coefficients are conditional, L2-shrunk and noncausal, with standardized-numeric and full-one-hot caveats in the [baseline report](baseline_model_report.md).

## Implemented Phase-5 challenger and provisional comparison

`xgboost-challenger-1.0.0` uses XGBoost 3.2.0, CPU hist, binary:logistic, n_jobs=1 and canonical scale_pos_weight=1.0. Search is limited to 24 candidates × four stratified TRAIN folds, with fold-local preprocessing and deterministic AUC/AP/simplicity tie rules. Project VALIDATION is not used for training, tuning or early stopping. Final fitting uses full TRAIN and the verified Phase-3 representation.

Stored baseline metadata and the trusted baseline artifact must agree with the current data/split/feature/preprocessor contract. Reproduced in-memory probabilities must reproduce stored metrics. Comparisons use the same VALIDATION population; paired bootstrap applies identical row indices to both models. `XGBOOST_LEADS_ON_VALIDATION_DISCRIMINATION` is the measured Phase-5 provisional status. Its historical final_model_selected=false remains unchanged; Phase 6 records a separate downstream development selection below.

## Implemented Phase-6 calibration governance

Both fixed candidates generate TRAIN-only five-fold OOF probabilities with fresh fold preprocessing. Another five-fold TRAIN-only CV selects minimum mean Brier, then log loss within 1e-12, then identity/sigmoid/isotonic simplicity. ECE is a ten-quantile-bin diagnostic, not the optimization objective. Both selected methods are identity, recorded as logistic-calibration-1.0.0 and xgboost-calibration-1.0.0 with null binary artifact paths/hashes. Reported probability therefore equals raw probability; no perfect-calibration or regulatory-PD claim follows.

After both mappings are fitted on TRAIN OOF and frozen, canonical VALIDATION metrics must reproduce stored raw model metrics. The deterministic reported-probability rule requires no worse AUC/AP and no worse Brier/log loss, with at least one strict improvement. Measured status is XGBOOST_SELECTED_FOR_DOWNSTREAM. This is development selection, not untouched-test confirmation or production readiness. Paired 1,000-replicate validation bootstrap intervals quantify conditional sample uncertainty only.

The technical max-KS threshold is selected only from the chosen model's TRAIN OOF reported probabilities, with the highest finite threshold winning ties. It is applied unchanged to VALIDATION; reference 0.50 remains separate. Phase 6 added no lending policy, risk bands, score or explanation code. Phase 7 adds the separately versioned explanation/score controls below; SHAP contributions must never be claimed to sum directly to calibrated/reported probability. TEST SET REMAINS SEALED. See [ADR 005](decisions/005-calibration-and-model-selection.md).

One temporary weighted model uses the TRAIN class ratio with unchanged selected parameters. Its separate validation diagnostics do not replace the canonical artifact. Raw probabilities remain uncalibrated; the fixed 0.50 reference threshold is neither optimized nor business policy. Native gain is an aggregate split diagnostic, not SHAP, causality or a customer reason. The versioned native JSON model is ignored, hash-identified and reloaded to verify TRAIN/VALIDATION probabilities. Load trusted XGBoost-created native files only. No customer-level probabilities or matrices are exported; TEST stays sealed. See [XGBoost report](xgboost_model_report.md).

## Implemented Phase-7 explanation and internal-score governance

| Identity | Version | Contract |
| --- | --- | --- |
| Model | `xgboost-challenger-1.0.0` | Frozen binary logistic artifact with SHA-256 |
| Calibration | `xgboost-calibration-1.0.0` | Identity; null artifact path/hash |
| Explainability | `xgboost-shap-1.0.0` | Tree SHAP raw margin, path dependent, signed local aggregation |
| Internal score | `internal-risk-score-1.0.0` | Base 600, good:bad odds 50, PDO 20 |

Future inference/audit records must identify all four independently, alongside preprocessing/feature identity. Phase 8 now supplies the independently versioned API/audit boundary below. Trusted project-local hashes are verified before artifact loading; no arbitrary external object is accepted, and no SHAP explainer binary is required.

Only VALIDATION supplies real-data Phase-7 SHAP, scores and decile diagnostics. Source contributions sum signed one-hot values first; global source/family magnitude is computed afterward. Positive default-risk SHAP lowers score points. Additive score decomposition is disabled for non-identity calibration, a non-logistic objective, different explanation units or numerically clipped probability. Raw-margin explanations and probability-to-score mathematics remain separate capabilities; a future non-identity consumer needs explicit versioned integration.

The score is not FICO, regulatory validation, a new predictive model or a business policy. No lending cutoff or risk bands exist. The Phase-6 threshold is read unchanged and converted only to a technical reference score. Diagnostic reason codes describe model behavior, not causality or regulatory adverse-action explanations. Demographic exclusion does not rule out proxies or establish fairness.

The owner explicitly chose to leave TRAIN OOF score statistics unavailable rather than retrain models to recover discarded row-level OOF probabilities. In-sample TRAIN scores are not substitutes. Historical experiment metadata and Phase-1–6 reports remain immutable. See [ADR 006](decisions/006-explainability-and-internal-score.md).

## Implemented Phase-8 inference audit contract

Each successful response follows an audit commit identifying API/input schema, model version and artifact SHA-256, calibration version/method, score version and explanation version where applicable. Service version credit-risk-api-1.0.0 and Alembic revision phase8_001 remain independent. Existing model/calibration/explanation/score identities are loaded from tracked metadata without rewriting historical records.

API requests contain only the 19 financial predictors. The artifact-only runtime loads once at startup, performs no fitting and never reads dataset partitions. Synthetic real-artifact tests verify direct inference and Phase-7 reason agreement. TEST remains sealed. No business action derives from the Phase-6 technical threshold.

Audit rows include server UUID, timezone-aware UTC timestamp, non-secret API-key ID, canonical outputs and optional top-k diagnostic reasons. Raw financial inputs, secrets, full feature/SHAP arrays, demographics and target labels are not retained. Consequently full historical input reconstruction needs an explicitly authorized future secure retention design. Database write failure rolls back and prevents a successful inference response.

Phase 8 verified isolated persistence/migrations and PostgreSQL SQL generation; Phase 9 subsequently verified live PostgreSQL 17.10 under local Docker Compose. Process-local rate limiting, shared-SHAP locking and absence of TLS/secret-management/observability infrastructure are explicit limitations. See [API](api.md), [persistence](persistence.md) and [ADR 007](decisions/007-api-and-persistence.md).


## Phase-9 operational identities and limits

Operations version model-operations-1.0.0 and baseline output-monitoring-baseline-1.0.0 are independent of model, calibration, explanation, score, API/service and Alembic revision. Container runtime versions/digests and actual PostgreSQL validation status are recorded separately in new operations metadata/report; historical scientific and API manifests are immutable.

The aggregate baseline consumes only the existing VALIDATION decile table. No row-level data or TEST scoring is required. PSI is descriptive, uses frozen bins and a small-sample flag, and never triggers retraining or lending actions. Audit failures emit counts rather than offending records. No feature drift, live predictive performance or API failure rate is inferred from retained successful output records. Cloud deployment, external secret management and final TEST evaluation remain unimplemented. See [model operations](model_operations.md).
