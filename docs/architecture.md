# Intended architecture and implemented boundary

Implemented now (Phases 1–2): project rules, validated configuration, official UCI acquisition, immutable raw XLS verification, manifest generation, strict loading/canonicalization, binary target validation, descriptive quality profiling, aggregate JSON metadata, physical data contract and tests. No predictive model or preprocessing pipeline exists.

```text
Raw public credit dataset                 [Phase 2: implemented]
        ↓
Data validation                         [Phase 2: implemented]
        ↓
Leakage-safe preprocessing               [Phase 3: planned]
        ↓
Feature engineering                     [Phase 3: planned]
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

Canonicalization renames fields and represents verified integral numeric cells as nullable Int64. It removes only the two verified header rows, never customer records. No category recoding, learned transformation, feature derivation or splitting occurs. JSON metadata contains aggregate statistics and schema, never customer records. Feature/model/explanation/utils directories remain reserved for future phases. Final serving and persistence designs require later review and ADRs.
