# Local Docker startup correction — 2026-09-19

## Scope

Post-Phase-10 local deployment diagnosis and configuration repair. This is not
a new phase. Historical completion reports and frozen evaluation artifacts
remain unchanged. No commit or tag was created.

## Root cause

The resolved Compose CREDIT_RISK_API_KEY contained the placeholder marker
`replace`. Presence and sufficient length did not make it valid: Settings
deliberately rejects this marker. The key-length/diversity checks, key-ID
format, APP_ENV, numeric limits and PostgreSQL URL checks otherwise passed.
The generic startup message suppressed the specific validation reason to
avoid disclosing environment values. PostgreSQL's own POSTGRES_* variables
are not needed in the API environment when DATABASE_URL is valid.

## Correction

Generated a cryptographically random 32-byte hex API key using Python secrets
and replaced only CREDIT_RISK_API_KEY in the ignored local `.env`. No secret
was printed. Compose resolved the new value, and the API was recreated to
receive it. Clients must use that same local key.

No application code, dependency, validation rule, database credential, model,
preprocessor, calibration, score, explanation or persistence contract changed.
No database volume was deleted. The owner's pre-existing edits to the tracked
`.env.example` were preserved; credentials belong in ignored `.env` only.
Added settings-specific troubleshooting to the deployment guide.

## Verification

Executed:

```powershell
docker compose run --rm --no-deps --entrypoint python api -c "from credit_risk.api.settings import Settings; Settings.from_env(); print('SETTINGS_OK')"
docker compose up -d db
docker compose run --rm migrate
docker compose up -d --force-recreate api
.venv\Scripts\python.exe -m pytest tests/test_api.py -q
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
docker compose ps
```

Resolved Compose settings were inspected in memory only, without printing
credentials. Container settings check returned SETTINGS_OK; migration exited
0. Local API probes returned liveness 200, readiness 200, authenticated
model-info 200 and unauthenticated model-info 401. Both API and PostgreSQL are
healthy; API is available at localhost port 8000 and left running for the owner.

API tests: **55 passed, one existing upstream Starlette/AnyIO deprecation
warning, 20.22 seconds**. Pip check found no broken requirements. Git whitespace
check passed. No new tests were needed for this configuration-only correction;
live checks exercised the actual failing environment. No TEST evaluation,
training or customer prediction request was performed.

## Files and limitations

Changed ignored local `.env` and the deployment guide; created this correction
report. `.env.example` was already modified when diagnosis began and was not
edited by this fix. Historical reports/metadata and frozen dependency hashes
remain intact. The generic startup exception remains intentionally unchanged;
the documented settings-only check isolates this failure safely.
