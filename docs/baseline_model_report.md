# Objective

Establish one reproducible, interpretable Logistic Regression baseline, version `logistic-baseline-1.0.0`, using train fitting and validation assessment. No performance-driven model selection occurred.

# Dataset and Target

UCI Default of Credit Card Clients, 30,000 historical Taiwan credit-card customers. Dataset SHA-256: `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`. Target: `default_next_month`, the source-defined next-month default-payment event. This is not Basel/IFRS 9 PD, 12-month PD, a verified 90-DPD event, FICO or a bank credit score. Attribution and source limitations remain in the [dataset card](dataset_card.md).

# Modeling Population

TRAIN: 21,000 rows; VALIDATION: 4,500 rows. TEST has 4,500 rows according to Phase-3 metadata. No customer rows are dropped or resampled.

# Feature Set

Reuse 19 raw financial inputs and 26 stateless engineered features. The transformed matrix has 39 standardized numeric columns plus 64 train-learned one-hot columns, totaling 103. ID, target, sex, age, education and marital status are absent from predictors. Demographic exclusion does not demonstrate fairness. No target-driven feature selection or correlation-based removal occurred.

# Split Strategy

`sorted_id_two_stage_stratified_v1`, seed 42, train/validation/test = 70/15/15. The baseline reproduces Phase-3 splitting, loads its verified fitted preprocessor and transforms only TRAIN and VALIDATION. TEST remains sealed. This is stratified random validation, with no out-of-time claim. The separately required Phase-3 preparation command still performs its existing structural transforms/checks; it generates no predictive evaluation.

# Model Specification

LogisticRegression, L2, C=1.0, solver=lbfgs, fit_intercept=True, class_weight=None, max_iter=5000, tol=1e-8. sklearn 1.8 expresses L2 as l1_ratio=0.0; see [ADR 003](decisions/003-logistic-baseline.md). LBFGS is deterministic without random_state; numerical fitting uses one thread. It converged in **1,042 iterations**, with no convergence warning. Intercept: **-1.626504411859469**.

Preprocessing: `train_median_scale_onehot_v1`; feature engineering: `financial_features_v1`. Preprocessor SHA-256: `e8f6ce776bd44c48871c585c5d472676ad8c418da39c513c1019bf36070ee8b4`. Its medians, scaling and vocabulary were fitted on Phase-3 TRAIN only. Phase 4 loads this state without refitting. Semantic manifest identities, implementation hashes, runtime versions, ordered names, lineage, sizes and finite values are checked before model fitting. Differences fail loudly.

# Why Logistic Regression

Linear log-odds and explicit coefficients provide an interpretable baseline commonly useful in credit-risk modeling. It is a comparison anchor for a future nonlinear challenger, not a claim that all banks use this model or that it is production-ready.

# Class Imbalance Decision

Use class_weight=None with no resampling. The approximately 22% positive rate warrants discrimination and probability diagnostics, but not an automatic change to the empirical prior. There is only one primary model and no balanced sensitivity experiment.

# Performance

| Metric | TRAIN | VALIDATION |
| --- | --- | --- |
| ROC-AUC | 0.778845055 | 0.765638177 |
| Average Precision (AP) | 0.555489176 | 0.519684092 |
| KS = max(TPR - FPR) | 0.426408675 | 0.405350576 |
| Gini = 2 × AUC - 1 | 0.557690110 | 0.531276353 |

Average Precision is not trapezoidal PR-AUC. Train minus validation gaps are 0.01321 AUC and 0.03581 AP. Validation discrimination is modestly lower, with no suspiciously perfect performance or dramatic collapse. This single split cannot establish absence of overfitting or identify the extent of underfitting; a linear model may miss nonlinearities. No arbitrary acceptance-performance floor or accuracy headline was used.

Validation row bootstrap: 1,000 requested and successful replicates, 0 single-class skips, seed 42, replacement sampling, percentile 95% intervals. AUC CI: **[0.747683105, 0.783025861]**; AP CI: **[0.487398831, 0.558423045]**. Intervals condition on fixed predictions and do not include model-training uncertainty. Results did not alter the model.

# Probability Diagnostics

| Metric | TRAIN | VALIDATION |
| --- | --- | --- |
| Brier score | 0.133943991 | 0.138791607 |
| Log loss | 0.429087163 | 0.441318621 |
| Mean raw probability | 0.221190478 | 0.219725065 |
| Observed positive rate | 0.221190476 | 0.221111111 |

These are **RAW / UNCALIBRATED** model probabilities of next-month default payment. Near-matching mean probability and prevalence does not prove calibration. No calibrated PD or fitted calibrator exists; formal calibration assessment belongs to Phase 6.

# Reference Threshold Diagnostics

**REFERENCE THRESHOLD = 0.50**, using raw_probability >= 0.50. This is a model diagnostic, not an optimized threshold, final credit cut-off, risk band or business policy. Undefined precision/F1 in zero-positive synthetic cases is reported as zero.

