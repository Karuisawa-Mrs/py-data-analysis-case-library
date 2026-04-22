# pyright: reportMissingImports=false, reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAny=false, reportMissingTypeArgument=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false, reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportImplicitStringConcatenation=false

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight


CASE_ID = "mkt-008-churn-prediction-benchmark"
CONTINUOUS_COLUMNS = [
    "tenure_months",
    "monthly_charges",
    "avg_monthly_data_gb",
    "support_tickets_90d",
    "payment_delay_days",
    "recent_outage_hours",
    "satisfaction_score",
    "referrals_12m",
]
CATEGORICAL_COLUMNS = ["contract_type", "region_tier"]
BINARY_COLUMNS = [
    "autopay",
    "paperless_billing",
    "fiber_optic",
    "multi_line",
    "streaming_bundle",
    "senior_customer",
]
TARGET_COLUMN = "churned"
DATA_MODE = "simulated"
CLAIM_BOUNDARY = "演示预测模型对比逻辑，不生成因果结论"


@dataclass(frozen=True)
class CaseConfig:
    seed: int
    output_dir: str
    sample_size: int
    smoke_test_sample_size: int
    test_size: float
    positive_class_floor: float
    positive_class_ceiling: float
    logistic_max_iter: int
    gradient_boosting_estimators: int
    gradient_boosting_learning_rate: float
    gradient_boosting_max_depth: int
    gradient_boosting_subsample: float
    top_feature_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate telecom churn data and benchmark Logistic Regression against Gradient Boosting. "
            "analysis.py is the single source of truth."
        )
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a smaller deterministic benchmark while still generating all required artifacts.",
    )
    return parser.parse_args()


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    output_dir = case_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "case_dir": case_dir,
        "output_dir": output_dir,
        "params_file": case_dir / "params.yaml",
        "index_file": case_dir / "index.md",
    }


