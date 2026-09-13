# Objective

Establish `xgboost-challenger-1.0.0` as a nonlinear comparison to the committed Logistic Regression baseline, using TRAIN-only selection and project VALIDATION assessment. No final production champion is selected.

# Dataset and Target

UCI Default of Credit Card Clients, 30,000 historical Taiwan credit-card customers. Target: default_next_month, the source-defined next-month default-payment outcome, not Basel/IFRS 9, 12-month or verified 90-DPD PD. Dataset SHA-256: `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`. Attribution and limitations remain in the [dataset card](dataset_card.md).

# Modeling Contract

Shared split: `sorted_id_two_stage_stratified_v1`, seed 42, 70/15/15. TRAIN has 21,000 rows and VALIDATION 4,500; TEST's 4,500-row count comes from Phase-3 metadata. Feature engineering: `financial_features_v1`; preprocessing: `train_median_scale_onehot_v1`. Final models share the exact 103 transformed features, including 39 numeric and 64 one-hot columns. Identifier, target and demographics are excluded.

Phase-3 manifests, raw bytes, code/runtime versions, feature lineage and fitted-preprocessor hash are verified. Stored Phase-4 metrics are loaded and checked against reproduced TRAIN/VALIDATION probabilities from the hash-verified baseline artifact. No baseline metrics are hard-coded. Historical reports and existing baseline data remain unchanged.

XGBoost consumes dense materializations of the same numeric values. This preserves implicit CSR zeros as actual zeros instead of XGBoost's sparse missing-value routing. No feature definition, scaling or category policy changes. The full-TRAIN float64 array is approximately 17.3 MB. See [ADR 004](decisions/004-xgboost-challenger.md) and the [official sparse/dense behavior](https://xgboost.readthedocs.io/en/release_3.2.0/faq.html).

# Why XGBoost

Boosted trees can learn nonlinear relationships and interactions absent from a linear log-odds baseline. It is a useful tabular-data challenger, without guaranteed superiority. Using the same representation controls the comparison primarily around model class.

XGBoost 3.2.0 is pinned and verified on Windows/Python 3.14.6; its Python >=3.10 requirement preserves this project's >=3.11 minimum. No existing numerical dependency changed.

# Test Set Policy

**TEST SET REMAINS SEALED. TEST SET WAS NOT EVALUATED.**

No test predictions, probabilities, performance metrics, bootstrap or selection decisions were generated. Phase-3 preparation retains its historical structural processing. The final modeling consumer exposes no test matrix or labels; the CV-input adapter discards project holdouts without examining them.

# Cross-Validation Design

24 randomized candidates × 4 shuffled stratified folds = **96 CV fits**, using TRAIN only and seed 42. Each fit constructs a fresh Phase-3 preprocessor. The wrapper accepts sklearn's y argument but discards it before unsupervised fitting, preserving the original target-rejection guard. Imputation, scaling and category vocabulary use fold-training rows only.

The Phase-3 full-TRAIN fitted preprocessor is never passed to CV. Stateless engineering may run beforehand. Synthetic tests vary fold distributions and inject a holdout-only category, then inspect fitted medians, vocabulary and row membership across actual CV Pipeline fits.

RandomizedSearchCV uses ROC-AUC and Average Precision, n_jobs=1, error_score=raise and return_train_score=False. Callable refit selects mean CV ROC-AUC first; machine-epsilon ties use AP, then smaller depth, fewer trees and stronger lambda/alpha/gamma regularization. An otherwise identical tie uses earlier candidate order. Accuracy is not a selection metric.

There is one search winner refit, one final canonical fit and one sensitivity fit: **99 total XGBoost fits per full run**. The search-refitted pipeline is not the published canonical artifact. No early stopping or project-validation fitting occurs.

# Search Space

The authoritative definition is configs/xgboost.yaml. CPU hist, binary:logistic, logloss, seed 42, n_jobs=1 and scale_pos_weight=1.0 remain invariant during search.

