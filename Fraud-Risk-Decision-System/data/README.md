# Data directory

PaySim is synthetic mobile-money transaction data from the
[`ealaxi/paysim1` Kaggle dataset](https://www.kaggle.com/datasets/ealaxi/paysim1).
The downloaded dataset is not committed to Git.

- `raw/`: immutable source files downloaded from Kaggle;
- `processed/`: local exports derived from versioned SQL or Python code.

The verified source used for the frozen run has SHA-256
`16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`.
Validation observed:

- 6,362,620 source and accepted rows;
- 8,213 fraud rows (0.129%);
- 16 rows flagged by the simulator's existing rule;
- zero rejected rows;
- zero exact duplicate-content rows.

`source_metadata.json` and `quality_summary.json` are committed evidence. The
CSV and Parquet parts remain ignored because they are large, reproducible
derived/local data.
