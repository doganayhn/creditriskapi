# PHASE 4 COMPLETION REPORT

## 1. Objective

Implement one fixed Logistic Regression baseline for raw next-month default-payment probabilities, TRAIN/VALIDATION evaluation, coefficient analysis and reproducible local model traceability. TEST SET REMAINS SEALED.

## 2. Pre-Implementation Repository State

HEAD: `819e449`; branch: `main`, aligned with `origin/main`. Working tree was clean. Phase 3 was committed as `feat: add leakage-safe credit risk feature pipeline`. Phases 1–3 were COMPLETED; Phases 4–10 were NOT_STARTED. Phase-3 manifests and the verified raw/preprocessor artifacts were available. No predictive model or Phase-5+ implementation existed, and TEST had not been predictively evaluated.

## 3. Documentation Reviewed

Reviewed AGENTS.md, PROJECT_RULES.md, ROADMAP.md, PHASE_STATUS.md, README.md and CHANGELOG.md; architecture, problem definition, dataset card, data contract, quality report, leakage policy, model governance, glossary, feature engineering and modeling-dataset documentation; ADRs 001/002 and Phase-1/2/3 reports. Inspected configuration, config.py, data/features modules, existing tests and Git state. Verified sklearn 1.8's LogisticRegression API against its installed signature and [official release notes](https://scikit-learn.org/1.8/whats_new/v1.8.html).

## 4. Modeling Contract Verification

- Dataset SHA-256: `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`.
- Split: `sorted_id_two_stage_stratified_v1`, seed 42, stratified random 70/15/15.
- Feature engineering: `financial_features_v1`.
- Preprocessing: `train_median_scale_onehot_v1`.
- Preprocessor SHA-256: `e8f6ce776bd44c48871c585c5d472676ad8c418da39c513c1019bf36070ee8b4`.
- TRAIN: 21,000 × 103; VALIDATION: 4,500 × 103.
- TEST: 4,500 rows from Phase-3 metadata, sealed.

The consumer verifies raw/Phase-2 identity, pinned semantic Phase-3 manifests, code/runtime versions, artifact checksum, unique ordered names, lineage, row counts and finite matrices. Identifier, target and demographic-review fields remain excluded. Disagreement fails before training; no Phase-3 metadata is repaired or overwritten by modeling.

## 5. Baseline Model Specification

Estimator: sklearn.linear_model.LogisticRegression. Version: `logistic-baseline-1.0.0`. Effective penalty: L2, represented by sklearn 1.8's `l1_ratio=0.0`. Fixed C=1.0, solver=lbfgs, fit_intercept=True, class_weight=None, max_iter=5000, tol=1e-8, random_state=None. LBFGS does not use random_state; fitting limits numerical-library threads to one.

Convergence: **converged in 1,042 iterations**, with no convergence warning. A ConvergenceWarning or iteration-limit exhaustion fails the run. Intercept: -1.626504411859469. No solver or hyperparameter search occurred.

## 6. Class Imbalance Decision

Use class_weight=None with no resampling. Approximately 22% positive prevalence is imbalanced but not an extreme rare-event setting. The unweighted objective preserves the empirical prior without class-weight-induced probability-scale changes before calibration analysis. No balanced sensitivity model, SMOTE, oversampling or undersampling was implemented.

## 7. Training Procedure

Load the verified Phase-3 TRAIN-fitted preprocessor without refitting. Reuse canonical loading, deterministic splitting, stateless engineering and transformation. Discard the TEST branch immediately after the existing splitter's structural checks. The modeling data object exposes only TRAIN/VALIDATION matrices and labels.

Fit the estimator on X_train/y_train only. Generate raw TRAIN and VALIDATION probabilities. No train+validation refit, validation fitting or TEST scoring occurs. The separately required Phase-3 preparation command retains its existing structural transforms/checks of all partitions; it performs no predictive evaluation.

## 8. Train Metrics

