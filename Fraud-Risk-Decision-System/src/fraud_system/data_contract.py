"""PaySim schema contract and row-level validation.

The raw CSV has no transaction identifier, so ``source_row_number`` is retained
as lineage. It is not a business identifier: it only tells us where a record
came from in a particular source file.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

SOURCE_COLUMNS = (
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
)

COLUMN_RENAMES = {
    "nameOrig": "name_orig",
    "oldbalanceOrg": "old_balance_orig",
    "newbalanceOrig": "new_balance_orig",
    "nameDest": "name_dest",
    "oldbalanceDest": "old_balance_dest",
    "newbalanceDest": "new_balance_dest",
    "isFraud": "is_fraud",
    "isFlaggedFraud": "is_flagged_fraud",
}

TRANSACTION_TYPES = frozenset({"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"})
NUMERIC_COLUMNS = (
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
)
BALANCE_COLUMNS = tuple(column for column in NUMERIC_COLUMNS if column != "amount")


@dataclass(frozen=True)
class ValidationResult:
    """Accepted and rejected records plus compact quality counts."""

    accepted: pd.DataFrame
    rejected: pd.DataFrame
    summary: dict[str, int]


def assert_source_columns(frame: pd.DataFrame) -> None:
    """Fail fast when the file is not the PaySim shape we documented."""
    actual = tuple(frame.columns)
    missing = sorted(set(SOURCE_COLUMNS) - set(actual))
    unexpected = sorted(set(actual) - set(SOURCE_COLUMNS))
    if missing or unexpected:
        raise ValueError(
            "PaySim schema mismatch. "
            f"Missing columns: {missing or 'none'}; "
            f"unexpected columns: {unexpected or 'none'}."
        )


def _reason_series(frame: pd.DataFrame) -> pd.Series:
    """Return one pipe-separated rejection reason per invalid row."""
    reasons = pd.Series("", index=frame.index, dtype="string")

    checks: dict[str, pd.Series] = {
        "missing_required_value": frame[list(SOURCE_COLUMNS)].isna().any(axis=1),
        "invalid_step": pd.to_numeric(frame["step"], errors="coerce").lt(1),
        "invalid_transaction_type": ~frame["type"].isin(TRANSACTION_TYPES),
        "invalid_amount": pd.to_numeric(frame["amount"], errors="coerce").lt(0),
        "invalid_balance": frame[list(BALANCE_COLUMNS)]
        .apply(pd.to_numeric, errors="coerce")
        .lt(0)
        .any(axis=1),
        "invalid_fraud_label": ~frame["isFraud"].isin((0, 1)),
        "invalid_flag_label": ~frame["isFlaggedFraud"].isin((0, 1)),
        "invalid_origin_id": ~frame["nameOrig"].astype("string").str.match(r"^C\d+$", na=False),
        "invalid_destination_id": ~frame["nameDest"]
        .astype("string")
        .str.match(r"^[CM]\d+$", na=False),
        "duplicate_source_row": frame[list(SOURCE_COLUMNS)].duplicated(keep="first"),
    }

    for reason, failed in checks.items():
        reasons = reasons.mask(
            failed & reasons.eq(""),
            reason,
        ).mask(
            failed & reasons.ne("") & ~reasons.str.contains(reason, regex=False),
            reasons + "|" + reason,
        )
    return reasons


def validate_paysim_frame(
    frame: pd.DataFrame,
    *,
    source_row_offset: int = 0,
) -> ValidationResult:
    """Validate a source frame without silently repairing invalid values.

    Coercing a malformed value to zero would make ingestion convenient but
    destroy evidence. Invalid rows are preserved in ``rejected`` with their
    original values and a reason; only accepted rows are converted to the
    canonical snake-case schema.
    """
    assert_source_columns(frame)
    working = frame.copy()
    working.insert(
        0,
        "source_row_number",
        np.arange(source_row_offset + 2, source_row_offset + len(frame) + 2),
    )
    reasons = _reason_series(working)

    rejected = working.loc[reasons.ne("")].copy()
    rejected.insert(1, "rejection_reason", reasons.loc[reasons.ne("")])

    accepted = working.loc[reasons.eq("")].rename(columns=COLUMN_RENAMES).copy()
    accepted["step"] = accepted["step"].astype("int32")
    accepted["is_fraud"] = accepted["is_fraud"].astype("int8")
    accepted["is_flagged_fraud"] = accepted["is_flagged_fraud"].astype("int8")
    for column in (
        "amount",
        "old_balance_orig",
        "new_balance_orig",
        "old_balance_dest",
        "new_balance_dest",
    ):
        accepted[column] = accepted[column].astype("float64")

    summary = {
        "source_rows": int(len(frame)),
        "accepted_rows": int(len(accepted)),
        "rejected_rows": int(len(rejected)),
        "fraud_rows": int(accepted["is_fraud"].sum()),
        "flagged_rows": int(accepted["is_flagged_fraud"].sum()),
    }
    return ValidationResult(accepted=accepted, rejected=rejected, summary=summary)
