# Overview

FastAPI V1 serves a frozen portfolio credit-risk model and requires audit persistence before returning successful inference. Service version: credit-risk-api-1.0.0. Model outputs are not lending decisions. TEST remains sealed.

# Architecture

An app factory creates routes without model/database startup side effects. Lifespan loads environment settings, verifies tracked metadata and trusted local artifact hashes, loads the preprocessor/model once, constructs TreeExplainer and the score mapper once, and initializes/checks database persistence. The runtime is held on app.state. Startup fails on missing credentials, missing/corrupt/incompatible artifacts or unavailable/unmigrated database.

The service layer is independent of HTTP, and the repository owns transactions. Runtime loading consumes metadata and artifacts only: it does not load raw data, splits or labels. Existing Phase-3 feature engineering and Phase-7 reason/score logic are reused. Explanation calls hold a lock around the shared TreeExplainer operation; prediction-only calls do not take that lock. No model or preprocessor is fitted by startup or requests.

# Authentication

Send X-API-Key to /v1/model-info, /v1/predict and /v1/explain. Missing/invalid keys receive the same generic 401. Constant-time comparison occurs before request-body reading. Keys come from the environment; empty/short/obvious placeholder keys fail configuration. Use a randomly generated secret of at least 32 characters. The configured non-secret API-key ID identifies audit records; neither logs nor database rows contain the key itself.

# Environment Variables

| Variable | Purpose/default |
| --- | --- |
| APP_ENV | development, test or production; default development |
| CREDIT_RISK_PROJECT_ROOT | Root containing configs/manifests/trusted artifacts; default current directory |
| DATABASE_URL | Required PostgreSQL URL using postgresql+psycopg |
| CREDIT_RISK_API_KEY | Required non-placeholder secret, at least 32 characters |
| CREDIT_RISK_API_KEY_ID | Required non-secret identifier, 1–100 letters/digits/underscore/dot/hyphen |
| RATE_LIMIT_REQUESTS_PER_MINUTE | Positive integer; default 60 |
| MAX_REQUEST_BODY_BYTES | Positive integer up to 1 MiB; default 65,536 |

.env.example contains placeholders only and is NOT loaded automatically. Configuration repr/errors exclude credentials. No CORS origins are allowed by default, and V1 provides no CORS override.

# Database Migration

Provision PostgreSQL and inject DATABASE_URL securely, then run:

```powershell
.venv\Scripts\python.exe -m alembic upgrade head
```

Initial revision: phase8_001. The API does not migrate or create tables automatically. Phase 8 had no live PostgreSQL server; Phase 9 subsequently verified a real PostgreSQL 17.10 Compose deployment. Temporary SQLite repository/migration tests and PostgreSQL dialect/offline migration-SQL tests passed; there is no production SQLite fallback.

# Running the API

Install dependencies, inject environment settings with actual secrets outside Git, and migrate the database before starting:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m uvicorn credit_risk.api.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

The supplied command disables generic access logging so query strings are not recorded by Uvicorn. The application emits its own allowlisted JSON operational logs. No TLS termination or cloud deployment is introduced; local Docker Compose is documented below. Model/preprocessor artifacts must already exist and match metadata; the API never trains missing replacements.

# API Versioning

All five service endpoints use /v1. Service, input-schema, model, calibration, explainability, internal-score and Alembic schema versions are independent. OpenAPI is available at /openapi.json and interactive documentation at /docs; neither contains credentials. There is no unversioned prediction or batch endpoint.

# Input Schema

Input schema financial-record-1.0.0 accepts exactly one object containing these 19 fields:

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

All fields are required and non-null. Monetary fields accept finite JSON numbers; credit_limit must be positive. Repayment statuses require strict integers in the supported Phase-3 range -2 through 9. Numeric strings, booleans, NaN/infinity, extra fields and batch arrays are rejected. Existing financial engineering performs domain/overflow validation; no new financial formulas are duplicated in HTTP code.

Negative bill amounts remain accepted. Negative payment amounts also remain accepted because the existing Phase-3 contract explicitly preserves negative monetary values: the prompt's rejection requirement is conditional on the existing contract forbidding them. Observed nonnegative payment values in the historical dataset do not establish a new domain prohibition. No interpretation is invented for repayment codes -2/0.

