# Model governance

Phase-4 baseline controls are identified below. Calibration, explanation, business-policy and deployment controls remain requirements for future phases.

## Model versioning
Every deployed/serialized model must have an explicit version or immutable artifact identity; link preprocessing, feature schema and any calibrator to it.

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
This system is not a regulatory or production lending authority. No real lending decision should rely on this repository. Security, privacy, monitoring and operational validation remain future work.

## Verified V1 data boundary
UCI 350 is selected under [ADR 001](decisions/001-dataset-selection.md). Experiments must identify the XLS checksum in the dataset manifest and the canonical schema. The label is next-month default payment, not a regulatory or 12-month PD. No event-level scoring dates or multiple calendar scoring cohorts exist in the verified workbook; the Phase-3 stratified random split is not out-of-time validation. Income/employment are absent. [ADR 002](decisions/002-feature-policy-and-split.md) excludes demographics from primary predictors while retaining separate review frames and preserves literal categorical repayment codes without assigning undocumented meanings.

Phase 3 fits preprocessing only, on 21,000 training rows. Manifests record split/feature/preprocessing versions, fitted row count, runtime versions and encoded lineage; a content-addressed local artifact has a verified serialization round-trip. The test set remains reserved for final evaluation. Future tuning/cross-validation must fit preprocessing inside each training fold and use consistent partitions across baseline/challenger comparisons.

## Implemented Phase-4 baseline

`logistic-baseline-1.0.0` uses fixed L2 LogisticRegression, C=1.0 and class_weight=None. TRAIN alone fits the model; the Phase-3 preprocessor is loaded without refitting. The model manifest links raw dataset SHA-256, split/feature/preprocessing identity, code/configuration/runtime versions, convergence and local artifact hash. Only trusted project-created joblib files may be loaded; a checksum cannot make arbitrary pickle safe. No customer predictions are exported.

TRAIN diagnostics and VALIDATION assessment include ROC-AUC, Average Precision, KS, Gini, Brier/log loss, mean probability, prevalence and fixed 0.50 reference-threshold metrics. VALIDATION bootstrap intervals do not alter the model. Threshold 0.50 is not optimized and has no lending-policy meaning. TEST probabilities, predictions and predictive metrics are prohibited in Phase 4; test_set_evaluated=false is recorded. TEST SET REMAINS SEALED.

Outputs are raw model probabilities of next-month default payment, not calibrated PD. Formal calibration assessment belongs to Phase 6. Future prediction metadata must identify model version, feature/preprocessing identity and raw_probability semantics; no API/persistence implementation exists yet. Phase 5's future challenger must be compared on the same validation population without opening TEST. Coefficients are conditional, L2-shrunk and noncausal, with standardized-numeric and full-one-hot caveats in the [baseline report](baseline_model_report.md).
