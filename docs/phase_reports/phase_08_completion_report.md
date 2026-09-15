# PHASE 8 COMPLETION REPORT

## 1. Objective

Expose frozen Phase-7 inference through FastAPI V1 and persist audit-safe outputs to a PostgreSQL-targeted SQLAlchemy/Alembic layer. Phase 8 is implemented and verified within the permitted isolated-database scope. No lending policy or later-phase functionality was added.

## 2. Pre-Implementation Repository State

HEAD: `9c54b410820724f38d904fda27673ff4e8ebd69e`; branch: `main`, aligned with `origin/main`. Phase 7 was committed (`9c54b41 feat: add shap explanability and internal risk score`). Working tree was clean. Phases 1–7 were COMPLETED; Phases 8–10 were NOT_STARTED. Phase 8 progressed through IN_PROGRESS to COMPLETED. HEAD remained unchanged during the original implementation. The subsequent correction starts from the existing Phase-8 commit; see Section 41.

## 3. Documentation Reviewed

Reviewed AGENTS.md, PROJECT_RULES.md, ROADMAP.md, PHASE_STATUS.md, README.md, CHANGELOG.md, pyproject.toml, .env.example and .gitignore; architecture, problem definition, data contract, leakage policy, model governance, feature engineering, modeling dataset, baseline/XGBoost/calibration/explainability/internal-score documents; ADRs 001–006; historical completion reports 1–7; dataset/feature/preprocessing/model/calibration/selection/explanation/score metadata; existing data, feature, modeling and explainability code and tests. Reconciled current phase instructions with historical scope; see Sections 37–38.

## 4. Frozen Model Contract Verification

Dataset: UCI Default of Credit Card Clients; target `default_next_month`; source event `default payment next month`. TRAIN/VALIDATION/TEST membership remains 21,000/4,500/4,500.

- Dataset SHA-256: `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`.
- Feature engineering: `financial_features_v1`.
- Preprocessing: `train_median_scale_onehot_v1`; transformed width 103.
- Preprocessor SHA-256: `e8f6ce776bd44c48871c585c5d472676ad8c418da39c513c1019bf36070ee8b4`.
- Selected model: `xgboost-challenger-1.0.0`.
- Model SHA-256: `2900f0cfe341400daeffeed7b0ef212d0a317113a657a4fcf73c332caec755ef`.
- Calibration: `xgboost-calibration-1.0.0`, identity; reported probability equals raw probability.
- Explainability: `xgboost-shap-1.0.0`, raw-margin Tree SHAP.
- Score: `internal-risk-score-1.0.0`; base 600, good:bad odds 50:1, PDO 20; unchanged.

Local artifacts exist and hashes/cross-manifest identities agree. Application logic loads historical identities from metadata. No model retraining, calibration change or threshold optimization occurred. TEST remains sealed.

## 5. API Architecture

`create_app` constructs routes without startup side effects. FastAPI lifespan validates settings/contracts, loads frozen objects once, initializes the database and checks readiness. Runtime resides on app.state. HTTP routes delegate inference to an independent service and audit transactions to a repository. Explanation calls serialize access to the shared TreeExplainer; prediction calls do not acquire that explanation lock.

## 6. Dependencies

