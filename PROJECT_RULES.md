# Project rules

## Model / decision separation
Applicant data → risk model → probability estimate → calibration if justified → reported PD → risk representation → versioned business rules → operational recommendation.
The model estimates risk; business policy makes lending/review decisions. Training must not encode final credit policy.

## Probability honesty
A raw model score is an algorithm-specific output (possibly a margin). A raw probability is the model's probability output. A calibrated probability is the result of a separately evaluated calibration procedure. Reported PD is the explicitly documented estimate for the dataset-defined event and horizon. An internal risk score is a presentation mapping, and a business recommendation is a policy result. These are not interchangeable.

## SHAP / calibration consistency
Tree-based SHAP may explain the underlying XGBoost output in its declared units. A subsequent calibrator changes the output; the original SHAP values must not be presented as additive explanations of calibrated PD. V1 may describe direction, magnitude/ranking and dominant drivers while API and documentation distinguish explained model output from final PD. Explanations are not causal conclusions.

## Temporal honesty
Conceptually: observation window → cut-off/scoring point → performance window → default outcome. Static data without sufficient event timestamps cannot establish true observation-window reconstruction or out-of-time validation. State that limitation; do not invent a 12-month horizon or regulatory default.

## Leakage prevention
Only information theoretically observable at scoring time may be a predictor. Future, target-derived and post-outcome variables are prohibited. Fit learned transformations on training partitions only; see docs/leakage_policy.md.

## Reproducibility
Future experiments record dataset identity/version and checksum where possible, full configuration, centralized seed, feature set, split membership/logic, model parameters, metrics and immutable artifact identity. Use deterministic splits where possible; a fixed seed does not guarantee determinism across hardware or library versions.
Use explicit experiment identifiers such as `baseline_<UTC timestamp>_<config digest>`, with configuration snapshots and dependency versions. Future artifacts live under `artifacts/<experiment_id>/`; never silently overwrite an experiment. A model version or content digest must identify each serialized model. Phase 1 creates no experiments or model artifacts.

## Auditability
Later production phases must identify model, preprocessing, calibration (if applicable), API schema and decision-rule versions, prediction timestamp, and an appropriate input representation subject to privacy/technical constraints. Phase 8 persists successful inference outputs and independent version identities to a PostgreSQL-targeted audit schema. Raw financial inputs are not retained; complete historical input reconstruction remains unavailable. Business-rule versions remain future work because no lending policy is implemented.

## No false production claims
This is educational / portfolio work, not a real bank credit-decision engine. No real lending decision should rely on it. Do not claim regulatory compliance without implemented and verified controls.
