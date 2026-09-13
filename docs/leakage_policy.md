# Leakage policy

Only predictors theoretically available at the scoring cut-off are eligible. Record provenance and time semantics for each field; uncertainty means investigate or exclude, not assume eligibility.

| Leakage type | Prohibited example | Required future control |
| --- | --- | --- |
| Target leakage | Target label, copied label, full-dataset default rate by customer | Explicit target/metadata exclusion; fold-safe target encoding if ever authorized |
| Future information | Next month's missed payment used to predict that month | Verify feature timestamps and cut-off |
| Post-default variables | Recovery amount, charge-off date, collection outcome after the event | Exclude post-outcome attributes |
| Preprocessing leakage | Imputing using train + test median | Fit imputers, scalers, encoders and feature selectors on training only |
| Train/test contamination | Same borrower or duplicate record across splits; test-driven tuning | Entity/duplicate-aware splitting and untouched final test set |
| Feature-engineering leakage | Aggregate includes future transactions or validation labels | Cut-off-safe aggregation; learned features fit within training folds |

During cross-validation, fit all learned transformations inside each training fold; validation/test receive transform only. Training-only resampling must occur after splitting. Calibration and threshold fitting must use designated non-test data; final test labels never select models, features or policy. Dataset-wide schema checks must not become data-driven fitted preprocessing.

Static public data often lack enough timestamps to reconstruct observation/performance windows. Random or stratified splitting is a documented compromise, never true out-of-time validation. Phase 2 performed semantic review; Phase 3 implements the split/feature controls described below.

## UCI 350 semantic/timing review

The question is whether information could theoretically be known at the intended scoring time before the outcome. Correlation with the target is not a definition of leakage. This review covers all 25 fields through the complete mapping in [data_contract.md](data_contract.md).

| Source fields | Canonical fields | Classification | Timing/eligibility assessment |
| --- | --- | --- | --- |
| ID | customer_id | IDENTIFIER | Retain for traceability; never a predictive feature |
| default payment next month | default_next_month | TARGET | Following-month outcome; never a predictor or input to full-data feature construction |
| LIMIT_BAL | credit_limit | PRE_OUTCOME_CANDIDATE | Available-credit snapshot is conceptually known at scoring; source does not provide update timestamps, so this is an assumption, not verified point-in-time reconstruction |
| SEX, EDUCATION, MARRIAGE, AGE | sex, education, marital_status, age | DEMOGRAPHIC_REVIEW_REQUIRED | Snapshot timing is assumed; Phase 3 must decide primary-model eligibility and retention for fairness analysis |
| PAY_0, PAY_2–PAY_6 | repayment_status_2005_09 through repayment_status_2005_04 | REQUIRES_INVESTIGATION | Historical periods precede intended next-month outcome, but -2/0 meanings are undocumented; pre-outcome candidates once semantics/eligibility are resolved |
| BILL_AMT1–BILL_AMT6 | bill_amount_2005_09 through bill_amount_2005_04 | PRE_OUTCOME_CANDIDATE | Source-documented past statements; negative balances need domain review, not automatic deletion |
| PAY_AMT1–PAY_AMT6 | payment_amount_2005_09 through payment_amount_2005_04 | PRE_OUTCOME_CANDIDATE | Source-documented payments during past months; do not append subsequent payments when predicting the existing label |

The verified workbook contains no recovery/charge-off/collection-outcome columns. Never add such post-event fields as predictors. Six history months within each row do not create six calendar scoring cohorts. The snapshot cannot support a true chronological holdout or reconstruction of individual cut-offs. Phase 2 retained all source records and codes. Its review table above records the semantic assessment; Phase 3 resolves modeling treatment through [ADR 002](decisions/002-feature-policy-and-split.md), without inventing unresolved code meanings.

## Implemented Phase-3 controls

Sort unique IDs, then stratify 70/15/15 using the centralized seed. Enforce complete row coverage, no customer overlap and binary labels. No row is silently removed. IDs and targets are never predictors; sex/age/education/marital status stay only in aligned review frames.

Stateless engineering accepts exactly the raw financial allowlist and has no target input. Repayment codes are literal categories; only documented positive levels feed delay summaries. No target-driven feature selection or clipping occurs. The sklearn schema guard rejects extra/forbidden columns and y arguments. Numeric medians/scaler statistics and categorical vocabulary fit only on the training branch; holdouts receive transform only. Tests contrast train with extreme holdout distributions and unseen categories, and spy on the sole fit call.

The Phase-3 test processing remains structural/finite/target-count checks only. Phase 4 now fits one baseline on TRAIN and evaluates TRAIN/VALIDATION; its modeling consumer discards TEST before engineering or transformation and exposes no test matrix or labels. TEST remains sealed: no test probabilities, predictions, performance metrics or selection decisions occur. Serialization checks use training inputs only. Review fields remain available for future fairness work; exclusion is not a guarantee against proxy effects or legal compliance. Future cross-validation must fit preprocessing independently inside each training fold.

## Implemented Phase-5 CV and comparison controls

The challenger reuses the sealed modeling consumer. Its separate CV input loader returns engineered TRAIN rows only. Each candidate/fold Pipeline fits a fresh preprocessor on fold-training rows; the full-TRAIN fitted preprocessor never enters CV. Synthetic tests inspect fitted medians, unseen-category vocabulary and actual fold membership. The primary selection metric is mean fold ROC-AUC; project VALIDATION is not supplied for fitting or early stopping.

The canonical XGBoost model is then fit on full TRAIN using the verified Phase-3 representation. Project VALIDATION supports final comparison, paired bootstrap and a separate weighted sensitivity diagnostic. Native serialization is checked on TRAIN and VALIDATION without fitting. TEST is never predictively evaluated or used in those decisions. All relevant artifacts record test_set_evaluated=false. Paired bootstrap uses the same validation indices for both models and does not export customer predictions. Phase-6 calibration is not implemented.
