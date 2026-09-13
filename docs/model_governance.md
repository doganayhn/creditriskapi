# Future model governance

These are rules for future phases, not claims of implemented controls.

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
UCI 350 is selected under [ADR 001](decisions/001-dataset-selection.md). Experiments must identify the XLS checksum in the dataset manifest and the canonical schema. The label is next-month default payment, not a regulatory or 12-month PD. No event-level scoring dates or multiple calendar scoring cohorts exist in the verified workbook; do not call a future random/stratified split out-of-time validation. Income/employment are absent. Undocumented repayment/category codes and demographic eligibility remain Phase-3 decisions. Phase 2 has profiled data but has fitted no model or preprocessing component.
