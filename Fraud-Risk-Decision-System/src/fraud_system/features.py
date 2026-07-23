"""Decision-time feature construction.

The intended decision point is *before settlement*. Therefore post-transaction
balances, the simulator's existing fraud flag, customer identifiers, and the
fraud label are deliberately excluded from the model matrix.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

CATEGORICAL_FEATURES = ("type",)
NUMERIC_FEATURES = (
    "step",
    "hour_of_day",
    "day_index",
    "amount",
    "log_amount",
    "old_balance_orig",
    "old_balance_dest",
    "amount_to_orig_balance",
    "amount_to_dest_balance",
    "origin_balance_is_zero",
    "destination_balance_is_zero",
    "origin_has_insufficient_balance",
    "destination_is_merchant",
)
MODEL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


@dataclass(frozen=True)
class FeatureSet:
    """Model inputs, target, and fields needed for policy evaluation."""

    features: pd.DataFrame
    target: pd.Series
    policy_context: pd.DataFrame


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide while avoiding infinite values for zero-balance accounts."""
    return numerator / denominator.clip(lower=1.0)


def build_decision_time_features(frame: pd.DataFrame) -> FeatureSet:
    """Create deterministic features available at the stated decision point."""
    required = {
        "step",
        "type",
        "amount",
        "name_dest",
        "old_balance_orig",
        "old_balance_dest",
        "is_fraud",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Cannot build features; missing columns: {missing}")

    features = pd.DataFrame(index=frame.index)
    features["type"] = frame["type"].astype("string")
    features["step"] = frame["step"].astype("int32")
    features["hour_of_day"] = ((frame["step"] - 1) % 24).astype("int8")
    features["day_index"] = ((frame["step"] - 1) // 24).astype("int16")
    features["amount"] = frame["amount"].astype("float64")
    features["log_amount"] = np.log1p(features["amount"])
    features["old_balance_orig"] = frame["old_balance_orig"].astype("float64")
    features["old_balance_dest"] = frame["old_balance_dest"].astype("float64")
    features["amount_to_orig_balance"] = _safe_ratio(
        features["amount"], features["old_balance_orig"]
    )
    features["amount_to_dest_balance"] = _safe_ratio(
        features["amount"], features["old_balance_dest"]
    )
    features["origin_balance_is_zero"] = features["old_balance_orig"].eq(0).astype("int8")
    features["destination_balance_is_zero"] = features["old_balance_dest"].eq(0).astype("int8")
    features["origin_has_insufficient_balance"] = (
        features["amount"].gt(features["old_balance_orig"]).astype("int8")
    )
    features["destination_is_merchant"] = (
        frame["name_dest"].astype("string").str.startswith("M").astype("int8")
    )

    policy_context = frame[["step", "amount", "type"]].copy()
    if "source_row_number" in frame:
        policy_context["source_row_number"] = frame["source_row_number"]

    return FeatureSet(
        features=features.loc[:, MODEL_FEATURES],
        target=frame["is_fraud"].astype("int8"),
        policy_context=policy_context,
    )
