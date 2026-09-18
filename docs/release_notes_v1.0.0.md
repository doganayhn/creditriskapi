# v1.0.0 release notes (prepared for owner review)

Educational Credit Risk Scoring & Explainability System, release identity `credit-risk-system-1.0.0`. No Git tag, commit or GitHub release has been created automatically.

Frozen XGBoost with identity calibration, raw-margin Tree SHAP and an internal log-odds score. Final 4,500-row holdout evaluation followed the pre-unseal snapshot, without fitting or tuning:

| Metric | Logistic TEST | XGBoost TEST |
| --- | --- | --- |
| average_precision | 0.52981208 | 0.55493342 |
| brier_score | 0.13815888 | 0.13517626 |
| ece | 0.013705673 | 0.018104312 |
| gini | 0.5206425 | 0.56029254 |
| ks | 0.40494512 | 0.43652693 |
| log_loss | 0.44034703 | 0.43003453 |
| mean_predicted_probability | 0.22051946 | 0.22103783 |
| observed_positive_rate | 0.22133333 | 0.22133333 |
| roc_auc | 0.76032125 | 0.78014627 |

FastAPI V1, API-key auth, process-local rate limiting, PostgreSQL output audit, separate Alembic migration and local non-root Docker Compose. Aggregate model operations and descriptive score PSI use a VALIDATION reference. Final outputs are aggregate-only; independent component identities and immutable publication support reproduction.

Historical Taiwan 2005 data; no true modern OOT validation, lending policy, FICO score, causal explanation, production/regulatory/fairness certification or cloud deployment. See [model card](model_card.md) and [limitations](limitations.md). Licensing remains unspecified.
