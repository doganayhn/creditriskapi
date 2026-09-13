# Feature engineering — financial_features_v1

# Modeling Population

All 30,000 verified UCI 350 customer records are eligible for splitting. No outlier/category-based row filtering is applied. Source identity and the Phase-2 manifest must agree before preparation. The target is default_next_month, a dataset-defined next-month event with the limitations already documented.

# Split Strategy

Sort by customer_id ascending, then use two sklearn stratified random splits with the centralized seed (42): 70% train / 30% temporary, then half temporary each for validation/test. This yields 21,000 / 4,500 / 4,500 records. Enforce unique non-null IDs, complete coverage, no customer overlap and both target classes in each partition. Config validates positive finite fractions summing to one. No chronological scoring cohorts exist; this is not out-of-time validation.

# Primary Feature Policy

Use the 19 explicitly allowlisted raw financial fields and 26 deterministic derived features. The engineered preprocessor input has 39 numeric and six categorical columns. Policy/version constants live in definitions.py; they are not free-form configuration toggles that could accidentally admit demographics.

# Excluded Fields

customer_id is an identifier; default_next_month is the target. Sex, age, education and marital_status are excluded from primary predictors as a project design choice, not a legal requirement or compliance/fairness claim.

# Fairness Review Fields

Each partition retains customer_id plus sex, age, education and marital_status in a separate review frame aligned with y and the matrix row order. Source demographics are not destroyed or recoded. Later fairness/subgroup analysis is not implemented in this phase.

# Raw Financial Features

- credit_limit
- repayment_status_2005_09
- repayment_status_2005_08
- repayment_status_2005_07
- repayment_status_2005_06
- repayment_status_2005_05
- repayment_status_2005_04
- bill_amount_2005_09
- bill_amount_2005_08
- bill_amount_2005_07
- bill_amount_2005_06
- bill_amount_2005_05
- bill_amount_2005_04
- payment_amount_2005_09
- payment_amount_2005_08
- payment_amount_2005_07
- payment_amount_2005_06
- payment_amount_2005_05
- payment_amount_2005_04

# Engineered Features

All calculations operate within a single customer's six recorded history months, never across customers or targets. Monetary amounts are NT dollars; normalized amounts are dimensionless. These ratios are not claimed to be regulatory utilization measures. Formula definitions and source lineage are also persisted in feature_manifest.json.

| Feature | Formula | Canonical source columns | Financial interpretation | Edge cases |
| --- | --- | --- | --- | --- |
| bill_amount_mean | mean(six bill amounts) | bill_amount_2005_09, bill_amount_2005_08, bill_amount_2005_07, bill_amount_2005_06, bill_amount_2005_05, bill_amount_2005_04 | Six-month bill-statement level or dispersion | Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| bill_amount_std | std(six bill amounts); population std, ddof=0 | bill_amount_2005_09, bill_amount_2005_08, bill_amount_2005_07, bill_amount_2005_06, bill_amount_2005_05, bill_amount_2005_04 | Six-month bill-statement level or dispersion | Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| bill_amount_min | min(six bill amounts) | bill_amount_2005_09, bill_amount_2005_08, bill_amount_2005_07, bill_amount_2005_06, bill_amount_2005_05, bill_amount_2005_04 | Six-month bill-statement level or dispersion | Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| bill_amount_max | max(six bill amounts) | bill_amount_2005_09, bill_amount_2005_08, bill_amount_2005_07, bill_amount_2005_06, bill_amount_2005_05, bill_amount_2005_04 | Six-month bill-statement level or dispersion | Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| payment_amount_mean | mean(six payment amounts) | payment_amount_2005_09, payment_amount_2005_08, payment_amount_2005_07, payment_amount_2005_06, payment_amount_2005_05, payment_amount_2005_04 | Six-month payment amount summary | Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| payment_amount_sum | sum(six payment amounts) | payment_amount_2005_09, payment_amount_2005_08, payment_amount_2005_07, payment_amount_2005_06, payment_amount_2005_05, payment_amount_2005_04 | Six-month payment amount summary | Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| payment_amount_max | max(six payment amounts) | payment_amount_2005_09, payment_amount_2005_08, payment_amount_2005_07, payment_amount_2005_06, payment_amount_2005_05, payment_amount_2005_04 | Six-month payment amount summary | Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| bill_to_limit_2005_09 | bill_amount_2005_09 / credit_limit | bill_amount_2005_09, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| bill_to_limit_2005_08 | bill_amount_2005_08 / credit_limit | bill_amount_2005_08, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| bill_to_limit_2005_07 | bill_amount_2005_07 / credit_limit | bill_amount_2005_07, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| bill_to_limit_2005_06 | bill_amount_2005_06 / credit_limit | bill_amount_2005_06, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| bill_to_limit_2005_05 | bill_amount_2005_05 / credit_limit | bill_amount_2005_05, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| bill_to_limit_2005_04 | bill_amount_2005_04 / credit_limit | bill_amount_2005_04, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| payment_to_limit_2005_09 | payment_amount_2005_09 / credit_limit | payment_amount_2005_09, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| payment_to_limit_2005_08 | payment_amount_2005_08 / credit_limit | payment_amount_2005_08, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| payment_to_limit_2005_07 | payment_amount_2005_07 / credit_limit | payment_amount_2005_07, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| payment_to_limit_2005_06 | payment_amount_2005_06 / credit_limit | payment_amount_2005_06, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| payment_to_limit_2005_05 | payment_amount_2005_05 / credit_limit | payment_amount_2005_05, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| payment_to_limit_2005_04 | payment_amount_2005_04 / credit_limit | payment_amount_2005_04, credit_limit | Statement/payment amount relative to given credit; not regulatory utilization | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. |
| bill_to_limit_mean | mean(six bill_amount_month / credit_limit ratios) | credit_limit, bill_amount_2005_09, bill_amount_2005_08, bill_amount_2005_07, bill_amount_2005_06, bill_amount_2005_05, bill_amount_2005_04 | Six-month normalized amount summary | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| bill_to_limit_max | max(six bill_amount_month / credit_limit ratios) | credit_limit, bill_amount_2005_09, bill_amount_2005_08, bill_amount_2005_07, bill_amount_2005_06, bill_amount_2005_05, bill_amount_2005_04 | Six-month normalized amount summary | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| payment_to_limit_mean | mean(six payment_amount_month / credit_limit ratios) | credit_limit, payment_amount_2005_09, payment_amount_2005_08, payment_amount_2005_07, payment_amount_2005_06, payment_amount_2005_05, payment_amount_2005_04 | Six-month normalized amount summary | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| payment_to_limit_max | max(six payment_amount_month / credit_limit ratios) | credit_limit, payment_amount_2005_09, payment_amount_2005_08, payment_amount_2005_07, payment_amount_2005_06, payment_amount_2005_05, payment_amount_2005_04 | Six-month normalized amount summary | Credit limit must be present and > 0; missing numerator stays NaN; negative and >1 ratios retained. Any missing source month makes the aggregate NaN for train-fitted imputation; no clipping. |
| months_with_documented_delay | sum(status > 0 over six months) | repayment_status_2005_09, repayment_status_2005_08, repayment_status_2005_07, repayment_status_2005_06, repayment_status_2005_05, repayment_status_2005_04 | Number of recorded history months with positive documented delay | NaN if any status missing; -2/-1/0 contribute no positive-delay evidence, not a no-risk meaning. |
| max_documented_delay | max(positive statuses), or 0 if none | repayment_status_2005_09, repayment_status_2005_08, repayment_status_2005_07, repayment_status_2005_06, repayment_status_2005_05, repayment_status_2005_04 | Largest documented positive delay level; code 9 is top-coded at nine or more months | NaN if any status missing; zero means no observed positive code, not proven absence of arrears. |
| recent_documented_delay_flag | 1 if repayment_status_2005_09 > 0 else 0 | repayment_status_2005_09 | Positive documented delay in the most recent source month | NaN if most recent status missing; no interpretation assigned to -2/0. |

