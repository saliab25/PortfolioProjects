# Why I designed the project this way

I wrote this note to make my reasoning visible, including the tradeoffs. The
code shows what I implemented; this document explains why I implemented it that
way and what I would reconsider with real data.

## 1. Why I used PostgreSQL instead of DuckDB

DuckDB would have been the simpler analytical option. It runs inside Python,
reads Parquet directly, and does not require a database server.

I chose PostgreSQL for three reasons:

1. it is the database I am most comfortable using;
2. schemas, constraints, transactions, and audit tables resemble a real
   financial-data workflow;
3. I wanted to demonstrate rejected-row logging and monitoring writes, not only
   analytical queries.

The tradeoff is extra setup. I use Docker Compose to make that setup
reproducible. I also keep prepared Parquet files because copying 6.36 million
rows from PostgreSQL for every model experiment would be slow. PostgreSQL is my
governed system of record; Parquet is my local analytical cache.

## 2. Why I separated the database into five schemas

I use schemas as trust boundaries:

- `raw` stores accepted source records and ingestion lineage;
- `staging` gives fields consistent names and types;
- `features` exposes predictors that are valid at the decision time;
- `monitoring` records model versions, decisions, outcomes, and drift;
- `audit` stores rejected records and their reasons.

I could have put everything in `public`, but then it would be harder to tell
whether a column is source evidence, a cleaned interpretation, a model input,
or an operational result.

## 3. Why I reject bad rows instead of repairing them silently

If an amount is negative, I preserve the row and its rejection reason rather
than replacing the amount with zero. Silent fixes can make a pipeline look
robust while hiding an upstream problem.

My validator returns accepted and rejected data separately. I repeat critical
checks as PostgreSQL constraints because Python validation and database
constraints protect against different failure paths.

PaySim does not include a business transaction ID. I retain the CSV line number
for lineage and calculate a content fingerprint for duplicate detection. A
64-bit fingerprint is sufficient for this exercise, but I would not treat it
as a legally authoritative transaction identifier.

## 4. Why I process the CSV in chunks

The source contains 6,362,620 rows. Loading the CSV, copying it during
validation, and creating features can consume several gigabytes.

I read 250,000 rows at a time and write Parquet parts. I chose Parquet because
it preserves types, compresses well, and lets me read only the columns needed
for modeling. I keep the original CSV unchanged and exclude both the CSV and
derived Parquet files from Git.

## 5. How I decided which features were legitimate

I define the decision as a pre-settlement review decision. That choice matters
more than feature correlation because it determines what information would
actually exist when the model scores a transaction.

I include:

- simulation time;
- transaction type and amount;
- balances recorded before the transaction;
- ratios and indicators derived from those values;
- the destination's customer-or-merchant prefix.

I exclude:

- `isFraud`, because it is the outcome;
- `isFlaggedFraud`, because it is an existing simulated rule output;
- new origin and destination balances, because they describe
  post-transaction state;
- raw customer identifiers, because they encourage memorization and have no
  credible governance story in this synthetic dataset.

Some excluded fields would improve performance. I do not consider that a valid
reason to use information that would be unavailable at the stated decision
time.

## 6. Why I used a chronological split

A fraud model scores future transactions. A random split would mix records from
the same simulated periods across training and test, making the evaluation
easier than the intended use.

I assign whole `step` values in chronological order:

1. earliest 70%: training;
2. next 15%: validation;
3. final 15%: test.

I reserve the latest 20% of training for calibration:

```text
estimator fit -> calibration -> model and threshold selection -> final test
```

I do not inspect test results until I have fixed the model and policy. This
split also exposed an important fact: PaySim's fraud rate rises sharply near
the end of the simulation. A random split would have hidden much of that shift.

## 7. Why I downsample only during estimator fitting

Fraud represents about 0.13% of the complete dataset. Using every non-fraud row
for estimator fitting adds substantial compute while giving the model many
similar majority examples.

I keep every fraud row and sample at most 50 non-fraud rows per fraud for the
fit partition. I do not downsample calibration, validation, or test. Those
periods retain the natural fraud prevalence so precision and calibrated
probabilities remain meaningful for this dataset.

## 8. Why I kept a logistic baseline

I use logistic regression as a baseline because it is fast, familiar, and a
useful check on whether nonlinear complexity adds value. I standardize numeric
features and one-hot encode transaction type.

I compare it with LightGBM because boosted trees can learn nonlinear thresholds
and interactions, such as transaction amount relative to account balance. I
predeclared two small parameter sets instead of running a large search. A large
search over one synthetic validation period could overfit the benchmark without
making the project more credible.

I select the operational champion by validation policy cost and use PR-AUC to
break a tie. I do not use accuracy as a primary metric: predicting every
transaction as legitimate would exceed 99% accuracy and still fail the
business problem.

## 9. Why I calibrated probabilities separately

Ranking metrics tell me whether fraud tends to receive a higher score.
The policy's expected-value formula treats the score as a probability, so I
also need the numerical values to be reasonably calibrated.

I fit sigmoid calibration on a later slice of the training period after fitting
each base estimator. I report:

- precision-recall AUC;
- recall at a fixed precision target;
- Brier score;
- expected calibration error;
- a calibration plot.

I include ROC-AUC as a secondary reference, not as the main result. Under
severe imbalance, ROC-AUC can look excellent while the review queue still has
poor precision.

## 10. How I turned probability into a review policy

A probability threshold is not a complete operating policy because the review
team has limited capacity.

I apply three rules:

1. probability must exceed the threshold selected on validation;
2. expected net review value must be positive;
3. when a day exceeds 200 eligible reviews, I select the 200 transactions with
   the highest expected net value.

I model 200 daily reviews as 25 investigators completing eight cases each. This
is my scenario assumption, not a value supplied by PaySim.

```text
expected review value =
    probability * amount * loss rate * recovery rate
    - review cost
    - (1 - probability) * customer-friction cost
```

```text
observed policy cost =
    fraud loss without review
    - recovered fraud loss
    + review costs
    + false-positive friction costs
```

I include transaction amount because missing a $10 fraud and missing a
$100,000 fraud should not have the same financial consequence.

## 11. Why assumptions live in configuration files

I keep review capacity, review cost, friction cost, loss rate, and recovery rate
in `configs/decision_policy.json`. Split fractions, seed, sampling ratio, and
model candidates live in `configs/model.json`.

The selected threshold is conditional on those assumptions. If operations
changes capacity or finance changes the cost estimates, I rerun the policy
search instead of reusing the old threshold.

## 12. What I monitor

My daily monitoring table includes:

- transaction and review volume;
- observed fraud;
- true positives, false positives, and false negatives;
- mean predicted probability;
- illustrative avoided loss;
- score Population Stability Index (PSI) relative to validation.

I use PSI because it is common in financial-risk monitoring and easy to
explain. I do not treat it as a statistical test. A high PSI says that a
distribution changed; it does not identify the cause or prove performance
deteriorated.

## 13. What I learned from the synthetic results

The LightGBM models separate PaySim fraud almost perfectly. I do not interpret
that as evidence of production readiness. It tells me that the simulator
contains strong, learnable fraud patterns.

Real fraud systems also face adaptive attackers, identity and device networks,
delayed chargebacks, disputed labels, investigator feedback, policy feedback
loops, privacy requirements, fairness review, and regional differences. PaySim
does not represent those issues well.

For that reason, I present this project as evidence that I can design and test
a governed fraud-decision workflow. I do not present it as evidence that I have
built a deployable fraud detector.

