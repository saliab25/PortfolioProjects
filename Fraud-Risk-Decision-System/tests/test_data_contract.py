from __future__ import annotations

import pandas as pd
import pytest

from fraud_system.data_contract import validate_paysim_frame


def test_valid_rows_are_canonicalized(paysim_frame: pd.DataFrame) -> None:
    result = validate_paysim_frame(paysim_frame)

    assert result.summary == {
        "source_rows": 4,
        "accepted_rows": 4,
        "rejected_rows": 0,
        "fraud_rows": 2,
        "flagged_rows": 0,
    }
    assert result.accepted["source_row_number"].tolist() == [2, 3, 4, 5]
    assert "old_balance_orig" in result.accepted
    assert "oldbalanceOrg" not in result.accepted


def test_invalid_and_duplicate_rows_are_rejected(paysim_frame: pd.DataFrame) -> None:
    invalid = paysim_frame.iloc[[0]].copy()
    invalid.loc[:, "amount"] = -1
    duplicate = paysim_frame.iloc[[1]].copy()
    frame = pd.concat([paysim_frame, invalid, duplicate], ignore_index=True)

    result = validate_paysim_frame(frame)

    assert len(result.rejected) == 2
    assert "invalid_amount" in set(result.rejected["rejection_reason"])
    assert "duplicate_source_row" in set(result.rejected["rejection_reason"])


def test_schema_mismatch_fails_fast(paysim_frame: pd.DataFrame) -> None:
    incomplete = paysim_frame.drop(columns=["isFraud"])

    with pytest.raises(ValueError, match="Missing columns"):
        validate_paysim_frame(incomplete)
