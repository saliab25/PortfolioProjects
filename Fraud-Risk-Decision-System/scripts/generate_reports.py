"""Generate the model card and risk memo from frozen held-out metrics."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

METRICS_DIR = Path("reports/metrics")


def money(value: float) -> str:
    return f"${value:,.0f}"


def percent(value: float) -> str:
    return f"{value:.2%}"


def main() -> None:
    metrics = json.loads((METRICS_DIR / "final_metrics.json").read_text(encoding="utf-8"))
    candidates = pd.read_csv(METRICS_DIR / "candidate_comparison.csv")
    transaction_segments = pd.read_csv(METRICS_DIR / "confusion_by_transaction_type.csv")
    importance = pd.read_csv(METRICS_DIR / "global_feature_importance.csv").head(10)

    split = metrics["split"]
    costs = metrics["cost_assumptions"]
    validation = metrics["validation_policy"]
    test = metrics["test_policy"]
    probability = metrics["test_probability_metrics"]
    no_review_cost = test["total_cost"] + test["net_benefit_vs_no_review"]
    legitimate_review_cost = money(
        costs["review_cost"] + costs["false_positive_friction_cost"]
    )

    memo = f"""# Fraud review policy: one-page risk memo

**Recommendation.** For this portfolio project, I recommend routing
transactions with calibrated fraud risk of at least
**{percent(validation["threshold"])}** and positive expected review value to a
queue capped at **{costs["review_capacity_per_day"]} reviews per day**. When the
cap is exceeded, prioritize expected preventable loss rather than probability
alone.

## Held-out operating result

| Measure | Result |
|---|---:|
| Test transactions | {split["test_rows"]:,} |
| Observed fraud | {test["true_positives"] + test["false_negatives"]:,} |
| Reviewed | {test["reviewed"]:,} |
| Fraud recall | {percent(test["recall"])} |
| Review precision | {percent(test["precision"])} |
| False positives | {test["false_positives"]:,} |
| Capacity-binding days | {test["capacity_binding_days"]} |
| Illustrative fraud loss avoided | {money(test["loss_avoided"])} |
| Policy cost | {money(test["total_cost"])} |
| No-review cost | {money(no_review_cost)} |

I selected the threshold only on validation data. I then froze the threshold
and capacity rule before evaluating them once on the final chronological test
period.

## Assumptions

- transaction amounts are treated as illustrative dollars;
- an unrecovered fraud loses {percent(costs["fraud_loss_rate"]) } of amount;
- review recovers {percent(costs["fraud_recovery_rate_when_reviewed"])} of a
  detected fraud;
- each review costs {money(costs["review_cost"])};
- each legitimate review adds {money(costs["false_positive_friction_cost"])}
  of customer-friction cost;
- capacity represents 25 investigators at eight cases per day.

## Risk judgment

I would **not** interpret the zero false positives or near-perfect PR-AUC as
credible production performance. PaySim is synthetic, the fraud rate rises
sharply in later simulation periods, and simulator rules make fraud unusually
separable. The result validates the mechanics of my cost- and capacity-aware
workflow, not a real fraud model.

Before any real use, I would replace the dataset, revalidate decision-time
availability, estimate costs with operations and finance, assess customer and
regional segments, model label delay, run a shadow deployment, and establish
independent model-risk review.
"""
    Path("reports/risk_memo.md").write_text(memo, encoding="utf-8")

    candidate_markdown = candidates.to_markdown(index=False)
    segment_markdown = transaction_segments.to_markdown(index=False)
    importance_markdown = importance.to_markdown(index=False)
    model_card = f"""# Model card: PaySim fraud review system

## Summary

- **Champion:** `{metrics["champion"]}`
- **Version:** `1.0.0`
- **Intended use:** I built this as a public portfolio demonstration of
  transaction-review prioritization.
- **Prohibited use:** real approval, decline, account restriction, law
  enforcement, customer treatment, or financial-loss forecasting.
- **Data:** PaySim synthetic mobile-money transactions.

## Data and split

The source contained {split["source_rows_loaded"]:,} accepted rows and an
overall fraud rate of {percent(split["overall_fraud_rate"])}. I split whole
simulated hours chronologically:

