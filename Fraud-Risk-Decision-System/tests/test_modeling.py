from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_system.features import MODEL_FEATURES
from fraud_system.modeling import (
    ModelBundle,
    choose_champion,
    fit_candidate_models,
    load_model_bundle,
    save_model_bundle,
)


def model_frame(size: int, seed: int) -> tuple[pd.DataFrame, pd.Series]:
    generator = np.random.default_rng(seed)
    amount = generator.uniform(1, 10_000, size)
    target = pd.Series((amount > 8_000).astype("int8"))
    frame = pd.DataFrame(
        {
            "type": np.where(target.eq(1), "TRANSFER", "PAYMENT"),
            "step": np.arange(size),
            "hour_of_day": np.arange(size) % 24,
            "day_index": np.arange(size) // 24,
            "amount": amount,
            "log_amount": np.log1p(amount),
            "old_balance_orig": generator.uniform(0, 20_000, size),
            "old_balance_dest": generator.uniform(0, 20_000, size),
            "amount_to_orig_balance": generator.uniform(0, 2, size),
            "amount_to_dest_balance": generator.uniform(0, 2, size),
            "origin_balance_is_zero": np.zeros(size),
            "destination_balance_is_zero": np.zeros(size),
            "origin_has_insufficient_balance": target,
            "destination_is_merchant": np.zeros(size),
        }
    )
    return frame.loc[:, MODEL_FEATURES], target


def test_candidate_training_and_bundle_round_trip(tmp_path) -> None:
    fit_x, fit_y = model_frame(120, 1)
    calibration_x, calibration_y = model_frame(80, 2)
    validation_x, validation_y = model_frame(80, 3)

    candidates = fit_candidate_models(
        fit_x,
        fit_y,
        calibration_x,
        calibration_y,
        validation_x,
        validation_y,
        lightgbm_candidates=[
            {
                "learning_rate": 0.1,
                "num_leaves": 7,
                "n_estimators": 10,
                "min_child_samples": 5,
            }
        ],
    )
    champion = choose_champion(candidates)
    bundle = ModelBundle(
        model=champion.model,
        model_name=champion.name,
        feature_names=MODEL_FEATURES,
        probability_threshold=0.5,
        review_capacity_per_day=10,
        cost_assumptions={"review_cost": 4},
        train_end_step=10,
        validation_end_step=20,
    )
    path = tmp_path / "model.joblib"

    save_model_bundle(bundle, str(path))
    loaded = load_model_bundle(str(path))

    assert loaded.model_name == champion.name
    assert loaded.predict_proba(validation_x).shape == (80,)
