"""Chronological split utilities for simulated transaction steps."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TimeSplit:
    """Boolean masks and the step boundaries that produced them."""

    train: pd.Series
    validation: pd.Series
    test: pd.Series
    train_end_step: int
    validation_end_step: int


def chronological_split(
    steps: pd.Series,
    *,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> TimeSplit:
    """Split on whole time steps so an hour never appears in two datasets."""
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1.")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1.")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("The train and validation fractions must sum to less than 1.")

    unique_steps = np.sort(steps.dropna().unique())
    if len(unique_steps) < 3:
        raise ValueError("At least three distinct time steps are required.")

    train_position = max(0, int(len(unique_steps) * train_fraction) - 1)
    validation_position = max(
        train_position + 1,
        int(len(unique_steps) * (train_fraction + validation_fraction)) - 1,
    )
    validation_position = min(validation_position, len(unique_steps) - 2)

    train_end = int(unique_steps[train_position])
    validation_end = int(unique_steps[validation_position])
    train = steps.le(train_end)
    validation = steps.gt(train_end) & steps.le(validation_end)
    test = steps.gt(validation_end)

    if not (train.any() and validation.any() and test.any()):
        raise ValueError("The requested fractions produced an empty split.")
    return TimeSplit(
        train=train,
        validation=validation,
        test=test,
        train_end_step=train_end,
        validation_end_step=validation_end,
    )


def split_fit_and_calibration(
    steps: pd.Series,
    *,
    calibration_fraction: float = 0.20,
) -> tuple[pd.Series, pd.Series]:
    """Reserve the latest part of training for probability calibration."""
    if not 0 < calibration_fraction < 1:
        raise ValueError("calibration_fraction must be between 0 and 1.")
    unique_steps = np.sort(steps.dropna().unique())
    boundary_position = max(0, int(len(unique_steps) * (1 - calibration_fraction)) - 1)
    boundary = unique_steps[boundary_position]
    fit = steps.le(boundary)
    calibration = steps.gt(boundary)
    if not (fit.any() and calibration.any()):
        raise ValueError("The calibration fraction produced an empty partition.")
    return fit, calibration
