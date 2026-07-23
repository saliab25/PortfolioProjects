"""Cost- and capacity-aware conversion of probabilities into review decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CostAssumptions:
    """Operational assumptions stated in currency units per transaction."""

    review_capacity_per_day: int = 300
    review_cost: float = 4.0
    false_positive_friction_cost: float = 12.0
    fraud_loss_rate: float = 1.0
    fraud_recovery_rate_when_reviewed: float = 0.85

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class PolicyResult:
    threshold: float
    total_cost: float
    loss_avoided: float
    net_benefit_vs_no_review: float
    reviewed: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    capacity_binding_days: int

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def apply_review_policy(
    probabilities: np.ndarray,
    context: pd.DataFrame,
    *,
    threshold: float,
    costs: CostAssumptions,
) -> pd.Series:
    """Apply the threshold, positive-value rule, and per-day capacity cap.

    Probability alone ranks likelihood. Expected preventable loss also reflects
    transaction amount, which is operationally preferable when two cases have
    similar fraud risk but very different financial exposure.
    """
    if len(probabilities) != len(context):
        raise ValueError("probabilities and context must have equal length.")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1.")

    working = context.reset_index(drop=True).copy()
    working["probability"] = np.asarray(probabilities, dtype=float)
    working["day_index"] = ((working["step"] - 1) // 24).astype("int32")
    working["expected_net_value"] = (
        working["probability"]
        * working["amount"]
        * costs.fraud_loss_rate
        * costs.fraud_recovery_rate_when_reviewed
        - costs.review_cost
        - (1 - working["probability"]) * costs.false_positive_friction_cost
    )
    working["eligible"] = working["probability"].ge(threshold) & working["expected_net_value"].gt(0)
    working["review"] = False

    eligible = working.loc[working["eligible"]].sort_values(
        ["day_index", "expected_net_value", "probability"],
        ascending=[True, False, False],
        kind="mergesort",
    )
    selected = eligible.groupby("day_index", sort=False).head(costs.review_capacity_per_day)
    working.loc[selected.index, "review"] = True
    return working["review"]


def evaluate_review_policy(
    probabilities: np.ndarray,
    target: pd.Series | np.ndarray,
    context: pd.DataFrame,
    *,
    threshold: float,
    costs: CostAssumptions,
) -> PolicyResult:
    """Evaluate both classification behavior and financial consequences."""
    actual = np.asarray(target, dtype=np.int8)
    review = apply_review_policy(
        probabilities,
        context,
        threshold=threshold,
        costs=costs,
    ).to_numpy()
    amounts = context["amount"].to_numpy(dtype=float)

    tp_mask = review & (actual == 1)
    fp_mask = review & (actual == 0)
    fn_mask = ~review & (actual == 1)
    tn_mask = ~review & (actual == 0)
    tp = int(tp_mask.sum())
    fp = int(fp_mask.sum())
    fn = int(fn_mask.sum())
    tn = int(tn_mask.sum())
    reviewed = int(review.sum())

    no_review_loss = float((amounts[actual == 1] * costs.fraud_loss_rate).sum())
    avoided_loss = float(
        (amounts[tp_mask] * costs.fraud_loss_rate * costs.fraud_recovery_rate_when_reviewed).sum()
    )
    total_cost = (
        no_review_loss
        - avoided_loss
        + reviewed * costs.review_cost
        + fp * costs.false_positive_friction_cost
    )
    reviewed_by_day = (
        pd.DataFrame(
            {
                "day_index": ((context["step"].to_numpy() - 1) // 24),
                "review": review,
            }
        )
        .groupby("day_index")["review"]
        .sum()
    )
    binding_days = int(reviewed_by_day.ge(costs.review_capacity_per_day).sum())
    return PolicyResult(
        threshold=float(threshold),
        total_cost=float(total_cost),
        loss_avoided=avoided_loss,
        net_benefit_vs_no_review=float(no_review_loss - total_cost),
        reviewed=reviewed,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        precision=tp / (tp + fp) if tp + fp else 0.0,
        recall=tp / (tp + fn) if tp + fn else 0.0,
        capacity_binding_days=binding_days,
    )


def select_policy_threshold(
    probabilities: np.ndarray,
    target: pd.Series | np.ndarray,
    context: pd.DataFrame,
    *,
    costs: CostAssumptions,
    grid_size: int = 201,
) -> tuple[PolicyResult, pd.DataFrame]:
    """Choose the lowest-cost threshold using validation data only."""
    if grid_size < 3:
        raise ValueError("grid_size must be at least 3.")
    candidates = np.unique(
        np.concatenate(
            (
                np.linspace(0, 1, grid_size),
                np.quantile(probabilities, np.linspace(0, 1, grid_size)),
            )
        )
    )
    results = [
        evaluate_review_policy(
            probabilities,
            target,
            context,
            threshold=float(threshold),
            costs=costs,
        )
        for threshold in candidates
    ]
    table = pd.DataFrame(result.as_dict() for result in results).sort_values(
        ["total_cost", "threshold"],
        ascending=[True, False],
    )
    best = min(results, key=lambda result: (result.total_cost, -result.threshold))
    return best, table.reset_index(drop=True)