| Partition | Rows/rate |
|---|---:|
| Training | {split["train_rows"]:,} ({percent(split["train_fraud_rate"])}) |
| Estimator fit after negative sampling | {split["fit_rows_after_negative_sampling"]:,} |
| Calibration | {split["calibration_rows"]:,} |
| Validation | {split["validation_rows"]:,} ({percent(split["validation_fraud_rate"])}) |
| Test | {split["test_rows"]:,} ({percent(split["test_fraud_rate"])}) |

Training ends at step {split["train_end_step"]}; validation ends at step
{split["validation_end_step"]}. The rising fraud prevalence is evidence of
temporal distribution shift and a central limitation.

## Feature and leakage policy

I use only fields that I assume are available before settlement. I exclude the
fraud label, the existing simulated rule, post-transaction balances, and raw
account identifiers. See `docs/data_dictionary.md`.

## Model development

I use logistic regression as the interpretable baseline and two predeclared
LightGBM configurations as challengers. I train base estimators on the earliest
training period and use the later training period for sigmoid probability
calibration. I select the candidate with the lowest validation policy cost and
use validation PR-AUC as the tie-breaker.

{candidate_markdown}

## Frozen test performance

| Metric | Result |
|---|---:|
| PR-AUC / average precision | {probability["pr_auc"]:.6f} |
| ROC-AUC | {probability["roc_auc"]:.6f} |
| Brier score | {probability["brier_score"]:.8f} |
| Expected calibration error | {probability["expected_calibration_error"]:.8f} |
| Recall at >=80% precision | {percent(probability["recall_at_precision_0.80"])} |
| Policy precision | {percent(test["precision"])} |
| Policy recall | {percent(test["recall"])} |

I intentionally omit accuracy as a primary measure because the severe class
imbalance makes it misleading.

## Operating policy

I selected a {percent(validation["threshold"])} threshold on validation.
I cap eligible positive-value cases at {costs["review_capacity_per_day"]} per
day and rank them by expected preventable loss. The test period used the full
daily capacity on {test["capacity_binding_days"]} days.

The dollar results are scenario calculations, not observed economic outcomes.
They depend directly on the versioned assumptions in
`configs/decision_policy.json`.

### Dollar-cost matrix

| Observed outcome | Allow | Send to review |
|---|---:|---:|
| Legitimate | $0 | review cost + friction cost = {legitimate_review_cost} |
| Fraud | amount x loss rate | unrecovered amount + review cost |

For the configured {percent(costs["fraud_recovery_rate_when_reviewed"])}
recovery rate, the reviewed-fraud cell is
`amount x {1 - costs["fraud_recovery_rate_when_reviewed"]:.2f} + {money(costs["review_cost"])}`.
This matrix is a scenario model; PaySim contains no observed investigation or
recovery costs.

## Confusion matrix by transaction type

{segment_markdown}

Zero false positives at the frozen policy prevents meaningful empirical
false-positive characterization. `false_positive_analysis.csv` therefore also
retains the highest-risk legitimate cases, including those below capacity or
threshold, for boundary review.

## Global explanation

{importance_markdown}

The importance table describes this fitted model on a 2,000-row test sample.
It does not establish causality, individual fairness, or valid reasons for
adverse customer action.

## Monitoring

I would monitor daily volume, review use, fraud outcomes, false positives,
false negatives, mean probability, avoided loss, and score PSI relative to
validation. I would investigate PSI alongside sample size and feature
distributions rather than automatically retraining when a heuristic threshold
is crossed.

## Limitations

1. PaySim is synthetic and encodes simplified fraud behavior.
2. Fraud is unusually separable; performance is not externally valid.
3. Labels are immediate and complete, unlike disputes and chargebacks.
4. There is no investigator feedback, policy feedback, or adversarial response.
5. The cost matrix and capacity are illustrative.
6. Geographic, legal, demographic, privacy, and fairness questions cannot be
   evaluated from these fields.
7. Probability calibration is measured on one simulated future period.

## Governance requirements before real use

Independent validation, documented data lineage, access control, privacy and
fairness review, cost estimation, outcome-label policy, shadow testing,
human-review procedures, override logging, monitoring ownership, incident
response, and scheduled revalidation.
"""
    Path("reports/model_card.md").write_text(model_card, encoding="utf-8")
    print("Generated reports/risk_memo.md and reports/model_card.md.")


if __name__ == "__main__":
    main()
