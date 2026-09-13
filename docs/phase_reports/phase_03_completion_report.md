# PHASE 3 COMPLETION REPORT

## 1. Objective

Create the reproducible, leakage-safe modeling-data layer: verified canonical data, explicit financial eligibility, deterministic stratified partitions, stateless financial features, train-only fitted preprocessing and traceable finite matrices. No predictive model is trained.

## 2. Pre-Implementation Repository State

HEAD was `4fe9809` (`feat: add credit risk data ingestion and quality pipeline`), on main and aligned with origin/main. Git status was clean. Phases 1–2 were COMPLETED; Phase 3 and Phases 4–10 were NOT_STARTED. Phase 2 was committed, with ingestion, canonical schema, aggregate quality metadata and 86 tests. No Phase-4+ implementation existed. Phase 3 was set to IN_PROGRESS after the required inspection. Neither historical completion report was changed.

## 3. Documentation Reviewed

Reviewed AGENTS.md, PROJECT_RULES.md, ROADMAP.md, PHASE_STATUS.md, README.md and CHANGELOG.md; architecture, problem definition, dataset decision/card, physical contract, quality report, leakage policy, model governance and glossary; ADR 001 and the Phase-1/2 reports. Inspected all configuration, config/data modules, existing tests, repository structure, Git status/history and ignore rules before implementation.

## 4. Feature Eligibility Policy

- customer_id: identifier only; excluded from X, retained for split integrity/traceability.
- default_next_month: target only; separate y Series, never passed to feature fitting.
- sex, age, education, marital_status: excluded from primary predictors and retained in separate aligned review frames for future fairness/subgroup analysis.
- Primary raw financial families: credit_limit, six repayment statuses, six bill amounts and six payment amounts: 19 raw fields.

Demographic exclusion is a project design choice, not a legal requirement or compliance/fairness claim. The feature manifest explicitly separates all roles.

## 5. Split Strategy

Algorithm: sort canonical rows by customer_id ascending, then two sklearn train_test_split calls, each stratified on default_next_month and using the centralized seed **42**. First reserve 30% temporary data; split it equally into validation/test. Fractions: **70% train, 15% validation, 15% test**.

Version: `sorted_id_two_stage_stratified_v1`. Sorting provides input-order-independent assignments. Validate fractions, complete binary labels, unique non-null IDs, complete coverage, no customer overlap and class representation. No rows are silently removed. Historical months within rows are not distinct scoring cohorts; this is stratified random validation, not out-of-time validation.

## 6. Real Split Results

| Partition | Rows | Negative | Positive | Positive rate |
| --- | --- | --- | --- | --- |
| Train | 21,000 | 16,355 | 4,645 | 22.119048% |
| Validation | 4,500 | 3,505 | 995 | 22.111111% |
| Test | 4,500 | 3,504 | 996 | 22.133333% |

All 30,000 customers occur exactly once. Customer overlap: **0**. Both classes exist in every partition. Rates are rounded here; full precision is in split_manifest.json. These are permitted integrity/class-count checks, not predictive evaluation.

## 7. Financial Feature Engineering

All 26 engineered features are deterministic, per-row and target-independent. In the formulas below, each six-month window covers September through April 2005. Bill standard deviation uses population ddof=0. Source fields, interpretation and edge cases are persisted in the feature manifest and feature-engineering documentation.

