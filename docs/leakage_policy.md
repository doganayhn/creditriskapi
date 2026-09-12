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

Static public data often lack enough timestamps to reconstruct observation/performance windows. Random or stratified splitting can be a documented compromise, never called true out-of-time validation. Phase 2 investigates source semantics; Phase 3 implements split/feature controls. None of these pipelines exists in Phase 1.
