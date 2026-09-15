FROM python:3.14.6-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CREDIT_RISK_PROJECT_ROOT=/app NUMBA_CACHE_DIR=/tmp/numba
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY requirements-container.txt pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir -r requirements-container.txt \
    && python -m pip install --no-cache-dir --no-deps . && python -m pip check
COPY configs ./configs
COPY data/metadata ./data/metadata
COPY alembic.ini ./
COPY alembic ./alembic
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "credit_risk.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
