# Reproduction and operating runbook

## First-time setup

```powershell
Copy-Item .env.example .env
# Edit .env and choose a local-only password.
docker compose up -d postgres
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install -e . --no-deps
python scripts/bootstrap_database.py
```

Docker runs PostgreSQL; Python remains on the host for a fast development loop.
The same SQL is executed in GitHub Actions against a temporary PostgreSQL
service.

## Full pipeline

```powershell
python scripts/download_data.py
python scripts/prepare_data.py
python scripts/ingest_postgres.py
python scripts/train_and_evaluate.py
python scripts/generate_reports.py
streamlit run app/streamlit_app.py
```

`ingest_postgres.py` may be skipped when only reproducing model artifacts, but
the portfolio's database evidence is incomplete until it has been run.
`prepare_data.py` refuses to replace existing parts unless `--overwrite` is
explicitly supplied.

To run the fitted interface in a container after training:

```powershell
docker compose --profile app up --build app
```

The model and reports are mounted read-only into the application container.

## Quality gates

```powershell
ruff check .
pytest
python -m fraud_system.healthcheck
```

The source CSV and derived data are ignored by Git. Commit source metadata,
quality summaries, report metrics, figures, SQL, tests, and documentation.

## Failure handling

- Schema mismatch: stop; do not infer renamed columns.
- Invalid rows: preserve payload and reason in the audit layer.
- Duplicate content: stop before training and investigate.
- Database batch failure: mark the batch failed before retrying.
- Missing model artifact: the Streamlit app refuses to score.
- Capacity overflow: rank eligible cases by expected preventable value.
- Drift alert: investigate data generation and performance; do not
  automatically retrain solely because PSI crossed a heuristic boundary.
