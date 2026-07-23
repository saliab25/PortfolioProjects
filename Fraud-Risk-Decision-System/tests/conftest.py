from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def paysim_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "step": [1, 2, 25, 26],
            "type": ["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT"],
            "amount": [10.0, 500.0, 400.0, 20.0],
            "nameOrig": ["C1", "C2", "C3", "C4"],
            "oldbalanceOrg": [100.0, 300.0, 0.0, 50.0],
            "newbalanceOrig": [90.0, 0.0, 0.0, 30.0],
            "nameDest": ["M1", "C10", "C11", "C12"],
            "oldbalanceDest": [0.0, 100.0, 200.0, 30.0],
            "newbalanceDest": [0.0, 600.0, 600.0, 50.0],
            "isFraud": [0, 1, 1, 0],
            "isFlaggedFraud": [0, 0, 0, 0],
        }
    )
