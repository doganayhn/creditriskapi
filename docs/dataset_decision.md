# Dataset decision framework

Phase 2 finalized UCI Default of Credit Card Clients after official-source and workbook verification on 2026-09-13; see [ADR 001](decisions/001-dataset-selection.md). The original XLS has been downloaded and profiled locally. [Dataset card](dataset_card.md), [physical contract](data_contract.md) and [quality report](data_quality_report.md) contain verified findings.

The table below preserves the Phase-1 candidate assessment as historical context. Its pending items describe knowledge at Phase 1, not the current state of UCI verification. Sources were consulted on 2026-09-12; counts in this comparison are source metadata. Current UCI measurements are in the quality report.

| Criterion | UCI Default of Credit Card Clients | German Credit (Statlog) | Give Me Some Credit | Home Credit Default Risk (2018) |
| --- | --- | --- | --- | --- |
| Target suitability | Documented binary default payment; horizon to verify | Good/bad risk label; weaker PD semantics | Candidate delinquency target; dictionary verification pending | Repayment-risk competition; exact event definition pending |
| Observations | UCI reports 30,000 | UCI reports 1,000 | Not verified | Not verified |
| Feature richness | UCI reports 23 features; limit, payment and bill history | UCI reports 20 features; mixed credit/applicant attributes | Affordability/history coverage to verify | Relational/history coverage to verify |
| Class imbalance | Prevalence to measure in Phase 2 | Prevalence to measure | Unverified | Unverified |
| Missing data | UCI reports none; inspect sentinels/codes later | UCI reports none; inspect category semantics later | Missingness unverified | Missingness unverified |
| Temporal information | Monthly histories, April–September 2005; no demonstrated multi-cohort temporal split | No demonstrated event chronology | Cut-off/timestamps unverified | Relative dates/cohorts require verification |
| Leakage risks | Outcome/ID exclusion; payment timing | Label mapping and credit-history timing | Outcome-proxy and scoring-time checks needed | Join/granularity and scoring-time checks needed |
| Interpretability | Financial history suitable; coded values need care | Compact, mixed coded features | Assess dictionary before inclusion | Assess source tables before aggregation |
| Accessibility | UCI direct public source | UCI direct public source | Kaggle access/rules must be checked | Kaggle access/rules must be checked |
| Licensing | UCI lists CC BY 4.0; preserve attribution | UCI lists CC BY 4.0; preserve attribution | Not verified; do not assume redistribution rights | Not verified; do not assume redistribution rights |
| Complexity (engineering judgment) | Moderate; spreadsheet/schema checks | Low; small mixed table | Pending dictionary; potential alternative | Potentially high if multi-table scope confirmed |
| Portfolio suitability (judgment) | Preferred manageable starting point | Useful small alternative; weak default semantics | Alternative pending evidence | Richer extension pending evidence and scope |

Sources: [UCI credit-card dataset](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients), [UCI German Credit](https://archive.ics.uci.edu/dataset/144/statloggermancreditdata), [Give Me Some Credit data](https://www.kaggle.com/c/GiveMeSomeCredit/data), [Home Credit data](https://www.kaggle.com/c/home-credit-default-risk/data). Kaggle data pages returned no readable dictionary during this review; their statistics and detailed semantics are intentionally unverified. Do not substitute the separate Home Credit Model Stability competition.

The Phase-1 recommendation favored UCI Default of Credit Card Clients because documented access, scale and payment history support a tractable baseline/challenger project. Phase 2 confirmed its identity and physical contents and adopted that recommendation. This engineering choice does not demonstrate future lending performance. Phase 3 adopted [ADR 002](decisions/002-feature-policy-and-split.md): demographics are excluded from primary predictors and retained separately for review; published features are not automatically eligible predictors.

Phase 2 verified identity, DOI, license/attribution, original file, hash, rows, headers/types, binary target, class balance, duplicates, true nulls and observed category codes. The workbook establishes a next-month label but not a detailed default adjudication rule. Undocumented codes remain unresolved. Income and employment are absent from the verified schema; DTI cannot be derived from it. Monthly history columns do not provide multiple calendar scoring cohorts. Do not claim out-of-time validation or true event-window reconstruction from this static snapshot. Phase 1 made no contradictory factual claim requiring its completion report to be changed.
