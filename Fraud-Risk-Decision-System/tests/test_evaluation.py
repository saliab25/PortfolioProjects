from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_system.evaluation import (
    calibration_table,
    confusion_by_segment,
    probability_metrics,
    recall_at_fixed_precision,
)


def test_perfect_ranking_has_perfect_average_precision() -> None:
    target = np.array([0, 0, 1, 1])
    probabilities = np.array([0.01, 0.1, 0.9, 0.99])

    metrics = probability_metrics(target, probabilities, minimum_precision=1.0)

    assert metrics["pr_auc"] == 1
    assert metrics["roc_auc"] == 1
    recall, threshold = recall_at_fixed_precision(
        target,
        probabilities,
        minimum_precision=1.0,
    )
    assert recall == 1
    assert threshold == 0.9


def test_confusion_counts_are_segmented() -> None:
    target = np.array([1, 0, 1, 0])
    review = np.array([1, 1, 0, 0])
    segment = pd.Series(["TRANSFER", "TRANSFER", "PAYMENT", "PAYMENT"])

    table = confusion_by_segment(target, review, segment).set_index("segment")

    assert table.loc["TRANSFER", "true_positives"] == 1
    assert table.loc["TRANSFER", "false_positives"] == 1
    assert table.loc["PAYMENT", "false_negatives"] == 1
    assert len(calibration_table(target, np.array([0.8, 0.7, 0.4, 0.1]))) > 0