def load_config(params_file: Path) -> CaseConfig:
    payload = yaml.safe_load(params_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("params.yaml must parse to a mapping")

    return CaseConfig(
        seed=int(payload["seed"]),
        output_dir=str(payload["output_dir"]),
        sample_size=int(payload["sample_size"]),
        smoke_test_sample_size=int(payload["smoke_test_sample_size"]),
        test_size=float(payload["test_size"]),
        positive_class_floor=float(payload["positive_class_floor"]),
        positive_class_ceiling=float(payload["positive_class_ceiling"]),
        logistic_max_iter=int(payload["logistic_max_iter"]),
        gradient_boosting_estimators=int(payload["gradient_boosting_estimators"]),
        gradient_boosting_learning_rate=float(payload["gradient_boosting_learning_rate"]),
        gradient_boosting_max_depth=int(payload["gradient_boosting_max_depth"]),
        gradient_boosting_subsample=float(payload["gradient_boosting_subsample"]),
        top_feature_count=int(payload["top_feature_count"]),
    )


def clipped_normal(rng: np.random.Generator, mean: float, std: float, size: int, low: float, high: float) -> np.ndarray:
    values = rng.normal(loc=mean, scale=std, size=size)
    return np.clip(values, low, high)


def simulate_dataset(config: CaseConfig, smoke_test: bool) -> pd.DataFrame:
    size = config.smoke_test_sample_size if smoke_test else config.sample_size
    rng = np.random.default_rng(config.seed + (101 if smoke_test else 0))

    tenure_months = rng.integers(1, 73, size=size)
    contract_type = rng.choice(
        ["month-to-month", "one-year", "two-year"],
        size=size,
        p=[0.57, 0.27, 0.16],
    )
    region_tier = rng.choice(["tier1", "tier2", "tier3"], size=size, p=[0.28, 0.45, 0.27])
    senior_customer = rng.binomial(1, 0.19, size=size)
    fiber_optic = rng.binomial(1, 0.48, size=size)
    multi_line = rng.binomial(1, 0.41, size=size)
    streaming_bundle = rng.binomial(1, 0.36 + 0.10 * fiber_optic, size=size)
    autopay = rng.binomial(1, 0.60 - 0.18 * (contract_type == "month-to-month"), size=size)
    paperless_billing = rng.binomial(1, 0.68, size=size)
    support_tickets_90d = np.clip(rng.poisson(lam=1.2 + 0.8 * fiber_optic, size=size), 0, 10)
    referrals_12m = np.clip(rng.poisson(lam=0.9 + 0.5 * autopay, size=size), 0, 8)

    monthly_charges = (
        42
        + 0.62 * tenure_months
        + 17.5 * fiber_optic
        + 7.0 * multi_line
        + 11.0 * streaming_bundle
        + clipped_normal(rng, 0.0, 8.5, size, -22.0, 24.0)
    )
    monthly_charges = np.clip(monthly_charges, 28.0, 145.0)

    avg_monthly_data_gb = (
        8.0
        + 12.0 * fiber_optic
        + 6.5 * streaming_bundle
        + clipped_normal(rng, 0.0, 5.0, size, -10.0, 16.0)
    )
    avg_monthly_data_gb = np.clip(avg_monthly_data_gb, 0.5, 52.0)

    payment_delay_days = np.maximum(
        0.0,
        clipped_normal(
            rng,
            mean=2.5 + 1.9 * (1 - autopay) + 1.2 * (contract_type == "month-to-month"),
            std=3.2,
            size=size,
            low=0.0,
            high=26.0,
        ),
    )

    recent_outage_hours = np.maximum(
        0.0,
        clipped_normal(
            rng,
            mean=1.2 + 1.4 * fiber_optic + 0.4 * (region_tier == "tier3"),
            std=1.7,
            size=size,
            low=0.0,
            high=13.0,
        ),
    )

    satisfaction_score = clipped_normal(
        rng,
        mean=(7.4 + 0.5 * autopay + 0.3 * (contract_type != "month-to-month") - 0.45 * support_tickets_90d - 0.18 * recent_outage_hours),
        std=1.0,
        size=size,
        low=1.0,
        high=10.0,
    )

    linear_score = (
        -2.35
        + 0.95 * (contract_type == "month-to-month")
        - 0.58 * (contract_type == "two-year")
        - 0.020 * tenure_months
        + 0.018 * monthly_charges
        + 0.17 * support_tickets_90d
        + 0.11 * payment_delay_days
        + 0.26 * recent_outage_hours
        - 0.48 * autopay
        - 0.10 * paperless_billing
        + 0.19 * fiber_optic
        + 0.14 * senior_customer
        - 0.42 * streaming_bundle
        - 0.10 * multi_line
        - 0.56 * referrals_12m
        - 0.60 * (satisfaction_score - 6.0)
        + 0.18 * (region_tier == "tier3")
        - 0.003 * avg_monthly_data_gb
        + 0.07 * support_tickets_90d * (contract_type == "month-to-month")
        + 0.04 * payment_delay_days * (satisfaction_score < 5.5)
    )

    churn_probability = 1.0 / (1.0 + np.exp(-linear_score))
    churn_rate = float(churn_probability.mean())
    if not (config.positive_class_floor <= churn_rate <= config.positive_class_ceiling):
        raise ValueError(
            "simulated churn rate fell outside configured bounds: "
            f"{churn_rate:.3f} not in [{config.positive_class_floor:.3f}, {config.positive_class_ceiling:.3f}]"
        )

    churned = rng.binomial(1, churn_probability)

    dataset = pd.DataFrame(
        {
            "customer_id": np.arange(1, size + 1, dtype=int),
            "tenure_months": tenure_months,
            "monthly_charges": monthly_charges,
            "avg_monthly_data_gb": avg_monthly_data_gb,
            "support_tickets_90d": support_tickets_90d,
            "payment_delay_days": payment_delay_days,
            "recent_outage_hours": recent_outage_hours,
            "satisfaction_score": satisfaction_score,
            "referrals_12m": referrals_12m,
            "autopay": autopay,
            "paperless_billing": paperless_billing,
            "fiber_optic": fiber_optic,
            "multi_line": multi_line,
            "streaming_bundle": streaming_bundle,
            "senior_customer": senior_customer,
            "contract_type": contract_type,
            "region_tier": region_tier,
            TARGET_COLUMN: churned,
        }
    )
    return dataset


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_preprocessor() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", make_one_hot_encoder()),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, CONTINUOUS_COLUMNS),
            ("cat", categorical_pipeline, CATEGORICAL_COLUMNS),
            ("bin", "passthrough", BINARY_COLUMNS),
        ]
    )


def transformed_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    numeric_names = CONTINUOUS_COLUMNS.copy()
    onehot = preprocessor.named_transformers_["cat"].named_steps["onehot"]
    categorical_names = onehot.get_feature_names_out(CATEGORICAL_COLUMNS).tolist()
    return numeric_names + categorical_names + BINARY_COLUMNS.copy()


def fit_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    config: CaseConfig,
) -> tuple[Pipeline, Pipeline, list[str]]:
    logistic = Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=config.logistic_max_iter,
                    random_state=config.seed,
                    solver="lbfgs",
                ),
            ),
        ]
    )
    logistic.fit(X_train, y_train)

    gradient = Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            (
                "model",
                GradientBoostingClassifier(
                    n_estimators=config.gradient_boosting_estimators,
                    learning_rate=config.gradient_boosting_learning_rate,
                    max_depth=config.gradient_boosting_max_depth,
                    subsample=config.gradient_boosting_subsample,
                    random_state=config.seed,
                ),
            ),
        ]
    )
    model_sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)
    gradient.fit(X_train, y_train, model__sample_weight=model_sample_weight)

    feature_names = transformed_feature_names(logistic.named_steps["preprocess"])
    return logistic, gradient, feature_names


