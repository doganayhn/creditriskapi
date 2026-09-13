# Intended architecture and implemented boundary

Implemented now (Phases 1–4): project rules, configuration, official UCI acquisition/quality, raw identity checks, canonical schema, stratified splitting, financial features, train-only preprocessing, one Logistic Regression baseline, raw probabilities, TRAIN/VALIDATION evaluation, coefficients, aggregate manifests and tests. TEST remains sealed.

```text
Raw public credit dataset                 [Phase 2: implemented]
        ↓
Data validation                         [Phase 2: implemented]
        ↓
Stratified train / validation / test     [Phase 3: implemented]
        ↓
Stateless financial feature engineering  [Phase 3: implemented]
        ↓
Train-only fitted preprocessing         [Phase 3: implemented]
        ↓
Logistic Regression baseline            [Phase 4: implemented; TRAIN fit]
        ↓
Raw default probability                 [Phase 4: TRAIN / VALIDATION only]
        ↓
Validation evaluation / coefficients    [Phase 4: implemented]
        ↓
XGBoost challenger                      [Phase 5: planned]
        ↓
Probability calibration when justified  [Phase 6: planned]
        ↓
PD                                      [Phase 6: planned]
        ↓
Explainability                          [Phase 7: planned]
        ↓
Internal risk representation            [Phase 7: planned]
        ↓
Versioned business rules                [Phase 8: planned]
        ↓
Versioned API                           [Phase 8: planned]
        ↓
Persistence / audit                     [Phase 8: planned]
```

The flow is conceptual: explainability also consumes the underlying model and transformed features; it does not automatically decompose calibrated PD. Training, calibration and policy retain independent identities. Operational controls arrive in Phase 9; final validation in Phase 10.

Use a src-layout Python package. Configuration receives an explicit project root and reads two fixed YAML files; no import-time I/O or environment discovery. `data/source.py` fixes the verified V1 identity/URL/hash; `download.py` acquires only the official archive and extracts its single XLS member unchanged; `load.py` validates the two header rows and numeric cells; `schema.py` holds immutable column definitions and validation; `quality.py` writes aggregate descriptive metadata. Paths come from config; CLI `--project-root` supports invocation outside the repository.

Acquisition flow: official HTTPS ZIP → checksum-verified XLS → atomic no-overwrite publication in configured raw directory → strict loader → aggregate manifest. Profiling is a separate local-only command that verifies the raw checksum again and writes aggregate JSON. Existing matching raw bytes are reused without network requests. Existing mismatches fail without overwriting; partial downloads are never published. The XLS checksum is locally measured and pinned, not a UCI-published signature.

Canonicalization renames fields and represents verified integral numeric cells as nullable Int64. It removes only the two verified header rows, never customer records. The Phase-2 data layer remains unchanged; all modeling-data transformations are isolated under `features/`.

The Phase-3 preparation CLI verifies raw bytes and manifest identity, splits sorted canonical rows, allowlists 19 financial fields, engineers each partition independently, and fits a guarded sklearn ColumnTransformer on train only. It transforms three finite CSR matrices while keeping targets and demographic/ID review frames separate. Its test processing is structural only. A trusted local fitted-preprocessor artifact is stored under ignored artifacts; tracked metadata contains only aggregate split statistics, definitions, encoded-name lineage and preprocessing provenance. No customer-level assignments or matrices are written to Git paths. See [modeling_dataset.md](modeling_dataset.md) and [ADR 002](decisions/002-feature-policy-and-split.md).

The Phase-4 `modeling/contract.py` adapter verifies committed V1 semantic manifest identities, feature implementation and runtime versions, raw bytes and the fitted-preprocessor checksum. It reuses the existing split/engineering/transform helpers; after structural splitting, it immediately discards the TEST branch and exposes only TRAIN/VALIDATION matrices and labels. It never refits preprocessing or rewrites Phase-3 metadata.

`modeling/baseline.py` fits one fixed L2 LogisticRegression on TRAIN and fails on non-convergence. `metrics.py` computes discrimination, probability diagnostics, a fixed 0.50 reference threshold and deterministic validation bootstrap intervals. Coefficients retain transformed-column lineage. `artifacts.py` saves a versioned content-addressed model under ignored artifacts/models and verifies its training-probability round-trip. Only aggregate metrics, parameters and manifests are written under metadata. No calibration, challenger, SHAP, scoring, decisions or serving is implemented. See [baseline_model_report.md](baseline_model_report.md) and [ADR 003](decisions/003-logistic-baseline.md).
