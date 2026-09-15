# ADR 008 — Containerization and model operations

## Status

Implemented for Phase 9, subject to the live validation evidence in its completion report. No Phase 10 implementation.

## Decisions

1. Docker supplies a reproducible local API runtime with Python 3.14.6 and pinned runtime dependencies.
2. PostgreSQL 17 runs in a dedicated local Compose project with a named audit volume and no published DB port.
3. A separate one-shot Alembic service waits for healthy PostgreSQL; API waits for successful migration and never auto-migrates.
4. Frozen artifacts remain ignored and externally mounted read-only, never baked into the image. Dataset directories are excluded entirely.
5. One non-root API worker preserves the documented process-local rate-limit scope. Multiple replicas require shared limiter redesign.
6. Operations read successful audit outputs and return aggregates only; no raw feature monitoring is possible.
7. Score-distribution PSI uses frozen VALIDATION aggregate bins and is a descriptive number, not a drift verdict or risk band.
8. Monitoring does not trigger retraining, artifact changes, model selection or lending decisions.
9. TEST remains sealed until an explicitly authorized final phase.

## Alternatives and consequences

Embedding artifacts or datasets would violate the existing retention/delivery boundary. Running migrations inside FastAPI would obscure lifecycle/schema ownership. Separate monitoring servers, Redis and cloud infrastructure are unnecessary for this local scope. Explicit build ownership on the API avoids concurrent same-tag image export by API/migration services; both consume the same image.

The image contains the unchanged standard XGBoost package, whose Linux dependency closure includes NCCL; this increases image size but avoids changing the verified package distribution. The runtime uses CPU inference. Base tag/OS-package resolution is not a bit-for-bit supply-chain lock; resolved versions and digest are reported. No vulnerability scan or production SLA claim is made.

Read-only root filesystems and tmpfs are used for API/migration; API artifacts are read-only. Credentials are environment-injected, so Docker-host administrators can inspect them. No external secret manager or TLS terminator exists. Successful audit rows do not reveal HTTP failure rate or realized predictive performance. Feature drift would require a separately authorized privacy-aware input telemetry design. Small synthetic traffic is demonstration only.

## References

[Compose startup ordering](https://docs.docker.com/compose/how-tos/startup-order/) and [service configuration](https://docs.docker.com/reference/compose-file/services/).
