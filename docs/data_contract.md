# Conceptual data contract

Status: Phase-1 conceptual contract, not an executable schema. No local dataset-native columns have been verified. Phase 2 must map and validate the selected source; the configured target remains null.

| Family | Possible concepts | Category now | Contract considerations for Phase 2 |
| --- | --- | --- | --- |
| Applicant / affordability | Income, debt, employment | Conceptual; availability not confirmed | Define gross/net income, frequency, currency, debt stock vs service flow and employment encoding |
| Credit exposure | Balance, limit, utilization, account count | Conceptual; dataset-native mapping pending | Confirm units, account/customer granularity, observation time and meaning of negative values |
| Payment history | Delinquency, DPD history, missed payments | Conceptual; dataset-native mapping pending | Distinguish days/months/categorical status, ordered months, unknown codes and pre-outcome cut-off |
| Derived | DTI, utilization ratios, delinquency aggregates | Derived proposal; not implemented | Require verified inputs, aligned units/windows, denominator-zero policy and documented missingness |
| Unsupported inputs | Any concept absent from chosen source | Unavailable / not yet confirmed | Do not fabricate or silently substitute fields |

Dataset-native means a verified field in the selected source, not a conceptual name. UCI metadata is evidence for candidate assessment, not final column mapping. A bill amount is not automatically total debt, and a bill/limit ratio is not automatically regulatory utilization. DTI requires a documented, consistent definition of periodic debt obligations and income.

The future row contract must specify entity key (excluded from predictors), one-row granularity, target role and binary mapping, feature roles/types/units, allowed categories/ranges, missing/sentinel handling, duplicate policy and scoring-time provenance. Separate predictors from target and metadata. Preserve raw source values; document transformations and rejection counts. Demographics and proxies require an explicit inclusion/exclusion rationale. Unexpected columns or target values must fail validation or enter an explicit documented quarantine policy, never silently alter the feature set.
