BEGIN;

CREATE TABLE IF NOT EXISTS monitoring.model_run (
    model_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    trained_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    train_end_step INTEGER NOT NULL,
    validation_end_step INTEGER NOT NULL,
    probability_threshold DOUBLE PRECISION NOT NULL
        CHECK (probability_threshold BETWEEN 0 AND 1),
    review_capacity_per_day INTEGER NOT NULL CHECK (review_capacity_per_day > 0),
    assumptions JSONB NOT NULL,
    metrics JSONB NOT NULL,
    UNIQUE (model_name, model_version)
);

CREATE TABLE IF NOT EXISTS monitoring.prediction (
    model_run_id BIGINT NOT NULL
        REFERENCES monitoring.model_run (model_run_id),
    transaction_id BIGINT NOT NULL
        REFERENCES raw.paysim_transactions (transaction_id),
    fraud_probability DOUBLE PRECISION NOT NULL
        CHECK (fraud_probability BETWEEN 0 AND 1),
    expected_net_value NUMERIC(20, 2) NOT NULL,
    review_decision BOOLEAN NOT NULL,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (model_run_id, transaction_id)
);

CREATE TABLE IF NOT EXISTS monitoring.daily_metrics (
    model_run_id BIGINT NOT NULL
        REFERENCES monitoring.model_run (model_run_id),
    day_index INTEGER NOT NULL,
    transaction_count BIGINT NOT NULL,
    review_count BIGINT NOT NULL,
    observed_fraud_count BIGINT,
    true_positive_count BIGINT,
    false_positive_count BIGINT,
    false_negative_count BIGINT,
    mean_probability DOUBLE PRECISION NOT NULL,
    population_stability_index DOUBLE PRECISION,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (model_run_id, day_index)
);

COMMIT;

