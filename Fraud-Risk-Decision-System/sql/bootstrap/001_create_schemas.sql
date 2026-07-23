BEGIN;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS features;
CREATE SCHEMA IF NOT EXISTS monitoring;
CREATE SCHEMA IF NOT EXISTS audit;

COMMENT ON SCHEMA raw IS
    'Source-faithful accepted records and ingestion metadata.';
COMMENT ON SCHEMA staging IS
    'Validated, typed, cleaned, and documented records.';
COMMENT ON SCHEMA features IS
    'Point-in-time features safe for model training and scoring.';
COMMENT ON SCHEMA monitoring IS
    'Predictions, outcomes, operating metrics, and drift summaries.';
COMMENT ON SCHEMA audit IS
    'Rejected records and traceability for data and model operations.';

COMMIT;