| Parameter | Candidates |
| --- | --- |
| colsample_bytree | 0.8, 0.9, 1 |
| gamma | 0, 0.1, 0.5 |
| learning_rate | 0.03, 0.05, 0.08, 0.1 |
| max_depth | 2, 3, 4, 5 |
| min_child_weight | 1, 3, 5, 10 |
| n_estimators | 200, 350, 500, 700 |
| reg_alpha | 0, 0.1, 0.5 |
| reg_lambda | 1, 5, 10 |
| subsample | 0.8, 0.9, 1 |

# Best Hyperparameters

| Parameter | Selected value |
| --- | --- |
| colsample_bytree | 1 |
| gamma | 0.5 |
| learning_rate | 0.03 |
| max_depth | 3 |
| min_child_weight | 10 |
| n_estimators | 350 |
| reg_alpha | 0.5 |
| reg_lambda | 5 |
| subsample | 0.9 |

The canonical model uses these parameters with the invariant settings. Class weighting is not searched.

# Cross-Validation Results

Selected zero-based candidate **21**, rank 1. Mean CV ROC-AUC **0.787520370**, std **0.008418025**. Mean CV AP **0.561642645**, std **0.008710672**.

| Rank | Candidate | CV AUC | CV AP |
| --- | --- | --- | --- |
| 1 | 21 | 0.787520370 | 0.561642645 |
| 2 | 19 | 0.787416339 | 0.563835147 |
| 3 | 0 | 0.786576146 | 0.559736492 |
| 4 | 3 | 0.786173059 | 0.556879238 |
| 5 | 1 | 0.785988771 | 0.554904339 |

Candidate 19 has slightly higher AP, but candidate 21's AUC advantage exceeds machine precision, so the predefined AUC rule selects 21. No subjective override occurred. Scores labeled mean_test_* in sklearn's search CSV refer to **CV fold holdouts**, never the sealed project TEST partition. Fit/score timing measurements are recorded but do not influence selection.

# Final Train Metrics

| Metric | TRAIN |
| --- | --- |
| ROC-AUC | 0.811032912 |
| Average Precision | 0.602438553 |
| KS | 0.467348085 |
| Gini | 0.622065824 |
| Brier score | 0.127919859 |
| Log loss | 0.408690994 |
| Mean raw probability | 0.221109911 |
| Observed positive rate | 0.221190476 |
| TN | 15544 |
| FP | 811 |
| FN | 2823 |
| TP | 1822 |
| PRECISION | 0.691986327 |
| RECALL | 0.392249731 |
| SPECIFICITY | 0.950412718 |
| F1 | 0.500687002 |

# Final Validation Metrics

| Metric | VALIDATION |
| --- | --- |
| ROC-AUC | 0.784304404 |
| Average Precision | 0.556211932 |
| KS | 0.424438885 |
| Gini | 0.568608807 |
| Brier score | 0.135284871 |
| Log loss | 0.428826621 |
| Mean raw probability | 0.219568509 |
| Observed positive rate | 0.221111111 |
| TN | 3317 |
| FP | 188 |
| FN | 638 |
| TP | 357 |
| PRECISION | 0.655045872 |
| RECALL | 0.358793970 |
| SPECIFICITY | 0.946362340 |
| F1 | 0.463636364 |

**REFERENCE THRESHOLD = 0.50**, using raw_probability >= 0.50. It is diagnostic only, not optimized, a credit cut-off, business threshold or risk-band boundary. Confusion matrix order: [[TN, FP], [FN, TP]]. AP means Average Precision, not trapezoidal PR-AUC. KS = max(TPR − FPR); Gini = 2 × ROC-AUC − 1. Reuse Phase-4 metric functions.

# Train vs Validation Gap

TRAIN minus VALIDATION: AUC **0.026728508**, AP **0.046226620**, KS **0.042909200**. TRAIN Brier/log loss are lower by 0.007365013/0.020135627. There is measurable fitting optimism, but no near-perfect training score or validation collapse; validation AUC is also close to the winning CV mean. This does not prove absence of overfitting or future generalization.