| Engineered feature | Formula |
| --- | --- |
| bill_amount_mean | mean(six bill amounts) |
| bill_amount_std | std(six bill amounts); population std, ddof=0 |
| bill_amount_min | min(six bill amounts) |
| bill_amount_max | max(six bill amounts) |
| payment_amount_mean | mean(six payment amounts) |
| payment_amount_sum | sum(six payment amounts) |
| payment_amount_max | max(six payment amounts) |
| bill_to_limit_2005_09 | bill_amount_2005_09 / credit_limit |
| bill_to_limit_2005_08 | bill_amount_2005_08 / credit_limit |
| bill_to_limit_2005_07 | bill_amount_2005_07 / credit_limit |
| bill_to_limit_2005_06 | bill_amount_2005_06 / credit_limit |
| bill_to_limit_2005_05 | bill_amount_2005_05 / credit_limit |
| bill_to_limit_2005_04 | bill_amount_2005_04 / credit_limit |
| payment_to_limit_2005_09 | payment_amount_2005_09 / credit_limit |
| payment_to_limit_2005_08 | payment_amount_2005_08 / credit_limit |
| payment_to_limit_2005_07 | payment_amount_2005_07 / credit_limit |
| payment_to_limit_2005_06 | payment_amount_2005_06 / credit_limit |
| payment_to_limit_2005_05 | payment_amount_2005_05 / credit_limit |
| payment_to_limit_2005_04 | payment_amount_2005_04 / credit_limit |
| bill_to_limit_mean | mean(six bill_amount_month / credit_limit ratios) |
| bill_to_limit_max | max(six bill_amount_month / credit_limit ratios) |
| payment_to_limit_mean | mean(six payment_amount_month / credit_limit ratios) |
| payment_to_limit_max | max(six payment_amount_month / credit_limit ratios) |
| months_with_documented_delay | sum(status > 0 over six months) |
| max_documented_delay | max(positive statuses), or 0 if none |
| recent_documented_delay_flag | 1 if repayment_status_2005_09 > 0 else 0 |

Negative bills and negative ratios are retained. Ratios above one are not capped. Missing/nonpositive credit limits fail explicitly. A missing month makes the affected six-month numeric aggregate NaN for training-median imputation; delay count/max require complete status history, while the recent flag requires only the latest status. Entirely null training numeric columns fail rather than inventing a median. No DTI, payment-to-bill ratio, arbitrary score or target-derived feature exists.

## 8. Repayment Status Treatment

- -2 stays `status_-2`; its meaning remains unresolved.
- -1 stays `status_-1`; UCI documents duly paid, but it is still categorical.
- 0 stays `status_0`; its meaning remains unresolved.
- Positive codes stay distinct categorical tokens and also support documented positive-delay summaries. Code 9 is top-coded at nine or more months.

Only positive documented levels contribute to delay summaries. Zero in a summary means no observed positive code, not proven absence of risk. Missing history is not silently interpreted as no delay. Values outside the source-documented/observed -2 through 9 domain fail for investigation. Valid codes absent from training remain safely transformable through unknown-category handling.

## 9. Preprocessing Architecture

A sklearn Pipeline contains an exact-schema guard and a ColumnTransformer.

Numeric: SimpleImputer(strategy="median") → StandardScaler.

Categorical: SimpleImputer(strategy="constant", fill_value="status_missing", keep_empty_features=True) → OneHotEncoder(handle_unknown="ignore", sparse_output=True).

