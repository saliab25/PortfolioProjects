# Notebooks

Notebooks are for investigation and communication. Reusable transformations,
model fitting, threshold selection, and inference belong in `src/fraud_system`.

`01_results_walkthrough.ipynb` reads frozen artifacts and explains the split,
model comparison, policy, and monitoring results. It deliberately does not
duplicate pipeline logic in cells. The notebook has been executed headlessly as
a verification check; outputs are left clear in the committed version so diffs
remain small and deterministic.
