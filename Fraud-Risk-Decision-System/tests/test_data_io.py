from __future__ import annotations

import pandas as pd
import pytest

from fraud_system.data_io import TRAINING_COLUMNS, load_prepared_transactions


def test_load_prepared_transactions_orders_and_combines_parts(tmp_path) -> None:
    first = pd.DataFrame({column: [1] for column in TRAINING_COLUMNS})
    first["type"] = "PAYMENT"
    first["name_dest"] = "M1"
    second = first.copy()
    second["source_row_number"] = 2
    second.to_parquet(tmp_path / "part-00002.parquet", index=False)
    first.to_parquet(tmp_path / "part-00001.parquet", index=False)

    loaded = load_prepared_transactions(tmp_path)

    assert loaded["source_row_number"].tolist() == [1, 2]


def test_load_prepared_transactions_requires_parts(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="prepare_data"):
        load_prepared_transactions(tmp_path)
