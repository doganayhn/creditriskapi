"""Explicit operator migrations; tests may inject an isolated connection."""

import os
from alembic import context
from sqlalchemy import create_engine, pool
from credit_risk.api.settings import postgres_url
from credit_risk.persistence.models import Base

config = context.config
target_metadata = Base.metadata


def migrate(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    url = postgres_url(os.environ.get("DATABASE_URL", ""))
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    migrate(config.attributes["connection"])
else:
    engine = create_engine(postgres_url(os.environ.get("DATABASE_URL", "")), poolclass=pool.NullPool,
                           hide_parameters=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            migrate(connection)
    except Exception:
        raise RuntimeError("Database migration failed; verify connectivity and migration state") from None
    finally:
        engine.dispose()
