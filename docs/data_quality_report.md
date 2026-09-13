# Data quality report — UCI 350

Phase-2 source/quality findings below remain unchanged. Phase 3 has now implemented the primary feature policy and dataset preparation in [ADR 002](decisions/002-feature-policy-and-split.md) and [feature_engineering.md](feature_engineering.md); references below to Phase-3 decisions describe the original Phase-2 handoff.

Measured by `python -m credit_risk.data.quality` from the original XLS. Raw SHA-256: `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`. Full precision and all column profiles are in [data_quality_summary.json](../data/metadata/data_quality_summary.json). Markdown numbers below are rounded only for display; the DataFrame and source values are unchanged.

# Dataset Dimensions

- Customer records: 30,000.
- Raw/canonical columns: 25 / 25 (ID + 23 candidate explanatory fields + target).
- Original sheet: 30,002 rows including two validated header rows.
- Canonical memory including index: 6,750,132 bytes, using nullable Int64 with pandas 2.3.3.

# Target Distribution

`default_next_month` preserves original labels: 0 = no default payment next month; 1 = default payment next month. Negative: 23,364 (77.88%); positive: 6,636 (22.12%). All labels are present and in {0, 1}. This is the observed cohort's label prevalence, not a modern population PD or model performance.

# Missing Values

Measured true null cells: 0. Every column has 0 missing values (0%). This agrees with UCI's declared absence of missing values but does not resolve special/undocumented codes. No imputation was performed.

# Duplicate Analysis

Exact duplicate rows, including ID and target: 0. Duplicate non-null IDs: 0. Counts mean occurrences after the first. These are separate measures; unique IDs do not prove that borrowers cannot recur under different IDs. No deduplication was performed.

# Identifier Quality

`customer_id` ranges from 1 to 30,000, with 30,000 distinct non-null values and 0 missing IDs. It is an IDENTIFIER for traceability and must never become a predictive feature.

# Repayment Status Findings

UCI documents -1 and 1–9; observed -2 and 0 are undocumented in the consulted official description. The following are exact value counts, not recoded categories. Code 9 is documented but absent. Months are source-backed historical fields within each row.

| Month | -2 | -1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2005-09 | 2759 | 5686 | 14737 | 3688 | 2667 | 322 | 76 | 26 | 11 | 9 | 19 | 0 |
| 2005-08 | 3782 | 6050 | 15730 | 28 | 3927 | 326 | 99 | 25 | 12 | 20 | 1 | 0 |
| 2005-07 | 4085 | 5938 | 15764 | 4 | 3819 | 240 | 76 | 21 | 23 | 27 | 3 | 0 |
| 2005-06 | 4348 | 5687 | 16455 | 2 | 3159 | 180 | 69 | 35 | 5 | 58 | 2 | 0 |
| 2005-05 | 4546 | 5539 | 16947 | 0 | 2626 | 178 | 84 | 17 | 4 | 58 | 1 | 0 |
| 2005-04 | 4895 | 5740 | 16286 | 0 | 2766 | 184 | 49 | 13 | 19 | 46 | 2 | 0 |

# Education Category Findings

Documented 1 graduate school, 2 university, 3 high school, 4 others; 0/5/6 are undocumented. No categories merged.

| Code | Count | Documented |
| --- | --- | --- |
| 0 | 14 | No |
| 1 | 10,585 | Yes |
| 2 | 14,030 | Yes |
| 3 | 4,917 | Yes |
| 4 | 123 | Yes |
| 5 | 280 | No |
| 6 | 51 | No |

# Marital Status Findings

Documented 1 married, 2 single, 3 others; 0 is undocumented. No categories merged.

| Code | Count | Documented |
| --- | --- | --- |
| 0 | 54 | No |
| 1 | 13,659 | Yes |
| 2 | 15,964 | Yes |
| 3 | 323 | Yes |

# Numeric Anomalies

Age and credit limit have zero null/nonpositive values. Age ranges from 21 to 79; no arbitrary upper-age rejection is applied. Credit limits range from NT$10,000 to NT$1,000,000. IQR flags are descriptive review flags, not invalid records. No deletion, clipping, capping, winsorization, log transformation, normalization or standardization occurred.

Statistics use sample standard deviation (ddof=1), linear quantiles and Tukey fences Q1 − 1.5×IQR / Q3 + 1.5×IQR. Encoded categories and IDs do not have a meaningful continuous financial interpretation. The table covers age, limit and monetary fields only.

