# Architecture

Docker Compose runs PostgreSQL 17, a one-shot Alembic migration and a non-root FastAPI container. API startup waits for healthy PostgreSQL and successful migration. Only the API builds the shared application image; migration reuses it to avoid concurrent publication of the same tag. The API never auto-migrates.

# Prerequisites

Running Docker with Linux containers and Compose; existing trusted frozen artifacts; localhost port 8000 available. Python base is 3.14.6-slim-bookworm. requirements-container.txt pins the verified runtime closure, including Linux-required nvidia-nccl-cu12 pulled by the unchanged XGBoost distribution; no GPU is used. libgomp1 is the only explicitly added OS package. No developer virtualenv is used in the image. OS packages/base tags are not a fully immutable supply-chain lock; record the resolved image digest and scan independently. No vulnerability-free claim is made.

# Environment Setup

```powershell
Copy-Item .env.example .env
```

Replace local placeholders with random secrets; never commit .env. Compose interpolates POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, CREDIT_RISK_API_KEY and CREDIT_RISK_API_KEY_ID. Use URL-safe hex for the database password and URL-safe names; Compose derives DATABASE_URL with host db. The standalone host DATABASE_URL placeholder is not used inside Compose. The application itself does not read dotenv. Never publish `docker compose config` output containing resolved secrets; use `docker compose config --quiet` to validate. An unchanged API-key placeholder fails startup.

# Frozen Artifact Requirement

Supply the preprocessor and selected model at the relative paths declared in their tracked manifests under artifacts/. They stay ignored. No training fallback or artifact copying into the image exists. Missing/corrupt/incompatible artifacts fail startup.

# Build Image

```powershell
docker compose config --quiet
docker compose build --no-cache
docker compose build
```

# Start PostgreSQL

```powershell
docker compose up -d db
docker compose ps
```

No PostgreSQL host port is published. Named volume audit-data is scoped to the Compose project.

# Run Migrations

```powershell
docker compose run --rm migrate
```

Migration revision remains phase8_001. Repeated upgrade is safe. API startup does not execute migration code.

# Start API

```powershell
docker compose up -d api
docker compose ps
```

The one-shot migration dependency may run again during up; it remains an idempotent Alembic upgrade. API port defaults to 127.0.0.1:8000. API_PORT can select another local port.

# Docker Compose Workflow

All commands can use `--env-file .env.phase9 -p creditrisk-phase9` for a dedicated synthetic validation project. Do not use an unrelated developer database. No automatic volume deletion is performed. Secrets stay local and are not printed by the integration script.

# Health Checks

PostgreSQL uses pg_isready. API uses Python urllib against /v1/health/ready; no curl package is installed. /v1/health/live remains independent of database/inference. Readiness includes actual schema/connectivity. First startup imports numerical libraries and verifies frozen artifacts.

# Synthetic Smoke Test

The comprehensive synthetic-only runner also serves as a smoke check:

```powershell
.venv\Scripts\python.exe scripts/phase9_integration.py --env-file .env.phase9 --project creditrisk-phase9
```

Build first. This runner starts/restarts/stops the selected project's services and tests an outage, so use a dedicated local project. It never deletes volumes. It validates actual HTTP, safe audit rows, schema, restarts, 10 concurrent requests, rate limiting, image contents, non-root/readonly behavior and aggregate operations. It writes only ignored aggregate evidence to .local/phase9_validation.json. Unit pytest never requires Docker.

# PostgreSQL Audit Verification

```powershell
docker compose exec -T api python -m credit_risk.ops.run audit
docker compose exec -T api python -m credit_risk.ops.run summary
```

These are read-only aggregate checks. Integration compares this run's request IDs with actual rows in memory; no customer-level output file is generated.

# Restart Behavior

```powershell
docker compose restart api
docker compose restart db
```

Named volume preserves audit history. The API reloads artifacts after its restart; operational IDs/timestamps change while model fields remain deterministic. Database recovery is observed through readiness and pool pre-ping. No container healthcheck automatically restarts an unhealthy container. The integration script exercises controlled DB stop/start without corruption.

# Stopping Services

```powershell
docker compose down
```

Stops/removes this project's containers/network and preserves audit-data.

# Destroying Local Volume

```powershell
docker compose down -v
```

DESTRUCTIVE: deletes this project's local audit history. Use only for an explicitly intended reset after persistence validation. Never target unknown resources. This was not automatically run.

# Non-Root Runtime

Dockerfile USER is 10001:10001. Validate actual runtime with `docker compose exec -T api id`; the integration script also checks os.getuid/getgid. Root package installation occurs only while building the image.

# Read-Only Artifact Mount

API mounts ./artifacts at /app/artifacts read-only and disables host-path autocreation. API/migrate use read-only root filesystems, /tmp tmpfs, dropped capabilities and no-new-privileges. Source/config/metadata do not mutate at startup. No raw/interim/processed dataset is mounted. Image build context is allowlisted.

# Security Notes

No TLS termination or external secret manager. Local operators with Docker access can inspect container environment: this is not secret isolation from host administrators. Logs are allowlisted; generic HTTP access logging is disabled. Audit outputs remain sensitive and need retention/access controls. Database connection pooling retains SQLAlchemy defaults (size 5, max overflow 10), pool timeout 5 seconds, psycopg connect timeout 5 seconds and pre-ping; no throughput/SLA claim. Existing lifespan disposes the engine on graceful shutdown.

# One-Worker Limitation

Exactly one API worker because the rate limiter is process-local. Multiple workers or replicas require a shared limiter design. Restart resets allowance. No Redis or distributed deployment was added.

# Troubleshooting

Start Docker Desktop if docker info cannot reach the daemon. Check ignored secret settings without printing them. Missing artifacts must be supplied, never trained automatically. Wrong runtime/source hashes require investigation, not edits to historical manifests. For a controlled database outage readiness and audited inference should return non-success and recover after db starts. Examine logs locally for startup errors; never publish resolved secrets or raw inspect/config output.

# TEST Set Boundary

TEST SET WAS NOT EVALUATED. TEST SET REMAINS SEALED. The image has no dataset partitions; only tracked aggregates/configuration/source and separately mounted frozen binaries are used.
