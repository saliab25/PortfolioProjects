"""Small database boundary shared by pipelines, tests, and applications."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, text

from fraud_system.config import DatabaseSettings


def create_database_engine(settings: DatabaseSettings | None = None) -> Engine:
    """Create a pooled SQLAlchemy engine without opening a connection yet."""
    resolved_settings = settings or DatabaseSettings.from_environment()
    return create_engine(resolved_settings.sqlalchemy_url, pool_pre_ping=True)


def database_healthcheck(engine: Engine) -> dict[str, str]:
    """Confirm connectivity and report the server and current database."""
    statement = text(
        """
        SELECT
            current_database() AS database_name,
            current_user AS database_user,
            current_setting('server_version') AS server_version
        """
    )
    with engine.connect() as connection:
        row = connection.execute(statement).mappings().one()
    return dict(row)
