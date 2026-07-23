from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_system.decision_policy import (
    CostAssumptions,
    apply_review_policy,
    evaluate_review_policy,
)


def test_capacity_prioritizes_expected_preventable_loss() -> None:
    probabilities = np.array([0.9, 0.8, 0.7])
    context = pd.DataFrame(
        {
            "step": [1, 1, 1],
            "amount": [100.0, 1_000.0, 10_000.0],
            "type": ["TRANSFER"] * 3,
        }
    )
    costs = CostAssumptions(
        review_capacity_per_day=1,
        review_cost=1,
        false_positive_friction_cost=1,
    )

    review = apply_review_policy(
        probabilities,
        context,
        threshold=0.5,
        costs=costs,
    )

    assert review.tolist() == [False, False, True]


def test_policy_cost_matches_stated_components() -> None:
    probabilities = np.array([0.9, 0.1])
    target = np.array([1, 0])
    context = pd.DataFrame(
        {
            "step": [1, 1],
            "amount": [100.0, 50.0],
            "type": ["TRANSFER", "PAYMENT"],
        }
    )
    costs = CostAssumptions(
        review_capacity_per_day=1,
        review_cost=4,
        false_positive_friction_cost=12,
        fraud_loss_rate=1,
        fraud_recovery_rate_when_reviewed=0.85,
    )

    result = evaluate_review_policy(
        probabilities,
        target,
        context,
        threshold=0.5,
        costs=costs,
    )

    assert result.reviewed == 1
    assert result.loss_avoided == 85
    assert result.total_cost == 19
    assert result.net_benefit_vs_no_review == 81