| Diagnostic | TRAIN | VALIDATION |
| --- | --- | --- |
| TN | 15,566 | 3,323 |
| FP | 789 | 182 |
| FN | 2,939 | 645 |
| TP | 1,706 | 350 |
| Precision | 0.683767535 | 0.657894737 |
| Recall / sensitivity | 0.367276642 | 0.351758794 |
| Specificity | 0.951757872 | 0.948074180 |
| F1 | 0.477871148 | 0.458415193 |

Confusion matrix ordering is [[TN, FP], [FN, TP]]. The reference threshold misses many positive labels; this does not establish an alternative business threshold or lending decision.

# Coefficient Analysis

All 103 coefficients are finite and aligned with the exact transformed names. Full values, exponentials, direction, type and original-source lineage are in [baseline_coefficients.json](../data/metadata/baseline_coefficients.json), ordered by transformed column.

| Strongest positive transformed feature | Coefficient | exp(coefficient) |
| --- | --- | --- |
| repayment__repayment_status_2005_09_status_2 | 0.915581 | 2.498227 |
| repayment__repayment_status_2005_09_status_3 | 0.808724 | 2.245041 |
| numeric__payment_amount_max | 0.602619 | 1.826897 |
| repayment__repayment_status_2005_07_status_6 | 0.516252 | 1.675735 |
| repayment__repayment_status_2005_04_status_4 | 0.507782 | 1.661602 |

| Strongest negative transformed feature | Coefficient | exp(coefficient) |
| --- | --- | --- |
| repayment__repayment_status_2005_06_status_5 | -0.981183 | 0.374867 |
| numeric__bill_amount_max | -0.836785 | 0.433101 |
| repayment__repayment_status_2005_09_status_8 | -0.630727 | 0.532205 |
| repayment__repayment_status_2005_05_status_4 | -0.579465 | 0.560198 |
| repayment__repayment_status_2005_09_status_5 | -0.576255 | 0.561999 |

Largest absolute coefficients, descending: June status_5, September status_2, numeric bill_amount_max, September status_3, September status_8. The positive payment maximum and negative high-delay tokens must not be read as standalone financial risk rules. They are conditional coefficients in a redundant, regularized feature representation; categorical sparsity can also make individual estimates unstable. No monotonicity, statistical significance or causal claims are made.

# Interpretation Caveats

Numeric coefficients approximately measure a change in model log-odds for one training-standard-deviation increase, holding other transformed inputs constant; exp(beta) gives the corresponding multiplicative odds change. Related histories, means, sums, maxima and ratios often cannot vary independently, limiting that interpretation.

All learned one-hot categories are retained. There is no omitted categorical reference: each categorical exp(beta) is **not** a conventional odds ratio versus an omitted group. L2 shrinks estimates and distributes signal among correlated inputs. Magnitudes depend on encoding/scaling; estimates are not causal effects or independent financial causes. No TRAIN correlation matrix was added, and no feature was removed. A future XGBoost challenger may capture nonlinear structure differently; it is not implemented here.

# Test Set Policy

**NO TEST PERFORMANCE WAS COMPUTED IN PHASE 4. TEST SET REMAINS SEALED.**

No test probabilities, predictions, threshold diagnostics, bootstrap or model-selection decisions were generated. The modeling consumer exposes no X_test or y_test. Automated tests make access to the discarded TEST branch fail.

# Known Limitations

Historical static population, undocumented repayment codes, missing event timestamps, possible proxies and related feature families remain. No true out-of-time validation, fairness certification, regulatory compliance or lending readiness is established. No formal calibration, challenger, SHAP, scoring/policy, API, database or deployment exists. Only the current Windows/Python 3.14.6 environment was exercised; transitive dependencies are recorded but not fully locked. Cross-runtime/hardware bitwise reproducibility is not promised.

Model artifact: `artifacts/models/logistic-baseline-1.0.0_a05feadd329d36515f3e66f3ca984af52401d90702a7fea2bf3f71834c2fa07c.joblib`; SHA-256: `a05feadd329d36515f3e66f3ca984af52401d90702a7fea2bf3f71834c2fa07c`. This ignored local object is trusted-project-only. A checksum does not make arbitrary pickle/joblib safe. See [model manifest](../data/metadata/baseline_model_manifest.json) and [metrics](../data/metadata/baseline_metrics.json). Future prediction metadata must include this model version, preprocessing/feature identity and explicit raw_probability semantics; no serving contract is implemented now.

# Next Phase Boundary

Phase 5 may create an XGBoost challenger only after owner review, commit and a new explicit phase request. Keep comparable validation partitions; any cross-validation must refit preprocessing within each training fold. Phase 5 is NOT_STARTED. Calibration belongs to Phase 6 and explainability to Phase 7.
