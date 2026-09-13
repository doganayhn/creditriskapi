# PHASE 2 COMPLETION REPORT

## 1. Objective

Establish reproducible official-source acquisition, a verified physical data contract and measured data-quality evidence for V1 credit-risk work. Implement ingestion and descriptive profiling only, with no modeling or Phase-3 preprocessing.

## 2. Pre-Implementation Repository State

The working tree was clean at `cf00195` (`feat: establish credit risk project foundation`). Phase 1 was COMPLETED; Phase 2 and Phases 3–10 were NOT_STARTED. Existing functionality comprised configuration and 34 foundation tests. Future component directories contained only markers. Phase 2 was set to IN_PROGRESS after the required inspection. The committed Phase-1 report remains unchanged.

## 3. Documentation Reviewed

Read AGENTS.md, PROJECT_RULES.md, ROADMAP.md, PHASE_STATUS.md, README.md, CHANGELOG.md; docs/architecture.md, problem_definition.md, dataset_decision.md, data_contract.md, leakage_policy.md, model_governance.md, glossary.md; the Phase-1 completion report; and the ADR/report directory policies. Inspected configuration, package/test code, repository structure, Git state and ignore rules before implementation.

## 4. Official Dataset Verification

- Name: **Default of Credit Card Clients**.
- UCI ID: **350**.
- DOI: **10.24432/C55S3H**.
- License: **CC BY 4.0**, as listed by UCI.
- Source: [official UCI dataset page](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) and its [original XLS archive](https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip), verified 2026-09-13.
- Attribution: Yeh, I. (2009). Default of Credit Card Clients [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C55S3H.
- UCI lists I-Cheng Yeh as creator; its introductory paper credits I. Yeh and Che-hui Lien (2009).
- Historical context: Taiwan credit-card clients, with source-documented April–September 2005 repayment, statement and payment histories. The 2016-01-25 donation date is distinct from the data period.

The archive contains one original workbook, `default of credit card clients.xls`. Metadata and downloaded workbook were both inspected. No mirror was used. Phase-1 unknowns were resolved or explicitly retained as unknown; no factual contradiction required rewriting the Phase-1 report.

## 5. Final Dataset Decision

Selected UCI 350 for V1 in `docs/decisions/001-dataset-selection.md`. Its verified source, manageable size and interpretable financial history suit the portfolio objective. German Credit, Give Me Some Credit and Home Credit were considered; the latter two retain incomplete source/access verification from Phase 1. This historical snapshot is not a modern banking event stream or a regulatory-representative population.

## 6. Target Definition

- Original target: `default payment next month`.
- Canonical target: `default_next_month`.
- Class 0: no default payment next month.
- Class 1: default payment next month.
- Horizon: next month, explicitly stated in the original workbook header; UCI supplies the yes/no binary meaning.
- Limitations: no documented Basel/IFRS 9, 90+ DPD or 12-month definition. The exact default-adjudication threshold is unspecified. October 2005 is a calendar inference from the latest history month, not a verified per-customer event timestamp.

## 7. Files Created

| File | Purpose |
| --- | --- |
| src/credit_risk/data/__init__.py | Data package boundary |
| src/credit_risk/data/source.py | Verified source identity, URL and pinned raw checksum |
| src/credit_risk/data/download.py | Safe acquisition, checksum and manifest CLI |
| src/credit_risk/data/load.py | Strict original XLS reader |
| src/credit_risk/data/schema.py | Immutable field definitions, mapping and validation |
| src/credit_risk/data/quality.py | Descriptive profiling and aggregate JSON CLI |
| data/metadata/dataset_manifest.json | Generated provenance and source mapping |
| data/metadata/data_quality_summary.json | Generated measured aggregate profiles |
| docs/decisions/001-dataset-selection.md | Final V1 selection ADR |
| docs/dataset_card.md | Identity, attribution, semantics and limitations |
| docs/data_quality_report.md | Measured quality findings and descriptive EDA |
| docs/phase_reports/phase_02_completion_report.md | This completion report |
| tests/conftest.py | Synthetic DataFrame and temporary-project fixtures |
| tests/test_data_download.py | Acquisition and local pipeline failure/success tests |
| tests/test_data_load.py | Original-format reader and malformed-input tests |
| tests/test_data_schema.py | Mapping, physical schema and target tests |
| tests/test_data_quality.py | Aggregate metric and no-transformation tests |
| tests/fixtures/synthetic_credit.xls | Four entirely synthetic source-format rows |
| tests/fixtures/README.md | Fixture provenance and regeneration instructions |

These are 19 new Git-visible files. The original XLS was created locally under ignored `data/raw/`; it is not a Git deliverable. A temporary xlwt 1.3.0 writer was installed only under ignored `artifacts/fixture_tools` to generate the synthetic fixture. Runtime and test installation do not require that writer.

## 8. Files Modified

Sixteen existing files: CHANGELOG.md, PHASE_STATUS.md, README.md, ROADMAP.md; configs/base.yaml and configs/experiment.yaml; docs/architecture.md, data_contract.md, dataset_decision.md, decisions/README.md, leakage_policy.md, model_governance.md and problem_definition.md; pyproject.toml; src/credit_risk/config.py; tests/test_config.py.

Changes add Phase-2 functionality/documentation, the metadata path, the verified target, pandas/xlrd dependencies and corresponding configuration assertions. Existing .gitignore already protects raw/interim/processed data, so no change was needed. Phase-1 completion history and Phases 3–10 implementations were not modified.

## 9. Data Acquisition Implementation

`python -m credit_risk.data.download` retrieves only the official HTTPS ZIP with a 30-second socket timeout, explicit network/HTTP failures, response/archive size limits and expected-member validation. The extracted XLS must match the pinned checksum before publication. Temporary bytes are published with an atomic no-overwrite hard link; conflicting existing files are never replaced.

Matching local bytes are rehashed and reused without a download. Manifest retrieval time is preserved on reruns; if matching bytes pre-exist without a recorded acquisition time, it is null rather than fabricated. Unreadable or checksum-conflicting existing manifests fail explicitly. Metadata writes are atomic and unchanged content is not rewritten. Configuration supplies portable raw/metadata directories and the CLI accepts an explicit project root.

## 10. Dataset Manifest

| Measurement | Value |
| --- | --- |
| Original filename | default of credit card clients.xls |
| File size | 5,539,328 bytes |
| SHA-256 | 30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933 |
| Acquisition time | 2026-09-13T12:45:06.069006+00:00 |
| Customer records | 30,000 |
| Raw / canonical columns | 25 / 25 |
| Header rows excluded | 2 |

`data/metadata/dataset_manifest.json` also records source URL, download URL, UCI ID, DOI, license, attribution, target semantics and the complete mapping. The checksum was measured from official UCI bytes and pinned locally; it is not a publisher-provided signature.

## 11. Canonical Schema

Twenty-five unique columns comprise `customer_id`, `credit_limit`, `sex`, `education`, `marital_status`, `age`, six `repayment_status_YYYY_MM`, six `bill_amount_YYYY_MM`, six `payment_amount_YYYY_MM`, and `default_next_month`.

History suffixes run from 2005_09 through 2005_04 using source-documented month meanings. The loader verifies the `Data` sheet and both header rows, rejects malformed schemas and non-numeric/error cells, validates finite integral values and the binary target, then represents values as nullable Int64. Only headers are removed; customer records and category codes are retained. The contract documents each source/canonical name, dtype, financial meaning, observed domain, missingness, role, eligibility and demographic flag. No future feature set is finalized.

## 12. Data Quality Findings

- Target: **23,364 negative**, **6,636 positive**, positive rate **22.12%**.
- True nulls: **0** across all 25 columns. Undocumented codes are not treated as nulls.
- Exact duplicate rows including ID/target: **0**; duplicate non-null IDs: **0**. Duplicate counts mean occurrences after the first.
- IDs: **30,000** unique, no missing values; range **1–30,000**.
- Canonical memory including index: **6,750,132 bytes**.
- Education undocumented codes: **0: 14**, **5: 280**, **6: 51**.
- Marital-status undocumented code: **0: 54**.

Repayment codes not defined in the consulted official description:

| History month | Code -2 count | Code 0 count |
| --- | --- | --- |
| September 2005 | 2,759 | 14,737 |
| August 2005 | 3,782 | 15,730 |
| July 2005 | 4,085 | 15,764 |
| June 2005 | 4,348 | 16,455 |
| May 2005 | 4,546 | 16,947 |
| April 2005 | 4,895 | 16,286 |

Age ranges **21–79**, with mean **35.4855**, median **34**, and **272** descriptive IQR flags. Credit limit ranges **NT$10,000–1,000,000**, median **140,000**, with **167** IQR flags; neither field has null/nonpositive values. No arbitrary upper-age rejection was applied.

Negative bill counts from September back to April are **590, 669, 655, 675, 655, 688**. Bills range as low as **−339,603** and as high as **1,664,089** NT dollars across months. Payment amounts have **0 negatives**, with a maximum of **1,684,259** NT dollars. Negative bills may represent credits/overpayments, but that explanation is not verified; values are retained.

The quality report includes all repayment/demographic distributions, per-column missingness/cardinality, numeric means/medians/sample standard deviations, quantiles and IQR counts. Full precision is in the generated JSON. No records, codes or outliers were removed or transformed.

## 13. Sensitive / Demographic Fields

Sex, age, education and marital status are classified DEMOGRAPHIC_REVIEW_REQUIRED. Phase 3 must decide primary-model eligibility and fairness-analysis retention. Phase 2 does not automatically include/exclude them or claim fairness/legal/regulatory compliance.

## 14. Temporal Assessment

Six historical months within each customer row are not multiple calendar scoring cohorts. The verified workbook has no per-row scoring/event timestamps supporting a true chronological train/test split or complete observation/performance-window reconstruction. Future random/stratified evaluation must not be described as out-of-time validation.

## 15. Leakage Assessment

The ID is traceability-only and the outcome is target-only. Credit limit, bills and payments are conditional pre-outcome candidates; demographic fields require review. Repayment fields additionally require investigation of undocumented codes. Snapshot update times are not verified, and historical labels do not prove operational point-in-time availability. No recovery/charge-off/collection-outcome columns exist in this workbook. Eligibility is assessed by semantic timing, not target correlation. The dataset-specific review covers all field families in the leakage policy and physical contract.

## 16. Tests Executed

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.data.quality
git diff --check
git status --short --untracked-files=all
git ls-files data/raw data/interim data/processed
git check-ignore -v 'data/raw/default of credit card clients.xls'
git diff -- docs/phase_reports/phase_01_completion_report.md
```

## 17. Test Results

Final full suite: **86 passed, 0 failed, 0 skipped**, in **1.15 seconds** on Windows/Python 3.14.6 with pytest 9.0.2. No final pytest warnings. Dependency check: **No broken requirements found.** Git diff whitespace check passed.

The initial expanded suite had 81 passes and one NumPy warning from an all-null synthetic column's median. Explicit empty-column handling resolved it; additional network/provenance tests brought the final suite to 86 clean passes. Unit tests use mocks, temporary directories and synthetic records; they require neither live network nor the real dataset. The real profiler reports 28 aggregate domain warnings for investigation, not test failures.

## 18. Real-Data Integration Validation

Executed official retrieval, SHA-256 verification, original XLS loading, two-header validation, canonicalization, physical/target validation, manifest generation, profiling and quality-summary generation against the real dataset. The commands completed successfully with the dimensions/prevalence above.

Repeated acquisition reused existing raw bytes. A further real-data rerun disabled network access through a mocked opener and verified that the raw XLS, manifest and quality JSON remained byte-for-byte identical with unchanged modification times. Their recorded/checksummed identities agree. No customer-level canonical export was created.

## 19. Known Limitations

Default-adjudication details, undocumented codes, negative-bill explanations and precise snapshot timing remain unresolved. The data is historical and cannot establish modern population representativeness or true temporal validation. Income/employment/debt-service fields are absent. No preprocessing or model exists.

The downloader pins one verified source version and fails on changes. Atomic raw publication requires filesystem hard-link support. A socket timeout is not a total wall-clock download deadline. Only Windows/Python 3.14.6 was exercised; direct dependencies are pinned but transitive/build dependencies are not fully locked. Markdown summaries are maintained alongside generated JSON, so future source/profiler changes require coordinated documentation updates.

## 20. Deviations From Prompt

None.

## 21. Risks / Technical Debt

Phase 3 must resolve or explicitly document code treatment, demographic eligibility, monetary anomalies and evaluation design. Do not infer undocumented meanings from popular third-party conventions. Preserving raw data and training-only fitted preprocessing remains mandatory. Snapshot timing assumptions limit leakage assurance. A local checksum proves byte identity, not publisher-authenticated provenance beyond HTTPS acquisition. Runtime/platform locking and CI remain future work. No meaningful instruction contradiction was found.

## 22. Phase-3 Recommendations

Decide identifier/target exclusion from predictors, demographic-model eligibility and fairness retention, undocumented-code policy, numeric treatment and leakage-safe evaluation design. Fit any eventual preprocessing only on training partitions. Do not derive DTI from absent income/debt-service data. Document non-temporal validation honestly. These recommendations have not been implemented.

## 23. Reproduction Commands

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.data.quality
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
```

The existing virtual environment was reused for this phase and dependencies were installed successfully. On POSIX use `.venv/bin/python`. Both data CLIs accept `--project-root PATH`; imports/config loading perform no network activity.

## 24. Git Status

Sixteen tracked files are modified and 19 new project files are untracked; none is staged. The original XLS is ignored by `/data/raw/*` and is not tracked/staged. `git ls-files` lists only .gitkeep markers under raw/interim/processed. Aggregate metadata is Git-visible; synthetic fixture rows are fabricated rather than copied customer records. Phase-1 report diff is empty. HEAD remains `cf00195`; no Git commit was created.

## 25. Documentation Status

Dataset ADR, card, measured quality report, physical contract, machine-readable metadata and this report exist. README, architecture, problem definition, dataset decision, leakage/governance documents, changelog and phase tracking reflect Phase-2 behavior. The Phase-1 report remains unchanged. Final status: Phases 1–2 COMPLETED; Phases 3–10 NOT_STARTED; current completed phase is Phase 2 and next phase is Phase 3, which has not begun.

## 26. Acceptance Criteria Checklist

- [x] Existing project docs were reviewed first.
- [x] Official UCI source was verified.
- [x] Dataset final decision was documented.
- [x] Dataset ADR was created.
- [x] DOI/license/attribution were documented.
- [x] Reproducible official-source download works.
- [x] Download behavior is idempotent/safe.
- [x] Raw source file remains immutable.
- [x] Raw customer-level data is excluded from Git.
- [x] SHA-256 is recorded.
- [x] Dataset manifest exists.
- [x] Real official dataset was loaded.
- [x] Source-to-canonical mapping exists.
- [x] Physical schema is validated.
- [x] Target semantics are exact and documented.
- [x] Target binary domain is validated.
- [x] Real row count was measured.
- [x] Real column count was measured.
- [x] Real target prevalence was measured.
- [x] Missingness was measured.
- [x] Exact duplicate rows were measured.
- [x] Duplicate IDs were measured.
- [x] Repayment-status codes were analyzed.
- [x] Education codes were analyzed.
- [x] Marital-status codes were analyzed.
- [x] Major numeric anomalies were reviewed.
- [x] Sensitive/demographic fields were identified.
- [x] Dataset card exists.
- [x] Data-quality report exists.
- [x] Machine-readable quality summary exists.
- [x] Dataset-specific leakage review exists.
- [x] Temporal limitations are explicitly documented.
- [x] No model was trained.
- [x] No Phase-3 preprocessing pipeline was implemented.
- [x] Automated tests pass.
- [x] Real-data integration pipeline passes.
- [x] README matches actual functionality.
- [x] Architecture documentation is updated.
- [x] Phase-2 completion report exists.
- [x] Phase 2 status is COMPLETED.
- [x] Phase 3 remains NOT_STARTED.
- [x] No Git commit was created automatically.

## 27. Final Verdict

PHASE 2 COMPLETED
