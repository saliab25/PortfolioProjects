"""Operational aggregates and simple population-drift indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_system.decision_policy import CostAssumptions


def population_stability_index(
    reference: np.ndarray,
    current: np.ndarray,
    *,
    bins: int = 10,
    epsilon: float = 1e-6,
) -> float:
    """Compare two distributions using reference quantile bins.

    PSI is retained because it is common and interpretable in financial-risk
    monitoring. It is not a statistical test and its conventional warning
    levels are heuristics, so it should be paired with sample sizes and plots.
    """
    reference_values = np.asarray(reference, dtype=float)
    current_values = np.asarray(current, dtype=float)
    if len(reference_values) == 0 or len(current_values) == 0:
        raise ValueError("Both reference and current arrays must be non-empty.")
    edges = np.unique(np.quantile(reference_values, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    reference_counts, _ = np.histogram(reference_values, bins=edges)
    current_counts, _ = np.histogram(current_values, bins=edges)
    reference_share = np.clip(reference_counts / reference_counts.sum(), epsilon, None)
    current_share = np.clip(current_counts / current_counts.sum(), epsilon, None)
    return float(
        ((current_share - reference_share) * np.log(current_share / reference_share)).sum()
    )


def daily_monitoring_table(
    probabilities: np.ndarray,
    target: pd.Series | np.ndarray,
    context: pd.DataFrame,
    review: pd.Series | np.ndarray,
    *,
    reference_probabilities: np.ndarray,
    costs: CostAssumptions,
) -> pd.DataFrame:
    """Aggregate volume, decisions, outcomes, avoided loss, and score drift."""
    frame = context.reset_index(drop=True).copy()
    frame["probability"] = np.asarray(probabilities)
    frame["actual"] = np.asarray(target, dtype=np.int8)
    frame["review"] = np.asarray(review, dtype=bool)
    frame["day_index"] = ((frame["step"] - 1) // 24).astype("int32")
    frame["true_positive"] = frame["review"] & frame["actual"].eq(1)
    frame["false_positive"] = frame["review"] & frame["actual"].eq(0)
    frame["false_negative"] = ~frame["review"] & frame["actual"].eq(1)
    frame["loss_avoided"] = (
        frame["true_positive"]
        * frame["amount"]
        * costs.fraud_loss_rate
        * costs.fraud_recovery_rate_when_reviewed
    )

    rows = []
    for day_index, group in frame.groupby("day_index", sort=True):
        rows.append(
            {
                "day_index": int(day_index),
                "transaction_count": int(len(group)),
                "review_count": int(group["review"].sum()),
                "observed_fraud_count": int(group["actual"].sum()),
                "true_positive_count": int(group["true_positive"].sum()),
                "false_positive_count": int(group["false_positive"].sum()),
                "false_negative_count": int(group["false_negative"].sum()),
                "mean_probability": float(group["probability"].mean()),
                "loss_avoided": float(group["loss_avoided"].sum()),
                "score_psi_vs_validation": population_stability_index(
                    reference_probabilities,
                    group["probability"].to_numpy(),
                ),
            }
        )
    return pd.DataFrame(rows)
