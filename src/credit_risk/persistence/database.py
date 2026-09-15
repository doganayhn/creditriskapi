"""Engine lifecycle and read-only migration/schema readiness checks."""

from sqlalchemy import create_engine, inspect, select, text, false, Float
from sqlalchemy.orm import sessionmaker

from credit_risk.api.settings import postgres_url
from credit_risk.persistence.models import PredictionEvent, SCHEMA_REVISION


class Database:
    def __init__(self, engine):
        self.engine = engine
        self.sessions = sessionmaker(engine, expire_on_commit=False)

    @classmethod
    def connect(cls, database_url):
        url = postgres_url(database_url)
        engine = create_engine(url, pool_pre_ping=True, pool_timeout=5, hide_parameters=True,
                               connect_args={"connect_timeout": 5}, echo=False)
        return cls(engine)

    def check_ready(self):
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
            if revision != [SCHEMA_REVISION]:
                raise ValueError("Database migration revision is incompatible")
            inspector = inspect(connection)
            columns = {column["name"]: column for column in inspector.get_columns("prediction_events")}
            expected = PredictionEvent.__table__
            if set(columns) != set(expected.columns.keys()) or any(
                    columns[col.name]["nullable"] != col.nullable for col in expected.columns):
                raise ValueError("Database audit schema is incompatible")
            for column in expected.columns:
                actual_type = columns[column.name]["type"]
                expected_type = column.type.impl if hasattr(column.type, "impl") else column.type
                same_float = isinstance(actual_type, Float) and isinstance(expected_type, Float)
                if not same_float and str(actual_type.compile(dialect=connection.dialect)) != str(expected_type.compile(dialect=connection.dialect)):
                    raise ValueError("Database audit column type is incompatible")
            if inspector.get_pk_constraint("prediction_events")["constrained_columns"] != ["request_id"]:
                raise ValueError("Database audit primary identity is incompatible")
            if connection.dialect.name == "postgresql" and not columns["created_at"]["type"].timezone:
                raise ValueError("Database timestamp must preserve timezone")
            checks = {constraint["name"] for constraint in inspector.get_check_constraints("prediction_events")}
            if not {"ck_raw_probability", "ck_reported_probability", "ck_test_sealed", "ck_latency", "ck_endpoint"} <= checks:
                raise ValueError("Database audit constraints are missing")
            connection.execute(select(expected).where(false()))  # Shape check; no customer rows read.

    def close(self):
        self.engine.dispose()
