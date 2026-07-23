from __future__ import annotations

import pytest

from fraud_system.config import DatabaseSettings


def test_database_url_requires_password() -> None:
    settings = DatabaseSettings(password="")

    with pytest.raises(ValueError, match="POSTGRES_PASSWORD"):
        _ = settings.sqlalchemy_url


def test_database_url_encodes_credentials() -> None:
    settings = DatabaseSettings(
        database="fraud risk",
        user="reviewer@example.com",
        password="not/a-real password",
        host="db",
        port=5433,
    )

    assert settings.sqlalchemy_url == (
        "postgresql+psycopg://reviewer%40example.com:" "not%2Fa-real+password@db:5433/fraud+risk"
    )