| Metric | Actual result |
| --- | --- |
| ROC-AUC | 0.778845055 |
| Average Precision | 0.555489176 |
| KS | 0.426408675 |
| Gini | 0.557690110 |
| Brier score | 0.133943991 |
| Log loss | 0.429087163 |
| Mean raw probability | 0.221190478 |
| Observed positive rate | 0.221190476 |
| TN / FP / FN / TP | 15,566 / 789 / 2,939 / 1,706 |
| Precision | 0.683767535 |
| Recall / sensitivity | 0.367276642 |
| Specificity | 0.951757872 |
| F1 | 0.477871148 |

## 9. Validation Metrics

| Metric | Actual result |
| --- | --- |
| ROC-AUC | 0.765638177 |
| Average Precision | 0.519684092 |
| KS | 0.405350576 |
| Gini | 0.531276353 |
| Brier score | 0.138791607 |
| Log loss | 0.441318621 |
| Mean raw probability | 0.219725065 |
| Observed positive rate | 0.221111111 |
| TN / FP / FN / TP | 3,323 / 182 / 645 / 350 |
| Precision | 0.657894737 |
| Recall / sensitivity | 0.351758794 |
| Specificity | 0.948074180 |
| F1 | 0.458415193 |

Both sections use **REFERENCE THRESHOLD = 0.50**, with probability >= 0.50. Confusion matrix order is [[TN, FP], [FN, TP]]. This is not an optimized threshold or business cut-off. KS = max(TPR − FPR); Gini = 2 × AUC − 1. Average Precision is not trapezoidal PR-AUC. JSON preserves full precision.

## 10. Validation Uncertainty

Deterministic row bootstrap with replacement, seed 42, percentile 95% intervals:

- ROC-AUC CI: **[0.747683105, 0.783025861]**.
- Average Precision CI: **[0.487398831, 0.558423045]**.
- Requested/successful replicates: **1,000 / 1,000**.
- Single-class skips: **0**.

Intervals condition on fixed validation predictions; they exclude training and population-shift uncertainty. They did not alter the model. TEST was not bootstrapped.

## 11. Train vs Validation Assessment

Train minus validation gaps: approximately 0.01321 AUC and 0.03581 AP. Validation Brier/log loss are modestly worse. There is no dramatic collapse, unexpectedly constant output, below-chance AUC or suspiciously perfect discrimination. This single split cannot establish absence of overfitting or quantify underfitting; the linear baseline may miss nonlinear structure. The reference threshold has limited positive-label recall. No TEST evidence or arbitrary performance floor was used.

## 12. Coefficient Analysis

Strongest positive coefficients:

| Transformed feature | Coefficient |
| --- | --- |
| repayment__repayment_status_2005_09_status_2 | 0.915581 |
| repayment__repayment_status_2005_09_status_3 | 0.808724 |
| numeric__payment_amount_max | 0.602619 |
| repayment__repayment_status_2005_07_status_6 | 0.516252 |
| repayment__repayment_status_2005_04_status_4 | 0.507782 |

Strongest negative coefficients:

| Transformed feature | Coefficient |
| --- | --- |
| repayment__repayment_status_2005_06_status_5 | -0.981183 |
| numeric__bill_amount_max | -0.836785 |
| repayment__repayment_status_2005_09_status_8 | -0.630727 |
| repayment__repayment_status_2005_05_status_4 | -0.579465 |
| repayment__repayment_status_2005_09_status_5 | -0.576255 |

Largest absolute coefficients, descending: June status_5, September status_2, bill_amount_max, September status_3, September status_8. All 103 coefficients are finite and aligned. Their source/type, absolute value, exponential and direction are recorded in the coefficient artifact.

These are conditional model terms. Positive payment maxima and negative high-delay tokens are not standalone financial risk rules; related inputs and sparse category representation limit interpretation. No monotonicity, significance or causal claim is made.

## 13. Coefficient Interpretation Caveats

