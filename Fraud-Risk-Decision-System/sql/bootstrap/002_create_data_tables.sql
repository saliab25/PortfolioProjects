BEGIN;

CREATE TABLE IF NOT EXISTS raw.ingestion_batch (
    ingestion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_sha256 CHAR(64) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    source_rows BIGINT,
    accepted_rows BIGINT,
    rejected_rows BIGINT,
    status TEXT NOT NULL DEFAULT 'started'
        CHECK (status IN ('started', 'completed', 'failed')),
    UNIQUE (source_sha256)
);

CREATE TABLE IF NOT EXISTS raw.paysim_transactions (
    transaction_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingestion_id BIGINT NOT NULL
        REFERENCES raw.ingestion_batch (ingestion_id),
    source_row_number BIGINT NOT NULL,
    row_fingerprint CHAR(16) NOT NULL,
    step INTEGER NOT NULL CHECK (step >= 1),
    transaction_type TEXT NOT NULL
        CHECK (transaction_type IN ('CASH_IN', 'CASH_OUT', 'DEBIT', 'PAYMENT', 'TRANSFER')),
    amount NUMERIC(20, 2) NOT NULL CHECK (amount >= 0),
    name_orig TEXT NOT NULL CHECK (name_orig ~ '^C[0-9]+$'),
    old_balance_orig NUMERIC(20, 2) NOT NULL CHECK (old_balance_orig >= 0),
    new_balance_orig NUMERIC(20, 2) NOT NULL CHECK (new_balance_orig >= 0),
    name_dest TEXT NOT NULL CHECK (name_dest ~ '^[CM][0-9]+$'),
    old_balance_dest NUMERIC(20, 2) NOT NULL CHECK (old_balance_dest >= 0),
    new_balance_dest NUMERIC(20, 2) NOT NULL CHECK (new_balance_dest >= 0),
    is_fraud SMALLINT NOT NULL CHECK (is_fraud IN (0, 1)),
    is_flagged_fraud SMALLINT NOT NULL CHECK (is_flagged_fraud IN (0, 1)),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ingestion_id, source_row_number),
    UNIQUE (ingestion_id, row_fingerprint)
);

CREATE INDEX IF NOT EXISTS paysim_transactions_step_idx
    ON raw.paysim_transactions (step);
CREATE INDEX IF NOT EXISTS paysim_transactions_fraud_idx
    ON raw.paysim_transactions (is_fraud)
    WHERE is_fraud = 1;

CREATE TABLE IF NOT EXISTS audit.rejected_rows (
    rejection_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingestion_id BIGINT NOT NULL
        REFERENCES raw.ingestion_batch (ingestion_id),
    source_row_number BIGINT NOT NULL,
    rejection_reason TEXT NOT NULL,
    source_payload JSONB NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON COLUMN raw.paysim_transactions.source_row_number IS
    'Line number in the source CSV, including the header as line 1.';
COMMENT ON COLUMN raw.paysim_transactions.row_fingerprint IS
    'Stable 64-bit content hash rendered as hexadecimal for duplicate detection.';
COMMENT ON COLUMN raw.paysim_transactions.is_flagged_fraud IS
    'Existing simulated rule output. Retained for audit and comparison, excluded from model features.';

COMMIT;

