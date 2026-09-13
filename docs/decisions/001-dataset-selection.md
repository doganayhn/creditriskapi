# Decision

Select UCI **Default of Credit Card Clients**, dataset 350, DOI [10.24432/C55S3H](https://doi.org/10.24432/C55S3H), as the V1 dataset. Decision made during Phase 2 on 2026-09-13 following official-source and original-workbook verification.

# Context

An accessible public dataset with a binary credit outcome and interpretable financial history is needed for reproducible educational risk-model development. No real lending data or modern banking event stream is available in this project.

# Alternatives Considered

- UCI Default of Credit Card Clients: verified public source, documented financial history and manageable size.
- German Credit: smaller benchmark; good/bad risk classes have weaker default-event semantics.
- Give Me Some Credit: potential delinquency alternative; detailed source/access verification remains incomplete.
- Home Credit Default Risk (2018): potential richer alternative with greater data-preparation complexity; source/access details remain unverified here.

The Phase-1 comparison remains in [dataset_decision.md](../dataset_decision.md); only the selected UCI source was acquired in Phase 2.

# Decision Rationale

The official [UCI description](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) and original XLS together establish provenance, financial meanings, monthly history and a next-month binary outcome. The measured 30,000 rows permit a tractable future baseline/challenger comparison. UCI lists CC BY 4.0; preserve attribution. The original file is retained unchanged locally with a pinned SHA-256.

# Advantages

Direct official acquisition, modest local storage requirements, clear source-to-canonical traceability, a real binary label and six months of credit-related history. No paid connector, API account or notebook is required for acquisition and profiling.

# Limitations

Historical Taiwan credit-card clients and a single static snapshot do not represent modern lending populations or multiple calendar scoring cohorts. The source does not define a regulatory default threshold. Several category codes are undocumented, and demographics require review. There is no verified income/employment field. No regulatory representativeness is claimed.

# Consequences

V1 estimates the dataset's next-month default-payment label, not 12-month or regulatory PD. No true out-of-time split can be justified from this workbook. Phase 3 must decide feature eligibility and code treatment without altering raw bytes. Other datasets require a new explicit decision; acquisition fails on a changed source hash rather than silently switching versions. Only aggregate metadata and synthetic fixtures may enter Git under this phase's scope; customer records remain ignored.
