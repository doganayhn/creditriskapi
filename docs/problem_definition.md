# Credit-risk problem definition

Business objective: estimate borrower credit-default risk using information theoretically available at scoring time. ML objective: binary classification producing an estimated Probability of Default (PD).

Conceptually `y = 0` means non-default and `y = 1` means default. The actual dataset event, label mapping, population and horizon must be verified in Phase 2. A public dataset's default-payment label or good/bad classification is not automatically regulatory default, 90 DPD, or 12-month PD. The configuration target is deliberately unset.

Conceptual time order: observation window → scoring cut-off → performance window → outcome. Admissible inputs are historical applicant, exposure and payment information observable at that cut-off. Exclude identifiers as predictors, outcomes, future balances, recoveries and post-default collections. Static historical snapshots do not establish deployability, full observation-window reconstruction or true out-of-time evaluation.

The intended PD is conditional on an eligible population and dataset-defined event/horizon. Raw probability requires evaluation before being reported as a credible PD; calibration is a future empirical choice. Policy decisions remain separate. Financial concepts in the glossary describe the domain, not implemented models or verified dataset fields.

Future evaluation should include discrimination, probability quality and calibration with uncertainty and comparable splits; accuracy alone is insufficient. Population shift, selection of existing borrowers, historical context and sensitive attributes constrain generalization. No lending authority or compliance claim is made.