The winning learning rate is at the low edge (0.03); min_child_weight=10, reg_alpha=0.5 and gamma=0.5 are at their upper searched values. Together with depth 3 and lambda 5, this favors restrained capacity. These are not pathological values; the search was not expanded or retuned after seeing validation results.

# Class-Imbalance Sensitivity

TRAIN counts: negative 16,355; positive 4,645; ratio **3.5209903121636166**. One temporary model uses that scale_pos_weight with the same selected parameters. It is fit on TRAIN and assessed only on VALIDATION.

| Metric | Canonical | Weighted |
| --- | --- | --- |
| ROC-AUC | 0.784304404 | 0.781754134 |
| Average Precision | 0.556211932 | 0.554985546 |
| KS | 0.424438885 | 0.421881160 |
| Gini | 0.568608807 | 0.563508269 |
| Brier score | 0.135284871 | 0.179989109 |
| Log loss | 0.428826621 | 0.544844855 |
| Mean raw probability | 0.219568509 | 0.422024017 |
| Observed positive rate | 0.221111111 | 0.221111111 |
| TN | 3317 | 2762 |
| FP | 188 | 743 |
| FN | 638 | 370 |
| TP | 357 | 625 |
| PRECISION | 0.655045872 | 0.456871345 |
| RECALL | 0.358793970 | 0.628140704 |
| SPECIFICITY | 0.946362340 | 0.788017118 |
| F1 | 0.463636364 | 0.528988574 |

Weighting raises recall from 0.3588 to 0.6281 but lowers precision/specificity and shifts mean raw probability from 0.2196 to 0.4220, versus observed prevalence 0.2211. AUC/AP decrease slightly; Brier/log loss worsen substantially. This illustrates a changed fitting objective and probability scale, not calibration or a lending-policy improvement. **The weighted sensitivity model is not canonical and is not serialized.** No resampling occurs.

# Baseline Comparison

Stored baseline version: logistic-baseline-1.0.0. Both models use the same project VALIDATION rows and transformed representation.

| Metric | Logistic | XGBoost | XGB − Logistic |
| --- | --- | --- | --- |
| ROC-AUC | 0.765638177 | 0.784304404 | 0.018666227 |
| Average Precision | 0.519684092 | 0.556211932 | 0.036527841 |
| KS | 0.405350576 | 0.424438885 | 0.019088309 |
| Gini | 0.531276353 | 0.568608807 | 0.037332454 |
| Brier score | 0.138791607 | 0.135284871 | -0.003506736 |
| Log loss | 0.441318621 | 0.428826621 | -0.012492000 |
| Mean raw probability | 0.219725065 | 0.219568509 | -0.000156556 |
| Observed positive rate | 0.221111111 | 0.221111111 | 0 |
| TN | 3323 | 3317 | -6 |
| FP | 182 | 188 | 6 |
| FN | 645 | 638 | -7 |
| TP | 350 | 357 | 7 |
| PRECISION | 0.657894737 | 0.655045872 | -0.002848865 |
| RECALL | 0.351758794 | 0.358793970 | 0.007035176 |
| SPECIFICITY | 0.948074180 | 0.946362340 | -0.001711840 |
| F1 | 0.458415193 | 0.463636364 | 0.005221170 |

Higher discrimination metrics favor XGBoost. Negative Brier/log-loss deltas indicate better raw-probability loss here, without proving calibration. Fixed-threshold precision/specificity are slightly lower and recall/F1 slightly higher.

# Paired Bootstrap Comparison

1,000 paired validation row resamples with replacement, seed 42. Both models receive identical indices in every replicate. All **1,000 succeeded**; **0 single-class skips**.

- Delta ROC-AUC percentile 95% CI: **[0.011856616, 0.026106355]**.
- Delta AP percentile 95% CI: **[0.022063804, 0.048515345]**.

