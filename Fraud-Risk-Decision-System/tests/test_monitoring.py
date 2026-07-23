from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_system.decision_policy import CostAssumptions
from fraud_system.monitoring import daily_monitoring_table, population_stability_index


def test_population_stability_is_zero_for_identical_distribution() -> None:
    values = np.linspace(0, 1, 100)

    assert population_stability_index(values, values) == 0


def test_population_stability_detects_shift() -> None:
    reference = np.linspace(0, 0.2, 100)
    shifted = np.linspace(0.8, 1, 100)

    assert population_stability_index(reference, shifted) > 0.25


def test_daily_monitoring_aggregates_policy_outcomes() -> None:
    table = daily_monitoring_table(
        probabilities=np.array([0.9, 0.2, 0.8]),
        target=np.array([1, 0, 1]),
        context=pd.DataFrame(
            {
                "step": [1, 2, 25],
                "amount": [100.0, 50.0, 200.0],
                "type": ["TRANSFER", "PAYMENT", "CASH_OUT"],
            }
        ),
        review=np.array([True, False, False]),
        reference_probabilities=np.linspace(0, 1, 50),
        costs=CostAssumptions(),
    )

    first_day = table.set_index("day_index").loc[0]
    assert first_day["transaction_count"] == 2
    assert first_day["true_positive_count"] == 1
    assert first_day["loss_avoided"] == 85
