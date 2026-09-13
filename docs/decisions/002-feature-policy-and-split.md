# Decision

Phase 3 adopts `sorted_id_two_stage_stratified_v1`: sort canonical rows by customer_id, then perform a seeded stratified random 70/15/15 train/validation/test split. Use the centralized project seed from config. Only train fits preprocessing. The test partition is reserved for future final evaluation.

The primary model inputs comprise 19 raw financial fields and 26 stateless derived financial features. Exclude customer_id (identifier), default_next_month (target), and sex/age/education/marital_status (demographic fields). Retain ID/demographics separately in aligned review frames. Demographic exclusion is a project design choice, not a legal requirement or evidence of regulatory compliance or fairness.

Treat each raw repayment status as a categorical literal token. Preserve -2, -1, 0 and positive codes distinctly; assign no invented meaning to -2/0. Only documented positive-delay levels inform delay summaries. Monthly bill/payment amounts and credit limit remain numeric. Preserve negative bills and ratios outside [0, 1]. Numeric inputs use train-median imputation then StandardScaler; categorical inputs use a fixed missing token then a train-learned OneHotEncoder with unknown-category ignore behavior.

# Context

Phase 2 established a static historical Taiwan credit-card sample with six monthly histories inside each row. It has no independent calendar scoring cohorts or per-customer scoring/outcome timestamps; true out-of-time validation is unsupported. The original raw schema includes unresolved repayment codes and demographic fields requiring a primary-model policy. No predictive model exists.

# Alternatives Considered

- Chronological splitting: unsupported by the verified data; monthly fields are not separate scoring cohorts.
- Unstratified random splitting: less reliable class representation, especially for smaller fixtures.
- Demographic primary predictors: deferred in favor of a financial/behavior-focused portfolio design; retain review fields for later subgroup analysis.
- Ordinal numeric repayment encoding: imposes unsupported geometry on -2/0; use separate categorical tokens instead.
- Full-data imputation/scaling/vocabulary fitting: prohibited leakage, not an acceptable shortcut.
- Broader feature search, clipping or target-driven feature selection: outside this phase's domain-defined scope.

# Consequences

Splits are reproducible from canonical data, ordering rule, configuration, seed and recorded library version. Customer IDs remain traceability-only. Stratification requires complete binary labels and unique non-null IDs; invalid populations fail instead of silently dropping rows.

Stateless feature engineering runs per partition. Missing source months propagate to affected aggregates, then train-fitted medians handle missing numeric values. Nonpositive/missing limits fail because ratio denominators are undefined. Entirely missing training numeric columns fail rather than inventing a median. Unseen repayment tokens produce an all-zero block for that field without expanding the training vocabulary.

The 26 features introduce related measures and possible collinearity; Phase 3 performs no target-driven selection or performance comparison. Scaling serves a shared numeric interface for future baseline/challenger models and does not train either. Demographic exclusion does not remove proxies or prove fairness. Holdout data may be transformed and structurally checked, never fitted or used to choose features.

See [feature_engineering.md](../feature_engineering.md) and [modeling_dataset.md](../modeling_dataset.md) for formulas, edge cases, APIs and measured matrix dimensions.
