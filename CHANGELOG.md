# Changelog

## Unreleased
- Added Phase-7 frozen XGBoost Tree SHAP in raw-margin units, verified 103-feature lineage, signed source/family aggregation and deterministic diagnostic local drivers using SHAP 0.51.0.
- Added versioned internal score (base 600, good:bad odds 50, PDO 20), inverse/rank validation, guarded additive score points, VALIDATION summary/deciles and the unchanged Phase-6 threshold's technical score equivalent.
- Added a validation-only shared consumer, five aggregate artifacts, Phase-7 tests, explainability/score documentation, ADR 006 and completion report. TRAIN OOF score statistics remain unavailable under the owner's explicit no-retraining instruction. Historical experiment metadata and reports remain unchanged; TEST stays sealed and Phase 8 has not started.
- Added Phase-6 five-fold TRAIN OOF generation for both fixed models, fold-local preprocessing, and a second TRAIN-only CV over identity, sigmoid and isotonic calibration.
- Selected versioned identity mappings for both models; added aggregate reliability/ECE, reported-probability comparison and paired AUC/AP/Brier/log-loss bootstrap. XGBoost is selected for downstream development, with TEST still sealed.
- Added TRAIN-derived max-KS technical threshold analysis, non-identity artifact serialization tests, calibration documentation, ADR 005 and the Phase-6 report. No SHAP, score, risk bands, business policy or Phase-7 functionality was implemented.
- Reproduced the unchanged Phase-4/5 workflows as required verification; model hashes, parameters and measured metrics are unchanged. The pre-commit governance fix restores historical metadata and preserves original provenance, timestamps and search timings on identical reruns; new experiments use explicitly scoped source hashes.
- Added XGBoost 3.2.0 and the unweighted xgboost-challenger-1.0.0 model with 24-candidate, four-fold TRAIN-only randomized search and fresh preprocessing within each fold.
- Added stored-baseline compatibility checks, validation deltas, paired bootstrap comparison, separate class-weight sensitivity, mapped native gain importance and ignored native JSON model serialization. TEST remains sealed and final selection is deferred.
- Added Phase-5 configuration, synthetic leakage/comparison/sealing tests, ADR 004 and XGBoost/phase reports. No calibration, SHAP or lending policy was implemented.
- Added one fixed L2 Logistic Regression baseline, version logistic-baseline-1.0.0, trained only on TRAIN with verified Phase-3 contracts and the existing local preprocessor.
- Added TRAIN/VALIDATION discrimination and raw-probability diagnostics, fixed-reference-threshold metrics, deterministic validation bootstrap intervals, coefficient lineage and content-addressed local model serialization. TEST remains sealed; no challenger, calibration or lending policy was implemented.
- Added baseline model documentation, ADR 003, Phase-4 completion report and synthetic contract/model/test-sealing tests.
- Added a deterministic stratified 70/15/15 split, explicit demographic/ID/target separation, 26 domain-defined financial features and train-only numeric/categorical preprocessing.
- Added aggregate split/feature/preprocessing manifests, traceable encoded names, trusted local serialization checks and synthetic leakage-isolation tests; no predictive model was trained.
- Completed official UCI 350 acquisition, pinned raw checksum, provenance manifest and strict canonical schema for the next-month default-payment target.
- Added descriptive data-quality profiling, aggregate metadata, dataset card, physical contract and dataset-selection ADR; retained undocumented codes and numeric anomalies unchanged.
- Added offline acquisition/loader/schema/quality tests and executed real-data integration; modeling and preprocessing remain future work.
- Established ten-phase governance and persistent project memory, with completion reports and project-owner technical review before the owner creates each Git commit.
- Defined the credit-risk problem, conceptual data contract, candidate framework and leakage policy.
- Added a minimal Python package, YAML configuration and dataset-independent foundation tests.
- Reserved future data, model and explanation directories without implementing those components.
