# Dataset decision framework

No dataset was present at initialization; none has been downloaded or ingested. This is a provisional recommendation, not final selection or schema verification. Source metadata was consulted on 2026-09-12. Exact counts below are published metadata, not measurements of local data.

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

Recommend UCI Default of Credit Card Clients for Phase 2 because documented access, scale and payment history support a tractable baseline/challenger project. This is an engineering inference from the metadata. It does not demonstrate future lending performance. Sensitive demographic fields require an explicit eligibility decision; published features are not automatically approved predictors.

Phase 2 must verify source/version, file hash, attribution requirements, actual rows, headers and types, target mapping/horizon, class balance, duplicates, nulls/sentinels, unusual categorical codes, scoring-time availability and cohort structure. Confirm whether income/employment exist before proposing affordability ratios. Record final selection in an ADR only when it is actually made. Do not claim out-of-time validation or true event-window reconstruction from a static snapshot.
