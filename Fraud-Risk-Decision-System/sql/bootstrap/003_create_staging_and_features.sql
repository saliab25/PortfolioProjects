BEGIN;

CREATE OR REPLACE VIEW staging.paysim_transactions AS
SELECT
    transaction_id,
    ingestion_id,
    source_row_number,
    step,
    ((step - 1) / 24)::INTEGER AS day_index,
    ((step - 1) % 24)::SMALLINT AS hour_of_day,
    transaction_type,
    amount,
    name_orig,
    old_balance_orig,
    new_balance_orig,
    name_dest,
    old_balance_dest,
    new_balance_dest,
    is_fraud,
    is_flagged_fraud,
    loaded_at
FROM raw.paysim_transactions;

CREATE OR REPLACE VIEW features.transaction_features AS
SELECT
    transaction_id,
    step,
    day_index,
    hour_of_day,
    transaction_type,
    amount,
    LN(1 + amount) AS log_amount,
    old_balance_orig,
    old_balance_dest,
    amount / GREATEST(old_balance_orig, 1) AS amount_to_orig_balance,
    amount / GREATEST(old_balance_dest, 1) AS amount_to_dest_balance,
    (old_balance_orig = 0)::INTEGER AS origin_balance_is_zero,
    (old_balance_dest = 0)::INTEGER AS destination_balance_is_zero,
    (amount > old_balance_orig)::INTEGER AS origin_has_insufficient_balance,
    (name_dest LIKE 'M%')::INTEGER AS destination_is_merchant,
    is_fraud
FROM staging.paysim_transactions;

COMMENT ON VIEW features.transaction_features IS
    'Pre-settlement model matrix. Post-transaction balances, identifiers, and existing rule output are excluded.';

COMMIT;