Both intervals are positive on this validation sample. They condition on the fitted models and omit training, hyperparameter-selection and population-shift uncertainty. No customer probabilities are saved and TEST is never bootstrapped.

# Provisional Discrimination Status

**XGBOOST_LEADS_ON_VALIDATION_DISCRIMINATION**

Both validation point estimates (AUC and AP) exceed the baseline, satisfying the deterministic rule. This is not final production-model selection. final_model_selected=false; final selection is deferred to Phase-6 calibration analysis and later requirements.

# Native Feature Importance

| Transformed feature | Gain | Normalized gain | Split count |
| --- | --- | --- | --- |
| numeric__max_documented_delay | 684.840210 | 0.338041 | 31 |
| numeric__recent_documented_delay_flag | 466.965149 | 0.230496 | 29 |
| numeric__months_with_documented_delay | 150.493820 | 0.074285 | 104 |
| repayment__repayment_status_2005_09_status_1 | 104.348236 | 0.051507 | 34 |
| repayment__repayment_status_2005_09_status_2 | 37.988525 | 0.018751 | 63 |
| numeric__payment_amount_max | 32.181496 | 0.015885 | 41 |
| numeric__bill_amount_max | 28.933823 | 0.014282 | 23 |
| repayment__repayment_status_2005_06_status_-1 | 28.839813 | 0.014235 | 4 |
| repayment__repayment_status_2005_07_status_-1 | 25.912405 | 0.012790 | 10 |
| numeric__bill_amount_mean | 17.737389 | 0.008755 | 50 |

All 103 transformed names are represented; unused features receive zero. Native f0…f102 identifiers are validated and mapped to exact Phase-3 names/lineage. The three documented-delay summaries dominate normalized gain (approximately 64.28%). Their source fields are permitted pre-outcome history, not targets or demographics. This concentration is plausible behavior-history dependence, not evidence of causality or verified snapshot timing.

Gain is mean training loss reduction per split using a feature; normalized gain divides each feature's gain by the sum across features. It is not total model-performance contribution, SHAP, a per-customer reason or a regulatory adverse-action explanation. Correlated fields, split opportunities and category sparsity affect interpretation. Final explainability belongs to Phase 7.

# Probability Semantics

All probabilities are **raw / uncalibrated** model probabilities of next-month default payment. No calibrated PD, risk bands, internal score or lending decisions exist. Formal calibration belongs to Phase 6.

# Known Limitations

Historical Taiwan population, static cohorts, unresolved repayment codes, snapshot timing assumptions, demographic proxies and related feature families remain. No out-of-time validation or fairness/regulatory/production claim is supported.

The search is bounded, not exhaustive. A single project validation set and conditional bootstrap do not establish deployment generalization. Native gain is an aggregate diagnostic. Only the recorded Windows environment was exercised; cross-XGBoost/compiler/platform bitwise identity is not promised. Dense materialization is appropriate for this population but would need reconsideration at much larger scale. Transitive dependencies are not fully locked.

Canonical native artifact: `artifacts/models/xgboost-challenger-1.0.0_2900f0cfe341400daeffeed7b0ef212d0a317113a657a4fcf73c332caec755ef.json`; SHA-256: `2900f0cfe341400daeffeed7b0ef212d0a317113a657a4fcf73c332caec755ef`. TRAIN/VALIDATION reload probabilities match within 1e-12. The artifact is ignored and only trusted locally generated native models may be loaded. Aggregate manifests, metrics, comparison, importance and search results contain no customer-level outputs.

# Phase-6 Boundary

Phase 6 may assess calibration and final probability quality only after owner review, commit and an explicit request. Carry both models forward as comparison candidates, with the unweighted XGBoost challenger leading provisionally. Preserve validation/test discipline and account for prior model comparison when designing calibration selection. Phase 6 is NOT_STARTED. No calibration, SHAP, score, API, database or deployment was implemented.