def best_f1_threshold(y_true: pd.Series, y_score: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, y_score)
    if len(thresholds) == 0:
        return 0.5
    f1_scores = 2.0 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-9)
    best_index = int(np.nanargmax(f1_scores))
    return float(thresholds[best_index])


def evaluate_model(name: str, model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float | str | np.ndarray]:
    probabilities = model.predict_proba(X_test)[:, 1]
    threshold = best_f1_threshold(y_test, probabilities)
    predictions = (probabilities >= threshold).astype(int)
    metrics: dict[str, float | str | np.ndarray] = {
        "model": name,
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
        "f1_at_best_threshold": float(f1_score(y_test, predictions)),
        "best_threshold": threshold,
        "positive_prediction_rate": float(predictions.mean()),
        "probabilities": probabilities,
        "predictions": predictions,
    }
    return metrics


def export_metrics(metrics_list: list[dict[str, float | str | np.ndarray]], output_path: Path) -> pd.DataFrame:
    records = []
    for item in metrics_list:
        records.append(
            {
                "model": str(item["model"]),
                "roc_auc": float(item["roc_auc"]),
                "average_precision": float(item["average_precision"]),
                "balanced_accuracy": float(item["balanced_accuracy"]),
                "f1_at_best_threshold": float(item["f1_at_best_threshold"]),
                "best_threshold": float(item["best_threshold"]),
                "positive_prediction_rate": float(item["positive_prediction_rate"]),
            }
        )
    table = pd.DataFrame.from_records(records).sort_values(by="average_precision", ascending=False)
    table.to_csv(output_path, index=False, encoding="utf-8-sig")
    return table


def save_pr_curve(metrics_list: list[dict[str, float | str | np.ndarray]], y_test: pd.Series, output_path: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(8.4, 5.8))

    for item in metrics_list:
        precision, recall, _ = precision_recall_curve(y_test, np.asarray(item["probabilities"]))
        ax.plot(
            recall,
            precision,
            linewidth=2,
            label=f"{item['model']} (AP={float(item['average_precision']):.3f}, AUC={float(item['roc_auc']):.3f})",
        )

    baseline = float(y_test.mean())
    ax.axhline(baseline, color="gray", linestyle="--", linewidth=1.2, label=f"baseline churn rate={baseline:.3f}")
    _ = ax.set_title("Precision-Recall curve comparison")
    _ = ax.set_xlabel("Recall")
    _ = ax.set_ylabel("Precision")
    _ = ax.set_xlim(0.0, 1.0)
    _ = ax.set_ylim(0.0, 1.02)
    _ = ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def save_confusion_matrices(
    metrics_list: list[dict[str, float | str | np.ndarray]],
    y_test: pd.Series,
    output_path: Path,
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, len(metrics_list), figsize=(11.8, 4.9))
    if len(metrics_list) == 1:
        axes = np.array([axes])

    for ax, item in zip(np.ravel(axes), metrics_list):
        matrix = confusion_matrix(y_test, np.asarray(item["predictions"]), labels=[0, 1])
        disp = ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=["stay", "churn"])
        disp.plot(ax=ax, colorbar=False, cmap="Blues", values_format="d")
        ax.set_title(f"{item['model']}\nthreshold={float(item['best_threshold']):.3f}")

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def normalize_importance(values: np.ndarray) -> np.ndarray:
    absolute_values = np.abs(values.astype(float))
    total = float(absolute_values.sum())
    if total <= 0.0:
        return np.zeros_like(absolute_values)
    return absolute_values / total


def export_feature_importance(
    *,
    logistic: Pipeline,
    gradient: Pipeline,
    feature_names: list[str],
    top_feature_count: int,
    output_path: Path,
) -> pd.DataFrame:
    logistic_coef = logistic.named_steps["model"].coef_.ravel()
    gradient_importance = gradient.named_steps["model"].feature_importances_

    table = pd.DataFrame(
        {
            "feature": feature_names,
            "logistic_signed_coef": logistic_coef,
            "logistic_abs_importance": normalize_importance(logistic_coef),
            "gradient_boosting_importance": normalize_importance(gradient_importance),
        }
    )
    table["combined_rank_score"] = table["logistic_abs_importance"] + table["gradient_boosting_importance"]
    table = table.sort_values(by="combined_rank_score", ascending=False)
    top_table = table.head(top_feature_count).copy()
    top_table.to_csv(output_path, index=False, encoding="utf-8-sig")
    return top_table


