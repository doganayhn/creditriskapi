# Limitations

## Data and target

The UCI Default of Credit Card Clients snapshot describes Taiwan credit-card customers in 2005. This public static dataset and stratified random split provide no true modern out-of-time validation. Existing approved cardholders do not represent all applicants. The target is default payment next month; its adjudication threshold is unspecified. It is not established as 90+ DPD, a 12-month Basel PD or IFRS 9 lifetime PD. Snapshot timing and undocumented repayment/demographic codes remain limitations. No invented recoding resolves these gaps.

## Modeling and calibration

No real bureau feeds, income/affordability verification, reject inference, LGD, EAD or expected-loss engine exists. Demographics are excluded, but proxies may remain; exclusion is not proof of fairness. VALIDATION was reused for development comparisons. TRAIN OOF calibration analysis is not fully nested end-to-end model-selection uncertainty. Identity calibration was selected from development data; TEST calibration is descriptive evaluation only. Frozen bootstrap intervals condition on this model and sample, not retraining or future population shift. No TEST-driven tuning occurred.

## Score and explainability

The internal log-odds score is a mathematical transformation, not FICO, a business cutoff or regulatory scoring system. TRAIN OOF score statistics remain unavailable under the owner's no-retraining decision. Tree SHAP explains raw XGBoost margin, not additive probability or causal effects. Correlation and path-dependent attribution affect interpretation. Exact score-point decomposition is supported only for the verified identity/logistic/unclipped case. Explanations are not certified adverse-action reasons. TEST contains only a small technical SHAP check; global interpretation remains based on VALIDATION.

## Deployment and security

Deployment is local Docker Compose with one worker and process-local rate limiting. There is no external secret manager, cloud high availability, TLS termination inside the app, distributed limiter, production SLA or vulnerability-free claim. Docker-host administrators can inspect injected environment secrets. The base tag and OS package resolution are not a complete immutable supply-chain lock. Strict frozen numerical versions are required; supported Python versions were not all matrix-tested.

## Persistence and monitoring

Only successful inference outputs and optional safe top-k diagnostics are retained. They remain sensitive and need operator-controlled access, retention and backups. Raw inputs are omitted, preventing full request reconstruction. Ambiguous network failure after a committed write has no idempotency/reconciliation protocol. Monitoring covers output distributions and aggregate contract checks only; no raw-feature drift, realized-outcome performance or live calibration monitoring exists. Successful audit rows cannot establish HTTP failure rates. Bounded windows are loaded into memory. PSI has no automatic action or business meaning.

## Business and governance

No approve/decline policy, business cutoff, risk bands or credit-limit recommendation exists. This is not a Basel/IFRS production model and has no regulatory validation or legal fairness certification. Modern deployment requires separate population, jurisdiction, privacy and model governance. The project has no repository LICENSE; repository licensing remains unspecified pending the owner's choice. Dataset attribution/terms are separately documented in the dataset card. No license was added automatically.

## Final evaluation boundary

TEST was opened only in Phase 10 after the development system was frozen. Final outputs are aggregates; no customer-level predictions, scores, labels, IDs or SHAP arrays are exported. Historical false TEST flags retain their original phase meaning. API/audit/operations false flags continue to mean that those paths do not evaluate dataset TEST records; final evaluation has its own true flag. Final results must never feed back into this frozen model.
