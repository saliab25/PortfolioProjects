from __future__ import annotations

import pandas as pd

from fraud_system.data_contract import validate_paysim_frame
from fraud_system.features import MODEL_FEATURES, build_decision_time_features


def test_features_respect_pre_settlement_boundary(paysim_frame: pd.DataFrame) -> None:
    accepted = validate_paysim_frame(paysim_frame).accepted

    feature_set = build_decision_time_features(accepted)

    assert tuple(feature_set.features.columns) == MODEL_FEATURES
    forbidden = {
        "new_balance_orig",
        "new_balance_dest",
        "is_flagged_fraud",
        "is_fraud",
        "name_orig",
        "name_dest",
    }
    assert forbidden.isdisjoint(feature_set.features.columns)
    assert feature_set.features.loc[0, "destination_is_merchant"] == 1
    assert feature_set.features.loc[2, "origin_has_insufficient_balance"] == 1