# Repayment Status Treatment

The source month mapping makes September 2005 the most recent field. Preserve literal status_-2, status_-1, status_0 and positive tokens distinctly. UCI defines -1 as duly paid and positive values as delay levels, with 9 top-coded at nine or more months. The meanings of -2 and 0 remain unresolved. Their absence from positive-delay counts is not a declaration of no arrears or no risk. Inputs outside the source-documented/observed domain (-2 through 9) fail for investigation; within-domain tokens unseen in train are safely handled by the encoder. For missing status history, count/max summaries are NaN if any history month is missing; the recent flag requires only the recent status.

# Preprocessing

A guarded sklearn Pipeline contains a ColumnTransformer: numeric median imputation then StandardScaler; categorical constant status_missing imputation then OneHotEncoder(handle_unknown="ignore", sparse_output=True). Fit all steps on train only. Entirely null training numeric columns fail because no median exists. Constant features use sklearn's normal scaling behavior. Numeric processing is dense within its block; the combined output is converted to CSR float64. Negative bill values and ratios above one are retained before scaling; no clipping or winsorization occurs.

Unknown categories produce a zero one-hot block for that source field without changing width or fitting new categories. A missing token absent from training behaves likewise. Column names/order and types are checked before both fit and transform. Source-to-canonical lineage and all 103 real transformed names are persisted. See [sklearn SimpleImputer](https://scikit-learn.org/1.8/modules/generated/sklearn.impute.SimpleImputer.html) and [OneHotEncoder](https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.OneHotEncoder.html) for the pinned library behavior.

# Leakage Protections

Split before engineering or fitting. Financial engineering has no target input and accepts only the exact raw allowlist. It never mutates caller frames. The preprocessor rejects forbidden/extra fields and y arguments. The preparation lifecycle calls fit once on train, then transform on train/validation/test. Synthetic tests verify medians and scaler means against training-only statistics, vocabulary exclusion of holdout-only categories and unchanged training matrices after holdout distributions change. Identity/target/demographic values never appear in encoded feature names. No feature selector, target encoding, WoE, DTI or arbitrary risk score exists.

# Test-Set Discipline

The test set is sealed for later final evaluation. Phase 3 creates/transforms it and checks dimensions, finite values, target completeness/class counts and partition integrity only. No predictive model, test relationship analysis or performance-guided feature decision is performed. Future cross-validation must refit preprocessing on each training fold.

# Known Limitations

Temporal and demographic snapshot assumptions remain. Categorical preservation does not resolve source code semantics; excluding demographics does not remove proxies or establish fairness. Several aggregates are mathematically related and may be collinear; no target-driven pruning or modeling evidence exists yet. Complete-window missing propagation is conservative and may increase imputation needs for future incomplete inputs. Missing/nonpositive credit limits cannot be repaired by this pipeline. The fit helper relies on callers supplying train-only data; the project lifecycle and tests enforce this boundary. Serialized joblib objects are trusted-local artifacts only, never safe arbitrary uploads. Cross-platform/runtime bitwise reproducibility has not been demonstrated.
