from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_required_sql_layers_exist() -> None:
    bootstrap_sql = (PROJECT_ROOT / "sql/bootstrap/001_create_schemas.sql").read_text(
        encoding="utf-8"
    )

    for schema in ("raw", "staging", "features", "monitoring", "audit"):
        assert f"CREATE SCHEMA IF NOT EXISTS {schema};" in bootstrap_sql


def test_secret_file_is_ignored() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in gitignore
