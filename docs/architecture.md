# Intended architecture and implemented boundary

Implemented now (Phase 1): project rules, conceptual data contract, configuration loading/validation, repository-relative path resolution and foundation tests.

```text
Raw public credit dataset                 [Phase 2: planned]
        ↓
Data validation                         [Phase 2: planned]
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

Use a src-layout Python package. Configuration receives an explicit project root and reads two fixed YAML files; no import-time I/O or environment discovery. Reserve data/features/modeling/explainability/utils directories without functional stubs. Final serving and persistence designs require later review and ADRs.
