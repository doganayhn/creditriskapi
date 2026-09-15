# ADR 007 — Versioned API and audit persistence

## Status

Implemented in Phase 8; project-owner technical review precedes commit. No Phase 9 work is included.

## Context

Phases 1–7 provide frozen, hash-identified feature, model, calibration, explanation and score contracts. Phase 8 must serve single supplied financial records, avoid dataset/TEST access and persist versioned audit outputs without introducing lending decisions.

## Decisions

1. Use FastAPI with versioned /v1 routes and strict Pydantic request/response schemas.
2. Verify and load the model/preprocessor once in application lifespan, construct TreeExplainer once and reuse a dedicated HTTP-independent inference service. Reuse existing feature/score/reason logic. Protect shared SHAP explanation execution with a lock; prediction-only calls are not serialized by that lock.
3. Use PostgreSQL, synchronous SQLAlchemy sessions and explicit Alembic migration phase8_001. Startup checks migration/schema readiness and never creates tables automatically.
4. Persist outputs and audit identities, without raw financial request payloads, complete features/SHAP, input fingerprints or secrets.
5. Require an environment-provided API key for model-info, predict and explain, using constant-time comparison. Persist only a non-secret key ID.
6. Apply a concurrency-safe in-process sliding-window limiter to authenticated predict/explain attempts. Default: 60 requests per minute per configured key identity.
7. Commit mandatory audit data before success. Roll back failures and return a generic HTTP 503 without successful model output.
8. Keep model, calibration, explainability, score, API/service and database schema identities separate.
9. Return model outputs only. No business credit decision, risk band or threshold action exists.

## Alternatives

Per-request loading repeats expensive work and weakens startup contract verification. Async database complexity is unnecessary for the bounded synchronous service. SQLite is used solely in isolated tests, with PostgreSQL required for real startup. Silent audit failure would produce unrecorded successful responses. Persisting full raw inputs would add sensitive retention without a V1 requirement. Redis, Docker and deployment/observability infrastructure are outside this phase.

## Rationale

Startup-scoped loading follows FastAPI's lifespan model; transaction ownership is explicit and independently testable. A separate runtime loader consumes manifests and trusted artifacts only, avoiding the dataset-loading Phase-7 batch adapter. Negative payment values remain accepted because Phase 3 explicitly preserves negative monetary inputs; the prompt's negative-payment prohibition is conditional on that existing contract. The API nevertheless requires all 19 inputs to be present, numeric and finite, with supported integer repayment codes and positive credit limit.

## Consequences

Independent audit versioning is implemented with reduced raw-input retention. Exact historical input reconstruction is unavailable from this table alone. Database availability is part of readiness and successful inference. The limiter is process-local; multiple processes multiply the effective allowance. Shared SHAP work is serialized. TLS termination, rate limiting across instances, secret management, observability, retention and deployment hardening remain future work. No real PostgreSQL server was tested because DATABASE_URL was unavailable; the prompt explicitly permits isolated tests without blocking Phase 8 solely for that reason.

The required preparation verification command reproduces TRAIN-fitted preprocessing using existing behavior; artifact and historical metadata bytes remain unchanged. Service startup and requests never fit anything. This distinguishes the explicitly required reproduction command from the runtime no-fit contract.

## Sources

[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [SQLAlchemy session transactions](https://docs.sqlalchemy.org/en/20/orm/session_basics.html), [Alembic programmatic connections](https://alembic.sqlalchemy.org/en/latest/cookbook.html).
