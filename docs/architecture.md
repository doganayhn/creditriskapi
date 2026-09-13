# Intended architecture and implemented boundary

Implemented now (Phases 1–3): project rules, validated configuration, official UCI acquisition and quality analysis, immutable raw identity checks, canonical schema, stratified dataset splitting, stateless financial features, train-only fitted preprocessing, aggregate manifests and tests. No predictive model exists.

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
Baseline / challenger models            [Phases 4–5: planned]
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

The Phase-3 preparation CLI verifies raw bytes and manifest identity, splits sorted canonical rows, allowlists 19 financial fields, engineers each partition independently, and fits a guarded sklearn ColumnTransformer on train only. It transforms three finite CSR matrices while keeping targets and demographic/ID review frames separate. A trusted local fitted-preprocessor artifact is stored under ignored artifacts; tracked metadata contains only aggregate split statistics, definitions, encoded-name lineage and preprocessing provenance. No customer-level assignments or matrices are written to Git paths. Model/explanation/utils components remain future work. See [modeling_dataset.md](modeling_dataset.md) for the consumer contract and [ADR 002](decisions/002-feature-policy-and-split.md) for decisions.
