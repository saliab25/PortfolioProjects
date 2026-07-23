"""Train, select, calibrate, and evaluate the fraud review system."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

matplotlib_cache = Path("work/matplotlib").resolve()
matplotlib_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter
from sklearn.metrics import PrecisionRecallDisplay, confusion_matrix

from fraud_system.data_io import load_prepared_transactions
from fraud_system.decision_policy import (
    CostAssumptions,
    apply_review_policy,
    evaluate_review_policy,
    select_policy_threshold,
)
from fraud_system.evaluation import (
    calibration_table,
    confusion_by_segment,
    probability_metrics,
)
from fraud_system.features import MODEL_FEATURES, build_decision_time_features
from fraud_system.modeling import (
    CandidateResult,
    ModelBundle,
    fit_candidate_models,
    save_model_bundle,
)
from fraud_system.monitoring import daily_monitoring_table
from fraud_system.splitting import chronological_split, split_fit_and_calibration


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sample_fit_partition(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    negative_to_positive_ratio: int,
    random_seed: int,
) -> tuple[pd.DataFrame, pd.Series]:
    """Retain every fraud and deterministically sample non-fraud for fitting.

    Sampling is limited to the estimator-fitting partition. Calibration,
    validation, and test keep their natural class balance, so reported
    probabilities and metrics represent the dataset rather than the sample.
    """
    positive_positions = np.flatnonzero(target.to_numpy() == 1)
    negative_positions = np.flatnonzero(target.to_numpy() == 0)
    negative_count = min(
        len(negative_positions),
        len(positive_positions) * negative_to_positive_ratio,
    )
    generator = np.random.default_rng(random_seed)
    selected_negative = generator.choice(
        negative_positions,
        size=negative_count,
        replace=False,
    )
    selected = np.sort(np.concatenate((positive_positions, selected_negative)))
    return (
        features.iloc[selected].reset_index(drop=True),
        target.iloc[selected].reset_index(drop=True),
    )


def plot_precision_recall(
    target: pd.Series,
    candidates: list[CandidateResult],
    output_path: Path,
) -> None:
    figure, axis = plt.subplots(figsize=(8, 6))
    for candidate in candidates:
        PrecisionRecallDisplay.from_predictions(
            target,
            candidate.validation_probabilities,
            name=candidate.name,
            ax=axis,
        )
    baseline = float(target.mean())
    axis.axhline(
        baseline,
        color="grey",
        linestyle="--",
        label=f"prevalence={baseline:.4f}",
    )
    axis.set_title("Validation precision-recall curves")
    axis.legend(loc="best")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def plot_calibration(table: pd.DataFrame, output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(7, 6))
    axis.plot([0, 1], [0, 1], linestyle="--", color="grey", label="perfect calibration")
    axis.plot(
        table["mean_predicted_probability"],
        table["observed_fraud_rate"],
        marker="o",
        label="champion",
    )
    axis.set(
        xlabel="Mean predicted probability",
        ylabel="Observed fraud rate",
        title="Test-set calibration",
    )
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def plot_policy_cost(table: pd.DataFrame, selected_threshold: float, output_path: Path) -> None:
    ordered = table.sort_values("threshold")
    figure, axis = plt.subplots(figsize=(8, 6))
    axis.plot(ordered["threshold"], ordered["total_cost"])
    axis.axvline(
        selected_threshold,
        color="crimson",
        linestyle="--",
        label=f"selected={selected_threshold:.4f}",
    )
    axis.set(
        xlabel="Calibrated probability threshold",
        ylabel="Validation cost",
        title="Cost-sensitive threshold selection",
    )
    if selected_threshold >= 0.9:
        axis.set_xlim(max(0, selected_threshold - 0.05), 1.001)
    axis.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"${value / 1_000_000:,.0f}M")
    )
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def plot_confusion(target: pd.Series, review: pd.Series, output_path: Path) -> None:
    matrix = confusion_matrix(target, review, labels=[0, 1])
    figure, axis = plt.subplots(figsize=(6, 5))
    image = axis.imshow(matrix, cmap="Blues")
    for row in range(2):
        for column in range(2):
            color = "white" if matrix[row, column] > matrix.max() / 2 else "black"
            axis.text(
                column,
                row,
                f"{matrix[row, column]:,}",
                ha="center",
                va="center",
                color=color,
            )
    axis.set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["Allow", "Review"],
        yticklabels=["Legitimate", "Fraud"],
        xlabel="Policy decision",
        ylabel="Observed label",
        title="Test confusion matrix",
    )
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def explain_champion(
    candidate: CandidateResult,
    sample: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write global feature importance for either supported model family."""
    calibrated_classifier = candidate.model.calibrated_classifiers_[0]
    pipeline = calibrated_classifier.estimator
    preprocessor = pipeline.named_steps["preprocess"]
    estimator = pipeline.named_steps["model"]
    transformed = preprocessor.transform(sample.loc[:, MODEL_FEATURES])
    names = preprocessor.get_feature_names_out()

    if candidate.name.startswith("lightgbm"):
        import shap

        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()
        values = shap.TreeExplainer(estimator).shap_values(transformed)
        if isinstance(values, list):
            values = values[-1]
        importance = np.abs(values).mean(axis=0)
        method = "mean_absolute_shap"
    else:
        importance = np.abs(estimator.coef_[0])
        method = "absolute_logistic_coefficient"

    pd.DataFrame(
        {
            "feature": names,
            "importance": importance,
            "method": method,
        }
    ).sort_values("importance", ascending=False).to_csv(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--accepted-dir",
        type=Path,
        default=Path("data/processed/accepted"),
    )
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    model_config = load_json(Path("configs/model.json"))
    policy_config = load_json(Path("configs/decision_policy.json"))
    costs = CostAssumptions(
        **{key: value for key, value in policy_config.items() if key != "threshold_grid_size"}
    )
    random_seed = int(model_config["random_seed"])
    np.random.seed(random_seed)

    args.artifacts_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = args.reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir = args.reports_dir / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    transactions = load_prepared_transactions(args.accepted_dir)
    feature_set = build_decision_time_features(transactions)
    split = chronological_split(
        feature_set.features["step"],
        train_fraction=model_config["train_fraction"],
        validation_fraction=model_config["validation_fraction"],
    )

    train_features = feature_set.features.loc[split.train].reset_index(drop=True)
    train_target = feature_set.target.loc[split.train].reset_index(drop=True)
    fit_mask, calibration_mask = split_fit_and_calibration(
        train_features["step"],
        calibration_fraction=model_config["calibration_fraction_within_train"],
    )
    fit_features, fit_target = sample_fit_partition(
        train_features.loc[fit_mask].reset_index(drop=True),
        train_target.loc[fit_mask].reset_index(drop=True),
        negative_to_positive_ratio=model_config["training_negative_to_positive_ratio"],
        random_seed=random_seed,
    )
    calibration_features = train_features.loc[calibration_mask].reset_index(drop=True)
    calibration_target = train_target.loc[calibration_mask].reset_index(drop=True)
    validation_features = feature_set.features.loc[split.validation].reset_index(drop=True)
    validation_target = feature_set.target.loc[split.validation].reset_index(drop=True)
    validation_context = feature_set.policy_context.loc[split.validation].reset_index(drop=True)
    test_features = feature_set.features.loc[split.test].reset_index(drop=True)
    test_target = feature_set.target.loc[split.test].reset_index(drop=True)
    test_context = feature_set.policy_context.loc[split.test].reset_index(drop=True)

    candidates = fit_candidate_models(
        fit_features,
        fit_target,
        calibration_features,
        calibration_target,
        validation_features,
        validation_target,
        lightgbm_candidates=model_config["lightgbm_candidates"],
        random_seed=random_seed,
    )
    candidate_rows = []
    policy_tables: dict[str, pd.DataFrame] = {}
    selected_policies = {}
    for candidate in candidates:
        selected_policy, policy_table = select_policy_threshold(
            candidate.validation_probabilities,
            validation_target,
            validation_context,
            costs=costs,
            grid_size=policy_config["threshold_grid_size"],
        )
        selected_policies[candidate.name] = selected_policy
        policy_tables[candidate.name] = policy_table
        candidate_rows.append(
            {
                "model": candidate.name,
                "validation_pr_auc": candidate.validation_pr_auc,
                "validation_policy_cost": selected_policy.total_cost,
                "selected_threshold": selected_policy.threshold,
                **candidate.parameters,
            }
        )

    champion = min(
        candidates,
        key=lambda candidate: (
            selected_policies[candidate.name].total_cost,
            -candidate.validation_pr_auc,
        ),
    )
    validation_policy = selected_policies[champion.name]
    test_probabilities = champion.model.predict_proba(test_features.loc[:, MODEL_FEATURES])[:, 1]
    test_probability_metrics = probability_metrics(
        test_target,
        test_probabilities,
        minimum_precision=model_config["minimum_precision_target"],
    )
    test_policy = evaluate_review_policy(
        test_probabilities,
        test_target,
        test_context,
        threshold=validation_policy.threshold,
        costs=costs,
    )
    test_review = apply_review_policy(
        test_probabilities,
        test_context,
        threshold=validation_policy.threshold,
        costs=costs,
    )

    candidate_table = pd.DataFrame(candidate_rows).sort_values(
        ["validation_policy_cost", "validation_pr_auc"],
        ascending=[True, False],
    )
    segment_table = confusion_by_segment(
        test_target,
        test_review,
        test_context["type"],
    )
    amount_band = pd.cut(
        test_context["amount"],
        bins=[-np.inf, 100, 1_000, 10_000, 100_000, np.inf],
        labels=["<=100", "100-1k", "1k-10k", "10k-100k", ">100k"],
    )
    amount_segment_table = confusion_by_segment(test_target, test_review, amount_band)
    calibration = calibration_table(test_target, test_probabilities)
    daily_monitoring = daily_monitoring_table(
        test_probabilities,
        test_target,
        test_context,
        test_review,
        reference_probabilities=champion.validation_probabilities,
        costs=costs,
    )
    decision_analysis = test_context.copy()
    decision_analysis["actual_fraud"] = test_target
    decision_analysis["probability"] = test_probabilities
    decision_analysis["review_decision"] = test_review
    false_positive_analysis = (
        decision_analysis.loc[decision_analysis["actual_fraud"].eq(0)]
        .sort_values(["review_decision", "probability", "amount"], ascending=False)
        .head(100)
    )

    split_summary = {
        "source_rows_loaded": int(len(transactions)),
        "train_rows": int(split.train.sum()),
        "fit_rows_after_negative_sampling": int(len(fit_features)),
        "calibration_rows": int(calibration_mask.sum()),
        "validation_rows": int(split.validation.sum()),
        "test_rows": int(split.test.sum()),
        "train_end_step": split.train_end_step,
        "validation_end_step": split.validation_end_step,
        "overall_fraud_rate": float(feature_set.target.mean()),
        "train_fraud_rate": float(feature_set.target.loc[split.train].mean()),
        "validation_fraud_rate": float(validation_target.mean()),
        "test_fraud_rate": float(test_target.mean()),
    }
    final_metrics = {
        "champion": champion.name,
        "split": split_summary,
        "cost_assumptions": costs.as_dict(),
        "validation_policy": validation_policy.as_dict(),
        "test_probability_metrics": test_probability_metrics,
        "test_policy": test_policy.as_dict(),
    }

    candidate_table.to_csv(metrics_dir / "candidate_comparison.csv", index=False)
    policy_tables[champion.name].to_csv(
        metrics_dir / "validation_threshold_search.csv",
        index=False,
    )
    segment_table.to_csv(metrics_dir / "confusion_by_transaction_type.csv", index=False)
    amount_segment_table.to_csv(metrics_dir / "confusion_by_amount_band.csv", index=False)
    calibration.to_csv(metrics_dir / "test_calibration.csv", index=False)
    daily_monitoring.to_csv(metrics_dir / "daily_monitoring.csv", index=False)
    false_positive_analysis.to_csv(
        metrics_dir / "false_positive_analysis.csv",
        index=False,
    )
    (metrics_dir / "final_metrics.json").write_text(
        json.dumps(final_metrics, indent=2) + "\n",
        encoding="utf-8",
    )

    plot_precision_recall(
        validation_target,
        candidates,
        figures_dir / "validation_precision_recall.png",
    )
    plot_calibration(calibration, figures_dir / "test_calibration.png")
    plot_policy_cost(
        policy_tables[champion.name],
        validation_policy.threshold,
        figures_dir / "validation_policy_cost.png",
    )
    plot_confusion(test_target, test_review, figures_dir / "test_confusion_matrix.png")

    explanation_sample = test_features.sample(
        n=min(2_000, len(test_features)),
        random_state=random_seed,
    )
    explain_champion(
        champion,
        explanation_sample,
        metrics_dir / "global_feature_importance.csv",
    )

    bundle = ModelBundle(
        model=champion.model,
        model_name=champion.name,
        feature_names=MODEL_FEATURES,
        probability_threshold=validation_policy.threshold,
        review_capacity_per_day=costs.review_capacity_per_day,
        cost_assumptions=costs.as_dict(),
        train_end_step=split.train_end_step,
        validation_end_step=split.validation_end_step,
    )
    save_model_bundle(bundle, str(args.artifacts_dir / "champion_model.joblib"))
    (args.artifacts_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "random_seed": random_seed,
                "model_config": model_config,
                "policy_config": policy_config,
                "champion_parameters": champion.parameters,
                "bundle": {key: value for key, value in asdict(bundle).items() if key != "model"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(final_metrics, indent=2))


if __name__ == "__main__":
    main()