Numeric coefficients approximately describe a one-training-standard-deviation increase in a transformed input, holding other transformed inputs constant; exp(beta) gives the corresponding multiplicative odds change. Related raw histories, aggregates and ratios may not vary independently.

Full one-hot encoding retains all learned categories. There is no omitted categorical reference, and categorical exp(beta) is not a conventional odds ratio versus an omitted group. L2 shrinks coefficients; correlated features distribute signal. Magnitudes depend on encoding/scaling and are not causal effects or independent financial causes. No correlation-based removal or target-driven feature selection occurred.

## 14. Probability Semantics

Probabilities are **RAW / UNCALIBRATED** model probabilities of next-month default payment. No calibrated PD exists yet. Mean probability near prevalence does not establish calibration. These outputs are not regulatory, Basel/IFRS 9, 12-month or verified 90-DPD probabilities, FICO or a bank credit score.

## 15. Test Set Status

**TEST SET WAS NOT EVALUATED. TEST SET REMAINS SEALED.**

No test probabilities, predictions or performance metrics were generated. TEST did not influence features, fitting, model choice, thresholds or coefficients. Both model and metrics manifests record test_set_evaluated=false.

## 16. Files Created

Twelve new Git-visible files:

- src/credit_risk/modeling/__init__.py
- src/credit_risk/modeling/contract.py
- src/credit_risk/modeling/baseline.py
- src/credit_risk/modeling/metrics.py
- src/credit_risk/modeling/artifacts.py
- tests/test_modeling.py
- data/metadata/baseline_model_manifest.json
- data/metadata/baseline_metrics.json
- data/metadata/baseline_coefficients.json
- docs/decisions/003-logistic-baseline.md
- docs/baseline_model_report.md
- docs/phase_reports/phase_04_completion_report.md

The model binary was also created locally under ignored artifacts/models.

## 17. Files Modified

Ten existing Markdown files: CHANGELOG.md, PHASE_STATUS.md, README.md, ROADMAP.md, docs/architecture.md, docs/decisions/README.md, docs/feature_engineering.md, docs/leakage_policy.md, docs/model_governance.md and docs/modeling_dataset.md.

Data/features implementation, configuration, dependencies, Phase-3 manifests and historical Phase-1/2/3 reports remain unchanged.

## 18. Model Artifact

Path: `artifacts/models/logistic-baseline-1.0.0_a05feadd329d36515f3e66f3ca984af52401d90702a7fea2bf3f71834c2fa07c.joblib`.

SHA-256: `a05feadd329d36515f3e66f3ca984af52401d90702a7fea2bf3f71834c2fa07c`.

Ignored and untracked. Training-probability serialization round-trip passed at absolute tolerance 1e-12. Only trusted project-created local artifacts may be loaded; a checksum does not make arbitrary pickle/joblib safe.

## 19. Metadata / Manifests

baseline_model_manifest.json records model/version, source hash, split/feature/preprocessor identities, configuration/code/runtime provenance, effective L2 and estimator parameters, convergence/iterations, intercept, row counts, artifact path/hash, timestamp and TEST sealing.

baseline_metrics.json contains only TRAIN/VALIDATION metrics plus validation uncertainty, raw-probability semantics, model version and the fixed reference threshold. baseline_coefficients.json contains all transformed-column coefficients and source lineage in deterministic order. No customer records or per-customer outputs are exported.

## 20. Tests Executed

```powershell
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m credit_risk.modeling.baseline
.venv\Scripts\python.exe -m pytest tests/test_modeling.py -q
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
git ls-files data/raw data/interim data/processed artifacts
git diff -- docs/phase_reports/phase_01_completion_report.md
git diff -- docs/phase_reports/phase_02_completion_report.md
git diff -- docs/phase_reports/phase_03_completion_report.md
```

