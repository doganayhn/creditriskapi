# Purpose

Read-only output and operations diagnostics for successful audited inference events. No training or credit decisions.

# Frozen Runtime Contract

Model, calibration, explanation, score, API/service, schema and operations identities remain separate. Operations version: model-operations-1.0.0. Expected values come from tracked metadata, never copied historical constants.

# Artifact Integrity

Startup retains Phase-8 hash/version/lineage checks. Frozen binaries are externally supplied through a read-only mount. Operations do not recreate missing artifacts.

# Audit Validation

The checker counts rows, invalid rows, version/hash mismatches, probability violations, TEST-flag violations, explanation-contract violations, invalid numeric values/endpoints and duplicate IDs. Identity calibration requires raw/reported equality. An invalid audit exits nonzero and suppresses the monitoring summary. No offending rows or IDs are exported. Empty windows report zero rows and a valid empty audit, not proof of deployment health.

# Operational Summary

For a UTC window [start,end), report successful event/predict/explain counts, model/calibration/score version counts, mean probability/score and p01/p05/p50/p95/p99, inference latency p50/p95/p99, and output bin counts. Failed HTTP requests are absent from this table: these counts cannot establish API failure rate. Current implementation holds the selected window in memory; this is intended for bounded local use, not unbounded production scans.

# Output Distribution Monitoring

Ten fixed score bins include both unbounded tails. Probability bins use fixed 0.1 increments. Internal edges belong to the upper bin. Summary stdout is aggregate JSON only; local integration evidence is ignored under .local/. No database snapshots are committed.

# Monitoring Baseline

output-monitoring-baseline-1.0.0 is derived exclusively from the existing Phase-7 VALIDATION decile CSV (4,500 records represented as aggregates). Boundaries are midpoints of the gaps between adjacent non-overlapping observed deciles, ordered by score ascending. Each expected proportion is 0.1. Weighted reference probability mean is 0.21956850854390197 and score mean is 531.9659941618735. No scoring or row reconstruction is needed. The source checksum is recorded. Overlapping deciles fail publication rather than inventing exact bins. Changes require a new reviewed version; the publisher refuses an inconsistent existing baseline.

# PSI Definition

PSI = sum((actual_i - expected_i) * ln(actual_i / expected_i)). Normalize counts, floor proportions at epsilon 1e-6, then renormalize both distributions before applying the formula. Return a numeric diagnostic with no drift label or retraining action. Empty windows have null PSI. Synthetic examples cannot establish production drift; no generic PSI cutoff is used.

# Sample-Size Limitation

Default minimum is 100 events; --minimum-count changes the reporting guard only. Smaller windows set sample_size_limited=true while returning mathematically available aggregates. Quantiles use NumPy linear interpolation. These are operational reporting choices, never lending thresholds.

# What Is NOT Monitored

No feature drift: raw inputs/features were not retained. No live performance metrics, realized calibration or outcome monitoring: production labels are unavailable. No automatic retraining, challenger selection or credit action. No API failure-rate estimate from successful audit rows. TEST is not a baseline.

# Version Consistency

Audit rows must match tracked model/hash/calibration/score/API/schema identities; explain rows must carry the expected explanation version. Summary baseline identity must match the same frozen model, calibration and score.

# Operational CLI

With DATABASE_URL and CREDIT_RISK_PROJECT_ROOT securely set:

```powershell
python -m credit_risk.ops.run audit --hours 24
python -m credit_risk.ops.run summary --hours 24 --minimum-count 100
```

In Compose use `docker compose exec -T api` before either command. Exceptions return generic credential-free JSON and exit 1. CLI checks database readiness first and never changes schema/data. The URL is read only from environment, not a command-line argument. Reproduce the aggregate baseline explicitly with `python -m credit_risk.ops.baseline`; it is not a startup action.

# TEST Set Policy

TEST SET WAS NOT EVALUATED. TEST SET REMAINS SEALED. No dataset partitions are loaded by operations.

# Limitations

Single local deployment; no monitoring server, retention automation, input telemetry, outcomes, distributed limiter or external secret manager. Multiple requests from one synthetic input do not form a representative population. See the Phase-9 report for actual integration evidence and limitations.

## Phase-10 lifecycle clarification

The separate final evaluator has now evaluated the frozen TEST holdout and published aggregate results. Earlier sealed-TEST statements above describe the Phase-8/9 implementation boundary: this API/persistence/deployment/operations path still does not load or evaluate dataset TEST records. Its historical metadata and audit false TEST flags remain unchanged. No TEST record is used in API demonstrations, and the monitoring baseline remains VALIDATION-only. See [final evaluation](final_evaluation_report.md) and [governance](model_governance.md).