Identity, demographics and the target—including customer_id, name, email, telephone, address, national identifier, sex, age, education, marital_status and default_next_month—are rejected.

# POST /v1/predict

Authenticated and rate limited. Returns HTTP 200 only after mandatory audit commit. Response includes server UUID4 request_id, UTC timestamp, API/model/calibration/score versions, raw margin, raw/reported probabilities, continuous internal score, integer display score and the dataset-defined event. Values retain normal float precision. No decision, recommendation, risk band or automatic threshold action is returned.

# POST /v1/explain

Uses the same input and authentication plus Phase-7 local explanation logic. Adds explanation version, output_space=raw_margin, raw/base margin, the score-decomposition support flag and up to five positive/five negative source-level drivers. Each driver contains only source name, risk direction, margin contribution and score-point contribution. No raw source value, full 103-feature vector or full 45-source vector is returned or persisted.

The top-k excerpt is incomplete: do not sum only these selected drivers and expect the full margin/score. Positive risk SHAP lowers score points; negative risk SHAP raises them. These are diagnostics, not causal or regulatory adverse-action reasons.

# GET /v1/model-info

Authentication required. Returns safe model name/version/hash, calibration version/method, explainability version/output units, internal-score version/direction, target and no-business-decision/test-sealing flags. It exposes no local paths, secrets, database URL or threshold action.

# Health Endpoints

GET /v1/health/live is public and returns status=ok without inference, artifact loading or database queries. GET /v1/health/ready is public and checks the loaded runtime plus database reachability and compatible migrated schema. Failure returns 503 SERVICE_NOT_READY. Readiness reads no historical customer rows and does not reload artifacts.

# Output Semantics

raw_probability is the frozen XGBoost positive-class probability for default payment next month. Current identity calibration means reported_probability equals raw_probability; this is not proof of perfect calibration or regulatory PD.

internal_risk_score is the Phase-7 continuous log good:bad odds mapping: base 600, odds 50:1 and PDO 20. Higher score means lower modeled risk. It is not FICO, a bureau score, regulatory score or credit-approval score. Display score is presentation only.

SHAP explains raw XGBoost margin: base_margin + sum(ALL signed SHAP contributions) approximately equals raw_margin; sigmoid(raw_margin) approximately equals raw_probability. SHAP values do not sum directly to probability. Exact score-point decomposition requires binary logistic raw-margin SHAP, identity calibration, the fixed score mapping and no numerical clipping; otherwise unsupported additive output is disabled. Startup rejects an incompatible current contract.

# Persistence Policy

Persist only output/audit metadata and optional safe top-k driver metadata. Raw financial inputs, complete features/SHAP, API secrets, direct identity/demographics and target labels are not retained. No input fingerprint is stored. A database failure triggers rollback and HTTP 503 PERSISTENCE_ERROR; no un-audited successful result is returned. See [persistence policy](persistence.md) for schema and reconstruction limitations.

# Rate Limiting

A lock-protected sliding window allows 60 authenticated inference attempts per minute per configured API-key identity by default. Predict/explain share the allowance; invalid authenticated requests also consume it. A rejected request returns 429 RATE_LIMIT_EXCEEDED with Retry-After. Liveness/readiness and model-info are not rate limited. This is process-local: it resets at restart and does not coordinate multiple workers/instances. No Redis or distributed limiter exists.

# Error Contract

Errors use a consistent envelope:

```json
{"error":{"code":"VALIDATION_ERROR","message":"Request validation failed.","request_id":"<server-generated UUID4>"}}
```

Validation errors additionally identify safe known field locations/types, omitting rejected values and replacing arbitrary unknown names. Codes include AUTHENTICATION_FAILED (401), RATE_LIMIT_EXCEEDED (429), VALIDATION_ERROR (422), REQUEST_TOO_LARGE (413), UNSUPPORTED_MEDIA_TYPE (415), SERVICE_NOT_READY/PERSISTENCE_ERROR (503) and INTERNAL_ERROR (500). Body handling checks declared and actual streamed bytes before inference, keeping at most the configured limit. Only application/json is accepted for inference; no uploads/multipart. Unexpected errors expose no traceback, paths, SQL or credentials.