Pre-commit consistency verification (2026-09-16): importlib.metadata, pip show and pip index versions all report **httpx2 2.13.0**; pyproject.toml declares `httpx2==2.13.0`. An explicit public-index query also lists 2.13.0. [Public PyPI release](https://pypi.org/project/httpx2/2.13.0/) provides a non-yanked wheel and source distribution. The installed distribution identifies pip as its installer and has no direct_url.json; that metadata alone does not retain the original index URL. Independently downloaded public wheel SHA-256 `fc12720cedf72faa26cca6b4ca394e05c894e7d7933fc45cafe767960804e49a` matches PyPI metadata, and all 35 installed wheel payload/metadata files match byte-for-byte (excluding installation-generated RECORD). Public reproducibility is verified; no private/local-only package or downgrade is required. The dependency declaration is unchanged.

Pinned runtime additions: FastAPI 0.141.1; Uvicorn 0.53.0; SQLAlchemy 2.0.53; Alembic 1.20.0; psycopg[binary] 3.3.5; Pydantic 2.13.5. Development HTTP test client: httpx2 2.13.0. Existing numerical/model dependencies were retained. Verification ran on Python 3.14.6; project metadata still requires Python >=3.11. One transitive Starlette/AnyIO warning remains, described in Section 29.

## 7. API Routes

| Method/path | Access / behavior |
| --- | --- |
| GET /v1/health/live | Public; process liveness, no inference |
| GET /v1/health/ready | Public; runtime and migrated database readiness |
| GET /v1/model-info | API key; safe versioned model metadata |
| POST /v1/predict | API key + rate limit; probability and score, mandatory audit |
| POST /v1/explain | API key + rate limit; same outputs plus diagnostic top-k reasons |

No batch or unversioned prediction endpoint exists.

## 8. Request Schema

One strict, required, non-null 19-field financial object; schema `financial-record-1.0.0`:

- `credit_limit`
- `repayment_status_2005_09`
- `repayment_status_2005_08`
- `repayment_status_2005_07`
- `repayment_status_2005_06`
- `repayment_status_2005_05`
- `repayment_status_2005_04`
- `bill_amount_2005_09`
- `bill_amount_2005_08`
- `bill_amount_2005_07`
- `bill_amount_2005_06`
- `bill_amount_2005_05`
- `bill_amount_2005_04`
- `payment_amount_2005_09`
- `payment_amount_2005_08`
- `payment_amount_2005_07`
- `payment_amount_2005_06`
- `payment_amount_2005_05`
- `payment_amount_2005_04`

Credit limit must be finite and positive. Status values must be strict integers within the existing -2 through 9 domain. Monetary fields must be finite JSON numbers. Strings, booleans, NaN/infinity, missing/extra fields, batch arrays, identity, demographics and target labels are rejected. Existing Phase-3 engineering validates numerical/domain behavior. Negative bill and payment amounts remain supported under the existing contract; no new financial semantics are invented.

## 9. Prediction Response Contract

Returns request_id (server UUID4), api_version, model_version, calibration_version/method, score_version, raw_margin, raw_probability, reported_probability, continuous internal_risk_score, integer display_score, probability_event and UTC timestamp. HTTP 200 follows successful audit commit. Float precision is retained; display rounding does not replace the canonical score. There is no lending decision, recommendation, risk band or threshold action.

## 10. Explanation Response Contract

Adds explanation version, raw-margin output space, raw/base margin, score-point decomposition support and up to five risk-increasing and five risk-decreasing source drivers. Drivers contain source name, direction, margin contribution and score-point contribution. No source values, demographics or full SHAP vector are exposed. Full contributions explain margin, not probability; the top-k excerpt is not the full additive sum. Positive risk SHAP lowers score points. Explanations are noncausal diagnostics, not regulatory adverse-action reasons.

## 11. Authentication

Protected endpoints require X-API-Key. CREDIT_RISK_API_KEY and a separate non-secret CREDIT_RISK_API_KEY_ID come from environment settings; .env is not automatically loaded. Empty, short and obvious placeholder keys are rejected. hmac.compare_digest performs constant-time credential comparison before body reading. Missing/invalid credentials receive generic 401. Secret values are excluded from representations, errors, logs and persistence; using the secret in the audit identity is rejected.

## 12. Rate Limiting

A lock-protected sliding 60-second window allows 60 authenticated inference attempts per minute per configured non-secret key ID by default. Predict/explain share the allowance; invalid authenticated requests consume it. Rejection returns 429 with Retry-After. Health and model-info are exempt. State is process-local and resets at restart; no cross-worker coordination or Redis exists.

## 13. Request / Error Security

Default body limit: 65,536 bytes, checked against declared and actual streamed size before inference; oversize returns 413. Inference accepts application/json only; other media types return 415. Strict validation returns 422 with safe field locations/types, without rejected values or arbitrary unknown field names. Unexpected errors return generic 500, excluding paths, SQL, tracebacks and credentials. Responses carry X-Request-ID and Cache-Control: no-store. No CORS origins are enabled. The documented Uvicorn command disables generic access logs; application logs use an allowlist.

## 14. Frozen Runtime Loading

Startup verifies trusted artifact paths, SHA-256, dataset/split/feature identities, selected model/calibration, score parameters, explanation lineage/configuration, source hashes, feature order/width and runtime versions. It loads one preprocessor, one native XGBoost, one TreeExplainer and one score mapper. Missing, corrupt or incompatible inputs fail startup. Tests spy on construction/load counts and prohibit per-request manifest reads and fitting. Runtime reads metadata/artifacts only, without raw data, partition records or labels.

## 15. Inference Consistency Validation

Three fabricated records were passed through the real frozen service and compared with direct frozen inference. For every case, absolute raw-margin, raw-probability, reported-probability and continuous-score differences were **0.0**.

| Synthetic case | Raw/reported probability | Continuous score |
| --- | ---: | ---: |
| Regular payments | 0.040095940232276917 | 578.7501190957933 |
| Recent delay | 0.3201100528240204 | 508.85754128189586 |
| Larger statements | 0.0876188650727272 | 554.7293398856282 |

Regular-payments raw margin: -3.17555832862854; display score: 579. These are synthetic integration outputs, not TEST results.

## 16. Explanation Consistency Validation

Real frozen synthetic explanation integration matched direct Phase-7 top-k source identities, rankings, signed margin contributions, base margin and score-point contributions exactly. Regular-payments base margin was -1.2638622522354126. Repeated calls retained the same model fields. No demographics, full transformed feature array or full SHAP/source vector appeared in response or persisted reasons.

## 17. Persistence Architecture

PostgreSQL via psycopg is the configured production target, with no production SQLite fallback. One SQLAlchemy engine/session factory is initialized during lifespan and disposed at shutdown. The repository owns one session/transaction per inference event; HTTP routes contain no SQL. Responses are validated before audit construction, then the transaction commits before success is returned. Engine configuration disables SQL echo, hides bound parameters and uses connection/pool acquisition timeouts.

## 18. Database Schema

`prediction_events` contains:

- Request: request_id (UUID primary key), created_at (timezone-aware UTC), endpoint_type, api_version, request_schema_version, api_key_id.
- Model: model_name, model_version, model_artifact_sha256.
- Calibration: calibration_version, calibration_method.
- Explanation/score: nullable explainability_version, score_version.
- Outputs: raw_margin, raw_probability, reported_probability, internal_risk_score, display_score.
- Diagnostics: explanation_requested, nullable score_point_decomposition_supported, nullable reason_codes_json.
- Operations: inference_latency_ms, test_set_evaluated.

Indexes cover created_at, model_version and api_key_id. Constraints enforce probability ranges [0,1], nonnegative latency, predict/explain endpoint type, false TEST-evaluated flag and unique request identity. Required columns are non-null. UTC binding rejects naive timestamps; isolated SQLite reads restore timezone explicitly.

## 19. Persistence Privacy Policy

Raw financial inputs are NOT persisted. API secrets are NOT persisted. Full features and full SHAP vectors are NOT persisted. Identity/demographics and target labels are not retained. Optional explanation JSON contains only safe top-k names, directions and contributions. No input fingerprint is stored. Output audit data still require access/retention controls; complete historical request reconstruction is unavailable.

## 20. Alembic

Revision `phase8_001` creates the audit table and three indexes. Temporary isolated SQLite tests passed upgrade, repeated upgrade, downgrade and re-upgrade. PostgreSQL dialect checks and offline migration SQL generation passed without a connection. Production startup never runs create_all or automatic migrations. No live PostgreSQL migration was executed because DATABASE_URL was unavailable.

## 21. Persistence Failure Behavior

Write/commit failure rolls back, closes the session and returns HTTP 503 PERSISTENCE_ERROR with the server request ID. No unaudited success response is returned. Logs record failed persistence without SQL or exception text. No automatic retry/idempotency is implemented; a network failure after commit can leave an uncertain client-visible outcome.

## 22. Health / Readiness

Liveness returns status=ok without inference or database queries. Readiness requires a loaded runtime, SELECT 1 connectivity, exact Alembic revision, expected column shape/types/nullability, UUID primary identity, required check constraints and a zero-row schema query. PostgreSQL timestamp timezone is checked. Failure returns 503 SERVICE_NOT_READY. Readiness does not reload artifacts or read historical customer rows.

## 23. Structured Logging

Allowlisted JSON fields: request_id, known endpoint, response status, non-secret API-key ID, model version, latency and persistence status. Response/log/database request IDs agree. Financial inputs, query strings, scores, reasons, API secrets, SQL, local paths and exception text are excluded. Unknown paths are logged as unmatched rather than arbitrary user text.

## 24. API Manifest

`data/metadata/api_manifest.json` records API v1, service credit-risk-api-1.0.0, input schema financial-record-1.0.0, frozen model/preprocessing/calibration/explanation/score identities, five routes and database revision phase8_001. It records API-key authentication, in-process rate limiting, PostgreSQL target, no raw-input persistence, no business decision and sealed TEST. It contains aggregate/configuration metadata only and no credentials. Explicit manifest publication preserves its timestamp when content is unchanged; startup/requests never rewrite it.

## 25. Test Set Status

TEST SET WAS NOT EVALUATED.

TEST SET REMAINS SEALED.

No TEST probability, SHAP, internal score or model metric was calculated. Required feature preparation performed structural partition reproduction only; real-artifact API checks used fabricated inputs.

## 26. Files Created

- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/phase8_001_prediction_events.py`
- `data/metadata/api_manifest.json`
- `docs/api.md`
- `docs/decisions/007-api-and-persistence.md`
- `docs/persistence.md`
- `docs/phase_reports/phase_08_completion_report.md`
- `src/credit_risk/api/__init__.py`
- `src/credit_risk/api/errors.py`
- `src/credit_risk/api/main.py`
- `src/credit_risk/api/manifest.py`
- `src/credit_risk/api/middleware.py`
- `src/credit_risk/api/rate_limit.py`
- `src/credit_risk/api/schemas.py`
- `src/credit_risk/api/security.py`
- `src/credit_risk/api/settings.py`
- `src/credit_risk/persistence/__init__.py`
- `src/credit_risk/persistence/database.py`
- `src/credit_risk/persistence/models.py`
- `src/credit_risk/persistence/repository.py`
- `src/credit_risk/service/__init__.py`
- `src/credit_risk/service/inference.py`
- `src/credit_risk/service/runtime.py`
- `tests/test_api.py`
- `tests/test_service_runtime.py`

## 27. Files Modified

- `.env.example`
- `CHANGELOG.md`
- `PHASE_STATUS.md`
- `PROJECT_RULES.md`
- `README.md`
- `ROADMAP.md`
- `docs/architecture.md`
- `docs/model_governance.md`
- `pyproject.toml`

## 28. Tests Executed

Additional commands for the 2026-09-16 consistency verification:

```powershell
.venv\Scripts\python.exe -c "import importlib.metadata; print(importlib.metadata.version('httpx2'))"
.venv\Scripts\python.exe -m pip show httpx2
.venv\Scripts\python.exe -m pip index versions httpx2
.venv\Scripts\python.exe -m pip index versions httpx2 --index-url https://pypi.org/simple
```

A Python verification fetched public PyPI JSON and the wheel, checked its SHA-256 and compared installed files. The required editable install, full pytest, pip check, whitespace/status and individual historical-diff commands below were rerun for this correction. Data download and feature preparation commands below belong to the original Phase-8 verification and were not rerun during this correction.

Exact CLI commands executed during implementation/verification (some repeated after fixes):

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m credit_risk.api.manifest
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m pytest tests/test_api.py -q
.venv\Scripts\python.exe -m pytest tests/test_service_runtime.py -q -s
.venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_service_runtime.py -q
.venv\Scripts\python.exe -m pytest tests/test_api.py::test_migration_upgrade_repeat_downgrade_and_schema -q
.venv\Scripts\python.exe -m pytest tests/test_api.py::test_alembic_offline_postgresql_sql -q
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
git ls-files data/raw data/interim data/processed artifacts
git diff --name-only -- data/metadata docs/phase_reports
git diff --stat
git log --oneline --decorate -7
git status
git rev-parse HEAD
git diff --cached --name-only
git diff -- docs/phase_reports/phase_01_completion_report.md
git diff -- docs/phase_reports/phase_02_completion_report.md
git diff -- docs/phase_reports/phase_03_completion_report.md
git diff -- docs/phase_reports/phase_04_completion_report.md
git diff -- docs/phase_reports/phase_05_completion_report.md
git diff -- docs/phase_reports/phase_06_completion_report.md
git diff -- docs/phase_reports/phase_07_completion_report.md
git diff -- data/metadata/baseline_model_manifest.json
git diff -- data/metadata/xgboost_model_manifest.json
git diff -- data/metadata/xgboost_search_results.csv
```

Alembic upgrade/downgrade/re-upgrade and offline PostgreSQL SQL generation ran programmatically in the named isolated tests. A live PostgreSQL `alembic upgrade head` was NOT executed.

## 29. Test Results

Final consistency-fix verification (2026-09-16): **339 passed, 0 failed, 0 skipped, 1 warning in 65.33 seconds**. Editable installation succeeded; every installed package version remained unchanged. pip check returned **No broken requirements found.** git diff --check passed. The warning remains the same upstream Starlette/AnyIO deprecation. All synthetic real-artifact inference/explanation, authentication, rate-limit and persistence tests passed again. The 133 genuine acceptance criteria remain checked; the PostgreSQL N/A limitation remains explicit.

Original implementation verification: **339 passed, 0 failed, 0 skipped, 1 warning in 59.28 seconds**. This includes 70 Phase-8 tests (55 API/persistence/security cases and 15 runtime cases), plus 269 existing tests. pip check: **No broken requirements found.** git diff --check passed. Download verified the 30,000-row dataset checksum; prepare reproduced finite TRAIN 21,000×103, VALIDATION 4,500×103 and TEST 4,500×103 matrices without predictive TEST evaluation.

An intermediate schema-readiness hardening run produced 2 failures and 42 setup errors because SQLite reflects UUID as CHAR(32). Removing the redundant incompatible length comparison fixed it; focused checks and subsequent full suites passed. An initial HTTP-client deprecation was resolved with httpx2. The final remaining warning is Starlette TestClient use of deprecated `anyio.abc.BlockingPortal`; it recommends `anyio.from_thread.BlockingPortal`. No warning was suppressed.

## 30. Synthetic Real-Artifact Integration

Integration used trusted local frozen artifacts copied into an isolated project containing metadata/configuration but no raw-data directory. The fabricated base input has credit limit 200,000, six repayment statuses -1, six bills 20,000 and six payments 20,000. Variants set the latest status to 2/latest payment to 0, or all bills to 180,000. No real customer record was copied. All real-artifact integration tests ran; none skipped. Tests prohibit fitting and raw-data loading and compare API/service outputs with direct Phase-7 computations.

## 31. PostgreSQL Integration Status

Implemented target: PostgreSQL + SQLAlchemy + psycopg, including Alembic migration and fail-closed audit repository. Executed validation: temporary SQLite migration/repository/API transactions plus PostgreSQL dialect/driver and offline SQL generation. **A real PostgreSQL server was NOT tested; DATABASE_URL was not configured.** No migration/write/read or concurrency success is claimed against live PostgreSQL. The phase prompt explicitly permits completion with this environment-dependent limitation.

## 32. Determinism Validation

Identical synthetic requests and frozen artifacts produced identical margin, raw/reported probabilities, continuous score, reason rankings and contributions. Request UUID, timestamp and latency are intentionally operational and may differ. Manifest regeneration was byte-identical when aggregate content was unchanged. Historical experiment metadata remained unchanged.

## 33. Security Validation

Passing tests cover missing/invalid keys and constant-time comparison; deterministic/concurrent limiter behavior; declared/streamed body limits; strict schema and finite values; identity/demographic rejection; safe unknown-field errors; generic internal/persistence failures; no-secret logs/persistence; request-ID correlation; UTC timestamps; protected routes; default CORS; fail-fast startup; no-fit/no-load request behavior and transaction rollback. This is tested portfolio security behavior, not a production or regulatory certification.

## 34. Git / Privacy Validation

Raw/interim/processed datasets and model binaries remain ignored. `git ls-files data/raw data/interim data/processed artifacts` returns only the four .gitkeep files. No customer-level output artifact or real API secret is tracked. .env.example contains placeholders only; tests and documentation use fabricated financial inputs. No files are staged, no Git commit was created and HEAD is unchanged.

## 35. Historical Integrity Validation

Correction verification: all ten individually requested historical report/experiment diffs were rerun and are EMPTY. A before/after SHA-256 inventory confirmed source code, tests, frozen artifacts and all metadata are byte-identical. The required editable install refreshed ignored packaging egg-info files only; no package versions changed. Selected XGBoost, identity calibration, artifact hashes, synthetic API numeric outputs, persistence policy and authentication/rate-limit behavior remain unchanged. TEST remains sealed; no Docker work or Phase 9 work started.

All seven individual historical phase-report diffs are EMPTY. Baseline manifest, XGBoost manifest and XGBoost search-results diffs are EMPTY. All other existing tracked metadata also remain unchanged; api_manifest.json is the only new metadata artifact. Frozen feature/model/calibration/explanation implementations and historical experiment results were not edited.

## 36. Known Limitations

Single-process in-memory rate limiter; no TLS termination inside the app; no distributed deployment; no external secret manager or multi-client credential management; no full historical request reconstruction because raw inputs are omitted; no production observability stack; live PostgreSQL behavior unverified; TEST evaluation pending; no business lending policy. Real-artifact tests require ignored frozen local artifacts and explicitly skip if absent rather than training replacements. Output audit retention/access and uncertain-commit reconciliation remain operator/future-design concerns.

## 37. Deviations From Prompt

2026-09-16 correction: no dependency change was necessary; installed/pinned httpx2 2.13.0 is publicly reproducible. Removed the erroneous standalone checked “incomplete” line and corrected the acceptance count from 134 to 133. The legitimate live-PostgreSQL N/A entry is preserved. Only this completion report is changed by this correction; the reviewed implementation remains untouched.

The prompt both prohibits fitting preprocessing and explicitly requires the existing features.prepare CLI, which fits the TRAIN preprocessor. The required reproduction command was executed; it reproduced unchanged preprocessing artifact/metadata identities. This is a verification-command exception to the general no-fit wording, not runtime fitting. Service startup and requests never fit preprocessing or any model. No model was retrained.

Negative payments remain accepted because the prompt makes their rejection conditional on the existing contract forbidding them; Phase 3 preserves negative monetary values. No new prohibition was invented. Live PostgreSQL validation was unavailable under the prompt's explicit isolated-test allowance. No other functional scope reduction was made.

## 38. Risks / Technical Debt

Current Phase-8 instructions supersede the old roadmap reference to business rules; documentation now describes inference/audit only. The no-fit versus required prepare-command tension is disclosed above. Phase-7 TRAIN OOF score statistics remain unavailable under the owner's no-retraining decision. Exact runtime-version/source pins intentionally reject incompatible artifact environments. SQLite tests cannot establish live PostgreSQL schema reflection, concurrency, transaction/network or deployment behavior. The upstream Starlette/AnyIO deprecation remains. No idempotency/reconciliation or audit-retention automation exists, and output-only persistence limits reconstruction. No claim of production/regulatory readiness is made.

## 39. Phase-9 Recommendations

Recommendations only: validate migration/startup/readiness and rollback against a provisioned PostgreSQL server; test concurrent workers and failure recovery; plan TLS, secure credentials and retention controls; add the authorized container/operational tests; address dependency warnings and deployment reproducibility. Preserve frozen model contracts and keep TEST sealed until the authorized final evaluation. None of this Phase-9 work was started.

## 40. Reproduction / Run Commands

Use existing trusted frozen artifacts. Inject DATABASE_URL, CREDIT_RISK_API_KEY and CREDIT_RISK_API_KEY_ID securely; placeholders in .env.example must be replaced outside Git. These are operator instructions; the live PostgreSQL migration/start commands below are not claimed as executed here.

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn credit_risk.api.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
```

Optional explicit aggregate manifest reproduction: `.venv\Scripts\python.exe -m credit_risk.api.manifest`. The service never regenerates missing artifacts.

## 41. Git Status

The listing below records the original Phase-8 implementation before the owner checkpoint. Current correction status is recorded afterward.

9 modified files and 26 new files, all unstaged. HEAD remains the Phase-7 commit. Nothing was automatically committed. Phase 9 and Phase 10 remain NOT_STARTED.

```text
 M .env.example
 M CHANGELOG.md
 M PHASE_STATUS.md
 M PROJECT_RULES.md
 M README.md
 M ROADMAP.md
 M docs/architecture.md
 M docs/model_governance.md
 M pyproject.toml
?? alembic.ini
?? alembic/env.py
?? alembic/versions/phase8_001_prediction_events.py
?? data/metadata/api_manifest.json
?? docs/api.md
?? docs/decisions/007-api-and-persistence.md
?? docs/persistence.md
?? docs/phase_reports/phase_08_completion_report.md
?? src/credit_risk/api/__init__.py
?? src/credit_risk/api/errors.py
?? src/credit_risk/api/main.py
?? src/credit_risk/api/manifest.py
?? src/credit_risk/api/middleware.py
?? src/credit_risk/api/rate_limit.py
?? src/credit_risk/api/schemas.py
?? src/credit_risk/api/security.py
?? src/credit_risk/api/settings.py
?? src/credit_risk/persistence/__init__.py
?? src/credit_risk/persistence/database.py
?? src/credit_risk/persistence/models.py
?? src/credit_risk/persistence/repository.py
?? src/credit_risk/service/__init__.py
?? src/credit_risk/service/inference.py
?? src/credit_risk/service/runtime.py
?? tests/test_api.py
?? tests/test_service_runtime.py
```

Current consistency-fix state (2026-09-16): the repository was clean at existing Phase-8 HEAD `169e5156012a26ef4a83b371d644f071da8849bf` before this correction. That HEAD remains unchanged. Only this report is modified, unstaged; no commit was created by Codex. Phase 9 remains NOT_STARTED.

```text
 M docs/phase_reports/phase_08_completion_report.md
```

## 42. Documentation Status

Created API documentation, persistence documentation, ADR 007 and this report. Updated README, ROADMAP, PHASE_STATUS, CHANGELOG, architecture and model-governance documentation, plus the auditability description in PROJECT_RULES and environment/dependency configuration. Phase 8 is COMPLETED; next phase is Phase 9, not started. Historical reports remain intact. Documentation distinguishes implemented persistence from isolated tests and unavailable live PostgreSQL validation.

## 43. Acceptance Criteria Checklist

All 133 applicable Section-88 criteria are reproduced below. Live-server validation is separately identified as not performed; it is not silently counted as complete.

- [x] Required project documentation was reviewed.
- [x] Phase 7 is committed.
- [x] Repository was clean before implementation.
- [x] Frozen dataset/model/preprocessor contracts were verified.
- [x] Selected model remains XGBoost.
- [x] Selected calibration remains identity.
- [x] Underlying model was NOT retrained.
- [x] Hyperparameters were NOT retuned.
- [x] Calibration was NOT changed.
- [x] Internal-score parameters were NOT changed.
- [x] TEST remained sealed.
- [x] FastAPI dependency added.
- [x] SQLAlchemy dependency added.
- [x] Alembic dependency added.
- [x] PostgreSQL driver added.
- [x] `/v1` API versioning exists.
- [x] `/v1/health/live` exists.
- [x] `/v1/health/ready` exists.
- [x] `/v1/model-info` exists.
- [x] `/v1/predict` exists.
- [x] `/v1/explain` exists.
- [x] Prediction/model endpoints require authentication.
- [x] API key comes from environment/configuration.
- [x] No real API key is committed.
- [x] Constant-time API-key comparison is used where applicable.
- [x] API-key secret is never persisted.
- [x] API-key secret is never logged.
- [x] Basic rate limiting is implemented.
- [x] Rate limiting is documented as in-process only.
- [x] Request body-size limit exists.
- [x] Unknown request fields are rejected.
- [x] customer_id is rejected.
- [x] Demographic fields are rejected.
- [x] NaN/inf are rejected.
- [x] Credit limit domain validation exists.
- [x] Repayment status validation exists.
- [x] Payment amount validation exists.
- [x] Negative valid bill amounts remain supported.
- [x] Model/preprocessor artifacts load once at startup.
- [x] TreeExplainer is not recreated per explanation request.
- [x] Artifact SHA-256 is verified at startup.
- [x] Startup fails clearly for artifact mismatch.
- [x] Request path never calls model/preprocessor fit.
- [x] Existing Phase-3 feature engineering is reused.
- [x] Existing Phase-7 score implementation is reused.
- [x] Existing Phase-7 reason-code logic is reused.
- [x] `/v1/predict` returns raw probability.
- [x] `/v1/predict` returns reported probability.
- [x] `/v1/predict` returns internal continuous score.
- [x] `/v1/predict` returns display score.
- [x] `/v1/predict` contains no lending decision.
- [x] `/v1/explain` identifies raw-margin explanation space.
- [x] `/v1/explain` returns source-level top drivers only.
- [x] `/v1/explain` does not expose full SHAP vector.
- [x] `/v1/explain` does not expose demographics.
- [x] SHAP is not claimed to sum directly to probability.
- [x] Internal score is not called FICO.
- [x] Internal score is not called regulatory score.
- [x] Phase-6 technical threshold is not used as business decision.
- [x] Server-generated request_id exists.
- [x] Same request_id reaches response/log/persistence.
- [x] UTC timezone-aware timestamping is used.
- [x] Structured logging exists.
- [x] Financial request body is not logged.
- [x] Validation error response avoids echoing full financial values.
- [x] PostgreSQL is the documented production persistence target.
- [x] SQLAlchemy repository layer exists.
- [x] Alembic migration exists.
- [x] Production startup does not call create_all automatically.
- [x] prediction-events audit table exists.
- [x] Model version is persisted.
- [x] Model artifact hash is persisted.
- [x] Calibration version is persisted.
- [x] Score version is persisted.
- [x] Explainability version is persisted where applicable.
- [x] Raw probability is persisted.
- [x] Reported probability is persisted.
- [x] Internal score is persisted.
- [x] Raw financial request is NOT persisted.
- [x] Full transformed feature vector is NOT persisted.
- [x] Full SHAP vector is NOT persisted.
- [x] Explain endpoint may persist only safe top-k reason metadata.
- [x] API-key ID may be persisted.
- [x] API-key secret is NOT persisted.
- [x] Persistence uses explicit transaction handling.
- [x] DB failure causes rollback.
- [x] Mandatory audit persistence failure returns non-success.
- [x] Readiness includes database reachability.
- [x] Liveness does not run inference.
- [x] Service layer is independent from HTTP route implementation.
- [x] Repository layer is independent from HTTP route implementation.
- [x] API modules can be imported without real startup side effects.
- [x] Deterministic synthetic prediction integration matches frozen model.
- [x] Deterministic synthetic explanation matches Phase-7 implementation.
- [x] Startup loading tests pass.
- [x] Authentication tests pass.
- [x] Rate-limiter tests pass.
- [x] Body-limit tests pass.
- [x] Schema-validation tests pass.
- [x] Persistence tests pass.
- [x] Persistence-failure tests pass.
- [x] Health tests pass.
- [x] Error-privacy tests pass.
- [x] No-fit request-path tests pass.
- [x] Alembic migration tests pass.
- [x] No Docker files were created.
- [x] No MLflow integration was added.
- [x] No Redis dependency was added.
- [x] No business decision engine exists.
- [x] No risk bands exist.
- [x] No new threshold was optimized.
- [x] No TEST probability was calculated.
- [x] No TEST SHAP was calculated.
- [x] No TEST score was calculated.
- [x] No TEST metric was calculated.
- [x] `api_manifest.json` exists.
- [x] API documentation exists.
- [x] Persistence documentation exists.
- [x] ADR 007 exists.
- [x] `.env.example` contains placeholders only.
- [x] Real frozen-artifact service integration succeeded with synthetic input.
- [x] Full automated test suite passes.
- [x] pip check passes.
- [x] git diff --check passes.
- [x] Historical completion reports remain unchanged.
- [x] Historical experiment metadata remains unchanged.
- [x] No customer-level output artifact is tracked.
- [x] README matches actual implementation.
- [x] Architecture documentation is updated.
- [x] Phase-8 completion report exists.
- [x] Phase 8 status is COMPLETED.
- [x] Phase 9 remains NOT_STARTED.
- [x] No Git commit was created automatically.

- [N/A] Live PostgreSQL server migration/write/read verification: environment-dependent; DATABASE_URL unavailable, NOT performed. PostgreSQL dialect/offline SQL and isolated database tests passed as explicitly permitted by the prompt.

## 44. Final Verdict

PHASE 8 COMPLETED
