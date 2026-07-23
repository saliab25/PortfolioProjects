"""Interactive explanation of the fitted transaction decision policy."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from fraud_system.features import build_decision_time_features
from fraud_system.modeling import load_model_bundle

MODEL_PATH = Path("artifacts/champion_model.joblib")


@st.cache_resource
def load_model():
    return load_model_bundle(str(MODEL_PATH))


st.set_page_config(page_title="Fraud review decision system", layout="wide")
st.title("Fraud review decision system")
st.warning(
    "Portfolio demonstration using synthetic PaySim data. "
    "This model is not validated for real financial decisions."
)

if not MODEL_PATH.exists():
    st.error("Model artifact not found. Run scripts/train_and_evaluate.py first.")
    st.stop()

bundle = load_model()
with st.sidebar:
    st.header("Pre-settlement transaction")
    step = st.number_input("Simulation hour (`step`)", min_value=1, value=500)
    transaction_type = st.selectbox(
        "Transaction type",
        ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"],
    )
    amount = st.number_input("Amount", min_value=0.0, value=1_000.0)
    old_balance_orig = st.number_input(
        "Origin balance before transaction",
        min_value=0.0,
        value=2_000.0,
    )
    old_balance_dest = st.number_input(
        "Destination balance before transaction",
        min_value=0.0,
        value=5_000.0,
    )
    destination_is_merchant = st.checkbox("Destination is a merchant")

transaction = pd.DataFrame(
    {
        "step": [int(step)],
        "type": [transaction_type],
        "amount": [amount],
        "name_dest": ["M1" if destination_is_merchant else "C1"],
        "old_balance_orig": [old_balance_orig],
        "old_balance_dest": [old_balance_dest],
        "is_fraud": [0],
    }
)
feature_set = build_decision_time_features(transaction)
probability = float(bundle.predict_proba(feature_set.features)[0])
costs = bundle.cost_assumptions
expected_net_value = (
    probability * amount * costs["fraud_loss_rate"] * costs["fraud_recovery_rate_when_reviewed"]
    - costs["review_cost"]
    - (1 - probability) * costs["false_positive_friction_cost"]
)
threshold_eligible = probability >= bundle.probability_threshold and expected_net_value > 0

left, middle, right = st.columns(3)
left.metric("Calibrated fraud probability", f"{probability:.2%}")
middle.metric("Policy threshold", f"{bundle.probability_threshold:.2%}")
right.metric("Expected net review value", f"${expected_net_value:,.2f}")

if threshold_eligible:
    st.error("Eligible for the manual-review queue")
else:
    st.success("Not eligible for manual review under the selected threshold")

st.caption(
    "Eligibility is not a guarantee of review. If more than "
    f"{bundle.review_capacity_per_day:,} eligible transactions arrive in a day, "
    "the batch policy prioritizes the highest expected preventable loss."
)
with st.expander("Why these inputs?"):
    st.write(
        "Only fields assumed available before settlement are accepted. "
        "Post-transaction balances, the simulator's fraud flag, customer IDs, "
        "and the true fraud label are deliberately unavailable to this interface."
    )
    feature_display = feature_set.features.T.reset_index()
    feature_display.columns = ["feature", "value"]
    feature_display["value"] = feature_display["value"].astype("string")
    st.dataframe(feature_display, hide_index=True)

st.divider()
st.header("Held-out operating dashboard")
metrics_path = Path("reports/metrics/final_metrics.json")
daily_path = Path("reports/metrics/daily_monitoring.csv")
if metrics_path.exists() and daily_path.exists():
    import json

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    daily = pd.read_csv(daily_path)
    test_policy = metrics["test_policy"]
    first, second, third, fourth = st.columns(4)
    first.metric("Test transactions", f"{metrics['split']['test_rows']:,}")
    second.metric("Transactions reviewed", f"{test_policy['reviewed']:,}")
    third.metric("Fraud recall", f"{test_policy['recall']:.2%}")
    fourth.metric("Loss avoided", f"${test_policy['loss_avoided']:,.0f}")

    st.subheader("Daily volume and review use")
    st.line_chart(daily.set_index("day_index")[["transaction_count", "review_count"]])
    st.subheader("Daily errors and drift")
    left_chart, right_chart = st.columns(2)
    left_chart.line_chart(
        daily.set_index("day_index")[["false_positive_count", "false_negative_count"]]
    )
    right_chart.line_chart(daily.set_index("day_index")[["score_psi_vs_validation"]])
    st.caption(
        "Population Stability Index (PSI) compares each test day's score "
        "distribution with validation. PSI is a screening indicator, not proof "
        "that model performance changed."
    )
else:
    st.info("Run the training pipeline to populate held-out monitoring results.")