Every response has X-Request-ID and Cache-Control: no-store. Server-generated IDs ignore externally supplied identifiers. JSON logs contain request_id, known endpoint, status, non-secret key ID, model version, latency and persistence status. They omit financial bodies, scores, reasons, secrets, SQL and exception text.

# Synthetic Example

SYNTHETIC / DEMONSTRATION ONLY. The fabricated record below is not copied from a real customer:

```json
{
  "credit_limit": 200000,
  "repayment_status_2005_09": -1,
  "repayment_status_2005_08": -1,
  "repayment_status_2005_07": -1,
  "repayment_status_2005_06": -1,
  "repayment_status_2005_05": -1,
  "repayment_status_2005_04": -1,
  "bill_amount_2005_09": 20000,
  "bill_amount_2005_08": 20000,
  "bill_amount_2005_07": 20000,
  "bill_amount_2005_06": 20000,
  "bill_amount_2005_05": 20000,
  "bill_amount_2005_04": 20000,
  "payment_amount_2005_09": 20000,
  "payment_amount_2005_08": 20000,
  "payment_amount_2005_07": 20000,
  "payment_amount_2005_06": 20000,
  "payment_amount_2005_05": 20000,
  "payment_amount_2005_04": 20000
}
```

Actual frozen model fields generated from this synthetic record follow; operational UUID/timestamp placeholders are intentionally shown rather than reused as request identities:

```json
{
  "model_version": "xgboost-challenger-1.0.0",
  "calibration_version": "xgboost-calibration-1.0.0",
  "calibration_method": "identity",
  "score_version": "internal-risk-score-1.0.0",
  "raw_margin": -3.17555832862854,
  "raw_probability": 0.040095940232276917,
  "reported_probability": 0.040095940232276917,
  "internal_risk_score": 578.7501190957933,
  "display_score": 579,
  "probability_event": "default payment next month",
  "api_version": "v1",
  "request_id": "<server-generated UUID4>",
  "timestamp": "<server-generated UTC timestamp>"
}
```

Three synthetic integration cases matched direct frozen inference exactly: regular payments probability 0.040095940232276917 / score 578.7501190957933; recent delay probability 0.3201100528240204 / score 508.85754128189586; larger statements probability 0.0876188650727272 / score 554.7293398856282. Raw margin, raw/reported probability and score differences were all zero; top-k reasons matched Phase 7 exactly.

# Security Limitations

This is a portfolio implementation, not validated production deployment. No TLS termination inside the app, distributed limiter, external secret manager, multi-client credential management, observability stack or deployment hardening exists. Output audit data still require operator access/retention controls. Because raw inputs are not retained, full historical request reconstruction is unavailable. A network failure after commit can leave an uncertain response outcome; idempotency/reconciliation are not implemented.

# Not a Lending Decision

The API returns probability, score and model diagnostics. No approve/decline/manual-review action, lending cutoff, recommended credit limit or risk band exists. The historical Phase-6 threshold remains diagnostic metadata and is not used for API actions. No regulatory, causal or fairness certification is claimed.

# TEST Set Policy

TEST SET WAS NOT EVALUATED. TEST SET REMAINS SEALED. The runtime operates solely on supplied financial records and frozen artifacts. No TEST probability, SHAP, score or model metric is calculated. Real-artifact API integration uses fabricated records only.


# Phase-9 Container Run Path

See [deployment](deployment.md) for the local Compose path. The API contract and model semantics are unchanged. The container runs one worker as UID/GID 10001 with a read-only artifact mount and no raw/processed dataset access. Multiple workers/replicas require replacing the process-local limiter. A separate migration service prepares PostgreSQL; FastAPI never auto-migrates. Actual validation results are recorded in the Phase-9 completion report.

## Phase-10 lifecycle clarification

The separate final evaluator has now evaluated the frozen TEST holdout and published aggregate results. Earlier sealed-TEST statements above describe the Phase-8/9 implementation boundary: this API/persistence/deployment/operations path still does not load or evaluate dataset TEST records. Its historical metadata and audit false TEST flags remain unchanged. No TEST record is used in API demonstrations, and the monitoring baseline remains VALIDATION-only. See [final evaluation](final_evaluation_report.md) and [governance](model_governance.md).
