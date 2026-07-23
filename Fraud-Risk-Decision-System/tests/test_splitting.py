from __future__ import annotations

import pandas as pd

from fraud_system.splitting import chronological_split, split_fit_and_calibration


def test_chronological_split_keeps_steps_whole() -> None:
    steps = pd.Series([1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6])

    split = chronological_split(steps, train_fraction=0.5, validation_fraction=0.25)

    assert steps[split.train].max() < steps[split.validation].min()
    assert steps[split.validation].max() < steps[split.test].min()
    assert not (split.train & split.validation).any()
    assert not (split.validation & split.test).any()


def test_calibration_is_later_than_estimator_fit() -> None:
    steps = pd.Series(range(1, 11))

    fit, calibration = split_fit_and_calibration(steps, calibration_fraction=0.2)

    assert steps[fit].max() < steps[calibration].min()
