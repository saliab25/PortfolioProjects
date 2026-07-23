"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus

from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseSettings:
    """Connection settings with development-safe, non-secret defaults."""

    database: str = "fraud_risk"
    user: str = "fraud_app"
    password: str = ""
    host: str = "localhost"
    port: int = 5432

    @classmethod
    def from_environment(cls) -> DatabaseSettings:
        """Build settings from the same variables used by Docker Compose."""
        load_dotenv()
        return cls(
            database=os.getenv("POSTGRES_DB", cls.database),
            user=os.getenv("POSTGRES_USER", cls.user),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            host=os.getenv("POSTGRES_HOST", cls.host),
            port=int(os.getenv("POSTGRES_PORT", str(cls.port))),
        )

    @property
    def sqlalchemy_url(self) -> str:
        """Return a psycopg SQLAlchemy URL with credentials safely encoded."""
        if not self.password:
            raise ValueError(
                "POSTGRES_PASSWORD is unset. Copy .env.example to .env "
                "or export the database environment variables."
            )
        user = quote_plus(self.user)
        password = quote_plus(self.password)
        database = quote_plus(self.database)
        return f"postgresql+psycopg://{user}:{password}@" f"{self.host}:{self.port}/{database}"
