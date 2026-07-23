"""Apply ordered, idempotent PostgreSQL bootstrap scripts."""

from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

from fraud_system.config import DatabaseSettings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql-dir", type=Path, default=Path("sql/bootstrap"))
    args = parser.parse_args()

    paths = sorted(args.sql_dir.glob("*.sql"))
    if not paths:
        raise FileNotFoundError(f"No SQL files found in {args.sql_dir}.")

    settings = DatabaseSettings.from_environment()
    connection_info = (
        f"dbname={settings.database} user={settings.user} password={settings.password} "
        f"host={settings.host} port={settings.port}"
    )
    with psycopg.connect(connection_info, autocommit=True) as connection:
        for path in paths:
            with connection.cursor() as cursor:
                cursor.execute(path.read_text(encoding="utf-8"))
            print(f"Applied {path}.")


if __name__ == "__main__":
    main()
