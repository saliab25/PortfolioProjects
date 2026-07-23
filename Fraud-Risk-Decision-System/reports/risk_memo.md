# Fraud review policy: one-page risk memo

**Recommendation.** For this portfolio project, I recommend routing
transactions with calibrated fraud risk of at least
**99.50%** and positive expected review value to a
queue capped at **200 reviews per day**. When the
cap is exceeded, prioritize expected preventable loss rather than probability
alone.

## Held-out operating result

| Measure | Result |
|---|---:|
| Test transactions | 89,466 |
| Observed fraud | 1,252 |
| Reviewed | 1,000 |
| Fraud recall | 79.87% |
| Review precision | 100.00% |
| False positives | 0 |
| Capacity-binding days | 5 |
| Illustrative fraud loss avoided | $1,797,427,294 |
| Policy cost | $332,705,381 |
| No-review cost | $2,130,128,675 |

I selected the threshold only on validation data. I then froze the threshold
and capacity rule before evaluating them once on the final chronological test
period.

## Assumptions

- transaction amounts are treated as illustrative dollars;
- an unrecovered fraud loses 100.00% of amount;
- review recovers 85.00% of a
  detected fraud;
- each review costs $4;
- each legitimate review adds $12
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
