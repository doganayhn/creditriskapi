# Dataset card — Default of Credit Card Clients

Phase-2 source/quality findings below remain unchanged. Phase 3 has now implemented the primary feature policy and dataset preparation in [ADR 002](decisions/002-feature-policy-and-split.md) and [feature_engineering.md](feature_engineering.md); references below to Phase-3 decisions describe the original Phase-2 handoff.

# Dataset Identity

Official name: Default of Credit Card Clients. UCI dataset ID: 350. Selected as V1 under [ADR 001](decisions/001-dataset-selection.md).

# Source

[official UCI description](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients), verified 2026-09-13. Original download: [official UCI ZIP](https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip), containing only `default of credit card clients.xls`. No mirror or third-party dataset was used. Local acquisition timestamp: 2026-09-13T12:45:06.069006+00:00.

# DOI

[10.24432/C55S3H](https://doi.org/10.24432/C55S3H).

# License

UCI lists [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Preserve attribution and indicate changes. This project retains source bytes unchanged; canonical column renaming and aggregate profiling are the project's adaptations. Raw customer records are excluded from Git by project policy.

# Attribution

Yeh, I. (2009). Default of Credit Card Clients [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C55S3H.

UCI lists I-Cheng Yeh as creator. Its introductory research paper is attributed to I. Yeh and Che-hui Lien (2009); the repository donation date is 2016-01-25. These publication/donation dates are distinct from the data-history period.

# Historical Period

Repayment status, bill statements and payment amounts cover April through September 2005. The workbook labels the outcome as next month. October 2005 is an inference from that sequence, not a verified per-customer timestamp; no exact scoring/event dates are supplied.

# Geography / Population

UCI describes credit-card default payments in Taiwan. This is a historical sample of credit-card clients, not a verified representative sample of current applicants, countries or banking products. Sampling and point-in-time snapshot details are insufficient to make representativeness claims.

# Target Definition

Original: `default payment next month`; canonical: `default_next_month`. Class 0 means no default payment; class 1 means default payment in the next month. UCI supplies the binary meaning and the workbook supplies the horizon. The consulted source does not establish 12-month PD, Basel/IFRS 9 default, 90+ DPD default or a detailed adjudication rule.

# Feature Families

Customer identifier; credit limit; sex/education/marital status/age; six monthly repayment-status fields; six bill-statement amounts; six payment amounts; target. Monetary units are NT dollars. Income, employment and debt-service flows are absent. No derived features exist. See [physical contract](data_contract.md) for every source/canonical field.

# Measured Dataset Size

30,000 records; 25 raw and 25 canonical columns (23 explanatory fields, ID and target). The XLS has 5,539,328 bytes. Its two header rows are excluded from record counts. SHA-256: `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`. The hash is locally measured from UCI bytes, not a publisher-supplied checksum. Aggregate provenance: [dataset_manifest.json](../data/metadata/dataset_manifest.json).

# Class Distribution

0: 23,364; 1: 6,636; positive prevalence: 22.12%. This is descriptive prevalence, not calibrated model output.

# Known Data Quality Issues

No measured true nulls, exact duplicate rows or duplicate IDs. Repayment -2/0, education 0/5/6 and marital status 0 are not defined by the consulted official description. Negative bills and extreme monetary values are retained. See [quality report](data_quality_report.md) and [aggregate JSON](../data/metadata/data_quality_summary.json) for measured counts, distributions and methods.

# Sensitive / Demographic Fields

Sex, age, education and marital status require review. Phase 2 neither includes nor excludes them from a model; Phase 3 decides primary-model eligibility and fairness-analysis retention. No fairness/legal/regulatory compliance is claimed.

# Temporal Limitations

HISTORICAL FEATURES WITHIN A ROW are not OUT-OF-TIME MODEL VALIDATION. Six monthly history columns per family do not create six independent calendar scoring cohorts. The workbook contains no scoring/event timestamps or multiple dated cohorts supporting true chronological train/test splitting. Random/stratified evaluation, if later used, must be labeled accordingly. True observation/performance-window reconstruction is unsupported.

# Generalization Limitations

Historical Taiwan credit-card behavior, borrower-selection effects, limited provenance detail and unresolved category meanings constrain extrapolation. No modern banking event stream, regulatory representativeness, causal explanation or real lending readiness is demonstrated.

# Intended Use

Educational / portfolio credit-risk ML system. Reproducible descriptive profiling now; future explicitly authorized modeling under the documented limitations.

# Non-Intended Use

- Real lending decisions.
- Regulatory risk estimation.
- Real bank underwriting.
- Legal credit decisions.