Fit once on train, then transform train/validation/test using the same fitted object. No y is passed; the guard rejects y arguments and forbidden/extra/misordered input fields. Unknown categories yield a zero block for their source field without expanding vocabulary. The numeric block is processed densely; the combined output is CSR float64. See the pinned [SimpleImputer](https://scikit-learn.org/1.8/modules/generated/sklearn.impute.SimpleImputer.html) and [OneHotEncoder](https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.OneHotEncoder.html) documentation.

## 10. Files Created

| File | Purpose |
| --- | --- |
| src/credit_risk/features/__init__.py | Feature package boundary |
| src/credit_risk/features/definitions.py | Immutable feature policy, versions and 26 formulas |
| src/credit_risk/features/engineering.py | Strict stateless financial engineering |
| src/credit_risk/features/split.py | Deterministic stratified splitting and integrity checks |
| src/credit_risk/features/preprocessing.py | Guarded train-fitted preprocessing and trusted serialization |
| src/credit_risk/features/prepare.py | Verified end-to-end preparation API/CLI and manifests |
| tests/test_features.py | 41 synthetic split, feature, leakage, serialization and integration cases |
| data/metadata/split_manifest.json | Aggregate split definition and measured counts |
| data/metadata/feature_manifest.json | Feature policy, formulas and complete encoded lineage |
| data/metadata/preprocessing_manifest.json | Fitted-row count, shapes, versions and artifact provenance |
| docs/decisions/002-feature-policy-and-split.md | Feature/split policy ADR |
| docs/feature_engineering.md | Every feature's formula, sources, interpretation and edge cases |
| docs/modeling_dataset.md | Consumer API, matrix/target/review alignment and lifecycle contract |
| docs/phase_reports/phase_03_completion_report.md | This completion report |

Fourteen new Git-visible files. A fitted preprocessing artifact was also generated locally under ignored artifacts/preprocessing. No customer-level split/matrix exports were created.

## 11. Files Modified

Sixteen existing files: CHANGELOG.md, PHASE_STATUS.md, README.md, ROADMAP.md, configs/base.yaml, pyproject.toml, src/credit_risk/config.py, tests/test_config.py; docs/architecture.md, data_contract.md, data_quality_report.md, dataset_card.md, dataset_decision.md, decisions/README.md, leakage_policy.md and model_governance.md.

Configuration adds validated fractions while preserving the centralized seed. scikit-learn 1.8.0 is the only new primary dependency; NumPy/SciPy/joblib are used through data/sklearn dependencies. Documentation distinguishes current Phase-3 decisions from historical source findings. Phase-1/2 reports, data ingestion code and original source bytes remain unchanged. Existing ignore rules already protect local outputs.

## 12. Metadata / Manifests

- split_manifest.json: dataset hash, algorithm/version, seed, fractions, ordering, rows, positive/negative counts/rates, complete coverage and zero customer overlap.
- feature_manifest.json: excluded/retained roles, raw and engineered fields, formulas/source columns, numeric/categorical separation, versions, all 103 unique transformed names and per-name lineage.
- preprocessing_manifest.json: dataset hash, split seed/version, input features, fitted train rows, all matrix shapes/finite checks, feature counts, runtime versions, implementation hashes, generation time, relative artifact path/hash and serialization result.

No customer-level records or assignments appear in tracked metadata. Unchanged regeneration preserves aggregate bytes and timestamps. Source XLS SHA-256: `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`.

## 13. Real Transformed Dataset Results

| Measurement | Actual result |
| --- | --- |
| Raw primary financial fields | 19 |
| Engineered fields | 26 |
| Numeric inputs | 39 |
| Categorical repayment inputs | 6 |
| Train-learned one-hot columns | 64 |
| Final transformed columns | 103 |
| Train matrix | 21,000 × 103 |
| Validation matrix | 4,500 × 103 |
| Test matrix | 4,500 × 103 |
| Matrix format | scipy CSR, float64 |
| NaN / positive or negative infinity | None in any matrix |

All 103 names are unique and match matrix width/order. Every encoded category traces to its canonical and original source column; derived fields retain source/formula lineage. Target Series are complete and binary.

## 14. Leakage Controls

Verify pinned raw bytes and Phase-2 manifest identity before loading/preparation. Split before feature engineering or learned transformations. Engineering accepts only the exact raw financial allowlist and has no target input; it does not mutate caller data.

The orchestration fits exactly once on train. Tests spy on the fitting input, compare numeric medians/scaler means with training-only statistics, verify holdout-only categories never enter vocabulary, and confirm changed holdout distributions cannot change training matrices or feature names. The preprocessor rejects extra/forbidden fields and target arguments. Test data is transformed and structurally checked only; no target association, feature selection or predictive performance is inspected.

The public fit helper requires training-only data by contract; arbitrary external DataFrames cannot prove their own provenance. Future consumers must preserve the lifecycle. Cross-validation, if later authorized, must refit preprocessing inside each training fold.

## 15. Demographic / Fairness Data Handling

Every returned partition has a separate review frame containing customer_id, sex, age, education and marital_status. Its indices and row order align with y and the corresponding X rows. Demographics are neither destroyed nor fed into primary preprocessing. No fairness metric, subgroup model or legal-compliance claim is implemented.

## 16. Tests Executed

```powershell
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
git ls-files data/raw data/interim data/processed artifacts
git diff -- docs/phase_reports/phase_01_completion_report.md docs/phase_reports/phase_02_completion_report.md
```

Additional executed checks compared repeated real preparation metadata byte-for-byte and by modification time, verified the artifact checksum/ignore status, and checked local Markdown links/text whitespace.

## 17. Test Results

Final full suite: **127 passed, 0 failed, 0 skipped**, in **5.31 seconds**, with **no warnings**. This includes 86 existing tests and 41 new Phase-3 cases. An earlier full run also passed all 127 tests. Environment: Windows, Python 3.14.6, pytest 9.0.2, scikit-learn 1.8.0. Dependency check: **No broken requirements found.** Git diff whitespace and documentation checks passed.

Tests require no live network or real customer data. A patch application initially failed due to hunk ordering before changes were applied; it was corrected. No failed test result is being omitted.

## 18. Real-Data Integration Validation

The official-source download command successfully verified and reused the pinned 30,000-row XLS. The preparation CLI verified manifest identity, loaded/validated canonical data, split, engineered, separated X/y/review, fitted train preprocessing, transformed all three splits, checked finite values and generated all required manifests.

A repeated real run produced the same split/matrix statistics. All three aggregate manifests remained byte-for-byte identical with unchanged modification times. No predictive model or customer-level export was produced.

## 19. Serialization Validation

The trusted local fitted preprocessor was saved, reloaded after checksum verification and compared against original training transforms. Real-data and synthetic round-trip checks passed. Artifact: `artifacts/preprocessing/preprocessor_e8f6ce776bd44c48871c585c5d472676ad8c418da39c513c1019bf36070ee8b4.joblib`.

SHA-256: `e8f6ce776bd44c48871c585c5d472676ad8c418da39c513c1019bf36070ee8b4`.

The file is ignored and untracked. Joblib loading is restricted by documented use to trusted local artifacts; a checksum does not make arbitrary pickle content safe.

## 20. Known Limitations

Historical static data cannot establish temporal validation or modern representativeness. Undocumented repayment meanings remain unresolved; categorical preservation avoids invented semantics but does not resolve them. Demographic exclusion does not eliminate proxies or establish fairness.

Related raw/aggregate features may be collinear; no performance-based selection has occurred. Missing-history propagation is conservative. Missing/nonpositive limits and entirely null training numeric columns fail explicitly. Unknown categories produce zero blocks and may lose information. Only Windows/Python 3.14.6 was exercised; direct dependencies are pinned but transitive/build dependencies are not fully locked. Fitted artifact recreation requires compatible code/runtime versions. No predictive model exists.

## 21. Deviations From Prompt

None.

## 22. Risks / Technical Debt

Later consumers must preserve row alignment, train-only fitting and test sealing. Future cross-validation cannot reuse statistics fitted on all training rows across its internal holdout folds. No source-verified resolution exists for -2/0 meanings or precise snapshot times. The feature policy is domain-defined and unvalidated for predictive performance. Serialized artifacts require trusted storage; a seed alone does not guarantee cross-version bitwise identity. No meaningful instruction contradiction was identified.

## 23. Phase-4 Recommendations

Use the prepared training/validation data and versioned feature names for the explicitly authorized baseline phase. Keep test sealed until the intended final evaluation, record dataset/split/preprocessing identities and assess the impact of correlated features within training/validation only. Preserve primary-feature/review separation and distinguish future raw probabilities from calibrated PD. No Logistic Regression or other predictor has been implemented or trained.

## 24. Reproduction Commands

From the repository root, creating a virtual environment only if needed:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
git ls-files data/raw data/interim data/processed artifacts
```

This phase reused the existing virtual environment and successfully installed the updated package/dependencies. POSIX uses `.venv/bin/python`. Data/preparation CLIs accept `--project-root PATH`. Preparation itself performs no network requests. Matrices and review frames can be recreated in memory through the documented API.

## 25. Git Status

Sixteen tracked files modified; fourteen new Git-visible files untracked. Nothing staged. Raw/interim/processed/artifacts tracking contains only .gitkeep markers. Original raw data, customer-level processed data and the fitted preprocessor are not tracked. No customer-level assignments/matrices were exported. Historical Phase-1/2 report diffs are empty. HEAD remains `4fe9809`; no Git commit was created.

## 26. Documentation Status

ADR 002, feature-engineering documentation, modeling-dataset contract, three aggregate manifests and this report exist. Current README, architecture, data contract, leakage/governance policy, changelog and phase records reflect Phase 3; historical reports remain unchanged. All local links and text whitespace checks pass. Final statuses: Phases 1–3 COMPLETED; Phases 4–10 NOT_STARTED. Current completed phase: Phase 3. Next phase: Phase 4, not started.

## 27. Acceptance Criteria Checklist

- [x] Required project documentation was read before implementation.
- [x] Phase-2 dataset/checksum identity is verified before preparation.
- [x] Phase-3 split is deterministic.
- [x] Split is stratified.
- [x] Train fraction is 70%.
- [x] Validation fraction is 15%.
- [x] Test fraction is 15%.
- [x] No row exists in multiple partitions.
- [x] Every eligible row belongs to exactly one partition.
- [x] customer_id is excluded from model predictors.
- [x] default_next_month is excluded from model predictors.
- [x] sex is excluded from the primary model.
- [x] age is excluded from the primary model.
- [x] education is excluded from the primary model.
- [x] marital_status is excluded from the primary model.
- [x] Demographic fields are retained separately for future fairness review.
- [x] Raw financial features are explicitly defined.
- [x] Engineered features are explicitly defined.
- [x] No DTI feature was fabricated.
- [x] Negative bill values are retained.
- [x] Financial ratios are not arbitrarily clipped.
- [x] Undocumented repayment codes are not assigned invented semantics.
- [x] Repayment-status fields are treated categorically.
- [x] Documented positive delay summary features are correctly generated.
- [x] Numeric preprocessing is fit on TRAIN only.
- [x] Categorical preprocessing is fit on TRAIN only.
- [x] Validation data is never used to fit preprocessing.
- [x] Test data is never used to fit preprocessing.
- [x] OneHotEncoder safely handles unseen categories.
- [x] Target cannot enter preprocessing.
- [x] Final transformed feature names are traceable.
- [x] Final transformed feature names are unique.
- [x] Train matrix contains no NaN/inf.
- [x] Validation matrix contains no NaN/inf.
- [x] Test matrix contains no NaN/inf.
- [x] Preprocessor serialization round-trip works.
- [x] Split manifest exists.
- [x] Feature manifest exists.
- [x] Preprocessing manifest exists.
- [x] Feature-policy ADR exists.
- [x] Feature-engineering documentation exists.
- [x] Modeling-dataset documentation exists.
- [x] Real UCI dataset was processed end-to-end.
- [x] Real split/matrix statistics were measured.
- [x] No customer-level processed dataset is tracked by Git.
- [x] No fitted preprocessing artifact is tracked by Git.
- [x] No predictive model was trained.
- [x] No Phase-4 functionality was implemented.
- [x] Full automated test suite passes.
- [x] pip check passes.
- [x] git diff --check passes.
- [x] README matches actual implementation.
- [x] Architecture documentation is updated.
- [x] Phase-3 completion report exists.
- [x] Phase 3 status is COMPLETED.
- [x] Phase 4 remains NOT_STARTED.
- [x] No Git commit was created automatically.

## 28. Final Verdict

PHASE 3 COMPLETED