| Field | Min | P01 | Q1 | Median | Q3 | P99 | Max | Mean | Sample SD | Outside IQR fences |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| credit_limit | 10,000 | 10,000 | 50,000 | 140,000 | 240,000 | 500,000 | 1,000,000 | 167,484.32 | 129,747.66 | 167 |
| age | 21 | 22 | 28 | 34 | 41 | 60 | 79 | 35.49 | 9.22 | 272 |
| bill_amount_2005_09 | -165,580 | -81 | 3,558.75 | 22,381.5 | 67,091 | 350,110.68 | 964,511 | 51,223.33 | 73,635.86 | 2400 |
| bill_amount_2005_08 | -69,777 | -200 | 2,984.75 | 21,200 | 64,006.25 | 337,495.28 | 983,931 | 49,179.08 | 71,173.77 | 2395 |
| bill_amount_2005_07 | -157,264 | -200 | 2,666.25 | 20,088.5 | 60,164.75 | 325,030.39 | 1,664,089 | 47,013.15 | 69,349.39 | 2469 |
| bill_amount_2005_06 | -170,000 | -212.02 | 2,326.75 | 19,052 | 54,506 | 304,997.27 | 891,586 | 43,262.95 | 64,332.86 | 2622 |
| bill_amount_2005_05 | -81,334 | -232.01 | 1,763 | 18,104.5 | 50,190.5 | 285,868.33 | 927,171 | 40,311.4 | 60,797.16 | 2725 |
| bill_amount_2005_04 | -339,603 | -331.03 | 1,256 | 17,071 | 49,198.25 | 279,505.06 | 961,664 | 38,871.76 | 59,554.11 | 2693 |
| payment_amount_2005_09 | 0 | 0 | 1,000 | 2,100 | 5,006 | 66,522.18 | 873,552 | 5,663.58 | 16,563.28 | 2745 |
| payment_amount_2005_08 | 0 | 0 | 833 | 2,009 | 5,000 | 76,651.02 | 1,684,259 | 5,921.16 | 23,040.87 | 2714 |
| payment_amount_2005_07 | 0 | 0 | 390 | 1,800 | 4,505 | 70,000 | 896,040 | 5,225.68 | 17,606.96 | 2598 |
| payment_amount_2005_06 | 0 | 0 | 296 | 1,500 | 4,013.25 | 67,054.44 | 621,000 | 4,826.08 | 15,666.16 | 2994 |
| payment_amount_2005_05 | 0 | 0 | 252.5 | 1,500 | 4,031.5 | 65,607.56 | 426,529 | 4,799.39 | 15,278.31 | 2945 |
| payment_amount_2005_04 | 0 | 0 | 117.75 | 1,500 | 4,000 | 82,619.05 | 528,666 | 5,215.5 | 17,777.47 | 2958 |

# Billing / Payment Findings

Negative bills are retained and are not automatically invalid: credits/overpayments are possible explanations, not confirmed source semantics. Negative payment amounts are absent. Large amounts are reported, not removed or used to design target-driven features.

| Month | Negative bill cells | Negative payment cells |
| --- | --- | --- |
| 2005-09 | 590 | 0 |
| 2005-08 | 669 | 0 |
| 2005-07 | 655 | 0 |
| 2005-06 | 675 | 0 |
| 2005-05 | 655 | 0 |
| 2005-04 | 688 | 0 |

# Sensitive / Demographic Fields

Sex, age, education and marital status are DEMOGRAPHIC_REVIEW_REQUIRED. Age distribution appears above and category distributions are reported without target stratification. Source sex codes 1 and 2 have counts 11,888 and 18,112 respectively. Phase 3 must decide primary-model eligibility and fairness-analysis retention; this profiling is not a fairness assessment or legal-compliance claim.

# Unresolved Questions

- What do repayment -2/0, education 0/5/6 and marital status 0 mean in the original collection process?
- What exact operational rule produced the default-payment outcome? The next-month horizon is stated, but no regulatory/DPD threshold is defined.
- What are the precise feature-snapshot cut-offs and demographic update times? No event-level timestamps are present.
- Are negative bills credits/overpayments, and what explains large bills/payments? Plausible explanations are not verified facts.
- Do unique IDs guarantee distinct people? The workbook alone cannot establish this beyond source record identifiers.

# Phase-3 Recommendations

Resolve or explicitly document unsupported codes; choose feature eligibility and demographic/fairness retention; assess duplicate/entity strategy and numeric treatment only after setting a leakage-safe evaluation design. Keep ID/target out of predictors. If preprocessing is later fitted, fit only on training partitions. Do not derive DTI without income/debt-service data. Use an honestly described non-temporal split if no new verified cohort information exists. These are recommendations only; none is implemented.

# Per-Column Completeness and Cardinality

Unique counts exclude true nulls. Integral dtype does not imply that encoded categories are continuous quantities.

| Column | Dtype | Missing | Missing % | Unique |
| --- | --- | --- | --- | --- |
| customer_id | Int64 | 0 | 0.0 | 30000 |
| credit_limit | Int64 | 0 | 0.0 | 81 |
| sex | Int64 | 0 | 0.0 | 2 |
| education | Int64 | 0 | 0.0 | 7 |
| marital_status | Int64 | 0 | 0.0 | 4 |
| age | Int64 | 0 | 0.0 | 56 |
| repayment_status_2005_09 | Int64 | 0 | 0.0 | 11 |
| repayment_status_2005_08 | Int64 | 0 | 0.0 | 11 |
| repayment_status_2005_07 | Int64 | 0 | 0.0 | 11 |
| repayment_status_2005_06 | Int64 | 0 | 0.0 | 11 |
| repayment_status_2005_05 | Int64 | 0 | 0.0 | 10 |
| repayment_status_2005_04 | Int64 | 0 | 0.0 | 10 |
| bill_amount_2005_09 | Int64 | 0 | 0.0 | 22723 |
| bill_amount_2005_08 | Int64 | 0 | 0.0 | 22346 |
| bill_amount_2005_07 | Int64 | 0 | 0.0 | 22026 |
| bill_amount_2005_06 | Int64 | 0 | 0.0 | 21548 |
| bill_amount_2005_05 | Int64 | 0 | 0.0 | 21010 |
| bill_amount_2005_04 | Int64 | 0 | 0.0 | 20604 |
| payment_amount_2005_09 | Int64 | 0 | 0.0 | 7943 |
| payment_amount_2005_08 | Int64 | 0 | 0.0 | 7899 |
| payment_amount_2005_07 | Int64 | 0 | 0.0 | 7518 |
| payment_amount_2005_06 | Int64 | 0 | 0.0 | 6937 |
| payment_amount_2005_05 | Int64 | 0 | 0.0 | 6897 |
| payment_amount_2005_04 | Int64 | 0 | 0.0 | 6939 |
| default_next_month | Int64 | 0 | 0.0 | 2 |