Additional Python stdin verification called run_baseline(Path.cwd()) again and asserted byte/mtime equality for all three baseline JSON files. Additional Git checks compared Phase-3 manifests and verified artifact ignore status; documentation links and whitespace were checked locally.

## 21. Test Results

**160 passed, 0 failed, 0 skipped, no warnings**, in **11.46 seconds**. This includes 127 existing tests and 33 new Phase-4 cases. The targeted Phase-4 suite also passed: 33 tests in 6.69 seconds. No test failures occurred.

pip check: **No broken requirements found.** Git whitespace check passed. Historical report and Phase-3 manifest diffs are empty. Automated tests require no network or real customer data.

## 22. Real-Data Integration Validation

The required acquisition command verified/reused the pinned 30,000-row XLS. Phase-3 preparation reproduced its existing 103-column contract and unchanged manifests. The baseline CLI then verified identities, loaded TRAIN-fitted preprocessing, fit TRAIN only, converged, evaluated TRAIN/VALIDATION, bootstrapped validation, extracted coefficients and verified local model serialization. No TEST predictive output was generated.

## 23. Determinism / Reproducibility Validation

A repeated real run produced identical model hash, 1,042 iterations and byte-identical metrics, coefficients and model manifest, with unchanged JSON modification times. Synthetic tests compare fitted coefficients/probabilities at absolute tolerance 1e-12 and metrics exactly; bootstrap results repeat with the same seed.

Source, split, preprocessing, model parameters, config/code hashes and runtime versions are recorded. LBFGS uses no stochastic random_state; bootstrap uses centralized seed 42. Cross-platform/library/BLAS bitwise reproducibility is not claimed.

## 24. Known Limitations

Historical Taiwan sample, static cohorts, undocumented category meanings, uncertain snapshot timing, demographic proxies and correlated feature families remain. No true out-of-time validation, fairness certification, production readiness or regulatory compliance is established.

The model is linear in transformed inputs. Coefficient interpretation is conditional and encoding-dependent. Calibration is unassessed; bootstrap intervals omit training uncertainty. No challenger, SHAP, score, risk bands, business decisions, API, database, Docker or MLflow was implemented.

## 25. Deviations From Prompt

One API-level adaptation: sklearn 1.8's non-deprecated l1_ratio=0.0 replaces the requested literal penalty="l2" argument, with exactly the same L2 objective. Both the effective penalty and actual estimator parameters are recorded and tested. No functional scope deviation.

## 26. Risks / Technical Debt

The Phase-3 V1 semantic contracts are deliberately pinned to the reviewed commit; definition/runtime/artifact changes require explicit investigation. Serialization requires trusted storage. The current Windows/Python 3.14.6 environment is verified, but transitive dependencies are not fully locked and cross-runtime artifact reconstruction is not guaranteed.

Raw/aggregate financial inputs share signal, and rare-category coefficients may be unstable. Demographic exclusion does not remove proxies. Future cross-validation must refit preprocessing within each training fold.

The Phase-4-authorized artifacts/models layout, with model version plus content digest, refines PROJECT_RULES.md's earlier generic experiment-directory example; ADR 003 records the choice. Aggregate manifests describe the latest fixed baseline while content-addressed binaries are not overwritten.

## 27. Phase-5 Recommendations

When explicitly authorized after owner review and commit, compare an XGBoost challenger on the same validation population. Preserve test sealing and fold-safe preprocessing for any tuning. Keep raw-probability, calibration and business-policy identities separate. These are recommendations only; Phase 5 is NOT_STARTED.

## 28. Reproduction Commands

From the repository root using the existing environment:

```powershell
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m credit_risk.modeling.baseline
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
git ls-files data/raw data/interim data/processed artifacts
```

All three project CLIs accept --project-root PATH. Fresh environments follow README installation instructions; reproducing the pinned Phase-3 artifact requires compatible recorded dependencies. No new dependency was installed for Phase 4.

## 29. Git Status

