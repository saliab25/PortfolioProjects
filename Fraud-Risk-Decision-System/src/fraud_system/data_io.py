"""File-system boundaries for prepared PaySim data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

TRAINING_COLUMNS = (
    "source_row_number",
    "step",
    "type",
    "amount",
    "name_dest",
    "old_balance_orig",
    "old_balance_dest",
    "is_fraud",
)


def load_prepared_transactions(
    accepted_dir: Path,
    *,
    columns: tuple[str, ...] = TRAINING_COLUMNS,
) -> pd.DataFrame:
    """Read validated Parquet parts in deterministic filename order."""
    paths = sorted(accepted_dir.glob("part-*.parquet"))
    if not paths:
        raise FileNotFoundError(
            f"No prepared Parquet parts found in {accepted_dir}. "
            "Run scripts/prepare_data.py first."
        )
    frames = [pd.read_parquet(path, columns=list(columns)) for path in paths]
    return pd.concat(frames, ignore_index=True)
