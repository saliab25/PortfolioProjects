"""Imbalance-aware probability and classification metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)


def recall_at_fixed_precision(
    target: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    *,
    minimum_precision: float,
) -> tuple[float, float]:
    """Return the best recall and its threshold at the precision constraint."""
    precision, recall, thresholds = precision_recall_curve(target, probabilities)
    candidate_mask = precision[:-1] >= minimum_precision
    if not candidate_mask.any():
        return 0.0, 1.0
    candidate_positions = np.flatnonzero(candidate_mask)
    best_position = candidate_positions[np.argmax(recall[:-1][candidate_mask])]
    return float(recall[best_position]), float(thresholds[best_position])


def expected_calibration_error(
    target: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    *,
    bins: int = 10,
) -> float:
    """Compute equal-width expected calibration error."""
    actual = np.asarray(target)
    probability = np.asarray(probabilities)
    edges = np.linspace(0, 1, bins + 1)
    assignments = np.minimum(np.digitize(probability, edges[1:-1]), bins - 1)
    error = 0.0
    for bin_index in range(bins):
        mask = assignments == bin_index
        if mask.any():
            error += mask.mean() * abs(actual[mask].mean() - probability[mask].mean())
    return float(error)


def probability_metrics(
    target: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    *,
    minimum_precision: float = 0.80,
) -> dict[str, float]:
    """Summarize ranking quality and probability reliability."""
    recall, threshold = recall_at_fixed_precision(
        target,
        probabilities,
        minimum_precision=minimum_precision,
    )
    return {
        "pr_auc": float(average_precision_score(target, probabilities)),
        "roc_auc": float(roc_auc_score(target, probabilities)),
        "brier_score": float(brier_score_loss(target, probabilities)),
        "expected_calibration_error": expected_calibration_error(target, probabilities),
        f"recall_at_precision_{minimum_precision:.2f}": recall,
        f"threshold_at_precision_{minimum_precision:.2f}": threshold,
    }


def confusion_by_segment(
    target: pd.Series | np.ndarray,
    review: pd.Series | np.ndarray,
    segment: pd.Series,
) -> pd.DataFrame:
    """Produce auditable confusion counts for each business segment."""
    frame = pd.DataFrame(
        {
            "actual": np.asarray(target, dtype=np.int8),
            "review": np.asarray(review, dtype=np.int8),
            "segment": segment.reset_index(drop=True).astype("string"),
        }
    )
    rows: list[dict[str, float | int | str]] = []
    for value, group in frame.groupby("segment", dropna=False):
        tn, fp, fn, tp = confusion_matrix(
            group["actual"],
            group["review"],
            labels=[0, 1],
        ).ravel()
        rows.append(
            {
                "segment": str(value),
                "transactions": int(len(group)),
                "fraud": int(group["actual"].sum()),
                "true_positives": int(tp),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_negatives": int(tn),
                "precision": float(tp / (tp + fp)) if tp + fp else 0.0,
                "recall": float(tp / (tp + fn)) if tp + fn else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("transactions", ascending=False)


def calibration_table(
    target: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    *,
    bins: int = 10,
) -> pd.DataFrame:
    """Return observed and predicted rates for calibration plotting."""
    observed, predicted = calibration_curve(
        target,
        probabilities,
        n_bins=bins,
        strategy="quantile",
    )
    return pd.DataFrame(
        {
            "mean_predicted_probability": predicted,
            "observed_fraud_rate": observed,
        }
    )