def write_summary(
    *,
    dataset: pd.DataFrame,
    metrics_table: pd.DataFrame,
    feature_table: pd.DataFrame,
    config: CaseConfig,
    paths: dict[str, Path],
    smoke_test: bool,
) -> Path:
    best_row = metrics_table.sort_values(by="average_precision", ascending=False).iloc[0]
    churn_rate = float(dataset[TARGET_COLUMN].mean())
    top_features = ", ".join(feature_table["feature"].head(5).tolist())

    lines = [
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"case_id: {CASE_ID}",
        f"seed: {config.seed}",
        f"sample_size: {len(dataset)}",
        f"churn_rate: {churn_rate:.3f}",
        f"data_mode: {DATA_MODE}",
        "imbalance_handling: LogisticRegression uses class_weight='balanced'; GradientBoosting uses balanced sample weights.",
        (
            "github_pattern_adaptation: adapted common open-source binary classification patterns—"
            "predict_proba-based evaluation, precision_recall_curve/roc_auc_score metrics, "
            "and class balancing for LogisticRegression."
        ),
        (
            f"best_model_by_average_precision: {best_row['model']} "
            f"(AP={best_row['average_precision']:.3f}, ROC_AUC={best_row['roc_auc']:.3f})"
        ),
        (
            "metric_snapshot: "
            + "; ".join(
                f"{row.model}: AUC={row.roc_auc:.3f}, AP={row.average_precision:.3f}, "
                f"BA={row.balanced_accuracy:.3f}, F1={row.f1_at_best_threshold:.3f}"
                for row in metrics_table.itertuples(index=False)
            )
        ),
        f"top_comparative_features: {top_features}",
        "interpretation_note: 逻辑回归的绝对系数强调线性方向强度；梯度提升树的重要性强调分裂贡献，两者不能做因果解释。",
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]

    summary_path = paths["output_dir"] / "summary.txt"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def write_smoke_artifact(paths: dict[str, Path], dataset: pd.DataFrame, smoke_test: bool) -> Path:
    artifact_path = paths["output_dir"] / "smoke_test.txt"
    mode = "SMOKE TEST" if smoke_test else "FULL RUN"
    artifact_path.write_text(
        "\n".join(
            [
                f"mode: {mode}",
                f"case_id: {CASE_ID}",
                f"sample_size: {len(dataset)}",
                f"churn_rate: {dataset[TARGET_COLUMN].mean():.3f}",
                "artifacts: model_metrics.csv, precision_recall_curve.png, confusion_matrices.png, feature_importance_comparison.csv, summary.txt",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact_path


def run_analysis(smoke_test: bool) -> dict[str, Path]:
    paths = resolve_paths()
    config = load_config(paths["params_file"])
    dataset = simulate_dataset(config, smoke_test=smoke_test)

    X = dataset[CONTINUOUS_COLUMNS + CATEGORICAL_COLUMNS + BINARY_COLUMNS].copy()
    y = dataset[TARGET_COLUMN].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=config.test_size,
        random_state=config.seed,
        stratify=y,
    )

    logistic, gradient, feature_names = fit_models(X_train, y_train, config)
    metrics_list = [
        evaluate_model("Logistic Regression", logistic, X_test, y_test),
        evaluate_model("Gradient Boosting", gradient, X_test, y_test),
    ]

    metrics_table = export_metrics(metrics_list, paths["output_dir"] / "model_metrics.csv")
    save_pr_curve(metrics_list, y_test, paths["output_dir"] / "precision_recall_curve.png")
    save_confusion_matrices(metrics_list, y_test, paths["output_dir"] / "confusion_matrices.png")
    feature_table = export_feature_importance(
        logistic=logistic,
        gradient=gradient,
        feature_names=feature_names,
        top_feature_count=config.top_feature_count,
        output_path=paths["output_dir"] / "feature_importance_comparison.csv",
    )
    summary_path = write_summary(
        dataset=dataset,
        metrics_table=metrics_table,
        feature_table=feature_table,
        config=config,
        paths=paths,
        smoke_test=smoke_test,
    )
    smoke_path = write_smoke_artifact(paths, dataset, smoke_test)

    return {
        "summary": summary_path,
        "smoke": smoke_path,
        "metrics": paths["output_dir"] / "model_metrics.csv",
        "pr_curve": paths["output_dir"] / "precision_recall_curve.png",
        "confusion": paths["output_dir"] / "confusion_matrices.png",
        "importance": paths["output_dir"] / "feature_importance_comparison.csv",
    }


def main() -> int:
    args = parse_args()
    artifacts = run_analysis(smoke_test=bool(args.smoke_test))
    print(f"[{CASE_ID}] generated artifacts:")
    for key, path in artifacts.items():
        print(f"- {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
