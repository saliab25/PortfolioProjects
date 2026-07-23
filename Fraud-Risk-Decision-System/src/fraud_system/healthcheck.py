"""Command-line database connectivity check."""

from __future__ import annotations

import json

from fraud_system.database import create_database_engine, database_healthcheck


def main() -> None:
    """Print database health information as machine-readable JSON."""
    engine = create_database_engine()
    result = database_healthcheck(engine)
    print(json.dumps({"status": "ok", **result}, indent=2))


if __name__ == "__main__":
    main()
