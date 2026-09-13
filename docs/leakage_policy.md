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

Static public data often lack enough timestamps to reconstruct observation/performance windows. Random or stratified splitting can be a documented compromise, never called true out-of-time validation. Phase 2 performs semantic review only; Phase 3 will implement split/feature controls. No modeling split or preprocessing pipeline exists yet.

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

The verified workbook contains no recovery/charge-off/collection-outcome columns. Never add such post-event fields as predictors. Six history months within each row do not create six calendar scoring cohorts. The snapshot cannot support a true chronological holdout or reconstruction of individual cut-offs; document any future random/stratified split honestly. Retain all source records and codes in Phase 2; no future-feature set is finalized.