Ten tracked Markdown files modified; twelve new Git-visible files untracked. Nothing staged. Raw/interim/processed/artifacts tracking contains only .gitkeep markers.

Raw data, processed customer data, customer probabilities/predictions, preprocessor binary and model binary are not tracked. Historical reports remain unchanged. HEAD remains `819e449`; **no commit was created**.

## 30. Documentation Status

Baseline report, ADR 003, aggregate outputs and this completion report exist. README, architecture, governance, leakage/data-consumer documentation, changelog and phase records reflect actual Phase-4 behavior. Final states: Phases 1–4 COMPLETED; Phases 5–10 NOT_STARTED. Current Completed Phase: Phase 4. Next Phase: Phase 5, not started.

## 31. Acceptance Criteria Checklist

- [x] Required repository documentation was reviewed before implementation.
- [x] Phase-2 dataset identity was verified.
- [x] Phase-3 split identity was verified.
- [x] Phase-3 feature/preprocessing identity was verified.
- [x] Logistic Regression is the only predictive model implemented.
- [x] Primary model uses L2 regularization.
- [x] Primary model uses fixed C=1.0.
- [x] Primary model uses class_weight=None.
- [x] No hyperparameter search was performed.
- [x] No resampling/SMOTE was performed.
- [x] Model was fit only on TRAIN.
- [x] Validation data was not used for fitting.
- [x] TEST data was not used for fitting.
- [x] TEST predictions were not generated.
- [x] TEST probabilities were not generated.
- [x] TEST performance metrics were not calculated.
- [x] test_set_evaluated=false is recorded.
- [x] Model convergence was explicitly verified.
- [x] Raw train probabilities were generated.
- [x] Raw validation probabilities were generated.
- [x] ROC-AUC was measured on TRAIN.
- [x] ROC-AUC was measured on VALIDATION.
- [x] Average Precision was measured on TRAIN.
- [x] Average Precision was measured on VALIDATION.
- [x] KS was measured on TRAIN.
- [x] KS was measured on VALIDATION.
- [x] Gini was measured on TRAIN.
- [x] Gini was measured on VALIDATION.
- [x] Brier score was measured on TRAIN.
- [x] Brier score was measured on VALIDATION.
- [x] Log loss was measured on TRAIN.
- [x] Log loss was measured on VALIDATION.
- [x] Reference-threshold metrics were computed at exactly 0.50.
- [x] Threshold 0.50 was not optimized.
- [x] Threshold 0.50 was not described as business policy.
- [x] Coefficients align with transformed feature names.
- [x] Coefficients contain no NaN/inf.
- [x] Numeric coefficient interpretation reflects standardization.
- [x] Categorical coefficients are not falsely described as omitted-reference odds ratios.
- [x] Regularization/correlation interpretation caveats are documented.
- [x] Model artifact was serialized locally.
- [x] Model artifact SHA-256 was recorded.
- [x] Model binary artifact is not tracked in Git.
- [x] Baseline model manifest exists.
- [x] Baseline metrics manifest exists.
- [x] Coefficient artifact exists.
- [x] Logistic baseline ADR exists.
- [x] Baseline model report exists.
- [x] No calibrated probability was created.
- [x] No SHAP implementation exists.
- [x] No risk band was created.
- [x] No internal score was created.
- [x] No business approval/decline decision was created.
- [x] No XGBoost model was implemented.
- [x] No customer-level predictions are tracked in Git.
- [x] Real UCI baseline experiment ran successfully.
- [x] Full automated test suite passes.
- [x] pip check passes.
- [x] git diff --check passes.
- [x] README matches actual implementation.
- [x] Architecture documentation is updated.
- [x] Historical phase reports remain unchanged.
- [x] Phase-4 completion report exists.
- [x] Phase 4 status is COMPLETED.
- [x] Phase 5 remains NOT_STARTED.
- [x] No Git commit was created automatically.

## 32. Final Verdict

PHASE 4 COMPLETED
