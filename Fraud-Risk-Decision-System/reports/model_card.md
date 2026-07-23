# Model card: PaySim fraud review system

## Summary

- **Champion:** `lightgbm_2`
- **Version:** `1.0.0`
- **Intended use:** I built this as a public portfolio demonstration of
  transaction-review prioritization.
- **Prohibited use:** real approval, decline, account restriction, law
  enforcement, customer treatment, or financial-loss forecasting.
- **Data:** PaySim synthetic mobile-money transactions.

## Data and split

The source contained 6,362,620 accepted rows and an
overall fraud rate of 0.13%. I split whole
simulated hours chronologically:

| Partition | Rows/rate |
|---|---:|
| Training | 6,082,007 (0.10%) |
| Estimator fit after negative sampling | 240,057 |
| Calibration | 91,560 |
| Validation | 191,147 (0.62%) |
| Test | 89,466 (1.40%) |

Training ends at step 520; validation ends at step
631. The rising fraud prevalence is evidence of
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

| model               |   validation_pr_auc |   validation_policy_cost |   selected_threshold | class_weight   |   learning_rate |   num_leaves |   n_estimators |   min_child_samples |
|:--------------------|--------------------:|-------------------------:|---------------------:|:---------------|----------------:|-------------:|---------------:|--------------------:|
| lightgbm_2          |            1        |              2.35446e+08 |                0.995 | nan            |            0.03 |           63 |            500 |                 200 |
| lightgbm_1          |            1        |              2.35446e+08 |                0.995 | nan            |            0.05 |           31 |            300 |                 100 |
| logistic_regression |            0.769958 |              2.76454e+08 |                0.035 | balanced       |          nan    |          nan |            nan |                 nan |

## Frozen test performance

| Metric | Result |
|---|---:|
| PR-AUC / average precision | 0.999321 |
| ROC-AUC | 0.999935 |
| Brier score | 0.00001119 |
| Expected calibration error | 0.00001328 |
| Recall at >=80% precision | 99.92% |
| Policy precision | 100.00% |
| Policy recall | 79.87% |

I intentionally omit accuracy as a primary measure because the severe class
imbalance makes it misleading.

## Operating policy

I selected a 99.50% threshold on validation.
I cap eligible positive-value cases at 200 per
day and rank them by expected preventable loss. The test period used the full
daily capacity on 5 days.

The dollar results are scenario calculations, not observed economic outcomes.
They depend directly on the versioned assumptions in
`configs/decision_policy.json`.

### Dollar-cost matrix

| Observed outcome | Allow | Send to review |
|---|---:|---:|
| Legitimate | $0 | review cost + friction cost = $16 |
| Fraud | amount x loss rate | unrecovered amount + review cost |

For the configured 85.00%
recovery rate, the reviewed-fraud cell is
`amount x 0.15 + $4`.
This matrix is a scenario model; PaySim contains no observed investigation or
recovery costs.

## Confusion matrix by transaction type

| segment   |   transactions |   fraud |   true_positives |   false_positives |   false_negatives |   true_negatives |   precision |   recall |
|:----------|---------------:|--------:|-----------------:|------------------:|------------------:|-----------------:|------------:|---------:|
| PAYMENT   |          30062 |       0 |                0 |                 0 |                 0 |            30062 |           0 | 0        |
| CASH_OUT  |          29152 |     626 |              495 |                 0 |               131 |            28526 |           1 | 0.790735 |
| CASH_IN   |          20713 |       0 |                0 |                 0 |                 0 |            20713 |           0 | 0        |
| TRANSFER  |           8827 |     626 |              505 |                 0 |               121 |             8201 |           1 | 0.806709 |
| DEBIT     |            712 |       0 |                0 |                 0 |                 0 |              712 |           0 | 0        |

Zero false positives at the frozen policy prevents meaningful empirical
false-positive characterization. `false_positive_analysis.csv` therefore also
retains the highest-risk legitimate cases, including those below capacity or
threshold, for boundary review.

## Global explanation

| feature                                  |   importance | method             |
|:-----------------------------------------|-------------:|:-------------------|
| numeric__origin_has_insufficient_balance |    3.24698   | mean_absolute_shap |
| numeric__amount_to_orig_balance          |    2.98676   | mean_absolute_shap |
| numeric__step                            |    0.200823  | mean_absolute_shap |
| numeric__old_balance_orig                |    0.18175   | mean_absolute_shap |
| categorical__type_PAYMENT                |    0.165796  | mean_absolute_shap |
| categorical__type_CASH_IN                |    0.127872  | mean_absolute_shap |
| numeric__old_balance_dest                |    0.12166   | mean_absolute_shap |
| numeric__amount_to_dest_balance          |    0.120517  | mean_absolute_shap |
| numeric__amount                          |    0.0712086 | mean_absolute_shap |
| numeric__hour_of_day                     |    0.0334056 | mean_absolute_shap |

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
