# Data dictionary and availability audit

PaySim is a synthetic mobile-money simulation. I retain the source fields in
PostgreSQL even when I exclude them from the model.

| Source field | Canonical field | Meaning | Main-model use | Reason |
|---|---|---|---|---|
| `step` | `step` | Simulated hour | Yes | Available at authorization |
| `type` | `transaction_type` / `type` | Transaction category | Yes | Available at authorization |
| `amount` | `amount` | Transaction value | Yes | Needed for risk and loss |
| `nameOrig` | `name_orig` | Origin account identifier | No | Memorization/privacy risk; no stable real mapping |
| `oldbalanceOrg` | `old_balance_orig` | Origin balance before transaction | Yes | Assumed available before settlement |
| `newbalanceOrig` | `new_balance_orig` | Origin balance after transaction | No | Post-transaction state |
| `nameDest` | `name_dest` | Destination identifier | Prefix only | Merchant prefix is used; identity is excluded |
| `oldbalanceDest` | `old_balance_dest` | Destination balance before transaction | Yes | Assumed available before settlement |
| `newbalanceDest` | `new_balance_dest` | Destination balance after transaction | No | Post-transaction state |
| `isFraud` | `is_fraud` | Simulated fraud label | Target only | Outcome leakage if used as input |
| `isFlaggedFraud` | `is_flagged_fraud` | Existing simulated rule | No | Existing decision output, not an independent predictor |

## Derived features

| Feature | Definition | Motivation |
|---|---|---|
| `hour_of_day` | `(step - 1) mod 24` | Captures time-of-day patterns |
| `day_index` | integer division of `(step - 1)` by 24 | Supports monitoring and capacity |
| `log_amount` | `log(1 + amount)` | Compresses a long-tailed amount distribution |
| `amount_to_orig_balance` | `amount / max(old_balance_orig, 1)` | Measures transaction size relative to funds |
| `amount_to_dest_balance` | `amount / max(old_balance_dest, 1)` | Measures size relative to destination history |
| `origin_balance_is_zero` | indicator | Avoids hiding the special zero-balance case inside a ratio |
| `destination_balance_is_zero` | indicator | Same rationale for destination |
| `origin_has_insufficient_balance` | `amount > old_balance_orig` | Captures an interpretable balance inconsistency |
| `destination_is_merchant` | destination starts with `M` | Uses entity type without retaining identity |
