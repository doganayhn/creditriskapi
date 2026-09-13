# Credit-risk problem definition

Business objective: estimate borrower credit-default risk using information theoretically available at scoring time. ML objective: binary classification producing an estimated Probability of Default (PD).

V1 uses UCI Default of Credit Card Clients (350). The original workbook target is `default payment next month`, mapped unchanged to `default_next_month`. UCI describes 0 as no default payment and 1 as default payment. The horizon is the next month, as specified by the workbook header; no numeric threshold for adjudicating default is documented in the consulted source. This means a dataset-defined next-month default-payment event, not 12-month PD, Basel default, IFRS 9 default or 90+ DPD default. The configuration target is now `default_next_month`.

Sources: [official UCI metadata](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) and its [original workbook archive](https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip), verified 2026-09-13. See [dataset card](dataset_card.md) for attribution and measured population details.

Conceptual time order: observation window → scoring cut-off → performance window → outcome. Here, source-documented payment/bill/status histories cover April–September 2005 within each customer row. The intended scoring point is after this history and before the next-month outcome; interpreting that following month as October 2005 is a calendar inference, not a separate verified event timestamp. The workbook contains no per-row calendar scoring/outcome timestamps or distinct scoring cohorts to support a true chronological train/test split. Historical features within a row are not out-of-time validation.

Admissible candidates must be theoretically observable at that intended cut-off. Exclude identifiers and the outcome from predictors. Limit/demographic snapshot timing and undocumented repayment codes require explicit treatment decisions. Static historical snapshots do not establish deployability, full event-window reconstruction or true out-of-time evaluation.

The intended PD is conditional on an eligible population and dataset-defined event/horizon. Raw probability requires evaluation before being reported as a credible PD; calibration is a future empirical choice. Policy decisions remain separate. Financial concepts in the glossary describe the domain, not implemented models or verified dataset fields.

Future evaluation should include discrimination, probability quality and calibration with uncertainty and comparable splits; accuracy alone is insufficient. Population shift, selection of existing borrowers, historical context and sensitive attributes constrain generalization. No lending authority or compliance claim is made.
