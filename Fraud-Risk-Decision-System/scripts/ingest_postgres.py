"""Copy validated Parquet parts into PostgreSQL with batch lineage."""

from __future__ import annotations

import argparse
import json
from io import StringIO
from pathlib import Path

import pandas as pd

from fraud_system.config import DatabaseSettings

COPY_COLUMNS = (
    "source_row_number",
    "row_fingerprint",
    "step",
    "type",
    "amount",
    "name_orig",
    "old_balance_orig",
    "new_balance_orig",
    "name_dest",
    "old_balance_dest",
    "new_balance_dest",
    "is_fraud",
    "is_flagged_fraud",
)

DATABASE_COPY_COLUMNS = (
    "source_row_number",
    "row_fingerprint",
    "step",
    "transaction_type",
    "amount",
    "name_orig",
    "old_balance_orig",
    "new_balance_orig",
    "name_dest",
    "old_balance_dest",
    "new_balance_dest",
    "is_fraud",
    "is_flagged_fraud",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument(
        "--source-metadata", type=Path, default=Path("data/raw/source_metadata.json")
    )
    args = parser.parse_args()

    import psycopg

    settings = DatabaseSettings.from_environment()
    metadata = json.loads(args.source_metadata.read_text(encoding="utf-8"))
    quality = json.loads((args.processed_dir / "quality_summary.json").read_text(encoding="utf-8"))
    connection_info = (
        f"dbname={settings.database} user={settings.user} password={settings.password} "
        f"host={settings.host} port={settings.port}"
    )
    with psycopg.connect(connection_info) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO raw.ingestion_batch (source_name, source_sha256)
                VALUES (%s, %s)
                RETURNING ingestion_id
                """,
                (metadata["dataset_handle"], metadata["sha256"]),
            )
            ingestion_id = cursor.fetchone()[0]
        connection.commit()

        try:
            with connection.cursor() as cursor:
                copy_sql = f"""
                    COPY raw.paysim_transactions (
                        ingestion_id, {", ".join(DATABASE_COPY_COLUMNS)}
                    ) FROM STDIN WITH (FORMAT CSV)
                """
                for path in sorted(
                    (args.processed_dir / "accepted").glob("*.parquet")
                ):
                    frame = pd.read_parquet(path, columns=list(COPY_COLUMNS))
                    frame.insert(0, "ingestion_id", ingestion_id)
                    buffer = StringIO()
                    frame.to_csv(buffer, index=False, header=False)
                    buffer.seek(0)
                    with cursor.copy(copy_sql) as copy:
                        while block := buffer.read(1024 * 1024):
                            copy.write(block)

                rejected_copy_sql = """
                    COPY audit.rejected_rows (
                        ingestion_id, source_row_number, rejection_reason, source_payload
                    ) FROM STDIN WITH (FORMAT CSV)
                """
                for path in sorted(
                    (args.processed_dir / "rejected").glob("*.parquet")
                ):
                    rejected = pd.read_parquet(path)
                    payload_columns = [
                        column
                        for column in rejected.columns
                        if column not in {"source_row_number", "rejection_reason"}
                    ]
                    rejected_for_copy = pd.DataFrame(
                        {
                            "ingestion_id": ingestion_id,
                            "source_row_number": rejected["source_row_number"],
                            "rejection_reason": rejected["rejection_reason"],
                            "source_payload": rejected[payload_columns].apply(
                                lambda row: json.dumps(row.to_dict(), default=str),
                                axis=1,
                            ),
                        }
                    )
                    buffer = StringIO()
                    rejected_for_copy.to_csv(buffer, index=False, header=False)
                    buffer.seek(0)
                    with cursor.copy(rejected_copy_sql) as copy:
                        while block := buffer.read(1024 * 1024):
                            copy.write(block)

                cursor.execute(
                    """
                    UPDATE raw.ingestion_batch
                    SET completed_at = CURRENT_TIMESTAMP,
                        source_rows = %s,
                        accepted_rows = %s,
                        rejected_rows = %s,
                        status = 'completed'
                    WHERE ingestion_id = %s
                    """,
                    (
                        quality["source_rows"],
                        quality["accepted_rows"],
                        quality["rejected_rows"],
                        ingestion_id,
                    ),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE raw.ingestion_batch
                    SET completed_at = CURRENT_TIMESTAMP,
                        status = 'failed'
                    WHERE ingestion_id = %s
                    """,
                    (ingestion_id,),
                )
            connection.commit()
            raise
    print(f"Completed ingestion batch {ingestion_id}.")


if __name__ == "__main__":
    main()
