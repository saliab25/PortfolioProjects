# Fraud and Risk Decision System

I built this project to turn fraud probabilities into an actual review
decision. Instead of stopping at model accuracy, I ask which transactions
should be sent to investigators when missed fraud, customer friction, review
cost, and team capacity do not carry the same weight.

> **Data limitation:** I use PaySim, a synthetic mobile-money simulation.
> Results from this project do not show how the model would perform with real
> customers or in any particular financial market.

## The decision I am trying to make

My working question is:

> Which transactions should enter manual review when I have unequal error
> costs and a limited number of investigators?

I turned the answer into a three-part operating policy:

1. require a calibrated fraud probability above a threshold selected on
   validation data;
2. require positive expected value from reviewing the transaction;
3. cap the queue at 200 reviews per day and rank overflow by expected
   preventable loss.

I treat the daily capacity as a scenario, not as a fact contained in PaySim. My
assumption is 25 investigators completing eight reviews each per day. If that
assumption changes, I rerun threshold selection rather than treating the old
threshold as permanent.

## What I built

- PostgreSQL schemas for raw data, staging, features, audit records, and
  monitoring;
- chunked validation of all 6,362,620 source transactions;
- rejected-row logging, source lineage, checksum verification, and duplicate
  detection;
- a feature pipeline based on what I assume is available before settlement;
- chronological fit, calibration, validation, and test periods;
- a logistic-regression baseline and two LightGBM candidates;
- PR-AUC, recall at fixed precision, Brier score, calibration error, and
  segment-level confusion matrices;
- a dollar-cost policy with a daily capacity constraint;
- SHAP importance, boundary-case analysis, and score-distribution monitoring;
- tests, GitHub Actions, Docker, a dependency lock, and a Streamlit interface;
- a model card and a short risk memo generated from the held-out results.

## Final held-out result

The second LightGBM candidate had the lowest validation policy cost. I selected
a 99.5% calibrated-risk threshold, a positive-value requirement, and a
200-case daily limit.

| Held-out measure | Result |
|---|---:|
| Transactions | 89,466 |
| Reviews | 1,000 |
| Fraud recall | 79.87% |
| Review precision | 100.00% |
| Capacity-binding days | 5 |
| Illustrative loss avoided | $1.797 billion |

The 100% precision is not a result I would project onto real fraud. It reflects
how separable the simulated PaySim fraud is under these features. I discuss
that limitation in the [risk memo](reports/risk_memo.md) and
[model card](reports/model_card.md).

## How the pieces fit together

```text
Kaggle PaySim CSV
        |
        v
chunked schema and row validation
        |
        +-- invalid rows --> audit.rejected_rows
        |
        +-- accepted rows --> raw.paysim_transactions
        |                           |
        |                           v
        |                  staging.paysim_transactions
        |                           |
        |                           v
        |                  features.transaction_features
        |
        +-- Parquet analytical cache
                    |
                    v
       fit -> calibrate -> validate -> test
                    |
                    v
       calibrated risk + review policy
                    |
          +---------+---------+
          |                   |
          v                   v
   Streamlit interface   monitoring and reports
```

I use PostgreSQL as the governed system of record. I also keep a derived
Parquet cache so repeated model experiments do not have to transfer 6.36
million rows from PostgreSQL every time. Notebooks present the analysis, while
reusable logic stays in `src/fraud_system`.

## Repository map

| Path | Purpose |
|---|---|
| `sql/bootstrap` | PostgreSQL schemas, tables, views, and constraints |
| `src/fraud_system` | Validation, features, splits, models, policy, metrics, and monitoring |
| `scripts` | Reproducible pipeline commands |
| `configs` | Model settings and operating assumptions |
| `tests` | Data, feature, split, cost, configuration, and monitoring tests |
| `reports` | Model card, risk memo, metrics, and figures |
| `docs` | My design rationale, data dictionary, and runbook |
| `app` | Streamlit decision interface and operating dashboard |
| `data` | Git-ignored source and prepared datasets |
| `artifacts` | Git-ignored fitted model bundle |

## Reproduce the project

I developed the project with Python 3.12 on Windows. Python 3.11 is also
supported. Docker Desktop and Git are required for the full workflow.

```powershell
Copy-Item .env.example .env
# Change POSTGRES_PASSWORD in .env.

docker compose up -d postgres
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install -e . --no-deps

python scripts/bootstrap_database.py
python scripts/download_data.py
python scripts/prepare_data.py
python scripts/ingest_postgres.py
python scripts/train_and_evaluate.py
python scripts/generate_reports.py

ruff check .
pytest
streamlit run app/streamlit_app.py
```

I do not commit the Kaggle CSV. The download script records its SHA-256
checksum and synthetic-data status in `data/raw/source_metadata.json`.

## How I evaluated the models

I split whole simulated hours in chronological order:

- earliest 70% of time: training;
- next 15%: validation;
- final 15%: test.

Within training, I reserve the latest 20% for probability calibration. I
downsample non-fraud only while fitting the estimators. Calibration, validation,
and test keep their natural class balance, so reported precision and
probability quality are not measured on an artificially balanced sample.

I do not use the test set to choose features, model parameters, calibration
method, policy threshold, capacity, or cost assumptions.

## How I handled leakage

I assume the review decision happens before settlement. Based on that decision
time, I exclude:

- the true fraud label;
- PaySim's existing fraud flag;
- balances recorded after the transaction;
- raw customer identifiers.

Some of those columns would improve benchmark performance. I excluded them
because feature legitimacy depends on what is available when a decision is
made, not simply on predictive power. The full audit is in
[docs/data_dictionary.md](docs/data_dictionary.md).

## Why I made these choices

[docs/design_decisions.md](docs/design_decisions.md) explains why I used
PostgreSQL, Parquet, chronological splitting, fit-only downsampling, sigmoid
calibration, PR-AUC, LightGBM, expected-value ranking, and PSI. It also explains
the drawbacks of each choice.

[docs/runbook.md](docs/runbook.md) contains the setup, reproduction, and
failure-handling instructions.

## What I would not claim

PaySim can encode simple simulator rules that make fraud unusually easy to
separate. Real fraud changes in response to controls and involves delayed
labels, investigator feedback, identity networks, disputes, privacy rules, and
regional differences. I view the near-perfect ranking result as a reason for
more scrutiny, not as evidence that this model is ready for deployment.

