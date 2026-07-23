# Reports

This directory contains the generated model card, one-page risk memo, frozen
metrics, and figures. Every stated operating metric identifies its data split,
threshold, capacity assumption, and cost assumption.

Run `python scripts/generate_reports.py` after training to regenerate the two
Markdown reports from `metrics/final_metrics.json` and the supporting CSVs.
