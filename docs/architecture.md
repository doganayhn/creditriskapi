# Intended architecture and implemented boundary

Implemented now (Phases 1–6): project rules, configuration, official UCI ingestion/quality, raw identity checks, canonical schema, stratified splitting, financial features, train-only preprocessing, Logistic Regression, XGBoost, TRAIN OOF calibration selection, reported probabilities, validation comparison, TRAIN-derived technical thresholds, coefficient/gain diagnostics, aggregate manifests and tests. TEST remains sealed.

```text
Official UCI data / ingestion / quality  [Phase 2: implemented]
        ↓
Stratified 70/15/15 split                [Phase 3: implemented; TEST sealed]
        ↓
Financial feature engineering           [Phase 3: implemented]
        ↓
TRAIN-only preprocessing                [Phase 3: implemented]
        ├──── Logistic Regression        [Phase 4: implemented]
        │
        └──── XGBoost challenger         [Phase 5: implemented]
                        ↓
              TRAIN OOF raw probabilities [Phase 6: fresh preprocessing/model per fold]
                        ↓
              Calibration selection CV   [Phase 6: TRAIN probabilities/labels only]
                        ↓
              Versioned frozen mappings  [Phase 6: identity selected for both]
                        ↓
              Reported default probability
                        ↓
              Validation model comparison [Phase 6: frozen mappings]
                        ↓
              XGBoost selected downstream [Development selection; TEST sealed]
                        ↓
              TRAIN OOF technical threshold analysis [No lending policy]

TRAIN engineered inputs → fresh preprocessing inside each CV fold
                        → XGBoost search → selected canonical parameters

PLANNED:
Phase 7: explainability / internal score
Phase 8: API / business rules / persistence
```

The flow is conceptual: explainability also consumes the underlying model and transformed features; it does not automatically decompose calibrated PD. Training, calibration and policy retain independent identities. Operational controls arrive in Phase 9; final validation in Phase 10.

Use a src-layout Python package. Configuration receives an explicit project root and reads two fixed YAML files; no import-time I/O or environment discovery. `data/source.py` fixes the verified V1 identity/URL/hash; `download.py` acquires only the official archive and extracts its single XLS member unchanged; `load.py` validates the two header rows and numeric cells; `schema.py` holds immutable column definitions and validation; `quality.py` writes aggregate descriptive metadata. Paths come from config; CLI `--project-root` supports invocation outside the repository.

Acquisition flow: official HTTPS ZIP → checksum-verified XLS → atomic no-overwrite publication in configured raw directory → strict loader → aggregate manifest. Profiling is a separate local-only command that verifies the raw checksum again and writes aggregate JSON. Existing matching raw bytes are reused without network requests. Existing mismatches fail without overwriting; partial downloads are never published. The XLS checksum is locally measured and pinned, not a UCI-published signature.

Canonicalization renames fields and represents verified integral numeric cells as nullable Int64. It removes only the two verified header rows, never customer records. The Phase-2 data layer remains unchanged; all modeling-data transformations are isolated under `features/`.

The Phase-3 preparation CLI verifies raw bytes and manifest identity, splits sorted canonical rows, allowlists 19 financial fields, engineers each partition independently, and fits a guarded sklearn ColumnTransformer on train only. It transforms three finite CSR matrices while keeping targets and demographic/ID review frames separate. Its test processing is structural only. A trusted local fitted-preprocessor artifact is stored under ignored artifacts; tracked metadata contains only aggregate split statistics, definitions, encoded-name lineage and preprocessing provenance. No customer-level assignments or matrices are written to Git paths. See [modeling_dataset.md](modeling_dataset.md) and [ADR 002](decisions/002-feature-policy-and-split.md).

The Phase-4 `modeling/contract.py` adapter verifies committed V1 semantic manifest identities, feature implementation and runtime versions, raw bytes and the fitted-preprocessor checksum. It reuses the existing split/engineering/transform helpers; after structural splitting, it immediately discards the TEST branch and exposes only TRAIN/VALIDATION matrices and labels. It never refits preprocessing or rewrites Phase-3 metadata.

`modeling/baseline.py` fits one fixed L2 LogisticRegression on TRAIN and fails on non-convergence. `metrics.py` computes discrimination, probability diagnostics, a fixed 0.50 reference threshold and deterministic validation bootstrap intervals. Coefficients retain transformed-column lineage. `artifacts.py` saves a versioned content-addressed model under ignored artifacts/models and verifies its training-probability round-trip. See [baseline_model_report.md](baseline_model_report.md) and [ADR 003](decisions/003-logistic-baseline.md).

`search.py` builds a fresh Phase-3 preprocessor inside every candidate/fold Pipeline, discarding y only at its unsupervised boundary. RandomizedSearchCV receives engineered TRAIN inputs only. `xgboost_challenger.py` verifies the existing final-data/baseline contracts, performs bounded CPU search, fits the selected unweighted model on full TRAIN, evaluates TRAIN/VALIDATION, runs one separate weighted sensitivity model, maps native gain and validates native JSON serialization. Dense materialization preserves the same 103 values and zero semantics.

`comparison.py` loads stored Phase-4 metrics and checks reproduced baseline probabilities, computes validation deltas and paired-bootstrap uncertainty, and assigns the Phase-5 provisional status. No customer outputs are exported; only aggregate search results, metrics, importance and manifests enter metadata. See [XGBoost report](xgboost_model_report.md) and [ADR 004](decisions/004-xgboost-challenger.md).

`calibration.py` verifies both stored models without first scoring validation, creates five-fold TRAIN OOF probabilities using fresh preprocessing and fixed model builders, and performs a separate TRAIN-only calibration-selection CV. `calibrators.py` implements identity, constrained sigmoid and monotonic isotonic using public SciPy/sklearn APIs. Both selected mappings are fitted and frozen before canonical VALIDATION scoring. Non-identity mappings have trusted local content-addressed joblib serialization; actual identity choices are metadata-only.

`calibration_metrics.py` adds quantile reliability/ECE and paired probability-quality intervals. Its four-metric dominance rule selects XGBoost for downstream development. `thresholds.py` derives max-KS only from selected-model TRAIN OOF probabilities and produces a TRAIN grid; the orchestration evaluates the frozen threshold and reference 0.50 on VALIDATION. Five aggregate metadata outputs link model/calibration/data identities. OOF and validation customer probabilities stay in memory. TEST remains sealed; SHAP, score, policy, API and persistence remain unimplemented. See [calibration report](calibration_report.md) and [ADR 005](decisions/005-calibration-and-model-selection.md).
