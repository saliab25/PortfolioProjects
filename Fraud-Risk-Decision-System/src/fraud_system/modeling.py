"""Model fitting, calibration, comparison, and serialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from fraud_system.features import CATEGORICAL_FEATURES, MODEL_FEATURES, NUMERIC_FEATURES


@dataclass(frozen=True)
class CandidateResult:
    """A fitted candidate and its validation ranking score."""

    name: str
    model: CalibratedClassifierCV
    validation_probabilities: np.ndarray
    validation_pr_auc: float
    parameters: dict[str, Any]


@dataclass
class ModelBundle:
    """Everything required to reproduce a single-transaction score."""

    model: CalibratedClassifierCV
    model_name: str
    feature_names: tuple[str, ...]
    probability_threshold: float
    review_capacity_per_day: int
    cost_assumptions: dict[str, float | int]
    train_end_step: int
    validation_end_step: int
    version: str = "1.0.0"

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        """Return the calibrated positive-class probability."""
        return self.model.predict_proba(features.loc[:, self.feature_names])[:, 1]


def _preprocessor() -> ColumnTransformer:
    """Use one-hot encoding for type and scaling for numeric logistic inputs."""
    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=True),
                list(CATEGORICAL_FEATURES),
            ),
            ("numeric", StandardScaler(), list(NUMERIC_FEATURES)),
        ],
        remainder="drop",
        sparse_threshold=0.3,
    )


def _logistic_pipeline(random_seed: int) -> Pipeline:
    return Pipeline(
        [
            ("preprocess", _preprocessor()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1_000,
                    random_state=random_seed,
                    solver="liblinear",
                ),
            ),
        ]
    )


def _lightgbm_pipeline(parameters: dict[str, Any], random_seed: int) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=True),
                list(CATEGORICAL_FEATURES),
            ),
            ("numeric", "passthrough", list(NUMERIC_FEATURES)),
        ],
        remainder="drop",
        sparse_threshold=0.3,
    )
    model = LGBMClassifier(
        objective="binary",
        class_weight="balanced",
        random_state=random_seed,
        n_jobs=-1,
        verbosity=-1,
        deterministic=True,
        force_col_wise=True,
        **parameters,
    )
    return Pipeline([("preprocess", preprocessor), ("model", model)])


def fit_and_calibrate(
    estimator: Pipeline,
    fit_features: pd.DataFrame,
    fit_target: pd.Series,
    calibration_features: pd.DataFrame,
    calibration_target: pd.Series,
) -> CalibratedClassifierCV:
    """Fit ranking on earlier data and sigmoid calibration on later data.

    ``cv='prefit'`` is intentional with scikit-learn 1.5.2. It prevents the
    calibrator from refitting the base estimator and keeps the two chronological
    periods separate.
    """
    estimator.fit(fit_features.loc[:, MODEL_FEATURES], fit_target)
    calibrated = CalibratedClassifierCV(estimator, method="sigmoid", cv="prefit")
    calibrated.fit(calibration_features.loc[:, MODEL_FEATURES], calibration_target)
    return calibrated


def fit_candidate_models(
    fit_features: pd.DataFrame,
    fit_target: pd.Series,
    calibration_features: pd.DataFrame,
    calibration_target: pd.Series,
    validation_features: pd.DataFrame,
    validation_target: pd.Series,
    *,
    lightgbm_candidates: list[dict[str, Any]],
    random_seed: int = 42,
) -> list[CandidateResult]:
    """Fit the required baseline and each pre-declared boosted-tree candidate."""
    specifications: list[tuple[str, Pipeline, dict[str, Any]]] = [
        (
            "logistic_regression",
            _logistic_pipeline(random_seed),
            {"class_weight": "balanced"},
        )
    ]
    specifications.extend(
        (
            f"lightgbm_{position}",
            _lightgbm_pipeline(parameters, random_seed),
            parameters,
        )
        for position, parameters in enumerate(lightgbm_candidates, start=1)
    )

    results: list[CandidateResult] = []
    for name, estimator, parameters in specifications:
        model = fit_and_calibrate(
            estimator,
            fit_features,
            fit_target,
            calibration_features,
            calibration_target,
        )
        probabilities = model.predict_proba(validation_features.loc[:, MODEL_FEATURES])[:, 1]
        results.append(
            CandidateResult(
                name=name,
                model=model,
                validation_probabilities=probabilities,
                validation_pr_auc=float(average_precision_score(validation_target, probabilities)),
                parameters=parameters,
            )
        )
    return results


def choose_champion(candidates: list[CandidateResult]) -> CandidateResult:
    """Select by validation PR-AUC; never inspect test metrics here."""
    if not candidates:
        raise ValueError("At least one candidate is required.")
    return max(candidates, key=lambda candidate: candidate.validation_pr_auc)


def save_model_bundle(bundle: ModelBundle, path: str) -> None:
    """Persist the fitted pipeline and policy metadata together."""
    joblib.dump(bundle, path)


def load_model_bundle(path: str) -> ModelBundle:
    """Load a bundle produced by :func:`save_model_bundle`."""
    loaded = joblib.load(path)
    if not isinstance(loaded, ModelBundle):
        raise TypeError(f"Expected ModelBundle, received {type(loaded).__name__}.")
    return loaded
